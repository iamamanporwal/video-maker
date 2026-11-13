"""python scenes/build.py <shot,...> [--stills [fracs]] [--full] [--nobuild]: scene scripts → .blend → stills sheet / public/3d/<shot>.mp4.

Durations come from scenes/dur.json (written by ../build.py from the VO word times); defaults below for look tests.
"""
import json, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(PROJ, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from reelforge.blender.render import BLENDER, render  # noqa: E402

MOD = {"street": "street", "drive": "street", "lodline": "lod", "lod": "lod", "cull": "cull", "reveal": "cull", "stream": "stream", "crowd": "crowd"}
DUR = {k: 4.0 for k in MOD}
DUR["street"] = 7.0
if os.path.exists(os.path.join(HERE, "dur.json")):
    DUR.update(json.load(open(os.path.join(HERE, "dur.json"))))
WORKERS = int(os.environ.get("WORKERS", "3"))
PUB = os.path.join(PROJ, "public", "3d")
WORK = os.path.join(PROJ, "out3d")


def main():
    shots = sys.argv[1].split(",")
    fr = [0.02, 0.5, 0.98]
    if "--stills" in sys.argv:
        i = sys.argv.index("--stills")
        if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--"):
            fr = [float(x) for x in sys.argv[i + 1].split(",")]
    os.makedirs(os.path.join(WORK, "blend"), exist_ok=True)
    sheet = []
    for shot in shots:
        t0 = time.time()
        blend = os.path.join(WORK, "blend", f"{shot}.blend")
        nf = max(2, int(round(DUR[shot] * 30)))
        if "--nobuild" not in sys.argv:
            r = subprocess.run([BLENDER, "-b", "-P", os.path.join(HERE, MOD[shot] + ".py"), "--", shot, blend, str(DUR[shot]), str(DUR.get(shot + "@ev", -1))],
                               capture_output=True, text=True, timeout=900)
            if r.returncode or "SAVED" not in r.stdout:
                print(r.stdout[-5000:], r.stderr[-5000:])
                sys.exit(f"build {shot} failed")
            print(f"{shot}: built in {time.time() - t0:.1f}s ({nf} f)", flush=True)
        if "--stills" in sys.argv:
            out = os.path.join(WORK, "stills", shot)
            shutil.rmtree(out, ignore_errors=True)
            frames = sorted({1 + min(nf - 1, int(round(x * (nf - 1)))) for x in fr})
            dt = render(blend, out, workers=min(WORKERS, len(frames)), stills=frames, scale=50)
            print(f"{shot}: {len(frames)} stills in {dt:.1f}s", flush=True)
            sheet += [os.path.join(out, f"f_{f:04d}.jpg") for f in frames]
        if "--full" in sys.argv:
            out = os.path.join(WORK, "frames", shot)
            shutil.rmtree(out, ignore_errors=True)
            dt = render(blend, out, workers=WORKERS, frames=(1, nf))
            print(f"{shot}: {nf} frames in {dt:.1f}s ({dt / nf:.2f}s/f)", flush=True)
            os.makedirs(PUB, exist_ok=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-start_number", "1", "-i", os.path.join(out, "f_%04d.jpg"),
                            "-frames:v", str(nf), "-vf", "scale=out_range=tv,format=yuv420p", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-crf", "16", "-preset", "medium", "-movflags", "+faststart", os.path.join(PUB, f"{shot}.mp4")], check=True, timeout=600)
    if sheet:
        from PIL import Image
        ims = [Image.open(p) for p in sheet]
        w, h = ims[0].size
        cols = min(6, len(ims))
        rows = -(-len(ims) // cols)
        S = Image.new("RGB", (cols * w, rows * h))
        for i, im in enumerate(ims):
            S.paste(im, ((i % cols) * w, (i // cols) * h))
        if S.width > 2400:
            S = S.resize((2400, int(S.height * 2400 / S.width)))
        p = os.path.join(WORK, f"sheet_{'_'.join(shots)[:60]}.jpg")
        S.save(p, quality=88)
        print("SHEET", p)


if __name__ == "__main__":
    main()
