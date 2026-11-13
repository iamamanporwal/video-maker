"""Data-centre aisle: dc (cool blue, endless racks) and dc_red (overload alarm).

blender -b -P dc.py -- <shot> <out.blend> <seconds>
"""
import math, os, random, sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402

shot, blend, dur = sys.argv[sys.argv.index("--") + 1:][:3]
s, NF = start(float(dur), samples=32, raytrace=True)
random.seed(5)
RED = shot == "dc_red"
D.world(s, (0.002, 0.003, 0.006), 1.0)

# rack face: stacked 1U servers with a blinking LED matrix
m, nt, out = new_mat("rack")
tc = nt.n("ShaderNodeTexCoord")
geo = nt.n("ShaderNodeNewGeometry")
oi = nt.n("ShaderNodeObjectInfo")
sep = nt.n("ShaderNodeSeparateXYZ", ins={"Vector": tc.outputs["Object"]})
nsep = nt.n("ShaderNodeSeparateXYZ", ins={"Vector": geo.outputs["Normal"]})
front = nt.math("GREATER_THAN", nt.math("ABSOLUTE", nsep.outputs["X"]), 0.9)
TIME = nt.value(0.0)
gy, gz = nt.math("MULTIPLY", sep.outputs["Y"], 46.0), nt.math("MULTIPLY", sep.outputs["Z"], 23.0)
fy, fz = nt.math("SUBTRACT", nt.math("FRACT", gy), 0.5), nt.math("SUBTRACT", nt.math("FRACT", gz), 0.5)
dist = nt.math("SQRT", nt.math("ADD", nt.math("MULTIPLY", fy, fy), nt.math("MULTIPLY", nt.math("MULTIPLY", fz, 0.5), nt.math("MULTIPLY", fz, 0.5))))
dotm = nt.maprange(dist, 0.10, 0.17, 1.0, 0.0)
cell = nt.n("ShaderNodeCombineXYZ", ins={"X": nt.math("FLOOR", gy), "Y": nt.math("FLOOR", gz), "Z": nt.math("MULTIPLY", oi.outputs["Random"], 91.0)})
wn = nt.n("ShaderNodeTexWhiteNoise", noise_dimensions="3D", ins={"Vector": cell.outputs[0]})
r = wn.outputs["Value"]
wn2 = nt.n("ShaderNodeTexWhiteNoise", noise_dimensions="4D", ins={"Vector": cell.outputs[0]})
nt.set(wn2.inputs["W"], nt.math("FLOOR", nt.math("ADD", nt.math("MULTIPLY", TIME, nt.math("ADD", 3.0, nt.math("MULTIPLY", r, 9.0))), nt.math("MULTIPLY", r, 17.0))))
on = nt.math("MULTIPLY", nt.math("GREATER_THAN", r, 0.52), nt.math("GREATER_THAN", wn2.outputs["Value"], 0.35))
if RED:
    lcol = nt.mix(nt.math("GREATER_THAN", r, 0.9), (1.0, 0.05, 0.02, 1), (1.0, 0.45, 0.05, 1))
else:
    lcol = nt.mix(nt.math("GREATER_THAN", r, 0.72), (0.1, 1.0, 0.35, 1), nt.mix(nt.math("GREATER_THAN", r, 0.9), (0.15, 0.55, 1.0, 1), (1.0, 0.6, 0.1, 1)))
seam = nt.math("LESS_THAN", nt.math("ABSOLUTE", fz), 0.44)
p = nt.n("ShaderNodeBsdfPrincipled", ins={"Metallic": 0.85})
nt.set(p.inputs["Base Color"], nt.mix(nt.math("MULTIPLY", seam, front), (0.004, 0.004, 0.005, 1), (0.035, 0.037, 0.042, 1)))
nt.set(p.inputs["Roughness"], nt.maprange(r, 0, 1, 0.28, 0.5))
nt.set(p.inputs["Emission Color"], lcol)
nt.set(p.inputs["Emission Strength"], nt.math("MULTIPLY", nt.math("MULTIPLY", nt.math("MULTIPLY", dotm, on), front), 26.0))
nt.t.links.new(p.outputs[0], out.inputs[0])

NR, SP = 26, 0.64
for side in (-1, 1):
    for i in range(NR):
        box("rack", (0.95, 0.6, 2.15), (side * 1.18, i * SP, 1.075), m, bevel=0.006)
        box("gap", (0.9, 0.02, 2.15), (side * 1.2, i * SP + SP / 2, 1.075), pbr("gapm", (0.002, 0.002, 0.002), rough=0.6))
