"""Shared helpers copied from sneeze-eyes/scene.py (Eric rig posing, props, PS2 shots). Import after bpy is set up."""
import math, os, re, sys
from mathutils import Matrix, Vector
import bpy
import director as D
import look as L
import ps2 as P

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda name: os.path.join(HERE, "assets", name)
ERIC_S = 1.82 / 186.865
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
T = D.T
H = D.hex_lin
SHOTS = []


def flat(name, hexc, emit=0.0):
    return D.mat(name, H(hexc), rough=1.0, emit=H(hexc) if emit else None, emit_strength=emit, spec=0.1)

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
