#!/usr/bin/env python3
"""MCP server (stdio) for Turbo MLX: local image generation, image editing and video generation on Apple silicon.

It drives the app's own engine (`turbo-engine serve`, newline-delimited JSON on stdin/stdout) with the models the app
has already downloaded into the Hugging Face cache. No dependencies beyond the standard library.

The engine in /Applications/Turbo MLX.app is sandboxed with `com.apple.security.inherit`, so it only starts when the
sandboxed app launches it. The server therefore keeps a private copy (engine + its two resource bundles) under
~/.local/share/turbo-mlx-mcp/engine, ad-hoc signed without the sandbox entitlement, and refreshes it whenever the
app is updated. The app itself is never modified.

Engine protocol (turbo-engine 0.4), as observed:
  -> {"cmd":"generate","id":..,"model":{"family","path","lowRam","text_encoder_path"?},
      "params":{"prompt","negativePrompt"?,"seed","width","height","steps","guidance","output",
                "image"?,"images"?,"frames"?,"fps"?,"quality"?}}       (steps and guidance are required)
  -> {"cmd":"cancel","id":..}   {"cmd":"shutdown"}
  <- {"event":"ready",..}  {"event":"phase","id","phase",..}  {"event":"done","id","path",..}  {"event":"error",..}

Register:  claude mcp add -s user turbo-mlx -- python3 /abs/path/tools/turbo_mlx_mcp.py
Env:       TURBO_MLX_APP, TURBO_MLX_HOME, TURBO_MLX_OUT, HF_HUB_CACHE / HF_HOME
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

APP = Path(os.environ.get("TURBO_MLX_APP", "/Applications/Turbo MLX.app"))
HOME = Path(os.environ.get("TURBO_MLX_HOME", "~/.local/share/turbo-mlx-mcp")).expanduser()
OUT = Path(os.environ.get("TURBO_MLX_OUT", "~/Movies/Turbo MLX MCP")).expanduser()
HUB = Path(os.environ.get("HF_HUB_CACHE") or Path(os.environ.get("HF_HOME", "~/.cache/huggingface")) / "hub").expanduser()
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")

# Models the engine knows (repo → family, what it does, default steps/guidance). Order = preference.
MODELS = [
    # repo,                                          family,           kinds,                  steps, guidance
    ("mflux-community/z-image-turbo-mflux-q8",       "z-image-turbo",   {"image"},                  9, 1.0),
    ("mflux-community/z-image-turbo-mflux-q4",       "z-image-turbo",   {"image"},                  9, 1.0),
    ("joeynyc/Ming-Image-0.1-Design-mflux-q8-te5",   "ming",            {"image", "edit"},          8, 1.0),
    ("mflux-community/flux2-klein-4b-mflux-q4",      "flux2-klein",     {"image", "edit"},          4, 1.0),
    ("black-forest-labs/flux-3-image-klein",         "flux3-klein",     {"image", "edit"},         16, 1.0),
    ("mflux-community/qwen-image-2512-mflux-q4",     "qwen-image",      {"image"},                 10, 4.0),
    ("mflux-community/qwen-image-edit-2511-mflux-q4", "qwen-image-edit", {"edit"},                  8, 4.0),
    ("mlx-community/SenseNova-U1.5-8B-MoT-8step-4bit", "sensenova",     {"image", "edit"},          8, 1.0),
    ("mlx-community/MOSS-Image-SFT-bf16",            "moss-image",      {"image"},                 50, 4.0),
    ("dgrauet/ltx-2.3-mlx-q8",                       "ltx-2",           {"video"},                  8, 1.0),
    ("dgrauet/ltx-2.3-mlx-q4",                       "ltx-2",           {"video"},                  8, 1.0),
    ("dgrauet/ltx-2.5-mlx-q4",                       "ltx-2.5",         {"video"},                  8, 1.0),
]
LTX_TEXT_ENCODER = "mlx-community/gemma-3-12b-it-4bit"


def log(*a):
    print("[turbo-mlx-mcp]", *a, file=sys.stderr, flush=True)


def snapshot(repo: str) -> Path | None:
    snaps = HUB / f"models--{repo.replace('/', '--')}" / "snapshots"
    if not snaps.is_dir():
        return None
    dirs = sorted((p for p in snaps.iterdir() if p.is_dir() and any(p.iterdir())), key=lambda p: p.stat().st_mtime)
    return dirs[-1] if dirs else None


def installed() -> list[dict]:
    out = []
    for repo, fam, kinds, steps, guidance in MODELS:
        if (path := snapshot(repo)):
            out.append({"id": repo, "family": fam, "kinds": sorted(kinds), "path": str(path),
                        "default_steps": steps, "default_guidance": guidance})
    return out


def pick_model(kind: str, want: str | None) -> dict:
    models = installed()
    usable = [m for m in models if kind in m["kinds"]]
    if want:
        hits = [m for m in usable if want in (m["id"], m["family"]) or want.lower() in m["id"].lower()]
        if not hits:
            raise ToolError(f"model {want!r} is not installed for {kind}. Installed for {kind}: "
                            f"{[m['id'] for m in usable] or 'none'}. Download models in the Turbo MLX app.")
        return hits[0]
    if not usable:
        raise ToolError(f"no installed Turbo MLX model can do {kind}. Download one in the Turbo MLX app "
                        f"(installed: {[m['id'] for m in models] or 'none'}).")
    return usable[0]


class ToolError(Exception):
    pass


# ---------------------------------------------------------------------------------------------------- engine copy

def engine_path() -> Path:
    """Private, unsandboxed copy of the app's engine; refreshed when the app's engine changes."""
    src = APP / "Contents/MacOS/turbo-engine"
    if not src.exists():
        raise ToolError(f"Turbo MLX engine not found at {src}. Install Turbo MLX or set TURBO_MLX_APP.")
    st = src.stat()
    stamp = f"{st.st_size}:{int(st.st_mtime)}"
    dest = HOME / "engine"
    exe, stamp_file = dest / "turbo-engine", dest / ".source-stamp"
    if exe.exists() and stamp_file.exists() and stamp_file.read_text() == stamp:
        return exe
    log("installing engine copy from", APP)
    tmp = HOME / f"engine.tmp-{os.getpid()}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    shutil.copy2(src, tmp / "turbo-engine")
    for b in (APP / "Contents/Resources").glob("*.bundle"):
        shutil.copytree(b, tmp / b.name, symlinks=True)
    subprocess.run(["xattr", "-cr", str(tmp)], check=False)
    r = subprocess.run(["codesign", "--force", "-s", "-", str(tmp / "turbo-engine")], capture_output=True, text=True)
    if r.returncode:
        raise ToolError(f"could not sign the engine copy: {r.stderr.strip()}")
    (tmp / ".source-stamp").write_text(stamp)
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    return exe


# ---------------------------------------------------------------------------------------------------- engine process

class Engine:
    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.info: dict = {}
        self.jobs: dict[str, dict] = {}
        self.lock = threading.RLock()
        self.cv = threading.Condition(self.lock)
        self.stderr_tail: list[str] = []

    def start(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                return
            exe = engine_path()
            self.info = {}
            self.proc = subprocess.Popen([str(exe), "serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True, bufsize=1, cwd=str(exe.parent))
            threading.Thread(target=self._read_out, args=(self.proc,), daemon=True).start()
            threading.Thread(target=self._read_err, args=(self.proc,), daemon=True).start()
            deadline = time.time() + 60
            while not self.info and self.proc.poll() is None and time.time() < deadline:
                self.cv.wait(1)
            if not self.info:
                code = self.proc.poll()
                tail = "\n".join(self.stderr_tail[-8:])
                self.proc.kill()
                raise ToolError(f"Turbo MLX engine did not start (exit {code}). {tail}")
            log("engine ready:", self.info.get("engine"), self.info.get("device"))

    def _read_err(self, proc):
        for line in proc.stderr:
            line = line.rstrip()
            with self.lock:
                self.stderr_tail = (self.stderr_tail + [line])[-40:]
            log("engine:", line[:300])

    def _read_out(self, proc):
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                log("engine stdout:", line.rstrip()[:300])
                continue
            with self.lock:
                kind, jid = ev.get("event"), ev.get("id")
                if kind == "ready":
                    self.info = ev
                job = self.jobs.get(jid) if jid else None
                if job:
                    job["updated"] = time.time()
                    if kind == "done":
                        job.update(status="done", phase="done", result=ev)
                    elif kind in ("error", "failure", "failed"):
                        msg = ev.get("message") or ev.get("error") or ev.get("errorDescription") or json.dumps(ev)
                        job.update(status="error", error=str(msg))
                    elif kind == "cancelled":
                        job.update(status="cancelled")
                    else:
                        if job["status"] == "queued":
                            job["status"] = "running"
                            job["started"] = time.time()
                        if ev.get("phase"):
                            job["phase"] = ev["phase"]
                        for k in ("step", "total", "frames"):
                            if k in ev:
                                job[k] = ev[k]
                self.cv.notify_all()
        # stdout closed: the engine exited (crash, OOM, shutdown). Fail whatever it was working on.
        with self.lock:
            code = proc.wait()
            tail = [l for l in self.stderr_tail if "rror" in l] or self.stderr_tail
            for job in self.jobs.values():
                if job["status"] in ("queued", "running"):
                    job.update(status="error", error=f"engine exited (code {code}): {' | '.join(tail[-3:])}")
            self.cv.notify_all()

    def submit(self, model: dict, params: dict, kind: str) -> dict:
        self.start()
        jid = uuid.uuid4().hex[:12]
        model_spec = {"family": model["family"], "path": model["path"], "lowRam": model.get("lowRam", True)}
        if model["family"].startswith("ltx"):
            enc = snapshot(LTX_TEXT_ENCODER)
            if not enc:
                raise ToolError(f"LTX needs its text encoder {LTX_TEXT_ENCODER}; download it in the Turbo MLX app.")
            model_spec["text_encoder_path"] = str(enc)
        cmd = {"cmd": "generate", "id": jid, "model": model_spec, "params": params}
        job = {"id": jid, "kind": kind, "model": model["id"], "status": "queued", "phase": "queued",
               "created": time.time(), "updated": time.time(), "output": params["output"],
               "prompt": params.get("prompt", "")[:200]}
        with self.lock:
            self.jobs[jid] = job
            try:
                self.proc.stdin.write(json.dumps(cmd) + "\n")
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                job.update(status="error", error=f"engine not accepting work: {e}")
        return job

    def wait(self, jid: str, timeout: float) -> dict:
        end = time.time() + timeout
        with self.lock:
            job = self.jobs[jid]
            while job["status"] in ("queued", "running") and time.time() < end:
                self.cv.wait(min(5, max(0.1, end - time.time())))
            return dict(job)

    def cancel(self, jid: str) -> dict:
        with self.lock:
            job = self.jobs.get(jid)
            if not job:
                raise ToolError(f"unknown job {jid}")
            if job["status"] in ("queued", "running") and self.proc and self.proc.poll() is None:
                self.proc.stdin.write(json.dumps({"cmd": "cancel", "id": jid}) + "\n")
                self.proc.stdin.flush()
                job["cancel_requested"] = True
            return dict(job)

    def shutdown(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                try:
                    self.proc.stdin.write('{"cmd": "shutdown"}\n')
                    self.proc.stdin.flush()
                    self.proc.wait(5)
                except Exception:
                    self.proc.kill()


ENGINE = Engine()


# ---------------------------------------------------------------------------------------------------- tools

def _out_path(output: str | None, kind: str, prompt: str, ext: str) -> str:
    if output:
        p = Path(output).expanduser()
        if p.suffix.lower() != ext:
            p = p.with_suffix(ext)
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:40].strip("-") or kind
        p = OUT / f"{time.strftime('%Y%m%d-%H%M%S')}-{kind}-{slug}{ext}"
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p.resolve())


def _in_path(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ToolError(f"input image not found: {path}")
    return str(p)


def _snap(v, mult: int, lo: int, hi: int) -> int:
    return int(min(hi, max(lo, round(int(v) / mult) * mult)))


def _base_params(a: dict, model: dict, kind: str, ext: str, mult: int) -> dict:
    prompt = (a.get("prompt") or "").strip()
    if not prompt:
        raise ToolError("prompt is required")
    p = {
        "prompt": prompt,
        "seed": int(a["seed"]) if a.get("seed") is not None else int.from_bytes(os.urandom(4), "big") % 2**31,
        "width": _snap(a.get("width", 1024 if kind != "video" else 768), mult, 256, 2048),
        "height": _snap(a.get("height", 1024 if kind != "video" else 512), mult, 256, 2048),
        "steps": int(a.get("steps") or model["default_steps"]),
        "guidance": float(a["guidance"]) if a.get("guidance") is not None else model["default_guidance"],
        "output": _out_path(a.get("output"), kind, prompt, ext),
    }
    if a.get("negative_prompt"):
        p["negativePrompt"] = a["negative_prompt"]
    return p


def _thumb(path: str, side: int = 512) -> dict | None:
    """Small JPEG preview so the calling model can see the result without loading a full-size file."""
    try:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td) / "t.jpg"
            r = subprocess.run(["sips", "-s", "format", "jpeg", "-Z", str(side), path, "--out", str(t)],
                               capture_output=True)
            if r.returncode or not t.exists():
                return None
            return {"type": "image", "mimeType": "image/jpeg", "data": base64.b64encode(t.read_bytes()).decode()}
    except Exception:
        return None


def _report(job: dict, preview: bool) -> list[dict]:
    view = {k: job.get(k) for k in ("id", "kind", "status", "phase", "model", "output", "error", "step", "total")
            if job.get(k) is not None}
    if job.get("started"):
        view["elapsed_s"] = round((job.get("updated") or time.time()) - job["started"], 1)
    res = job.get("result") or {}
    for k in ("path", "poster", "width", "height", "seed", "frames", "fps", "seconds", "timings"):
        if k in res:
            view[k] = res[k]
    if res.get("peak_memory"):
        view["peak_memory_gb"] = round(res["peak_memory"] / 1e9, 1)
    if job["status"] in ("queued", "running"):
        view["hint"] = "still generating; call turbo_mlx_status with this id to check again"
    content = [{"type": "text", "text": json.dumps(view, indent=1)}]
    if preview and job["status"] == "done":
        still = res.get("poster") or res.get("path")
        if still and (t := _thumb(still)):
            content.append(t)
    return content


def _run(kind: str, model: dict, params: dict, a: dict, default_timeout: float):
    job = ENGINE.submit(model, params, kind)
    if a.get("wait", True):
        job = ENGINE.wait(job["id"], float(a.get("timeout_s") or default_timeout))
    else:
        job = dict(job)
    if job["status"] == "error":
        raise ToolError(f"generation failed: {job.get('error')}")
    return _report(job, a.get("preview", True))


def tool_generate_image(a):
    model = pick_model("image", a.get("model"))
    params = _base_params(a, model, "image", ".png", 16)
    return _run("image", model, params, a, 600)


def tool_edit_image(a):
    model = pick_model("edit", a.get("model"))
    params = _base_params(a, model, "edit", ".png", 16)
    params["image"] = _in_path(a["image"])
    refs = [_in_path(p) for p in a.get("reference_images") or []]
    if refs:
        params["images"] = [params["image"], *refs]
    if "width" not in a and "height" not in a:   # keep the source's aspect ratio by default
        try:
            r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", params["image"]],
                               capture_output=True, text=True)
            w, h = (int(x) for x in re.findall(r"pixel(?:Width|Height): (\d+)", r.stdout))
            s = 1024 / max(w, h)
            params["width"], params["height"] = _snap(w * s, 16, 256, 2048), _snap(h * s, 16, 256, 2048)
        except Exception:
            pass
    return _run("edit", model, params, a, 600)


def tool_generate_video(a):
    model = pick_model("video", a.get("model"))
    params = _base_params(a, model, "video", ".mp4", 32)
    fps = int(a.get("fps") or 24)
    if a.get("frames"):
        frames = int(a["frames"])
    else:
        frames = round(float(a.get("seconds") or 5) * fps)
    params["frames"] = max(9, (frames - 1) // 8 * 8 + 1)   # LTX wants 8k+1 frames
    params["fps"] = fps
    if a.get("image"):
        params["image"] = _in_path(a["image"])            # image-to-video: becomes the first frame
    if a.get("quality"):
        params["quality"] = True
    return _run("video", model, params, a, 1800)


def tool_status(a):
    if a.get("cancel"):
        job = ENGINE.cancel(a["cancel"])
        return _report(ENGINE.wait(job["id"], 15), False)
    if a.get("id"):
        with ENGINE.lock:
            if a["id"] not in ENGINE.jobs:
                raise ToolError(f"unknown job {a['id']} (jobs live only as long as this server process)")
        job = ENGINE.wait(a["id"], float(a.get("wait_s") or 0))
        return _report(job, a.get("preview", True))
    with ENGINE.lock:
        running = ENGINE.proc is not None and ENGINE.proc.poll() is None
        jobs = [{k: j.get(k) for k in ("id", "kind", "status", "phase", "output", "error") if j.get(k)}
                for j in sorted(ENGINE.jobs.values(), key=lambda j: j["created"])[-20:]]
        info = {k: ENGINE.info.get(k) for k in ("engine", "device", "mlx", "families") if ENGINE.info.get(k)}
    view = {"app": str(APP), "app_installed": (APP / "Contents/MacOS/turbo-engine").exists(),
            "engine_running": running, "engine": info or "not started (starts on first generation)",
            "output_dir": str(OUT), "models": [{k: m[k] for k in ("id", "family", "kinds")} for m in installed()],
            "jobs": jobs}
    return [{"type": "text", "text": json.dumps(view, indent=1)}]


COMMON = {
    "prompt": {"type": "string", "description": "What to make. Be concrete: subject, setting, style, camera, light."},
    "negative_prompt": {"type": "string", "description": "What to avoid (models with CFG only)."},
    "seed": {"type": "integer", "description": "Fix for reproducible results; random when omitted."},
    "steps": {"type": "integer", "description": "Denoising steps; the model's default when omitted."},
    "guidance": {"type": "number", "description": "CFG scale; the model's default when omitted."},
    "model": {"type": "string", "description": "Model repo id or family (see turbo_mlx_status); best installed one when omitted."},
    "output": {"type": "string", "description": f"Where to save the file; default {OUT}/<time>-<prompt>."},
    "wait": {"type": "boolean", "description": "Block until done (default true). false returns a job id at once."},
    "timeout_s": {"type": "number", "description": "Max seconds to block when wait=true; the job keeps running after."},
    "preview": {"type": "boolean", "description": "Attach a small JPEG preview of the result (default true)."},
}


def _schema(extra: dict, required=("prompt",)):
    return {"type": "object", "properties": {**COMMON, **extra}, "required": list(required)}


TOOLS = {
    "turbo_mlx_generate_image": (tool_generate_image, {
        "description": "Generate an image from a text prompt with a local Turbo MLX model (Apple silicon, offline, "
                       "no cost). Returns the saved PNG path and a preview. Typical time: 10-60 s.",
        "inputSchema": _schema({"width": {"type": "integer", "description": "Pixels, multiple of 16 (default 1024)."},
                                "height": {"type": "integer", "description": "Pixels, multiple of 16 (default 1024)."}}),
    }),
    "turbo_mlx_edit_image": (tool_edit_image, {
        "description": "Edit an existing image with an instruction (e.g. 'make it night', 'turn the cube blue', "
                       "'put this character in a desert') using a local Turbo MLX edit-capable model. Optional extra "
                       "reference images. Returns the saved PNG path and a preview.",
        "inputSchema": _schema({
            "image": {"type": "string", "description": "Path of the image to edit."},
            "reference_images": {"type": "array", "items": {"type": "string"},
                                 "description": "Extra reference image paths (style, subject, product)."},
            "width": {"type": "integer", "description": "Output width; keeps the source aspect when omitted."},
            "height": {"type": "integer", "description": "Output height; keeps the source aspect when omitted."}},
            required=("prompt", "image")),
    }),
    "turbo_mlx_generate_video": (tool_generate_video, {
        "description": "Generate a short video clip with sound (LTX-2) from a text prompt, or animate a still image "
                       "(image-to-video: pass `image`, it becomes the first frame). Local, no cost, but slow: "
                       "~30 s for 1 s at 512 px, several minutes for 5 s at 768 px. Use wait=false for long clips "
                       "and poll turbo_mlx_status.",
        "inputSchema": _schema({
            "image": {"type": "string", "description": "Optional start frame for image-to-video."},
            "seconds": {"type": "number", "description": "Clip length (default 5). Ignored when frames is set."},
            "frames": {"type": "integer", "description": "Exact frame count (rounded to 8k+1)."},
            "fps": {"type": "integer", "description": "Frames per second (default 24)."},
            "width": {"type": "integer", "description": "Multiple of 32 (default 768). Vertical: 512x896."},
            "height": {"type": "integer", "description": "Multiple of 32 (default 512)."},
            "quality": {"type": "boolean", "description": "Full two-stage pipeline: better, much slower."}}),
    }),
    "turbo_mlx_status": (tool_status, {
        "description": "Turbo MLX status. No arguments: engine state, installed models and recent jobs. With `id`: "
                       "that job's status/phase/progress and its result when done (optionally wait up to wait_s). "
                       "With `cancel`: cancel that job.",
        "inputSchema": {"type": "object", "properties": {
            "id": {"type": "string", "description": "Job id returned by a generate/edit call."},
            "wait_s": {"type": "number", "description": "Wait up to this many seconds for the job to finish."},
            "cancel": {"type": "string", "description": "Job id to cancel."},
            "preview": {"type": "boolean", "description": "Attach a preview when the job is done (default true)."}}},
    }),
}


# ---------------------------------------------------------------------------------------------------- MCP / JSON-RPC

_write_lock = threading.Lock()


def send(msg: dict):
    with _write_lock:
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


def handle_call(rid, params):
    name, args = params.get("name"), params.get("arguments") or {}
    try:
        if name not in TOOLS:
            raise ToolError(f"unknown tool {name}")
        content = TOOLS[name][0](args)
        send({"jsonrpc": "2.0", "id": rid, "result": {"content": content, "isError": False}})
    except ToolError as e:
        send({"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": str(e)}], "isError": True}})
    except Exception as e:  # never kill the server on a tool bug
        log("tool crash:", repr(e))
        send({"jsonrpc": "2.0", "id": rid,
              "result": {"content": [{"type": "text", "text": f"internal error: {e!r}"}], "isError": True}})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        method, rid = msg.get("method"), msg.get("id")
        if method == "initialize":
            want = (msg.get("params") or {}).get("protocolVersion")
            send({"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "turbo-mlx", "version": "0.1.0"},
                "instructions": "Local, free image/video generation with Turbo MLX on this Mac. Generations run one "
                                "at a time; videos are slow, so prefer wait=false + turbo_mlx_status for clips."}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": rid,
                  "result": {"tools": [{"name": n, **spec} for n, (_, spec) in TOOLS.items()]}})
        elif method == "tools/call":
            threading.Thread(target=handle_call, args=(rid, msg.get("params") or {}), daemon=True).start()
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": rid, "result": {}})
        elif rid is not None:
            send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}})
        # notifications (initialized, cancelled, ...) need no answer
    ENGINE.shutdown()


if __name__ == "__main__":
    main()
