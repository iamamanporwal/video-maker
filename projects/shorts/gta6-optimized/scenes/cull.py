"""Debug-view culling shots. cull: frustum sweep then occlusion (red) — reveal: the payoff, a lit wedge of city in a ghost-wire world.

blender -b -P cull.py -- <shot> <out.blend> <seconds> <ev>
"""
import math, os, random, sys
import bpy
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402
from city import City, sky, PITCH  # noqa: E402
from carlib import load_car  # noqa: E402

shot, blend, dur, ev = sys.argv[sys.argv.index("--") + 1:][:4]
dur, ev = float(dur), float(ev)
if ev < 0:
    ev = 0.5
REVEAL = shot == "reveal"
s, NF = start(dur, samples=20, raytrace=False)
sky(s, top=(0.01, 0.015, 0.05), mid=(0.12, 0.06, 0.16), hor=(0.5, 0.2, 0.2), strength=0.8)
C = City(s, 7, 7, seed=4)
HALF, RNG = math.radians(30), 105.0
wm_c = emit_mat("ghostc", (0.1, 0.55, 0.8), 1.3)
wm_r = emit_mat("ghostr", (1.0, 0.12, 0.08), 6.0)
rng = random.Random(2)

# player + cone ----------------------------------------------------------------------------------------------
def player_pos(t):                                 # world position of the player at t01
    return Vector((0.0, (-20 + 90 * t) if REVEAL else 28.0, 0.0))

if REVEAL:
    yaw = lambda t: math.radians(90)  # noqa: E731
else:
    yaw = lambda t: math.radians(90 + 62 * math.sin(min(t / ev, 1.0) * math.pi * 1.5) * (1 - ease(max(0, (t - ev * 0.92) / 0.1))))  # noqa: E731

pivot = bpy.data.objects.new("pivot", None)
link(pivot, s)
me = bpy.data.meshes.new("cone")
N = 24
vs = [(0, 0, 0)] + [(RNG * math.cos(-HALF + 2 * HALF * k / N), RNG * math.sin(-HALF + 2 * HALF * k / N), 0) for k in range(N + 1)]
fs = [(0, k + 1, k + 2) for k in range(N)]
me.from_pydata(vs, [], fs)
cm, cnt, cout = new_mat("conem", blended=True)
em = cnt.n("ShaderNodeEmission", ins={"Color": (1.0, 0.85, 0.2, 1), "Strength": 2.5})
tr = cnt.n("ShaderNodeBsdfTransparent")
mx = cnt.n("ShaderNodeMixShader", ins={"Fac": 0.16})
cnt.t.links.new(tr.outputs[0], mx.inputs[1])
cnt.t.links.new(em.outputs[0], mx.inputs[2])
cnt.t.links.new(mx.outputs[0], cout.inputs[0])
me.materials.append(cm)
cone = bpy.data.objects.new("cone", me)
cone.location.z = 0.6
cone.parent = pivot
link(cone, s)
edge = emit_mat("edge", (1.0, 0.85, 0.2), 6.0)
for sg in (-1, 1):
    e = box("edge", (RNG, 0.35, 0.2), (RNG / 2 * math.cos(sg * HALF), RNG / 2 * math.sin(sg * HALF), 0.7), edge, rot=(0, 0, sg * HALF))
    e.parent = pivot
hero = load_car(0.25, "hero")
hero.scale = (2.2, 2.2, 2.2)
hm = pbr("heroc", (0.9, 0.08, 0.38), rough=0.3, emit=(1.0, 0.1, 0.45), emit_strength=0.8)
hero.data.materials.clear()
hero.data.materials.append(hm)
hero.parent = pivot
hero.rotation_euler = (0, 0, -math.pi / 2)

# visibility simulation ----------------------------------------------------------------------------------------
def rect_hit(p, q, b, pad=0.0):
    """segment p→q (2D) vs building footprint."""
    x0, x1, y0, y1 = b["cx"] - b["w"] / 2 - pad, b["cx"] + b["w"] / 2 + pad, b["cy"] - b["d"] / 2 - pad, b["cy"] + b["d"] / 2 + pad
    t0, t1 = 0.0, 1.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    for pp, dd, lo, hi in ((p[0], dx, x0, x1), (p[1], dy, y0, y1)):
        if abs(dd) < 1e-9:
            if pp < lo or pp > hi:
                return False
        else:
            a, b2 = (lo - pp) / dd, (hi - pp) / dd
            if a > b2:
                a, b2 = b2, a
            t0, t1 = max(t0, a), min(t1, b2)
            if t0 > t1:
                return False
    return True


