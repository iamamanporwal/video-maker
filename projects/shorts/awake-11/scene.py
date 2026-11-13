"""blender -b -P scene.py -- <out.blend>: "What if you stayed awake for 11 days?" (Randy Gardner, 1963-64), PS2 look.

Timeline seconds (VO starts at VO_AT = 0.2 s). Sets (scenes):
  BED    0.0 hook: bloodshot eyes propped open with matchsticks, days fly by; 2.3 yawn; 12.5 boombox headbang;
         17.4 moody → faceplant; 32.7 264 hours; 35.0 collapses onto bed; 36.2 sleeps 14 h; 41.4 years later: insomnia
  FAIR   4.8 1963 science fair booth "HOW LONG CAN YOU STAY AWAKE?"; 11.4 cola cans pile up
  BATH   13.3 cold shower           VOID 14.6 brain glitch (x-ray); 37.9 record book stamped; 40.0 danger sign
  STREET 19.3 day 4: shakes hands with a street sign that grows a face
  FIELD  22.4 "famous football player"     CLINIC 25.3 count down by sevens → 65 → "?"
Helpers (rig, eyes, shots) are copied from projects/shorts/sneeze-eyes/scene.py.
"""
import math, os, random, re, sys, json
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
import bpy
import director as D
import look as L
import ps2 as P

out = sys.argv[sys.argv.index("--") + 1]
A = lambda name: os.path.join(HERE, "assets", name)
ERIC_S = 1.82 / 186.865
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
END = 46.4
T = D.T
H = D.hex_lin
random.seed(7)

base = D.reset(w=360, h=640, frames=T(END) - 1)
P.setup(base)
SHOTS = []

# ---------------------------------------------------------------- materials (matte, PS2)
def flat(name, hexc, emit=0.0):
    return D.mat(name, H(hexc), rough=1.0, emit=H(hexc) if emit else None, emit_strength=emit, spec=0.1)


EYE_W = flat("eye_white", "#f4f1ea", 0.15)
IRIS = flat("iris", "#3d86d9", 0.2)
PUPIL = flat("pupil", "#060606")
CORD = flat("cord", "#c4313f", 0.15)
HOLE = flat("hole", "#1a0606")
SKIN = flat("lid", "#b98468")
LASH = flat("lash", "#2a1a12")
YEL = flat("yel", "#f8e800", 1.2)
WHITE_E = flat("white_e", "#ffffff", 1.5)
RED_E = flat("red_e", "#ff2a2a", 1.5)
GERM = flat("germ", "#5ee34a", 0.6)
SPRAY = flat("spray", "#d9f2ff", 0.8)
wood = L.pbr("wood", "wood_table_001", scale=1.5)


def txt(body, size, loc, m, rot=(math.pi / 2, 0, 0), extrude=0.06):
    return D.text3d("t_" + body[:10], body, size, loc, m, extrude=extrude, bevel=size * 0.03, font=FONT, rot=rot)


def pop(o, t, scale=1.0, dur=0.25):
    s = tuple(o.scale) if scale is None else (scale,) * 3
    D.key(o, "scale", 1, (0, 0, 0))
    D.overshoot(o, "scale", T(t), T(t + dur), (0, 0, 0), s, 1.18)


def vanish(o, t):
    D.key(o, "scale", T(t) - 1, tuple(o.scale))
    D.key(o, "scale", T(t), (0, 0, 0))


def shot(sc, name, t0, t1, loc0, loc1, at0, at1, lens0=24, lens1=None, shake=0.0, parent=None):
    c, l = D.camera(name, lens0)
    if parent:
        c.parent = l.parent = parent
    D.move(c, l, T(t0), T(t1), loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    P.ps2_camera(c, c.data.lens)
    D.cut(sc, T(t0), c)
    SHOTS.append((sc.name, T(t0), T(t1) - 1))
    return c, l


def cyl_between(name, a, b, r, m, verts=8):
    a, b = Vector(a), Vector(b)
    o = D.cyl(name, r, (b - a).length, (a + b) / 2, m=m, verts=verts)
    o.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return o


def upd():
    """Refresh EVERY set's depsgraph: objects built into a non-context set otherwise keep stale matrix_world."""
    for sc in bpy.data.scenes:
        sc.view_layers[0].update()


def glb(path, keep=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    for o in new:
        D.adopt(o)
    upd()
    meshes = [o for o in new if o.type == "MESH" and (keep is None or keep(o))]
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in new:
        if o not in meshes:
            bpy.data.objects.remove(o)
    for o in meshes:
        o.data = o.data.copy() if o.data.users > 1 else o.data
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix()
    return meshes


def bounds(objs):
    upd()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def prop(path, size, axis, loc, rotz=0.0, keep=None, tris=None, name="prop"):
    """Import a glb, re-centre (bottom at z=0), scale so extent[axis] == size, group under an empty at loc."""
    ms = glb(path, keep)
    lo, hi = bounds(ms)
    s = size / (hi - lo)[axis]
    off = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    g = D.empty(name, loc)
    g.rotation_euler = (0, 0, rotz)
    for o in ms:
        o.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation(-off))
        o.parent = g
        if tris:
            P.lowpoly(o, tris, flat=True)
    return g, ms


# ---------------------------------------------------------------- Eric rig (from learn-blender-hindi)
def own_vl(o):
    return o.users_scene[0].view_layers[0]


def aim_limb(arm, n, world_dir, frame, fwd=None):
    pb = D.bone(arm, n)
    own_vl(arm).update()
    inv = arm.matrix_world.to_3x3().inverted()
    cur = (pb.children[0].head - pb.head).normalized()
    tgt = (inv @ Vector(world_dir)).normalized()
    if n in ("Neck", "Head"):
        rest = (pb.children[0].bone.head_local - pb.bone.head_local).normalized()
        up = (inv @ (UPV[arm.name])).normalized()
        tgt = up.rotation_difference(tgt) @ rest
    m = pb.matrix.copy()
    nm = (cur.rotation_difference(tgt).to_matrix() @ m.to_3x3()).to_4x4()
    nm.translation = m.translation
    pb.matrix = nm
    own_vl(arm).update()
    eyes = [arm.pose.bones.get(e) for e in ("eye_l_011", "eye_r_013")]
    if n == "Head" and fwd is not None and all(eyes):
        face = (eyes[0].head + eyes[1].head) / 2 - pb.head
        want = (inv @ Vector(fwd)).normalized()
        a = (face - face.project(tgt)).normalized()
        b = (want - want.project(tgt)).normalized()
        ang = math.atan2(a.cross(b).dot(tgt), a.dot(b))
        m = pb.matrix.copy()
        nm = (Matrix.Rotation(ang, 3, tgt) @ m.to_3x3()).to_4x4()
        nm.translation = m.translation
        pb.matrix = nm
        own_vl(arm).update()
    pb.keyframe_insert("rotation_quaternion", frame=frame)


UPV = {}


def pose_strip(arm, root, keys, f0, f1, blend=2):
    """Pose dicts are in the character's own frame (rest faces -Y, up +Z); rotated by the root's world rotation."""
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions.new(f"{arm.name}_pose_{f0}")
    ad.use_nla = False
    ad.action = act
    R = root.matrix_world.to_quaternion()
    UPV[arm.name] = R @ Vector((0, 0, 1))
    for fr, dirs in keys:
        arm.users_scene[0].frame_set(fr)
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
        own_vl(arm).update()
        for n, d in (dirs | {k: v for k, v in HEAD_UP.items() if k not in dirs}).items():
            aim_limb(arm, n, R @ Vector(d), fr, fwd=R @ Vector((0, -1, 0)))
    ad.action = None
    ad.use_nla = True
    tr = ad.nla_tracks.new()
    st = tr.strips.new(act.name, int(f0), act)
    st.action_frame_start, st.action_frame_end = f0, f1
    st.frame_start, st.frame_end = f0, f1
    st.blend_in = st.blend_out = blend
    st.extrapolation = "NOTHING"
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)


