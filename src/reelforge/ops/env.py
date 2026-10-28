"""S0: tool checks, ports and secrets."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

REMOTION_PORT = 3700


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "node" / "remotion").is_dir():
            return p
    return Path(os.environ.get("REELFORGE_HOME", Path.cwd()))


def node_dir(name: str) -> Path:
    return repo_root() / "node" / name


def load_env(project_root: Optional[Path] = None) -> None:
    from dotenv import load_dotenv

    for d in filter(None, [project_root, repo_root(), Path.cwd()]):
        f = Path(d) / ".env"
        if f.exists():
            load_dotenv(f, override=False)


def port_free(port: int) -> bool:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ver(cmd: list[str]) -> Optional[str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0] if r.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def chrome_path() -> Optional[str]:
    for p in (os.environ.get("CHROME_PATH"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium")):
        if p and Path(p).exists():
            return p
    return None


def http_status(url: str) -> Optional[int]:
    import httpx

    try:
        return httpx.get(url, timeout=5, follow_redirects=True).status_code
    except Exception:
        return None


def env_check(app_url: Optional[str] = None, need_capture: bool = True) -> dict:
    checks: dict[str, dict] = {}

    def add(name: str, ok: bool, detail: str = "", required: bool = True):
        checks[name] = {"ok": bool(ok), "detail": detail, "required": required}

    add("python", sys.version_info >= (3, 11), sys.version.split()[0])
    for mod in ("PIL", "numpy"):
        try:
            __import__(mod)
            add(mod, True)
        except ImportError:
            add(mod, False, "pip install")
    node = _ver(["node", "--version"])
    add("node", node is not None, node or "missing")
    ff = _ver(["ffmpeg", "-version"])
    add("ffmpeg", ff is not None, (ff or "missing")[:60])
    add("ffprobe", _ver(["ffprobe", "-version"]) is not None)
    add("remotion_deps", (node_dir("remotion") / "node_modules" / "remotion").exists(),
        "run `reelforge setup`" if not (node_dir("remotion") / "node_modules").exists() else "")
    add("playwright_deps", (node_dir("capture") / "node_modules" / "playwright").exists(), "", required=need_capture)
    add("chrome", chrome_path() is not None, chrome_path() or "set CHROME_PATH", required=need_capture)
    add(f"port_{REMOTION_PORT}", port_free(REMOTION_PORT),
        "pinned Remotion port is in use (another dev server?)" if not port_free(REMOTION_PORT) else "")
    if not port_free(3000):
        add("port_3000", True, "3000 is taken (that's why Remotion is pinned to 3700)", required=False)
    if app_url:
        st = http_status(app_url)
        add("app_url", st == 200, f"{app_url} -> {st}", required=need_capture)
    for key, req in (("ANTHROPIC_API_KEY", False), ("FAL_KEY", False), ("ELEVENLABS_API_KEY", False)):
        add(key, bool(os.environ.get(key)), "set in .env" if not os.environ.get(key) else "set", required=req)
    ok = all(c["ok"] for c in checks.values() if c["required"])
    return {"ok": ok, "checks": checks}
