"""Vertical shorts (9:16) for the Vi3W channel: reel.yaml -> ElevenLabs voiceover -> Remotion GameReel -> mastered mp4.

    python -m reelforge.shorts build projects/shorts/doodle-derby [--stills 0,60,120]
    python -m reelforge.shorts sheet Input/clip.mov out.jpg [--fps 1]
    python -m reelforge.shorts frame Input/clip.mov 12.4 subject.png [--crop x,y,w,h]
    python -m reelforge.shorts find "monster truck game" [--max-sec 90 --top 10]
    python -m reelforge.shorts fetch <url> projects/shorts/x/ref/source.mp4 [--to 8]

Python does the operations; the skills (.claude/skills/game-reel, hook-to-3d) decide what goes in reel.yaml.
No music is baked in: trending audio is added in the Instagram / YouTube app so it stays licensed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

from .ops import media

ROOT = Path(__file__).resolve().parents[2]
REMOTION = ROOT / "node" / "remotion"
SHARED_SFX = ROOT / "assets" / "shorts-sfx"
ELEVEN = "https://api.elevenlabs.io/v1"

DEFAULTS: dict[str, Any] = {
    "fps": 30,
    "brand": {"accent": "#7CFF6B", "ink": "#07080C", "text": "#FFFFFF"},
    # "Laura": young, enthusiastic social-media voice. eleven_v3 reads audio tags like [excited] [gasps] [laughs];
    # stability 0.0 is v3's most expressive ("Creative") setting. Override per reel with voice.id / voice.model.
    "voice": {"id": "FGY2WhTYpPnrIDTdsKH5", "model": "eleven_v3", "stability": 0.0},
    # Spoken form of words TTS gets wrong. Captions still show the written form.
    "say": {"Vi3W": "View", "Vi3W.in": "view dot in"},
    "sfx": True,
}
SFX_PROMPTS = {
    "whoosh": ("fast airy whoosh transition, short, clean, no music", 0.8),
    "pop": ("bright satisfying UI pop with a soft sparkle, short", 0.6),
}
RIGHTS = {"own", "permission", "remix", "recreate"}


class ReelError(Exception):
    pass


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise ReelError(f"{' '.join(cmd[:3])}… failed:\n{(r.stderr or r.stdout)[-2000:]}")
    return r.stdout


def _key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise ReelError("ELEVENLABS_API_KEY is not set (.env)")
    return key


def _post(url: str, body: dict) -> httpx.Response:
    for attempt in range(5):
        r = httpx.post(url, headers={"xi-api-key": _key()}, json=body, timeout=180)
        if r.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        if r.status_code >= 400:
            raise ReelError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
        return r
    raise ReelError("ElevenLabs: still rate-limited")


def _log_cost(d: Path, **kw: Any) -> None:
    with open(d / "costs.jsonl", "a") as fh:
        fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **kw}) + "\n")


# --------------------------------------------------------------------------- media prep


def proxy(src: Path, pub: Path, fps: int) -> str:
    """Conform any capture (120 fps Retina .mov, trailer mp4) to a 30 fps 1920-wide H.264 proxy in public/clips."""
    if not src.exists():
        raise ReelError(f"missing clip: {src}")
    slug = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-")
    dst = pub / "clips" / f"{slug}-{hashlib.sha1(str(src).encode()).hexdigest()[:6]}.mp4"
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        dst.parent.mkdir(parents=True, exist_ok=True)
        has_audio = any(s.get("codec_type") == "audio" for s in media.probe(src).get("streams", []))
        cmd = ["ffmpeg", "-y", "-hide_banner", "-i", str(src), "-vf", f"fps={fps},scale=1920:-2:flags=lanczos",
               "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"] if has_audio else ["-an"]
        _run(cmd + ["-movflags", "+faststart", str(dst)])
    return dst.relative_to(pub).as_posix()


def place(src: Path, pub: Path) -> str:
    """Copy an image / video / GLB into public/assets (videos are proxied)."""
    if not src.exists():
        raise ReelError(f"missing asset: {src}")
    if src.suffix.lower() in {".mov", ".mp4", ".webm", ".m4v"}:
        return proxy(src, pub, 30)
    dst = pub / "assets" / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        shutil.copy2(src, dst)
    return dst.relative_to(pub).as_posix()


def ensure_sfx(pub: Path) -> dict[str, str]:
    """Shared whoosh/pop, generated once with ElevenLabs sound-generation and reused by every reel."""
    SHARED_SFX.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, (prompt, secs) in SFX_PROMPTS.items():
        f = SHARED_SFX / f"{name}.mp3"
        if not f.exists():
            r = _post(f"{ELEVEN}/sound-generation", {"text": prompt, "duration_seconds": secs, "prompt_influence": 0.6})
            f.write_bytes(r.content)
        dst = pub / "sfx" / f.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        out[name] = dst.relative_to(pub).as_posix()
    return out


# --------------------------------------------------------------------------- voiceover


def _words(al: dict) -> list[tuple[float, float, str]]:
    """ElevenLabs character alignment -> [(start_s, end_s, word)]."""
    out, cur, t0, t1 = [], "", 0.0, 0.0
    for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if cur:
                out.append((t0, t1, cur))
            cur = ""
            continue
        if not cur:
            t0 = a
        cur, t1 = cur + ch, b
    if cur:
        out.append((t0, t1, cur))
    return out


TAG = re.compile(r"(\[[^\]]+\])")
EDGE = re.compile(r"^([^\w]*)(.*?)([.,!?…:;'\")]*)$")


def speak(text: str, say: dict[str, str]) -> tuple[str, list[tuple[str | None, int]]]:
    """Caption text -> (text sent to TTS, plan). Each plan item is (caption word or None for an audio tag,
    number of spoken words it covers), so "Vi3W.in" can be said as "view dot in" and still caption as one word."""
    spoken, plan = [], []
    for part in TAG.split(text):
        if TAG.fullmatch(part):
            spoken.append(part)
            plan.append((None, len(part.split())))
            continue
        for tok in part.split():
            lead, core, trail = EDGE.match(tok).groups()
            sub = next((v for k, v in say.items() if k.lower() == core.lower()), core)
            spoken.append(f"{lead}{sub}{trail}")
            plan.append((tok, len(sub.split()) or 1))
    return " ".join(spoken), plan


def caption_words(words: list, plan: list) -> list:
    """Map spoken-word timings back onto caption words; drop audio tags."""
    if len(words) != sum(n for _, n in plan):
        return [w for w in words if not TAG.fullmatch(w[2])]
    out, i = [], 0
    for cap, n in plan:
        if cap is not None:
            out.append((words[i][0], words[i + n - 1][1], cap))
        i += n
    return out


def tts(d: Path, pub: Path, voice: dict, text: str, say: dict, prev: str = "", nxt: str = "") -> tuple[str, list, float]:
    """One VO line, cached by (voice, text, context). Returns (public path, caption word timings in s, duration s)."""
    spoken, plan = speak(text, say)
    v3 = voice["model"].startswith("eleven_v3")
    if v3:
        prev = nxt = ""  # v3 takes no request stitching
    h = hashlib.sha1(json.dumps([voice, spoken, prev, nxt], sort_keys=True).encode()).hexdigest()[:12]
    mp3, meta = pub / "vo" / f"{h}.mp3", pub / "vo" / f"{h}.json"
    if not (mp3.exists() and meta.exists()):
        mp3.parent.mkdir(parents=True, exist_ok=True)
        keys = ("stability",) if v3 else ("stability", "similarity_boost", "style")
        body = {"text": spoken, "model_id": voice["model"],
                "voice_settings": {k: voice[k] for k in keys if k in voice} | ({} if v3 else {"use_speaker_boost": True})}
        if not v3:
            body |= {"previous_text": prev or None, "next_text": nxt or None}
        r = _post(f"{ELEVEN}/text-to-speech/{voice['id']}/with-timestamps?output_format=mp3_44100_128", body).json()
        mp3.write_bytes(base64.b64decode(r["audio_base64"]))
        al = r.get("normalized_alignment") or r["alignment"]
        meta.write_text(json.dumps({"text": text, "spoken": spoken, "words": caption_words(_words(al), plan)}))
        _log_cost(d, provider="elevenlabs", what="tts", chars=len(spoken))
    words = json.loads(meta.read_text())["words"]
    dur = float(media.probe(mp3)["format"]["duration"])
    return mp3.relative_to(pub).as_posix(), words, dur


# --------------------------------------------------------------------------- build


def load(d: Path) -> dict:
    f = d / "reel.yaml"
    if not f.exists():
        raise ReelError(f"{f} not found")
    spec = yaml.safe_load(f.read_text()) or {}
    for k, v in DEFAULTS.items():
        spec[k] = {**v, **(spec.get(k) or {})} if isinstance(v, dict) else spec.get(k, v)
    return spec


def check_rights(spec: dict, d: Path) -> str:
    """Third-party footage ("source" segments) needs a recorded right to use it. Returns the rights mode."""
    has_source = any(s.get("type") == "source" for s in spec.get("segments", []))
    src = spec.get("source") or {}
    mode = src.get("rights")
    if not has_source:
        return mode or "own"
    if mode not in RIGHTS:
        raise ReelError(f"source.rights must be one of {sorted(RIGHTS)} when the reel has source segments")
    if mode == "permission":
        proof = src.get("proof")
        if not src.get("creator") or not proof or not (d / proof).exists():
            raise ReelError("rights: permission needs source.creator and source.proof (a file, e.g. a screenshot of the creator's yes)")
    return mode


def build(d: Path, render: bool = True, stills: list[int] | None = None) -> dict:
    d = d.resolve()
    spec = load(d)
    fps = int(spec["fps"])
    pub = d / "public"
    pub.mkdir(exist_ok=True)
    mode = check_rights(spec, d)
    title = spec.get("title") or d.name

    # Segments -> frames. In remix mode the platform supplies the source clip, so we drop it.
    segs, ids, t = [], {}, 0
    for i, s in enumerate(spec.get("segments") or []):
        kind = s.get("type", "clip")
        if kind == "source" and mode == "remix":
            continue
        if kind in ("clip", "source"):
            speed = float(s.get("speed", 1))
            secs = (float(s["out"]) - float(s["in"])) / speed
            seg = {"type": kind, "src": proxy((d / s["src"]).resolve(), pub, fps), "startFrom": round(float(s["in"]) * fps),
                   "speed": speed, "fit": s.get("fit", "frame"), "focus": s.get("focus", 0.5), "zoom": s.get("zoom", 1),
                   "gain": s.get("gain", 0), "label": s.get("label")}
        elif kind == "reveal":
            secs = float(s.get("seconds", 4.5))
            if not (s.get("after") or s.get("glb")):
                raise ReelError(f"segment {i}: reveal needs a real Vi3W output (after: video or glb:)")
            seg = {"type": "reveal", "before": place(d / s["before"], pub), "beforeLabel": s.get("before_label"),
                   "label": s.get("label"), "timer": s.get("timer")}
            for k in ("after", "glb"):
                if s.get(k):
                    seg[k] = place(d / s[k], pub)
        elif kind == "cta":
            secs = float(s.get("seconds", 2.5))
            seg = {"type": "cta", "line": s.get("line"), "button": s.get("button")}
            for k in ("after", "glb", "logo", "backdrop"):
                if s.get(k):
                    seg[k] = place(d / s[k], pub)
        else:
            raise ReelError(f"segment {i}: unknown type {kind!r}")
        n = max(1, round(secs * fps))
        seg.update({"from": t, "dur": n})
        ids[s.get("id", f"s{i}")] = t
        segs.append({k: v for k, v in seg.items() if v is not None})
        t += n
    if not segs:
        raise ReelError("reel.yaml has no segments")
    total = t

    # Voiceover: each line placed at seconds or at a segment id (+ offset); no overlaps, must end before the reel.
    lines, vo, end = spec.get("vo") or [], [], -1
    for i, ln in enumerate(lines):
        at = ln.get("at", 0)
        if isinstance(at, str):
            if at not in ids:
                if mode == "remix":
                    continue  # line belonged to the dropped source hook
                raise ReelError(f"vo line {i}: unknown segment id {at!r}")
            f0 = ids[at] + round(float(ln.get("offset", 0)) * fps)
        else:
            f0 = round(float(at) * fps)
        f0 = max(f0, end + 2)
        prev = lines[i - 1]["text"] if i else ""
        nxt = lines[i + 1]["text"] if i + 1 < len(lines) else ""
        path, words, dur = tts(d, pub, spec["voice"], ln["text"], spec["say"], prev, nxt)
        end = f0 + round(dur * fps)
        if end > total:
            raise ReelError(f"vo line {i} ends at {end / fps:.2f}s but the reel is {total / fps:.2f}s: "
                            f"shorten the line or lengthen a segment")
        vo.append({"src": path, "from": f0, "words": [[f0 + round(a * fps), f0 + round(b * fps), w] for a, b, w in words]})

    hook = spec.get("hook")
    props = {
        "fps": fps, "durationInFrames": total, "brand": spec["brand"], "segments": segs, "vo": vo,
        "hook": {"text": hook["text"], "until": round(float(hook.get("seconds", 2.5)) * fps)} if hook and mode != "remix" else None,
        "credit": spec.get("credit"),
        "sfx": ensure_sfx(pub) if spec.get("sfx") else None,
    }
    props = {k: v for k, v in props.items() if v is not None}
    out = d / "out"
    out.mkdir(exist_ok=True)
    (out / "props.json").write_text(json.dumps(props, indent=1))
    name = f"{title}-remix" if mode == "remix" else title
    report = {"title": name, "seconds": round(total / fps, 2), "segments": len(segs), "vo_lines": len(vo), "rights": mode}

    base = ["npx", "remotion"]
    common = ["--props", str(out / "props.json"), "--public-dir", str(pub)]
    if stills:
        sd = out / "stills"
        sd.mkdir(exist_ok=True)
        for f in stills:
            _run(base + ["still", "src/shorts/index.ts", "GameReel", str(sd / f"f{f:05d}.png"), "--frame", str(f)] + common, cwd=REMOTION)
        report["stills"] = str(sd)
    if render:
        raw = out / f"{name}.raw.mp4"
        _run(base + ["render", "src/shorts/index.ts", "GameReel", str(raw), "--codec", "h264", "--crf", "16",
                     "--pixel-format", "yuv420p", "--image-format", "png"] + common, cwd=REMOTION)
        final = out / f"{name}-9x16.mp4"
        report["master"] = media.master(raw, final)
        raw.unlink(missing_ok=True)
        media.still_at(final, 0.15, out / "poster.jpg")
        media.contact_sheet(final, out / "contact.jpg", fps=2.0, cols=8, cell_w=180, title=name)
        report |= {"file": str(final), "loudness": media.loudness(final), "summary": media.summary(final)}
        post = spec.get("post") or {}
        if post:
            tags = " ".join(f"#{h.lstrip('#')}" for h in post.get("hashtags", []))
            (out / "caption.txt").write_text(f"{post.get('caption', '').strip()}\n\n{tags}\n")
    return report


# --------------------------------------------------------------------------- find / fetch (yt-dlp)


def find(query: str, max_sec: float = 90, top: int = 10, pool: int = 60) -> list[dict]:
    """Search YouTube, keep Shorts-length videos, rank by views; add upload date + views/day for the top ones.

    Search order is relevance, so we over-fetch `pool` results and sort ourselves. Keyword search often returns
    long videos; a "#tag" query (e.g. "#gta5mods") reads that hashtag's Shorts tab instead, which is Shorts only.
    """
    if query.startswith("#"):
        url = f"https://www.youtube.com/hashtag/{query.lstrip('#')}/shorts"
        res = json.loads(_run(["yt-dlp", "--flat-playlist", "-J", "--no-warnings", "--playlist-items", f"1:{pool}", url]))
        hits = [e for e in res.get("entries") or [] if e]          # Shorts tab has no durations; all are Shorts
    else:
        q = query if "#shorts" in query.lower() else f"{query} #shorts"
        res = json.loads(_run(["yt-dlp", "--flat-playlist", "-J", "--no-warnings", f"ytsearch{pool}:{q}"]))
        hits = [e for e in res.get("entries") or [] if e and e.get("duration") and e["duration"] <= max_sec]
    hits.sort(key=lambda e: e.get("view_count") or 0, reverse=True)
    out = []
    today = time.time()
    for e in hits[:top]:
        url = f"https://www.youtube.com/shorts/{e['id']}"
        info = json.loads(_run(["yt-dlp", "-J", "--skip-download", "--no-warnings", url]))
        days = max((today - (info.get("timestamp") or today)) / 86400, 1)
        out.append({
            "url": url, "title": e.get("title"), "channel": info.get("uploader_id") or e.get("channel"),
            "seconds": e.get("duration") or info.get("duration"), "views": e.get("view_count"), "likes": info.get("like_count"),
            "uploaded": info.get("upload_date"), "views_per_day": round((e.get("view_count") or 0) / days),
        })
    return out


def fetch(url: str, out: Path, start: float = 0, end: float | None = None, height: int = 1920) -> Path:
    """Download a video (or a window of it) as mp4. Rights are the skill's job: the builder still needs a `source:` block."""
    out.parent.mkdir(parents=True, exist_ok=True)
    win = ["--download-sections", f"*{start}-{end}", "--force-keyframes-at-cuts"] if end else []
    _run(["yt-dlp", "-q", "--no-warnings", "--no-playlist", "-S", f"res:{height},ext:mp4:m4a", *win,
          "--merge-output-format", "mp4", "-o", str(out), url])
    if not out.exists():
        raise ReelError(f"yt-dlp produced nothing for {url}")
    return out


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(prog="reelforge.shorts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="render a reel folder (reel.yaml)")
    b.add_argument("dir", type=Path)
    b.add_argument("--stills", help="comma-separated frames to render as PNGs (fast layout check)")
    b.add_argument("--no-render", action="store_true")
    s = sub.add_parser("sheet", help="timecoded contact sheet of a video")
    s.add_argument("video", type=Path)
    s.add_argument("out", type=Path)
    s.add_argument("--fps", type=float, default=1.0)
    fr = sub.add_parser("frame", help="extract one frame (optionally cropped) as PNG")
    fr.add_argument("video", type=Path)
    fr.add_argument("sec", type=float)
    fr.add_argument("out", type=Path)
    fr.add_argument("--crop", help="x,y,w,h in source pixels")
    fi = sub.add_parser("find", help="search YouTube Shorts, ranked by views")
    fi.add_argument("query")
    fi.add_argument("--max-sec", type=float, default=90)
    fi.add_argument("--top", type=int, default=10)
    fe = sub.add_parser("fetch", help="download a video (or a window of it) as mp4")
    fe.add_argument("url")
    fe.add_argument("out", type=Path)
    fe.add_argument("--from", dest="start", type=float, default=0)
    fe.add_argument("--to", dest="end", type=float)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "build":
            stills = [int(x) for x in a.stills.split(",")] if a.stills else None
            print(json.dumps(build(a.dir, render=not a.no_render, stills=stills), indent=1, default=str))
        elif a.cmd == "find":
            print(json.dumps(find(a.query, max_sec=a.max_sec, top=a.top), indent=1))
        elif a.cmd == "fetch":
            print(fetch(a.url, a.out, a.start, a.end))
        elif a.cmd == "sheet":
            print(media.contact_sheet(a.video, a.out, fps=a.fps, cols=6, cell_w=320))
        else:
            vf = ["-vf", "crop={2}:{3}:{0}:{1}".format(*a.crop.split(","))] if a.crop else []
            a.out.parent.mkdir(parents=True, exist_ok=True)
            _run(["ffmpeg", "-y", "-hide_banner", "-ss", str(a.sec), "-i", str(a.video), "-frames:v", "1", *vf, str(a.out)])
            print(a.out)
    except ReelError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
