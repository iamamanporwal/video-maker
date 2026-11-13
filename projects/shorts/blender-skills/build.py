"""python build.py [--no-render] [--stills 0.5,4,...]: "This GitHub repo gives AI 94 Blender skills" informative short.

scene.py → parallel EEVEE (720x1280) → upscale → captions, skill chips, MCP chat, install terminal, SFX, music ducked
under the VO. Same pipeline as 3d-history, but NO Vi3W outro (the user asked for a purely informative video).
VO = Chatterbox best-of-N (vo.py) → out/words.json.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from reelforge.blender.render import BLENDER, render_shots  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

OUT, FPS, NAME = D / "out", 30, "blender-skills"
VO_AT = 0.15                                       # must match scene.py
SANS = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MONO = "/System/Library/Fonts/Menlo.ttc"
MUSIC = D / "music/investigations.mp3"            # Kevin MacLeod "Investigations", CC BY 4.0
SFX = D / "sfx"
VO = json.loads((OUT / "words.json").read_text()) if (OUT / "words.json").exists() else None
SAY = [(("ninety-four",), "94"), (("ai",), "AI")]


def ws(key, i=0):
    return VO_AT + VO["words"][VO["lines"][key][0] + i][0]


def we(key):
    return VO_AT + VO["words"][VO["lines"][key][1] - 1][1]


def run(cmd, timeout=1800):
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)


def plan():
    END = json.loads((OUT / "timing.json").read_text())["END"]
    off_t, jump_t = we("p4") + 0.15, we("p4") + 0.6
    cards = [("WITHOUT SKILLS", 0.05, ws("h3"), "bad"), ("WITH blender-skills", ws("h3"), ws("h4"), "good"),
             ("", ws("h4") + 0.55, ws("b1"), "circle")]
    t4 = ws("b1", 4)
    for k in range(10):                                          # counter 1 → 94 lands on "Ninety-four"
        a = ws("b1") + (t4 - ws("b1")) * k / 10
        n = max(1, round(94 * ((k + 1) / 10) ** 1.6))
        cards.append((f"{n} SKILLS", a, ws("b1") + (t4 - ws("b1")) * (k + 1) / 10, "count"))
    cards.append(("94 SKILLS", t4, ws("b2"), "count"))
    cards.append(("github.com/arjun988/blender-skills", ws("b1"), ws("b2"), "url"))
    st = [ws("b2", i) for i in (4, 6, 7, 11, 12)] + [ws("b3")]
    for k, n in enumerate(("hard-surface", "retopology", "uv-workflow", "materials", "lighting")):
        cards.append((n, st[k], st[k + 1], "chip"))
    sy = [ws("b4", i) for i in (5, 7, 8, 9)] + [ws("b5")]
    for k, n in enumerate(("lowpoly-style", "anime-style", "voxel-style", "horror-style")):
        cards.append((n, sy[k], sy[k + 1], "chip"))
    cards.append(("no style", ws("b4"), sy[0], "chipdim"))
    prompt = "build a tiny low-poly island"
    t0, t1 = ws("b5") + 0.1, ws("b5") + 1.6
    steps = 10
    for k in range(steps):
        n = round(len(prompt) * (k + 1) / steps)
        cards.append((prompt[:n], t0 + (t1 - t0) * k / steps, t0 + (t1 - t0) * (k + 1) / steps if k < steps - 1 else ws("p1"),
                      "chat"))
    cards.append(("BLENDER MCP  CONNECTED", ws("b5"), ws("p1"), "mcp"))
    jobs = [(ws("p2"), ws("p2", 3), "JOB 1", "horror-style + lighting"),
            (ws("p2", 3), ws("p2", 6), "JOB 2", "hard-surface + materials"),
            (ws("p2", 6), ws("p3"), "JOB 3", "lowpoly-style + cozy-wholesome-mood")]
    cards.append(("3 JOBS", ws("p1"), ws("p2"), "count"))
    for a, b, j, chain in jobs:
        cards.append((j, a, b, "count"))
        cards.append((chain, a, b, "chip"))
    cards.append(("2,409 stars  ·  MIT licence", ws("p3"), ws("p3", 7), "star"))
    term = ["$ git clone github.com/arjun988/blender-skills", "$ cp -r blender-skills/.claude/skills .claude/",
            "94 skills ready"]
    tl = [ws("p3", 7), ws("p3", 9), ws("p3", 11)]
    for k in range(3):
        cards.append(("\n".join(term[:k + 1]), tl[k], (tl[k + 1] if k < 2 else ws("p3", 12)), "term"))
    hit = ws("p3", 12) + 0.75
    cards.append(("NO MORE DONUTS", hit, ws("p4"), "stamp"))
    cards.append(("github.com/arjun988/blender-skills", ws("p4"), off_t, "url2"))
    cues = [(0.0, "tick", 0.3), (ws("h2", 8), "click", 0.5), (ws("h3") - 0.15, "whoosh", 0.45), (ws("h3"), "dun", 0.55),
            (ws("h3"), "buzz", 0.5), (ws("h4"), "riser", 0.4), (ws("h4") + 0.5, "whoosh", 0.4), (ws("h4") + 0.55, "dun", 0.6),
            (ws("b1"), "whoosh", 0.4), (ws("b2"), "whoosh", 0.35)] + \
           [(t, "pop", 0.45) for t in st[:5]] + [(ws("b3"), "whoosh", 0.35)] + \
           [(ws("b3", i), "click", 0.45) for i in (4, 6, 8, 10, 12)] + \
           [(t, "whoosh", 0.35) for t in [ws("b4")] + sy[:4]] + [(ws("b5"), "typing", 0.3)] + \
           [(ws("b5") + 0.3 + k * ((ws("p1") - 0.5) - (ws("b5") + 0.3)) / 8 + 0.25, "pop", 0.3) for k in range(8)] + \
           [(ws("p1"), "buzz", 0.45), (ws("p2", 3), "whoosh", 0.35), (ws("p2", 6), "whoosh", 0.35),
            (ws("p3"), "ding", 0.35), (ws("p3", 7), "typing", 0.4), (ws("p3", 11), "ding", 0.4), (ws("p3", 12), "whoosh", 0.35),
            (hit, "dun", 0.8), (hit, "pop", 0.6), (ws("p4"), "buzz", 0.4), (off_t, "click", 0.7), (jump_t, "stab", 1.0)]
    return END, cards, cues


CENSOR = {"fucking": "f*cking", "fuck": "f*ck", "shit.": "sh*t.", "shit": "sh*t", "asshole": "a**hole"}


def display_words(words):
    out = []
    for a, b, w in words:
        core = w.lower().strip(".,!?")
        rep = next((r for pat, r in SAY if pat == (core,)), None)
        w = CENSOR.get(w.lower(), w)
        out.append((a, b, (rep + (w[-1] if w[-1] in ".,!?" else "")) if rep else w))
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


def pill(d, x0, y0, text, f, fill, fg, pad=34, h=None):
    tw = d.textlength(text, font=f)
    h = h or f.size + 34
    d.rounded_rectangle((x0, y0, x0 + tw + pad * 2, y0 + h), radius=h // 2, fill=fill)
    d.text((x0 + pad, y0 + (h - f.size) / 2 - 4), text, font=f, fill=fg)
    return tw + pad * 2


def draw_card(text, kind, path):
    im = Image.new("RGBA", (1080, 1920))
    d = ImageDraw.Draw(im)
    if kind in ("bad", "good"):
        f = ImageFont.truetype(SANS, 66)
        tw = d.textlength(text, font=f) + 80
        pill(d, (1080 - tw) / 2, 250, text, f, "#ff3b3b" if kind == "bad" else "#3dff7a", "white" if kind == "bad" else "#06120a",
             40, 110)
    elif kind == "circle":                                     # meme red circle around the guy in the doorway
        d.ellipse((540 - 170, 860 - 300, 540 + 170, 860 + 300), outline="#ff2020", width=14)
    elif kind == "stamp":
        f = ImageFont.truetype(SANS, 96)
        st_ = Image.new("RGBA", (1000, 300))
        sd = ImageDraw.Draw(st_)
        tw = sd.textlength(text, font=f)
        sd.rounded_rectangle((500 - tw / 2 - 40, 60, 500 + tw / 2 + 40, 240), radius=24, outline="#ff1f3a", width=14)
        sd.text((500 - tw / 2, 82), text, font=f, fill="#ff1f3a")
        st_ = st_.rotate(-9, expand=False, resample=Image.BICUBIC)
        im.alpha_composite(st_, (40, 230))
    elif kind == "count":
        f = ImageFont.truetype(SANS, 120)
        tw = d.textlength(text, font=f)
        d.text(((1080 - tw) / 2, 220), text, font=f, fill="#ffd23f", stroke_width=8, stroke_fill="black")
    elif kind in ("url", "url2"):
        f = ImageFont.truetype(MONO, 40 if kind == "url" else 44)
        tw = d.textlength(text, font=f) + 60
        y = 380 if kind == "url" else 1210
        d.rounded_rectangle(((1080 - tw) / 2, y, (1080 + tw) / 2, y + 80), radius=18, fill=(10, 12, 20, 225),
                            outline="#3dff7a" if kind == "url2" else "#4a5370", width=3)
        d.text(((1080 - tw) / 2 + 30, y + 16), text, font=f, fill="white")
    elif kind in ("chip", "chipdim"):
        f = ImageFont.truetype(MONO, 54)
        if d.textlength(text, font=f) > 960:
            f = ImageFont.truetype(MONO, int(54 * 960 / d.textlength(text, font=f)))
        tw = d.textlength(text, font=f) + 70
        x0 = (1080 - tw) / 2
        y0 = 370 if "+" in text else 250
        pill(d, x0, y0, text, f, "#e9e9e9" if kind == "chipdim" else "#3dff7a", "#06120a", 35, 100)
    elif kind == "chat":
        f = ImageFont.truetype(MONO, 46)
        x0, y0, w_, h_ = 70, 230, 940, 170
        d.rounded_rectangle((x0, y0, x0 + w_, y0 + h_), radius=28, fill=(20, 22, 30, 235), outline="#7c5cff", width=4)
        d.text((x0 + 36, y0 + 22), "you ›", font=ImageFont.truetype(SANS, 34), fill="#a99bff")
        d.text((x0 + 36, y0 + 82), text + "▌", font=f, fill="white")
    elif kind == "mcp":
        f = ImageFont.truetype(SANS, 40)
        tw = d.textlength(text, font=f) + 110
        x0, y0 = (1080 - tw) / 2, 440
        d.rounded_rectangle((x0, y0, x0 + tw, y0 + 76), radius=38, fill=(12, 14, 20, 230))
        d.ellipse((x0 + 28, y0 + 24, x0 + 56, y0 + 52), fill="#3dff7a")
        d.text((x0 + 76, y0 + 15), text, font=f, fill="white")
    elif kind == "star":
        f = ImageFont.truetype(SANS, 64)
        tw = d.textlength(text, font=f) + 80
        x0 = (1080 - tw) / 2
        d.rounded_rectangle((x0, 250, x0 + tw, 370), radius=60, fill=(12, 14, 20, 235), outline="#ffd23f", width=4)
        d.text((x0 + 40, 274), text, font=f, fill="#ffd23f")
    elif kind == "term":
        f = ImageFont.truetype(MONO, 34)
        x0, y0, w_, h_ = 50, 640, 980, 360
        sh = Image.new("RGBA", im.size)
        ImageDraw.Draw(sh).rectangle((0, y0 - 90, 1080, y0 + h_ + 90), fill=(0, 0, 0, 130))
        ImageDraw.Draw(sh).rounded_rectangle((x0 + 8, y0 + 14, x0 + w_ + 8, y0 + h_ + 14), radius=26, fill=(0, 0, 0, 170))
        im = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), im)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((x0, y0, x0 + w_, y0 + h_), radius=26, fill=(14, 16, 24, 245), outline="#2e3550", width=3)
        for k, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
            d.ellipse((x0 + 30 + k * 40, y0 + 28, x0 + 54 + k * 40, y0 + 52), fill=c)
        for k, line in enumerate(text.split("\n")):
            col = "#3dff7a" if not line.startswith("$") else "white"
            d.text((x0 + 34, y0 + 100 + k * 78), ("✓ " + line) if not line.startswith("$") else line, font=f, fill=col)
    im.save(path)


def caption_cards(words, out_dir, cards_spec):
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype(SANS, 68)
    cards = []
    chunks = phrases(display_words(words))
    for k, ch in enumerate(chunks):
        text = " ".join(t for _, _, t in ch).rstrip(",")
        im = Image.new("RGBA", (1080, 1920))
        d = ImageDraw.Draw(im)
        tw = d.textlength(text, font=f)
        if tw > 1000:
            f2 = ImageFont.truetype(SANS, int(68 * 1000 / tw))
            tw = d.textlength(text, font=f2)
        else:
            f2 = f
        d.text(((1080 - tw) / 2, 1440), text, font=f2, fill="white", stroke_width=7, stroke_fill=(8, 8, 12))
        p = out_dir / f"cap_{k:03d}.png"
        im.save(p)
        t1 = chunks[k + 1][0][0] if k + 1 < len(chunks) else ch[-1][1] + 0.5
        cards.append((p, ch[0][0], min(t1, ch[-1][1] + 0.5)))
    for k, (text, a, b, kind) in enumerate(cards_spec):
        p = out_dir / f"card_{k:03d}.png"
        draw_card(text, kind, p)
        cards.append((p, a, b))
    return cards


def lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])


def level(mp4, target=-14.0):
    gain = target - lufs(mp4)
    tmp = mp4.with_suffix(".lvl.mp4")
    run(["ffmpeg", "-y", "-i", mp4, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp])
    tmp.replace(mp4)


def make_stab():
    p = SFX / "stab.mp3"
    if not p.exists():                                  # jumpscare: noise burst + detuned low saws, hard attack
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=1.2:c=white:a=0.6", "-f", "lavfi", "-i",
             "aevalsrc='0.5*sin(2*PI*55*t)*gte(sin(2*PI*58*t),0)+0.4*sin(2*PI*233*t)':d=1.2", "-filter_complex",
             "[0]lowpass=f=5000,volume=0.7[a];[1]volume=0.9[b];[a][b]amix=inputs=2:normalize=0,"
             "afade=t=out:st=0.2:d=1.0,acompressor", "-ac", "2", "-ar", "48000", p])


def make_buzz():
    p = SFX / "buzz.mp3"
    if not p.exists():                                  # fluorescent hum: 120 Hz + harmonics, slight crackle
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=120:d=2.6", "-f", "lavfi", "-i", "sine=f=240:d=2.6",
             "-f", "lavfi", "-i", "anoisesrc=d=2.6:c=pink:a=0.08", "-filter_complex",
             "[0]volume=0.5[a];[1]volume=0.25[b];[2]highpass=f=2000[c];[a][b][c]amix=inputs=3:normalize=0,"
             "afade=t=in:d=0.05,afade=t=out:st=2.0:d=0.6", "-ac", "2", "-ar", "48000", p])


def main(do_render=True):
    t_all, stamps = time.time(), {}
    END, spec, CUES = plan()
    frames = OUT / "frames"
    if do_render:
        t = time.time()
        run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
        stamps["scene"] = time.time() - t
        shutil.rmtree(frames, ignore_errors=True)
        shots = json.loads((OUT / "shots.json").read_text())
        stamps["render"] = render_shots(str(OUT / "scene.blend"), str(frames), shots, workers=3)
    t = time.time()
    make_buzz()
    make_stab()
    words = [(a + VO_AT, b + VO_AT, w) for a, b, w in VO["words"]]
    cards = caption_cards(words, OUT / "captions", spec)
    seq = sorted(frames.glob("f_*.*"))[: int(END * FPS)]
    lst = OUT / "frames.txt"
    lst.write_text("".join(f"file '{p}'\nduration {1 / FPS:.6f}\n" for p in seq))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", VO["mp3"], "-stream_loop", "-1", "-i", MUSIC]
    for _, name, _v in CUES:
        cmd += ["-i", SFX / f"{name}.mp3"]
    n0 = 3 + len(CUES)
    for p, *_ in cards:
        cmd += ["-i", p]
    chain = [f"[0:v]fps={FPS},scale=1080:1920:flags=lanczos,setsar=1,format=yuv420p,trim=duration={END},setpts=PTS-STARTPTS[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(cards):
        chain.append(f"[{last}][{n0 + k}:v]overlay=0:0:enable='between(t,{a:.2f},{b - 0.01:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]null[vout]")
    vo_ms = int(VO_AT * 1000)
    m0 = int((ws("h2") - 0.1) * 1000)
    chain.append(f"[1:a]aresample=48000,volume=1.8,adelay={vo_ms}|{vo_ms},apad,asplit=3[vo][key][key2]")
    chain.append(f"[2:a]aresample=48000,volume=0.2,adelay={m0}|{m0},afade=t=out:st={END - 2.0}:d=2.0[mus]")
    chain.append("[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=400[duck]")
    sfx = []
    for i, (t_, name, vol) in enumerate(CUES):
        ms = int(t_ * 1000)
        chain.append(f"[{3 + i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol},adelay={ms}|{ms}[s{i}]")
        sfx.append(f"[s{i}]")
    chain.append(f"{''.join(sfx)}amix=inputs={len(sfx)}:normalize=0:duration=longest[fxr]")
    chain.append("[fxr][key2]sidechaincompress=threshold=0.04:ratio=5:attack=15:release=300[fx]")
    chain.append(f"[vo][duck][fx]amix=inputs=3:normalize=0:duration=first,atrim=0:{END}[aout]")
    mp4 = OUT / f"{NAME}.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", f"{END}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
            "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", mp4]
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