near = [b for b in C.bld if abs(b["cx"]) < 190 and -90 < b["cy"] < 260]
for b in near:
    b["objs"] = [b["obj"]] + b["tiers"]
    b["gc"], b["gr"] = [], []
    for o in b["objs"]:
        for mat, lst in ((wm_c, b["gc"]), (wm_r, b["gr"])):
            md = o.data.copy()
            md.materials.clear()
            md.materials.append(mat)
            md.transform(Matrix.Diagonal((o.scale.x, o.scale.y, o.scale.z, 1.0)))
            tw = bpy.data.objects.new("g", md)
            tw.location = o.location.copy()
            m = tw.modifiers.new("wf", "WIREFRAME")
            m.thickness, m.use_replace, m.use_even_offset = (0.22 if mat is wm_c else 0.4), True, True
            link(tw, s)
            lst.append(tw)
    b["v"], b["r"], b["g"] = 1.0, 0.0, 0.0
    b["h0"] = [o.scale.z for o in b["objs"]]

for f in range(1, NF + 1):
    t = (f - 1) / max(1, NF - 1)
    P = player_pos(t)
    pivot.location = P
    pivot.rotation_euler = (0, 0, yaw(t))
    pivot.keyframe_insert("location", frame=f)
    pivot.keyframe_insert("rotation_euler", frame=f)
    yw = yaw(t)
    occl_on = REVEAL or t >= ev
    for b in near:
        dxy = (b["cx"] - P.x, b["cy"] - P.y)
        d = math.hypot(*dxy)
        ang = math.atan2(dxy[1], dxy[0]) - yw
        ang = (ang + math.pi) % (2 * math.pi) - math.pi
        spread = math.atan2(max(b["w"], b["d"]) * 0.5, max(d, 1))
        inc = (abs(ang) < HALF + spread) and d < RNG + 10 or d < 14
        occ = False
        if inc and occl_on and d > 20:
            for o2 in near:
                if o2 is b or o2["h"] < b["h"] * 0.55:
                    continue
                if math.hypot(o2["cx"] - P.x, o2["cy"] - P.y) < d - 3 and rect_hit((P.x, P.y), (b["cx"], b["cy"]), o2, pad=-2.0):
                    occ = True
                    break
        vis = 1.0 if inc and not occ else 0.0
        b["v"] += (vis - b["v"]) * 0.32
        red_t = 1.0 if (inc and occ) else 0.0
        b["r"] += (red_t - b["r"]) * 0.4
        for k, o in enumerate(b["objs"]):
            o.scale.z = max(0.001, b["h0"][k] * ease(b["v"], "io"))
            o.keyframe_insert("scale", frame=f, index=2)
            gz = max(0.001, 1.0 - ease(b["v"], "io"))
            gc, gr = b["gc"][k], b["gr"][k]
            rr = max(0.001, b["r"])
            gc.scale.z = max(0.001, gz * (1 - rr)) if not (inc and occ) else 0.001
            gr.scale.z = rr * max(0.001, 1.0 - 0.0)
            gc.keyframe_insert("scale", frame=f, index=2)
            gr.keyframe_insert("scale", frame=f, index=2)

# camera ------------------------------------------------------------------------------------------------------
cam = camera(s, lens=28)
if REVEAL:
    def cp(t):
        P = player_pos(t)
        k = ease(t, "io")
        return Vector((P.x - 3 + 26 * k, P.y - 13 - 90 * k, 3.4 + 140 * k))
    cam_path(cam, NF, cp, lambda t: player_pos(t) + Vector((0, 22 + 40 * ease(t, "io"), 6)))
else:
    cam_path(cam, NF, lambda t: Vector((18 * math.sin(t * 1.4), 28 - 125 - 10 * t, 125 + 12 * t)), lambda t: Vector((0, 28 + 55, 0)))
light(s, "SUN", (0, 0, 50), 1.5, color=(0.8, 0.85, 1.0), target=(0, 20, 0), name="moon")
L.post(s, bloom=0.5, bloom_threshold=1.0, bloom_size=0.6, dispersion=0.004, vignette=0.3, saturation=1.1, contrast=0.07)
save(s, blend)
