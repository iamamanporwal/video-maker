"""python build.py [--no-render] [--stills 0.6,2.4,...]: "60 years of 3D modeling → Vi3W" mini-doc.

scene.py → parallel EEVEE (720x1280, 8 samples) → upscale → era grading (B&W film 1963-72, faded 1975), serif year
cards, captions, the REAL Vi3W capture (Input/demo3.mp4) framed at 53.7-59.0 with the official logo, feature chips,
SFX, documentary music ducked under the VO, shared Vi3W outro. VO = local Kokoro am_michael (vo.py).
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
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

OUT, FPS = D / "out", 30
VO_AT, STORY_END = 0.3, 66.6
END = STORY_END + outro.META["dur"]
NAME = "3d-history"
SERIF = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
SANS = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MUSIC = D / "music/cinematic-documentary.mp3"   # AShamaluevMusic "Cinematic Documentary" (free for Shorts with credit)
SFX = D / "sfx"
CAPTURE = ROOT / "Input/demo3.mp4"              # real Vi3W screen capture: car sketch → image → 3D
CAP_SEGS = [(1.3, 2.7), (13.0, 14.6), (18.6, 20.0)]   # sketch, model appears, textured model turning
CAP_AT = 54.6                                   # capture starts on "Draw a sketch"
LOGO = ROOT / "Vi3W Assets/Vi3W LOGO.png"
BW = (5.6, 18.6)
FADED = (18.6, 23.9)
# (text, t0, t1, kind): year = big serif top card, chip = green pill, count = mono counter
CARDS = [(y, 0.05 + i * 0.28, 0.05 + (i + 1) * 0.28, "year") for i, y in
         enumerate(("1963", "1972", "1975", "1985", "1995", "2005", "2015"))] + [("2026", 2.01, 2.3, "year"),
         ("1963", 5.9, 12.9, "year"), ("1972", 13.0, 18.6, "year"), ("1975", 18.8, 23.9, "year"), ("1995", 24.2, 29.5, "year"),
         ("1998", 37.0, 38.7, "year"), ("2008", 38.7, 40.2, "year"), ("2018", 40.2, 41.6, "year"), ("TODAY", 41.6, 42.6, "year")] + \
        [(f"VERTICES MOVED: {n:,}", 46.4 + k * 0.2, 46.4 + (k + 1) * 0.2, "count") for k, n in
         enumerate((1, 37, 412, 1288, 2950, 4812, 7340))] + \
        [(f"DAY {d}", 48.4 + (d - 1) * 0.7, 48.4 + d * 0.7, "count") for d in (1, 2, 3)] + \
        [("SKETCH  →  3D", 54.6, 59.0, "label"),
         ("AUTO-RIG", 59.0, 62.0, "chip0"), ("ANIMATE", 59.8, 62.0, "chip1"), ("ROBLOX", 60.9, 62.0, "chip2"),
         ("UNITY", 61.55, 62.0, "chip3")]
CUES = [(0.0, "tick", 0.35)] + [(0.05 + i * 0.28, "click", 0.25) for i in range(8)] + \
       [(2.6, "click", 0.6), (5.6, "projector", 0.45), (5.6, "whoosh", 0.35), (12.9, "whoosh", 0.35), (18.6, "whoosh", 0.35),
        (23.9, "whoosh", 0.35), (29.5, "whoosh", 0.35), (35.4, "typing", 0.35), (37.0, "click", 0.4), (38.7, "click", 0.4),
        (40.2, "click", 0.4), (41.6, "click", 0.4)] + \
       [(t, "click", 0.55) for t in (42.9, 44.3, 45.4, 46.2, 46.8, 47.3)] + \
       [(48.3, "tick", 0.3), (52.5, "dun", 0.5), (53.2, "riser", 0.5), (53.75, "whoosh", 0.5), (54.6, "pop", 0.4),
        (59.0, "pop", 0.4), (59.8, "pop", 0.4), (60.9, "pop", 0.4), (61.55, "pop", 0.4), (62.0, "whoosh", 0.35),
        (STORY_END - 0.5, "riser", 0.4), (STORY_END + 4.0, "click", 0.6)]
SAY = [(("three-d",), "3D"), (("three", "d", "s", "max"), "3ds Max"), (("view",), "Vi3W"),
       (("nineteen", "sixty-three"), "1963"), (("nineteen", "seventy-two"), "1972"), (("nineteen", "seventy-five"), "1975"),
       (("nineteen", "ninety-five"), "1995"), (("nineteen", "ninety-eight"), "1998"), (("two", "thousand", "eight"), "2008"),
       (("twenty", "eighteen"), "2018"), (("sixty",), "60")]


def run(cmd, timeout=900):
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)


def display_words(words):
    out, i = [], 0
    while i < len(words):
        for pat, rep in SAY:
            seq = [w[2].lower().strip(".,!?") for w in words[i:i + len(pat)]]
            if tuple(seq) == pat:
                tail = words[i + len(pat) - 1][2][-1] if words[i + len(pat) - 1][2][-1] in ".,!?" else ""
                out.append((words[i][0], words[i + len(pat) - 1][1], rep + tail))
                i += len(pat)
                break
        else:
            out.append(words[i])
            i += 1
    return out


def phrases(words, max_words=4):
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


def draw_card(text, kind, path):
    im = Image.new("RGBA", (1080, 1920))
    d = ImageDraw.Draw(im)
    if kind == "year":
        f = ImageFont.truetype(SERIF, 170)
        tw = d.textlength(text, font=f)
        sh = Image.new("RGBA", im.size)
        ImageDraw.Draw(sh).text(((1080 - tw) / 2 + 4, 268), text, font=f, fill=(0, 0, 0, 200))
        im = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), im)
        ImageDraw.Draw(im).text(((1080 - tw) / 2, 260), text, font=f, fill="#f5efe2")
    elif kind in ("count", "label"):
        f = ImageFont.truetype(SANS, 64 if kind == "count" else 70)
        tw = d.textlength(text, font=f)
        y = 300 if kind == "count" else 1340
        d.text(((1080 - tw) / 2, y), text, font=f, fill="#ffd23f" if kind == "count" else "#7cff6b",
               stroke_width=5, stroke_fill="black")
    else:                                              # chips: green pills stacked
        k = int(kind[-1])
        f = ImageFont.truetype(SANS, 60)
        tw = d.textlength(text, font=f)
        x0, y0 = (1080 - tw) / 2 - 40, 1150 + k * 115
        d.rounded_rectangle((x0, y0, x0 + tw + 80, y0 + 95), radius=48, fill="#7cff6b")
        d.text((x0 + 40, y0 + 14), text, font=f, fill="#0b0d12")
    im.save(path)


def caption_cards(words, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype(SERIF, 62)
    cards = []
    chunks = phrases(display_words(words))
    for k, ch in enumerate(chunks):
        text = " ".join(t for _, _, t in ch).rstrip(",")
        im = Image.new("RGBA", (1080, 1920))
        d = ImageDraw.Draw(im)
        tw = d.textlength(text, font=f)
        d.text(((1080 - tw) / 2, 1480), text, font=f, fill="white", stroke_width=5, stroke_fill=(10, 10, 14))
        p = out_dir / f"cap_{k:03d}.png"
        im.save(p)
        t1 = chunks[k + 1][0][0] if k + 1 < len(chunks) else ch[-1][1] + 0.5
        cards.append((p, ch[0][0], min(t1, ch[-1][1] + 0.5)))
    for k, (text, a, b, kind) in enumerate(CARDS):
        p = out_dir / f"card_{k:03d}.png"
        draw_card(text, kind, p)
        cards.append((p, a, b))
    return cards


def capture_clip():
    """The real Vi3W capture: 3 windows of demo3, framed 1040 wide with a thin border, on transparent 1080x1920."""
    dst = OUT / "capture.mov"
    parts, ins = [], []
    for i, (a, b) in enumerate(CAP_SEGS):
        ins += ["-ss", f"{a}", "-t", f"{b - a}", "-i", CAPTURE]
        parts.append(f"[{i}:v]fps={FPS},scale=1040:-2,setsar=1,pad=1052:ih+12:6:6:color=0x7c5cff[c{i}]")
    n = len(CAP_SEGS)
    graph = ";".join(parts) + ";" + "".join(f"[c{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    run(["ffmpeg", "-y", *ins, "-filter_complex", graph, "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-pix_fmt",
         "yuv420p", dst])
    return dst, sum(b - a for a, b in CAP_SEGS)


def logo_png():
    """Official Vi3W logo (black-backed art) → alpha from brightness so it sits on any dark frame."""
    dst = OUT / "logo_alpha.png"
    im = Image.open(LOGO).convert("RGB")
    im.thumbnail((620, 620))
    a = im.convert("L").point(lambda v: min(255, int(v * 2.2)))
    out = im.copy()
    out.putalpha(a)
    canvas = Image.new("RGBA", (1080, 1920))
    canvas.paste(out, ((1080 - out.width) // 2, 560), out)
    canvas.save(dst)
    return dst


def lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])


def level(mp4, target=-13.2):
    gain = target - lufs(mp4)
    tmp = mp4.with_suffix(".lvl.mp4")
    run(["ffmpeg", "-y", "-i", mp4, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.85:level=false",
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
    cap, cap_dur = capture_clip()
    logo = logo_png()
    seq = sorted(frames.glob("f_*.*"))[: int(STORY_END * FPS)]
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
    ci = n0 + len(cards)
    cmd += ["-itsoffset", f"{CAP_AT}", "-i", cap, "-loop", "1", "-i", logo, "-i", outro.CLIP]
    li, oi = ci + 1, ci + 2
    b0, b1 = BW
    f0, f1 = FADED
    chain = [f"[0:v]fps={FPS},scale=1080:1920:flags=lanczos,setsar=1,"
             f"hue=s=0:enable='between(t,{b0},{b1})',eq=contrast=1.12:enable='between(t,{b0},{b1})',"
             f"noise=alls=22:allf=t:enable='between(t,{b0},{b1})',"
             f"hue=s=0.45:enable='between(t,{f0},{f1})',noise=alls=10:allf=t:enable='between(t,{f0},{f1})',"
             f"vignette=PI/5,format=yuv420p[st]",
             f"[{ci}:v]setsar=1[cap]",
             f"[st][cap]overlay=(W-w)/2:520:eof_action=pass:enable='between(t,{CAP_AT},{CAP_AT + cap_dur})'[s1]",
             f"[{li}:v]format=rgba,fade=t=in:st=53.7:d=0.25:alpha=1,fade=t=out:st=54.35:d=0.25:alpha=1[lg]",
             f"[s1][lg]overlay=0:0:enable='between(t,53.7,54.6)':shortest=0,trim=duration={STORY_END},setpts=PTS-STARTPTS[s2]",
             f"[{oi}:v]fps={FPS},scale=1080:1920,format=yuv420p,setsar=1[ou]", "[s2][ou]concat=n=2:v=1:a=0[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(cards):
        chain.append(f"[{last}][{n0 + k}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]fade=t=out:st={END - 0.6}:d=0.6[vout]")
    vo_ms, o_ms = int(VO_AT * 1000), int((STORY_END + o_at) * 1000)
    chain.append(f"[1:a]aresample=48000,volume=2.0,adelay={vo_ms}|{vo_ms}[vo1]")
    chain.append(f"[2:a]aresample=48000,volume=1.15,adelay={o_ms}|{o_ms}[vo2]")
    chain.append("[vo1][vo2]amix=inputs=2:normalize=0:duration=longest,apad,asplit=2[vo][key]")
    chain.append(f"[3:a]aresample=48000,volume=0.22,afade=t=out:st={END - 2.5}:d=2.5[mus]")
    chain.append("[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=400[duck]")
    sfx = []
    for i, (t_, name, vol) in enumerate(CUES):
        ms = int(t_ * 1000)
        chain.append(f"[{4 + i}:a]aresample=48000,volume={vol},adelay={ms}|{ms}[s{i}]")
        sfx.append(f"[s{i}]")
    chain.append(f"[vo][duck]{''.join(sfx)}amix=inputs={2 + len(sfx)}:normalize=0:duration=first,atrim=0:{END}[aout]")
    mp4 = OUT / f"{NAME}.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", f"{END}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-color_range", "tv",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", mp4]
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
    dt = render_shots(str(OUT / "scene.blend"), str(dst), jobs, workers=3, scale=50)
    fs = sorted(dst.glob("f_*.*"))
    cols, w, h = 6, 360, 640
    sheet = Image.new("RGB", (w * cols, h * (-(-len(fs) // cols))), "black")
    for i, f in enumerate(fs):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(Image.open(f).convert("RGB").resize((w, h)), (x, y))
        ImageDraw.Draw(sheet).text((x + 6, y + 6), f"{(int(f.stem[2:]) - 1) / FPS:.1f}s", fill="red")
    sheet.save(OUT / "sheet.jpg", quality=88)
    print(f"{len(times)} stills in {dt:.1f}s → out/sheet.jpg")


if __name__ == "__main__":
    if "--stills" in sys.argv:
        stills([float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")])
    else:
        main(do_render="--no-render" not in sys.argv)
