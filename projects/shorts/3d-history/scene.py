"""blender -b -P scene.py -- <out.blend>: "How 3D modeling started and where it's going" (60 years → Vi3W).

Timeline seconds (VO starts at VO_AT = 0.3 s). Each era is drawn in its own graphics style:
  LAB 0.0 hook teapot morphs wire→flat→gouraud→plastic→PBR | DESK 2.3 "the hardest part never changed"
  TX2 5.6 1963 Sketchpad: light pen, room-sized computer | HAND 12.9 1972 Catmull's hand → polygons one by one
  LAB 18.6 1975 Utah teapot | TOYS 23.9 1995 first fully CG feature | LAB 29.5 Maya/3ds Max/Blender quality ramp
  DESK 35.4 same artist, same shot: 1998, 2008, 2018, today | VIEWPORT 42.6 click a vertex, drag, repeat
  DESK 47.9 "days" | GRAPH 50.6 graphics line rises, workflow line flat | 53.7-59.0 REAL Vi3W capture (compose)
  SHOW 59.0 real Vi3W models; 62.0 the real robot sketch beside its real Vi3W model. Then the shared outro.
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
END = 66.6
T = D.T
H = D.hex_lin
random.seed(7)

base = D.reset(w=720, h=1280, frames=T(END) - 1)
D.fast_eevee(base, samples=8, look="AgX - Punchy")
base.render.resolution_x, base.render.resolution_y = 720, 1280
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
        P.lowpoly(b, 9000)
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




# ================================================================= shared materials
SERIF = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
GREEN = flat("phosphor", "#39ff6a", 3.0)
ORANGE = flat("vtx", "#ff8a1f", 2.5)
WHITE_M = flat("whitem", "#f2f2f2", 0.05)
INK = flat("ink", "#111111")
METAL = D.mat("metal", H("#8a8f99"), rough=0.4, metal=0.6)
BEIGE = D.mat("beige", H("#d9cfb4"), rough=0.6)
BLACKP = L.plastic("blackp", H("#18191d"), rough=0.35)


def stxt(body, size, loc, m, rot=(math.pi / 2, 0, 0), extrude=0.02):
    return D.text3d("s_" + body[:10], body, size, loc, m, extrude=extrude, bevel=size * 0.02, font=SERIF, rot=rot)


def wire_copy(o, m, thick=0.004, ratio=None, name=None, build=None):
    c = o.copy()
    c.data = o.data.copy()
    D.link(c)
    c.name = name or o.name + "_wire"
    if ratio:
        d = c.modifiers.new("dec", "DECIMATE")
        d.ratio = ratio
    if build:
        bd = c.modifiers.new("build", "BUILD")
        bd.frame_start, bd.frame_duration, bd.use_random_order = build
    w = c.modifiers.new("wire", "WIREFRAME")
    w.thickness, w.use_replace = thick, True
    w.offset = 1.0
    w.use_even_offset = False
    c.data.materials.clear()
    c.data.materials.append(m)
    return c


def tree(o):
    return [o] + list(o.children_recursive)


def visible(o, spans):
    """Show o (and its whole child tree) only inside the [t0, t1) spans; hidden elsewhere."""
    for x in tree(o):
        x.hide_render = True
        x.keyframe_insert("hide_render", frame=1)
        for a, b in spans:
            x.hide_render = False
            x.keyframe_insert("hide_render", frame=max(1, T(a)))
            x.hide_render = True
            x.keyframe_insert("hide_render", frame=T(b))
        for fc in D._fcurves(x.animation_data.action):
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"


def show_between(objs, t0, t1=None):
    for o in objs:
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=1)
        o.hide_render = False
        o.keyframe_insert("hide_render", frame=T(t0))
        if t1:
            o.hide_render = True
            o.keyframe_insert("hide_render", frame=T(t1))


def studio(sc, colour, strength=0.9, key_w=450, at=(0, 0, 1.0)):
    L.hdri_world(sc, "studio_small_09", strength, rot_deg=40, backdrop=colour, backdrop_strength=0.9)
    D.cyclorama(L.plastic(sc.name + "_cyc", colour, rough=0.72, coat=0.0), width=40, depth=30, y_wall=8, radius=4, height=20)
    D.area_light(sc.name + "_key", key_w, (-3, -5, 6), at, size=4)
    D.area_light(sc.name + "_rim", key_w * 0.6, (3, 4, 4), at, size=3, rgb=H("#fff1dc"))


def teapot(name, loc, size, m, smooth=True):
    ms = glb(A("teapot.glb"))
    lo, hi = bounds(ms)
    s = size / max(hi - lo)
    off = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    g = D.empty(name, loc)
    for o in ms:
        o.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation(-off))
        o.parent = g
        o.data.materials.clear()
        o.data.materials.append(m)
        for p in o.data.polygons:
            p.use_smooth = smooth
    return g, ms


def real_model(path, loc, size, rotz=0.0, name="model"):
    """A real Vi3W GLB (static mesh), re-centred on its footprint, scaled to `size` tall."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    for o in new:
        D.adopt(o)
    upd()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = size / (hi.z - lo.z)
    piv = D.empty(name, loc)
    for o in new:
        if o.parent is None:
            o.parent = piv
            o.location = o.location - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    piv.scale = (s,) * 3
    piv.rotation_euler = (0, 0, rotz)
    return piv