REN = {"hip": "Hips", "spine_01": "Spine", "spine_02": "Spine1", "spine_03": "Spine2", "neck": "Neck", "head": "Head",
       "jaw": "Jaw"}
for _s, _S in (("l", "Left"), ("r", "Right")):
    REN |= {f"shoulder_{_s}": f"{_S}Shoulder", f"upperarm_{_s}": f"{_S}Arm", f"lowerarm_{_s}": f"{_S}ForeArm",
            f"hand_{_s}": f"{_S}Hand", f"upperleg_{_s}": f"{_S}UpLeg", f"lowerleg_{_s}": f"{_S}Leg", f"foot_{_s}": f"{_S}Foot"}


def man(name, loc, yaw=0.0, scale=1.0, rot=None):
    r, arm, body = D.import_char(A("eric.glb"), name)
    for b in arm.data.bones:
        bn = re.sub(r"_\d+$", "", b.name)
        if bn in REN:
            b.name = REN[bn]
    arm.scale = (ERIC_S,) * 3
    r.location, r.rotation_euler, r.scale = loc, rot or (0, 0, yaw), (scale,) * 3
    for b in body:
        P.lowpoly(b, 6000)
    own_vl(arm).update()
    return r, arm, body


HEAD_UP = {"Neck": (0, -0.08, 1), "Head": (0, -0.12, 1)}
STAND = {"LeftUpLeg": (0.04, 0, -1), "RightUpLeg": (-0.04, 0, -1), "LeftLeg": (0, 0.03, -1), "RightLeg": (0, 0.03, -1),
         "Spine": (0, 0.02, 1), "LeftArm": (0.22, 0.02, -1), "RightArm": (-0.22, 0.02, -1),
         "LeftForeArm": (0.08, -0.12, -1), "RightForeArm": (-0.08, -0.12, -1)}
AAH = STAND | {"Spine": (0, 0.12, 1), "Neck": (0, 0.3, 1), "Head": (0, 0.7, 1),
               "LeftArm": (0.35, 0.05, -1), "RightArm": (-0.35, 0.05, -1)}
CHOO = STAND | {"Spine": (0, -0.2, 1), "Neck": (0, -0.3, 1), "Head": (0, -0.45, 1),
                "LeftArm": (0.3, 0.25, -1), "RightArm": (-0.3, 0.25, -1)}
HOLD = STAND | {"LeftArm": (0.15, -0.75, -0.6), "RightArm": (-0.15, -0.75, -0.6),
                "LeftForeArm": (-0.5, 0.25, 0.85), "RightForeArm": (0.5, 0.25, 0.85)}
HOLD_CHOO = HOLD | {"Spine": (0, -0.15, 1), "Neck": (0, -0.25, 1), "Head": (0, -0.35, 1)}
PINCH = STAND | {"RightArm": (-0.05, -0.9, -0.42), "RightForeArm": (0.62, 0.05, 0.72)}
PINCH_JOLT = PINCH | {"Spine": (0, -0.12, 1), "Neck": (0, -0.25, 1), "Head": (0, -0.35, 1)}
SIT = {"LeftUpLeg": (0.12, -1, 0.02), "RightUpLeg": (-0.12, -1, 0.02), "LeftLeg": (0, -0.15, -1), "RightLeg": (0, -0.15, -1),
       "Spine": (0, 0.1, 1), "LeftArm": (0.25, -0.75, -0.6), "RightArm": (-0.25, -0.75, -0.6),
       "LeftForeArm": (-0.05, -1, 0.15), "RightForeArm": (0.05, -1, 0.15)}
SIT_PINCH = SIT | {"RightArm": (-0.05, -0.9, -0.42), "RightForeArm": (0.62, 0.05, 0.72)}
SIT_JOLT = SIT_PINCH | {"Spine": (0, -0.1, 1), "Neck": (0, -0.3, 1), "Head": (0, -0.4, 1)}
WHISPER = STAND | {"Spine": (-0.3, 0, 1), "Neck": (-0.35, -0.1, 1), "Head": (-0.4, -0.1, 1),
                   "RightArm": (-0.3, -0.7, -0.2), "RightForeArm": (0.35, -0.3, 0.9)}
LISTEN = STAND | {"Neck": (0.15, -0.05, 1), "Head": (0.3, -0.1, 1)}
CAMOP = STAND | {"Spine": (0, -0.15, 1), "LeftArm": (0.2, -0.8, -0.55), "RightArm": (-0.2, -0.8, -0.55),
                 "LeftForeArm": (-0.1, -1, 0.1), "RightForeArm": (0.1, -1, 0.1), "Head": (0, -0.3, 1)}


# ---------------------------------------------------------------- procedural eyes
def eyeball(name, r, parent=None, loc=(0, 0, 0)):
    g = D.empty(name, loc, parent=parent)
    for nm, rr, y, sy, m in (("w", r, 0, 1, EYE_W), ("i", r * 0.55, -r * 0.86, 0.32, IRIS), ("p", r * 0.27, -r * 0.99, 0.3, PUPIL)):
        o = D.sphere(f"{name}_{nm}", rr, (0, 0, 0), m=m, seg=14, rings=8)
        for p in o.data.polygons:
            p.use_smooth = False
        o.parent = g
        o.location = (0, y, 0)
        o.scale = (1, sy, 1)
    return g


