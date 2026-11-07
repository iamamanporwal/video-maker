"""python build.py [--preview] [--no-render] [--stills t,..]: scene.py → EEVEE → Breaking Bad grade + element-tile
cards + captions + VO + music + SFX + shared Vi3W outro.

Captions stay off for the first 4.5 s (channel rule: the hook is picture + voice only). Music is ducked under
the voice; whooshes/pops sit in the voice gaps only.
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

OUT, FPS = D / "out", 30
VO_ = json.loads((OUT / "words.json").read_text())
STORY_END = VO_["words"][-1][1] + 2.6
from reelforge import outro  # noqa: E402
END = STORY_END + outro.META["dur"]
NAME = "walt-no-cancer"
OUTRO_LINE = outro.LINE
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MUSIC = D / "music/bed.wav"                     # "Southern Gothic", Kevin MacLeod (incompetech.com), CC BY 4.0
SFX = D / "sfx"
CAPTIONS_FROM = 4.5
MUSIC_OFF = (42.55, 45.66)                       # smash to silence for the hat; the final cut brings it back
# (s, sfx file, gain) — booms/clunks sit in VO gaps; the ticks are quiet under "twenty-five more years"
CUES = [(0.0, "boom", 0.55), (18.18, "boom", 0.35), (26.2, "ticks", 0.22), (42.5, "clunk", 0.7),
        (45.66, "boom", 0.45), (47.3, "boom", 0.9)]
GREEN = (38, 120, 52)                            # Breaking Bad element-tile green
FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
# time-ranged grade: sun-baked desert yellow outside, sick fluorescent green inside (story only; outro untouched)
OUTSIDE = [(0.0, 3.32), (14.22, 23.65), (45.71, 99)]
INSIDE = [(3.32, 14.22), (23.65, 45.71)]


def tile(d, x, y, sz, sym, num="", mass="", alpha=255):
    """One periodic-table element tile (green gradient, white edge, symbol + atomic number + mass)."""
    tl = Image.new("RGBA", (sz, sz))
    td = ImageDraw.Draw(tl)
    for i in range(sz):                                      # vertical gradient, lighter at top
        k = 1.25 - 0.5 * i / sz
        td.line([(0, i), (sz, i)], fill=(int(GREEN[0] * k), int(GREEN[1] * k), int(GREEN[2] * k), alpha))
    td.rectangle((0, 0, sz - 1, sz - 1), outline=(235, 245, 230, alpha), width=max(3, sz // 40))
    f = ImageFont.truetype(FONT_B, int(sz * (0.55 if len(sym) <= 2 else 0.4)))
    td.text((sz / 2, sz * 0.56), sym, font=f, fill=(255, 255, 255, alpha), anchor="mm")
    if num:
        td.text((sz * 0.1, sz * 0.07), num, font=ImageFont.truetype(FONT_B, int(sz * 0.15)), fill=(230, 240, 225, alpha))
    if mass:
        td.text((sz * 0.5, sz * 0.9), mass, font=ImageFont.truetype(FONT_B, int(sz * 0.11)), fill=(230, 240, 225, alpha),
                anchor="mm")
    d.alpha_composite(tl, (int(x), int(y)))


def shadow_text(im, xy, text, font, fill="white", anchor="la"):
    sh = Image.new("RGBA", im.size)
    ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 6), text, font=font, fill=(0, 0, 0, 220), anchor=anchor)
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(im).text(xy, text, font=font, fill=fill, anchor=anchor)


def counter_cards(out_dir, w=1080, h=1920):
    """Element-tile cards: the 25 years ticking by (CLASS), 99.1 % (BOX) and the title card on the last image."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    years, t0, t1 = list(range(2009, 2035)), 26.2, 28.12
    for k, yr in enumerate(years):                           # year tile accelerates like the clock
        a = t0 + (t1 - t0) * (k / len(years)) ** 0.8
        b = t0 + (t1 - t0) * ((k + 1) / len(years)) ** 0.8 if k + 1 < len(years) else 28.1
        im = Image.new("RGBA", (w, h))
        tile(im, (w - 300) / 2, 300, 300, str(yr - 2008), num="YEARS", mass=str(yr))
        p = out_dir / f"yr_{k:02d}.png"
        im.save(p)
        cards.append((p, a, b))
    im = Image.new("RGBA", (w, h))                           # 99.1 %
    tile(im, w / 2 - 330, 300, 300, "99", num="purity", mass="")
    tile(im, w / 2 + 30, 300, 300, ".1%", num="", mass="")
    p = out_dir / "pure.png"
    im.save(p)
    cards.append((p, 38.03, 42.3))
    # title: "What if" + No [Ca]ncer — classic element-tile wordmark
    im = Image.new("RGBA", (w, h))
    shadow_text(im, (w / 2, 470), "WHAT IF...", ImageFont.truetype(FONT_B, 64), fill=(240, 240, 230), anchor="mm")
    big = ImageFont.truetype(FONT_B, 150)
    d = ImageDraw.Draw(im)
    sz = 220
    parts = ["No ", None, "ncer"]
    widths = [d.textlength("No ", font=big), sz + 8, d.textlength("ncer", font=big)]
    x = (w - sum(widths)) / 2
    y = 560
    shadow_text(im, (x, y + sz * 0.5), "No", big, anchor="lm")
    x += widths[0]
    tile(im, x, y, sz, "Ca", num="20", mass="40.078")
    x += widths[1]
    shadow_text(im, (x, y + sz * 0.5), "ncer", big, anchor="lm")
    p = out_dir / "title.png"
    im.save(p)
    cards.append((p, 47.3, STORY_END))
    return cards


