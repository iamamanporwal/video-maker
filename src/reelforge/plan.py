"""beats.json -> timeline.json (deterministic), and JSON-patch application for fix plans."""

from __future__ import annotations

import copy
from typing import Any, Optional

from .grid import Grid
from .schemas import BeatsDoc, Brief, CutTimeline, Scene, Timeline, TimelineOp


def _scene_props(kind: str, beat, prev_props: Optional[dict]) -> dict:
    props = dict(prev_props or {})
    props.update(beat.props or {})
    props.pop("hook_at", None)
    if beat.headline:
        if kind in ("product_shot", "finale_3d"):
            props.setdefault("headlines", [{"text": beat.headline, "at": 6}])
        elif kind in ("end_room", "end_card"):
            props.setdefault("tagline", beat.headline)
        elif kind == "plot_twist":
            props.setdefault("big", {"text": beat.headline, "at": 12})
        elif kind == "cold_open":
            props.setdefault("slam", {"text": beat.headline, "at": max(0, int(beat.dur * 30) - 24)})
        else:
            props.setdefault("headline", beat.headline)
    return props


def beats_to_timeline(doc: BeatsDoc, brief: Brief, brand: dict, previous: Optional[Timeline] = None) -> Timeline:
    """Seconds -> frames on the grid. Props already edited in a previous timeline are preserved per scene id."""
    grid = Grid(bpm=doc.bpm, fps=brief.fps)
    cuts = []
    for cb in doc.cuts:
        cut = next(c for c in brief.cuts if c.name == cb.cut)
        prev_scenes = {}
        if previous:
            try:
                prev_scenes = {s.id: s.props for s in previous.cut(cb.cut).scenes}
            except KeyError:
                pass
        scenes, captions, sfx = [], [], []
        for b in cb.beats:
            f0 = grid.nearest_beat(grid.sec_to_frame(b.start))
            f1 = grid.nearest_beat(grid.sec_to_frame(b.start + b.dur))
            scenes.append(Scene(id=b.id, kind=b.kind, **{"from": f0}, duration=f1 - f0,
                                props=_scene_props(b.kind, b, prev_scenes.get(b.id))))
            if b.caption:
                captions.append((f0 + 3, f1 - 3, b.caption))
            for i, hint in enumerate(b.sfx_hints):
                sfx.append((f0 + i * int(grid.beat_frames), hint, 0.8, 2.0))
        total = grid.sec_to_frame(cut.seconds)
        # Fix rounding so scenes are contiguous and end exactly at the cut length.
        for a, b2 in zip(scenes, scenes[1:]):
            a.duration = b2.from_ - a.from_
        if scenes:
            scenes[-1].duration = total - scenes[-1].from_
        prev_music = []
        if previous:
            try:
                prev_music = previous.cut(cb.cut).music
            except KeyError:
                pass
        cuts.append(CutTimeline(name=cb.cut, fps=brief.fps, durationInFrames=total, formats=cut.formats, bpm=doc.bpm,
                                scenes=scenes, sfx=sfx, captions=captions, music=prev_music))
    return Timeline(project=brief.project, brand=brand, cuts=cuts)


# ------------------------------------------------------------------ JSON pointer patching (fix plans)


def _parts(path: str) -> list[str]:
    if not path.startswith("/"):
        raise ValueError(f"bad pointer {path}")
    return [p.replace("~1", "/").replace("~0", "~") for p in path.split("/")[1:]]


def _resolve_scene_ids(doc: dict, parts: list[str]) -> list[str]:
    """Allow /cuts/hero/scenes/s07/... as well as numeric indices (friendlier for the LLM)."""
    out, node = [], doc
    for p in parts:
        if isinstance(node, list) and not p.isdigit() and p != "-":
            idx = next((i for i, x in enumerate(node) if isinstance(x, dict) and (x.get("id") == p or x.get("name") == p)), None)
            if idx is None:
                raise KeyError(f"no element with id/name '{p}'")
            p = str(idx)
        out.append(p)
        try:
            node = node[int(p)] if isinstance(node, list) else node[p]
        except (KeyError, IndexError, ValueError):
            node = None
    return out


def apply_patch(doc: dict, ops: list[TimelineOp]) -> dict:
    doc = copy.deepcopy(doc)
    for op in ops:
        parts = _resolve_scene_ids(doc, _parts(op.path))
        parent: Any = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent.setdefault(p, {})
        last = parts[-1]
        if isinstance(parent, list):
            if op.op == "add":
                parent.insert(len(parent) if last == "-" else int(last), op.value)
            elif op.op == "replace":
                parent[int(last)] = op.value
            else:
                parent.pop(int(last))
        else:
            if op.op in ("add", "replace"):
                parent[last] = op.value
            else:
                parent.pop(last, None)
    return doc


def retime(doc: dict, cut: str) -> dict:
    """After a patch changes durations, make scenes contiguous again (from = previous end)."""
    for ct in doc["cuts"]:
        if ct["name"] != cut:
            continue
        f = 0
        for s in ct["scenes"]:
            s["from"] = f
            f += s["duration"]
    return doc
