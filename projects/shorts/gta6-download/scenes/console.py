"""Living-room console shots: console (212 GB download), locked (pre-loaded, chained), unlock (midnight), patch, grid (millions).

blender -b -P console.py -- <shot> <out.blend> <seconds>
"""
import math, os, random, sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402

shot, blend, dur = sys.argv[sys.argv.index("--") + 1:][:3]
s, NF = start(float(dur), samples=32, raytrace=True)
random.seed(3)
_a = sys.argv[sys.argv.index('--') + 1:]
T_EVENT = float(_a[3]) if len(_a) > 3 and float(_a[3]) > 0 else 0.42

LED_COL = {"console": (0.15, 0.45, 1.0), "locked": (1.0, 0.08, 0.05), "unlock": (1.0, 0.08, 0.05), "patch": (1.0, 0.45, 0.05),
           "grid": (0.15, 0.45, 1.0)}[shot]

# ------------------------------------------------------------------ materials
white = pbr("shell", (0.86, 0.87, 0.9), rough=0.42, coat=0.25)
black = pbr("core", (0.012, 0.012, 0.014), rough=0.12, coat=0.6)
steel = pbr("steel", (0.62, 0.64, 0.68), rough=0.28, metal=1.0)
brass = pbr("brass", (0.83, 0.58, 0.2), rough=0.3, metal=1.0)
dark = pbr("darkmetal", (0.03, 0.03, 0.035), rough=0.4, metal=0.6)

led_m, lnt, lout = new_mat("led")
LED = lnt.n("ShaderNodeEmission")
LED.inputs[0].default_value = (*LED_COL, 1)
LED.inputs[1].default_value = 30.0
if shot == "grid":
    geo = lnt.n("ShaderNodeNewGeometry")
    sep = lnt.n("ShaderNodeSeparateXYZ", ins={"Vector": geo.outputs["Position"]})
    FRONT = lnt.value(0.0)
    on = lnt.maprange(lnt.math("SUBTRACT", FRONT, sep.outputs["Y"]), 0.0, 0.6, 0.02, 1.0)
    fl = lnt.maprange(lnt.math("ABSOLUTE", lnt.math("SUBTRACT", FRONT, sep.outputs["Y"])), 0.0, 1.2, 1.0, 0.0)
    lnt.set(LED.inputs[1], lnt.math("MULTIPLY", on, lnt.math("ADD", 30.0, lnt.math("MULTIPLY", fl, 120.0))))
lnt.t.links.new(LED.outputs[0], lout.inputs[0])


def console(root_name="console"):
    root = bpy.data.objects.new(root_name, None)
    link(root, s)
    parts = [
        box("core", (0.082, 0.225, 0.355), (0, 0, 0.19), black, bevel=0.012, segs=4),
        box("shellL", (0.013, 0.262, 0.402), (-0.050, 0, 0.205), white, bevel=0.0055, segs=4, rot=(0, math.radians(-2.2), 0)),
        box("shellR", (0.013, 0.262, 0.402), (0.050, 0, 0.205), white, bevel=0.0055, segs=4, rot=(0, math.radians(2.2), 0)),
        box("ledL", (0.004, 0.215, 0.0035), (-0.0405, 0, 0.3725), led_m),
        box("ledR", (0.004, 0.215, 0.0035), (0.0405, 0, 0.3725), led_m),
        box("ledFL", (0.0035, 0.004, 0.33), (-0.0405, -0.1135, 0.2), led_m),
        box("ledFR", (0.0035, 0.004, 0.33), (0.0405, -0.1135, 0.2), led_m),
        cyl("base", 0.075, 0.012, (0, 0, 0.006), black),
        box("slot", (0.004, 0.003, 0.11), (0.012, -0.1128, 0.2), dark),
        box("usb", (0.012, 0.003, 0.005), (-0.012, -0.1128, 0.09), dark),
    ]
    for p in parts:
        p.parent = root
    return root, parts