SIT = {"LeftUpLeg": (0.12, -1, 0.02), "RightUpLeg": (-0.12, -1, 0.02), "LeftLeg": (0, -0.15, -1), "RightLeg": (0, -0.15, -1),
       "Spine": (0, -0.05, 1), "LeftArm": (0.3, -0.7, -0.6), "RightArm": (-0.3, -0.7, -0.6),
       "LeftForeArm": (-0.05, -1, 0.1), "RightForeArm": (0.05, -1, 0.1), "Head": (0, -0.2, 1)}
SLUMP = SIT | {"Spine": (0, -0.4, 1), "Neck": (0, -0.6, 1), "Head": (0, -0.8, 0.6),
               "LeftArm": (0.2, -0.3, -1), "RightArm": (-0.2, -0.3, -1)}
PEN = SIT | {"RightArm": (-0.25, -0.85, -0.2), "RightForeArm": (0.15, -0.9, 0.35)}
RAISE = STAND | {"RightArm": (-0.35, -0.45, 0.8), "RightForeArm": (-0.05, -0.25, 1), "Head": (0, -0.1, 1)}
CHEER = STAND | {"LeftArm": (0.6, -0.15, 0.8), "RightArm": (-0.6, -0.15, 0.8), "LeftForeArm": (0.5, -0.15, 0.85),
                 "RightForeArm": (-0.5, -0.15, 0.85), "Head": (0, 0.1, 1)}

# ================================================================= LAB: hook teapot through the eras (x=0), 1975 Utah (x=12), quality ramp (x=24)
lab = L.new_set("LAB", main=True)
studio(lab, H("#20232c"), strength=0.7, key_w=500, at=(0, 0, 0.6))
styles = [("t_wire", None, False), ("t_flat", D.mat("tflat", H("#9a9ca3"), rough=0.9), False),
          ("t_gour", D.mat("tgour", H("#6d8fd6"), rough=0.5), True),
          ("t_plas", L.plastic("tplas", H("#ff3b47"), rough=0.2, coat=0.8), True),
          ("t_pbr", L.pbr("tpbr", "metal_plate", scale=3, rough_mul=0.3, spec=0.8), True)]
hook = []
for i, (nm, m, sm) in enumerate(styles):
    g, ms = teapot(nm, (0, 0, 0.35), 1.0, m or WHITE_M, smooth=sm)
    if m is None:
        for o in ms:
            w = o.modifiers.new("wire", "WIREFRAME")
            w.thickness, w.use_replace = 0.012, True
            w.use_even_offset = False
            o.data.materials.clear()
            o.data.materials.append(GREEN)
    hook.append(g)
for i, g in enumerate(hook):
    visible(g, [(0.0 if i == 0 else i * 0.45, (i + 1) * 0.45 if i < 4 else 2.4)])
D.cyl("ped", 0.75, 0.35, (0, 0, 0.175), m=BLACKP, verts=48)
for g in hook:
    D.key(g, "rotation_euler", 1, (0, 0, 0))
    D.key(g, "rotation_euler", T(2.3), (0, 0, math.radians(200)))
    D.ease_last(g, "LINEAR")
