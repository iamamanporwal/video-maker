"""Motion clips from stills for the roblox-anime shorts (ffmpeg zoompan), plus the quest-panel overlay (Pillow).
Run from the repo root: python3 projects/shorts/roblox-anime/gen/make_stills.py"""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

G = Path(__file__).parent
L = Path("projects/launch/one-sketch-away/assets")
IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
ARIAL = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def fit_916(src: Path, bg="white") -> Image.Image:
    """Letterbox any image into 1080x1920 (contain), on a blurred copy of itself for photos or flat colour."""
    im = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", (1080, 1920), bg)
    s = min(1000 / im.width, 1500 / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    canvas.paste(im, ((1080 - im.width) // 2, (1920 - im.height) // 2))
    return canvas


def kenburns(img: Image.Image, out: Path, secs: float, z0=1.0, z1=1.12, shake=0):
    tmp = out.with_suffix(".src.png")
    img.save(tmp)
    n = round(secs * 30)
    # zoompan on a 2x upscale for smooth sub-pixel motion; optional jitter for "anime impact" shake
    jx = f"+{shake}*sin(on*2.1)" if shake else ""
    jy = f"+{shake}*cos(on*1.7)" if shake else ""
    vf = (f"scale=2160:3840,zoompan=z='{z0}+({z1}-{z0})*on/{n}':d={n}:s=1080x1920:fps=30:"
          f"x='iw/2-(iw/zoom/2){jx}':y='ih/2-(ih/zoom/2){jy}',format=yuv420p")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(tmp), "-vf", vf, "-frames:v", str(n),
                    "-c:v", "libx264", "-crf", "16", "-an", str(out)], check=True)
    tmp.unlink()


def quest_panel() -> Image.Image:
    base = Image.open(G / "npc.png").convert("RGB").resize((1080, 1890), Image.LANCZOS)
    canvas = Image.new("RGB", (1080, 1920), "black")
    canvas.paste(base, (0, 15))
    d = ImageDraw.Draw(canvas, "RGBA")
    x0, y0, x1, y1 = 70, 1180, 1010, 1640
    d.rounded_rectangle((x0, y0, x1, y1), 34, fill=(18, 14, 40, 235), outline=(255, 214, 64, 255), width=8)
    d.text((540, y0 + 70), "NEW QUEST!", font=ImageFont.truetype(IMPACT, 92), fill=(255, 214, 64), anchor="mm")
    f = ImageFont.truetype(ARIAL, 50)
    d.text((540, y0 + 190), "Get a 3D sea monster", font=f, fill="white", anchor="mm")
    d.text((540, y0 + 255), "for your game", font=f, fill="white", anchor="mm")
    d.text((540, y0 + 365), "REWARD: 0 Robux", font=ImageFont.truetype(IMPACT, 70), fill=(255, 90, 90), anchor="mm")
    return canvas


if __name__ == "__main__":
    kenburns(fit_916(L / "sneaker-sketch.png"), G / "sneaker-sketch.mp4", 2.6, 1.0, 1.10, shake=6)
    kenburns(fit_916(L / "robot-drawing.png", bg="#d9cbb3"), G / "robot-drawing.mp4", 2.4, 1.0, 1.08)
    kenburns(quest_panel(), G / "npc-quest.mp4", 3.6, 1.0, 1.06)
    kenburns(fit_916(G / "npc.png"), G / "npc-still.mp4", 0.5)
    print("ok")