if shot == "grid":
    # ---------------------------------------------------------------- millions of consoles to the horizon
    root, parts = console()
    col = bpy.data.collections.new("unit")
    bpy.context.scene.collection.children.link(col)
    for o in [root] + parts:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    bpy.context.view_layer.layer_collection.children["unit"].exclude = True
    NX, NY, DX, DY = 44, 120, 0.36, 0.52
    for ix in range(NX):
        for iy in range(NY):
            e = bpy.data.objects.new("inst", None)
            e.instance_type, e.instance_collection = "COLLECTION", col
            e.location = ((ix - NX / 2 + 0.5) * DX, iy * DY, 0)
            e.rotation_euler = (0, 0, random.uniform(-0.05, 0.05))
            link(e, s)
    floor = box("floor", (60, 120, 0.1), (0, 40, -0.05), pbr("floor", (0.012, 0.014, 0.02), rough=0.16, coat=0.3))
    D.world(s, (0.004, 0.006, 0.014), 1.0)
    top = light(s, "POINT", (0, 2, 3), 900, color=(0.5, 0.65, 1.0), size=0.6, name="top")
    top.data.specular_factor = 0.0
    key(top, "location", lambda t, f: (0, 0.5 + 2.0 * ease(t), 2.2 + 3.2 * ease(t)), NF)
    light(s, "AREA", (0, -3, 2.5), 260, color=(1.0, 0.85, 0.7), size=3, target=(0, 1, 0.2), name="key")
    key_sock(FRONT, lambda t, f: -2 + 52 * ease(min(1.0, t / 0.85), "in"), NF)
    cam = camera(s, lens=24, dof=2.2, fstop=4.0)
    cam_path(cam, NF, lambda t: Vector((0.25 - 0.2 * t, -1.35 - 0.5 * ease(t), 0.42 + 4.4 * ease(t))),
             lambda t: Vector((0, 1.5 + 0.6 * ease(t), 0.25 - 0.25 * ease(t))))
    L.post(s, bloom=0.5, bloom_threshold=1.3, bloom_size=0.5, dispersion=0.004, vignette=0.3, saturation=1.08, contrast=0.06)
    save(s, blend)
    sys.exit(0)

# ---------------------------------------------------------------- room
root, parts = console()
wood = L.pbr("wood", "wood_table_001", scale=1.6, rough_mul=1.5, rough_add=0.15)
desk = box("desk", (2.6, 0.9, 0.06), (0, 0.1, -0.03), wood, bevel=0.006)
wall = box("wall", (6, 0.1, 4), (0, 0.78, 1.0), L.pbr("wall", "painted_plaster_wall", scale=0.8, tint=(0.06, 0.07, 0.1)))
TVW, TVH, TVZ, TVY = 1.42, 0.80, 0.70, 0.60
tvframe = box("tvframe", (TVW + 0.03, 0.03, TVH + 0.03), (0, TVY + 0.02, TVZ), black, bevel=0.004)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, TVY, TVZ), rotation=(math.radians(90), 0, 0))
screen = bpy.context.object
screen.scale = (TVW, TVH, 1)
sm, snt, sout = new_mat("screen")
uvn = snt.n("ShaderNodeTexCoord")
IMG = {"console": "tv_dl", "locked": "tv_locked", "unlock": "tv_locked", "patch": "tv_patch"}[shot]
img = snt.image(os.path.join(TEX, IMG + ".png"), uvn.outputs["UV"], ext="EXTEND")
colr = img.outputs["Color"]
SWITCH = snt.value(0.0)
PROG = snt.value(0.0)
if shot == "unlock":
    img2 = snt.image(os.path.join(TEX, "tv_play.png"), uvn.outputs["UV"], ext="EXTEND")
    colr = snt.mix(SWITCH, colr, img2.outputs["Color"])
if shot in ("console", "patch"):
    # live progress bar: fill the track (UV rect measured from make_ui.py) up to PROG
    sep = snt.n("ShaderNodeSeparateXYZ", ins={"Vector": uvn.outputs["UV"]})
    x0, x1 = (960 - 330) / 1920, (960 + 330) / 1920
    inx = snt.math("MULTIPLY", snt.math("GREATER_THAN", sep.outputs["X"], x0),
                   snt.math("LESS_THAN", sep.outputs["X"], snt.math("ADD", x0, snt.math("MULTIPLY", PROG, x1 - x0))))
    BY = float(open(os.path.join(TEX, "bar_y.txt")).read()) if os.path.exists(os.path.join(TEX, "bar_y.txt")) else 0.5
    iny = snt.math("MULTIPLY", snt.math("GREATER_THAN", sep.outputs["Y"], BY - 0.012), snt.math("LESS_THAN", sep.outputs["Y"], BY + 0.012))
    colr = snt.mix(snt.math("MULTIPLY", inx, iny), colr, (0.2, 0.55, 1.0, 1) if shot == "console" else (1.0, 0.6, 0.1, 1))