shot(lab, "A_hook", 0.0, 2.3, (0.0, -2.6, 1.3), (0.0, -2.1, 1.1), (0, 0, 0.75), (0, 0, 0.75), 30)
# 1975: the classic Utah teapot on a checkerboard
chk = bpy.data.materials.new("checker")
chk.use_nodes = True
nt = chk.node_tree
ct = nt.nodes.new("ShaderNodeTexChecker")
ct.inputs["Scale"].default_value = 6
ct.inputs["Color1"].default_value = (*H("#d8d8d8"), 1)
ct.inputs["Color2"].default_value = (*H("#3a3a3a"), 1)
nt.links.new(ct.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
D.box("checkfloor", (4, 4, 0.02), (12, 0, 0.01), chk)
utah, _ = teapot("utah", (12, 0, 0.02), 1.1, D.mat("utahm", H("#e8e2d0"), rough=0.35), smooth=True)
D.key(utah, "rotation_euler", T(18.6), (0, 0, math.radians(-30)))
D.key(utah, "rotation_euler", T(23.9), (0, 0, math.radians(60)))
shot(lab, "T1_1975", 18.6, 21.1, (12.0, -3.0, 1.6), (12.0, -2.5, 1.4), (12, 0, 0.55), (12, 0, 0.55), 30)
shot(lab, "T2_famous", 21.1, 23.9, (13.6, -1.8, 0.9), (13.0, -2.0, 0.8), (12, 0, 0.5), (12, 0, 0.55), 30)
# quality ramp: same man, flat → clay → full texture
ramp = []
for i, (nm, m, ratio) in enumerate((("r_flat", D.mat("rflat", H("#a0a3aa"), rough=0.9), 0.04),
                                     ("r_clay", D.mat("rclay", H("#c9a58a"), rough=0.6), 0.25), ("r_real", None, None))):
    r, arm, body = man(nm, (-12, 0, 0), math.radians(-15))
    pose_strip(arm, r, [(1, STAND), (T(END), STAND)], 1, T(END), blend=1)
    for b in body:
        if ratio:
            d = b.modifiers.new("dec2", "DECIMATE")
            d.ratio = ratio
            b.data = b.data.copy()
            b.data.materials.clear()
            b.data.materials.append(m)
            for p in b.data.polygons:
                p.use_smooth = i > 0
    ramp.append(r)
for i, r in enumerate(ramp):
    visible(r, [(0.0 if i == 0 else 29.5 + i * 1.3, 29.5 + (i + 1) * 1.3 if i < 2 else 99)])
D.area_light("ramp_key", 600, (-13.5, -2.5, 3.0), (-12, 0, 1.4), size=2.5, rgb=H("#fff0dc"))
D.area_light("ramp_rim", 500, (-10.4, 1.8, 2.6), (-12, 0, 1.5), size=1.5, rgb=H("#9fc4ff"))
shot(lab, "R1_ramp", 29.5, 35.4, (-11.1, -2.2, 1.65), (-11.65, -1.0, 1.62), (-12, 0, 1.45), (-12, 0, 1.6), 30, 40)

# ================================================================= TX2: 1963, a computer that fills a room
tx = L.new_set("TX2")
with L.building(tx):
    L.hdri_world(tx, "studio_small_09", 0.15, backdrop=H("#0a0a0c"))
    D.room("txroom", (0, 2, 2), (12, 12, 4), L.pbr("txwall", "dirty_concrete", scale=0.8))
    D.box("txfloor", (12, 12, 0.02), (0, 2, 0.0), L.pbr("txfl", "concrete_floor_02", scale=0.8))
    D.area_light("txkey", 260, (-2.5, -2.5, 3.6), (0, 0.5, 1.0), size=3)
    D.area_light("txfill", 160, (3.0, 4.0, 3.5), (0, 2, 1.0), size=4)
    random.seed(3)
    LAMP_ON = flat("lampon", "#ffe28a", 4.0)
    LAMP_OFF = flat("lampoff", "#3a2f1a")
    cab_x = [-3.6 + k * 0.9 for k in range(9)]
    for row, y in enumerate((2.0, 4.2)):
        for x in cab_x:
            D.box("cab", (0.85, 0.7, 2.2), (x, y, 1.1), METAL, bevel=0.01)
            for r in range(4):
                for c in range(5):
                    lo_ = D.box("lamp", (0.06, 0.02, 0.06), (x - 0.24 + c * 0.12, y - 0.36, 1.6 + r * 0.12),
                                LAMP_ON if random.random() < 0.5 else LAMP_OFF)
                    if random.random() < 0.35:
                        show_between([lo_], random.uniform(5.6, 8), random.uniform(9, 14))
            D.cyl("reel", 0.16, 0.03, (x, y - 0.36, 0.85), (math.pi / 2, 0, 0), m=INK, verts=16)
    D.box("console", (1.6, 0.8, 0.8), (0, -0.2, 0.4), METAL, bevel=0.01)
    crt = D.cyl("crt", 0.28, 0.5, (0, -0.15, 1.15), (math.pi / 2, 0, 0), m=METAL, verts=24)
    D.cyl("crtglass", 0.24, 0.02, (0, -0.41, 1.15), (math.pi / 2, 0, 0), m=flat("glass", "#062010", 0.6), verts=24)
    cube = D.box("vcube", (0.18, 0.18, 0.18), (0, -0.44, 1.15), GREEN)
    w = cube.modifiers.new("wire", "WIREFRAME")
    w.thickness, w.use_replace = 0.006, True
    w.use_even_offset = False
    D.key(cube, "rotation_euler", T(5.6), (0.4, 0, 0))
    D.key(cube, "rotation_euler", T(12.9), (0.4 + 3, 2.5, 0))
    D.ease_last(cube, "LINEAR")
    op, oparm, _ = man("sutherland", (0, -1.05, 0.6 - 96.9 * ERIC_S), math.pi)
    D.box("stool", (0.45, 0.45, 0.55), (0, -1.15, 0.28), METAL)
    pose_strip(oparm, op, [(1, PEN), (T(END), PEN)], 1, T(END), blend=1)
    tx.frame_set(T(9.0))
    upd()
    hand = oparm.matrix_world @ oparm.pose.bones["RightHand"].head
    pen = cyl_between("lightpen", hand + Vector((0, 0.04, 0.03)), Vector((0.05, -0.43, 1.18)), 0.012, INK)
    D.cyl("pencord", 0.004, 1.2, (0.4, -0.6, 0.7), (0.6, 0.3, 0), m=INK, verts=6)
    shot(tx, "T1_room", 5.6, 8.3, (2.6, -3.8, 1.9), (2.1, -3.2, 1.75), (0, 0.2, 1.1), (0, 0.0, 1.15), 22)
    shot(tx, "T2_pen", 8.3, 10.8, (0.55, -1.15, 1.45), (0.45, -1.0, 1.35), (0.0, -0.42, 1.15), (0.02, -0.42, 1.16), 32)
    shot(tx, "T3_whole_room", 10.8, 12.9, (-2.6, -3.0, 3.0), (-3.2, -3.5, 3.3), (0.5, 3.0, 1.0), (0.5, 3.0, 1.0), 20)

# ================================================================= HAND: 1972, a hand turned into polygons
hs = L.new_set("HAND")
with L.building(hs):
    L.hdri_world(hs, "studio_small_09", 0.35, backdrop=H("#0c0c0e"))
    D.area_light("hkey", 380, (-1.5, -2.5, 2.8), (0, 0, 1.6), size=2.5)
    D.area_light("hrim", 260, (1.6, 1.4, 2.6), (0, 0, 1.6), size=1.5)
    cat, catarm, catbody = man("catmull", (0, 0, 0))
    pose_strip(catarm, cat, [(1, STAND), (T(13.4), STAND), (T(14.1), RAISE), (T(END), RAISE)], 1, T(END), blend=1)
    PLASTER = D.mat("plaster", H("#ece8df"), rough=0.85)
    for b in catbody:
        b.data = b.data.copy()
        b.data.materials.clear()
        b.data.materials.append(PLASTER)
        wire_copy(b, INK, thick=0.35, ratio=0.12, name="catwire", build=(T(15.9), T(18.6) - T(15.9), True))
    hs.frame_set(T(16.5))
    upd()
    HP = catarm.matrix_world @ catarm.pose.bones["RightHand"].head + Vector((0, 0, 0.08))
    shot(hs, "H1_1972", 12.9, 15.9, (0.9, -2.6, 1.5), (0.7, -2.1, 1.55), (0, 0, 1.3), (0, 0, 1.45), 30)
    shot(hs, "H2_polys", 15.9, 18.6, HP + Vector((0.15, -0.6, 0.05)), HP + Vector((0.1, -0.42, 0.03)), HP, HP, 34)

# ================================================================= TOYS: 1995, smooth plastic toys
ty = L.new_set("TOYS")
with L.building(ty):
    L.hdri_world(ty, "studio_small_09", 0.9, rot_deg=60, backdrop=H("#ffd9a8"))
    D.room("toyroom", (0, 1, 2), (8, 8, 4), L.pbr("toywall", "painted_plaster_wall", scale=0.8, tint=H("#8fd0ff"), tint_amount=0.8))
    D.box("toyfloor", (8, 8, 0.02), (0, 1, 0.0), L.pbr("toyfl", "laminate_floor_02", scale=0.8))
    D.area_light("sunpatch", 700, (-2.5, -2.0, 3.4), (0, 0.6, 0.2), size=2.0, rgb=H("#fff0d0"))
    cols = ["#ff3b47", "#ffc21a", "#3bd2ff", "#7cff6b", "#ff7ad8", "#ff8a1f"]
    for i, (x, y, z, ch) in enumerate(((-0.5, 0.4, 0.12, "A"), (-0.25, 0.45, 0.12, "B"), (-0.38, 0.42, 0.36, "C"), (0.35, 0.7, 0.12, "D"))):
        bl = D.box(f"block{i}", (0.24, 0.24, 0.24), (x, y, z), L.plastic(f"blk{i}", H(cols[i]), rough=0.3, coat=0.6), bevel=0.02)
        bl.rotation_euler = (0, 0, math.radians(random.uniform(-15, 15)))
        t_ = D.text3d(f"L{ch}", ch, 0.16, (0, -0.125, -0.05), L.plastic("blkl", H("#ffffff"), rough=0.3), extrude=0.01, font=SERIF)
        t_.parent = bl
    rocket = D.empty("rocket", (0.45, 0.25, 0))
    D.cyl("rbody", 0.09, 0.5, (0, 0, 0.35), m=L.plastic("rwhite", H("#f4f4f4"), rough=0.25, coat=0.7), verts=24).parent = rocket
    D.cone("rnose", 0.09, 0.2, (0, 0, 0.7), m=L.plastic("rred", H("#ff3b47"), rough=0.25, coat=0.7), verts=24).parent = rocket
    for k in range(3):
        a = k / 3 * math.tau
        f = D.box("fin", (0.02, 0.14, 0.16), (0.1 * math.cos(a), 0.1 * math.sin(a), 0.16), L.plastic("rred2", H("#ff3b47"), coat=0.7))
        f.rotation_euler = (0, 0, a + math.pi / 2)
        f.parent = rocket
    D.sphere("toyball", 0.15, (-0.05, 0.05, 0.15), m=L.plastic("ballb", H("#2f6bff"), rough=0.2, coat=0.9))
    car = D.empty("toycar", (0.05, -0.25, 0.0))
    D.box("cbody", (0.34, 0.18, 0.1), (0, 0, 0.1), L.plastic("cyel", H("#ffc21a"), coat=0.8), bevel=0.03).parent = car
    D.box("ctop", (0.18, 0.16, 0.08), (-0.02, 0, 0.19), L.plastic("cyel2", H("#ffc21a"), coat=0.8), bevel=0.03).parent = car
    for x in (-0.11, 0.11):
        for yy in (-0.09, 0.09):
            D.cyl("wheel", 0.045, 0.03, (x, yy, 0.045), (math.pi / 2, 0, 0), m=BLACKP, verts=16).parent = car
    car.rotation_euler = (0, 0, math.radians(25))
    D.key(car, "location", T(26.6), (0.05, -0.25, 0))
    D.key(car, "location", T(29.5), (-0.35, -0.45, 0))
    D.key(rocket, "rotation_euler", T(23.9), (0, 0, 0))
    D.key(rocket, "rotation_euler", T(29.5), (0, 0, 1.4))
    shot(ty, "Y1_1995", 23.9, 26.6, (0.9, -1.6, 0.9), (0.7, -1.3, 0.75), (0, 0.4, 0.25), (0, 0.4, 0.25), 28)
    shot(ty, "Y2_toys", 26.6, 29.5, (-0.6, -0.9, 0.35), (-0.3, -0.75, 0.3), (0.1, 0.4, 0.25), (0.2, 0.4, 0.3), 26)

# ================================================================= DESK: the artist, 1998 → today (same shot), click click click
dk = L.new_set("DESK")
with L.building(dk):
    L.hdri_world(dk, "studio_small_09", 0.12, backdrop=H("#05070f"))
    D.room("office", (0, 0, 2.0), (7, 7, 4), L.pbr("offwall", "plastered_wall", scale=0.6, tint=H("#2e3150"), tint_amount=0.9, normal=0.5))
    D.box("offfloor", (7, 7, 0.02), (0, 0, 0.0), L.pbr("offfl", "laminate_floor_02", scale=0.8, rough_mul=0.7))
    DY = -0.8
    D.box("desktop", (1.8, 0.8, 0.05), (0, DY - 0.15, 0.74), L.pbr("deskw", "wood_table_001", scale=1.5))
    for x in (-0.85, 0.85):
        D.box("dleg", (0.05, 0.7, 0.72), (x, DY - 0.15, 0.36), INK)
    D.box("chair", (0.5, 0.5, 0.08), (0, 0.05, 0.55), BLACKP)
    D.box("chairb", (0.5, 0.06, 0.6), (0, 0.32, 0.88), BLACKP)
    SCR = D.mat("viewport", H("#2a2b30"), rough=1, emit=H("#3a3c44"), emit_strength=1.6)
    SCR_Y = DY - 0.36
    mons = []
    # 1998 beige CRT
    g = D.empty("m1998", (0, 0, 0))
    D.box("crtbody", (0.46, 0.45, 0.42), (0, SCR_Y - 0.25, 1.0), BEIGE, bevel=0.02).parent = g
    D.box("crtscr", (0.36, 0.01, 0.28), (0, SCR_Y, 1.02), SCR).parent = g
    D.box("kb98", (0.46, 0.16, 0.03), (0, DY + 0.05, 0.78), BEIGE).parent = g
    mons.append((g, [(37.0, 38.7)]))
    # 2008 boxy LCD
    g = D.empty("m2008", (0, 0, 0))
    D.box("lcd", (0.5, 0.05, 0.36), (0, SCR_Y - 0.03, 1.02), BLACKP, bevel=0.01).parent = g
    D.box("lcdscr", (0.44, 0.01, 0.3), (0, SCR_Y, 1.02), SCR).parent = g
    D.box("lcdst", (0.06, 0.06, 0.2), (0, SCR_Y - 0.06, 0.84), BLACKP).parent = g
    D.box("kb08", (0.46, 0.16, 0.02), (0, DY + 0.05, 0.775), BLACKP).parent = g
    mons.append((g, [(38.7, 40.2)]))
    # 2018 widescreen
    g = D.empty("m2018", (0, 0, 0))
    D.box("wide", (0.66, 0.03, 0.4), (0, SCR_Y - 0.02, 1.08), BLACKP, bevel=0.005).parent = g
    D.box("widescr", (0.63, 0.01, 0.37), (0, SCR_Y, 1.08), SCR).parent = g
    D.box("widest", (0.05, 0.05, 0.25), (0, SCR_Y - 0.06, 0.87), METAL).parent = g
    D.box("kb18", (0.44, 0.14, 0.015), (0, DY + 0.05, 0.775), METAL).parent = g
    mons.append((g, [(40.2, 41.6)]))
    # today: ultrawide
    g = D.empty("mtoday", (0, 0, 0))
    D.box("uw", (1.0, 0.03, 0.42), (0, SCR_Y - 0.02, 1.1), BLACKP, bevel=0.005).parent = g
    D.box("uwscr", (0.97, 0.01, 0.39), (0, SCR_Y, 1.1), SCR).parent = g
    D.box("uwst", (0.05, 0.05, 0.25), (0, SCR_Y - 0.06, 0.88), METAL).parent = g
    D.box("kbnow", (0.44, 0.14, 0.015), (0, DY + 0.05, 0.775), flat("rgbkb", "#7a2cff", 1.2)).parent = g
    mons.append((g, [(0.0, 37.0), (41.6, 99)]))
    for g, spans in mons:
        visible(g, spans)
    # on-screen model: a small orange wire sphere, same in every era
    sv = D.sphere("onscreen", 0.09, (0, SCR_Y + 0.015, 1.05), m=ORANGE, seg=12, rings=8)
    w = sv.modifiers.new("wire", "WIREFRAME")
    w.thickness, w.use_replace = 0.004, True
    w.use_even_offset = False
    D.key(sv, "rotation_euler", 1, (0, 0, 0))
    D.key(sv, "rotation_euler", T(END), (0, 0, 6))
    D.ease_last(sv, "LINEAR")
    D.box("mouse", (0.06, 0.1, 0.03), (0.32, DY + 0.08, 0.78), BLACKP, bevel=0.01)
    D.area_light("monglow", 140, (0, SCR_Y + 0.15, 1.05), (0, 0.2, 1.1), size=0.8, rgb=H("#cfd8ff"))
    D.area_light("deskkey", 120, (-1.8, -2.2, 2.6), (0, -0.2, 1.0), size=2.0, rgb=H("#8fa6ff"))
    D.area_light("deskrim", 160, (1.6, 1.8, 2.3), (0, 0, 1.2), size=1.5, rgb=H("#ff9a5a"))
    WIN = D.mat("dwin", H("#0b1530"), rough=1, emit=H("#132657"), emit_strength=0.9)
    D.box("dwin", (1.3, 0.05, 1.0), (-1.9, -3.45, 2.0), WIN)
    e = WIN.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
    for i in range(14):
        e.default_value = (*H("#ffd88a" if i % 2 else "#132657"), 1)
        e.keyframe_insert("default_value", frame=T(48.2 + i * 0.18))
    art, artarm, _ = man("artist", (0, 0.0, 0.6 - 96.9 * ERIC_S), 0.0)
    pose_strip(artarm, art, [(1, SIT), (T(48.3), SIT), (T(48.9), SLUMP), (T(END), SLUMP)], 1, T(END), blend=1)
    for i in range(60):                                        # mouse-click twitch
        D.key(art, "location", T(35.4) + i * 4, (0, 0.0 + (0.006 if i % 2 else 0), 0.6 - 96.9 * ERIC_S))
    OTS = ((0.85, 0.75, 1.55), (0, SCR_Y, 1.02))
    shot(dk, "D0_part", 2.3, 3.9, (0.12, SCR_Y + 0.28, 1.08), (0.1, SCR_Y + 0.22, 1.07), (0, SCR_Y, 1.05), (0, SCR_Y, 1.05), 32)
    shot(dk, "D0_never", 3.9, 5.6, (1.6, 1.6, 1.9), (1.4, 1.4, 1.8), (0, -0.4, 1.0), (0, -0.4, 1.0), 26)
    shot(dk, "D1_look", 35.4, 37.0, (1.5, 1.6, 1.9), (0.95, 0.85, 1.6), (0, -0.4, 1.0), (0, SCR_Y, 1.02), 26)
    for y, t0, t1 in (("1998", 37.0, 38.7), ("2008", 38.7, 40.2), ("2018", 40.2, 41.6), ("today", 41.6, 42.6)):
        shot(dk, f"D_{y}", t0, t1, OTS[0], OTS[0], OTS[1], OTS[1], 26)
    shot(dk, "D9_days", 47.9, 50.6, (-1.3, -2.0, 1.4), (-1.1, -1.7, 1.35), (0, -0.2, 1.0), (0, -0.2, 0.95), 24)

# ================================================================= VIEWPORT: click a vertex, drag it, repeat
vp = L.new_set("VIEWPORT")
with L.building(vp):
    D.world(vp, H("#2b2c31"), 1.0)
    vp.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    GRID = flat("vgrid", "#3d3f46", 0.6)
    for k in range(-10, 11):
        D.box("vg", (20, 0.01, 0.002), (0, k, -1.2), GRID)
        D.box("vg", (0.01, 20, 0.002), (k, 0, -1.2), GRID)
    D.box("vgx", (20, 0.02, 0.003), (0, 0, -1.19), flat("axx", "#c8414a", 1.0))
    D.box("vgy", (0.02, 20, 0.003), (0, 0, -1.19), flat("axy", "#7ec44a", 1.0))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1.0)
    ms = bpy.context.active_object
    ms.name = "vmesh"
    D.adopt(ms)
    D.give(ms, ORANGE)
    VTX = flat("vdot", "#111111")
    SEL = flat("vsel", "#ffffff", 3.0)
    verts = [v.co.copy() for v in ms.data.vertices]
    front = sorted(range(len(verts)), key=lambda i: verts[i].y)[:24]          # vertices facing the camera (-Y)
    random.seed(4)
    picks = random.sample(front, 6)
    hooks, times = [], [42.9, 44.3, 45.4, 46.2, 46.8, 47.3]
    for k, (vi, t0) in enumerate(zip(picks, times)):
        p = verts[vi]
        e_ = D.empty(f"hook{k}", p)
        hm = ms.modifiers.new(f"hook{k}", "HOOK")
        hm.object = e_
        hm.vertex_indices_set([vi])
        hm.matrix_inverse = Matrix.Translation(-p)
        out_ = p + p.normalized() * random.uniform(0.25, 0.45) + Vector((random.uniform(-0.15, 0.15), 0, random.uniform(-0.1, 0.15)))
        dur = 0.8 if k < 2 else 0.35
        D.key(e_, "location", T(t0), p)
        D.key(e_, "location", T(t0 + dur), out_)
        hooks.append((e_, p, out_, t0, dur))
    w = ms.modifiers.new("wire", "WIREFRAME")
    w.thickness, w.use_replace = 0.012, True
    w.use_even_offset = False
    for i, p in enumerate(verts):
        hooked = next((h for h in hooks if (h[1] - p).length < 1e-5), None)
        d = D.box(f"vd{i}", (0.035, 0.035, 0.035), p, VTX)
        if hooked:
            d.parent = hooked[0]
            d.location = (0, 0, 0)
            d.data = d.data.copy()
            D.give(d, SEL)
    # cursor arrow follows each drag
    bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.07, depth=0.02)
    cur = bpy.context.active_object
    cur.name = "cursor"
    D.adopt(cur)
    D.give(cur, flat("curm", "#ffffff", 1.0))
    cur.rotation_euler = (math.pi / 2, 0, math.radians(20))
    for e_, p, o_, t0, dur in hooks:
        D.key(cur, "location", T(t0) - 4, p + Vector((0.3, -0.3, 0.2)))
        D.key(cur, "location", T(t0), p + Vector((0.04, -0.12, -0.04)))
        D.key(cur, "location", T(t0 + dur), o_ + Vector((0.04, -0.12, -0.04)))
    D.key(ms, "rotation_euler", T(42.6), (0, 0, 0))
    D.key(ms, "rotation_euler", T(47.9), (0, 0, 0))
    shot(vp, "V1_click", 42.6, 45.2, (0.5, -3.6, 0.6), (0.35, -3.1, 0.5), (0, 0, 0.1), (0, 0, 0.1), 30)
    shot(vp, "V2_repeat", 45.2, 47.9, (-1.8, -3.4, 1.4), (-1.4, -3.0, 1.2), (0, 0, 0), (0, 0, 0), 26)

