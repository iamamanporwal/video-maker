"""TV screen UI plates (generic console dashboard, GTA VI key art logo) → tex/tv_*.png. Run with the repo venv (PIL)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(PROJ, "..", "..", ".."))
LOGO = os.path.join(ROOT, "projects/shorts/gta6-billion/public/logos/gta6_logo.png")
W, H = 1920, 1080
def font(sz, bold=True):
    for p, i in (("/System/Library/Fonts/HelveticaNeue.ttc", 1 if bold else 0), ("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0)):
        try: return ImageFont.truetype(p, sz, index=i)
        except Exception: pass
    return ImageFont.load_default()
def base(tint):
    im = Image.new("RGB", (W, H), (4, 6, 14)); d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(c * (0.25 + 0.75 * (1 - k)) ) for c in tint))
    glow = Image.new("RGB", (W, H), (0, 0, 0)); g = ImageDraw.Draw(glow)
    g.ellipse([W//2 - 520, 40, W//2 + 520, 760], fill=tuple(int(c * 1.6) for c in tint))
    im = Image.blend(im, Image.composite(glow.filter(ImageFilter.GaussianBlur(160)), im, Image.new("L", (W, H), 150)), 0.6)
    lg = Image.open(LOGO).convert("RGBA"); s = 400 / lg.width; lg = lg.resize((400, int(lg.height * s)))
    im.paste(lg, (W//2 - 200, 110), lg)
    return im, ImageDraw.Draw(im), 110 + lg.height
def ctext(d, y, txt, sz, fill=(255, 255, 255), bold=True):
    f = font(sz, bold); w = d.textlength(txt, font=f); d.text((W/2 - w/2, y), txt, font=f, fill=fill)
def bar(d, y, frac=0.0, col=(60, 150, 255)):
    x0, x1 = W//2 - 330, W//2 + 330
    d.rounded_rectangle([x0, y, x1, y + 26], 13, fill=(40, 46, 62))
    if frac > 0: d.rounded_rectangle([x0, y, x0 + int((x1 - x0) * frac), y + 26], 13, fill=col)
def lock(d, cx, cy, s, col):
    d.arc([cx - s*0.42, cy - s*0.95, cx + s*0.42, cy - s*0.05], 180, 360, fill=col, width=int(s*0.16))
    d.line([cx - s*0.42 + s*0.07, cy - s*0.5, cx - s*0.42 + s*0.07, cy - s*0.1], fill=col, width=int(s*0.16))
    d.line([cx + s*0.42 - s*0.08, cy - s*0.5, cx + s*0.42 - s*0.08, cy - s*0.1], fill=col, width=int(s*0.16))
    d.rounded_rectangle([cx - s*0.6, cy - s*0.2, cx + s*0.6, cy + s*0.7], int(s*0.12), fill=col)
out = os.path.join(PROJ, "tex")
im, d, y = base((16, 30, 70)); ctext(d, y + 40, "Downloading…", 54); ctext(d, y + 118, "212 GB", 120); bar(d, y + 290); ctext(d, y + 345, "Time left: calculating", 36, (170, 185, 215), False); im.save(os.path.join(out, "tv_dl.png"))
im, d, y = base((70, 14, 18)); lock(d, W//2, y + 130, 110, (255, 255, 255)); ctext(d, y + 250, "PRE-LOADED", 84); bar(d, y + 372, 1.0, (235, 60, 60)); ctext(d, y + 425, "Unlocks Nov 19 · 12:00 AM", 44, (255, 200, 200), False); im.save(os.path.join(out, "tv_locked.png"))
im, d, y = base((10, 70, 34)); d.rounded_rectangle([W//2 - 290, y + 90, W//2 + 290, y + 270], 90, fill=(40, 225, 110)); ctext(d, y + 118, "PLAY", 120, (4, 30, 12)); ctext(d, y + 320, "Ready to play", 50, (200, 255, 220), False); im.save(os.path.join(out, "tv_play.png"))
im, d, y = base((74, 40, 6)); ctext(d, y + 40, "Update required", 60); ctext(d, y + 125, "Day-one patch", 92, (255, 190, 60)); bar(d, y + 290); ctext(d, y + 345, "Time left: good luck", 36, (230, 205, 160), False); im.save(os.path.join(out, "tv_patch.png"))
open(os.path.join(out, "bar_y.txt"), "w").write(str(1 - (y + 290 + 13) / H))
print("ui ok", y)
