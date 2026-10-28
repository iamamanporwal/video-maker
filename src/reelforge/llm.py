"""The only place an LLM is called. Every decision takes structured input and returns schema-validated JSON.

Two backends:
  * ``api``   - calls the Claude API directly (CLI / CI use).
  * ``agent`` - writes a decision request to ``plan/decisions/<id>.request.json`` and stops. The
                calling agent (Claude Code, via the skill + MCP ``decision_submit`` tool) or a human
                writes the answer; the stage re-runs and validates it. This lets Claude Code itself
                be the director without an API key.
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Any, Callable, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .project import Project, sha

T = TypeVar("T", bound=BaseModel)

MODEL = os.environ.get("REELFORGE_MODEL", "claude-opus-5-5")
# $ per million tokens (input, output) used for budget accounting.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50),
          "claude-fable-5-1": (10.0, 50.0)}

HARD_RULES = """\
HARD RULES (non-negotiable, also checked by Python):
1. Never fake the product. Every UI frame, image and 3D model comes from a real run of the product.
   Allowed: framing (crop, zoom, tilt), re-timing, cursor/highlight overlays, material/lighting/camera for 3D.
   Not allowed: invented UI, retouched outputs, edited geometry.
2. Generated video (fal) only for non-product shots, always labelled as generated.
3. Trademarks listed in rules.trademark_avoid must never appear on screen, in typed prompts or legible on outputs.
4. Honesty labels: real timings are shown as real ("3 min 7 s - real time").
5. Headlines are at most 4 words. Every animation is frame-driven and deterministic.
"""


class DecisionPending(RuntimeError):
    """Raised in agent mode when a decision has been requested but not yet answered."""

    def __init__(self, decision_id: str, request_path: Path):
        super().__init__(f"decision {decision_id} awaiting an answer: {request_path}")
        self.decision_id = decision_id
        self.request_path = request_path


class DecisionFailed(RuntimeError):
    pass


def backend() -> str:
    mode = os.environ.get("REELFORGE_DECIDER")
    if mode in ("api", "agent"):
        return mode
    return "api" if (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")) else "agent"


def _image_block(path: Path, max_side: int = 1568) -> dict:
    from PIL import Image

    im = Image.open(path)
    im.thumbnail((max_side, max_side))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.standard_b64encode(buf.getvalue()).decode()}}


class Decider:
    def __init__(self, project: Project, mode: Optional[str] = None, model: str = MODEL):
        self.p = project
        self.mode = mode or backend()
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    # ------------------------------------------------------------------ public

    def decide(
        self,
        decision_id: str,
        schema: Type[T],
        task: str,
        context: dict[str, Any],
        images: Optional[list[Path]] = None,
        validator: Optional[Callable[[T], list[str]]] = None,
        web_research: bool = False,
        effort: str = "high",
        max_retries: int = 3,
    ) -> T:
        images = [Path(i) for i in (images or [])]
        inputs_hash = sha({"task": task, "context": context, "images": [sha(i) for i in images],
                           "schema": schema.model_json_schema()})
        cached = self._cached(decision_id, inputs_hash, schema, validator)
        if cached is not None:
            return cached
        if self.mode == "agent":
            return self._agent(decision_id, schema, task, context, images, validator, inputs_hash)
        return self._api(decision_id, schema, task, context, images, validator, web_research, effort,
                         max_retries, inputs_hash)

    # ------------------------------------------------------------------ cache

    def _dir(self) -> Path:
        d = self.p.path("plan/decisions")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _cached(self, did: str, h: str, schema: Type[T], validator) -> Optional[T]:
        f = self._dir() / f"{did}.json"
        if not f.exists():
            return None
        rec = json.loads(f.read_text())
        if rec.get("inputs_hash") != h:
            return None
        try:
            out = schema.model_validate(rec["output"])
        except ValidationError:
            return None
        if validator and validator(out):
            return None
        return out

    def _store(self, did: str, h: str, out: BaseModel, meta: dict) -> None:
        payload = out.model_dump(mode="json")
        (self._dir() / f"{did}.json").write_text(json.dumps(
            {"decision": did, "inputs_hash": h, "output": payload, **meta}, indent=2))
        self.p.log("decisions", {"decision": did, "inputs_hash": h, "backend": self.mode, **meta,
                                 "output_hash": sha(payload)})

    # ------------------------------------------------------------------ agent backend

    def _agent(self, did, schema, task, context, images, validator, h) -> BaseModel:
        req = self._dir() / f"{did}.request.json"
        resp = self._dir() / f"{did}.response.json"
        if resp.exists():
            data = json.loads(resp.read_text())
            try:
                out = schema.model_validate(data)
                errs = validator(out) if validator else []
            except ValidationError as e:
                errs = [str(e)]
            if not errs:
                self._store(did, h, out, {"model": "agent"})
                resp.unlink()
                req.unlink(missing_ok=True)
                return out
            prev = json.loads(req.read_text()) if req.exists() else {}
            context = {**context, "_previous_attempt_errors": errs}
            resp.rename(resp.with_suffix(".rejected.json"))
            prev_attempts = prev.get("attempt", 0) + 1
        else:
            prev_attempts = 0
        req.write_text(json.dumps({
            "decision": did,
            "inputs_hash": h,
            "attempt": prev_attempts,
            "rules": HARD_RULES,
            "task": task,
            "context": context,
            "images": [str(i) for i in images],
            "output_schema": schema.model_json_schema(),
            "answer_with": f"write JSON matching output_schema to {resp} (or call MCP tool decision_submit)",
        }, indent=2, default=str))
        raise DecisionPending(did, req)

    # ------------------------------------------------------------------ api backend

    def _api(self, did, schema, task, context, images, validator, web, effort, max_retries, h) -> BaseModel:
        import anthropic

        self.p.check_budget("llm", est_usd=0.5)
        research = ""
        if web:
            research = self._research(task, context)
        content: list[dict] = [_image_block(i) for i in images]
        text = f"{task}\n\nCONTEXT (JSON):\n{json.dumps(context, indent=1, default=str)}"
        if research:
            text += f"\n\nRESEARCH NOTES:\n{research}"
        if images:
            text += "\n\nIMAGES (in order): " + ", ".join(i.name for i in images)
        content.append({"type": "text", "text": text})
        messages: list[dict] = [{"role": "user", "content": content}]
        system = [{"type": "text", "text": "You are the director of a product launch film. You make one decision "
                   "at a time and answer only with JSON matching the requested schema.\n\n" + HARD_RULES,
                   "cache_control": {"type": "ephemeral"}}]
        last_err: list[str] = []
        for attempt in range(max_retries + 1):
            try:
                resp = self.client.messages.parse(
                    model=self.model, max_tokens=16000, system=system, messages=messages,
                    output_format=schema, output_config={"effort": effort},
                    extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
                    extra_body={"fallbacks": "default"},
                )
            except anthropic.RateLimitError:
                raise
            except anthropic.APIStatusError as e:
                raise DecisionFailed(f"{did}: API error {e.status_code}: {e.message}") from e
            self._account(did, resp)
            if resp.stop_reason == "refusal":
                raise DecisionFailed(f"{did}: model refused ({getattr(resp, 'stop_details', None)})")
            out = resp.parsed_output
            errs = [] if out is not None else ["output did not parse against the schema"]
            if out is not None and validator:
                errs = validator(out)
            if not errs:
                self._store(did, h, out, {"model": self.model, "attempts": attempt + 1})
                return out
            last_err = errs
            self.p.log("decisions", {"decision": did, "attempt": attempt, "validator_errors": errs})
            # Append-only history: pass every block (thinking included) back unchanged.
            messages.append({"role": "assistant", "content": [
                b.model_dump(exclude_none=True, exclude={"parsed_output"}) for b in resp.content]})
            messages.append({"role": "user", "content": "The validator rejected that answer:\n- "
                             + "\n- ".join(errs) + "\nReturn a corrected JSON answer."})
        raise DecisionFailed(f"{did}: still invalid after {max_retries + 1} attempts: {last_err}")

    def _research(self, task: str, context: dict) -> str:
        resp = self.client.messages.create(
            model=self.model, max_tokens=16000,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}],
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": f"Research for this task, then write concise notes "
                       f"(what to steal, from whom, why):\n{task}\n\n{json.dumps(context, default=str)[:6000]}"}],
        )
        self._account("research", resp)
        return "\n".join(b.text for b in resp.content if b.type == "text")

    def _account(self, did: str, resp) -> None:
        u = resp.usage
        pin, pout = PRICES.get(self.model, (5.0, 25.0))
        usd = (u.input_tokens * pin + u.output_tokens * pout + (u.cache_read_input_tokens or 0) * pin * 0.1
               + (u.cache_creation_input_tokens or 0) * pin * 1.25) / 1e6
        self.p.add_cost("llm", round(usd, 5), decision=did, input_tokens=u.input_tokens,
                        output_tokens=u.output_tokens)


def submit_decision(project: Project, decision_id: str, answer: dict | str) -> Path:
    """Used by the MCP server / UI to answer an agent-mode decision request."""
    data = json.loads(answer) if isinstance(answer, str) else answer
    f = project.path("plan/decisions", f"{decision_id}.response.json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2))
    return f


def pending_decisions(project: Project) -> list[dict]:
    d = project.path("plan/decisions")
    if not d.exists():
        return []
    return [json.loads(f.read_text()) for f in sorted(d.glob("*.request.json"))]
