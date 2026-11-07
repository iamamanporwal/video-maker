"""blender -b -P scene.py -- <out.blend>: "What if Walter White never had cancer?" (dramatic, Breaking Bad look).

Every key time is a VO word time from out/words.json (vo.py). Walt: Sketchfab "Breaking bad - Walter White"
(rigged, CC-BY) + procedural porkpie. Props: Sketchfab CC-BY (assets/*.json). One Blender scene per set;
sets_a.py / sets_b.py build them. The Breaking Bad grade (yellow desert / sick green interiors) + grain is
applied at compose time in build.py so it can be tuned without re-rendering.

  HOOK    0.00  Heisenberg in the desert at dusk, RV behind     XRAY   3.32  lightbox; the tumor fades on "clean"
  HOSP    8.30  Walt on the hospital bed, relief                DESERT 14.22 RV + blue; vanish on "RV/desert/blue"
  ROOF   21.90  pizza on the roof → gone                        CLASS  23.65 chemistry class, clock spins 25 yrs
  CAKE   28.17  75th birthday alone                             GARAGE 33.03 box on the workbench → opens
  HAT    42.91  the hat on the table, one light                 HOOK   45.71 the hat is on his head again
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
sys.path.insert(0, HERE)
import bpy
import director as D
import look as L
import cast as C

out = sys.argv[sys.argv.index("--") + 1]
VO = json.load(open(os.path.join(HERE, "out", "words.json")))
B = VO["beats"]
W = {}
for a, b, w in VO["words"]:                             # first time each (lower, stripped) word is said
    W.setdefault(w.lower().strip(".,?!:"), a)
END = VO["words"][-1][1] + 2.6                           # hold on the final image under the title card
F = D.T
H = D.hex_lin
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
CHALK = "/System/Library/Fonts/Supplemental/Chalkboard.ttc"
random.seed(11)

base = D.reset(frames=F(END) - 1)
D.fast_eevee(base, samples=14, look="AgX - Medium High Contrast")
SHOTS = []


def shot(sc, name, t0, t1, loc0, loc1, at0, at1, lens0=30, lens1=None, shake=0.004, dof=None):
    c, l = D.camera(name, lens0, dof=dof)
    D.move(c, l, F(t0), F(t1), loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    D.cut(sc, F(t0), c)
    SHOTS.append((sc.name, F(t0), F(t1) - 1 if t1 < END else F(END) - 1))


def txt(body, size, loc, m, rot=(math.pi / 2, 0, 0), extrude=0.0, font=FONT):
    return D.text3d("t_" + body[:12], body, size, loc, m, extrude=extrude, bevel=0, font=font, rot=rot)


def pose(arm, root, keys, t0=0, t1=None):
    """[(seconds, POSE), ...] → one held NLA strip t0..t1 (default whole film)."""
    C.pose_strip(arm, root, [(max(1, F(t)), p) for t, p in keys] + [(F(t1 or END), keys[-1][1])], max(1, F(t0)),
                 F(t1 or END), blend=1)


def room(sc, w, d, h, wall, floor, ceil=None, open_side=-1):
    """Box room centred on x=0, y from -d/2..d/2; the -Y wall is left open for the cameras."""
    D.box(sc.name + "_floor", (w, d, 0.04), (0, 0, -0.02), floor)
    D.box(sc.name + "_back", (w, 0.1, h), (0, d / 2, h / 2), wall)
    for s in (-1, 1):
        D.box(sc.name + "_side", (0.1, d, h), (s * w / 2, 0, h / 2), wall)
    if ceil:
        D.box(sc.name + "_ceil", (w, d, 0.05), (0, 0, h), ceil)


def dark_world(sc, rgb="#0b0d0c", strength=1.0):
    D.world(sc, H(rgb), strength)


def spot(name, power, loc, at, size_deg=40, blend=0.5, rgb=(1, 1, 1)):
    import mathutils
    l = bpy.data.lights.new(name, "SPOT")
    l.energy, l.spot_size, l.spot_blend, l.color = power, math.radians(size_deg), blend, rgb
    o = D.link(bpy.data.objects.new(name, l))
    o.location = loc
    o.rotation_euler = (mathutils.Vector(at) - mathutils.Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def point(name, power, loc, rgb=(1, 1, 1), r=0.05):
    l = bpy.data.lights.new(name, "POINT")
    l.energy, l.color, l.shadow_soft_size = power, rgb, r
    o = D.link(bpy.data.objects.new(name, l))
    o.location = loc
    return o


def key_val(sock_owner, sock, frame, value):
    sock.default_value = value
    sock.keyframe_insert("default_value", frame=frame)


MAT = {k: L.plastic(k, H(c), rough=r, coat=0.0) for k, c, r in (
    ("white", "#ecebe6", 0.5), ("ink", "#151719", 0.5), ("steel", "#8d9399", 0.35), ("card", "#b48a5a", 0.85),
    ("paper", "#b9b2a0", 0.9), ("felt", "#141414", 0.85))}
MAT["chalk"] = D.mat("chalk", H("#e9efe6"), rough=0.9, emit=H("#e9efe6"), emit_strength=0.15)
MAT["blue"] = D.mat("blue_glow", H("#2aa8ff"), rough=0.15, emit=H("#1e9bff"), emit_strength=2.5)
MAT["flame"] = D.mat("flame", H("#ffb347"), rough=0.5, emit=H("#ff9a2e"), emit_strength=25.0)

ctx = dict(D=D, L=L, C=C, B=B, W=W, END=END, F=F, H=H, MAT=MAT, shot=shot, txt=txt, pose=pose, room=room,
           dark_world=dark_world, spot=spot, point=point, key_val=key_val, math=math, random=random, bpy=bpy,
           HERE=HERE, CHALK=CHALK, FONT=FONT)
for part in ("sets_a.py", "sets_b.py"):
    exec(open(os.path.join(HERE, part)).read(), ctx)

SHOTS.sort(key=lambda x: x[1])
json.dump(SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(SHOTS), "scenes", [s.name for s in bpy.data.scenes])
