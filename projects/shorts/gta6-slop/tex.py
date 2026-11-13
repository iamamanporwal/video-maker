"""python tex.py: PIL textures for scene.py (screens, phone comment, map, tablet, perfume label, crayon fills)
+ 2D stamp overlays for build.py. All text is fake UI; commenter handle is invented (@SlopHater_69)."""
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = Path(__file__).resolve().parent
OUT = D / "out" / "tex"
SUP = "/System/Library/Fonts/Supplemental/"
COMIC, ARIAL, IMPACT = SUP + "Comic Sans MS Bold.ttf", SUP + "Arial Bold.ttf", SUP + "Impact.ttf"
F = lambda p, s: ImageFont.truetype(p, s)
random.seed(3)


def centered(d, y, text, font, fill, w):
    d.text(((w - d.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)


def chat(name, user, reply=None, reply_bad=False, header="Claude Opus 5.5", bar=False, regen=False):
    """Monitor screen, 16:10, 800x500. Huge text so it survives the 360 px PS2 render."""
    w, h = 800, 500
    im = Image.new("RGB", (w, h), "#1b1b22")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 70), fill="#2a2a35")
    d.text((24, 12), header, font=F(ARIAL, 40), fill="#f0a070")
    d.rounded_rectangle((120, 100, w - 30, 210), 30, fill="#3d5afe")
    d.text((150, 120), user, font=F(COMIC, 56), fill="white")
    if reply:
        d.rounded_rectangle((30, 240, w - 120, 360), 30, fill="#d32f2f" if reply_bad else "#33333f",
                            outline="#ff5252" if reply_bad else None, width=6)
        d.text((60, 262), reply, font=F(ARIAL, 52), fill="white")
    if bar:
        d.text((40, 250), "generating...", font=F(COMIC, 48), fill="#cccccc")
        d.rectangle((40, 330, w - 40, 380), outline="#888888", width=4)   # fill bar is a 3D object over this
    if regen:
        d.rounded_rectangle((180, 380, w - 180, 470), 40, fill="#ffffff")
        centered(d, 395, "Regenerate", F(ARIAL, 56), "#111111", w)
        d.text((40, 245), "here's ur son:", font=F(COMIC, 48), fill="#cccccc")
    im.save(OUT / f"{name}.png")


def phone_comment():
    w, h = 540, 1080
    im = Image.new("RGB", (w, h), "#0f0f0f")
    d = ImageDraw.Draw(im)
    d.text((30, 40), "Comments  1.2K", font=F(ARIAL, 40), fill="white")
    d.line((0, 110, w, 110), fill="#333333", width=3)
    y = 380
    d.ellipse((30, y, 130, y + 100), fill="#7e57c2")
    d.text((62, y + 18), "S", font=F(ARIAL, 56), fill="white")
    d.text((150, y), "@SlopHater_69", font=F(ARIAL, 36), fill="#aaaaaa")
    d.text((150, y + 55), "ur ai slop", font=F(ARIAL, 60), fill="white")
    d.text((150, y + 130), "bores me", font=F(ARIAL, 60), fill="white")
    d.text((150, y + 220), "3 likes   Reply", font=F(ARIAL, 32), fill="#aaaaaa")
    for k, (yy, wd) in enumerate(((180, 380), (230, 300), (760, 400), (810, 260), (900, 420), (950, 330))):
        d.rounded_rectangle((150, yy, 150 + wd, yy + 26), 13, fill="#262626")
        if k in (0, 2, 4):
            d.ellipse((30, yy - 10, 130, yy + 90), fill="#262626")
    im.save(OUT / "comment.png")


def crayon(name, base, n=900):
    """Scribbly crayon fill: base colour + darker/lighter diagonal strokes, visible paper gaps."""
    w = h = 256
    im = Image.new("RGB", (w, h), "#f6f1e4")
    d = ImageDraw.Draw(im)
    r, g, b = (int(base[i:i + 2], 16) for i in (1, 3, 5))
    for _ in range(n):
        x, y = random.uniform(-40, w), random.uniform(-40, h)
        k = random.uniform(0.8, 1.15)
        c = tuple(max(0, min(255, int(v * k))) for v in (r, g, b))
        d.line((x, y, x + random.uniform(20, 70), y + random.uniform(10, 40)), fill=c, width=random.randint(3, 7))
    im.save(OUT / f"cr_{name}.png")


