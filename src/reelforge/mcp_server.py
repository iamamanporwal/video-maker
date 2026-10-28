"""MCP server (stdio): every deterministic operation as a tool, plus the decision hand-off tools.

Ops only - no tool here calls an LLM. In agent mode Claude Code *is* the director: a stage stops with a
decision request, Claude reads it (decision_pending), answers (decision_submit), and re-runs the stage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

from . import review as rv
from . import stages
from .llm import Decider, DecisionPending, pending_decisions, submit_decision
from .ops import audio, glb, media, providers, remotion as rem
from .ops import capture as cap
from .ops import env as envops
from .ops.images import find_image as _find_image
from .ops.takes import AssetServer, make_takes as _make_takes
from .project import Project
from .schemas import BeatsDoc, Timeline
from .validate import validate_beats as _validate_beats, validate_timeline

mcp = MCPServer("reelforge", instructions="ReelForge ops tools. Load the reelforge skill for the workflow and decision rules.")


def _p(project: str) -> Project:
    p = Project.open(project)
    envops.load_env(p.root)
    return p


def _rel(p: Project, x) -> str:
    try:
        return str(Path(x).resolve().relative_to(p.root))
    except ValueError:
        return str(x)


# ------------------------------------------------------------------ project + pipeline


@mcp.tool()
def project_init(project: str, template: Optional[str] = None) -> dict:
    """Create a project folder (optionally from a template folder with brief.yaml/brand.json/assets/capture.yaml)."""
    from .cli import cmd_init

    class A:  # reuse the CLI implementation
        pass

    a = A()
    a.project, a.template = project, template
    cmd_init(a)
    return {"project": str(Path(project).resolve()), "files": sorted(x.name for x in Path(project).iterdir())}


@mcp.tool()
def env_check(project: Optional[str] = None) -> dict:
    """Check node, ffmpeg, Chrome, Remotion/Playwright deps, pinned port 3700, API keys and the app URL."""
    url = None
    if project:
        p = _p(project)
        url = p.brief.product.url
    return envops.env_check(url)


@mcp.tool()
def status(project: str) -> dict:
    """Stage status (S0-S10), current iteration, costs and pending decisions."""
    p = _p(project)
    st = p.state()
    return {"stages": {s: {"name": stages.STAGE_NAMES[s], **{k: v for k, v in st["stages"].get(s, {}).items() if k != "result"}}
                       for s in stages.STAGE_FUNCS},
            "iteration": st.get("iteration", 0), "costs": p.costs(),
            "pending_decisions": [d["decision"] for d in pending_decisions(p)]}


@mcp.tool()
def run_stage(project: str, stage: str, force: bool = False, options: Optional[dict] = None) -> dict:
    """Run one pipeline stage (S0..S10 or a name: init, treatment, beats, storyboard, capture, audio, prep, compose,
    render, review, handover). Cached by input hash unless force. If a decision is needed, returns
    status=awaiting_decision with the request path - answer it with decision_submit, then call run_stage again."""
    p = _p(project)
    try:
        return stages.run_stage(p, stage, force=force, **(options or {}))
    except DecisionPending as e:
        req = json.loads(e.request_path.read_text())
        return {"status": "awaiting_decision", "decision": e.decision_id, "request": _rel(p, e.request_path),
                "task": req["task"], "images": req["images"],
                "hint": "Read the request (decision_pending), answer with decision_submit, then re-run this stage."}
    except Exception as e:  # noqa: BLE001
        return {"status": "failed", "error": str(e)[:4000]}


@mcp.tool()
def decision_pending(project: str, decision: Optional[str] = None) -> Any:
    """List pending decision requests, or return one in full (task, context, image paths, rules, output JSON schema)."""
    p = _p(project)
    reqs = pending_decisions(p)
    if decision:
        r = next((x for x in reqs if x["decision"] == decision), None)
        return r or {"error": f"no pending request {decision}"}
    return [{"decision": r["decision"], "attempt": r.get("attempt", 0), "task": r["task"][:400]} for r in reqs]


@mcp.tool()
def decision_submit(project: str, decision: str, answer: dict) -> dict:
    """Submit a JSON answer for a pending decision. It is schema-validated when the stage re-runs; a rejected answer
    comes back as a new request with _previous_attempt_errors in its context."""
    p = _p(project)
    f = submit_decision(p, decision, answer)
    return {"saved": _rel(p, f), "next": "re-run the stage that requested it"}


# ------------------------------------------------------------------ plan data


@mcp.tool()
def validate_beats(project: str, beats: dict) -> dict:
    """Validate a beats.json document against the brief (grid, durations, hook, headline length, trademarks)."""
    p = _p(project)
    errs = _validate_beats(BeatsDoc.model_validate(beats), p.brief)
    return {"ok": not errs, "errors": errs}


@mcp.tool()
def write_timeline(project: str, timeline: dict) -> dict:
    """Validate and write plan/timeline.json (the renderer is a pure function of this file)."""
    p = _p(project)
    tl = Timeline.model_validate(timeline)
    errs = validate_timeline(tl, p.brief)
    if errs:
        return {"ok": False, "errors": errs}
    p.write_json("plan/timeline.json", tl)
    return {"ok": True, "path": "plan/timeline.json", "cuts": [c.name for c in tl.cuts]}


@mcp.tool()
def read_timeline(project: str) -> dict:
    """Return plan/timeline.json."""
    return _p(project).read_json("plan/timeline.json", {})


# ------------------------------------------------------------------ S3 / S7 / S8 rendering


@mcp.tool()
def render_stills(project: str, comp: str, frames: list[int], scale: float = 0.5, debug: bool = False) -> dict:
    """Render stills of a composition (e.g. 'hero-16x9', 'Poster-hero-9x16') at frames. One bundle, one browser."""
    p = _p(project)
    rem.write_brand_ts(p.brand)
    with AssetServer(p.root) as srv:
        props = rem.write_props(p, srv.url, debug=debug)
        out = rem.render_stills(p, props, [{"comp": comp, "frames": frames}], p.path("render", "stills"), scale=scale)
    return {"stills": [_rel(p, x) for x in out]}


@mcp.tool()
def contact_sheet(project: str, source: str, fps: float = 2.0) -> dict:
    """Contact sheet with timecode labels from a video or a directory of images (project-relative path)."""
    p = _p(project)
    src = p.path(source)
    out = media.contact_sheet(src, src.with_suffix(".sheet.jpg") if src.is_file() else src / "sheet.jpg", fps=fps)
    return {"sheet": _rel(p, out)}


@mcp.tool()
def render(project: str, cuts: Optional[list[str]] = None, formats: Optional[list[str]] = None) -> dict:
    """Render, master (-14 LUFS), posters, SRT and spec-verify the masters. Fails if any spec check fails."""
    p = _p(project)
    try:
        return stages.s8_render(p, Decider(p), cuts=cuts, formats=formats)
    except Exception as e:  # noqa: BLE001
        spec = p.path("render/out/spec-table.md")
        return {"status": "failed", "error": str(e)[:3000], "spec_table": spec.read_text() if spec.exists() else None}


@mcp.tool()
def master(project: str, src: str, dst: str) -> dict:
    """Two-pass loudness master to -14 LUFS / -1.5 dBTP, AAC 48k 320k, -shortest, +faststart (video copied)."""
    p = _p(project)
    return media.master(p.path(src), p.path(dst))


@mcp.tool()
def verify_specs(project: str, file: str, duration: float, width: int, height: int, fps: int = 30) -> dict:
    """Spec checks on one file: duration, resolution, fps, codec/profile, pix_fmt, AAC 48k stereo, loudness,
    true peak, decode errors, dark frames."""
    p = _p(project)
    return media.verify_specs(p.path(file), {"duration": duration, "width": width, "height": height, "fps": fps})


@mcp.tool()
def scan_dark_frames(project: str, file: str) -> dict:
    """Near-black frames and one-frame dips in a video."""
    p = _p(project)
    r = media.scan_dark_frames(p.path(file))
    return {"dark": r["dark"][:200], "dips": r["dips"], "frames": r["frames"]}


@mcp.tool()
def srt(project: str, cut: str) -> dict:
    """Write render/out/<cut>-16x9.srt from the timeline captions."""
    p = _p(project)
    ct = p.timeline.cut(cut)
    f = p.path("render/out", f"{cut}-16x9.srt")
    f.write_text(media.srt(ct.captions, ct.fps))
    return {"srt": _rel(p, f)}


# ------------------------------------------------------------------ S4 capture


@mcp.tool()
def capture_step(project: str, command: str, take: str, args: Optional[dict] = None, headless: Optional[bool] = None) -> dict:
    """Run a capture macro from capture.yaml (sketch | edit | to3d | look | models ...) against the real app.
    Records the screencast, events and mouse log to capture/<take>/."""
    p = _p(project)
    return cap.capture_step(p, command, take, args or {}, headless=headless)


@mcp.tool()
def ui_dump(project: str, view: str = "") -> dict:
    """Dump visible buttons/inputs/roles of an app view (for choosing selectors)."""
    p = _p(project)
    r = cap.ui_dump(p, view)
    r["ui"] = r.get("ui", [])[:300]
    return r


@mcp.tool()
def mint_auth(project: str, force: bool = False) -> dict:
    """Mint (or reuse, < 50 min old) the app's test token. Tokens expire after 1 hour."""
    p = _p(project)
    tok = cap.mint_auth(p, force=force)
    return {"minted": bool(tok), "token_preview": (tok[:8] + "...") if tok else None}