def eyes_on(arm, root, r=0.0165):
    """Two eyeballs (+ cords, dark sockets, lids) bone-parented to Head. Ball location is keyed in socket space:
    (0, -d, -droop) = d metres out of the face. Returns {'balls','holes','lids','sockets'}."""
    own_vl(arm).update()
    R = root.matrix_world.to_quaternion().to_matrix().to_4x4()
    res = {"balls": [], "holes": [], "lids": [], "sockets": []}
    for side, bn in (("L", "eye_l_011"), ("R", "eye_r_013")):
        p = arm.matrix_world @ arm.data.bones[bn].head_local
        p = p + R.to_3x3() @ Vector((0, -0.004 * root.scale.x, 0))
        s = D.empty(f"{arm.name}_sock{side}", (0, 0, 0))
        s.parent, s.parent_type, s.parent_bone = arm, "BONE", "Head"
        own_vl(arm).update()
        s.matrix_world = Matrix.Translation(p) @ R @ Matrix.Scale(root.scale.x, 4)
        b = eyeball(f"{arm.name}_eye{side}", r, parent=s)
        hole = D.sphere(f"{arm.name}_hole{side}", r * 1.08, (0, 0, 0), m=HOLE, seg=10, rings=6)
        hole.parent, hole.location, hole.scale = s, (0, -0.002, 0), (0, 0, 0)
        cord = D.cyl(f"{arm.name}_cord{side}", 0.0035, 1.0, (0, 0, 0), m=CORD, verts=6)
        cord.data.transform(Matrix.Rotation(-math.pi / 2, 4, "X") @ Matrix.Translation((0, 0, 0.5)))  # 0→1 along +Y
        cord.parent = s
        c = cord.constraints.new("STRETCH_TO")
        c.target, c.rest_length, c.volume = b, 1.0, "NO_VOLUME"
        lid = D.empty(f"{arm.name}_lid{side}", (0, 0, 0), parent=s)
        lo = D.sphere(f"{arm.name}_lidm{side}", r * 1.12, (0, 0, 0), m=SKIN, seg=12, rings=8)
        lo.parent = lid
        lo.location = (0, -0.002, 0)
        la = D.box(f"{arm.name}_lash{side}", (r * 2.0, 0.002, 0.0025), (0, 0, 0), LASH)
        la.parent, la.location = lid, (0, -r * 1.12, 0)
        lid.scale = (0, 0, 0)
        res["balls"].append(b)
        res["holes"].append(hole)
        res["lids"].append(lid)
        res["sockets"].append(s)
    return res


def ball_keys(E, keys):
    """keys: [(t, (x, y, z), spin_deg)] applied to both eyes (x mirrored), constant interpolation where flagged."""
    for i, b in enumerate(E["balls"]):
        sx = 1 if i == 0 else -1
        for t, (x, y, z), spin in keys:
            D.key(b, "location", T(t), (x * sx, y, z))
            D.key(b, "rotation_euler", T(t), (math.radians(spin * 0.6), 0, math.radians(spin * sx)))


def holes(E, spans):
    for h in E["holes"]:
        D.key(h, "scale", 1, (0, 0, 0))
        for a, b in spans:
            D.key(h, "scale", T(a) - 1, (0, 0, 0), "CONSTANT")
            D.key(h, "scale", T(a), (1, 0.5, 1), "CONSTANT")
            D.key(h, "scale", T(b), (0, 0, 0), "CONSTANT")


def blink(E, t_close, t_open, frames=2):
    for lid in E["lids"]:
        D.key(lid, "scale", T(t_close) - frames - 1, (0, 0, 0), "CONSTANT")
        D.key(lid, "scale", T(t_close) - frames, (1, 1, 0.0))
        D.key(lid, "scale", T(t_close), (1, 1, 1))
        D.key(lid, "scale", T(t_open), (1, 1, 1))
        D.key(lid, "scale", T(t_open) + frames, (1, 1, 0.0), "CONSTANT")
        D.key(lid, "scale", T(t_open) + frames + 1, (0, 0, 0))


def spray(name, origin, direction, t, n=26, spread=0.35, dist=0.9, dur=0.35):
    o, d = Vector(origin), Vector(direction).normalized()
    for i in range(n):
        s = D.ico(f"{name}{i}", random.uniform(0.004, 0.011), origin, m=SPRAY, sub=1)
        jitter = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.6, 0.6))) * spread
        end = o + (d + jitter).normalized() * dist * random.uniform(0.5, 1.1) + Vector((0, 0, -0.15))
        D.key(s, "scale", 1, (0, 0, 0))
        D.key(s, "scale", T(t) - 1, (0, 0, 0), "CONSTANT")
        D.key(s, "scale", T(t), (1, 1, 1))
        D.key(s, "location", T(t), o)
        D.key(s, "location", T(t + dur * random.uniform(0.7, 1.2)), end)
        D.key(s, "scale", T(t + dur * 1.3), (1, 1, 1), "CONSTANT")
        D.key(s, "scale", T(t + dur * 1.3) + 1, (0, 0, 0))


def mouth_of(arm, root):
    own_vl(arm).update()
    e = [arm.matrix_world @ arm.data.bones[b].head_local for b in ("eye_l_011", "eye_r_013")]
    m = (e[0] + e[1]) / 2
    return m + root.matrix_world.to_quaternion() @ Vector((0, -0.09, -0.085)) * root.scale.x



# ================================================================= look tweaks: bloodshot, tired eyes
_b = EYE_W.node_tree.nodes["Principled BSDF"]
_b.inputs["Base Color"].default_value = (*H("#f2c9c0"), 1)
_b.inputs["Emission Color"].default_value = (*H("#ff9a8a"), 1)
_b.inputs["Emission Strength"].default_value = 0.25
BAG = flat("bag", "#6b4656")
MATCH = flat("match", "#d9b27a")
TIP = flat("tip", "#c0282a", 0.3)
GOLD = flat("gold", "#ffc21a", 1.0)
PINK = flat("brain", "#ff7fb0", 1.2)
GREEN_S = flat("signg", "#1f7a3a", 0.2)


def tired(E, arm, matches_until=None):
    for i, s in enumerate(E["sockets"]):
        bag = D.sphere(f"{arm.name}_bag{i}", 0.012, (0, 0, 0), m=BAG, seg=10, rings=6)
        bag.parent, bag.location, bag.scale = s, (0, -0.006, -0.016), (1.4, 0.5, 0.45)
        if matches_until:
            g = D.empty(f"{arm.name}_match{i}", (0, -0.0175, 0), parent=s)
            st = D.box(f"{arm.name}_stick{i}", (0.004, 0.004, 0.046), (0, 0, 0), MATCH)
            st.parent, st.location = g, (0, 0, 0)
            tp = D.sphere(f"{arm.name}_tip{i}", 0.003, (0, 0, 0), m=TIP, seg=6, rings=4)
            tp.parent, tp.location = g, (0, 0, 0.024)
            D.key(g, "scale", 1, (1, 1, 1), "CONSTANT")
            D.key(g, "scale", T(matches_until), (0, 0, 0), "CONSTANT")


def keyroot(o, path, keys):
    """[(t, value, interp)] in time order."""
    for t, v, it in keys:
        D.key(o, path, T(t), v, it)


def hide_until(objs, t_show, t_hide=None):
    for o in objs:
        s = tuple(o.scale)
        D.key(o, "scale", 1, (0, 0, 0), "CONSTANT")
        D.key(o, "scale", T(t_show), s, "CONSTANT")
        if t_hide:
            D.key(o, "scale", T(t_hide), (0, 0, 0), "CONSTANT")


YAWN = STAND | {"Spine": (0, 0.15, 1), "Neck": (0, 0.3, 1), "Head": (0, 0.65, 1), "LeftArm": (0.45, 0.05, 0.9),
                "RightArm": (-0.45, 0.05, 0.9), "LeftForeArm": (0.1, 0.1, 1), "RightForeArm": (-0.1, 0.1, 1)}
HB_DOWN = STAND | {"Spine": (0, -0.15, 1), "Neck": (0, -0.4, 1), "Head": (0, -0.75, 0.7),
                   "LeftArm": (0.4, -0.3, -0.8), "RightArm": (-0.4, -0.3, -0.8)}