def run(cmd, timeout=600):
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
            fill = "#7ddc5a" if any(c.isdigit() for c in t) or t.lower().startswith(("heisenberg", "cancer")) else "white"
            d.text((x, yy), t, font=font, fill=fill, stroke_width=4, stroke_fill=(20, 22, 28, 235))
            x += tw + space
        p = out_dir / f"cap_{k:03d}.png"
        im.save(p)
        t0 = ch[0][0]
        t1 = chunks[k + 1][0][0] if k + 1 < len(chunks) else ch[-1][1] + 0.6
        cards.append((p, t0, min(t1, ch[-1][1] + 0.6)))
    return cards


def place_vo(mp3):
    """Story VO + a fresh take of the shared outro line at STORY_END → one wav (kept out of the main graph)."""
    dst = OUT / "vo_track.wav"
    o_mp3, _, o_at = outro.voice(D, OUTRO_LINE)
    ms = int((STORY_END + o_at) * 1000)
    run(["ffmpeg", "-y", "-i", mp3, "-i", o_mp3, "-filter_complex",
         f"[0:a]aresample=48000[a0];[1:a]aresample=48000,adelay={ms}|{ms}[a1];"
         f"[a0][a1]amix=inputs=2:normalize=0:duration=longest,apad=whole_dur={END}[a]", "-map", "[a]", "-t", f"{END}", dst])
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
    cards = caption_cards([tuple(x) for x in vo["words"]], OUT / "captions")
    cards += counter_cards(OUT / "counter")
    fps_in = FPS / 2 if preview else FPS
    seq = sorted(frames.glob("f_*.jpg"))[: int(STORY_END * fps_in)]
    lst = OUT / "frames.txt"
    lst.write_text("".join(f"file '{p}'\nduration {1 / fps_in:.6f}\n" for p in seq))
    W = 540 if preview else 1080
    vo_track = place_vo(vo["mp3"])
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", vo_track,
           "-i", MUSIC]
    for _, name, _g in CUES:
        cmd += ["-i", SFX / f"{name}.wav"]
    n0 = 3 + len(CUES)
    for p, *_ in cards:
        cmd += ["-i", p]
    cmd += ["-i", outro.CLIP]
    oi = n0 + len(cards)
    chain = [f"[0:v]fps={FPS},scale={W}:-2,format=yuv420p,setsar=1[st]",
             f"[{oi}:v]fps={FPS},scale={W}:-2,format=yuv420p,setsar=1[ou]", "[st][ou]concat=n=2:v=1:a=0[v0]"]
    def rng(spans):
        return "+".join(f"between(t,{a:.2f},{min(b, STORY_END):.2f})" for a, b in spans)
    chain.append(f"[v0]colorbalance=rs=0.10:gs=0.04:bs=-0.16:rm=0.08:gm=0.03:bm=-0.14:rh=0.04:bh=-0.08:enable='{rng(OUTSIDE)}',"
                 f"eq=saturation=1.18:contrast=1.08:enable='{rng(OUTSIDE)}',"
                 f"colorbalance=rs=-0.06:gs=0.05:bs=-0.02:rm=-0.05:gm=0.07:bm=-0.04:enable='{rng(INSIDE)}',"
                 f"eq=saturation=0.88:contrast=1.06:enable='{rng(INSIDE)}',"
                 f"noise=alls=9:allf=t:enable='between(t,0,{STORY_END:.2f})'[vg]")
    last = "vg"
    for k, (p, a, b) in enumerate(cards):
        chain.append(f"[{n0 + k}:v]scale={W}:-2[c{k}]")
        chain.append(f"[{last}][c{k}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]fade=t=out:st={END - 0.7}:d=0.7[vout]")
    # audio: VO up front; music ducked by the VO (sidechain); SFX in the gaps
    chain.append("[1:a]aresample=48000,apad,asplit=2[vo][key]")
    chain.append(f"[2:a]aresample=48000,volume=0.55,volume=0:enable='between(t,{MUSIC_OFF[0]},{MUSIC_OFF[1]})',"
                 f"afade=t=out:st={END - 2.0}:d=2.0[mus]")
    chain.append("[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[duck]")
    sfx = []
    for i, (t_, name, g) in enumerate(CUES):
        ms = int(t_ * 1000)
        chain.append(f"[{3 + i}:a]aresample=48000,volume={g},adelay={ms}|{ms}[s{i}]")
        sfx.append(f"[s{i}]")
    chain.append(f"[vo][duck]{''.join(sfx)}amix=inputs={2 + len(sfx)}:normalize=0:duration=first,"
                 f"atrim=0:{END}[aout]")
    mp4 = OUT / f"{NAME}{'-preview' if preview else ''}.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", f"{END}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-maxrate", "14M", "-bufsize", "28M", "-c:a", "aac", "-b:a", "192k",
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
