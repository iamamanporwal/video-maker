"""python out3d_a/build.py <shot,...> [--stills] [--full]: scene.py → .blend → look stills (contact sheet) / full mp4.

  --stills  2 frames per shot at 50 % → out3d_a/stills/<shot>_<f>.jpg + out3d_a/sheet.jpg
  --full    3 workers full-res → out3d_a/frames/<shot>/ → public/3d/<shot>.mp4 (H.264 yuv420p crf 18, no audio)
"""
import os, subprocess, sys, shutil, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from reelforge.blender.render import BLENDER, render

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, "..", "public", "3d")
NF = {"trashcan": 162, "props": 72, "citypull": 66, "pipeline": 132, "florida": 75, "office": 108}
STILLS = {"trashcan": [1, 30, 55, 85, 112, 135, 160], "props": [8, 30, 60], "citypull": [1, 33, 66], "pipeline": [20, 60, 85, 110, 130], "florida": [10, 35, 72], "office": [1, 50, 108]}


def build(shot):
    blend = os.path.join(HERE, "blend", f"{shot}.blend")
    r = subprocess.run([BLENDER, "-b", "-P", os.path.join(HERE, "scene.py"), "--", shot, blend],
                       capture_output=True, text=True, timeout=300)
    if r.returncode or not os.path.exists(blend):
        print(r.stdout[-6000:], r.stderr[-3000:])
        sys.exit(f"build {shot} failed")
    return blend


def main():
    shots = sys.argv[1].split(",")
    if "--only" in sys.argv: STILLS.update({shots[0]: [int(x) for x in sys.argv[sys.argv.index("--only")+1].split(",")]})
    for shot in shots:
        t0 = time.time()
        blend = build(shot)
        print(f"{shot}: built in {time.time() - t0:.1f}s")
        if "--build" in sys.argv: continue
        if "--stills" in sys.argv:
            out = os.path.join(HERE, "stills", shot)
            shutil.rmtree(out, ignore_errors=True)
            dt = render(blend, out, workers=2, stills=STILLS[shot], scale=50)
            print(f"{shot}: stills in {dt:.1f}s")
        if "--full" in sys.argv:
            out = os.path.join(HERE, "frames", shot)
            shutil.rmtree(out, ignore_errors=True)
            dt = render(blend, out, workers=3, frames=(1, NF[shot]))
            print(f"{shot}: {NF[shot]} frames in {dt:.1f}s ({dt / NF[shot]:.2f}s/f)")
            os.makedirs(PUB, exist_ok=True)
            mp4 = os.path.join(PUB, f"{shot}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-start_number", "1",
                            "-i", os.path.join(out, "f_%04d.jpg"), "-vf", "scale=out_range=tv,format=yuv420p", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-color_range", "tv",
                            "-crf", "18", "-preset", "medium", "-an", "-movflags", "+faststart", mp4],
                           check=True, timeout=300)
            print("wrote", mp4)
    if "--stills" in sys.argv:
        files = []
        for shot in shots:
            d = os.path.join(HERE, "stills", shot)
            files += [os.path.join(d, f) for f in sorted(os.listdir(d))]
        sheet = os.path.join(HERE, "sheet_" + "_".join(shots) + ".jpg")
        n = len(files)
        args = []
        for f in files:
            args += ["-i", f]
        flt = "".join(f"[{i}:v]scale=360:640[v{i}];" for i in range(n)) + "".join(f"[v{i}]" for i in range(n)) + \
              f"hstack=inputs={n}" if n > 1 else "[0:v]scale=360:640"
        if n > 8:
            per = -(-n // 2)
            flt = "".join(f"[{i}:v]scale=360:640[v{i}];" for i in range(n)) + "".join(f"[v{i}]" for i in range(per)) + f"hstack=inputs={per}[a];" + "".join(f"[v{i}]" for i in range(per, n)) + (f"hstack=inputs={n-per}[b];" if n - per > 1 else "null[b];") + ("[a][b]vstack" if n - per == per else f"[b]pad={per*360}:640[bb];[a][bb]vstack")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", flt, sheet], check=True, timeout=60)
        print("sheet", sheet)


if __name__ == "__main__":
    main()
