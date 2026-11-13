"""python tex.py: PIL textures for scene.py + 2D HUD overlays for build.py."""
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).resolve().parent
OUT = D / "out" / "tex"
OV = D / "out" / "ov"
SUP = "/System/Library/Fonts/Supplemental/"
COMIC, ARIAL, IMPACT, MARKER = SUP + "Comic Sans MS Bold.ttf", SUP + "Arial Bold.ttf", SUP + "Impact.ttf", "/System/Library/Fonts/MarkerFelt.ttc"
F = lambda p, s: ImageFont.truetype(p, s)
random.seed(4)


def centered(d, y, text, font, fill, w, **kw):
    d.text(((w - d.textlength(text, font=font)) / 2, y), text, font=font, fill=fill, **kw)


def calendar():
    w, h = 600, 700
    im = Image.new("RGB", (w, h), "#fbfbf6")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 170), fill="#d62828")
    centered(d, 25, "NOVEMBER", F(IMPACT, 120), "white", w)
    centered(d, 190, "19", F(IMPACT, 380), "#111111", w)
    centered(d, 600, "PS5  +  XBOX  ONLY", F(ARIAL, 52), "#d62828", w)
    im.save(OUT / "calendar.png")


def page(n):
    w, h = 300, 360
    im = Image.new("RGB", (w, h), "#fbfbf6")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 80), fill="#3a86ff")
    centered(d, 10, "MONTH", F(IMPACT, 56), "white", w)
    centered(d, 100, str(n), F(IMPACT, 200), "#111111", w)
    im.save(OUT / f"page_{n:02d}.png")


def waiting_screen():
    w, h = 800, 500
    im = Image.new("RGB", (w, h), "#101018")
    d = ImageDraw.Draw(im)
    centered(d, 70, "GTA V  —  PC", F(IMPACT, 110), "#ffffff", w)
    centered(d, 220, "COMING SOON...", F(ARIAL, 70), "#ffcc00", w)
    d.rectangle((90, 350, w - 90, 400), outline="#888888", width=5)
    d.rectangle((96, 356, 140, 394), fill="#3dff6a")
    centered(d, 420, "1%", F(ARIAL, 44), "#aaaaaa", w)
    im.save(OUT / "waiting.png")


def card(name, text, bg="#fff8a6", size=70, font=MARKER, rot=0, sketch=None):
    w, h = 360, 280
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        centered(d, 40 + i * (size + 10) + (60 if len(lines) == 1 else 0), ln, F(font, size), "#1a1a1a", w)
    if sketch == "cow":
        d.ellipse((230, 170, 330, 240), outline="#1a1a1a", width=5)
        d.ellipse((250, 185, 275, 205), fill="#1a1a1a")
    im.save(OUT / f"card_{name}.png")


def server_label():
    w, h = 600, 160
    im = Image.new("RGB", (w, h), "#111111")
    d = ImageDraw.Draw(im)
    centered(d, 20, "THE INTERNET", F(IMPACT, 110), "#ffffff", w)
    im.save(OUT / "internet.png")


def disc():
    s = 256
    im = Image.new("RGB", (s, s), "#c0c0c0")
    d = ImageDraw.Draw(im)
    for k in range(60):
        a0 = k * 6
        hue = [(255, 80, 200), (80, 200, 255), (255, 230, 80), (120, 255, 140)][k % 4]
        d.pieslice((0, 0, s, s), a0, a0 + 6, fill=hue)
    d.ellipse((s / 2 - 30, s / 2 - 30, s / 2 + 30, s / 2 + 30), fill="#e0e0e0")
    centered(d, 70, "VI", F(IMPACT, 90), "#ffffff", s, stroke_width=4, stroke_fill="#ff2d95")
    im.save(OUT / "disc.png")


def hud(name, text, sub=None, color="#ffffff"):
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    centered(d, 190, text, F(IMPACT, 130), color, 1080, stroke_width=8, stroke_fill="black")
    if sub:
        centered(d, 340, sub, F(ARIAL, 52), "#ffcc00", 1080, stroke_width=5, stroke_fill="black")
    im.save(OV / f"hud_{name}.png")


def credit():
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((36, 110), "mods footage: RADAL (YouTube)", font=F(ARIAL, 34), fill="#ffffff", stroke_width=3, stroke_fill="black")
    im.save(OV / "credit.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    OV.mkdir(parents=True, exist_ok=True)
    calendar()
    for n in range(1, 20):
        page(n)
    waiting_screen()
    card("pc", "PC??", size=110)
    card("mods", "MODS", bg="#ffd6e7", size=110)
    card("cows", "COWS?!", bg="#d6f5ff", size=96, sketch="cow")
    card("toilet", "TOILET\nCARS", bg="#fff8a6", size=80)
    card("day1", "DAY 1", bg="#e3ffd6", size=110)
    card("nopc", "NO PC\nWHY???", bg="#ffffff", size=80)
    server_label()
    disc()
    hud("day1", "DAY 1", "GTA 6 on PC")
    for h in (1, 3, 6, 9):
        hud(f"h{h}", f"HOUR {h}")
    for n in range(1, 20):
        hud(f"m{n:02d}", f"MONTH {n}", color="#ffffff" if n < 19 else "#ff3b3b")
    credit()
    print("ok")