def sun_face():
    w = h = 512
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(14):                                   # wobbly rays
        import math
        a = k / 14 * 2 * math.pi
        d.line((256 + 150 * math.cos(a), 256 + 150 * math.sin(a), 256 + 245 * math.cos(a + 0.1), 256 + 245 * math.sin(a + 0.1)),
               fill="#ffb300", width=16)
    d.ellipse((90, 95, 420, 420), fill="#ffd600", outline="#ff8f00", width=10)
    d.ellipse((175, 190, 215, 245), fill="#222222")
    d.ellipse((290, 185, 330, 240), fill="#222222")
    d.arc((170, 220, 340, 360), 20, 160, fill="#222222", width=14)
    d.ellipse((140, 270, 185, 300), fill="#ff8a80")
    d.ellipse((330, 265, 375, 295), fill="#ff8a80")
    im.save(OUT / "sun.png")


def map_tex():
    w = h = 1024
    im = Image.new("RGB", (w, h), "#4fa3e0")
    d = ImageDraw.Draw(im)
    for _ in range(400):
        x, y = random.uniform(0, w), random.uniform(0, h)
        d.line((x, y, x + 40, y + 6), fill="#5fb3ec", width=4)
    pts = [(380, 120), (560, 100), (640, 260), (600, 420), (660, 600), (720, 820), (640, 900), (560, 760), (470, 600),
           (430, 420), (360, 300)]
    d.polygon(pts, fill="#7cc35a", outline="#3e7a2a")
    d.ellipse((620, 820, 700, 880), fill="#7cc35a")
    d.text((420, 330), "VICE", font=F(COMIC, 64), fill="#2e5e1e")
    d.text((420, 400), "CITY", font=F(COMIC, 64), fill="#2e5e1e")
    d.text((60, 60), "THE MAP", font=F(COMIC, 80), fill="white")
    im.save(OUT / "map.png")


def tablet():
    w, h = 600, 800
    im = Image.new("RGB", (w, h), "#8d8a83")
    d = ImageDraw.Draw(im)
    for _ in range(3000):
        x, y = random.uniform(0, w), random.uniform(0, h)
        c = random.choice(("#7a776f", "#9d9a92", "#6c6962", "#a8a59d"))
        d.ellipse((x, y, x + random.uniform(2, 9), y + random.uniform(2, 9)), fill=c)
    font = F(IMPACT, 96)
    for i, line in enumerate(("PROMPT #1:", "MAKE ME", "A HORSE")):
        y = 140 + i * 170
        centered(d, y + 5, line, font, "#c8c5bd", w)        # carved: light lip below, dark groove on top
        centered(d, y, line, font, "#3a3833", w)
    d.text((40, 700), "~ 3000 BC", font=F(COMIC, 44), fill="#3a3833")
    im.save(OUT / "tablet.png")


def label():
    w, h = 400, 400
    im = Image.new("RGB", (w, h), "#1a1020")
    d = ImageDraw.Draw(im)
    d.rectangle((10, 10, w - 10, h - 10), outline="#d4af37", width=8)
    centered(d, 70, "OPUS", F("/System/Library/Fonts/Supplemental/Didot.ttc" if Path(SUP + "Didot.ttc").exists()
                                else ARIAL, 110), "#d4af37", w)
    centered(d, 200, "5.5", F(ARIAL, 90), "#f5e6b0", w)
    centered(d, 310, "eau de prompt", F(COMIC, 34), "#d4af37", w)
    im.save(OUT / "label.png")


def stamp(name, text, color, size=150, rot=-12):
    """2D overlay (1080x1920 RGBA) — rubber stamp with border."""
    font = F(IMPACT, size)
    tmp = Image.new("RGBA", (1000, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    tw = d.textlength(text, font=font)
    x0 = (1000 - tw) / 2
    d.rectangle((x0 - 30, 60, x0 + tw + 30, 120 + size), outline=color, width=16)
    d.text((x0, 70), text, font=font, fill=color)
    tmp = tmp.rotate(rot, resample=Image.BICUBIC, expand=False)
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    im.alpha_composite(tmp, (40, 560))
    im.save(D / "out" / f"stamp_{name}.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    chat("scr_gta", "make GTA 6. no bugs", bar=True)
    chat("scr_mom", "generate ur mom")
    chat("scr_refuse", "generate ur mom", reply="I can't help with that.", reply_bad=True)
    chat("scr_son", "make me a son")
    chat("scr_regen", "make me a son", regen=True)
    phone_comment()
    for n, c in (("pink", "#ff6fb5"), ("teal", "#2ec4b6"), ("orange", "#ff9f1c"), ("purple", "#9b5de5"), ("yellow", "#fee440"),
                 ("green", "#57cc04"), ("brown", "#8d5524"), ("road", "#55555f"), ("sky", "#ff9ec7"), ("sand", "#f4d58d"),
                 ("blue", "#3a86ff"), ("red", "#e63946")):
        crayon(n, c)
    sun_face()
    map_tex()
    tablet()
    label()
    stamp("delayed", "DELAYED", (230, 30, 30, 255))
    stamp("skill", "SKILL ISSUE", (230, 30, 30, 255), size=130)
    print("ok", len(list(OUT.glob("*.png"))))
