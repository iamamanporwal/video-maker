"""python build.py [--no-render] [--stills 0.6,2.4,...]: scene.py → parallel EEVEE → captions, deep-fry hits,
gunshots + meme SFX in the VO gaps, ducked music, shared Vi3W outro.

VO = local Kokoro af_heart take (vo.py), starts at VO_AT. Parody of the "Cars anatomy" fan-art meme.
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
VO_AT, STORY_END = 0.3, 41.4
END = STORY_END + outro.META["dur"]
NAME = "mcqueen-brain"
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
MUSIC = D / "music/sneaky-snitch.mp3"     # Kevin MacLeod, "Sneaky Snitch", CC BY 4.0 (credited in caption)
SFX = D / "sfx"
FRY = [(5.75, 6.25), (24.2, 24.6), (40.25, 40.9)]          # deep-fried zoom hits: BRO / teeth / Ka-chow
HOT = {"brain", "heart", "gasoline", "intestines", "mouth", "teeth", "feet", "awake", "crime", "hearse", "ka-chow",
       "machines", "eyelids"}
# (time s, sfx, volume): SFX sit in the VO gaps; the tyre gunshots are the one deliberate overlap (short transients)
CUES = [(0.0, "whoosh", 0.4), (1.2, "shock", 0.35), (2.75, "squish", 0.7), (2.8, "whoosh", 0.55),
        (5.72, "vineboom", 0.9), (7.34, "gun", 0.9), (7.58, "gun2", 0.9),
        (11.3, "pop", 0.45), (11.72, "pop", 0.45), (12.5, "slam", 0.3),
        (16.5, "bubble", 0.4), (18.0, "squish", 0.8), (19.9, "whoosh", 0.5),
        (24.22, "vineboom", 0.85),
        (26.3, "pop", 0.35), (26.42, "pop", 0.35), (26.54, "pop", 0.35), (26.66, "pop", 0.35),
        (27.18, "gun", 0.4), (27.34, "gun2", 0.4), (27.54, "gun", 0.4), (27.9, "gun9", 0.7),
        (30.66, "sadflute-short", 0.55),
        (32.95, "slam", 0.9), (32.97, "gun9", 0.5), (34.55, "dun", 0.6),
        (38.32, "vineboom", 0.8), (40.95, "gun9", 1.0),
        (STORY_END + 4.0, "click", 0.6)]


def run(cmd, timeout=1800):
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)


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


def card(text, path, size=78, y=0.64, fill="white", w=1080, h=1920):
    font = ImageFont.truetype(FONT, size)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    while d.textlength(text, font=font) > w - 120:
        size -= 4
        font = ImageFont.truetype(FONT, size)
    tw = d.textlength(text, font=font)
    d.text(((w - tw) / 2, int(h * y)), text, font=font, fill=fill, stroke_width=7, stroke_fill="black")
    im.save(path)


EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"
GUNS = [t for t, n, _ in CUES if n.startswith("gun")]
SHAKE = [(t, t + 0.3) for t in GUNS] + [(5.72, 6.0), (24.22, 24.5), (32.95, 33.4), (38.32, 38.6)]
# (text-or-emoji, t0, t1, x, y, size, rotation, colour) - meme stickers; emoji when colour is None
STICKERS = [("BANG!", 7.34, 7.85, 120, 330, 150, 12, "#ff2a2a"), ("BANG!", 7.58, 7.85, 560, 520, 120, -10, "#ffd400"),
            ("💀", 6.3, 7.3, 760, 300, 160, -8, None),
            ("🤢", 18.4, 19.85, 760, 330, 160, 10, None),
            ("BANG!", 27.18, 27.6, 90, 300, 120, 10, "#ff2a2a"), ("BANG!", 27.34, 27.7, 600, 420, 110, -12, "#ffd400"),
            ("BANG!", 27.54, 27.9, 200, 600, 120, -6, "#ff2a2a"), ("BANG!!", 27.9, 28.3, 380, 260, 160, 6, "#ffd400"),
            ("thank you 🥹", 29.5, 31.1, 0, 0, 80, 0, "bubble"),
            ("🚨", 33.4, 35.0, 90, 280, 150, -10, None), ("🚨", 33.4, 35.0, 820, 280, 150, 10, None),
            ("R.I.P.", 37.46, 38.9, 0, 300, 170, 0, "#ffffff"), ("🪦", 37.46, 38.9, 460, 520, 160, 0, None),
            ("BANG!", 40.95, 41.4, 160, 420, 190, -8, "#ff2a2a")]


def sticker(text, x, y, size, rot, colour, path, w=1080, h=1920):
    im = Image.new("RGBA", (w, h))
    if colour is None:
        f = ImageFont.truetype(EMOJI, 160)
        tile = Image.new("RGBA", (200, 200))
        ImageDraw.Draw(tile).text((20, 20), text, font=f, embedded_color=True)
        tile = tile.resize((int(200 * size / 160),) * 2).rotate(rot, expand=True, resample=Image.BICUBIC)
        im.alpha_composite(tile, (x, y))
    elif colour == "bubble":
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((240, 380, 840, 560), 60, fill="white", outline="black", width=8)
        d.polygon([(430, 552), (500, 552), (420, 660)], fill="white", outline="black")
        d.line([(436, 556), (494, 556)], fill="white", width=10)
        ft = ImageFont.truetype(FONT, size)
        ef = ImageFont.truetype(EMOJI, 160)
        word, emo = text.rsplit(" ", 1)
        d.text((290, 425), word, font=ft, fill="black")
        e = Image.new("RGBA", (200, 200)); ImageDraw.Draw(e).text((20, 20), emo, font=ef, embedded_color=True)
        im.alpha_composite(e.resize((90, 90)), (720, 420))
    else:
        f = ImageFont.truetype(FONT, size)
        d0 = ImageDraw.Draw(im)
        tw = d0.textlength(text, font=f)
        tile = Image.new("RGBA", (int(tw) + 60, size + 80))
        ImageDraw.Draw(tile).text((30, 20), text, font=f, fill=colour, stroke_width=10, stroke_fill="black")
        tile = tile.rotate(rot, expand=True, resample=Image.BICUBIC)
        im.alpha_composite(tile, (int((w - tile.width) / 2) if x == 0 else x, y))
    im.save(path)


def caption_cards(words, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    chunks = phrases(words)
    for k, ch in enumerate(chunks):
        text = " ".join(t for _, _, t in ch).rstrip(",").upper()
        hot = any(t.lower().strip(".,?!") in HOT for _, _, t in ch)
        p = out_dir / f"cap_{k:03d}.png"
        card(text, p, fill="#ffe600" if hot else "white")
        t0 = ch[0][0]
        t1 = chunks[k + 1][0][0] if k + 1 < len(chunks) else ch[-1][1] + 0.6
        cards.append((p, t0, min(t1, ch[-1][1] + 0.5, STORY_END)))
    for k, (txt, a, b, x, y, size, rot, col) in enumerate(STICKERS):
        p = out_dir / f"stk_{k:02d}.png"
        sticker(txt, x, y, size, rot, col, p)
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
    seq = sorted(frames.glob("f_*.jpg"))[: int(STORY_END * FPS)]
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
    fry_en = "+".join(f"between(t,{a},{b})" for a, b in FRY)
    sh = "+".join(f"between(t,{a},{b})" for a, b in SHAKE)
    fl = "+".join(f"between(t,{t_},{t_ + 0.07})" for t_ in GUNS)
    chain = [f"[0:v]fps={FPS},scale=1188:2112,crop=1080:1920:x='54+if({sh},26*sin(t*97),0)':y='96+if({sh},26*cos(t*83),0)',"
             f"eq=brightness=0.45:contrast=0.8:enable='{fl}',setsar=1,trim=duration={STORY_END},split=2[st][fry]",
             f"[fry]crop=iw/1.3:ih/1.3,scale=1080:1920,eq=saturation=2.6:contrast=1.5:brightness=0.04,"
             f"noise=alls=30:allf=t,unsharp=7:7:2.0[fry2]",
             f"[st][fry2]overlay=0:0:enable='{fry_en}',format=yuv420p[st2]",
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
    chain.append(f"[3:a]aresample=48000,volume=0.17,afade=t=out:st={END - 2.0}:d=2.0[mus]")
    chain.append("[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[duck]")
    sfx = []
    for i, (t_, name, vol) in enumerate(CUES):
        ms = int(t_ * 1000)
        chain.append(f"[{4 + i}:a]aresample=48000,volume={vol},adelay={ms}|{ms}[s{i}]")
        sfx.append(f"[s{i}]")
    chain.append(f"[vo][duck]{''.join(sfx)}amix=inputs={2 + len(sfx)}:normalize=0:duration=first,atrim=0:{END}[aout]")
    mp4 = OUT / f"{NAME}.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", f"{END}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M",
            "-pix_fmt", "yuv420p", "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", mp4]
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
    fs = sorted(dst.glob("f_*.jpg"))
    cols, w, h = 6, 270, 480
    sheet = Image.new("RGB", (w * cols, h * (-(-len(fs) // cols))), "black")
    for i, f in enumerate(fs):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(Image.open(f).convert("RGB").resize((w, h)), (x, y))
        ImageDraw.Draw(sheet).text((x + 6, y + 6), f"{(int(f.stem[2:]) - 1) / FPS:.1f}s", fill="red")
    sheet.save(OUT / "sheet.jpg", quality=90)
    print(f"{len(times)} stills in {dt:.1f}s → out/sheet.jpg")


if __name__ == "__main__":
    if "--stills" in sys.argv:
        stills([float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")])
    else:
        main(do_render="--no-render" not in sys.argv)
