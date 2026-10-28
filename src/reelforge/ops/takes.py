"""S6: variable-rate screencasts -> indexable takes, and a local HTTP server for frames and assets.

Frames are served over HTTP rather than copied into Remotion's public/ folder (they can be gigabytes).
"""

from __future__ import annotations

import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..project import Project
from .env import free_port


def make_take(take_dir: Path) -> dict:
    frames = json.loads((take_dir / "frames.json").read_text())
    events = json.loads((take_dir / "events.json").read_text()) if (take_dir / "events.json").exists() else []
    mouse = json.loads((take_dir / "mouse.json").read_text()) if (take_dir / "mouse.json").exists() else []
    info = json.loads((take_dir / "take.json").read_text()) if (take_dir / "take.json").exists() else {}
    start = next((e["t"] for e in events if e["name"] == "recordStart"), 0)
    rebase = lambda t: round((t - start) / 1000, 4)
    frames = sorted(frames, key=lambda f: f["t"])
    return {
        "take": take_dir.name,
        "dir": f"capture/{take_dir.name}/frames",
        "page": info.get("viewport", {"width": 1920, "height": 1080}),
        "dpr": info.get("dpr", 2),
        "t": [rebase(f["t"]) for f in frames],
        "f": [f["file"] for f in frames],
        "events": [{**e, "t": rebase(e["t"])} for e in events],
        "mouse": [[rebase(m["t"]), round(m["x"], 1), round(m["y"], 1), 1 if m["down"] else 0] for m in mouse],
        "outputs": {f.name: f"capture/{take_dir.name}/{f.name}" for f in take_dir.iterdir()
                    if f.is_file() and f.suffix in (".jpg", ".png", ".glb") and f.name != "job.json"},
        "duration": rebase(frames[-1]["t"]) if frames else 0,
    }


def make_takes(p: Project, takes: list[str] | None = None) -> dict:
    root = p.path("capture")
    dirs = [root / t for t in takes] if takes else [d for d in sorted(root.iterdir())
                                                    if d.is_dir() and (d / "frames.json").exists()]
    out = {d.name: make_take(d) for d in dirs}
    p.write_json("plan/takes.json", out)
    return {k: {"frames": len(v["t"]), "duration": v["duration"], "events": len(v["events"])} for k, v in out.items()}


class _CORSHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "max-age=3600")
        super().end_headers()

    def log_message(self, *args):
        pass


class AssetServer:
    """Serves the project folder on a random free port for the duration of a render."""

    def __init__(self, root: Path):
        self.root = root
        self.port = free_port()
        handler = functools.partial(_CORSHandler, directory=str(root))
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> "AssetServer":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.httpd.shutdown()
