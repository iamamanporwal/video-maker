"""Instancing: a crowd of 100 pedestrians that all share ONE mesh. At <ev> their colours collapse to the same clay-cyan → clones.

blender -b -P crowd.py -- crowd <out.blend> <seconds> <ev>
"""
import math, os, random, sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402
from city import City, sky  # noqa: E402

shot, blend, dur, ev = sys.argv[sys.argv.index("--") + 1:][:4]
dur, ev = float(dur), float(ev)
if ev < 0:
    ev = 0.5
s, NF = start(dur, samples=20, raytrace=True)
rng = random.Random(21)
sky(s)
C = City(s, 3, 3, seed=5)
UNI = bpy.data.node_groups  # noqa: F841

# one pedestrian mesh -------------------------------------------------------------------------------------------
cm, nt, out = new_mat("clothes")
oi = nt.n("ShaderNodeObjectInfo")
ramp = nt.n("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = "CONSTANT"
pal = [(0.8, 0.1, 0.1), (0.1, 0.3, 0.8), (0.9, 0.8, 0.1), (0.1, 0.6, 0.3), (0.9, 0.9, 0.9), (0.6, 0.1, 0.6), (0.95, 0.45, 0.05), (0.05, 0.05, 0.06)]
ramp.color_ramp.elements[0].color = (*pal[0], 1)
ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 1 / 8, (*pal[1], 1)
for i in range(2, 8):
    e = ramp.color_ramp.elements.new(i / 8)
    e.color = (*pal[i], 1)
nt.t.links.new(oi.outputs["Random"], ramp.inputs["Fac"])
UNIF = nt.value(0.0)
col = nt.mix(UNIF, ramp.outputs["Color"], (0.1, 0.8, 1.0, 1))
p = nt.n("ShaderNodeBsdfPrincipled", ins={"Roughness": 0.55})
nt.set(p.inputs["Base Color"], col)
nt.set(p.inputs["Emission Color"], col)
nt.set(p.inputs["Emission Strength"], nt.math("ADD", nt.math("MULTIPLY", UNIF, 1.0), 0.35))
nt.t.links.new(p.outputs[0], out.inputs[0])
skin = pbr("skin", (0.75, 0.55, 0.42), rough=0.6)
parts = []
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(0, 0, 1.68), segments=16, ring_count=10)
h = bpy.context.object
h.data.materials.append(skin)
parts.append(h)
for (sz, loc, rot) in (((0.42, 0.24, 0.62), (0, 0, 1.2), 0), ((0.14, 0.16, 0.8), (-0.11, 0, 0.4), 0), ((0.14, 0.16, 0.8), (0.11, 0, 0.4), 0),
                        ((0.09, 0.1, 0.62), (-0.28, 0, 1.25), 0), ((0.09, 0.1, 0.62), (0.28, 0, 1.25), 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = sz
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(cm)
    parts.append(o)
bpy.ops.object.select_all(action="DESELECT")
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = h
bpy.ops.object.join()
ped = h
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
ped.name = "ped_master"
ped.location = (0, 0, -60)
bpy.ops.object.shade_smooth()
n_tri = len(ped.data.polygons)

# crowd ---------------------------------------------------------------------------------------------------------
N = 100
people = []
for i in range(N):
    o = bpy.data.objects.new("ped", ped.data)             # ← the same mesh data every time
    link(o, s)
    row = i // 10
    x = rng.uniform(-5.8, 5.8)
    y = 7 + row * 2.6 + rng.uniform(-1.2, 1.2)
    d = 1 if x > 0 else -1
    people.append((o, x, y, d, rng.uniform(0, 6.28), rng.uniform(0.6, 1.1), rng.uniform(1.25, 1.5)))
for f in range(1, NF + 1):
    t = (f - 1) / max(1, NF - 1)
    tt = (f - 1) / FPS
    for o, x, y, d, ph, sp, sc in people:
        o.location = (x, y + d * sp * tt * 0.0 + (-d) * sp * tt, abs(math.sin(tt * 6.0 * sp + ph)) * 0.05)
        o.rotation_euler = (0, 0.04 * math.sin(tt * 6.0 * sp + ph), math.pi if d < 0 else 0.0)
        o.scale = (sc, sc, sc)
        for pth in ("location", "rotation_euler", "scale"):
            o.keyframe_insert(pth, frame=f)
key_sock(UNIF, lambda t, f: ease((t - ev) / 0.12) if t >= ev - 0.001 else 0.0, NF)
light(s, "SUN", (0, 60, 20), 4.0, color=(1.0, 0.55, 0.3), target=(0, 10, 0), name="sun")
cam = camera(s, lens=30)
K = lambda t: ease(max(0, (t - 0.3) / 0.7), "io")  # noqa: E731
cam_path(cam, NF, lambda t: Vector((-1.5 + 3 * t, 0 + 6 * t, 1.5 + 11 * K(t))),
         lambda t: Vector((0, 16 + 4 * t, 1.0 - 0.8 * K(t))))
L.post(s, bloom=0.5, bloom_threshold=1.0, bloom_size=0.6, dispersion=0.004, vignette=0.28, saturation=1.1, contrast=0.07)
save(s, blend)
