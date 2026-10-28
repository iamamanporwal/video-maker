"""Deterministic validators. Failures are returned as human-readable reasons so they can be fed back to the LLM."""

from __future__ import annotations

import re
from typing import Iterable

from .grid import Grid, timecode
from .schemas import SCENE_KINDS, Asset, BeatsDoc, Brief, CutTimeline, Timeline

PLACEHOLDER_KEYS = ("headline", "headlines", "text", "copy", "sub", "tagline", "url", "messages", "prompt", "labels", "slam")


def _words(s: str) -> int:
    return len([w for w in re.split(r"\s+", s.strip()) if w])


def trademark_hits(texts: Iterable[str], terms: list[str]) -> list[str]:
    hits = []
    for t in texts:
        for term in terms:
            if re.search(rf"\b{re.escape(term)}\b", t or "", flags=re.I):
                hits.append(f"trademark '{term}' appears in on-screen text: {t!r}")
    return hits


def onscreen_texts(obj) -> list[str]:
    """All strings reachable in a props tree (conservative: any string could be on screen)."""
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out += onscreen_texts(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out += onscreen_texts(v)
    return out


def validate_beats(doc: BeatsDoc, brief: Brief) -> list[str]:
    errs: list[str] = []
    grid = Grid(bpm=doc.bpm, fps=brief.fps)
    if doc.bpm != brief.music.bpm:
        errs.append(f"bpm {doc.bpm} differs from brief music.bpm {brief.music.bpm}")
    by_name = {c.name: c for c in brief.cuts}
    seen = set()
    for cb in doc.cuts:
        if cb.cut not in by_name:
            errs.append(f"unknown cut '{cb.cut}'; expected one of {list(by_name)}")
            continue
        seen.add(cb.cut)
        cut = by_name[cb.cut]
        total_f = grid.sec_to_frame(cut.seconds)
        cursor = 0
        ids = set()
        for b in cb.beats:
            if b.id in ids:
                errs.append(f"[{cb.cut}] duplicate beat id {b.id}")
            ids.add(b.id)
            sf, df = grid.sec_to_frame(b.start), grid.sec_to_frame(b.dur)
            if df <= 0:
                errs.append(f"[{cb.cut}] beat {b.id} has non-positive duration")
            if abs(sf - cursor) > 1:
                errs.append(f"[{cb.cut}] beat {b.id} starts at {b.start}s but previous ends at "
                            f"{cursor / brief.fps:.3f}s (gaps/overlaps not allowed)")
            if not grid.on_beat(sf):
                errs.append(f"[{cb.cut}] beat {b.id} cut at {b.start}s ({sf}f) is off the beat grid "
                            f"(nearest beat {grid.nearest_beat(sf) / brief.fps:.3f}s; {grid.describe()})")
            if df > 0 and not grid.on_beat(sf + df):
                errs.append(f"[{cb.cut}] beat {b.id} ends at {b.start + b.dur:.3f}s ({sf + df}f), off the beat grid "
                            f"(nearest beat {grid.nearest_beat(sf + df) / brief.fps:.3f}s)")
            if b.headline and _words(b.headline) > brief.rules.max_headline_words:
                errs.append(f"[{cb.cut}] beat {b.id} headline '{b.headline}' has more than "
                            f"{brief.rules.max_headline_words} words")
            errs += [f"[{cb.cut}] beat {b.id}: {h}" for h in
                     trademark_hits([b.headline, b.caption, *onscreen_texts(b.props)], brief.rules.trademark_avoid)]
            cursor = sf + df
        if abs(cursor - total_f) > 1:
            errs.append(f"[{cb.cut}] durations sum to {cursor / brief.fps:.3f}s, expected exactly {cut.seconds}s")
        if cut.hook_seconds is not None and cb.beats:
            first = cb.beats[0]
            hook_at = first.props.get("hook_at")
            if hook_at is None and first.dur > cut.hook_seconds + 1e-6:
                errs.append(f"[{cb.cut}] hook must land within {cut.hook_seconds}s; first beat {first.id} lasts "
                            f"{first.dur}s with no props.hook_at. Shorten it or set props.hook_at (seconds) "
                            f"<= {cut.hook_seconds}")
            elif hook_at is not None and float(hook_at) > cut.hook_seconds:
                errs.append(f"[{cb.cut}] props.hook_at {hook_at} > hook_seconds {cut.hook_seconds}")
    for name in by_name:
        if name not in seen:
            errs.append(f"missing cut '{name}'")
    return errs


def validate_cut_timeline(ct: CutTimeline, brief: Brief) -> list[str]:
    errs: list[str] = []
    cursor = 0
    for s in sorted(ct.scenes, key=lambda s: s.from_):
        if s.kind not in SCENE_KINDS:
            errs.append(f"[{ct.name}] scene {s.id}: unknown kind {s.kind}")
        if s.from_ != cursor:
            errs.append(f"[{ct.name}] scene {s.id} starts at {timecode(s.from_)} but previous ends at {timecode(cursor)}")
        if s.duration <= 0:
            errs.append(f"[{ct.name}] scene {s.id} has duration {s.duration}")
        errs += _monotone_keys(ct.name, s.id, s.props)
        errs += [f"[{ct.name}] scene {s.id}: {h}" for h in trademark_hits(onscreen_texts(s.props), brief.rules.trademark_avoid)]
        cursor = s.from_ + s.duration
    if cursor != ct.durationInFrames:
        errs.append(f"[{ct.name}] scenes end at frame {cursor}, durationInFrames is {ct.durationInFrames}")
    for f, name, vol, dur in ct.sfx:
        if not 0 <= f < ct.durationInFrames:
            errs.append(f"[{ct.name}] sfx '{name}' at frame {f} is outside the cut")
    for a, b, text in ct.captions:
        if b <= a:
            errs.append(f"[{ct.name}] caption '{text}' has empty range")
        errs += trademark_hits([text], brief.rules.trademark_avoid)
    for m in ct.music:
        frames = [k[0] for k in m.volumeKeys]
        if frames != sorted(frames) or len(set(frames)) != len(frames):
            errs.append(f"[{ct.name}] music {m.src} volumeKeys must be strictly increasing")
    return errs


def _monotone_keys(cut: str, sid: str, props: dict) -> list[str]:
    """Interpolate input ranges must be strictly monotonic (a stare: 9999 once crashed the social cut)."""
    errs = []
    for key in ("timeKeys", "focusKeys", "wipeKeys", "kenBurns", "keys"):
        ks = props.get(key)
        if isinstance(ks, list) and ks and isinstance(ks[0], (list, tuple)):
            frames = [k[0] for k in ks]
            if any(b <= a for a, b in zip(frames, frames[1:])):
                errs.append(f"[{cut}] scene {sid}: props.{key} frames are not strictly increasing: {frames}")
    for k, v in props.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) >= 9999:
            errs.append(f"[{cut}] scene {sid}: props.{k}={v} looks like a disabled-beat sentinel; remove the beat instead")
    return errs


def validate_timeline(tl: Timeline, brief: Brief) -> list[str]:
    errs = []
    for ct in tl.cuts:
        errs += validate_cut_timeline(ct, brief)
    return errs


def enforce_asset_rules(asset: Asset, usage: str) -> list[str]:
    """Python enforces the manifest's `never` rules; AI only proposes."""
    if usage in asset.never:
        return [f"asset {asset.file} must never be used for '{usage}'"]
    return []
