"""python build.py [--no-render] [--stills 0.6,2.4,...]: scene.py → parallel EEVEE (PS2: 360x640, 1 sample, PNG) →
nearest-neighbour upscale → yellow PS2 captions + GTA-style day/hour title cards, brain-glitch effect, SFX, ducked
music, shared Vi3W outro. VO = local Kokoro af_heart take (vo.py; ElevenLabs credits were exhausted).
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
VO_AT, STORY_END = 0.2, 46.4
END = STORY_END + outro.META["dur"]
NAME = "awake-11"
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MUSIC = D / "music/pixelland.mp3"         # Kevin MacLeod, "Pixelland", CC BY 4.0 (credited in caption)
BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
SFX = D / "sfx"
GLITCH = (16.1, 17.4)
# GTA-style title cards (text, t0, t1)
TITLES = [(f"DAY {d}", 0.2 + (d - 1) * 0.19, 0.2 + d * 0.19) for d in range(1, 11)] + [("DAY 11", 2.1, 2.3),
          ("DAY 3", 14.85, 17.4), ("DAY 4", 19.45, 22.4), ("264 HOURS", 33.2, 35.0), ("14 HOURS", 36.3, 37.9),
          ("YEARS LATER", 42.95, 44.3)]
# (time s, sfx, volume)
CUES = [(0.0, "tick", 0.5)] + [(0.2 + d * 0.19, "click", 0.3) for d in range(11)] + \
       [(5.0, "pop", 0.6), (11.55, "pop", 0.35), (11.85, "pop", 0.35), (12.15, "pop", 0.35),
        (12.45, "slam", 0.35), (12.85, "slam", 0.35), (13.25, "slam", 0.35), (13.3, "shower", 0.7),
        (16.1, "error", 0.5), (16.12, "vhs", 0.3), (18.75, "slam", 0.7), (21.2, "yt-boing", 0.8), (22.95, "wow", 0.6),
        (27.85, "bleep", 0.25), (28.55, "bleep", 0.25), (28.85, "bleep", 0.25), (29.15, "bleep", 0.25), (29.45, "bleep", 0.25),
        (30.1, "pop", 0.6), (31.2, "sadflute-short", 0.5), (33.2, "tick", 0.4), (35.35, "slam", 0.5), (36.3, "snore", 0.55),
        (38.95, "slam", 0.85), (40.05, "shock", 0.5), (44.6, "dun", 0.6),
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


NUM = [(("nineteen", "sixty-three"), "1963"), (("two", "hundred", "and", "sixty-four"), "264"),
       (("seventeen-year-old",), "17-year-old"), (("sixty-five",), "65"), (("fourteen",), "14"), (("eleven",), "11"),
       (("hundred",), "100")]


def merge_numbers(words):
    out, i = [], 0
    while i < len(words):
        for pat, rep in NUM:
            seq = [w[2].lower().strip(".,!?") for w in words[i:i + len(pat)]]
            if tuple(seq) == pat:
                out.append((words[i][0], words[i + len(pat) - 1][1], rep))
                i += len(pat)
                break
        else:
            out.append(words[i])
            i += 1
    return out


def caption_cards(words, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    chunks = phrases(merge_numbers(words))
    for k, ch in enumerate(chunks):
        text = " ".join(t for _, _, t in ch).rstrip(",")
        p = out_dir / f"cap_{k:03d}.png"
        card(text, p)
        t0 = ch[0][0]
        t1 = chunks[k + 1][0][0] if k + 1 < len(chunks) else ch[-1][1] + 0.6
        cards.append((p, t0, min(t1, ch[-1][1] + 0.5)))
    for k, (text, a, b) in enumerate(TITLES):
        p = out_dir / f"title_{k:02d}.png"
        font = ImageFont.truetype(BLACK, 120)
        im = Image.new("RGBA", (1080, 1920))
        d = ImageDraw.Draw(im)
        tw = d.textlength(text, font=font)
        d.text(((1080 - tw) / 2, 300), text, font=font, fill="#ffffff", stroke_width=8, stroke_fill="black")
        im.save(p)
        cards.append((p, a, b))
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
        cmd += (["-t", "2.6"] if name == "snore" else []) + ["-i", SFX / f"{name}.mp3"]
    n0 = 4 + len(CUES)
    for p, *_ in cards:
        cmd += ["-i", p]
    cmd += ["-i", outro.CLIP]
    oi = n0 + len(cards)
    g0, g1 = GLITCH
    chain = [f"[0:v]fps={FPS},scale=1080:1920:flags=neighbor,setsar=1,split=2[st][gl]",
             f"[gl]rgbashift=rh=-18:bh=18:gv=6,noise=alls=40:allf=t,hue=h=40*sin(40*t)[gl2]",
             f"[st][gl2]overlay=0:0:enable='between(t,{g0},{g1})',format=yuv420p[st2]",
             f"[{oi}:v]fps={FPS},scale=1080:1920,format=yuv420p,setsar=1[ou]", "[st2][ou]concat=n=2:v=1:a=0[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(cards):
        chain.append(f"[{last}][{n0 + k}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]fade=t=out:st={END - 0.6}:d=0.6[vout]")
    vo_ms, o_ms = int(VO_AT * 1000), int((STORY_END + o_at) * 1000)
    chain.append(f"[1:a]aresample=48000,volume=1.9,adelay={vo_ms}|{vo_ms}[vo1]")
    chain.append(f"[2:a]aresample=48000,volume=1.15,adelay={o_ms}|{o_ms}[vo2]")
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
