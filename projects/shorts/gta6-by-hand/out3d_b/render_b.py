"""Render agent-B shots. Plain python (repo .venv), drives background Blenders.

    render_b.py stills [--scale 50] [--only rig,npcs]     → stills/<shot>_<t>.jpg + stills/sheet_<shot>.jpg
    render_b.py full [--only ...] [--workers 3]           → frames/<shot>/f_####.jpg → ../public/3d/<shot>.mp4
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "src"))
from reelforge.blender.render import BLENDER

BLEND = os.path.join(HERE, "scene.blend")
SHOTS = json.load(open(os.path.join(HERE, "shots.json")))     # [shot, scene, f0, f1]
PUB = os.path.abspath(os.path.join(HERE, "..", "public", "3d"))
DUR = {"npcs": 4.3, "rig": 3.5, "animate": 3.5, "cycles": 5.3, "fallthrough": 3.2, "bugs": 2.4, "lonely": 2.1}
STILLS = {"npcs": [0.3, 1.4, 2.3, 3.6], "rig": [0.8, 1.9], "animate": [0.6, 2.3, 3.2], "cycles": [0.3, 0.9, 1.5, 2.3, 3.8],
          "fallthrough": [0.5, 1.8, 2.8], "bugs": [0.15, 1.6], "lonely": [0.2, 1.9]}

PY = """
import bpy, json, sys
a = sys.argv[sys.argv.index('--') + 1:]
scale, jobs = int(a[0]), json.loads(a[1])
for scn, f0, f1, pat in jobs:
    s = bpy.data.scenes[scn]
    s.frame_start, s.frame_end, s.frame_step = f0, f1, 1
    s.render.resolution_percentage = scale
    s.render.filepath = pat
    bpy.ops.render.render(animation=True, scene=scn)
"""


def run(jobs, workers, scale, timeout):
    bins, load = [[] for _ in range(workers)], [0] * workers
    for j in sorted(jobs, key=lambda x: x[1] - x[2]):
        i = load.index(min(load))
        bins[i].append(j)
        load[i] += j[2] - j[1] + 1
    t0 = time.time()
    procs = [subprocess.Popen([BLENDER, "-b", BLEND, "--python-expr", PY, "--", str(scale), json.dumps(b)],
                              stdout=open(os.path.join(HERE, f"log_w{i}.txt"), "w"), stderr=subprocess.STDOUT)
             for i, b in enumerate(bins) if b]
    for p in procs:
        try:
            p.wait(timeout=max(1, timeout - (time.time() - t0)))
        except subprocess.TimeoutExpired:
            p.kill()
            print("TIMEOUT: killed worker")
    print(f"rendered in {time.time() - t0:.1f}s", [p.returncode for p in procs])


def scene_for(shot, f):
    for s, scn, f0, f1 in SHOTS:
        if s == shot and f0 <= f <= f1:
            return scn, f0
    return None, None


def shot_start(shot):
    return min(f0 for s, _, f0, _ in SHOTS if s == shot)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode")
    ap.add_argument("--only")
    ap.add_argument("--scale", type=int, default=50)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--chunk", type=int, default=24)
    a = ap.parse_args()
    only = a.only.split(",") if a.only else list(DUR)
    if a.mode == "stills":
        d = os.path.join(HERE, "stills")
        os.makedirs(d, exist_ok=True)
        jobs = []
        for shot in only:
            st = shot_start(shot)
            for t in STILLS[shot]:
                f = st + int(round(t * 30))
                scn, _ = scene_for(shot, f)
                jobs.append((scn, f, f, os.path.join(d, f"{shot}_{t}_####")))
        run(jobs, a.workers, a.scale, a.timeout)
        from PIL import Image
        for shot in only:
            ims = [Image.open(os.path.join(d, f"{shot}_{t}_{shot_start(shot) + int(round(t * 30)):04d}.jpg"))
                   for t in STILLS[shot]]
            w, h = ims[0].size
            sheet = Image.new("RGB", (w * len(ims), h))
            for i, im in enumerate(ims):
                sheet.paste(im, (i * w, 0))
            sheet.save(os.path.join(d, f"sheet_{shot}.jpg"), quality=85)
    else:
        jobs = []
        for shot in only:
            od = os.path.join(HERE, "frames", shot)
            os.makedirs(od, exist_ok=True)
            for s, scn, f0, f1 in SHOTS:
                if s != shot:
                    continue
                for c0 in range(f0, f1 + 1, a.chunk):
                    jobs.append((scn, c0, min(c0 + a.chunk - 1, f1), os.path.join(od, "f_####")))
        run(jobs, a.workers, a.scale, a.timeout)
        os.makedirs(PUB, exist_ok=True)
        for shot in only:
            od = os.path.join(HERE, "frames", shot)
            n = int(round(DUR[shot] * 30))
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-start_number", str(shot_start(shot)),
                   "-i", os.path.join(od, "f_%04d.jpg"), "-frames:v", str(n), "-vf", "scale=1080:1920:out_range=tv,format=yuv420p",
                   "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an", os.path.join(PUB, f"{shot}.mp4")]
            subprocess.run(cmd, check=False)
            print("wrote", shot)
