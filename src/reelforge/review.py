"""S9: evidence packs (all Python), the rubric, score merging and the scoreboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .grid import timecode
from .ops import media
from .project import Project
from .schemas import DIMENSIONS, Review

RUBRIC = {
    "hook": "Does the first 1.5-3 s stop the scroll? Is there a question or tension immediately?",
    "story": "Clear setup -> problem -> product -> twist -> payoff; a character you care about; humour lands.",
    "product_clarity": "Can a stranger say what the product does after one watch? Real UI, legible, focused crops.",
    "before_after": "Is the transformation dramatic and readable at a 320 px thumbnail?",
    "motion": "Eased, purposeful motion; no linear UI moves; no glyph slicing; no jank or stalls in time remaps.",
    "visual_design": "Brand colours/typography respected; accent used sparingly; composition and hierarchy.",
    "finale_3d": "Is the 3D finale cinematic: lighting, materials, camera language, thrusters, no artefacts?",
    "pacing_sync": "Cuts on the beat grid; drops land on major events; no dead air; silence used deliberately.",
    "format_adaptation": "9:16 and 4:5 are re-composed (not crops); safe zones respected; text never under UI.",
    "tech_honesty": "Spec-exact masters; no dark-frame dips; honest real-time labels; no fake UI; no trademarks.",
}

HARD_RULES_REVIEW = [
    "Every score must cite at least one timecode and format.",
    "Never invented UI or retouched product outputs; generated footage must be labelled.",
    "Trademarks in rules.trademark_avoid must not be legible anywhere.",
    "Masters must pass the spec table (duration, codec, -14 LUFS, true peak, zero decode errors, no dark dips).",
    "A 10 needs every dimension >= 9.5 and no medium/high issues.",
    "Contact sheets are tiled: before claiming a clipped headline or black frame, say which full-res still shows it.",
]


def iteration_dir(p: Project, it: int) -> Path:
    d = p.path("review", f"it{it:02d}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def scene_boundaries(p: Project, cut: str) -> list[int]:
    ct = p.timeline.cut(cut)
    return [s.from_ for s in ct.scenes[1:]]


def screenshot_frames(p: Project, cut: str) -> list[int]:
    ct = p.timeline.cut(cut)
    tr = p.read_json("research/treatment.json", {}) or {}
    marks = [s.from_ + s.duration // 2 for s in ct.scenes]
    for sf in tr.get("screenshot_frames_at", []):
        if isinstance(sf, (int, float)):
            marks.append(int(sf * ct.fps))
    return sorted(set(m for m in marks if 0 <= m < ct.durationInFrames))


def evidence_pack(p: Project, it: int, masters: Optional[list[Path]] = None, strips: bool = True) -> dict:
    """Contact sheets (2 fps, timecodes), 10 fps transition strips, full-res stills, waveform, loudness,
    dark-frame list and 320 px thumbnail tests, for every master."""
    d = iteration_dir(p, it)
    masters = masters or sorted(p.path("render/out").glob("*.mp4"))
    index: dict = {"iteration": it, "masters": {}}
    for m in masters:
        name = m.stem
        cut, _, fmt = name.rpartition("-")
        e: dict = {"file": str(m.relative_to(p.root))}
        e["sheet"] = str(media.contact_sheet(m, d / f"{name}.sheet.jpg", fps=2, cols=8, cell_w=240,
                                             title=f"{name} @2fps").relative_to(p.root))
        e["waveform"] = str(media.waveform(m, d / f"{name}.wave.png").relative_to(p.root))
        e["loudness"] = media.loudness(m)
        dark = media.scan_dark_frames(m)
        e["dark_frames"] = [timecode(f) for f in dark["dark"][:50]]
        e["dips"] = [timecode(f) for f in dark["dips"]]
        stills = []
        try:
            for f in screenshot_frames(p, cut):
                out = media.still_at(m, f / 30 + 0.001, d / "stills" / f"{name}_{f:05d}.jpg")
                stills.append({"frame": f, "tc": timecode(f), "file": str(out.relative_to(p.root))})
        except KeyError:
            pass
        e["stills"] = stills
        if strips:
            e["strips"] = []
            try:
                for b in scene_boundaries(p, cut)[:16]:
                    s0, s1 = max(0, b / 30 - 0.5), b / 30 + 0.5
                    out = media.strip(m, d / "strips" / f"{name}_{b:05d}.jpg", s0, s1, fps=10, cell_w=200)
                    e["strips"].append({"boundary": timecode(b), "file": str(out.relative_to(p.root))})
            except KeyError:
                pass
        index["masters"][name] = e
    for poster in sorted(p.path("render/out").glob("Poster-*.png")):
        index.setdefault("thumb_tests", []).append(
            str(media.thumbnail(poster, d / "thumbs" / f"{poster.stem}.320.jpg").relative_to(p.root)))
    spec = p.path("render/out/spec-table.md")
    if spec.exists():
        index["spec_table"] = spec.read_text()
    (d / "evidence.json").write_text(json.dumps(index, indent=2))
    return index


def evidence_images(p: Project, index: dict, max_images: int = 18) -> list[Path]:
    """The images a vision reviewer sees: sheets first, then stills, then strips."""
    imgs: list[Path] = []
    for e in index["masters"].values():
        imgs.append(p.root / e["sheet"])
    for e in index["masters"].values():
        imgs += [p.root / s["file"] for s in e["stills"][:4]]
    for e in index["masters"].values():
        imgs += [p.root / s["file"] for s in e.get("strips", [])[:2]]
    imgs += [p.root / t for t in index.get("thumb_tests", [])]
    return imgs[:max_images]


def merge(self_review: Review, fresh: Optional[Review]) -> dict:
    """If self and fresh differ by more than 1 on a dimension, the lower one counts; otherwise average."""
    a = {s.dimension: s.score for s in self_review.scores}
    b = {s.dimension: s.score for s in fresh.scores} if fresh else {}
    merged = {}
    for dim, _w in DIMENSIONS:
        x, y = a.get(dim), b.get(dim)
        if x is None and y is None:
            continue
        if x is None or y is None:
            merged[dim] = x if y is None else y
        elif abs(x - y) > 1:
            merged[dim] = min(x, y)
        else:
            merged[dim] = round((x + y) / 2, 2)
    total = sum(merged.get(d, 0) * w for d, w in DIMENSIONS) / sum(w for d, w in DIMENSIONS if d in merged) if merged else 0
    issues = list((fresh.issues if fresh else [])) + [i for i in self_review.issues]
    blocking = [i for i in issues if i.severity in ("medium", "high")]
    if total >= 9.95 and (blocking or any(v < 9.5 for v in merged.values())):
        total = 9.4
    return {"dimensions": merged, "total": round(total, 2), "issues": [i.model_dump() for i in issues],
            "blocking": len(blocking)}


def stuck_dimensions(p: Project, window: int = 2) -> list[str]:
    """Dimensions that haven't improved for `window` iterations -> change approach, not parameters."""
    hist = scoreboard_rows(p)
    if len(hist) <= window:
        return []
    stuck = []
    for dim, _ in DIMENSIONS:
        vals = [h["dimensions"].get(dim) for h in hist[-(window + 1):]]
        if None not in vals and max(vals[1:]) <= vals[0]:
            stuck.append(dim)
    return stuck


def scoreboard_rows(p: Project) -> list[dict]:
    rows = []
    for f in sorted(p.path("review").glob("it*/scores.json")):
        rows.append(json.loads(f.read_text()))
    return rows


def write_scoreboard(p: Project) -> Path:
    rows = scoreboard_rows(p)
    dims = [d for d, _ in DIMENSIONS]
    lines = ["# Scoreboard", "", "| it | total | " + " | ".join(dims) + " | decision |", "|---" * (len(dims) + 3) + "|"]
    for r in rows:
        lines.append(f"| {r['iteration']:02d} | **{r['total']:.2f}** | "
                     + " | ".join(f"{r['dimensions'].get(d, '-')}" for d in dims) + f" | {r.get('decision', '')} |")
    f = p.path("review", "SCOREBOARD.md")
    f.write_text("\n".join(lines) + "\n")
    return f