@mcp.tool()
def find_image(project: str, ref: str, candidates: list[str]) -> dict:
    """Pixel-match ref against candidates (history order is unstable: select by content, never by position)."""
    p = _p(project)
    r = _find_image(p.path(ref), [p.path(c) for c in candidates])
    return r


# ------------------------------------------------------------------ S5 audio + generative


@mcp.tool()
def gen_music(project: str, name: str, plan: dict) -> dict:
    """ElevenLabs Music via fal with a composition plan (section durations match the edit). Budget-checked."""
    p = _p(project)
    return {"file": _rel(p, providers.gen_music(p, name, plan))}


@mcp.tool()
def gen_sfx(project: str, cues: list[dict]) -> dict:
    """ElevenLabs SFX, max 4 concurrent. cues: [{name, prompt, seconds}]."""
    p = _p(project)
    return {"files": [_rel(p, x) for x in providers.gen_sfx(p, cues)]}


@mcp.tool()
def gen_video(project: str, clip: str, prompt: str, seconds: float, aspect: str = "16:9") -> dict:
    """fal video b-roll for NON-product shots only; logged as generated in CREDITS.md. Budget-checked."""
    p = _p(project)
    return {"file": _rel(p, providers.gen_video(p, clip, prompt, seconds, aspect))}