HB_UP = STAND | {"Neck": (0, 0.15, 1), "Head": (0, 0.35, 1), "LeftArm": (0.5, -0.2, -0.7), "RightArm": (-0.5, -0.2, -0.7)}
ANGRY = STAND | {"Spine": (0, -0.08, 1), "Neck": (0, -0.2, 1), "Head": (0, -0.35, 1),
                 "LeftArm": (0.3, -0.15, -1), "RightArm": (-0.3, -0.15, -1), "LeftForeArm": (-0.4, -0.8, 0.2),
                 "RightForeArm": (0.4, -0.8, 0.2)}
TRIP = STAND | {"LeftArm": (0.3, -0.9, 0.3), "RightArm": (-0.3, -0.9, 0.3), "LeftForeArm": (0.1, -1, 0.3),
                "RightForeArm": (-0.1, -1, 0.3), "LeftUpLeg": (0.04, 0.3, -1)}
SLUMP = STAND | {"Spine": (0, -0.2, 1), "Neck": (0, -0.35, 1), "Head": (0, -0.5, 0.9),
                 "LeftArm": (0.15, -0.05, -1), "RightArm": (-0.15, -0.05, -1)}
FALLBACK = STAND | {"LeftArm": (0.6, -0.4, 0.7), "RightArm": (-0.6, -0.4, 0.7), "Head": (0, -0.2, 1)}
SHIVER = STAND | {"Spine": (0, -0.12, 1), "LeftArm": (0.25, -0.5, -0.8), "RightArm": (-0.25, -0.5, -0.8),
                  "LeftForeArm": (-0.8, -0.3, 0.5), "RightForeArm": (0.8, -0.3, 0.5), "Head": (0, -0.3, 1)}
PROUD = STAND | {"RightArm": (-0.4, -0.5, 0.2), "RightForeArm": (-0.1, -0.3, 1)}
SHAKE = STAND | {"RightArm": (-0.12, -0.9, -0.45), "RightForeArm": (-0.05, -1, 0.05), "Head": (0, -0.05, 1)}
CHEER = STAND | {"LeftArm": (0.6, -0.15, 0.8), "RightArm": (-0.45, -0.1, 0.9), "LeftForeArm": (0.5, -0.15, 0.85),
                 "RightForeArm": (-0.15, -0.05, 1), "Head": (0, 0.25, 1)}
CLIPB = STAND | {"LeftArm": (0.2, -0.6, -0.75), "LeftForeArm": (-0.4, -0.9, 0.2), "RightArm": (-0.2, -0.6, -0.75),
                 "RightForeArm": (0.4, -0.9, 0.2)}
BLANK = STAND | {"Neck": (0.1, -0.05, 1), "Head": (0.35, -0.15, 1), "LeftArm": (0.12, 0.02, -1), "RightArm": (-0.12, 0.02, -1)}


