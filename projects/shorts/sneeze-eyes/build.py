"""python build.py [--no-render] [--stills 0.6,2.4,...]: scene.py → parallel EEVEE (PS2: 360x640, 1 sample, PNG) →
nearest-neighbour upscale → yellow PS2 captions, rewind + "cursed" effects, SFX, ducked music, shared Vi3W outro.

VO (Brian, one take) starts at VO_AT so the sneeze + eye pop own the first second.
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
from reelforge import outro  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT, FPS = D / "out", 30
VO_AT, STORY_END = 1.2, 36.8
END = STORY_END + outro.META["dur"]
NAME = "sneeze-eyes"
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MUSIC = D / "music/elevator.mp3"          # Kevin MacLeod, "Local Forecast - Elevator", CC BY 4.0 (credited in caption)
SFX = D / "sfx"
REWIND = (5.4, 5.8)
CURSED = (26.0, 27.6)
# (time s, sfx, volume)
CUES = [(0.0, "sneeze", 2.6), (0.58, "yt-boing", 0.8), (0.62, "pop", 0.5), (3.2, "whoosh", 0.45), (5.4, "vhs", 0.55),
        (9.0, "pop", 0.9), (9.02, "splash", 0.35)] + \
       [(10.15 + i * 0.22, "click", 0.35) for i in range(6)] + \
       [(12.95, "whoosh", 0.3), (15.95, "slam", 0.6), (16.65, "error", 0.35), (18.0, "sneeze2", 2.2), (18.0, "shutter", 0.4),
        (19.5, "sadflute-short", 0.5), (20.92, "slam", 0.35), (22.5, "squish", 0.45), (22.75, "bubble", 0.3),
        (24.55, "sneeze2", 2.2), (26.0, "vineboom", 0.75), (27.6, "dun", 0.55), (28.8, "stifle", 1.6), (29.7, "rain", 0.45),
        (32.85, "stifle", 1.6), (33.8, "shock", 0.55), (35.2, "bleep", 0.25),
        (STORY_END - 0.5, "riser", 0.45), (STORY_END + 4.0, "click", 0.6)]


def run(cmd, timeout=900):
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)


def phrases(words, max_words=5):
    out, cur = [], []
    for i, (a, b, w) in enumerate(words):
        cur.append((a, b, w))
        nxt = words[i + 1][0] if i + 1 < len(words) else None
        if len(cur) >= max_words or w[-1] in ".,?!" or (nxt and nxt - b > 0.3):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def card(text, path, size=58, y=0.67, fill="#f8e800", w=1080, h=1920, xy=None):
    font = ImageFont.truetype(FONT, size)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=font)
    x, yy = xy or ((w - tw) / 2, int(h * y))
    d.text((x, yy), text, font=font, fill=fill, stroke_width=4, stroke_fill="black")
    im.save(path)


def caption_cards(words, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    chunks = phrases(words)
    for k, ch in enumerate(chunks):
        text = " ".join(t for _, _, t in ch).rstrip(",")
        p = out_dir / f"cap_{k:03d}.png"
        card(text, p)
        t0 = ch[0][0]
        t1 = chunks[k + 1][0][0] if k + 1 < len(chunks) else ch[-1][1] + 0.6
        cards.append((p, t0, min(t1, ch[-1][1] + 0.5)))
    rw = out_dir / "rewind.png"
    card("<< REWIND", rw, size=64, fill="white", xy=(60, 120))
    cards.append((rw, *REWIND))
    return cards


def lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])


def level(mp4, target=-13.6):
    gain = target - lufs(mp4)
    tmp = mp4.with_suffix(".lvl.mp4")
    run(["ffmpeg", "-y", "-i", mp4, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp])
    tmp.replace(mp4)


def main(do_render=True):
    t_all, stamps = time.time(), {}
    vo = json.loads((OUT / "words.json").read_text())
    frames = OUT / "frames"
    if do_render:
        t = time.time()
        run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
        stamps["scene"] = time.time() - t
        shutil.rmtree(frames, ignore_errors=True)
        shots = json.loads((OUT / "shots.json").read_text())
        stamps["render"] = render_shots(str(OUT / "scene.blend"), str(frames), shots, workers=3)
    t = time.time()
    words = [(a + VO_AT, b + VO_AT, w) for a, b, w in vo["words"]]
    cards = caption_cards(words, OUT / "captions")
    seq = sorted(frames.glob("f_*.png"))[: int(STORY_END * FPS)]
    lst = OUT / "frames.txt"
    lst.write_text("".join(f"file '{p}'\nduration {1 / FPS:.6f}\n" for p in seq))
    o_mp3, _, o_at = outro.voice(D)
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", vo["mp3"], "-i", o_mp3,
           "-stream_loop", "-1", "-i", MUSIC]
    for _, name, _v in CUES:
        cmd += ["-i", SFX / f"{name}.mp3"]
    n0 = 4 + len(CUES)
    for p, *_ in cards:
        cmd += ["-i", p]
    cmd += ["-i", outro.CLIP]
    oi = n0 + len(cards)
    r0, r1 = REWIND
    c0, c1 = CURSED
    chain = [f"[0:v]fps={FPS},{'scale=1080:1920:flags=neighbor'},setsar=1,"
             f"hue=s=0.15:enable='between(t,{r0},{r1})',noise=alls=25:allf=t:enable='between(t,{r0},{r1})',"
             f"split=2[st][fry]",
             f"[fry]crop=iw/1.35:ih/1.35,scale=1080:1920:flags=neighbor,eq=saturation=3.2:contrast=1.7:brightness=0.05,"
             f"noise=alls=45:allf=t,unsharp=7:7:2.5[fry2]",
             f"[st][fry2]overlay=0:0:enable='between(t,{c0},{c1})',format=yuv420p[st2]",
             f"[{oi}:v]fps={FPS},scale=1080:1920,format=yuv420p,setsar=1[ou]", "[st2][ou]concat=n=2:v=1:a=0[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(cards):
        chain.append(f"[{last}][{n0 + k}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]fade=t=out:st={END - 0.6}:d=0.6[vout]")
    vo_ms, o_ms = int(VO_AT * 1000), int((STORY_END + o_at) * 1000)
    chain.append(f"[1:a]aresample=48000,volume=1.5,adelay={vo_ms}|{vo_ms}[vo1]")
    chain.append(f"[2:a]aresample=48000,volume=1.3,adelay={o_ms}|{o_ms}[vo2]")
    chain.append("[vo1][vo2]amix=inputs=2:normalize=0:duration=longest,apad,asplit=2[vo][key]")
    chain.append(f"[3:a]aresample=48000,volume=0.16,afade=t=out:st={END - 2.0}:d=2.0[mus]")
    chain.append("[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[duck]")
    sfx = []
    for i, (t_, name, vol) in enumerate(CUES):
        ms = int(t_ * 1000)
        chain.append(f"[{4 + i}:a]aresample=48000,volume={vol},adelay={ms}|{ms}[s{i}]")
        sfx.append(f"[s{i}]")
    chain.append(f"[vo][duck]{''.join(sfx)}amix=inputs={2 + len(sfx)}:normalize=0:duration=first,atrim=0:{END}[aout]")
    mp4 = OUT / f"{NAME}.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", f"{END}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", mp4]
    run(cmd)
    level(mp4)
    stamps["compose"] = time.time() - t
    print(" | ".join(f"{k} {v:.1f}s" for k, v in stamps.items()), f"| TOTAL {time.time() - t_all:.1f}s →", mp4)


def stills(times):
    run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
    shots = json.loads((OUT / "shots.json").read_text())
    jobs = []
    for t in times:
        f = round(t * FPS) + 1
        sc = next(s for s, a, b in shots if a <= f <= b)
        jobs.append((sc, f, f))
    dst = OUT / "stills"
    shutil.rmtree(dst, ignore_errors=True)
    dt = render_shots(str(OUT / "scene.blend"), str(dst), jobs, workers=3)
    from PIL import Image as I, ImageDraw as ID
    fs = sorted(dst.glob("f_*.png"))
    cols = 6
    w, h = 360, 640
    sheet = I.new("RGB", (w * cols, h * (-(-len(fs) // cols))), "black")
    for i, f in enumerate(fs):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(I.open(f).convert("RGB"), (x, y))
        ID.Draw(sheet).text((x + 6, y + 6), f"{(int(f.stem[2:]) - 1) / FPS:.1f}s", fill="red")
    sheet.save(OUT / "sheet.jpg", quality=90)
    print(f"{len(times)} stills in {dt:.1f}s → out/sheet.jpg")


if __name__ == "__main__":
    if "--stills" in sys.argv:
        stills([float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")])
    else:
        main(do_render="--no-render" not in sys.argv)
