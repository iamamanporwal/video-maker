"""~/models/chatterbox-venv/bin/python assemble.py rec/takeN.mp4 → out/blender-first-time-3d.mp4
Finds the magenta sync marker (viewport rect + T0), crops the Studio viewport to 9:16 (or un-rolls a 90°-rolled camera),
overlays one-word captions + the Vi3W insert + Blender toast, then the shared audio mix (VO, music, SFX) and custom outro."""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import build as B  # caption(), vi3w_card(), W/L, constants

REC = Path(sys.argv[1])
TL = json.loads((D / "studio/timeline.json").read_text())
OUT = D / "out"
W, H, FPS = 1080, 1920, 30


def probe(p):
    s = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                            "stream=width,height", "-of", "json", str(p)]))["streams"][0]
    return s["width"], s["height"]


MARK_TO_T0 = 2.6                                  # Camera.client: magenta ends 2.6 s before T0
GLITCH = set()                                     # frame indices (30 fps) where ScreenCaptureKit delivered a 1x/half frame


def find_marker():
    """scan at 1/4 res, 30 fps: magenta frames → (t_end_of_magenta, bbox of the LARGEST magenta frame); also logs
    half-scale glitch frames (right/bottom quadrant empty) for the whole take."""
    sw, sh = probe(REC)
    w4, h4 = sw // 4, sh // 4
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(REC), "-vf", f"fps={FPS},scale={w4}:{h4}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    last, box, best, i = None, None, 0, 0
    while True:
        buf = p.stdout.read(w4 * h4 * 3)
        if len(buf) < w4 * h4 * 3: break
        a8 = np.frombuffer(buf, np.uint8).reshape(h4, w4, 3)
        if a8[-4:, :].mean() < 3 and a8[:, -4:].mean() < 3: GLITCH.add(i)
        a = a8.astype(int)
        mag = (a[..., 0] > 200) & (a[..., 1] < 70) & (a[..., 2] > 200)
        n = int(mag.sum())
        if n > 0.05 * w4 * h4:
            if n > best and i not in GLITCH:
                ys, xs = np.where(mag)
                box = (xs.min() * 4, ys.min() * 4, (xs.max() + 1) * 4, (ys.max() + 1) * 4); best = n
            last = i
        i += 1
    p.kill()
    if last is None: raise SystemExit("no magenta marker found")
    return (last + 1) / FPS, box


def main():
    t_mag_end, (x0, y0, x1, y1) = find_marker()
    T0 = t_mag_end + MARK_TO_T0
    vw, vh = x1 - x0, y1 - y0
    print(f"marker ends {t_mag_end:.2f}s → T0 {T0:.2f}s; viewport {vw}x{vh} at {x0},{y0}")
    rot = TL.get("roll90") or vw > vh * 1.25          # client rolled the camera 90° on a wide viewport
    end = TL["end"]
    SW, SH = probe(REC)
    # decode FULL frames; per frame, measure the window's real scale (ScreenCaptureKit sometimes hands over a
    # down-scaled window in the top-left with black right/bottom), then crop the viewport at that scale.
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{T0:.3f}", "-i", str(REC), "-t", f"{end:.3f}",
                          "-vf", f"fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    FB = SW * SH * 3

    def grab():
        buf = p.stdout.read(FB)
        if len(buf) < FB: return None
        a = np.frombuffer(buf, np.uint8).reshape(SH, SW, 3)
        col = a[::8, :, :].max(axis=(0, 2)) > 12          # non-black columns
        right = int(np.nonzero(col)[0].max()) + 1 if col.any() else SW
        sc = min(1.0, right / SW)
        if sc > 0.97: sc = 1.0
        bx0, by0, bw, bh = x0 * sc, y0 * sc, vw * sc, vh * sc
        im = Image.fromarray(a[int(by0):int(by0 + bh), int(bx0):int(bx0 + bw)])
        if rot: im = im.transpose(Image.ROTATE_90)
        cw, ch = im.size
        tw = min(cw, int(ch * 9 / 16)); th = int(tw * 16 / 9)
        l, t_ = (cw - tw) // 2, (ch - th) // 2
        return im.crop((l, t_, l + tw, t_ + th)).resize((W, H), Image.LANCZOS), sc
    story = OUT / "story3d_video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(story)],
                           stdin=subprocess.PIPE)
    shots = TL["shots"]
    vi = next(s for s in shots if s["id"] == "VI3W")
    vi_end = next(s["t"] for s in shots if s["t"] > vi["t"])
    s10 = next(s for s in shots if s["id"] == "S10a")
    card = B.vi3w_card()
    toastf = ImageFont.truetype(B.FONT, 52)
    n = int(end * FPS)
    for fi in range(n):
        g = grab()
        if g is None: break
        fr, sc = g
        if sc < 1.0: nglitch = locals().get("nglitch", 0) + 1
        t = fi / FPS
        if vi["t"] <= t < vi_end:
            k = min(2, int((t - vi["t"]) / ((vi_end - vi["t"]) / 3)))
            fr = card[k].copy()
        if s10["t"] <= t < s10["t"] + 1.1 and t - s10["t"] > 0.4:
            d = ImageDraw.Draw(fr)
            d.rounded_rectangle((170, 300, 910, 400), 18, fill=(30, 30, 30), outline=(255, 160, 40), width=4)
            d.text((205, 323), "Deleted 1 object(s): Cube", font=toastf, fill=(235, 235, 235))
        B.caption(fr, t)
        enc.stdin.write(fr.tobytes())
        if fi % 300 == 0: print("frame", fi, "/", n, flush=True)
    enc.stdin.close(); enc.wait(); p.kill()

    # reuse the 2D build's outro concat + audio mix by pointing it at this story
    full_v = OUT / "full3d_video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(story), "-i", str(B.OUTRO), "-filter_complex",
                    "[0:v]fps=30,format=yuv420p,setsar=1[a];[1:v]scale=1080:1920,fps=30,format=yuv420p,setsar=1[b];[a][b]concat=n=2:v=1:a=0[v]",
                    "-map", "[v]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", str(full_v)], check=True)
    audio = OUT / "mix.wav"          # produced by build.py (same VO/music/SFX timeline, story length end)
    final = OUT / "blender-first-time-3d.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full_v), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    print("done", final)


if __name__ == "__main__":
    main()
