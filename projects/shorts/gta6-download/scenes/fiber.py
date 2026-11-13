"""Macro fibre-optic bundle: light pulses race down the glass, then overheat (cyan → white-hot red).

blender -b -P fiber.py -- fiber <out.blend> <seconds>
"""
import math, os, random, sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402

shot, blend, dur = sys.argv[sys.argv.index("--") + 1:][:3]
s, NF = start(float(dur), samples=32, raytrace=True)
random.seed(11)
D.world(s, (0.002, 0.003, 0.006), 1.0)
_a = sys.argv[sys.argv.index('--') + 1:]
T_HOT = float(_a[3]) if len(_a) > 3 and float(_a[3]) > 0 else 0.45

m, nt, out = new_mat("fiber")
tc = nt.n("ShaderNodeTexCoord")
sep = nt.n("ShaderNodeSeparateXYZ", ins={"Vector": tc.outputs["Object"]})
oi = nt.n("ShaderNodeObjectInfo")
PHASE, HEAT = nt.value(0.0), nt.value(0.0)
spd = nt.math("ADD", 0.7, nt.math("MULTIPLY", oi.outputs["Random"], 0.9))
v = nt.math("FRACT", nt.math("SUBTRACT", nt.math("ADD", nt.math("MULTIPLY", sep.outputs["X"], 2.6), nt.math("MULTIPLY", oi.outputs["Random"], 9.0)),
                             nt.math("MULTIPLY", PHASE, spd)))
pulse = nt.math("POWER", v, 7.0)
col = nt.mix(HEAT, nt.mix(oi.outputs["Random"], (0.05, 0.55, 1.0, 1), (0.2, 0.95, 1.0, 1)), nt.mix(pulse, (1.0, 0.07, 0.01, 1), (1.0, 0.42, 0.1, 1)))
p = nt.n("ShaderNodeBsdfPrincipled", ins={"Base Color": (0.02, 0.03, 0.04, 1), "Roughness": 0.08})
nt.set(p.inputs["Emission Color"], col)
nt.set(p.inputs["Emission Strength"], nt.math("ADD", nt.math("ADD", 0.5, nt.math("MULTIPLY", HEAT, 0.6)),
                                            nt.math("MULTIPLY", pulse, nt.math("ADD", 60.0, nt.math("MULTIPLY", HEAT, 25.0)))))
nt.t.links.new(p.outputs[0], out.inputs[0])

tm, tnt, tout = new_mat("tip")
TH = tnt.value(0.0)
te = tnt.n("ShaderNodeEmission")
tnt.set(te.inputs["Color"], tnt.mix(TH, (0.3, 0.85, 1.0, 1), (1.0, 0.3, 0.08, 1)))
tnt.set(te.inputs["Strength"], tnt.math("ADD", 40.0, tnt.math("MULTIPLY", TH, 20.0)))
tnt.t.links.new(te.outputs[0], tout.inputs[0])

LEN = 0.62
for i in range(150):
    a = random.uniform(0, 2 * math.pi)
    r0 = 0.024 * math.sqrt(random.random())
    sy, sz = math.cos(a) * r0, math.sin(a) * r0
    fan = random.uniform(1.5, 9.0)
    ln = LEN * random.uniform(0.72, 1.0)
    cd = bpy.data.curves.new("fib", "CURVE")
    cd.dimensions = "3D"
    sp = cd.splines.new("POLY")
    n = 28
    sp.points.add(n)
    wob = random.uniform(-0.02, 0.02)
    for k in range(n + 1):
        u = k / n
        sp.points[k].co = (u * ln, sy * (1 + fan * u ** 1.6) + wob * math.sin(u * 5), sz * (1 + fan * u ** 1.6) - 0.05 * u * u, 1)
    cd.bevel_depth, cd.bevel_resolution = 0.0011, 3
    o = bpy.data.objects.new("fib", cd)
    o.data.materials.append(m)
    link(o, s)
    e = sp.points[n].co
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.0019, location=(e[0], e[1], e[2]))
    bpy.context.object.data.materials.append(tm)

rubber = pbr("rubber", (0.015, 0.015, 0.017), rough=0.55)
cyl("jacket", 0.031, 3.0, (-1.5, 0, 0), rubber, rot=(0, math.radians(90), 0))
cyl("ferrule", 0.034, 0.05, (-0.02, 0, 0), pbr("steel", (0.6, 0.62, 0.66), rough=0.25, metal=1.0), rot=(0, math.radians(90), 0))
box("table", (4, 4, 0.02), (0, 0, -0.16), pbr("tbl", (0.01, 0.011, 0.014), rough=0.12, coat=0.4))
bok = [emit_mat("b0", (0.2, 0.6, 1.0), 14), emit_mat("b1", (1.0, 0.5, 0.2), 14), emit_mat("b2", (0.9, 0.9, 1.0), 10)]
for i in range(46):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=random.uniform(0.006, 0.014),
                                         location=(random.uniform(-1.2, 1.6), random.uniform(1.4, 2.6), random.uniform(-0.1, 0.9)))
    bpy.context.object.data.materials.append(random.choice(bok))
light(s, "AREA", (-0.4, -0.6, 0.6), 6, color=(0.6, 0.75, 1.0), size=0.6, target=(0.1, 0, 0), name="key")
heat = light(s, "POINT", (0.45, 0, 0.05), 0.0, color=(1.0, 0.25, 0.05), size=0.1, name="heat")

fh = int(T_HOT * NF)
key_sock(PHASE, lambda t, f: f / FPS * (2.2 + 5.0 * ease((f - fh) / (NF * 0.3))), NF)
for sock in (HEAT, TH):
    key_sock(sock, lambda t, f: ease((f - fh) / (NF * 0.22)), NF)
key(heat.data, "energy", lambda t, f: 0.6 * ease((f - fh) / (NF * 0.22)) * (0.8 + 0.2 * math.sin(f * 1.3)), NF)
focus = bpy.data.objects.new("focus", None)
link(focus, s)
key(focus, "location", lambda t, f: (0.12 + 0.36 * ease(t), 0, 0), NF)
cam = camera(s, lens=60, dof=focus, fstop=1.8)
cam_path(cam, NF, lambda t: Vector((0.02 + 0.52 * ease(t), -0.62 + 0.16 * ease(t), 0.20 - 0.10 * ease(t))),
         lambda t: Vector((0.16 + 0.34 * ease(t), 0, -0.01)),
         lambda t: math.radians(8) + (0.01 * math.sin(t * NF * 2.1) * ease((t - T_HOT) * 4)))
L.post(s, bloom=0.6, bloom_threshold=1.3, bloom_size=0.55, dispersion=0.006, vignette=0.3, saturation=1.1, contrast=0.06)
save(s, blend)