# floor tiles
fm, fnt, fout = new_mat("floor")
tcf = fnt.n("ShaderNodeTexCoord")
br = fnt.n("ShaderNodeTexBrick", offset=0.0, ins={"Vector": tcf.outputs["Object"], "Scale": 1.0, "Mortar Size": 0.006,
                                                  "Color1": (0.05, 0.052, 0.058, 1), "Color2": (0.06, 0.062, 0.07, 1), "Mortar": (0.005, 0.005, 0.006, 1),
                                                  "Brick Width": 0.6, "Row Height": 0.6})
fp = fnt.n("ShaderNodeBsdfPrincipled", ins={"Roughness": 0.14})
fnt.set(fp.inputs["Base Color"], br.outputs["Color"])
fnt.t.links.new(fp.outputs[0], fout.inputs[0])
box("floor", (6, 60, 0.1), (0, 15, -0.05), fm)
box("ceil", (6, 60, 0.1), (0, 15, 2.75), pbr("ceil", (0.01, 0.01, 0.012), rough=0.7))
box("end", (6, 0.2, 3), (0, NR * SP + 0.5, 1.4), pbr("endw", (0.008, 0.008, 0.01), rough=0.7))
# overhead: light strips + yellow fibre trunks in a tray
LC = (1.0, 0.06, 0.03) if RED else (0.62, 0.8, 1.0)
sm, snt, sout = new_mat("strip")
SE = snt.n("ShaderNodeEmission")
SE.inputs[0].default_value = (*LC, 1)
SE.inputs[1].default_value = 16.0
snt.t.links.new(SE.outputs[0], sout.inputs[0])
lights = []
for i in range(0, NR, 2):
    y = i * SP + 0.3
    box("strip", (0.07, 0.9, 0.02), (0, y, 2.66), sm)
    lights.append(light(s, "AREA", (0, y, 2.6), 26 if RED else 34, color=LC, size=0.8, target=(0, y, 0), name="strip_l"))
ym = pbr("yellow", (0.9, 0.62, 0.02), rough=0.45)
for k, x in enumerate((-0.52, -0.46, -0.40, 0.42, 0.48)):
    cyl("trunk", 0.022, 40, (x, 15, 2.5 + 0.01 * (k % 2)), ym, rot=(math.radians(90), 0, 0), verts=16)
box("tray", (0.3, 40, 0.012), (-0.46, 15, 2.47), pbr("tray", (0.25, 0.26, 0.28), rough=0.35, metal=1.0))
box("tray2", (0.2, 40, 0.012), (0.45, 15, 2.47), pbr("tray2", (0.25, 0.26, 0.28), rough=0.35, metal=1.0))
# haze
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 8, 1.35))
vol = bpy.context.object
vol.scale = (3.0, 20, 2.7)
vm, vnt, vout = new_mat("haze")
vs = vnt.n("ShaderNodeVolumePrincipled", ins={"Density": 0.035 if RED else 0.02})
vs.inputs["Color"].default_value = (1.0, 0.5, 0.45, 1) if RED else (0.8, 0.88, 1.0, 1)
vnt.t.links.new(vs.outputs[0], vout.inputs["Volume"])
vol.data.materials.append(vm)

key_sock(TIME, lambda t, f: f / FPS * (2.6 if RED else 1.0), NF)
cam = camera(s, lens=20, dof=4.0, fstop=2.8)
if RED:
    fl = lambda f: 0.35 + 0.65 * (0.5 + 0.5 * math.sin(f * 0.55)) ** 2  # noqa: E731
    key(SE.inputs[1], "default_value", lambda t, f: 22.0 * fl(f), NF)
    for lg in lights:
        key(lg.data, "energy", lambda t, f: 30.0 * fl(f), NF)
    cam_path(cam, NF, lambda t: Vector((0.05 * math.sin(t * 40), 0.4 + 2.6 * ease(t, "out") + 0.0, 1.05 + 0.012 * math.sin(t * 55))),
             lambda t: Vector((0, 12, 1.25)), lambda t: math.radians(4 * math.sin(t * 9)))
else:
    cam_path(cam, NF, lambda t: Vector((-0.12, 0.3 + 0.42 * t * float(dur), 1.25)), lambda t: Vector((0.05, 14, 1.2)))
L.post(s, bloom=0.5, bloom_threshold=1.3, bloom_size=0.5, dispersion=0.005, vignette=0.3, saturation=1.08, contrast=0.06)
save(s, blend)
