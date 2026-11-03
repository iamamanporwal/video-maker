"""Build the NakeyJakey mod clips (shorts.yaml) into 9:16 shorts with a Vi3W ending.

usage: .venv/bin/python projects/shorts/nakey-mods/build.py [id-prefix ...] [--stills] [--ship]
  cut ranges → public/clips/<id>.mp4 (30 fps, -16 LUFS), creator words → caption frames, CTA VO (fal ElevenLabs v3),
  props → Remotion ModClip → master (-14 LUFS) → out/<id>/<id>.mp4 + contact sheet + caption.txt.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")
from reelforge import shorts  # noqa: E402
from reelforge.ops import media  # noqa: E402

FPS = 30
PUB = D / "public"
VOICE = {"id": "FGY2WhTYpPnrIDTdsKH5", "provider": "fal", "model": "eleven_v3", "stability": 0.0}  # Laura
FIX = {"gary's": "Garry's", "imposter": "impostor"}  # whisper spellings
MASK = {"fucking": "f*cking", "fucked": "f*cked", "shit": "sh*t", "goddamn": "godd*mn", "-ass": "-a*s"}


def run(cmd: list[str], cwd: Path | None = None) -> str:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{' '.join(map(str, cmd[:4]))} failed:\n{(r.stderr or r.stdout)[-3000:]}")
    return r.stdout


def clean(w: str) -> str:
    """Fix whisper spellings and soften profanity in captions (audio is untouched)."""
    core = re.sub(r"[^\w'*-]", "", w).lower()
    for k, v in {**FIX, **MASK}.items():
        if core == k:
            return re.sub(re.escape(k), v, w, flags=re.I)
    return w


def cut(src: Path, ranges: list, out: Path) -> None:
    """Stitch ranges with 40 ms audio fades at every join; 1080p30, audio at -16 LUFS."""
    parts, labels = [], []
    for i, (a, b) in enumerate(ranges):
        d = b - a
        parts.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,fps={FPS}[v{i}];"
                     f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={d - 0.06:.3f}:d=0.06[a{i}];")
        labels.append(f"[v{i}][a{i}]")
    fc = "".join(parts) + "".join(labels) + f"concat=n={len(ranges)}:v=1:a=1[v][a0];[a0]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
         "-ar", "48000", str(out)])


def words_for(all_words: list, ranges: list) -> tuple[list, list]:
    out, cuts, t0 = [], [], 0.0
    for a, b in ranges:
        if t0:
            cuts.append(round(t0 * FPS))
        for s, e, w in all_words:
            if a - 0.05 <= s < b - 0.05:
                if w.startswith("-") and out:            # whisper splits "Half -Life", "Among Us -style"
                    out[-1][1], out[-1][2] = round((min(e, b) - a + t0) * FPS), out[-1][2] + clean(w)
                    continue
                out.append([round((s - a + t0) * FPS), round((min(e, b) - a + t0) * FPS), clean(w)])
        t0 += b - a
    return out, cuts


def build(cfg: dict, s: dict, stills: bool) -> dict:
    sid = s["id"]
    out = D / "out" / sid
    out.mkdir(parents=True, exist_ok=True)
    clip = PUB / "clips" / f"{sid}.mp4"
    if not clip.exists() or clip.stat().st_mtime < (D / "shorts.yaml").stat().st_mtime:
        cut(D / cfg["source"], s["ranges"], clip)
    clip_s = float(media.probe(clip)["format"]["duration"])
    clip_f = int(clip_s * FPS) - 1
    words, cuts = words_for(json.loads((D / cfg["words"]).read_text()), s["ranges"])

    vo_path, _, vo_s = shorts.tts(D, PUB, VOICE, s["vo"], {"Vi3W": "View", "Vi3W.in": "view dot in"})
    vo_n = PUB / vo_path.replace(".mp3", "-n.mp3")
    if not vo_n.exists():
        run(["ffmpeg", "-v", "error", "-y", "-i", str(PUB / vo_path), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", str(vo_n)])
    reveal = 40                                         # sketch scanned → 3D pops at ending frame 40
    vo_at = 8
    cta_f = max(round(7.5 * FPS), vo_at + round(vo_s * FPS) + 26)
    total = clip_f + cta_f
    cta = cfg["cta"] | {"line": s.get("cta_line", cfg["cta"]["line"]), "from": clip_f, "dur": cta_f, "reveal": reveal,
                        "sketch": "img/sketch.png", "glb": "models/robot-tt.webm", "logo": "img/logo.png"}
    props = {
        "fps": FPS, "durationInFrames": total,
        "clip": {"src": f"clips/{sid}.mp4", "dur": clip_f, "cuts": cuts, "focus": s.get("focus", 0.6), "zoom": s.get("zoom", 1.0)},
        "words": words, "emphasis": [e.lower() for e in s.get("emphasis", [])],
        "headline": {"text": s["headline"], "from": round(s.get("headline_at", 4.0) * FPS)},
        "credit": cfg["credit"], "cta": cta,
        "vo": [{"src": vo_n.relative_to(PUB).as_posix(), "from": clip_f + vo_at}],
        "cues": [
            {"src": "sfx/whoosh.mp3", "from": clip_f - 8, "volume": 0.5},
            {"src": "sfx/pop.mp3", "from": clip_f + reveal, "volume": 0.45},
            {"src": "music/pixelland.mp3", "from": clip_f, "volume": 0.07},
        ],
    }
    pj = out / "props.json"
    pj.write_text(json.dumps(props, indent=1))
    common = ["--props", str(pj), "--public-dir", str(PUB)]
    rem = ROOT / "node" / "remotion"
    if stills:
        for t in (0.2, 4.6, clip_s * 0.5, clip_s - 1, clip_s + 0.6, clip_s + 2.2, total / FPS - 0.5):
            run(["npx", "remotion", "still", "src/shorts/index.ts", "ModClip", str(out / f"s_{t:05.1f}.png"),
                 "--frame", str(min(total - 1, round(t * FPS)))] + common, cwd=rem)
        return {"id": sid, "stills": str(out)}
    raw = out / f"{sid}.raw.mp4"
    run(["npx", "remotion", "render", "src/shorts/index.ts", "ModClip", str(raw), "--codec", "h264", "--crf", "16",
         "--pixel-format", "yuv420p", "--image-format", "jpeg", "--jpeg-quality", "95", "--timeout", "240000",
         "--concurrency", "6"] + common, cwd=rem)
    final = out / f"{sid}.mp4"
    media.master(raw, final)
    raw.unlink(missing_ok=True)
    media.contact_sheet(final, out / "contact.jpg", fps=1.0, cols=8, cell_w=180, title=sid)
    tags = " ".join(f"#{h}" for h in s.get("hashtags", []))
    (out / "caption.txt").write_text(f"{s['caption'].strip()}\n\n{cfg['music_credit']}\n\n{tags}\n")
    return {"id": sid, "file": str(final), "seconds": round(total / FPS, 2), "clip_s": round(clip_s, 2),
            "loudness": media.loudness(final)}


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cfg = yaml.safe_load((D / "shorts.yaml").read_text())
    for s in cfg["shorts"]:
        if args and not any(s["id"].startswith(a) for a in args):
            continue
        print(json.dumps(build(cfg, s, "--stills" in sys.argv)), flush=True)


if __name__ == "__main__":
    main()
