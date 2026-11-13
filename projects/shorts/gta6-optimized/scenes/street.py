"""Boulevard shots. street: hook cruise + wire dissolve at <ev> ("not drawn"). drive: chase cam behind the hero hatchback.

blender -b -P street.py -- <shot> <out.blend> <seconds> <ev_fraction>
"""
import math, os, random, sys
import bpy
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402
from city import City, sky, PITCH  # noqa: E402
from carlib import load_car  # noqa: E402
from traffic import make_traffic, key_traffic  # noqa: E402

shot, blend, dur, ev = sys.argv[sys.argv.index("--") + 1:][:4]
dur, ev = float(dur), float(ev)
if ev < 0:
    ev = 0.55
s, NF = start(dur, samples=20, raytrace=True)
rng = random.Random(11)
sky(s)
C = City(s, 9, 9, seed=7)
LAMP = emit_mat("lamp", (1.0, 0.6, 0.25), 12.0)
PINK, CYAN, YEL = emit_mat("npink", (1.0, 0.1, 0.5), 9.0), emit_mat("ncyan", (0.1, 0.8, 1.0), 9.0), emit_mat("nyel", (1.0, 0.8, 0.2), 8.0)
metal = pbr("pole", (0.06, 0.06, 0.07), rough=0.4, metal=0.8)

# street furniture along the boulevard
for k in range(-4, 16):
    y = k * 28.0
    for side in (-1, 1):
        cyl("pole", 0.09, 8.5, (side * 8.2, y, 4.25), metal, verts=10)
        box("arm", (1.4 if side < 0 else 1.4, 0.12, 0.12), (side * 7.5, y, 8.4), metal)
        box("head", (0.9, 0.3, 0.1), (side * 6.9, y, 8.3), LAMP)
# neon signs on facades facing the boulevard
for b in C.bld:
    if abs(b["cx"]) < 40 and -40 < b["cy"] < 280 and b["h"] > 16 and rng.random() < 0.55:
        side = -1 if b["cx"] > 0 else 1                                   # face toward x=0
        fx = b["cx"] + side * (b["w"] / 2 + 0.25)
        m = rng.choice((PINK, CYAN, YEL))
        if rng.random() < 0.6:
            box("sign", (0.3, 0.5, rng.uniform(4, 9)), (fx, b["cy"] + rng.uniform(-3, 3), rng.uniform(8, 14) + 3), m)
        else:
            box("sign", (0.3, rng.uniform(3, 6), 0.7), (fx, b["cy"] + rng.uniform(-2, 2), rng.uniform(6, 16)), m)

lanes = [(-5.2, -1), (-1.9, -1), (1.9, 1), (5.2, 1)]
speed = lambda x, d: 9.0 if abs(x) > 4 else 13.0  # noqa: E731
HERO = shot == "drive"
CAM_V = 22.0 if HERO else 11.0
cars = make_traffic(s, rng, lanes, (-30, 330), 46, speed, lod=0.06, nf=NF,
                    camera_clear=(1.9, -30 + 0))
key_traffic(cars, NF)
D.sun("sun", 4.5, (0.25, -0.9, -0.14), (1.0, 0.55, 0.28), angle=2.0) if hasattr(D, "sun") else None

cam = camera(s, lens=22 if not HERO else 30)
if HERO:
    hero = load_car(1.0, "hero")
    key(hero, "location", lambda t, f: Vector((1.9, -10 + CAM_V * (f - 1) / FPS, 0)), NF)
    key(hero, "rotation_euler", lambda t, f: Vector((0.012 * math.sin(f * 0.3), 0, 0.012 * math.sin(f * 0.17))), NF)
    # headlights/tail for hero
    for sx in (-0.68, 0.68):
        box("hl", (0.34, 0.06, 0.13), (1.9 + sx, -10 - 2.1, 0.62), emit_mat("htail", (1, 0.04, 0.02), 7.0))
    for sx in (-0.68, 0.68):
        lamp = box("hl", (0.34, 0.06, 0.13), (sx, -2.1, 0.62), emit_mat("htail2", (1, 0.04, 0.02), 7.0))
        lamp.parent = hero
    cam_path(cam, NF, lambda t: Vector((1.9 + 0.5 * math.sin(t * 5), -10 + CAM_V * t * dur - 6.8, 2.3 - 0.4 * ease(t, "out"))),
             lambda t: Vector((1.9, -10 + CAM_V * t * dur + 6, 1.0)))
else:
    key_pos = lambda t: Vector((3.2 + 0.25 * math.sin(t * 3.0), -34 + CAM_V * t * dur, 1.55 + 0.06 * math.sin(t * 7)))  # noqa: E731
    cam_path(cam, NF, key_pos, lambda t: key_pos(t) + Vector((-0.4 + 0.5 * math.sin(t * 2.0), 40, 6.0 + 2.0 * ease(t, "io"))))

    # "not drawn": wire twins + sinking solids, sweeping away from the camera at ev
    tev = ev * dur
    cy_ev = -34 + CAM_V * tev
    wm = emit_mat("wire", (0.2, 0.85, 1.0), 3.2)
    pending = []
    for b in C.bld:
        if -60 < b["cx"] < 60 and cy_ev - 70 < b["cy"] < cy_ev + 260:
            pending.append(b)
    for b in pending:
        for o in [b["obj"]] + b["tiers"]:
            md = o.data.copy()
            md.materials.clear()
            md.materials.append(wm)
            md.transform(Matrix.Diagonal((o.scale.x, o.scale.y, o.scale.z, 1.0)))      # real size → absolute wire thickness
            tw = bpy.data.objects.new("w", md)
            tw.location = o.location.copy()
            m = tw.modifiers.new("wf", "WIREFRAME")
            m.thickness, m.use_replace, m.use_even_offset = 0.28, True, True
            link(tw, s)
            b.setdefault("twins", []).append((o, tw))
            d = max(0.0, (b["cy"] - cy_ev) / 260.0 + abs(b["cx"]) / 400.0)
            t0 = tev + d * 1.1
            h0 = o.scale.z
            ws = Vector((1.0, 1.0, 1.0))

            def sc(t, f, o=o, tw=tw, t0=t0, h0=h0, ws=ws):
                u = (f - 1) / FPS
                k = min(1.0, max(0.0, (u - t0) / 0.22))
                return k
            for f in range(1, NF + 1):
                k = sc(0, f)
                o.scale.z = max(0.001, h0 * (1.0 - ease(k, "in") * 0.999))
                tw.scale = (ws.x, ws.y, max(0.001, ws.z * (0.05 + 0.95 * ease(k, "out"))) if k > 0 else 0.0001)
                o.keyframe_insert("scale", frame=f)
                tw.keyframe_insert("scale", frame=f)
L.post(s, bloom=0.5, bloom_threshold=1.1, bloom_size=0.6, dispersion=0.004, vignette=0.28, saturation=1.1, contrast=0.07)
save(s, blend)