em = snt.n("ShaderNodeEmission", ins={"Color": colr, "Strength": 2.6})
snt.t.links.new(em.outputs[0], sout.inputs[0])
screen.data.materials.append(sm)

D.world(s, (0.006, 0.008, 0.016), 1.0)
TVC = {"console": (0.3, 0.5, 1.0), "locked": (1.0, 0.2, 0.2), "unlock": (1.0, 0.2, 0.2), "patch": (1.0, 0.6, 0.2)}[shot]
tvl = light(s, "AREA", (0, TVY - 0.06, TVZ), 55, color=TVC, size=1.2, target=(0, -1, 0.2), name="tvglow")
keyl = light(s, "AREA", (-1.1, -1.2, 1.1), 38, color=(1.0, 0.86, 0.72), size=1.0, target=(0, 0, 0.2), name="key")
riml = light(s, "AREA", (1.2, 0.35, 0.9), 90, color=(0.5, 0.7, 1.0), size=0.6, target=(0, 0, 0.22), name="rim")
ledl = light(s, "POINT", (0, -0.18, 0.3), 1.5, color=LED_COL, size=0.05, name="ledglow")

# ---------------------------------------------------------------- chain + padlock
chain = []
if shot in ("locked", "unlock"):
    def loop_pts(hx, hy, z, step):
        r = 0.03
        per = []
        segs = [((-hx + r, -hy), (hx - r, -hy)), ((hx, -hy + r), (hx, hy - r)), ((hx - r, hy), (-hx + r, hy)), ((-hx, hy - r), (-hx, -hy + r))]
        for (a, b) in segs:
            a, b = Vector((*a, 0)), Vector((*b, 0))
            n = max(1, int((b - a).length / step))
            for i in range(n):
                p = a.lerp(b, i / n)
                per.append((Vector((p.x, p.y, z)), math.atan2((b - a).y, (b - a).x)))
            corner_c = None
        return per

    for z, tilt in ((0.125, 0.0), (0.275, 0.0)):
        pts = loop_pts(0.074, 0.150, z, 0.027)
        for i, (p, ang) in enumerate(pts):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.0125, minor_radius=0.0036, major_segments=20, minor_segments=8, location=p)
            lk_ = bpy.context.object
            lk_.scale = (1.55, 1.0, 1.0)
            lk_.rotation_euler = (math.radians(90) if i % 2 else 0.0, 0, ang)
            bpy.ops.object.shade_smooth()
            lk_.data.materials.append(steel)
            chain.append(lk_)
    body = box("lockbody", (0.085, 0.034, 0.07), (0, -0.172, 0.165), brass, bevel=0.008, segs=4)
    keyhole = cyl("keyhole", 0.007, 0.004, (0, -0.1895, 0.16), dark, rot=(math.radians(90), 0, 0))
    keyhole.parent = body
    cd = bpy.data.curves.new("shackle", "CURVE")
    cd.dimensions = "3D"
    sp = cd.splines.new("POLY")
    n = 24
    R, LEG = 0.026, 0.05
    P = [(-R, 0, 0)] + [(-R * math.cos(math.pi * i / n), 0, LEG + R * math.sin(math.pi * i / n)) for i in range(n + 1)] + [(R, 0, 0.012)]
    sp.points.add(len(P) - 1)
    for i, q in enumerate(P):
        sp.points[i].co = (*q, 1)
    cd.bevel_depth, cd.bevel_resolution = 0.0075, 6
    cd.use_fill_caps = True
    shackle = bpy.data.objects.new("shackle", cd)
    link(shackle, s)
    shackle.data.materials.append(steel)
    shackle.location = (0, -0.172, 0.195)
    chain += [body]

cam = camera(s, lens=38, dof=root, fstop=4.5)
focus = bpy.data.objects.new("focus", None)
link(focus, s)
focus.location = (0, -0.12, 0.2)
cam.data.dof.focus_object = focus

if shot == "console":
    key_sock(PROG, lambda t, f: 0.06 + 0.10 * t, NF)
    cam_path(cam, NF, lambda t: Vector((-0.42 + 0.34 * ease(t), -1.18 + 0.12 * ease(t), 0.27 + 0.05 * t)),
             lambda t: Vector((0, 0.1, 0.36)))
