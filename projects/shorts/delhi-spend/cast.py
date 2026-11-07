"""Shared helpers for scene.py (runs inside Blender): Renderpeople Eric rig + pose dicts (from learn-blender-hindi),
glTF prop import/fit, linked-copy instancing, pop/vanish keys. Import after sys.path holds reelforge/blender."""
import math, os, re
import bpy
from mathutils import Matrix, Vector
import director as D
import look as L

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda name: os.path.join(HERE, "assets", name)
MAN = A("eric.glb")
ERIC_S = 1.82 / 186.865                                # Renderpeople scan is in cm → 1.82 m
H = D.hex_lin


def rotz(v, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


def own_vl(o):
    """The view layer of the set this object lives in (pose maths must refresh THAT depsgraph, not ROOM's)."""
    return o.users_scene[0].view_layers[0]


def aim_limb(arm, n, world_dir, frame, fwd=None):
    """Joint → child joint along world_dir (glTF bone tails are arbitrary, so D.aim misses). For the head, `fwd`
    (world) also rolls it about its own axis until the eyes face that way: the minimal-arc aim alone left Eric's
    face turned to the back."""
    pb = D.bone(arm, n)
    own_vl(arm).update()
    inv = arm.matrix_world.to_3x3().inverted()
    cur = (pb.children[0].head - pb.head).normalized()
    tgt = (inv @ Vector(world_dir)).normalized()
    if n in ("Neck", "Head"):                          # Eric's head_end is not "up": tilt the REST vector by up→dir
        rest = (pb.children[0].bone.head_local - pb.bone.head_local).normalized()
        up = (inv @ Vector((0, 0, 1))).normalized()
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


def pose_strip(arm, root, keys, f0, f1, blend=4):
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions.new(f"{arm.name}_pose_{f0}")
    ad.use_nla = False
    ad.action = act
    for fr, dirs in keys:
        arm.users_scene[0].frame_set(fr)
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
        own_vl(arm).update()
        yaw = root.matrix_world.to_euler().z
        for n, d in (dirs | {k: v for k, v in HEAD_UP.items() if k not in dirs}).items():
            aim_limb(arm, n, rotz(d, yaw), fr, fwd=rotz((0, -1, 0), yaw))
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


def man(name, loc, yaw=0.0):
    """Renderpeople Eric: UE-style bones renamed to Mixamo names (vertex groups follow), so the pose dicts work."""
    r, arm, body = D.import_char(MAN, name)
    for b in arm.data.bones:
        base_n = re.sub(r"_\d+$", "", b.name)
        if base_n in REN:
            b.name = REN[base_n]
    arm.scale = (ERIC_S,) * 3
    r.location, r.rotation_euler = loc, (0, 0, yaw)
    for b in body:
        for m in b.data.materials:
            bs = m.node_tree.nodes.get("Principled BSDF") if m and m.use_nodes else None
            if bs:
                bs.inputs["Roughness"].default_value = 0.55
    return r, arm, body


HEAD_UP = {"Neck": (0, -0.08, 1), "Head": (0, -0.12, 1)}      # keyed on every pose so no head key leaks across strips
SIT = {"LeftUpLeg": (0.12, -1, 0.02), "RightUpLeg": (-0.12, -1, 0.02), "LeftLeg": (0, -0.15, -1), "RightLeg": (0, -0.15, -1),
       "Spine": (0, -0.12, 1), "LeftArm": (0.35, -0.75, -0.55), "RightArm": (-0.35, -0.75, -0.55),
       "LeftForeArm": (-0.1, -1, 0.05), "RightForeArm": (0.1, -1, 0.05)}
SLUMP = SIT | {"Spine": (0, -0.45, 1), "Neck": (0, -0.6, 1), "Head": (0, -0.8, 0.6),
               "LeftArm": (0.2, -0.1, -1), "RightArm": (-0.2, -0.1, -1), "LeftForeArm": (0.05, -0.3, -1),
               "RightForeArm": (-0.05, -0.3, -1)}
STAND = {"LeftUpLeg": (0.04, 0, -1), "RightUpLeg": (-0.04, 0, -1), "LeftLeg": (0, 0.03, -1), "RightLeg": (0, 0.03, -1),
         "Spine": (0, 0.02, 1), "LeftArm": (0.22, 0.02, -1), "RightArm": (-0.22, 0.02, -1),
         "LeftForeArm": (0.08, -0.12, -1), "RightForeArm": (-0.08, -0.12, -1)}
LOOKUP = STAND | {"Neck": (0, 0.2, 1), "Head": (0, 0.55, 1)}
SCRATCH = LOOKUP | {"RightArm": (-0.75, -0.15, 0.6), "RightForeArm": (0.45, 0.2, 0.85)}
CHEER = STAND | {"LeftArm": (0.6, -0.15, 0.8), "RightArm": (-0.6, -0.15, 0.8), "LeftForeArm": (0.5, -0.15, 0.85),
                 "RightForeArm": (-0.5, -0.15, 0.85), "Head": (0, 0.1, 1)}
HANDS_HEAD = SIT | {"LeftArm": (0.85, -0.2, 0.45), "RightArm": (-0.85, -0.2, 0.45), "LeftForeArm": (-0.55, -0.15, 0.8),
                    "RightForeArm": (0.55, -0.15, 0.8), "Spine": (0, 0.1, 1), "Neck": (0, 0.25, 1), "Head": (0, 0.45, 1)}
ARMS_UP = SIT | {"LeftArm": (0.5, -0.2, 1), "RightArm": (-0.5, -0.2, 1), "LeftForeArm": (0.3, -0.2, 1),
                 "RightForeArm": (-0.3, -0.2, 1)}


def glb(path, decimate=None, keep=None):
    """Import a glTF prop, optionally keep only some meshes, decimate, and bake transforms. → (meshes, lo, hi)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        D.adopt(o)
    bpy.context.view_layer.update()
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
        if decimate and len(o.data.polygons) > 2000:
            md = o.modifiers.new("dec", "DECIMATE")
            md.ratio = decimate
            bpy.context.view_layer.objects.active = o
            with bpy.context.temp_override(object=o, active_object=o):
                bpy.ops.object.modifier_apply(modifier=md.name)
    return meshes, *bounds(meshes)


def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def fit(objs, lo, hi, size, axis=0, base=True):
    """Re-centre meshes on their footprint (bottom at z=0 if base) and scale so extent[axis] == size."""
    s = size / (hi - lo)[axis]
    off = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z if base else (lo.z + hi.z) / 2))
    for o in objs:
        o.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation(-off))
    return s




def template(path, size, axis=0, base=True, decimate=None, keep=None, rot=None, join=False):
    """Import a prop once as hidden template meshes (fit to `size` along `axis`); copy() makes linked instances.
    join=True merges it into ONE mesh so big crowds of copies stay cheap (one object each)."""
    with L.building(bpy.context.scene):                 # import into the context scene (decimate/join need its view layer)
        ms, lo, hi = glb(path, decimate=decimate, keep=keep)
    if join and len(ms) > 1:
        with bpy.context.temp_override(active_object=ms[0], object=ms[0], selected_objects=ms,
                                       selected_editable_objects=ms):
            bpy.ops.object.join()
        ms = [ms[0]]
    if rot:
        for o in ms:
            o.data.transform(Matrix.Rotation(rot[1], 4, rot[0]))
        lo, hi = bounds(ms)
    fit(ms, lo, hi, size, axis=axis, base=base)
    for o in ms:
        for c in list(o.users_collection):
            c.objects.unlink(o)
    return ms


def copy(tmpl, name, loc, s=1.0, yaw=0.0, mat=None):
    """Linked copy of a template under one empty (scale/rot/loc on the empty). `mat` overrides every slot."""
    g = D.empty(name, loc)
    for t in tmpl:
        o = t.copy()
        D.link(o)
        o.parent = g
        if mat:
            for i in range(len(o.material_slots)):
                o.material_slots[i].link = "OBJECT"
                o.material_slots[i].material = mat
    g.scale = (s,) * 3
    g.rotation_euler = (0, 0, yaw)
    return g


def pop(o, f, dur_f=9, amount=1.15):
    s = tuple(o.scale)
    D.key(o, "scale", 1, (0, 0, 0))
    D.key(o, "scale", f, (0, 0, 0))
    D.overshoot(o, "scale", f, f + dur_f, (0, 0, 0), s, amount)


def vanish(o, f, dur_f=1):
    D.key(o, "scale", f - dur_f, tuple(o.scale))
    D.key(o, "scale", f, (0, 0, 0))


def gold_mat(name="gold", rough=0.22):
    return D.mat(name, H("#ffb627"), rough=rough, metal=1.0)
