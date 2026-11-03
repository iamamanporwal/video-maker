"""Parallel EEVEE rendering for director .blend files (plain Python, not inside Blender).

    python -m reelforge.blender.render <scene.blend> <out_dir> [--workers 3] [--frames 1-300] [--step 1]
                                                               [--scale 100] [--stills 1,60,150]

Splits the frame range into `workers` contiguous chunks and renders each in its own background Blender, so
scene sync / shader compile on the CPU overlaps with GPU work. --scale 50 --step 2 is the fast preview pass;
--stills renders just those frames (look checks). Frames land as out_dir/f_####.jpg.
"""
import argparse, os, subprocess, sys, time

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")

# Inline settings applied in every worker before rendering (resolution scale, frame step).
PY = "import bpy,sys; s=bpy.context.scene; a=sys.argv[sys.argv.index('--')+1:]; s.render.resolution_percentage=int(a[0]); s.frame_step=int(a[1])"


def chunks(a, b, n):
    size = -(-(b - a + 1) // n)
    return [(i, min(i + size - 1, b)) for i in range(a, b + 1, size)]


def render(blend, out, workers=3, frames=(1, 300), step=1, scale=100, stills=None, quiet=True):
    os.makedirs(out, exist_ok=True)
    pat = os.path.join(os.path.abspath(out), "f_####")
    jobs = []
    if stills:
        groups = [stills[i::workers] for i in range(workers) if stills[i::workers]]
        for g in groups:
            cmd = [BLENDER, "-b", blend, "--python-expr", PY, "-o", pat]
            for f in g:
                cmd += ["-f", str(f)]
            jobs.append(cmd + ["--", str(scale), "1"])
    else:
        for a, b in chunks(frames[0], frames[1], workers):
            jobs.append([BLENDER, "-b", blend, "--python-expr", PY, "-o", pat, "-s", str(a), "-e", str(b),
                         "-a", "--", str(scale), str(step)])
    t0 = time.time()
    procs = [subprocess.Popen(j, stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.STDOUT) for j in jobs]
    codes = [p.wait() for p in procs]
    dt = time.time() - t0
    if any(codes):
        sys.exit(f"render failed: exit codes {codes}")
    return dt


SHOTS_PY = """
import bpy, json, sys
a = sys.argv[sys.argv.index('--') + 1:]
pat, scale, step, shots = a[0], int(a[1]), int(a[2]), json.loads(a[3])
for name, f0, f1 in shots:
    s = bpy.data.scenes[name]
    s.frame_start, s.frame_end, s.frame_step = f0, f1, step
    s.render.resolution_percentage = scale
    s.render.filepath = pat
    bpy.ops.render.render(animation=True, scene=name)
"""


def render_shots(blend, out, shots, workers=3, step=1, scale=100, quiet=True):
    """shots = [(scene_name, f0, f1), ...]: each shot renders with its own set's scene; greedy-balanced workers."""
    import json
    os.makedirs(out, exist_ok=True)
    pat = os.path.join(os.path.abspath(out), "f_####")
    bins = [[] for _ in range(workers)]
    load = [0] * workers
    for sh in sorted(shots, key=lambda x: x[1] - x[2]):                 # longest first
        i = load.index(min(load))
        bins[i].append(list(sh))
        load[i] += sh[2] - sh[1] + 1
    t0 = time.time()
    procs = [subprocess.Popen([BLENDER, "-b", blend, "--python-expr", SHOTS_PY, "--", pat, str(scale), str(step),
                               json.dumps(b)], stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.STDOUT)
             for b in bins if b]
    codes = [p.wait() for p in procs]
    if any(codes):
        sys.exit(f"render failed: exit codes {codes}")
    return time.time() - t0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--frames", default="1-300")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--scale", type=int, default=100)
    ap.add_argument("--stills")
    a = ap.parse_args()
    fr = tuple(int(x) for x in a.frames.split("-"))
    st = [int(x) for x in a.stills.split(",")] if a.stills else None
    dt = render(a.blend, a.out, a.workers, fr, a.step, a.scale, st)
    n = len(st) if st else (fr[1] - fr[0]) // a.step + 1
    print(f"rendered {n} frames in {dt:.1f}s ({dt / n:.2f}s/frame, {a.workers} workers)")