elif shot == "locked":
    cam_path(cam, NF, lambda t: Vector((0.36 - 0.26 * ease(t), -1.12 + 0.30 * ease(t), 0.34 - 0.04 * t)),
             lambda t: Vector((0, 0.05, 0.30 - 0.04 * ease(t))))
    key(LED.inputs[1], "default_value", lambda t, f: 30.0 * (0.65 + 0.35 * math.sin(f * 0.35)), NF)
elif shot == "patch":
    key_sock(PROG, lambda t, f: 0.004 + 0.012 * t, NF)
    key(LED.inputs[1], "default_value", lambda t, f: 30.0 * (0.55 + 0.45 * math.sin(f * 0.6)), NF)
    cam_path(cam, NF, lambda t: Vector((0.12 + 0.1 * t, -0.92 - 0.3 * ease(t, "out"), 0.3)),
             lambda t: Vector((0, 0.1, 0.36)), lambda t: math.radians(-5 * ease(t, "out")))
elif shot == "unlock":
    fe = int(T_EVENT * NF)
    # shackle pops up + swings open, then chains and lock drop under gravity; LED + TV flip to green
    for f in range(1, NF + 1):
        k = ease((f - fe) / 5.0, "out")
        fall = max(0.0, (f - fe - 6) / FPS)
        shackle.location = (0, -0.172, 0.195 + 0.022 * k - 4.9 * fall * fall)
        shackle.rotation_euler = (0, 0, math.radians(75) * k)
        shackle.keyframe_insert("location", frame=f)
        shackle.keyframe_insert("rotation_euler", frame=f)
    for o in chain:
        z0 = o.location.z
        r0 = o.rotation_euler.copy()
        d = random.uniform(5, 10)
        sx, sy, sr = random.uniform(-0.25, 0.25), random.uniform(-0.5, -0.05), random.uniform(-6, 6)
        for f in range(1, NF + 1):
            tt = max(0.0, (f - fe - d) / FPS)
            z = z0 - 4.9 * tt * tt
            x, y = o.location.x, o.location.y
            if z < 0.012 and o.name != "lockbody":
                z = 0.012
            if z < 0.018 and o.name == "lockbody":
                z = 0.018
                o.rotation_euler = (math.radians(90), 0, 0.5)
            o.location.z = z
            o.rotation_euler = (r0.x + sr * tt, r0.y + sr * 0.6 * tt, r0.z) if z > 0.04 else o.rotation_euler.copy()
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("rotation_euler", frame=f)
    gcol = (0.1, 1.0, 0.35)
    for f in range(1, NF + 1):
        k = ease((f - fe - 4) / 6.0)
        c = tuple(LED_COL[i] + (gcol[i] - LED_COL[i]) * k for i in range(3))
        LED.inputs[0].default_value = (*c, 1)
        LED.inputs[0].keyframe_insert("default_value", frame=f)
        fl = math.exp(-max(0, f - fe - 4) / 7.0) if f >= fe + 4 else 0.0
        LED.inputs[1].default_value = 30 + 160 * fl
        LED.inputs[1].keyframe_insert("default_value", frame=f)
        for lg in (ledl, tvl):
            lg.data.color = c if lg is ledl else tuple(TVC[i] + ((0.25, 1.0, 0.5)[i] - TVC[i]) * k for i in range(3))
            lg.data.keyframe_insert("color", frame=f)
        ledl.data.energy = 1.5 + 14 * fl
        ledl.data.keyframe_insert("energy", frame=f)
        SWITCH.default_value = k
        SWITCH.keyframe_insert("default_value", frame=f)
    cam_path(cam, NF, lambda t: Vector((0.10 - 0.16 * ease(t), -0.80 - 0.34 * ease(max(0.0, (t - T_EVENT) / (1 - T_EVENT)), "out"), 0.26 + 0.04 * t)),
             lambda t: Vector((0, 0.05, 0.25 + 0.10 * ease(max(0.0, (t - T_EVENT) / (1 - T_EVENT))))))

L.post(s, bloom=0.4, bloom_threshold=1.4, bloom_size=0.5, dispersion=0.004, vignette=0.3, saturation=1.08, contrast=0.06)
save(s, blend)
