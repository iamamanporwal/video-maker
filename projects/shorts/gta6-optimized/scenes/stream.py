"""World streaming: tiles ahead of the player load (rise + green pulse), tiles behind unload (sink + fade). Top-down-ish tracking cam.

blender -b -P stream.py -- stream <out.blend> <seconds> <ev>
"""
import math, os, random, sys
import bpy
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402
from city import City, sky, PITCH, LOT, ROADW  # noqa: E402
from carlib import load_car  # noqa: E402

shot, blend, dur, ev = sys.argv[sys.argv.index("--") + 1:][:4]
dur = float(dur)
s, NF = start(dur, samples=20, raytrace=False)
sky(s, top=(0.01, 0.015, 0.05), mid=(0.12, 0.06, 0.16), hor=(0.4, 0.18, 0.2), strength=0.8)
NX, NY = 9, 14
C = City(s, NX, NY, seed=9)
R = 2.3 * PITCH
V = 52.0                                        # m/s (stylised)
Y0 = -30.0
tile_mat, nt, out = new_mat("tile")
oi = nt.n("ShaderNodeObjectInfo")
p = nt.n("ShaderNodeBsdfPrincipled", ins={"Roughness": 0.5, "Base Color": (0.02, 0.025, 0.03, 1)})
nt.set(p.inputs["Emission Color"], oi.outputs["Color"])
nt.set(p.inputs["Emission Strength"], 2.0)
nt.t.links.new(p.outputs[0], out.inputs[0])
tiles = {}
for b in C.bld:
    key_ = (round((b["cx"] - C.x0) // PITCH), round((b["cy"] - C.y0) // PITCH))
    tiles.setdefault(key_, []).append(b)
slabs = {}
for (i, j), bl in tiles.items():
    bx, by = C.block_origin(i, j)
    slab = box("slab", (PITCH - ROADW + 1.0, PITCH - ROADW + 1.0, 0.5), (bx + LOT, by + LOT, 0.25), tile_mat)
    slabs[(i, j)] = slab
    for b in bl:
        b["h0"] = [o.scale.z for o in [b["obj"]] + b["tiers"]]
state = {k: 0.0 for k in tiles}
loaded_at = {k: None for k in tiles}
ring = bpy.data.objects.new("ring", None)
link(ring, s)
rm = emit_mat("ringm", (0.3, 1.0, 0.55), 6.0)
bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=0.9, major_segments=96, minor_segments=8)
tor = bpy.context.object
tor.data.materials.append(rm)
tor.parent = ring
hero = load_car(0.25, "hero")
hero.scale = (2.6, 2.6, 2.6)
hero.data.materials.clear()
hero.data.materials.append(pbr("heroc", (0.9, 0.08, 0.38), rough=0.3, emit=(1.0, 0.1, 0.45), emit_strength=1.0))
hero.parent = ring
ptr = lambda t: Vector((0.0, Y0 + V * t * dur, 0.0))  # noqa: E731
for f in range(1, NF + 1):
    t = (f - 1) / max(1, NF - 1)
    P = ptr(t)
    ring.location = (P.x, P.y, 0.9)
    ring.keyframe_insert("location", frame=f)
    hero.location = (0, 0, -0.5)
    for (i, j), bl in tiles.items():
        bx, by = C.block_origin(i, j)
        cx, cy = bx + LOT, by + LOT
        inside = math.hypot(cx - P.x, cy - P.y) < R
        tgt = 1.0 if inside else 0.0
        st = state[(i, j)]
        rate = 0.16 if tgt > st else 0.12
        st = st + max(-rate, min(rate, tgt - st)) * (1.0 if f > 1 else 10.0)
        newly = tgt > 0.5 and st < 0.98 and f > 4
        state[(i, j)] = st
        e = ease(st, "io")
        slab = slabs[(i, j)]
        pulse = (math.sin(min(1, st) * math.pi)) if f > 4 else 0
        col = (0.02 + 0.08 * e, 0.025 + 0.3 * e + 0.8 * pulse, 0.03 + 0.15 * e + 0.2 * pulse, 1)
        slab.color = col
        slab.keyframe_insert("color", frame=f)
        for b in bl:
            for k, o in enumerate([b["obj"]] + b["tiers"]):
                o.scale.z = max(0.001, b["h0"][k] * e)
                o.keyframe_insert("scale", frame=f, index=2)
light(s, "SUN", (0, 0, 50), 2.0, color=(0.8, 0.85, 1.0), target=(0, 20, 0), name="moon")
cam = camera(s, lens=30)
cam_path(cam, NF, lambda t: ptr(t) + Vector((30 * math.sin(t * 1.3), -140, 250)), lambda t: ptr(t) + Vector((0, 20, 0)))
L.post(s, bloom=0.55, bloom_threshold=1.0, bloom_size=0.6, dispersion=0.004, vignette=0.3, saturation=1.1, contrast=0.07)
save(s, blend)
