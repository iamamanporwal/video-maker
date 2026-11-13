"""~/models/chatterbox-venv/bin/python build.py: Roblox Studio stills (frames/) + real Vi3W robot renders (out/robot) →
1080x1920 story with push-ins, punch-ins, one-word captions (GreenBroRants style), then the custom Vi3W outro.
Audio: Chatterbox VO (out/vo/story.wav) + Kevin MacLeod "Sneaky Snitch" (CC BY 4.0) bed + SFX in VO gaps."""
import json, math, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageEnhance

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
OUT = D / "out"; FR = D / "frames"
W, H, FPS = 1080, 1920, 30
M = json.loads((OUT / "words.json").read_text())
L = {l["id"]: l for l in M["lines"]}
STORY_END = M["dur"] + 0.25
CROP = {k: int(v) for k, v in (ln.split() for ln in (FR / "crops.txt").read_text().split("\n") if ln.strip())}
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
SKETCH = ROOT / "projects/launch/one-sketch-away/assets/robot-drawing.png"
CLAY = ROOT / "projects/launch/one-sketch-away/assets/robot0.jpeg"
TEX = ROOT / "projects/launch/one-sketch-away/assets/robot1.jpeg"
LOGO = ROOT / "Vi3W Assets/Vi3W LOGO.png"
SFXD = ROOT / "projects/shorts/landlord-dog/sfx"
MUSIC = ROOT / "projects/shorts/landlord-dog/music/sneaky-snitch.mp3"
OUTRO = OUT / "outro.mp4"
OUTRO_META = {"dur": 7.0, "url_at": 3.33}


def w(lid, i):
    return L[lid]["words"][i][1]


# ---------------------------------------------------------------- composites (in capture coordinates, 1018x1080)
def robot(name):
    im = Image.open(OUT / "robot" / f"robot_{name}.png").convert("RGBA")
    return im.crop(im.getbbox())


def paste_robot(base, name, cx, feet_y, height, flip=False):
    r = robot(name)
    if flip:
        r = r.transpose(Image.FLIP_LEFT_RIGHT)
    s = height / r.height
    r = r.resize((max(1, int(r.width * s)), int(height)), Image.LANCZOS)
    base.alpha_composite(r, (int(cx - r.width / 2), int(feet_y - r.height)))
    return base


def comp(name):
    im = Image.open(FR / f"{name.split('+')[0]}.jpg").convert("RGBA")
    if name == "S19":                       # the REAL hand-drawn sketch on his paper
        sk = Image.open(SKETCH).convert("RGBA").resize((254 - 12, 329 - 12), Image.LANCZOS)
        sk = ImageEnhance.Contrast(ImageEnhance.Brightness(sk).enhance(1.05)).enhance(1.6)
        im.alpha_composite(sk, (368 + 6, 398 + 6))
    elif name == "S20+robot":
        paste_robot(im, "night_low", 790, 830, 760)
    elif name == "S21":
        paste_robot(im, "night_kick", 250, 885, 600, flip=True)
    elif name == "S22":
        paste_robot(im, "day", 520, 735, 430)
        paste_robot(im, "day", 300, 1000, 300, flip=True)
    return im


