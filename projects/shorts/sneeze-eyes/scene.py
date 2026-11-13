"""blender -b -P scene.py -- <out.blend>: "What if you sneezed with your eyes open?" in the PS2 / LowPolyShorts look.

Timeline seconds (VO starts at VO_AT = 1.2 s, so timeline = vo word time + 1.2). Sets are separate scenes:

  HOME   0.0  hook: AAH-CHOO, procedural eyeballs fly out on optic cords; slow-mo re-pop; rewind
         20.4 eyelids slam shut / germs bounce off;  23.9 holding eyes open + sneeze;  26.0 cursed freeze
  PLAY   5.8  playground kids whisper the myth;  12.9 tent held by six ropes
  VOID   8.0  eyeball vs champagne cork;  10.1 x-ray eye + 6 muscles;  14.5 / 19.2 speedometer 100 → 10;
         33.3 x-ray windpipe tears
  CLINIC 17.6 scientists film a sneeze;  34.7 hospital bed, neck brace, eyes fine
  DARK   27.6 "the real danger": pinching the nose
  ROAD   29.7 rainy highland road at night, driver pinches nose

Cast: Renderpeople "Eric" (Sketchfab, CC-BY). The eyeballs, lids and cords are procedural, bone-parented to Head.
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
END = 36.8
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


# ================================================================= HOME: living room (hook, shut eyes, cursed)
home = L.new_set("HOME", main=True)
P.flat_light(home, "#8fb6e6", ambient=1.5, sun=1.2)
D.room("living", (0, 0, 1.5), (7, 7, 3), L.pbr("hwall", "painted_plaster_wall", scale=0.8, tint=H("#b9a6e8"), tint_amount=0.9))
D.box("hfloor", (7, 7, 0.02), (0, 0, 0.0), L.pbr("hcarpet", "fabric_pattern_07", scale=1.2, tint=H("#d8c39a"), tint_amount=0.8))
D.box("hwin", (1.6, 0.05, 1.2), (-1.4, 3.45, 1.7), flat("winsky", "#bfe3ff", 1.4))
D.box("hwinf", (1.75, 0.04, 1.35), (-1.4, 3.47, 1.7), flat("winframe", "#f2efe8"))
L.prop("fancy_picture_frame_01", (1.3, 3.45, 1.7), rot_z=0, scale=1.6)
L.prop("potted_plant_02", (2.2, 2.6, 0), scale=1.4)
sofa = D.box("sofa", (2.2, 0.9, 0.45), (0.6, 2.7, 0.22), L.pbr("sofa", "leather_red_02", scale=2))
D.box("sofab", (2.2, 0.25, 0.9), (0.6, 3.1, 0.45), L.pbr("sofa2", "leather_red_02", scale=2))
you, yarm, ybody = man("you", (0, 0, 0))
E = eyes_on(yarm, you)
M_YOU = mouth_of(yarm, you)
pose_strip(yarm, you, [
    (1, AAH), (T(0.45), AAH), (T(0.55), CHOO), (T(1.6), CHOO), (T(2.3), STAND), (T(3.15), STAND),
    (T(3.2), CHOO), (T(5.4), CHOO), (T(5.75), STAND), (T(23.5), STAND),
    (T(23.9), HOLD), (T(24.85), HOLD), (T(25.0), HOLD_CHOO), (T(25.4), HOLD_CHOO), (T(25.8), HOLD), (T(27.6), HOLD)], 1, T(27.6), blend=1)
# eyeballs: pop at 0.55 → boing → dangle;  slow-mo re-pop 3.2 → 5.4;  rewind snaps back 5.4 → 5.75
ball_keys(E, [(0.0, (0, 0, 0), 0), (0.54, (0, 0, 0), 0), (0.64, (0.02, -0.30, 0.02), 220), (0.74, (0.03, -0.20, -0.05), 300),
              (0.86, (0.04, -0.27, -0.10), 380), (1.0, (0.04, -0.21, -0.15), 420), (1.2, (0.05, -0.20, -0.20), 450),
              (1.5, (0.03, -0.16, -0.24), 470), (1.9, (0.05, -0.12, -0.27), 480), (2.4, (0.02, -0.10, -0.28), 490),
              (2.9, (0.04, -0.11, -0.27), 500), (3.15, (0.04, -0.11, -0.27), 500),
              (3.19, (0, 0, 0), 0), (3.3, (0, -0.01, 0), 0), (4.9, (0.03, -0.30, -0.02), 260), (5.4, (0.04, -0.31, -0.05), 280),
              (5.75, (0, 0, 0), 0), (END, (0, 0, 0), 0)])
holes(E, [(0.56, 3.19), (3.32, 5.72)])
blink(E, 20.95, 23.4)
spray("sp_hook", M_YOU + Vector((0, -0.04, -0.03)), (0, -1, -0.2), 0.55)
spray("sp_slow", M_YOU + Vector((0, -0.04, -0.03)), (0, -1, -0.2), 3.25, dur=1.6, dist=0.8)
spray("sp_hold", M_YOU + Vector((0, -0.04, -0.03)), (0, -1, -0.2), 25.0)
# germs fly at the shut eyes and bounce off
for i in range(7):
    g = D.ico(f"germ{i}", 0.012, (0, 0, 0), m=GERM, sub=1)
    sp = D.ico(f"germs{i}", 0.017, (0, 0, 0), m=GERM, sub=0)
    sp.parent = g
    sp.rotation_euler = (0.5, 0.3, 0.2)
    eye = (0.012 if i % 2 else -0.047, -0.11, 1.68)
    st = Vector((random.uniform(-0.25, 0.25), -0.9, 1.68 + random.uniform(-0.2, 0.2)))
    t0 = 22.15 + i * 0.12
    hit = Vector(eye) + Vector((0, -0.03, 0))
    away = hit + Vector((random.uniform(-0.3, 0.3), -0.35, random.uniform(-0.25, 0.3)))
    D.key(g, "scale", 1, (0, 0, 0))
    D.key(g, "scale", T(t0) - 1, (0, 0, 0), "CONSTANT")
    D.key(g, "scale", T(t0), (1, 1, 1))
    D.key(g, "location", T(t0), st)
    D.key(g, "location", T(t0 + 0.35), hit)
    D.key(g, "location", T(t0 + 0.8), away)
    D.key(g, "rotation_euler", T(t0), (0, 0, 0))
    D.key(g, "rotation_euler", T(t0 + 0.8), (4, 3, 5))
    D.key(g, "scale", T(t0 + 0.8), (1, 1, 1), "CONSTANT")
    D.key(g, "scale", T(t0 + 0.8) + 1, (0, 0, 0))
FACE = Vector((-0.017, -0.1, 1.66))
shot(home, "A1_hook", 0.0, 1.9, (0.05, -0.8, 1.64), (0.03, -0.65, 1.63), (-0.017, -0.1, 1.62), (-0.017, -0.12, 1.6), 28)
shot(home, "A2_dangle", 1.9, 3.2, (-0.75, -0.55, 1.5), (-0.68, -0.5, 1.5), (0, -0.2, 1.48), (0, -0.2, 1.48), 30)
shot(home, "A3_slowmo", 3.2, 5.4, (0.02, -0.62, 1.46), (0.02, -0.66, 1.46), (-0.017, -0.1, 1.62), (-0.017, -0.25, 1.6), 22)
shot(home, "A4_rewind", 5.4, 5.8, (0.05, -0.8, 1.64), (0.05, -0.8, 1.64), (-0.017, -0.1, 1.6), (-0.017, -0.1, 1.6), 28)
shot(home, "E1_shut", 20.4, 22.0, (0.0, -0.42, 1.68), (0.0, -0.36, 1.68), (-0.017, -0.1, 1.67), (-0.017, -0.1, 1.67), 30)
shot(home, "E2_germs", 22.0, 23.9, (0.35, -0.6, 1.72), (0.3, -0.55, 1.71), (-0.017, -0.2, 1.67), (-0.017, -0.2, 1.67), 24)
shot(home, "O1_hold", 23.9, 26.0, (0.2, -1.1, 1.6), (0.12, -0.85, 1.62), (-0.017, -0.1, 1.55), (-0.017, -0.1, 1.6), 26)
shot(home, "O2_cursed", 26.0, 27.6, (0.0, -0.45, 1.67), (0.0, -0.4, 1.67), (-0.017, -0.1, 1.66), (-0.017, -0.1, 1.66), 30)

# ================================================================= PLAY: playground kids + tent with six ropes
play = L.new_set("PLAY")
with L.building(play):
    P.flat_light(play, "#8fb6e6", ambient=1.6, sun=1.4)
    D.box("grass", (120, 120, 0.02), (0, 0, -0.01), L.pbr("grass", "leafy_grass", scale=0.5))
    prop(A("playground.glb"), 9.0, 0, (-1.0, 7.0, 0), rotz=math.radians(10), name="playground")
    L.prop("tree_small_02", (5, 9, 0), scale=1.2)
    L.prop("tree_small_02", (-7, 12, 0), scale=1.4)
    kids = [man("kidA", (0, 0, 0), math.radians(15), 0.55), man("kidB", (0.42, 0.08, 0), math.radians(-80), 0.55),
            man("kidC", (0.2, 0.45, 0), math.radians(-160), 0.55)]
    pose_strip(kids[0][1], kids[0][0], [(1, LISTEN), (T(8.0), LISTEN)], 1, T(8.0), blend=1)
    pose_strip(kids[1][1], kids[1][0], [(1, STAND), (T(6.4), STAND), (T(6.8), WHISPER), (T(8.0), WHISPER)], 1, T(8.0), blend=1)
    pose_strip(kids[2][1], kids[2][0], [(1, LISTEN), (T(8.0), LISTEN)], 1, T(8.0), blend=1)
    shot(play, "P1_huddle", 5.8, 6.85, (1.6, -3.4, 1.5), (1.3, -3.0, 1.4), (0.2, 0.2, 0.55), (0.2, 0.2, 0.55), 22)
    shot(play, "P2_whisper", 6.85, 8.0, (-0.55, 0.45, 0.95), (-0.5, 0.4, 0.92), (0.35, 0.0, 0.85), (0.3, 0.02, 0.85), 26)
    # tent site at x=30, six guy ropes to pegs
    tent, tms = prop(A("tent.glb"), 2.0, 0, (30, 0, 0), rotz=0, tris=1500, name="tent")
    tlo, thi = bounds(tms)
    ROPE = flat("rope", "#f2d16b", 0.3)
    PEG = flat("peg", "#888888")
    cx, cy = (tlo.x + thi.x) / 2, (tlo.y + thi.y) / 2
    hx, hy, hz = (thi.x - tlo.x) / 2, (thi.y - tlo.y) / 2, thi.z
    anchors = [((cx - hx * 0.9, cy - hy * 0.8, hz * 0.45), (cx - hx * 2.2, cy - hy * 1.9, 0)),
               ((cx + hx * 0.9, cy - hy * 0.8, hz * 0.45), (cx + hx * 2.2, cy - hy * 1.9, 0)),
               ((cx - hx * 0.9, cy + hy * 0.8, hz * 0.45), (cx - hx * 2.2, cy + hy * 1.9, 0)),
               ((cx + hx * 0.9, cy + hy * 0.8, hz * 0.45), (cx + hx * 2.2, cy + hy * 1.9, 0)),
               ((cx, cy - hy * 0.95, hz * 0.95), (cx, cy - hy * 2.6, 0)),
               ((cx, cy + hy * 0.95, hz * 0.95), (cx, cy + hy * 2.6, 0))]
    for i, (a, b) in enumerate(anchors):
        r = cyl_between(f"rope{i}", a, b, 0.012, ROPE)
        D.box(f"peg{i}", (0.05, 0.05, 0.25), (b[0], b[1], 0.08), PEG)
        pop(r, 13.0 + i * 0.12, scale=None, dur=0.15)
    for t, a in ((12.9, 0), (13.3, 2.0), (13.7, -1.5), (14.1, 1.8), (14.5, 0)):
        D.key(tent, "rotation_euler", T(t), (math.radians(a), 0, 0))
    shot(play, "T1_tent", 12.9, 14.5, (32.6, -4.2, 1.6), (32.1, -3.6, 1.4), (cx, cy, 0.7), (cx, cy, 0.8), 22)

# ================================================================= VOID: dark science void
void = L.new_set("VOID")
with L.building(void):
    P.flat_light(void, "#0a1060", ambient=1.3, sun=1.0)
    grid = flat("grid", "#2a3cff", 0.8)
    for x0 in (0, 20, 40, 60):                           # glowing floor grid under every station
        for k in range(-8, 9):
            D.box("gx", (16, 0.015, 0.004), (x0, k * 1.0, 0.0), grid)
            D.box("gy", (0.015, 16, 0.004), (x0 + k * 1.0, 0, 0.0), grid)
    # -- table: eyeball vs champagne cork
    D.box("table", (1.3, 0.75, 0.06), (0, 0, 0.75), wood)
    for x in (-0.58, 0.58):
        for y in (-0.3, 0.3):
            D.box("tleg", (0.06, 0.06, 0.72), (x, y, 0.36), wood)
    teye = eyeball("teye", 0.07, loc=(-0.2, -0.05, 0.85))
    for t, z in ((8.0, 0), (8.6, 8), (9.2, -6), (10.1, 0)):
        D.key(teye, "rotation_euler", T(t), (0, 0, math.radians(z)))
    bottle, _ = prop(A("champagne.glb"), 0.62, 2, (0.25, 0.05, 0.78), tris=900, name="bottle")
    cork = D.cyl("cork", 0.022, 0.05, (0.25, 0.05, 0.78 + 0.62 + 0.02), m=flat("corkm", "#c8955a"), verts=8)
    D.key(cork, "location", T(9.0), cork.location.copy())
    D.key(cork, "location", T(9.45), Vector((0.45, 0.25, 3.2)))
    D.key(cork, "rotation_euler", T(9.0), (0, 0, 0))
    D.key(cork, "rotation_euler", T(9.45), (9, 4, 0))
    spray("foam", (0.25, 0.05, 1.42), (0.2, 0, 1), 9.0, n=20, spread=0.25, dist=0.7, dur=0.5)
    shot(void, "C1_but", 8.0, 8.8, (-0.12, -0.5, 0.92), (-0.14, -0.42, 0.9), (-0.2, -0.05, 0.86), (-0.2, -0.05, 0.86), 30)
    shot(void, "C2_cork", 8.8, 10.1, (0.05, -1.5, 1.15), (0.05, -1.35, 1.25), (0.02, 0, 1.0), (0.05, 0, 1.25), 26)
    # -- x-ray eye + six muscles
    EC = Vector((20, 0, 1.5))
    big = eyeball("bigeye", 0.5, loc=EC)
    apex = EC + Vector((0, 1.7, 0))
    starts = [(0, -0.25, 1), (0, -0.25, -1), (1, -0.25, 0), (-1, -0.25, 0)]
    mus = []
    for i, d in enumerate(starts):
        a = EC + Vector(d).normalized() * 0.48
        mus.append(cyl_between(f"rect{i}", a, apex, 0.09, None, verts=6))
    mus.append(cyl_between("obl_s", EC + Vector((-0.2, -0.1, 0.45)), EC + Vector((-0.75, -0.55, 0.65)), 0.06, None, verts=6))
    mus.append(cyl_between("obl_i", EC + Vector((-0.2, 0.1, -0.45)), EC + Vector((-0.8, -0.45, -0.55)), 0.06, None, verts=6))
    for i, o in enumerate(mus):
        m = D.mat(f"mus{i}", H("#7a1020"), rough=1, emit=H("#ff3040"), emit_strength=0.0)
        D.give(o, m)
        es = m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        es.default_value = 0.0
        es.keyframe_insert("default_value", frame=T(10.15 + i * 0.22) - 1)
        es.default_value = 2.5
        es.keyframe_insert("default_value", frame=T(10.15 + i * 0.22))
    six = txt("6", 0.9, EC + Vector((0, 0, 1.25)), YEL)
    pop(six, 10.15)
    for t, z in ((10.1, -10), (11.3, 12), (12.9, -6)):
        D.key(big, "rotation_euler", T(t), (0, 0, math.radians(z)))
    shot(void, "M1_muscles", 10.1, 12.9, (22.0, -2.6, 2.3), (18.6, -2.9, 2.0), (20, 0.4, 1.5), (20, 0.4, 1.6), 26)
    # -- speedometer
    SC = Vector((40, 0, 1.6))
    dial = D.cyl("dial", 1.05, 0.06, SC, (math.pi / 2, 0, 0), m=flat("dialm", "#14161f"), verts=24)
    D.torus("dialrim", 1.08, 0.05, SC + Vector((0, -0.03, 0)), rot=(math.pi / 2, 0, 0), m=flat("rim", "#c0c4cc", 0.3))

    def ang(v):
        return math.radians(225 - v * 2.7)
    for v in range(0, 101, 10):
        a = ang(v)
        d = Vector((math.cos(a), 0, math.sin(a)))
        tk = D.box(f"tick{v}", (0.16, 0.01, 0.035), SC + d * 0.88 + Vector((0, -0.05, 0)), RED_E if v >= 80 else WHITE_E)
        tk.rotation_euler = (0, -a, 0)
        if v % 20 == 0:
            txt(str(v), 0.15, SC + d * 0.66 + Vector((0, -0.05, 0)), WHITE_E, extrude=0.01)
    txt("MPH", 0.17, SC + Vector((0, -0.05, -0.45)), YEL, extrude=0.01)
    piv = D.empty("needle", SC + Vector((0, -0.08, 0)))
    nd = D.box("needle_m", (0.85, 0.015, 0.045), (0.38, 0, 0), RED_E)
    nd.parent = piv
    D.cyl("hub", 0.08, 0.06, SC + Vector((0, -0.09, 0)), (math.pi / 2, 0, 0), m=flat("hub", "#c0c4cc", 0.3), verts=12)
    for t, v in ((14.5, 0), (15.7, 0), (16.0, 104), (16.15, 96), (16.3, 100), (19.4, 100), (19.55, 30), (19.75, 6), (19.9, 12),
                 (20.05, 10), (END, 10)):
        D.key(piv, "rotation_euler", T(t), (0, -ang(v), 0))
    l100 = txt("100 MPH", 0.36, SC + Vector((0, -0.2, -1.45)), RED_E)
    pop(l100, 15.8)
    strike = D.box("strike", (2.1, 0.02, 0.07), SC + Vector((0, -0.3, -1.45)), WHITE_E)
    strike.rotation_euler = (0, math.radians(-8), 0)
    pop(strike, 16.65, scale=None, dur=0.15)
    vanish(l100, 19.3)
    vanish(strike, 19.3)
    l10 = txt("10 MPH", 0.36, SC + Vector((0, -0.2, -1.45)), YEL)
    pop(l10, 19.6)
    shot(void, "S1_100", 14.5, 17.6, (40, -3.6, 1.2), (40, -3.0, 1.15), (40, 0, 1.15), (40, 0, 1.1), 28)
    shot(void, "S2_10", 19.2, 20.4, (40.3, -3.1, 1.15), (40.2, -2.8, 1.15), (40, 0, 1.1), (40, 0, 1.1), 28)
    # -- x-ray windpipe
    xr, xarm, xbody = man("xray", (60, 0, 0))
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
    pose_strip(xarm, xr, [(1, STAND), (T(33.3), PINCH), (T(33.7), PINCH_JOLT), (T(END), PINCH_JOLT)], 1, T(END), blend=1)
    own_vl(xarm).update()
    nk = xarm.matrix_world @ xarm.data.bones["Neck"].head_local
    hd = xarm.matrix_world @ xarm.data.bones["Head"].head_local
    pipe_c = (nk + hd) / 2 + Vector((0, -0.035, -0.06))
    WP = D.mat("pipe", H("#ffffff"), rough=1, emit=H("#ffffff"), emit_strength=2.0)
    pipe = D.empty("pipe", pipe_c)
    tube = D.cyl("pipe_t", 0.016, 0.26, (0, 0, 0), m=WP, verts=10)
    tube.parent = pipe
    for k in range(7):
        ring = D.torus(f"pring{k}", 0.019, 0.004, (0, 0, -0.11 + k * 0.036), m=WP)
        ring.parent = pipe
        ring.location = (0, 0, -0.11 + k * 0.036)
    pec = WP.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
    for t, c in ((33.3, "#ffffff"), (33.7, "#ffd0d0"), (33.84, "#ff2020")):
        pec.default_value = (*H(c), 1)
        pec.keyframe_insert("default_value", frame=T(t))
    for t, s in ((33.3, 1.0), (33.75, 1.7), (33.84, 1.9), (33.9, 1.2), (END, 1.2)):
        D.key(pipe, "scale", T(t), (s, s, 1))
    rip = D.box("rip", (0.012, 0.012, 0.05), pipe_c + Vector((0, -0.03, 0.01)), RED_E)
    pop(rip, 33.84, dur=0.12)
    shot(void, "X1_pipe", 33.3, 34.7, (60.45, -0.95, 1.52), (60.32, -0.72, 1.5), (60, 0, 1.47), (60, -0.02, 1.47), 28,
         shake=0.004)

# ================================================================= CLINIC: lab (x=0) + hospital (x=8)
cl = L.new_set("CLINIC")
with L.building(cl):
    P.flat_light(cl, "#dfe8f0", ambient=1.6, sun=1.0)
    D.room("clinic", (4, 0, 1.5), (16, 7, 3), L.pbr("tiles", "long_white_tiles", scale=1.0))
    D.box("cfloor", (16, 7, 0.02), (4, 0, 0.0), L.pbr("lino", "old_linoleum_flooring_01", scale=0.8))
    subj, sarm, _ = man("subject", (0, 1.3, 0), 0.0)
    SM = mouth_of(sarm, subj)
    pose_strip(sarm, subj, [(1, STAND), (T(17.9), STAND), (T(18.3), AAH), (T(18.45), CHOO), (T(19.2), CHOO)], 1, T(19.2), blend=1)
    spray("sp_lab", SM + Vector((0, -0.08, -0.05)), (0, -1, -0.15), 18.45, n=40, dist=1.2, dur=0.5)
    sci, carm, _ = man("scientist", (0.45, -1.05, 0), math.pi)
    pose_strip(carm, sci, [(1, CAMOP), (T(19.2), CAMOP)], 1, T(19.2), blend=1)
    rig, _ = prop(A("camtripod.glb"), 1.55, 2, (0.15, -0.45, 0), rotz=math.radians(90), tris=2000, name="camtripod")
    rec = D.sphere("rec", 0.025, (0.15, -0.3, 1.62), m=RED_E, seg=8, rings=4)
    txt("1000 FPS", 0.1, (-0.6, 2.5, 2.3), RED_E, extrude=0.01)
    shot(cl, "L1_lab", 17.6, 19.2, (2.9, -1.9, 1.7), (2.7, -1.6, 1.65), (0.1, 0.1, 1.2), (0.1, 0.2, 1.25), 20)
    # hospital
    bed, bms = prop(A("bed.glb"), 2.1, 0, (8, 0.4, 0), rotz=math.radians(-90), name="bed")   # pillow end → +Y
    sheet = [o for o in bms if any(m and "lagen" in m.name for m in o.data.materials)]
    blo, bhi = bounds(sheet or bms)
    pat, parm, _ = man("patient", (8, -0.55, bhi.z + 0.1), rot=(-math.pi / 2, 0, 0))     # lying on back, head → +Y
    PE = eyes_on(parm, pat)
    pose_strip(parm, pat, [(1, STAND), (T(END), STAND)], 1, T(END), blend=1)
    blink(PE, 35.55, 35.75)
    own_vl(parm).update()
    nk = parm.matrix_world @ parm.data.bones["Neck"].head_local
    hd = parm.matrix_world @ parm.data.bones["Head"].head_local
    brace = D.cyl("brace", 0.085, 0.11, (nk + hd) / 2 + Vector((0, -0.03, 0)), (math.pi / 2, 0, 0), m=flat("brace", "#f4f4f0"), verts=12)
    D.box("monitor", (0.45, 0.3, 0.35), (8.9, 1.7, 1.45), flat("mon", "#2a2f38"))
    D.box("monline", (0.36, 0.01, 0.05), (8.9, 1.54, 1.47), flat("ecg", "#3dff6a", 2.0))
    D.cyl("ivpole", 0.015, 1.9, (7.2, 1.6, 0.95), m=flat("pole", "#c0c4cc"), verts=6)
    D.box("ivbag", (0.15, 0.05, 0.25), (7.2, 1.6, 1.8), flat("bag", "#e6f4ff", 0.4))
    upd()
    FC = sum((sk.matrix_world.translation for sk in PE["sockets"]), Vector()) / 2
    shot(cl, "H1_bed", 34.7, END, FC + Vector((0.75, -0.1, 0.55)), FC + Vector((0.6, -0.05, 0.45)), FC, FC, 24)

# ================================================================= DARK: the real danger
dark = L.new_set("DARK")
with L.building(dark):
    P.flat_light(dark, "#050208", ambient=0.35, sun=0.3)
    D.area_light("redrim", 60, (0.9, 0.6, 2.0), (0, 0, 1.6), size=1.0, rgb=H("#ff2a2a"))
    D.area_light("redkey", 25, (-0.8, -1.2, 1.9), (0, 0, 1.6), size=1.0, rgb=H("#ff6060"))
    dm, darm, _ = man("danger", (0, 0, 0))
    pose_strip(darm, dm, [(1, STAND), (T(28.0), STAND), (T(28.4), PINCH), (T(28.95), PINCH), (T(29.05), PINCH_JOLT),
                          (T(29.7), PINCH_JOLT)], 1, T(29.7), blend=1)
    shot(dark, "D1_danger", 27.6, 29.7, (0.15, -0.9, 1.62), (0.08, -0.6, 1.64), (-0.017, -0.1, 1.58), (-0.017, -0.1, 1.6), 30,
         shake=0.003)

# ================================================================= ROAD: rainy highland night
road = L.new_set("ROAD")
with L.building(road):
    P.flat_light(road, "#1c1f45", ambient=0.9, sun=0.6)
    D.box("asphalt", (6, 300, 0.02), (0, 0, 0.0), L.pbr("asph", "asphalt_02", scale=0.4))
    D.box("grassL", (120, 300, 0.02), (-63, 0, -0.01), L.pbr("rgrass", "leafy_grass", scale=0.3, tint=H("#3a6a3a"), tint_amount=0.6))
    D.box("grassR", (120, 300, 0.02), (63, 0, -0.01), L.pbr("rgrass2", "leafy_grass", scale=0.3, tint=H("#3a6a3a"), tint_amount=0.6))
    for i in range(14):
        x = random.choice((-1, 1)) * random.uniform(15, 60)
        h = D.ico(f"hill{i}", random.uniform(8, 20), (x, random.uniform(-120, 120), -4), m=flat("hill", "#2c4a32"), sub=1)
        h.scale.z = 0.5
    for k in range(40):                                    # white road dashes
        D.box("dash", (0.12, 1.5, 0.005), (0, -100 + k * 5, 0.012), flat("dash", "#e8e8e8", 0.3))
    car = D.empty("car", (1.5, 0, 0))
    cbody, cms = prop(A("car.glb"), 4.1, 1, (0, 0, 0), keep=lambda o: not any(m and ("Hemi" in m.name or "shadow" in m.name)
                                                                                for m in o.data.materials), name="carbody")
    cbody.parent = car
    for o in cms:
        P.lowpoly(o, 2500, flat=True)
    for x in (-0.55, 0.55):
        D.sphere("hl", 0.09, (x, -2.0, 0.65), m=flat("hlm", "#fff6c8", 3.0), seg=8, rings=4).parent = car
    D.key(car, "location", T(29.7), (1.5, 20, 0))
    D.key(car, "location", T(33.3), (1.5, -10, 0))
    D.ease_last(car, "LINEAR")
    for fc in D._fcurves(car.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"
    drv, darm2, _ = man("driver", (-0.37, 0.15, -0.5), 0.0)
    drv.parent = car
    pose_strip(darm2, drv, [(1, SIT), (T(31.2), SIT), (T(31.5), SIT_PINCH), (T(32.9), SIT_PINCH), (T(33.0), SIT_JOLT),
                            (T(33.3), SIT_JOLT)], 1, T(33.3), blend=1)
    # rain: particle streaks from a plane above the road
    streak = D.box("streak", (0.006, 0.006, 0.35), (0, 0, -50), flat("rain", "#a8c4ff", 0.8))
    em_ = D.box("rainem", (40, 80, 0.01), (0, 10, 14), None)
    em_.modifiers.new("rain", "PARTICLE_SYSTEM")
    ps = em_.particle_systems[0].settings
    ps.count, ps.frame_start, ps.frame_end, ps.lifetime = 40000, -60, T(END), 40
    ps.emit_from, ps.normal_factor = "FACE", 0.0
    ps.object_align_factor = (0, 0, -14)
    ps.effector_weights.gravity = 0.0
    ps.render_type, ps.instance_object, ps.particle_size = "OBJECT", streak, 1.0
    em_.show_instancer_for_render = False
    shot(road, "R1_road", 29.7, 31.2, (-3.0, -3, 1.3), (-2.8, -3.5, 1.25), (1.5, 14, 0.8), (1.5, 7, 0.8), 24)
    shot(road, "R2_driver", 31.2, 33.3, (0.35, -0.55, 1.15), (0.33, -0.5, 1.15), (-0.37, 0.05, 1.05), (-0.37, 0.05, 1.07), 20,
         shake=0.006, parent=car)

# ---------------------------------------------------------------- PS2 pass
P.crunch_textures(512)
SHOTS.sort(key=lambda x: x[1])
json.dump(SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(SHOTS), [s.name for s in bpy.data.scenes])