def window_flicker(m, t0, t1, step, day="#ffd88a", night="#132657"):
    e = m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
    e.default_value = (*H(night), 1)
    e.keyframe_insert("default_value", frame=1)
    e.keyframe_insert("default_value", frame=T(t0) - 1)
    i, t = 0, t0
    while t < t1:
        e.default_value = (*H(day if i % 2 == 0 else night), 1)
        e.keyframe_insert("default_value", frame=T(t))
        t += step
        i += 1
    e.default_value = (*H(night), 1)
    e.keyframe_insert("default_value", frame=T(t1))
    for fc in D._fcurves(m.node_tree.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "CONSTANT"


def clock(name, loc, spins):
    """Wall clock facing -Y; spins = [(t, turns)] for the minute hand."""
    WH = flat("clockface", "#f4f1ea", 0.4)
    D.cyl(name, 0.32, 0.05, loc, (math.pi / 2, 0, 0), m=WH, verts=16)
    D.torus(name + "_rim", 0.32, 0.03, Vector(loc) + Vector((0, -0.02, 0)), rot=(math.pi / 2, 0, 0), m=flat("crim", "#22252e"))
    hand = D.empty(name + "_hand", Vector(loc) + Vector((0, -0.04, 0)))
    D.box(name + "_hm", (0.03, 0.01, 0.26), (0, 0, 0.11), flat("chand", "#111111")).parent = hand
    for t, n in spins:
        D.key(hand, "rotation_euler", T(t), (0, math.radians(n * 360), 0))
    for fc in D._fcurves(hand.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"


def rain_like(name, size, loc, count, speed, mat, life=30, t0=1, t1=None, streak=(0.006, 0.006, 0.25)):
    st = D.box(name + "_st", streak, (0, 0, -80), mat)
    em = D.box(name + "_em", size, loc, None)
    em.modifiers.new(name, "PARTICLE_SYSTEM")
    ps = em.particle_systems[0].settings
    ps.count, ps.frame_start, ps.frame_end, ps.lifetime = count, T(t0) - 40, T(t1 or END), life
    ps.emit_from, ps.normal_factor = "FACE", 0.0
    ps.object_align_factor = (0, 0, -speed)
    ps.effector_weights.gravity = 0.0
    ps.render_type, ps.instance_object, ps.particle_size = "OBJECT", st, 1.0
    em.show_instancer_for_render = False
    return em


# ================================================================= BED: night bedroom (hook, yawn, music, trip, collapse, insomnia)
bed_sc = L.new_set("BED", main=True)
P.flat_light(bed_sc, "#0b1030", ambient=1.0, sun=0.9)
D.room("bedroom", (0.5, 0.8, 1.5), (7, 7, 3), L.pbr("bwall", "painted_plaster_wall", scale=0.8, tint=H("#4a4f9e"), tint_amount=0.9))
D.box("bfloor", (7, 7, 0.02), (0.5, 0.8, 0.0), L.pbr("bfl", "laminate_floor_02", scale=0.8))
D.area_light("lamp", 90, (-1.5, -1.0, 2.6), (0.3, 0.6, 1.0), size=1.5, rgb=H("#ffd6a0"))
WIN = D.mat("bwin", H("#0b1530"), rough=1, emit=H("#132657"), emit_strength=1.2)
D.box("bwinf", (1.7, 0.06, 1.3), (-1.4, 4.27, 1.7), flat("bwinframe", "#e8e4dc"))
D.box("bwin", (1.5, 0.05, 1.1), (-1.4, 4.24, 1.7), WIN)
window_flicker(WIN, 0.25, 2.3, 0.1)
clock("wclock", (0.9, 4.25, 2.3), [(0, 0), (0.2, 0), (2.3, 11 * 24), (32.7, 11 * 24), (35.0, 11 * 24 + 6), (36.3, 11 * 24 + 6),
                                  (37.9, 11 * 24 + 20), (41.4, 11 * 24 + 20), (46.4, 11 * 24 + 21)])
# bed along +Y (pillow end +Y), mattress top 0.6
BX, BY0, BY1 = 1.3, 0.55, 2.65
D.box("bframe", (1.15, BY1 - BY0, 0.3), (BX, (BY0 + BY1) / 2, 0.2), wood)
D.box("bhead", (1.15, 0.08, 1.0), (BX, BY1 + 0.04, 0.5), wood)
D.box("mattress", (1.05, BY1 - BY0 - 0.05, 0.25), (BX, (BY0 + BY1) / 2, 0.47), flat("matt", "#f0ece4"))
D.box("pillow", (0.6, 0.35, 0.12), (BX, BY1 - 0.25, 0.66), flat("pillowm", "#ffffff", 0.1))
D.box("blanket", (1.12, 1.35, 0.32), (BX, BY0 + 0.68, 0.76), L.pbr("blank", "fabric_pattern_07", scale=2, tint=H("#3a6fd8"), tint_amount=0.8))
D.box("dresser", (0.9, 0.5, 0.8), (-1.3, 1.2, 0.4), wood)
bbox = D.box("boombox", (0.6, 0.22, 0.32), (-1.3, 1.15, 0.96), flat("bbm", "#2b2b30"))
spk = []
for x in (-0.17, 0.17):
    sp = D.cyl("speaker", 0.1, 0.03, (-1.3 + x, 1.03, 0.95), (math.pi / 2, 0, 0), m=flat("spk", "#888a92", 0.2), verts=10)
    spk.append(sp)
    for i, t in enumerate([12.4 + k * 0.2 for k in range(6)]):
        D.key(sp, "scale", T(t), (1.35, 1.35, 1) if i % 2 == 0 else (1, 1, 1))
D.box("poster", (0.8, 0.02, 1.1), (2.6, 4.25, 1.8), flat("posterm", "#e04a3a", 0.3))

randy, rarm, _ = man("randy", (0, 0, 0))
RE = eyes_on(rarm, randy)
tired(RE, rarm, matches_until=2.3)
pose_strip(rarm, randy, [
    (1, STAND), (T(2.3), STAND), (T(2.7), YAWN), (T(4.5), YAWN), (T(4.9), STAND), (T(12.3), STAND),
    (T(12.45), HB_DOWN), (T(12.65), HB_UP), (T(12.85), HB_DOWN), (T(13.05), HB_UP), (T(13.25), HB_DOWN), (T(13.4), STAND),
    (T(17.3), STAND), (T(17.5), ANGRY), (T(18.35), ANGRY), (T(18.55), TRIP), (T(32.6), TRIP),
    (T(32.7), SLUMP), (T(35.0), SLUMP), (T(35.2), FALLBACK), (T(35.5), FALLBACK)], 1, T(35.5), blend=1)
keyroot(randy, "location", [(0, (0, 0, 0), "CONSTANT"), (32.6, (0, 0, 0), "CONSTANT"), (32.7, (BX, 0.3, 0), None),
                            (35.0, (BX, 0.3, 0), None), (35.4, (BX, 0.35, 0.45), "CONSTANT")])
keyroot(randy, "rotation_euler", [(0, (0, 0, 0), "CONSTANT"), (18.45, (0, 0, 0), None), (18.85, (math.radians(84), 0, 0), "CONSTANT"),
                                  (32.7, (0, 0, 0), None), (35.0, (0, 0, 0), None), (35.4, (math.radians(-80), 0, 0), "CONSTANT")])
D.key(randy, "scale", 1, (1, 1, 1), "CONSTANT")
D.key(randy, "scale", T(35.45), (0, 0, 0), "CONSTANT")
blink(RE, 5.0, 5.15)
# the sleeper (swapped in when Randy lands on the bed)
sl, slarm, _ = man("sleeper", (BX, 0.62, 0.6 + 0.12), rot=(-math.pi / 2, 0, 0))
SE = eyes_on(slarm, sl)
tired(SE, slarm)
pose_strip(slarm, sl, [(1, STAND), (T(END), STAND)], 1, T(END), blend=1)
D.key(sl, "scale", 1, (0, 0, 0), "CONSTANT")
D.key(sl, "scale", T(35.45), (1, 1, 1), "CONSTANT")
blink(SE, 35.5, 42.95)
upd()
FCS = sum((s.matrix_world.translation for s in SE["sockets"]), Vector()) / 2
zz = []
for i in range(3):
    z = txt("Z", 0.16 + i * 0.07, FCS + Vector((0.18 + i * 0.16, -0.15 - i * 0.12, 0.25 + i * 0.25)), YEL, rot=(0, 0, 0), extrude=0.03)
    pop(z, 36.4 + i * 0.25, dur=0.2)
    vanish(z, 41.4)
    zz.append(z)
window_flicker(WIN, 36.3, 37.9, 0.13)
shot(bed_sc, "B1_eyes", 0.0, 1.2, (0.0, -0.55, 1.68), (0.0, -0.47, 1.68), (-0.017, -0.1, 1.67), (-0.017, -0.1, 1.67), 30, shake=0.003)
shot(bed_sc, "B2_days", 1.2, 2.3, (1.9, -2.5, 1.7), (1.7, -2.2, 1.65), (0.1, 0.8, 1.3), (0.1, 0.8, 1.3), 22)
shot(bed_sc, "B3_yawn", 2.3, 4.8, (0.55, -1.7, 1.5), (0.4, -1.35, 1.55), (0, 0, 1.45), (0, 0, 1.5), 26)
shot(bed_sc, "B4_music", 12.5, 13.3, (-0.55, -2.1, 1.45), (-0.6, -1.9, 1.4), (-0.6, 0.5, 1.15), (-0.6, 0.5, 1.15), 22, shake=0.01)
shot(bed_sc, "B5_trip", 17.4, 19.3, (2.4, -1.4, 1.3), (2.2, -1.2, 1.2), (0, -0.4, 0.9), (0, -0.5, 0.7), 24)
shot(bed_sc, "B6_264", 32.7, 35.0, (1.9, -1.9, 1.55), (1.75, -1.5, 1.5), (BX, 0.5, 1.3), (BX, 0.5, 1.3), 24)
shot(bed_sc, "B7_fall", 35.0, 36.2, (-0.3, -1.4, 1.7), (-0.2, -1.25, 1.65), (BX, 1.0, 0.9), (BX, 1.1, 0.85), 22)
shot(bed_sc, "B8_sleep", 36.2, 37.9, (BX + 0.05, 1.6, 2.9), (BX + 0.05, 1.7, 2.7), (BX, 1.75, 0.6), (BX, 1.8, 0.6), 22)
shot(bed_sc, "B9_later", 41.4, 43.0, (BX + 0.05, 1.7, 2.6), (BX + 0.05, 1.8, 2.3), (BX, 1.85, 0.6), (BX, 1.9, 0.6), 22)
shot(bed_sc, "B10_insomnia", 43.0, END, FCS + Vector((0.02, -0.12, 0.55)), FCS + Vector((0.02, -0.06, 0.42)), FCS, FCS, 26)

# ================================================================= FAIR: 1963 school science fair
fair = L.new_set("FAIR")
with L.building(fair):
    P.flat_light(fair, "#cfd8e6", ambient=1.5, sun=1.1)
    D.room("gym", (0, 2, 2.5), (14, 12, 5), L.pbr("gwall", "red_brick_03", scale=0.6, tint=H("#c9b28a"), tint_amount=0.5))
    D.box("gfloor", (14, 12, 0.02), (0, 2, 0.0), L.pbr("gfl", "laminate_floor_02", scale=0.5))
    BOARD = flat("board", "#2a5fc4", 0.15)
    for k, (x, title, col) in enumerate(((-2.6, "VOLCANO", "#c84a2a"), (0, "RANDY", "#2a5fc4"), (2.6, "PLANTS", "#3a9a4a"))):
        D.box(f"tbl{k}", (1.7, 0.75, 0.05), (x, 1.0, 0.75), flat(f"cloth{k}", "#f2f0ea"))
        D.box(f"tskirt{k}", (1.7, 0.02, 0.7), (x, 0.63, 0.38), flat(f"skirt{k}", "#d8d4cc"))
        bm = flat(f"bd{k}", col, 0.15)
        D.box(f"bdc{k}", (0.9, 0.03, 0.75), (x, 1.3, 1.15), bm)
        for sgn in (-1, 1):
            p = D.box(f"bds{k}", (0.45, 0.03, 0.75), (x + sgn * 0.62, 1.18, 1.15), bm)
            p.rotation_euler = (0, 0, math.radians(-30 * sgn))
        if title == "RANDY":
            txt("HOW LONG CAN", 0.085, (x, 1.27, 1.38), YEL, extrude=0.005)
            txt("YOU STAY", 0.085, (x, 1.27, 1.26), YEL, extrude=0.005)
            txt("AWAKE?", 0.13, (x, 1.27, 1.11), WHITE_E, extrude=0.005)
        else:
            txt(title, 0.12, (x, 1.27, 1.3), WHITE_E, extrude=0.005)
    D.cone("volcano", 0.3, 0.35, (-2.6, 0.95, 0.95), m=L.pbr("vrock", "dry_ground_rocks", scale=3), verts=10)
    lava = D.sphere("lava", 0.07, (-2.6, 0.95, 1.12), m=flat("lavam", "#ff5a1a", 3.0), seg=8, rings=4)
    for i in range(6):
        D.ico(f"plant{i}", 0.08, (2.2 + i * 0.16, 0.9, 0.85), m=flat("leaf", "#4cc94a", 0.3), sub=1)
    y1963 = txt("1963", 0.5, (0, 1.4, 2.35), GOLD, extrude=0.08)
    pop(y1963, 5.0, dur=0.35)
    ry, ryarm, _ = man("fair_randy", (-0.62, 0.3, 0), math.radians(12))
    FE = eyes_on(ryarm, ry)
    pose_strip(ryarm, ry, [(1, STAND), (T(7.3), STAND), (T(7.6), PROUD), (T(END), PROUD)], 1, T(END), blend=1)
    for i in range(14):                                  # cola cans pile onto the table
        x = -0.65 + (i % 7) * 0.2
        y = 0.82 + (i // 7) * 0.14
        can = D.cyl(f"can{i}", 0.033, 0.12, (x, y, 0.84), m=flat("cola", "#c4161c", 0.25), verts=10)
        D.cyl(f"canband{i}", 0.034, 0.025, (0, 0, 0.0), m=flat("canb", "#e8e8e8", 0.3), verts=10).parent = can
        pop(can, 11.55 + i * 0.06, dur=0.12)
    shot(fair, "F1_1963", 4.8, 6.3, (0, -3.6, 1.8), (0, -3.0, 1.75), (0, 1.0, 1.6), (0, 1.0, 1.7), 24)
    shot(fair, "F2_randy", 6.3, 9.9, (0.2, -1.7, 1.5), (0.1, -1.4, 1.5), (-0.25, 0.7, 1.35), (-0.25, 0.7, 1.4), 24)
    shot(fair, "F3_fair", 9.9, 11.4, (-3.6, -2.4, 1.7), (-3.2, -2.2, 1.6), (0, 1.0, 1.0), (0.3, 1.0, 1.0), 22)
    shot(fair, "F4_cola", 11.4, 12.5, (0.55, 0.15, 1.3), (0.5, 0.25, 1.25), (-0.1, 0.9, 0.84), (-0.1, 0.9, 0.84), 24)

# ================================================================= BATH: cold shower
bath = L.new_set("BATH")
with L.building(bath):
    P.flat_light(bath, "#cfe4ff", ambient=1.4, sun=0.8)
    D.room("bathroom", (0, 0.5, 1.5), (3, 3, 3), L.pbr("btile", "long_white_tiles", scale=1.5, tint=H("#9fd0ff"), tint_amount=0.4))
    D.box("bfloor2", (3, 3, 0.02), (0, 0.5, 0.0), L.pbr("btile2", "long_white_tiles", scale=2))
    D.cyl("pipe", 0.02, 0.4, (0, 0.85, 2.2), (math.pi / 2, 0, 0), m=flat("chrome", "#c0c4cc", 0.2), verts=8)
    D.cyl("showerhead", 0.12, 0.05, (0, 0.6, 2.15), m=flat("chrome2", "#d0d4dc", 0.3), verts=12)
    D.area_light("cold", 80, (0.8, -1.0, 2.4), (0, 0.3, 1.3), size=1.2, rgb=H("#8fc8ff"))
    rain_like("water", (0.35, 0.35, 0.01), (0, 0.45, 2.1), 6000, 7, flat("water", "#2f8cff", 1.6), life=12, t0=13.3, t1=14.7,
              streak=(0.014, 0.014, 0.2))
    sh, sharm, _ = man("shower_randy", (0, 0.3, 0), 0.0)
    pose_strip(sharm, sh, [(1, SHIVER), (T(END), SHIVER)], 1, T(END), blend=1)
    for i in range(14):
        D.key(sh, "location", T(13.3) + i * 3, (0.012 if i % 2 else -0.012, 0.3, 0))
    shot(bath, "S1_shower", 13.3, 14.6, (0.45, -1.1, 1.65), (0.4, -0.95, 1.65), (0, 0.3, 1.45), (0, 0.3, 1.5), 22, shake=0.006)

# ================================================================= VOID: brain glitch (x=0), record book (x=20), danger (x=40)
void = L.new_set("VOID")
with L.building(void):
    P.flat_light(void, "#0a1060", ambient=1.3, sun=1.0)
    grid = flat("grid", "#2a3cff", 0.8)
    for x0 in (0, 20, 40):
        for k in range(-8, 9):
            D.box("gx", (16, 0.015, 0.004), (x0, k * 1.0, 0.0), grid)
            D.box("gy", (0.015, 16, 0.004), (x0 + k * 1.0, 0, 0.0), grid)
    xr, xarm, xbody = man("xray", (0, 0, 0))
    XRAY = bpy.data.materials.new("xray")
    XRAY.use_nodes = True
    nt = XRAY.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    fr, em, tr, mx = (nt.nodes.new("ShaderNodeLayerWeight"), nt.nodes.new("ShaderNodeEmission"),
                      nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeMixShader"))
    em.inputs["Color"].default_value = (*H("#6fd8ff"), 1)
    em.inputs["Strength"].default_value = 1.6
    fr.inputs["Blend"].default_value = 0.35
    nt.links.new(fr.outputs["Facing"], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    XRAY.surface_render_method = "BLENDED"
    for b in xbody:
        b.data.materials.clear()
        b.data.materials.append(XRAY)
    pose_strip(xarm, xr, [(1, STAND), (T(END), STAND)], 1, T(END), blend=1)
    upd()
    e = [xarm.matrix_world @ xarm.data.bones[b].head_local for b in ("eye_l_011", "eye_r_013")]
    BC = (e[0] + e[1]) / 2 + Vector((0, 0.07, 0.04))
    brain = D.ico("brain", 0.075, BC, m=PINK, sub=2)
    brain.scale = (0.85, 1.1, 0.8)
    random.seed(11)
    for i in range(18):
        t = 15.9 + i * 0.08
        D.key(brain, "location", T(t), BC + Vector((random.uniform(-0.02, 0.02), 0, random.uniform(-0.015, 0.015))))
        D.key(brain, "rotation_euler", T(t), (0, 0, random.uniform(-0.4, 0.4)))
    pe = PINK.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
    for i in range(18):
        pe.default_value = (*H(random.choice(("#ff7fb0", "#7fffd8", "#ffffff", "#ff2a6a"))), 1)
        pe.keyframe_insert("default_value", frame=T(15.9 + i * 0.08))
    shot(void, "V1_brain", 14.6, 17.4, (0.25, -1.05, 1.7), (0.12, -0.8, 1.68), (-0.017, 0, 1.6), (-0.017, 0, 1.63), 26)
    # record book + stamp
    book = D.box("book", (0.9, 0.16, 1.2), (20, 0, 1.3), L.pbr("bookc", "leather_red_02", scale=2))
    D.box("pages", (0.86, 0.15, 1.16), (20, 0.02, 1.3), flat("pagesm", "#f2ead8"))
    txt("WORLD", 0.16, (20, -0.09, 1.62), GOLD, extrude=0.01)
    txt("RECORDS", 0.16, (20, -0.09, 1.42), GOLD, extrude=0.01)
    txt("SLEEP: 264 H", 0.08, (20, -0.09, 1.1), WHITE_E, extrude=0.01)
    stamp = txt("NOT TRACKED", 0.14, (20, -0.13, 1.25), RED_E, extrude=0.02)
    stamp.rotation_euler = (math.pi / 2, math.radians(14), 0)
    D.key(stamp, "scale", 1, (0, 0, 0), "CONSTANT")
    D.key(stamp, "scale", T(38.95), (3, 3, 3))
    D.key(stamp, "scale", T(39.05), (1, 1, 1))
    shot(void, "V2_book", 37.9, 40.0, (20.3, -2.7, 1.5), (20.2, -2.2, 1.45), (20, 0, 1.3), (20, 0, 1.3), 28)
    # danger
    tri = D.cone("hazard", 0.9, 0.08, (40, 0, 1.4), m=flat("hazy", "#ffd21a", 1.2), verts=3)
    tri.rotation_euler = (math.pi / 2, 0, 0)
    D.cone("hazard_in", 0.72, 0.09, (40, -0.01, 1.4), m=flat("hazb", "#111111"), verts=3).rotation_euler = (math.pi / 2, 0, 0)
    D.cone("hazard_in2", 0.62, 0.1, (40, -0.02, 1.4), m=flat("hazy2", "#ffd21a", 1.2), verts=3).rotation_euler = (math.pi / 2, 0, 0)
    ex = txt("!", 0.7, (40, -0.09, 1.3), flat("exm", "#111111"), extrude=0.02)
    pop(ex, 40.15, dur=0.2)
    beacon = D.area_light("beacon", 400, (40.8, -1.0, 2.4), (40, 0, 1.3), size=1.0, rgb=H("#ff2020"))
    for i in range(10):
        beacon.data.energy = 600 if i % 2 == 0 else 0
        beacon.data.keyframe_insert("energy", frame=T(40.0 + i * 0.15))
    shot(void, "V3_danger", 40.0, 41.4, (40.0, -2.6, 1.35), (40.0, -2.3, 1.35), (40, 0, 1.3), (40, 0, 1.3), 28, shake=0.008)

# ================================================================= STREET: night street, the sign is a person
street = L.new_set("STREET")
with L.building(street):
    P.flat_light(street, "#1c1f45", ambient=1.0, sun=0.7)
    D.box("road", (8, 60, 0.02), (3.5, 0, 0.0), L.pbr("sasph", "asphalt_02", scale=0.5))
    D.box("walk", (4, 60, 0.12), (-2.0, 0, 0.06), L.pbr("swalk", "pavement_02", scale=0.8))
    D.box("bld", (2, 60, 6), (-5.0, 0, 3.0), L.pbr("sbrick", "red_brick_03", scale=0.6))
    for y in (-6, 0, 6):
        D.cyl("lamp", 0.05, 4.0, (-0.6, y + 2.5, 2.0), m=flat("lampp", "#3a3d45"), verts=6)
        D.box("lamph", (0.5, 0.25, 0.12), (-0.4, y + 2.5, 4.0), flat("lampl", "#ffd98a", 4.0))
    D.area_light("sodium", 160, (0.2, 2.0, 3.6), (0.4, 0, 1.2), size=2.0, rgb=H("#ffc870"))
    D.cyl("signpole", 0.035, 1.95, (0.95, 0, 0.95), m=flat("spole", "#9aa0aa", 0.1), verts=6)
    for k, z in enumerate((1.98, 1.78)):
        pl = D.box(f"plate{k}", (0.03 if k == 0 else 0.8, 0.8 if k == 0 else 0.03, 0.18), (0.95, 0, z), GREEN_S)
        name = "MAIN ST" if k == 0 else "4TH AVE"
        if k == 0:
            txt(name, 0.1, (0.93, 0, z), WHITE_E, rot=(math.pi / 2, 0, -math.pi / 2), extrude=0.005)
        else:
            txt(name, 0.1, (0.95, -0.02, z), WHITE_E, extrude=0.005)
    face = D.empty("signface", (0.9, 0, 1.45))
    face.rotation_euler = (0, 0, math.radians(-90))
    for x in (-0.07, 0.07):
        eb = eyeball("signeye", 0.055, parent=face, loc=(x, 0, 0.05))
    mouth = D.torus("smile", 0.07, 0.012, (0, 0, -0.07), rot=(math.pi / 2, 0, 0), m=flat("mouthm", "#111111"))
    mouth.parent = face
    mouth.location = (0, -0.02, -0.08)
    pop(face, 21.2, dur=0.25)
    for t, a in ((21.5, -90), (21.7, -80), (21.9, -100), (22.1, -85), (22.4, -90)):
        D.key(face, "rotation_euler", T(t), (0, 0, math.radians(a)))
    sr, srarm, _ = man("street_randy", (0, 0, 0.12), math.radians(90))
    SRE = eyes_on(srarm, sr)
    tired(SRE, srarm)
    pose_strip(srarm, sr, [(1, STAND), (T(20.0), STAND), (T(20.4), SHAKE), (T(END), SHAKE)], 1, T(END), blend=1)
    shot(street, "ST1_sign", 19.3, 21.2, (0.5, -2.8, 1.6), (0.48, -2.4, 1.6), (0.45, 0, 1.45), (0.45, 0, 1.5), 26)
    shot(street, "ST2_face", 21.2, 22.4, (0.15, -0.35, 1.6), (0.2, -0.3, 1.58), (0.9, 0, 1.55), (0.9, 0, 1.55), 26)

# ================================================================= FIELD: famous football player (night game)
field = L.new_set("FIELD")
with L.building(field):
    P.flat_light(field, "#141a3a", ambient=1.3, sun=1.0)
    D.box("turf", (60, 90, 0.02), (0, 10, -0.01), L.pbr("turf", "leafy_grass", scale=0.4, tint=H("#2fae3a"), tint_amount=0.7))
    for k in range(-8, 12):
        D.box("yard", (30, 0.12, 0.005), (0, k * 4.0, 0.005), flat("yardl", "#ffffff", 0.4))
    for x in (-2.8, 2.8):
        D.cyl("upright", 0.07, 6, (x, 14, 3), m=flat("goal", "#ffe01a", 0.6), verts=8)
    D.cyl("crossbar", 0.07, 5.6, (0, 14, 3), (0, math.pi / 2, 0), m=flat("goal2", "#ffe01a", 0.6), verts=8)
    for x, y in ((-14, 20), (14, 20), (-14, -6), (14, -6)):
        D.cyl("tower", 0.2, 14, (x, y, 7), m=flat("tow", "#555a66"), verts=6)
        D.box("lights", (3, 0.5, 1.6), (x, y, 14.5), flat("flood", "#fffbe6", 5.0))
    D.area_light("spot", 900, (2, -4, 7), (0, 0, 1.3), size=2.5, rgb=H("#fff3d0"))
    fr_, frarm, _ = man("player", (0, 0, 0), math.radians(10))
    pose_strip(frarm, fr_, [(1, STAND), (T(22.6), STAND), (T(23.0), CHEER), (T(END), CHEER)], 1, T(END), blend=1)
    bpy.data.scenes["FIELD"].frame_set(T(24.0))
    upd()
    hb = frarm.pose.bones["RightHand"]
    hand = frarm.matrix_world @ hb.head
    ball = D.sphere("football", 0.11, hand + Vector((0, 0, 0.12)), m=L.pbr("ballm", "leather_red_02", scale=4, tint=H("#7a3f1c")), seg=12, rings=8)
    ball.scale = (0.62, 0.62, 1.0)
    ball.rotation_euler = (0, math.radians(30), 0)
    hide_until([ball], 22.95)
    random.seed(5)
    for i in range(60):
        c = D.box(f"conf{i}", (0.05, 0.05, 0.005), (random.uniform(-2, 2), random.uniform(-1.5, 1.5), 4.5),
                  flat(f"cf{i % 5}", ("#ff3b47", "#ffd21a", "#3bd2ff", "#7cff6b", "#ff7ad8")[i % 5], 0.8))
        t0 = 23.0 + random.uniform(0, 0.6)
        D.key(c, "location", T(t0), c.location.copy())
        D.key(c, "location", T(t0 + 2.4), c.location + Vector((random.uniform(-0.5, 0.5), 0, -4.4)))
        D.key(c, "rotation_euler", T(t0), (0, 0, 0))
        D.key(c, "rotation_euler", T(t0 + 2.4), (random.uniform(0, 9), random.uniform(0, 9), 0))
        hide_until([c], t0)
    shot(field, "FD1_hero", 22.4, 25.3, (0.9, -2.6, 0.45), (0.7, -2.1, 0.55), (0, 0, 1.45), (0, 0, 1.55), 20)

# ================================================================= CLINIC: counting down by sevens
cl = L.new_set("CLINIC")
with L.building(cl):
    P.flat_light(cl, "#dfe8f0", ambient=1.6, sun=1.0)
    D.room("clinic", (0, 1, 1.5), (8, 7, 3), L.pbr("tiles", "long_white_tiles", scale=1.0))
    D.box("cfloor", (8, 7, 0.02), (0, 1, 0.0), L.pbr("lino", "old_linoleum_flooring_01", scale=0.8))
    doc, docarm, _ = man("doctor", (0.95, 0, 0), math.radians(-90))
    pose_strip(docarm, doc, [(1, CLIPB), (T(END), CLIPB)], 1, T(END), blend=1)
    cb = D.box("clipboard", (0.04, 0.24, 0.32), (0.62, 0, 1.12), flat("cbm", "#a8743a"))
    cb.rotation_euler = (0, math.radians(-30), 0)
    cr, crarm, _ = man("count_randy", (-0.6, 0, 0), math.radians(90))
    CRE = eyes_on(crarm, cr)
    tired(CRE, crarm)
    pose_strip(crarm, cr, [(1, STAND), (T(30.9), STAND), (T(31.2), BLANK), (T(END), BLANK)], 1, T(END), blend=1)
    nums = []
    for v, t in ((100, 27.85), (93, 28.55), (86, 28.85), (79, 29.15), (72, 29.45), (65, 30.1)):
        o = txt(str(v), 0.42 if v != 65 else 0.55, (0.15, -0.2, 2.25), RED_E if v == 65 else YEL)
        nums.append((o, T(t)))
    D.swap(nums)
    last = nums[-1][0]
    D.key(last, "location", T(31.1), last.location.copy())
    D.key(last, "location", T(31.8), last.location + Vector((0, 0, -2.6)))
    D.key(last, "rotation_euler", T(31.1), last.rotation_euler.copy())
    D.key(last, "rotation_euler", T(31.8), (math.pi / 2 + 1.2, 0.6, 0))
    q = txt("?", 0.22, (-0.45, -0.05, 2.08), YEL)
    pop(q, 31.2, dur=0.25)
    spin = D.empty("spinner", (-0.45, -0.05, 2.3))
    for k in range(8):
        a = k / 8 * math.tau
        d = D.sphere(f"spin{k}", 0.025, (0, 0, 0), m=D.mat(f"spm{k}", H("#ffffff"), emit=H("#ffffff"), emit_strength=0.3 + k * 0.35),
                     seg=6, rings=4)
        d.parent = spin
        d.location = (0.12 * math.cos(a), 0, 0.12 * math.sin(a))
    hide_until([spin], 31.5)
    D.key(spin, "rotation_euler", T(31.5), (0, 0, 0))
    D.key(spin, "rotation_euler", T(END), (0, math.radians(-360 * 8), 0))
    D.ease_last(spin, "LINEAR")
    shot(cl, "C1_doctor", 25.3, 28.0, (0.2, -2.3, 1.6), (0.2, -2.0, 1.6), (0.15, 0, 1.5), (0.15, 0, 1.6), 24)
    shot(cl, "C2_sevens", 28.0, 31.0, (0.0, -2.2, 1.9), (0.0, -2.0, 1.95), (0.0, 0, 1.85), (0.0, 0, 1.9), 26)
    shot(cl, "C3_blank", 31.0, 32.7, (0.25, -0.45, 1.75), (0.2, -0.4, 1.78), (-0.55, 0, 1.85), (-0.55, 0, 1.9), 24)

# ---------------------------------------------------------------- PS2 pass
P.crunch_textures(512)
SHOTS.sort(key=lambda x: x[1])
json.dump(SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(SHOTS), [s.name for s in bpy.data.scenes])