def plate(name):
    """capture → 9:16 crop at the shot's centre → 1.12x oversize canvas for push-ins."""
    im = comp(name)
    key = name.split("+")[0]
    cx = {"S20+robot": 760, "S20": 330}.get(name, CROP.get(key, 509))
    cw = int(1080 * 9 / 16)
    x0 = max(0, min(im.width - cw, cx - cw // 2))
    im = im.crop((x0, 0, x0 + cw, 1080)).convert("RGB")
    big = im.resize((int(W * 1.12), int(H * 1.12)), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=2))
    big = ImageEnhance.Color(big).enhance(1.12)
    return big


def vi3w_card():
    """Insert: real sketch → Vi3W clay → textured, with the official logo (Vi3W Assets)."""
    bg = Image.new("RGB", (W, H), (14, 8, 30))
    g = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        g.line([(0, y), (W, y)], fill=(int(14 + 30 * t), int(8 + 10 * t), int(30 + 40 * (1 - t))))
    logo = Image.open(LOGO).convert("RGB").resize((300, int(300 * 1964 / 2068)), Image.LANCZOS)
    cards = []
    for p in (SKETCH, CLAY, TEX):
        c = bg.copy()
        c.paste(ImageChops.lighter(c.crop((390, 120, 690, 120 + logo.height)), logo), (390, 120))
        img = Image.open(p).convert("RGB").resize((960, 960), Image.LANCZOS)
        c.paste(img, (60, 520))
        d = ImageDraw.Draw(c)
        f = ImageFont.truetype(FONT, 70)
        lab = {SKETCH: "my drawing", CLAY: "Vi3W turns it 3D", TEX: "real 3D model"}[p]
        tw = d.textlength(lab, font=f)
        d.text(((W - tw) / 2, 1560), lab, font=f, fill="white", stroke_width=8, stroke_fill="black")
        cards.append(c)
    return cards


# ---------------------------------------------------------------- shot list
PUNCH = {"S01", "S13b", "S16b", "S17c", "S14a", "S10b", "S21", "S20+robot", "S12a"}
SHOTS = [
    (0.0, "S01"), (w("h2", 0), "S02"), (w("a1", 0), "S03"), (w("a2", 0), "S04"),
    (w("a3", 0), "S05"), (w("a3", 6), "S06"), (w("m1", 0), "S07"), (w("m2", 0), "S08"),
    (w("c1", 0), "S09a"), (w("c1", 10), "S09b"), (w("c2", 0), "S10a"), (L["c2"]["end"] + 0.2, "S10b"),
    (w("c3", 0), "S11"), (w("c4", 0), "S12a"), (w("c4", 2), "S12b"), (w("c4", 3), "S12c"),
    (w("n1", 0), "S13a"), (w("n1", 5), "S13b"), (w("n1", 7), "S13c"),
    (w("n2", 0), "S14a"), (w("n2", 4), "S14b"), (w("n2", 9), "S14c"), (w("n3", 0), "S15"),
    (w("b1", 0), "S16a"), (w("b1", 7), "S16b"),
    (w("b2", 0), "S17a"), (w("b2", 4), "S17b"), (w("b2", 7), "S17c"), (w("b3", 0), "S18"),
    (w("v1", 0), "S19"), (w("v1", 11), "VI3W"),
    (w("v2", 0), "S20"), (w("v2", 3), "S20+robot"), (w("v3", 0), "S21"),
    (w("e1", 0), "S22"), (w("e2", 0), "S23"),
]
SHAKE = {"S13b": 0.35, "S16b": 0.3, "S18": 0.25, "S14a": 0.2, "S21": 0.25}


def ease(t):
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- captions (one word at a time)
DISPLAY = {"fuck": "f*ck", "view.": "Vi3W.", "view": "Vi3W"}
WORDS = []
for l in M["lines"]:
    ws = l["words"]
    for i, (txt, s, e) in enumerate(ws):
        nxt = ws[i + 1][1] if i + 1 < len(ws) else e + 0.25
        WORDS.append((s, min(nxt, e + 0.45), DISPLAY.get(txt.lower(), txt)))
CAPF = ImageFont.truetype(FONT, 104)


def caption(frame, t):
    for s, e, txt in WORDS:
        if s <= t < e:
            d = ImageDraw.Draw(frame)
            k = min(1.0, (t - s) / 0.07)              # quick pop
            f = CAPF if k >= 1 else ImageFont.truetype(FONT, int(104 * (0.8 + 0.2 * k)))
            tw = d.textlength(txt, font=f)
            d.text(((W - tw) / 2, 1180), txt, font=f, fill="white", stroke_width=11, stroke_fill="black")
            return


# ---------------------------------------------------------------- render
def main():
    plates, card = {}, None
    for _, n in SHOTS:
        if n == "VI3W":
            card = vi3w_card()
        elif n not in plates:
            plates[n] = plate(n)
    n_frames = int(STORY_END * FPS)
    story = OUT / "story_video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(story)],
                          stdin=subprocess.PIPE)
    starts = [s for s, _ in SHOTS] + [STORY_END]
    for fi in range(n_frames):
        t = fi / FPS
        k = max(i for i, (s, _) in enumerate(SHOTS) if s <= t)
        s0, name = SHOTS[k]
        s1 = starts[k + 1]
        u = (t - s0) / max(0.01, s1 - s0)
        if name == "VI3W":
            idx = min(2, int((t - s0) / ((s1 - s0) / 3)))
            fr = card[idx].copy()
            zt = 1 + 0.04 * u
            fr = fr.resize((int(W * zt), int(H * zt)), Image.BILINEAR).crop((int((W * zt - W) / 2), int((H * zt - H) / 2), int((W * zt - W) / 2) + W, int((H * zt - H) / 2) + H))
        else:
            big = plates[name]
            z = 1.0 + 0.07 * ease(u)                    # slow push-in
            if name in PUNCH:
                z += 0.10 * max(0.0, 1 - (t - s0) / 0.22)
            sc = z / 1.12
            cw, ch = W / sc * (1.0), H / sc
            cw, ch = min(cw, big.width), min(ch, big.height)
            ox, oy = (big.width - cw) / 2, (big.height - ch) / 2
            amp = SHAKE.get(name, 0) * max(0.0, 1 - (t - s0) / 0.5) * 40
            ox += amp * math.sin(t * 90); oy += amp * math.cos(t * 77)
            ox, oy = max(0, min(big.width - cw, ox)), max(0, min(big.height - ch, oy))
            fr = big.resize((W, H), Image.BILINEAR, box=(ox, oy, ox + cw, oy + ch))
            if name == "S10a":                           # Blender-style info toast
                d = ImageDraw.Draw(fr)
                f = ImageFont.truetype(FONT, 52)
                d.rounded_rectangle((170, 760, 910, 860), 18, fill=(30, 30, 30), outline=(255, 160, 40), width=4)
                d.text((205, 783), "Deleted 1 object(s): Cube", font=f, fill=(235, 235, 235))
        # 3-frame white flash on the giant-cube reveal and the robot reveal
        if name in ("S13b", "S20+robot") and t - s0 < 0.1:
            fr = Image.blend(fr, Image.new("RGB", (W, H), "white"), 0.55 * (1 - (t - s0) / 0.1))
        caption(fr, t)
        ff.stdin.write(fr.tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{n_frames}", flush=True)
    ff.stdin.close(); ff.wait()

    # ---- video: story + outro
    full_v = OUT / "full_video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(story), "-i", str(OUTRO), "-filter_complex",
                    "[0:v]fps=30,format=yuv420p,setsar=1[a];[1:v]scale=1080:1920,fps=30,format=yuv420p,setsar=1[b];[a][b]concat=n=2:v=1:a=0[v]",
                    "-map", "[v]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", str(full_v)], check=True)

    # ---- audio: VO + outro VO + music bed + SFX in gaps
    total = STORY_END + OUTRO_META["dur"]
    o_words = M["outro"]["words"]
    url = next((s for wd, s, e in o_words if wd.lower().startswith("view")), 1.9)
    o_at = STORY_END + max(0.05, OUTRO_META["url_at"] - url)
    sfx = [("click.mp3", L["c2"]["end"] + 0.05, 0.9), ("dun.mp3", L["c3"]["end"] + 0.05, 0.8),
           ("gulp.mp3", L["n1"]["end"] + 0.02, 0.7), ("squish.mp3", L["b3"]["end"] + 0.02, 0.9),
           ("grow.mp3", L["v1"]["end"] + 0.02, 0.6)]
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(OUT / "vo/story.wav"), "-i", str(OUT / "vo/outro.wav"),
           "-stream_loop", "-1", "-i", str(MUSIC)]
    for f, _, _ in sfx:
        cmd += ["-i", str(SFXD / f)]
    fc = [f"[0:a]aresample=48000,loudnorm=I=-15:TP=-1.5:LRA=9,apad=whole_dur={total:.2f},asplit=2[vo][sc]",
          f"[1:a]aresample=48000,loudnorm=I=-15:TP=-1.5,adelay={int(o_at*1000)}|{int(o_at*1000)}[ovo]",
          f"[2:a]aresample=48000,atrim=0:{total:.2f},volume=0.22,afade=t=out:st={total-1.2:.2f}:d=1.2[mus]",
          "[mus][sc]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=350[ducked]"]
    mix = ["[vo]", "[ovo]", "[ducked]"]
    for i, (f, at, vol) in enumerate(sfx):
        fc.append(f"[{3+i}:a]aresample=48000,volume={vol},adelay={int(at*1000)}|{int(at*1000)}[s{i}]")
        mix.append(f"[s{i}]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total:.2f},alimiter=limit=0.95[a]")
    audio = OUT / "mix.wav"
    subprocess.run(cmd + ["-filter_complex", ";".join(fc), "-map", "[a]", "-ac", "2", str(audio)], check=True)

    final = OUT / "blender-first-time.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full_v), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    print("done", final)


if __name__ == "__main__":
    main()
