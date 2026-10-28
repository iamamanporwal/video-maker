"""Project folder, state.json, content hashing, logs, costs and per-stage git commits."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

from .schemas import Asset, Brand, Brief, Timeline

SUBDIRS = (
    "assets", "research", "plan", "capture", "audio/music", "audio/sfx", "video_gen",
    "render/out", "render/raw", "review", "logs",
)

STAGES = ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10")


class BudgetExceeded(RuntimeError):
    pass


def sha(data: Any) -> str:
    if isinstance(data, (bytes, bytearray)):
        b = bytes(data)
    elif isinstance(data, Path):
        b = data.read_bytes() if data.is_file() else str(data).encode()
    else:
        b = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(b).hexdigest()[:16]


def hash_files(paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(Path(x) for x in paths):
        if p.is_file():
            h.update(str(p.name).encode())
            h.update(p.read_bytes())
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    h.update(str(f.relative_to(p)).encode())
                    h.update(f.stat().st_size.to_bytes(8, "little"))
                    h.update(int(f.stat().st_mtime).to_bytes(8, "little"))
    return h.hexdigest()[:16]


@dataclass
class Project:
    root: Path

    # ------------------------------------------------------------------ construction

    @classmethod
    def open(cls, root: str | Path) -> "Project":
        p = cls(Path(root).resolve())
        if not (p.root / "brief.yaml").exists():
            raise FileNotFoundError(f"{p.root}/brief.yaml not found; run `reelforge init` first")
        return p

    @classmethod
    def create(cls, root: str | Path, brief: Optional[Path] = None, brand: Optional[Path] = None,
               manifest: Optional[Path] = None) -> "Project":
        p = cls(Path(root).resolve())
        p.root.mkdir(parents=True, exist_ok=True)
        for d in SUBDIRS:
            (p.root / d).mkdir(parents=True, exist_ok=True)
        if brief and not (p.root / "brief.yaml").exists():
            (p.root / "brief.yaml").write_text(Path(brief).read_text())
        if brand and not (p.root / "brand.json").exists():
            (p.root / "brand.json").write_text(Path(brand).read_text())
        if manifest and not (p.root / "assets/manifest.yaml").exists():
            (p.root / "assets/manifest.yaml").write_text(Path(manifest).read_text())
        if not (p.root / "assets/manifest.yaml").exists():
            (p.root / "assets/manifest.yaml").write_text("[]\n")
        if not (p.root / ".gitignore").exists():
            (p.root / ".gitignore").write_text("capture/*/frames/\nrender/raw/\n*.glb\n.env\n")
        if not (p.root / "state.json").exists():
            p.save_state({"stages": {}, "iteration": 0, "created": time.time()})
        p.git(["init", "-q"], check=False)
        return p

    # ------------------------------------------------------------------ paths

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    @property
    def name(self) -> str:
        return self.brief.project

    # ------------------------------------------------------------------ inputs

    @property
    def brief(self) -> Brief:
        return Brief.model_validate(yaml.safe_load(self.path("brief.yaml").read_text()))

    @property
    def brand(self) -> Brand:
        f = self.path("brand.json")
        if not f.exists():
            return Brand(colors={"ink": "#0B0B0C", "accent": "#D4F77C", "text": "#E2E6DA",
                                 "muted": ["#8E9686", "#585E54", "#3A3F36"], "accentShadow": "#2E3A12"})
        return Brand.model_validate_json(f.read_text())

    @property
    def assets(self) -> list[Asset]:
        f = self.path("assets/manifest.yaml")
        data = yaml.safe_load(f.read_text()) if f.exists() else []
        return [Asset.model_validate(a) for a in (data or [])]

    def save_assets(self, assets: list[Asset]) -> None:
        self.path("assets/manifest.yaml").write_text(
            yaml.safe_dump([a.model_dump(exclude_none=True) for a in assets], sort_keys=False))

    # ------------------------------------------------------------------ plan data

    def read_json(self, rel: str, default: Any = None) -> Any:
        f = self.path(rel)
        return json.loads(f.read_text()) if f.exists() else default

    def write_json(self, rel: str, data: Any) -> Path:
        f = self.path(rel)
        f.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(data, "model_dump"):
            data = data.model_dump(by_alias=True, mode="json")
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return f

    @property
    def timeline(self) -> Timeline:
        return Timeline.model_validate(self.read_json("plan/timeline.json"))

    # ------------------------------------------------------------------ state + caching

    def state(self) -> dict:
        return self.read_json("state.json", {"stages": {}, "iteration": 0})

    def save_state(self, s: dict) -> None:
        self.write_json("state.json", s)

    def stage_fresh(self, stage: str, input_hash: str) -> bool:
        st = self.state()["stages"].get(stage, {})
        return st.get("status") == "done" and st.get("hash") == input_hash

    def mark(self, stage: str, status: str, input_hash: str = "", **extra: Any) -> None:
        s = self.state()
        s["stages"][stage] = {"status": status, "hash": input_hash, "at": time.time(), **extra}
        self.save_state(s)
        self.log("run", {"stage": stage, "status": status, **extra})

    # ------------------------------------------------------------------ logs + costs

    def log(self, stream: str, record: dict) -> None:
        f = self.path("logs", f"{stream}.jsonl")
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a") as fh:
            fh.write(json.dumps({"t": round(time.time(), 3), **record}, default=str) + "\n")

    def read_log(self, stream: str) -> list[dict]:
        f = self.path("logs", f"{stream}.jsonl")
        if not f.exists():
            return []
        return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]

    def costs(self) -> dict[str, float]:
        tot: dict[str, float] = {}
        for r in self.read_log("costs"):
            tot[r["provider"]] = tot.get(r["provider"], 0.0) + float(r.get("usd", 0) or 0)
            if "credits" in r:
                tot["app_credits"] = tot.get("app_credits", 0.0) + float(r["credits"])
        return {k: round(v, 4) for k, v in tot.items()}

    def add_cost(self, provider: str, usd: float = 0.0, **extra: Any) -> None:
        self.log("costs", {"provider": provider, "usd": usd, **extra})

    def check_budget(self, provider: str, est_usd: float = 0.0, credits: float = 0.0) -> None:
        """Enforced before any paid call."""
        b = self.brief.budgets
        c = self.costs()
        limits = {"fal": b.fal_usd, "llm": b.llm_usd}
        if provider in limits and c.get(provider, 0) + est_usd > limits[provider]:
            raise BudgetExceeded(f"{provider} budget ${limits[provider]} would be exceeded "
                                 f"(spent ${c.get(provider, 0):.2f} + est ${est_usd:.2f})")
        if credits and c.get("app_credits", 0) + credits > b.app_credits:
            raise BudgetExceeded(f"app credit budget {b.app_credits} would be exceeded")

    def append_credit(self, line: str) -> None:
        f = self.path("CREDITS.md")
        existing = f.read_text() if f.exists() else "# Credits and licences\n\n"
        if line not in existing:
            f.write_text(existing + f"- {line}\n")

    # ------------------------------------------------------------------ git

    def git(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=check)

    def commit(self, msg: str) -> None:
        self.git(["add", "-A"], check=False)
        self.git(["-c", "user.name=reelforge", "-c", "user.email=reelforge@localhost",
                  "commit", "-q", "--allow-empty", "-m", msg], check=False)