# ================================================================= GRAPH: graphics evolved, the work didn't
gr = L.new_set("GRAPH")
with L.building(gr):
    D.world(gr, H("#0a1033"), 1.0)
    AX = flat("axis", "#c9d2ff", 1.0)
    D.box("xaxis", (3.2, 0.02, 0.02), (0, 0, 0), AX)
    D.box("yaxis", (0.02, 0.02, 2.4), (-1.6, 0, 1.2), AX)
    for k, yr in enumerate(("1963", "1975", "1995", "2010", "2026")):
        stxt(yr, 0.12, (-1.6 + k * 0.8, -0.02, -0.15), AX, extrude=0.005)

    def line(name, pts, m, t0, t1):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", 0.03, 3
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p_, xyz in zip(sp.points, pts):
            p_.co = (*xyz, 1)
        o = D.link(bpy.data.objects.new(name, cu))
        o.data.materials.append(m)
        cu.bevel_factor_end = 0.0
        cu.keyframe_insert("bevel_factor_end", frame=T(t0))
        cu.bevel_factor_end = 1.0
        cu.keyframe_insert("bevel_factor_end", frame=T(t1))
        return o
    up = [(-1.6 + i * 0.16, -0.01, 0.1 + 2.1 * (i / 20) ** 2.2) for i in range(21)]
    line("gline", up, flat("gl", "#3dff8a", 2.5), 50.7, 51.9)
    line("rline", [(-1.6 + i * 0.32, -0.01, 0.12) for i in range(11)], flat("rl", "#ff3b47", 2.5), 52.3, 53.4)
    lg = txt("GRAPHICS", 0.15, (0.85, -0.02, 2.4), flat("glt", "#3dff8a", 2.0), extrude=0.01)
    pop(lg, 51.3)
    lr = txt("THE WORK", 0.15, (1.0, -0.02, 0.32), flat("rlt", "#ff3b47", 2.0), extrude=0.01)
    pop(lr, 52.5)
    shot(gr, "G2_capture_bg", 53.7, 59.0, (0, -4.0, 9.0), (0, -4.0, 9.0), (0, 0, 9.5), (0, 0, 9.5), 30)
    shot(gr, "G1_graph", 50.6, 53.7, (0.1, -5.0, 1.25), (0.0, -4.6, 1.2), (0, 0, 1.15), (0, 0, 1.15), 22)

