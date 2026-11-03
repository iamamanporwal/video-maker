"""python build.py [--preview] [--no-render] [--stills 1,3,...]: scene.py → parallel EEVEE → VO lines placed on the
timeline + captions + comedy SFX + music.

0-5 s is silent of VO and text (channel rule): picture + squish/yelp/growl carry the hook. The one Laura take
(vo.py) is cut into lines (SEGS) and each line is dropped at its beat; captions follow the shifted word times.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
import os  # noqa: E402
for _l in (ROOT / ".env").read_text().splitlines():
    if "=" in _l and not _l.lstrip().startswith("#"):
        _k, _v = _l.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
from reelforge.blender.render import BLENDER, render_shots  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

OUT, FPS, STORY_END = D / "out", 30, 24.0
from reelforge import outro  # noqa: E402
END = STORY_END + outro.META["dur"]
NAME = "landlord-dog"
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
MUSIC = D / "music/sneaky-snitch.mp3"      # Kevin MacLeod, "Sneaky Snitch", CC BY 4.0 (credited in caption)
SFX = D / "sfx"
CAPTIONS_FROM = 5.0
# (vo start s, vo end s, timeline s): lines of the single VO take, placed on their beats
SEGS = [(0.30, 2.95, 5.0), (2.95, 5.50, 7.9), (5.50, 9.40, 10.9), (9.40, 10.40, 14.3), (10.40, 14.98, 18.4)]
# ending = the shared pre-rendered Vi3W outro (reelforge.outro) + a fresh VO take of its line for this short


def cues(step):
    """(time s, sfx, volume); the squish/yelp land on the measured foot plant."""
    return [(step - 0.02, "squish", 0.8), (step + 0.08, "yelp", 0.9), (3.1, "growl", 0.75), (5.3, "grow", 0.6),
            (8.5, "pop", 0.5), (9.9, "whoosh", 0.45), (11.05, "gulp", 0.8), (13.9, "growl", 0.55),
            (14.05, "bark", 0.7), (14.45, "scramble", 0.6), (16.5, "bark", 0.5), (18.3, "dun", 0.65),
            (21.3, "kaching", 0.7), (23.8, "riser", 0.5), (24.05, "whoosh", 0.4), (25.0, "pop", 0.4), (26.8, "pop", 0.3),
            (28.0, "click", 0.7), (28.95, "pop", 0.4)]      # outro: reveal, headline, chip, URL click, link-in-bio


def shifted_words(vo):
    out = []
    for a, b, w in vo["words"]:
        for s0, s1, at in SEGS:
            if s0 <= a < s1:
                out.append((a - s0 + at, b - s0 + at, w))
    return out                     # the outro's 3D title carries its words: no captions there


def run(cmd, timeout=600):
    """Every step is time-boxed: a stalled ffmpeg graph once hung silently for 2.5 h; now it fails in minutes."""
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=timeout)


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


def place_vo(mp3):
    """The VO lines dropped on their beats → one wav (separate pass: splitting one input 6 ways in the main
    graph stalled ffmpeg)."""
    dst = OUT / "vo_track.wav"
    parts, ins = [], []
    for i, (s0, s1, at) in enumerate(SEGS):
        ins += ["-ss", f"{s0}", "-t", f"{s1 - s0:.2f}", "-i", mp3]
        ms = int(at * 1000)
        parts.append(f"[{i}:a]aresample=48000,afade=t=in:d=0.03,afade=t=out:st={s1 - s0 - 0.05:.2f}:d=0.05,"
                     f"adelay={ms}|{ms}[l{i}]")
    n = len(SEGS)
    o_mp3, _, o_at = outro.voice(D)
    ins += ["-i", o_mp3]
    ms = int((STORY_END + o_at) * 1000)
    parts.append(f"[{n}:a]aresample=48000,adelay={ms}|{ms}[l{n}]")
    graph = ";".join(parts) + ";" + "".join(f"[l{i}]" for i in range(n + 1)) + \
        f"amix=inputs={n + 1}:normalize=0:duration=longest,apad=whole_dur={END}[a]"
    run(["ffmpeg", "-y", *ins, "-filter_complex", graph, "-map", "[a]", "-t", f"{END}", dst])
    return dst


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
    cards = caption_cards(shifted_words(vo), OUT / "captions")
    CUES = cues(json.loads((OUT / "meta.json").read_text())["step"])
    fps_in = FPS / 2 if preview else FPS
    seq = sorted(frames.glob("f_*.jpg"))[: int(STORY_END * fps_in)]
    lst = OUT / "frames.txt"
    lst.write_text("".join(f"file '{p}'\nduration {1 / fps_in:.6f}\n" for p in seq))
    W = 540 if preview else 1080
    vo_track = place_vo(vo["mp3"])
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", vo_track,
           "-stream_loop", "-1", "-i", MUSIC]
    for _, name, _v in CUES:
        cmd += ["-i", (SFX / f"{name}.mp3") if (SFX / f"{name}.mp3").exists() else ROOT / "assets/shorts-sfx" / f"{name}.mp3"]
    n0 = 3 + len(CUES)
    for p, *_ in cards:
        cmd += ["-i", p]
    cmd += ["-i", outro.CLIP]
    oi = n0 + len(cards)
    chain = [f"[0:v]fps={FPS},scale={W}:-2,format=yuv420p,setsar=1[st]",
             f"[{oi}:v]fps={FPS},scale={W}:-2,format=yuv420p,setsar=1[ou]", "[st][ou]concat=n=2:v=1:a=0[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(cards):
        chain.append(f"[{n0 + k}:v]scale={W}:-2[c{k}]")
        chain.append(f"[{last}][c{k}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]fade=t=out:st={END - 0.7}:d=0.7[vout]")
    # audio: VO up front; music ducked by the VO (sidechain); SFX in the gaps
    chain.append("[1:a]aresample=48000,volume=1.6,apad,asplit=2[vo][key]")
    chain.append(f"[2:a]aresample=48000,volume=0.2,afade=t=out:st={END - 2.0}:d=2.0[mus]")
    chain.append("[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[duck]")
    sfx = []
    for i, (t_, name, vol) in enumerate(CUES):
        ms = int(t_ * 1000)
        chain.append(f"[{3 + i}:a]aresample=48000,volume={vol},adelay={ms}|{ms}[s{i}]")
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
