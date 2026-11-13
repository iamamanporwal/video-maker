"""LOD shots. lodline: four copies of one real car at 100% / 25% / 6% / 1.5% triangles with wire overlays (dolly along the row).
lod: the same car drives away down the boulevard and swaps LOD at painted distance rings.

blender -b -P lod.py -- <shot> <out.blend> <seconds> <ev>
"""
import math, os, random, sys, json
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402
from city import City, sky  # noqa: E402
from carlib import load_car, tris  # noqa: E402

shot, blend, dur, ev = sys.argv[sys.argv.index("--") + 1:][:4]
dur = float(dur)
s, NF = start(dur, samples=24, raytrace=True)
RATIOS = (1.0, 0.25, 0.06, 0.015)
COLS = [(0.25, 1.0, 0.45), (0.2, 0.85, 1.0), (1.0, 0.85, 0.15), (1.0, 0.25, 0.12)]


def lod_car(i, mat_wire):
    c = load_car(RATIOS[i], f"lod{i}")
    w = c.copy()
    w.data = c.data.copy()
    w.data.materials.clear()
    w.data.materials.append(mat_wire)
    m = w.modifiers.new("wf", "WIREFRAME")
    m.thickness, m.use_replace, m.use_even_offset = (0.006 if i == 0 else 0.02 + 0.01 * i), True, True
    link(w, s)
    return c, w


counts = {}
if shot == "lodline":
    D.world(s, (0.004, 0.005, 0.01), 1.0)
    fm, nt, out = new_mat("floor")
    tc = nt.n("ShaderNodeTexCoord")
    br = nt.n("ShaderNodeTexBrick", offset=0.0, ins={"Vector": tc.outputs["Object"], "Scale": 1.0, "Mortar Size": 0.012, "Color1": (0.02, 0.022, 0.03, 1),
                                                  "Color2": (0.025, 0.027, 0.036, 1), "Mortar": (0.0, 0.25, 0.3, 1), "Brick Width": 2.0, "Row Height": 2.0})
    p = nt.n("ShaderNodeBsdfPrincipled", ins={"Roughness": 0.12, "Metallic": 0.3})
    nt.set(p.inputs["Base Color"], br.outputs["Color"])
    nt.set(p.inputs["Emission Color"], br.outputs["Color"])
    nt.set(p.inputs["Emission Strength"], 0.6)
    nt.t.links.new(p.outputs[0], out.inputs[0])
    box("floor", (60, 40, 0.1), (8, 0, -0.05), fm)
    SP = 5.6
    for i in range(4):
        wm = emit_mat(f"w{i}", COLS[i], 3.0 if i else 1.6)
        c, w = lod_car(i, wm)
        for o in (c, w):
            o.location = (i * SP, 0, 0)
            o.rotation_euler = (0, 0, math.radians(-28))
        counts[i] = tris(c)
        # glow pad
        pad = emit_mat(f"pad{i}", COLS[i], 0.5)
        cyl("pad", 2.3, 0.01, (i * SP, 0, 0.012), pad, verts=64)
    light(s, "AREA", (6, -6, 9), 900, color=(1, 0.95, 0.9), size=8, target=(8, 0, 0.5), name="key")
    light(s, "AREA", (14, 8, 5), 500, color=(0.4, 0.6, 1.0), size=6, target=(8, 0, 0.5), name="rim")
    cam = camera(s, lens=36)
    cam_path(cam, NF, lambda t: Vector((-3.0 + 16.5 * ease(t, "io"), -7.0 - 1.0 * t, 1.1 + 0.4 * math.sin(t * 3))),
             lambda t: Vector((-0.5 + 17.0 * ease(t, "io") + 0.2, 0, 0.9)))
else:
    sky(s)
    C = City(s, 5, 3, seed=7)
    # ring markers at the LOD distances
    Y0, VMAX = 6.0, 52.0
    fr = (0.30, 0.55, 0.78)
    for k, f in enumerate(fr):
        y = Y0 + VMAX * f
        box("ring", (14.0, 0.5, 0.03), (0, y, 0.03), emit_mat(f"ring{k}", COLS[k + 1], 5.0))
    cars, wires = [], []
    for i in range(4):
        wm = emit_mat(f"w{i}", COLS[i], 2.2 if i else 1.2)
        c, w = lod_car(i, wm)
        cars.append(c)
        wires.append(w)
        counts[i] = tris(c)
    for i in range(4):
        for o in (cars[i], wires[i]):
            def vis(t, f, i=i):
                lv = 0 if t < fr[0] else 1 if t < fr[1] else 2 if t < fr[2] else 3
                return 1.5 if lv == i else 0.0001
            key(o, "scale", lambda t, f, i=i: Vector([vis(t, f, i)] * 3), NF)
            key(o, "location", lambda t, f: Vector((1.9 + 0.012 * math.sin(f * 0.6), Y0 + VMAX * t, 0)), NF)
    for _ in range(1):
        light(s, "SUN", (0, 60, 20), 4.0, color=(1.0, 0.55, 0.3), target=(0, 0, 0), name="sun")
    cam = camera(s, lens=32)
    cam_path(cam, NF, lambda t: Vector((1.9 - 2.5 * t, -4 + 22 * t, 1.5 + 1.0 * t)), lambda t: Vector((1.9, Y0 + 20 + 34 * t, 1.0)))
json.dump(counts, open(os.path.join(os.path.dirname(blend), "..", "lod_counts.json"), "w"))
L.post(s, bloom=0.5, bloom_threshold=1.0, bloom_size=0.6, dispersion=0.004, vignette=0.28, saturation=1.1, contrast=0.07)
save(s, blend)
