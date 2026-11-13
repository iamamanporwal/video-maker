"""python out3d_a/build.py <shot,...> [--stills] [--full] [--build]: scene.py → .blend → stills sheet / mp4.

Shots carry a pre-roll (scene PRE frames, so particles are already flying at shot frame 1). Rendered range is
PRE+1 .. PRE+NF; stills are given in shot seconds.
  --stills  frames at 50 % → out3d_a/stills/<shot>/ + out3d_a/sheet_<shots>.jpg
  --full    3 workers full-res → out3d_a/frames/<shot>/ → public/3d/<shot>.mp4 (H.264 yuv420p crf 18, no audio)
"""
import json, os, shutil, subprocess, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from reelforge.blender.render import BLENDER, render

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, "..", "public", "3d")
DUR = {"rocket": 4.8, "cashrain": 6.0, "vault": 4.6, "printer": 5.9}
PRE = {"rocket": 40, "cashrain": 240, "vault": 20, "printer": 90}
STILLS = {"rocket": [0.0, 1.5, 3.0, 3.4, 4.6], "cashrain": [0.0, 3.0, 5.9], "vault": [0.0, 1.0, 1.4, 2.4, 3.4, 4.5],
          "printer": [0.0, 2.5, 5.8]}
WORKERS = int(os.environ.get("WORKERS", "3"))


def build(shot):
    blend = os.path.join(HERE, "blend", f"{shot}.blend")
    r = subprocess.run([BLENDER, "-b", "-P", os.path.join(HERE, "scene.py"), "--", shot, blend],
                       capture_output=True, text=True, timeout=900)
    if r.returncode or not os.path.exists(blend) or "SAVED" not in r.stdout:
        print(r.stdout[-6000:], r.stderr[-3000:])
        sys.exit(f"build {shot} failed")
    return blend


def main():
    shots = sys.argv[1].split(",")
    if "--only" in sys.argv:
        STILLS[shots[0]] = [float(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")]
    for shot in shots:
        t0 = time.time()
        blend = os.path.join(HERE, "blend", f"{shot}.blend")
        if "--nobuild" not in sys.argv:
            blend = build(shot)
            print(f"{shot}: built in {time.time() - t0:.1f}s", flush=True)
        if "--build" in sys.argv:
            continue
        nf, pre = int(round(DUR[shot] * 30)), PRE[shot]
        if "--stills" in sys.argv:
            out = os.path.join(HERE, "stills", shot)
            shutil.rmtree(out, ignore_errors=True)
            fr = [pre + 1 + min(nf - 1, int(round(s * 30))) for s in STILLS[shot]]
            dt = render(blend, out, workers=min(WORKERS, len(fr)), stills=fr, scale=50)
            print(f"{shot}: stills in {dt:.1f}s", flush=True)
        if "--full" in sys.argv:
            out = os.path.join(HERE, "frames", shot)
            shutil.rmtree(out, ignore_errors=True)
            dt = render(blend, out, workers=WORKERS, frames=(pre + 1, pre + nf))
            print(f"{shot}: {nf} frames in {dt:.1f}s ({dt / nf:.2f}s/f)", flush=True)
            os.makedirs(PUB, exist_ok=True)
            mp4 = os.path.join(PUB, f"{shot}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-start_number", str(pre + 1),
                            "-i", os.path.join(out, "f_%04d.jpg"), "-frames:v", str(nf),
                            "-vf", "scale=out_range=tv,format=yuv420p", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-color_range", "tv", "-crf", "18", "-preset", "medium", "-an", "-movflags", "+faststart", mp4],
                           check=True, timeout=300)
            json.dump([[shot, 1, nf]], open(os.path.join(out, "shots.json"), "w"))
            print("wrote", mp4, flush=True)
    if "--stills" in sys.argv:
        files = []
        for shot in shots:
            d = os.path.join(HERE, "stills", shot)
            files += [os.path.join(d, f) for f in sorted(os.listdir(d))]
        sheet = os.path.join(HERE, "sheet_" + "_".join(shots) + ".jpg")
        args = []
        for f in files:
            args += ["-i", f]
        n = len(files)
        flt = "".join(f"[{i}:v]scale=360:640[v{i}];" for i in range(n)) + "".join(f"[v{i}]" for i in range(n)) + \
            f"hstack=inputs={n}" if n > 1 else "[0:v]scale=360:640"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", flt, sheet], check=True, timeout=60)
        print("sheet", sheet)


if __name__ == "__main__":
    main()