@mcp.tool()
def analyse_audio(project: str, file: str) -> dict:
    """Tempo, beat phase, kicks and drops (numpy, no AI)."""
    p = _p(project)
    a = audio.analyse(p.path(file), bpm_prior=p.brief.music.bpm)
    a["kicks"] = a["kicks"][:32]
    return a


@mcp.tool()
def align_music(project: str) -> dict:
    """Solve music offsets so drops land on the edit's bar lines; writes music segments into timeline.json."""
    return stages.align_music(_p(project))


# ------------------------------------------------------------------ S6 prep


@mcp.tool()
def make_takes(project: str, takes: Optional[list[str]] = None) -> dict:
    """Screencast frames -> indexable takes (plan/takes.json), mouse/events rebased to recording start."""
    p = _p(project)
    return _make_takes(p, takes)


@mcp.tool()
def inspect_glb(project: str, path: str) -> dict:
    """GLB bounds (node transforms baked), up-axis guess, materials, normalisation scale."""
    return glb.inspect_glb(_p(project).path(path))


@mcp.tool()
def texture_check(project: str, glb_path: str, source_image: Optional[str] = None) -> dict:
    """Is the base-colour texture baked lighter than the source image? Recommends a base-colour factor only."""
    p = _p(project)
    return glb.texture_check(p.path(glb_path), p.path(source_image) if source_image else None)


# ------------------------------------------------------------------ S9 review


@mcp.tool()
def evidence_pack(project: str, iteration: int) -> dict:
    """Build review/itNN: 2 fps timecoded contact sheets, 10 fps transition strips, full-res stills, waveform,
    loudness, dark-frame list and 320 px thumbnail tests for every master."""
    p = _p(project)
    idx = rv.evidence_pack(p, iteration)
    return {"dir": f"review/it{iteration:02d}", "images": [_rel(p, x) for x in rv.evidence_images(p, idx)],
            "masters": {k: {kk: v[kk] for kk in ("loudness", "dark_frames", "dips")} for k, v in idx["masters"].items()},
            "rubric": rv.RUBRIC, "hard_rules": rv.HARD_RULES_REVIEW}


@mcp.tool()
def scoreboard(project: str) -> dict:
    """SCOREBOARD rows so far and stuck dimensions (no improvement for 2 iterations)."""
    p = _p(project)
    rv.write_scoreboard(p)
    return {"rows": rv.scoreboard_rows(p), "stuck": rv.stuck_dimensions(p)}


# ------------------------------------------------------------------ misc


@mcp.tool()
def git_commit(project: str, message: str) -> dict:
    """Commit the project folder (one commit per stage / iteration)."""
    p = _p(project)
    p.commit(message)
    return {"committed": message}


@mcp.tool()
def costs(project: str) -> dict:
    """Spend so far per provider and the budgets."""
    p = _p(project)
    return {"spent": p.costs(), "budgets": p.brief.budgets.model_dump()}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
