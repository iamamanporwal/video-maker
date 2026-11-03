"""python build.py [--preview] [--no-render]: vo.py words → scene.py → parallel EEVEE → captions + VO + music + SFX.

Captions stay off for the first 4.5 s (channel rule: the hook is picture + voice only). Music is ducked under
the voice; whooshes/pops sit in the voice gaps only.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from reelforge.blender.render import BLENDER, render_shots  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

OUT, FPS, END = D / "out", 30, 75.5
NAME = "what-if-100"
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
MUSIC = ROOT / "projects/shorts/vi3w-memes/music/investigations.mp3"     # Kevin MacLeod, CC BY 4.0
SFX = ROOT / "assets/shorts-sfx"
CAPTIONS_FROM = 4.5
# (time s, sfx) — all inside measured VO gaps
CUES = [(3.0, "whoosh"), (14.7, "whoosh"), (16.95, "pop"), (26.45, "whoosh"), (40.7, "whoosh"),
        (57.3, "whoosh"), (66.05, "whoosh"), (69.75, "pop")]


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def phrases(words, max_words=3):
    """Group VO words into caption chunks: break on punctuation, long pauses or max_words."""
    out, cur = [], []
    for i, (a, b, w) in enumerate(words):
        cur.append((a, b, w))
        nxt = words[i + 1][0] if i + 1 < len(words) else None
        if len(cur) >= max_words or w[-1] in ".,?!" or (nxt and nxt - b > 0.35):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def caption_cards(words, out_dir, w=1080, h=1920, y=0.795):
    out_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(FONT, 70)
    cards = []
    chunks = [c for c in phrases(words) if c[0][0] >= CAPTIONS_FROM - 0.05]
    for k, ch in enumerate(chunks):
        toks = [t.strip(".,!?") if t[-1] in ".,!" else t for _, _, t in ch]
        im = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(im)
        space = d.textlength(" ", font=font)
        widths = [d.textlength(t, font=font) for t in toks]
        x = (w - sum(widths) - space * (len(toks) - 1)) / 2
        yy = int(h * y)
        sh = Image.new("RGBA", (w, h))
        sd = ImageDraw.Draw(sh)
        xx = x
        for t, tw in zip(toks, widths):
            sd.text((xx + 2, yy + 6), t, font=font, fill=(0, 0, 0, 200), stroke_width=8, stroke_fill=(0, 0, 0, 200))
            xx += tw + space
        im = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)), im)
        d = ImageDraw.Draw(im)
        for t, tw in zip(toks, widths):
            fill = "#ffd23f" if any(c.isdigit() for c in t) else "white"      # numbers pop in yellow
            d.text((x, yy), t, font=font, fill=fill, stroke_width=4, stroke_fill=(20, 22, 28, 235))
            x += tw + space
        p = out_dir / f"cap_{k:03d}.png"
        im.save(p)
        t0 = ch[0][0]
        t1 = chunks[k + 1][0][0] if k + 1 < len(chunks) else ch[-1][1] + 0.6
        cards.append((p, t0, min(t1, ch[-1][1] + 0.6)))
    return cards


def lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])


def level(mp4, target=-14.0):
    """Measured gain to the target loudness, then a -1 dBFS peak limiter; video stream copied untouched."""
    gain = target - lufs(mp4)
    tmp = mp4.with_suffix(".lvl.mp4")
    run(["ffmpeg", "-y", "-i", mp4, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp])
    tmp.replace(mp4)


def main(preview=False, do_render=True):
    t_all, stamps = time.time(), {}
    vo = json.loads((OUT / "words.json").read_text())
    if do_render:
        t = time.time()
        run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
        stamps["scene"] = time.time() - t
        frames = OUT / ("preview" if preview else "frames")
        shutil.rmtree(frames, ignore_errors=True)
        shots = json.loads((OUT / "shots.json").read_text())
        stamps["render"] = render_shots(str(OUT / "scene.blend"), str(frames), shots, workers=3,
                                        step=2 if preview else 1, scale=50 if preview else 100)
    frames = OUT / ("preview" if preview else "frames")

    t = time.time()
    cards = caption_cards([tuple(x) for x in vo["words"]], OUT / "captions")
    fps_in = FPS / 2 if preview else FPS
    seq = sorted(frames.glob("f_*.jpg"))
    lst = OUT / "frames.txt"
    lst.write_text("".join(f"file '{p}'\nduration {1 / fps_in:.6f}\n" for p in seq))
    W = 540 if preview else 1080
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", vo["mp3"],
           "-stream_loop", "-1", "-i", MUSIC]
    for _, name in CUES:
        cmd += ["-i", SFX / f"{name}.mp3"]
    n0 = 3 + len(CUES)
    for p, *_ in cards:
        cmd += ["-i", p]
    chain = [f"[0:v]fps={FPS},scale={W}:-2,format=yuv420p[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(cards):
        chain.append(f"[{n0 + k}:v]scale={W}:-2[c{k}]")
        chain.append(f"[{last}][c{k}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]fade=t=out:st={END - 0.7}:d=0.7[vout]")
    # audio: VO up front; music ducked by the VO (sidechain); SFX in the gaps
    chain.append("[1:a]aresample=48000,apad,asplit=2[vo][key]")
    chain.append(f"[2:a]aresample=48000,volume=0.22,afade=t=out:st={END - 2.0}:d=2.0[mus]")
    chain.append("[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[duck]")
    sfx = []
    for i, (t_, name) in enumerate(CUES):
        ms = int(t_ * 1000)
        chain.append(f"[{3 + i}:a]aresample=48000,volume={0.5 if name == 'whoosh' else 0.6},adelay={ms}|{ms}[s{i}]")
        sfx.append(f"[s{i}]")
    chain.append(f"[vo][duck]{''.join(sfx)}amix=inputs={2 + len(sfx)}:normalize=0:duration=first,"
                 f"atrim=0:{END}[aout]")
    mp4 = OUT / f"{NAME}{'-preview' if preview else ''}.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", f"{END}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", mp4]
    run(cmd)
    level(mp4)
    stamps["compose"] = time.time() - t
    print(" | ".join(f"{k} {v:.1f}s" for k, v in stamps.items()), f"| TOTAL {time.time() - t_all:.1f}s →", mp4)
    if not preview:
        dst = ROOT / "FinalUploads" / "Drafts"
        shutil.copy(mp4, dst / f"{NAME}.mp4")
        (dst / f"{NAME}.txt").write_text((D / "caption.txt").read_text())


def stills(times, scale=50):
    """Look-check: render the frames at these seconds, each with its own set's scene → out/stills + sheet."""
    run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
    shots = json.loads((OUT / "shots.json").read_text())
    jobs = []
    for t in times:
        f = round(t * FPS) + 1
        sc = next(s for s, a, b in shots if a <= f <= b)
        jobs.append((sc, f, f))
    dst = OUT / "stills"
    shutil.rmtree(dst, ignore_errors=True)
    dt = render_shots(str(OUT / "scene.blend"), str(dst), jobs, workers=3, scale=scale)
    run([sys.executable, D / "sheet.py", dst, OUT / "sheet.jpg", str(min(6, len(times)))])
    print(f"{len(times)} stills in {dt:.1f}s → out/sheet.jpg")


if __name__ == "__main__":
    if "--stills" in sys.argv:
        stills([float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")])
    else:
        main(preview="--preview" in sys.argv, do_render="--no-render" not in sys.argv)
