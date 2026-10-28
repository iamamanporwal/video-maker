"""S4 ops: expand capture macros from the product's capture.yaml into primitive steps and run capture.mjs.

The product-specific knowledge (selectors, flows) lives in <project>/capture.yaml, so the driver stays generic.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

import yaml

from ..project import Project
from .env import chrome_path, node_dir

TOKEN_TTL_S = 50 * 60  # tokens expire after 1 hour: re-mint before each batch


def _subst(obj: Any, vars: dict) -> Any:
    if isinstance(obj, str):
        m = re.fullmatch(r"\{(\w+)\}", obj)
        if m and m.group(1) in vars:
            return vars[m.group(1)]
        return re.sub(r"\{(\w+)\}", lambda mm: str(vars.get(mm.group(1), mm.group(0))), obj)
    if isinstance(obj, dict):
        return {k: _subst(v, vars) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_subst(v, vars) for v in obj]
    return obj


def capture_config(p: Project) -> dict:
    f = p.path("capture.yaml")
    if not f.exists():
        raise FileNotFoundError(f"{f} missing: describe the product's flows (macros) for capture")
    return yaml.safe_load(f.read_text())


def mint_auth(p: Project, force: bool = False) -> Optional[str]:
    auth = p.brief.product.auth
    if auth.method != "test_token":
        return None
    cache = p.path("logs", "token.json")
    if cache.exists() and not force:
        c = json.loads(cache.read_text())
        if time.time() - c["at"] < TOKEN_TTL_S:
            return c["token"]
    script = Path(auth.script).expanduser()
    if not script.is_absolute():
        script = p.root / script
    cwd = Path(os.environ.get("REELFORGE_APP_DIR", script.parent.parent if script.parent.name == "scripts" else script.parent))
    r = subprocess.run(["node", str(script)], cwd=cwd, capture_output=True, text=True, check=True)
    token = r.stdout.strip().splitlines()[-1].strip()
    cache.write_text(json.dumps({"token": token, "at": time.time()}))
    p.log("capture", {"event": "token_minted"})
    return token


def expand(p: Project, command: str, vars: dict) -> list[dict]:
    cfg = capture_config(p)
    macros = cfg.get("macros", {})
    if command not in macros:
        raise KeyError(f"capture.yaml has no macro '{command}' (have: {list(macros)})")
    base = {"url": p.brief.product.url.rstrip("/"), **cfg.get("vars", {}), **vars}
    steps = []
    for st in macros[command]:
        if "use" in st:  # macro composition
            steps += expand(p, st["use"], {**vars, **st.get("with", {})})
        else:
            steps.append(_subst(st, base))
    return steps


def run_take(p: Project, take: str, steps: list[dict], headless: Optional[bool] = None,
             timeout: int = 1800) -> dict:
    cfg = capture_config(p)
    out = p.path("capture", take)
    if out.exists():
        for f in (out / "frames").glob("*.jpg"):
            f.unlink()
    out.mkdir(parents=True, exist_ok=True)
    token = mint_auth(p)
    auth = p.brief.product.auth
    job = {
        "take": take, "outDir": str(out), "steps": steps,
        "profileDir": str(p.path("capture", ".profile")),
        "viewport": cfg.get("viewport", {"width": 1920, "height": 1080}), "dpr": cfg.get("dpr", 2),
        "chromePath": chrome_path(),
        "headless": cfg.get("headless", False) if headless is None else headless,
        "auth": {"token": token, "key": auth.local_storage_key, "extra": cfg.get("local_storage", {})} if token else None,
        "storageState": auth.storage_state,
        "cosmetics": {"replaceText": cfg.get("replace_text", {})},
    }
    jf = out / "job.json"
    jf.write_text(json.dumps(job, indent=1))
    t0 = time.time()
    r = subprocess.run(["node", str(node_dir("capture") / "capture.mjs"), str(jf)], capture_output=True, text=True,
                       timeout=timeout)
    (out / "capture.stdout.log").write_text(r.stdout + "\n" + r.stderr)
    info = json.loads((out / "take.json").read_text()) if (out / "take.json").exists() else {"ok": False}
    events = json.loads((out / "events.json").read_text()) if (out / "events.json").exists() else []
    real = [e for e in events if "waitMs" in e]
    _capture_log(p, take, info, real, time.time() - t0)
    p.log("capture", {"take": take, "ok": info.get("ok"), "frames": info.get("frames"), "wall_s": round(time.time() - t0, 1)})
    return {"take": take, "ok": info.get("ok", False), "error": info.get("error"), "frames": info.get("frames"),
            "dir": str(out), "real_timings": [{"event": e["name"], "seconds": round(e["waitMs"] / 1000, 1)} for e in real],
            "outputs": [f.name for f in out.iterdir() if f.suffix in (".jpg", ".png", ".glb") and f.parent == out]}


def _capture_log(p: Project, take: str, info: dict, real: list[dict], wall: float) -> None:
    f = p.path("logs", "capture-log.md")
    head = f.read_text() if f.exists() else "# Capture log\n\nReal timings recorded during capture (used for honest on-screen tags).\n\n"
    lines = [f"## {take} - {time.strftime('%Y-%m-%d %H:%M')}",
             f"- ok: {info.get('ok')}  frames: {info.get('frames')}  wall: {wall:.1f}s"]
    lines += [f"- {e['name']}: {e['waitMs'] / 1000:.1f}s real time" for e in real]
    if info.get("error"):
        lines.append(f"- error: `{str(info['error']).splitlines()[0]}`")
    f.write_text(head + "\n".join(lines) + "\n\n")


def capture_step(p: Project, command: str, take: str, args: dict, headless: Optional[bool] = None) -> dict:
    """High-level step: sketch | edit | to3d | look | models (macros in capture.yaml)."""
    if command in ("sketch", "edit") and "strokes" in args and isinstance(args["strokes"], str):
        args = {**args, "strokes": json.loads(Path(args["strokes"]).read_text())["strokes"]}
    steps = expand(p, command, args)
    return run_take(p, take, steps, headless=headless)


def ui_dump(p: Project, view: str = "", take: str = "_ui") -> dict:
    url = p.brief.product.url.rstrip("/") + ("/" + view.lstrip("/") if view else "")
    res = run_take(p, take, [{"action": "goto", "url": url}, {"action": "dump_ui", "as": "ui.json"},
                             {"action": "screenshot", "as": "ui.png"}], headless=True)
    f = p.path("capture", take, "ui.json")
    res["ui"] = json.loads(f.read_text()) if f.exists() else []
    return res