# ================================================================= SHOW: real Vi3W models (auto-rig / animate / export beat) + final sketch → model
sh = L.new_set("SHOW")
with L.building(sh):
    studio(sh, H("#141026"), strength=0.6, key_w=550, at=(0, 0, 1.0))
    RING = flat("ring", "#7c5cff", 3.0)
    models = [("robot.glb", -1.5, 1.4), ("panda.glb", -0.5, 1.0), ("roblox.glb", 0.5, 1.3), ("brickguy.glb", 1.5, 1.3)]
    for k, (f, x, h) in enumerate(models):
        D.cyl(f"sped{k}", 0.4, 0.2, (x, 0, 0.1), m=BLACKP, verts=40)
        D.torus(f"sring{k}", 0.4, 0.015, (x, 0, 0.2), m=RING)
        m_ = real_model(os.path.join(HERE, "..", "..", "..", "Input", f), (x, 0, 0.2), h * 0.55, name=f"vm{k}")
        D.key(m_, "rotation_euler", T(59.0), (0, 0, math.radians(-40 + k * 25)))
        D.key(m_, "rotation_euler", T(62.0), (0, 0, math.radians(100 + k * 25)))
        D.ease_last(m_, "LINEAR")
        L0 = m_.location.copy()
        D.key(m_, "location", 1, L0 + Vector((0, 0, -3)), "CONSTANT")
        D.key(m_, "location", T(59.0 + k * 0.25), L0)
    shot(sh, "S1_models", 59.0, 62.0, (0.0, -4.6, 1.4), (0.0, -4.1, 1.3), (0, 0, 0.6), (0, 0, 0.65), 22)
    # final: the real robot sketch on an easel next to the real Vi3W robot
    img = bpy.data.images.load(os.path.join(HERE, "..", "..", "..", "Input", "robot0.jpeg"))
    pm = bpy.data.materials.new("sketch")
    pm.use_nodes = True
    tn = pm.node_tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    bs = pm.node_tree.nodes["Principled BSDF"]
    pm.node_tree.links.new(tn.outputs["Color"], bs.inputs["Base Color"])
    pm.node_tree.links.new(tn.outputs["Color"], bs.inputs["Emission Color"])
    bs.inputs["Emission Strength"].default_value = 0.35
    ar = img.size[0] / max(1, img.size[1])
    bpy.ops.mesh.primitive_plane_add(size=1)
    paper = bpy.context.active_object
    D.adopt(paper)
    paper.data.materials.append(pm)
    paper.scale = (1.1 * ar, 1.1, 1)
    paper.location = (19.45, 0, 1.35)
    paper.rotation_euler = (math.pi / 2, 0, math.radians(14))
    D.box("easel", (0.08, 0.08, 1.4), (19.45, 0.12, 0.7), L.pbr("easelw", "wood_table_001", scale=1.5))
    D.cyl("fped", 0.6, 0.3, (20.55, 0, 0.15), m=BLACKP, verts=48)
    D.torus("fring", 0.6, 0.02, (20.55, 0, 0.3), m=RING)
    fr = real_model(os.path.join(HERE, "..", "..", "..", "Input", "robot.glb"), (20.55, 0, 0.3), 1.35, name="final_robot")
    D.key(fr, "rotation_euler", T(62.0), (0, 0, math.radians(-50)))
    D.key(fr, "rotation_euler", T(END), (0, 0, math.radians(120)))
    D.ease_last(fr, "LINEAR")
    shot(sh, "F1_sketch", 62.0, 64.4, (19.4, -2.6, 1.5), (19.6, -2.2, 1.45), (19.4, 0, 1.3), (19.7, 0, 1.25), 30)
    shot(sh, "F2_one_sketch", 64.4, END, (20.0, -4.4, 1.5), (20.0, -4.0, 1.45), (20.0, 0, 1.0), (20.0, 0, 1.0), 26)

SHOTS.sort(key=lambda x: x[1])
json.dump(SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(SHOTS), [s.name for s in bpy.data.scenes])
