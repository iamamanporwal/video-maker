"""Vertical launch film (9:16): film.yaml -> clips, ElevenLabs VO + SFX, optional ElevenLabs Music (fal) -> Remotion
LaunchFilm -> mastered mp4.

    python -m reelforge.launch build projects/launch/one-sketch-away [--stills 0,90,600] [--no-render] [--music]

Shots play back to back; `dur` is in seconds. VO, titles, counters and SFX are placed at absolute seconds.
Music is the only paid call: it runs only with --music and is cached in audio/music.mp3 afterwards.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from . import shorts
from .ops import media
from .shorts import ELEVEN, REMOTION, ReelError, _log_cost, _post, _run, place, proxy, tts

ROOT = Path(__file__).resolve().parents[2]
BRAND = {"accent": "#D4F77C", "ink": "#0B0B0C", "text": "#E2E6DA", "paper": "#EFEAE0"}
MUSIC_USD_PER_MIN = 0.8   # estimate logged to costs.jsonl; fal bills per generated second


def sfx(d: Path, pub: Path, name: str, prompt: str, secs: float) -> str:
    """One ElevenLabs sound effect, generated once per project and reused by every re-render."""
    f = d / "audio" / "sfx" / f"{name}.mp3"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(_post(f"{ELEVEN}/sound-generation", {"text": prompt, "duration_seconds": secs, "prompt_influence": 0.7}).content)
        _log_cost(d, provider="elevenlabs", what="sfx", name=name)
    dst = pub / "sfx" / f.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, dst)
    return dst.relative_to(pub).as_posix()


def music(d: Path, pub: Path, spec: dict, generate: bool) -> str | None:
    """A licensed track (`source:`, e.g. copyright-free music downloaded from YouTube) or, only with --music, a paid
    ElevenLabs Music generation. Either way `edit:` re-cuts it to the film."""
    f = d / spec["source"] if spec.get("source") else d / "audio" / "music.mp3"
    if spec.get("source") and not f.exists():
        raise ReelError(f"music source missing: {f}")
    if not f.exists():
        if not generate:
            return None
        from .ops.providers import Fal, _find_url
        plan = spec["plan"]
        secs = sum(s["duration_ms"] for s in plan["sections"]) / 1000
        res = Fal().run("fal-ai/elevenlabs/music", {"composition_plan": plan, "respect_sections_durations": True})
        url = _find_url(res)
        if not url:
            raise ReelError(f"no audio url in fal response: {json.dumps(res)[:300]}")
        f.parent.mkdir(parents=True, exist_ok=True)
        Fal().download(url, f)
        _log_cost(d, provider="fal", what="music", seconds=secs, usd=round(MUSIC_USD_PER_MIN * secs / 60, 3))
    if spec.get("edit"):
        f = recut(f, spec["edit"], d / "audio" / "music-edit.wav")
    dst = pub / "audio" / f.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, dst)
    return dst.relative_to(pub).as_posix()


def recut(f: Path, edit: list[dict], out: Path) -> Path:
    """Re-arrange the generated track to the edit without a new paid call: each piece is [from, to) of the source,
    placed at `at` seconds with a gain (dB) and short fades, then all pieces are mixed. Hide splices under SFX hits."""
    out.parent.mkdir(parents=True, exist_ok=True)
    parts, labels = [], []
    for i, e in enumerate(edit):
        dur = float(e["to"]) - float(e["from"])
        fi, fo = float(e.get("fade_in", 0.03)), float(e.get("fade_out", 0.08))
        parts.append(f"[0:a]atrim={e['from']}:{e['to']},asetpts=PTS-STARTPTS,volume={e.get('gain', 0)}dB,"
                     f"afade=t=in:d={fi},afade=t=out:st={max(0.0, dur - fo):.3f}:d={fo},"
                     f"adelay={round(float(e['at']) * 1000)}:all=1[p{i}]")
        labels.append(f"[p{i}]")
    graph = ";".join(parts) + f";{''.join(labels)}amix=inputs={len(edit)}:normalize=0:duration=longest[m]"
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(f), "-filter_complex", graph, "-map", "[m]",
          "-ar", "48000", str(out)])
    return out


def build(d: Path, render: bool = True, stills: list[int] | None = None, gen_music: bool = False) -> dict:
    d = d.resolve()
    spec = yaml.safe_load((d / "film.yaml").read_text())
    fps = int(spec.get("fps", 30))
    pub = d / "public"
    pub.mkdir(exist_ok=True)
    fr = lambda s: round(float(s) * fps)  # noqa: E731
    asset = lambda p: place((d / p).resolve(), pub) if p and (d / p).exists() else None  # noqa: E731

    shots, t = [], 0
    for i, s in enumerate(spec["shots"]):
        kind, n = s.get("type", "clip"), max(1, fr(s["dur"]))
        shot: dict[str, Any] = {"type": kind, "from": t, "dur": n, "credit": s.get("credit")}
        if kind == "clip":
            shot |= {"src": proxy((d / s["src"]).resolve(), pub, fps), "startFrom": fr(s["in"]), "speed": s.get("speed", 1),
                     "focus": s.get("focus", 0.5), "focusY": s.get("focus_y", 0.5), "zoom": s.get("zoom"), "gain": s.get("gain", 0)}
        elif kind == "image":
            shot |= {"src": asset(s["src"]), "zoom": s.get("zoom"), "paper": s.get("paper", False)}
        elif kind == "count":
            shot |= {"n": s["n"], "label": s["label"]}
        elif kind == "scan":
            shot |= {"before": asset(s["before"]), "after": asset(s.get("after")), "glb": asset(s.get("glb")),
                     "phase": s.get("phase", "scan"), "label": s.get("label")}
        elif kind in ("models", "line"):
            shot["glbs"] = [g for g in (asset(x) for x in s["glbs"]) if g]
        elif kind == "logo":
            shot |= {"logo": asset(s["logo"]), "line": s["line"], "url": s["url"], "clicks": [fr(c) for c in s.get("clicks", [])]}
        elif kind != "black":
            raise ReelError(f"shot {i}: unknown type {kind!r}")
        if kind in ("image", "scan", "logo") and not (shot.get("src") or shot.get("before") or shot.get("logo")):
            raise ReelError(f"shot {i}: missing image {s.get('src') or s.get('before') or s.get('logo')}")
        shots.append({k: v for k, v in shot.items() if v is not None})
        t += n
    total = t

    voice = {**shorts.DEFAULTS["voice"], **(spec.get("voice") or {})}
    say = {**shorts.DEFAULTS["say"], **(spec.get("say") or {})}
    vo, end = [], -1
    for i, ln in enumerate(spec.get("vo") or []):
        f0 = max(fr(ln["at"]), end + 2)
        path, words, dur = tts(d, pub, voice, ln["text"], say)
        end = f0 + fr(dur)
        if end > total:
            raise ReelError(f"vo line {i} ends at {end / fps:.2f}s but the film is {total / fps:.2f}s")
        vo.append({"src": path, "from": f0, "words": [[f0 + fr(a), f0 + fr(b), w] for a, b, w in words],
                   "accent": ln.get("accent"), "y": ln.get("y"), "hide": ln.get("hide")})

    lib = spec.get("sfx_library") or {}
    cues = []
    for c in spec.get("sfx") or []:
        prompt, secs = lib[c["name"]]
        cues.append({"src": sfx(d, pub, c["name"], prompt, secs), "from": fr(c["at"]), "volume": c.get("volume", 0.8)})

    m = spec.get("music") or {}
    msrc = music(d, pub, m, gen_music) if m else None
    props = {
        "fps": fps, "durationInFrames": total, "brand": {**BRAND, **(spec.get("brand") or {})}, "shots": shots, "vo": vo,
        "titles": [{"from": fr(x["from"]), "to": fr(x["to"]), "text": x["text"], "y": x.get("y"), "size": x.get("size")}
                   for x in spec.get("titles") or []],
        "counters": [{"from": fr(x["from"]), "to": fr(x["to"]), "label": x["label"], "a": x["a"], "b": x["b"]}
                     for x in spec.get("counters") or []],
        "sfx": cues,
        "music": {"src": msrc, "volume": m.get("volume", 0.55), "duck": m.get("duck", 0.45)} if msrc else None,
    }
    out = d / "out"
    out.mkdir(exist_ok=True)
    (out / "props.json").write_text(json.dumps(props, indent=1))
    title = spec.get("title") or d.name
    report: dict[str, Any] = {"title": title, "seconds": round(total / fps, 2), "shots": len(shots), "vo_lines": len(vo),
                              "music": bool(msrc), "pending": [i for i, s in enumerate(shots) if s["type"] == "scan" and s.get("phase") == "model"
                                                               and not (s.get("glb") or s.get("after"))]}
    base = ["npx", "remotion"]
    common = ["--props", str(out / "props.json"), "--public-dir", str(pub), "--gl", "angle"]
    if stills:
        sd = out / "stills"
        sd.mkdir(exist_ok=True)
        for f in stills:
            _run(base + ["still", "src/launch/index.ts", "LaunchFilm", str(sd / f"f{f:05d}.png"), "--frame", str(f)] + common, cwd=REMOTION)
        report["stills"] = str(sd)
    if render:
        raw = out / f"{title}.raw.mp4"
        _run(base + ["render", "src/launch/index.ts", "LaunchFilm", str(raw), "--codec", "h264", "--crf", "16",
                     "--pixel-format", "yuv420p", "--image-format", "jpeg", "--jpeg-quality", "95", "--concurrency", "4"] + common, cwd=REMOTION)
        final = out / f"{title}-9x16.mp4"
        report["master"] = media.master(raw, final)
        raw.unlink(missing_ok=True)
        media.still_at(final, 0.15, out / "poster.jpg")
        media.contact_sheet(final, out / "contact.jpg", fps=2.0, cols=10, cell_w=160, title=title)
        report |= {"file": str(final), "loudness": media.loudness(final)}
    return report


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(prog="reelforge.launch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="render a launch film folder (film.yaml)")
    b.add_argument("dir", type=Path)
    b.add_argument("--stills", help="comma-separated frames to render as PNGs (fast layout check)")
    b.add_argument("--no-render", action="store_true")
    b.add_argument("--music", action="store_true", help="generate the music if audio/music.mp3 is missing (paid, fal)")
    a = ap.parse_args(argv)
    try:
        stills = [int(x) for x in a.stills.split(",")] if a.stills else None
        print(json.dumps(build(a.dir, render=not a.no_render, stills=stills, gen_music=a.music), indent=1, default=str))
    except ReelError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
