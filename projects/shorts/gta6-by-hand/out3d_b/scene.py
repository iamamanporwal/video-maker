"""blender -b -P scene.py -- <out.blend>: agent-B shots for "GTA 6 by hand" (characters, rigging, animation, bugs).

One scene per set; every shot is (shot_name, scene, f0, f1) in shots.json (frame 1 of a shot = t 0.0 of its mp4).

  NPCS     npcs        4.3 s  grey mannequin duplicates into a crowd, colour wave at 2.4
  RIGSET   rig         3.5 s  X-ray body + glowing bones, elbow folds like a lawn chair at 1.4, snaps clean at 2.6
  ANIM     animate     3.5 s  pose-to-pose with onion-skin ghosts, stepped → smooth, collapses face-down
  STREET   cycles 0-3.0 s / fallthrough / bugs (time-offset ranges in one sunset street set)
  CLEAN    cycles 3.0-5.3 s  grey viewport, frozen mid-air tumble pose being "cleaned" step by step
  ROOM     lonely      2.1 s  lone dev (Eric) at a monitor at night, push-in
"""
import math, os, random, re, sys, json
from mathutils import Matrix, Vector, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "reelforge", "blender"))
import bpy
import bmesh
import director as D
import look as L

out = sys.argv[sys.argv.index("--") + 1]
H = D.hex_lin
T = D.T
random.seed(7)
XBOT = os.path.join(ROOT, "projects/shorts/learn-blender/assets/Xbot.glb")
MICH = os.path.join(ROOT, "projects/shorts/3d-2d-hat/assets/Michelle.glb")
HINDI = os.path.join(ROOT, "projects/shorts/learn-blender-hindi/assets")
CAR = os.path.join(HERE, "assets", "car.glb")
SHOTS = []

base = D.reset(frames=520)
D.fast_eevee(base, samples=14, look="AgX - Punchy", motion_blur=False)


# ================================================================= helpers
def vl_of(o):
    return o.users_scene[0].view_layers[0]


def child_dir_bone(pb):
    kids = [c for c in pb.children if "Shoulder" not in c.name and "Eye" not in c.name]
    pref = {"Hips": "Spine", "Spine": "Spine1", "Spine1": "Spine2", "Spine2": "Neck"}
    nm = pb.name.split(":")[-1]
    for c in kids:
        if pref.get(nm) and c.name.endswith(pref[nm]):
            return c
    return kids[0] if len(kids) == 1 else None


def aim(arm, n, wdir, fr, twist=0.0):
    """Joint → child joint along world dir (glTF tails are guesses); optional twist about the new axis."""
    pb = D.bone(arm, n)
    vl_of(arm).update()
    inv = arm.matrix_world.to_3x3().inverted()
    c = child_dir_bone(pb)
    cur = ((c.head if c else pb.tail) - pb.head).normalized()
    tgt = (inv @ Vector(wdir)).normalized()
    m = pb.matrix.copy()
    r = cur.rotation_difference(tgt).to_matrix()
    if twist:
        r = Quaternion(tgt, math.radians(twist)).to_matrix() @ r
    nm = (r @ m.to_3x3()).to_4x4()
    nm.translation = m.translation
    pb.matrix = nm
    vl_of(arm).update()
    pb.keyframe_insert("rotation_quaternion", frame=fr)


ORDER = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "LeftShoulder", "RightShoulder", "LeftArm", "RightArm",
         "LeftForeArm", "RightForeArm", "LeftHand", "RightHand", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg",
         "LeftFoot", "RightFoot"]


def pose_action(arm, root, keys, name, twists=None):
    """keys: [(frame, {bone: local dir (char faces -Y)})] → new action on arm (bones reset before each key).
    Directions are rotated by the root's world rotation at that frame (key the root first)."""
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions.new(name)
    ad.use_nla = False
    ad.action = act
    sc = arm.users_scene[0]
    allb = sorted({b for _, d in keys for b in d}, key=lambda b: ORDER.index(b) if b in ORDER else 99)
    for fr, dirs in keys:
        sc.frame_set(fr)
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
        vl_of(arm).update()
        R = root.matrix_world.to_quaternion()
        for n in allb:
            if n in dirs:
                aim(arm, n, R @ Vector(dirs[n]), fr, ((twists or {}).get(fr, {})).get(n, 0.0))
            else:
                D.bone(arm, n).keyframe_insert("rotation_quaternion", frame=fr)
    return act


def to_strip(arm, act, f0, f1, blend=2):
    ad = arm.animation_data
    ad.action = None
    ad.use_nla = True
    tr = ad.nla_tracks.new()
    st = tr.strips.new(act.name, int(f0), act)
    if hasattr(st, "action_slot") and act.slots:
        st.action_slot = act.slots[0]
    st.action_frame_start, st.action_frame_end = f0, f1
    st.frame_start, st.frame_end = f0, f1
    st.blend_in = st.blend_out = blend
    st.extrapolation = "NOTHING"
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
    return st


def play(arm, act, f0, f1, speed=1.0, blend=3):
    ad = arm.animation_data or arm.animation_data_create()
    tr = ad.nla_tracks.new()
    st = tr.strips.new(f"{act.name}_{f0}", int(f0), act)
    if hasattr(st, "action_slot") and act.slots:
        st.action_slot = act.slots[0]
    a0, a1 = act.frame_range
    st.scale = 1.0 / speed
    st.repeat = max(0.05, (f1 - f0) / ((a1 - a0) / speed))
    st.blend_in = st.blend_out = blend
    st.extrapolation = "NOTHING"
    return st


def interp_before(o, frame, kind="CONSTANT"):
    ad = o.animation_data
    if ad and ad.action:
        for fc in D._fcurves(ad.action):
            for k in fc.keyframe_points:
                if k.co.x < frame - 0.5:
                    k.interpolation = kind


def vis(o, ranges):
    """Visible only in the given inclusive frame ranges (recurses into children)."""
    for x in [o] + list(o.children_recursive):
        x.hide_render = True
        x.keyframe_insert("hide_render", frame=1)
        for a, b in ranges:
            x.hide_render = False
            x.keyframe_insert("hide_render", frame=a)
            x.hide_render = True
            x.keyframe_insert("hide_render", frame=b + 1)
        for fc in D._fcurves(x.animation_data.action):
            if fc.data_path == "hide_render":
                for k in fc.keyframe_points:
                    k.interpolation = "CONSTANT"


def bake_mesh(sc, meshes, name, decimate=None, mat_split=True):
    """Evaluated (posed) meshes → one static world-space mesh; mesh i keeps material slot i."""
    dg = sc.view_layers[0].depsgraph
    dg.update()
    bm = bmesh.new()
    for i, m in enumerate(meshes):
        me = bpy.data.meshes.new_from_object(m.evaluated_get(dg))
        me.transform(m.matrix_world)
        for p in me.polygons:
            p.material_index = i if mat_split else 0
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    out_me = bpy.data.meshes.new(name)
    bm.to_mesh(out_me)
    for p in out_me.polygons:
        p.use_smooth = True
    if decimate:
        tmp = bpy.data.objects.new("tmp", out_me)
        sc.collection.objects.link(tmp)
        md = tmp.modifiers.new("d", "DECIMATE")
        md.ratio = decimate
        dg.update()
        dec = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
        bpy.data.objects.remove(tmp)
        bpy.data.meshes.remove(out_me)
        out_me = dec
        out_me.name = name
    return out_me


def objcolor_mat(name, rough=0.45, mult=1.0, add=0.0, coat=0.25):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    info = nt.nodes.new("ShaderNodeObjectInfo")
    col = info.outputs["Color"]
    if mult != 1.0 or add:
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type, mx.blend_type = "RGBA", "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        nt.links.new(col, mx.inputs[6])
        mx.inputs[7].default_value = (mult, mult, mult, 1)
        col = mx.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    return m


def grid_mat(name, bg="#3d3d3d", line="#5a5a5a", fade=28.0, axes=True):
    """Blender-viewport floor: 1 m grid, red X / green Y axis lines, fading out with distance."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, Lk = nt.nodes, nt.links.new
    b = N["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.8
    tc = N.new("ShaderNodeTexCoord")
    fr = N.new("ShaderNodeVectorMath"); fr.operation = "FRACTION"
    Lk(tc.outputs["Object"], fr.inputs[0])
    sub = N.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    Lk(fr.outputs[0], sub.inputs[0])
    ab = N.new("ShaderNodeVectorMath"); ab.operation = "ABSOLUTE"
    Lk(sub.outputs[0], ab.inputs[0])
    sp = N.new("ShaderNodeSeparateXYZ"); Lk(ab.outputs[0], sp.inputs[0])
    mxm = N.new("ShaderNodeMath"); mxm.operation = "MAXIMUM"
    Lk(sp.outputs[0], mxm.inputs[0]); Lk(sp.outputs[1], mxm.inputs[1])
    gt = N.new("ShaderNodeMath"); gt.operation = "SMOOTH_MAX" if False else "GREATER_THAN"; gt.inputs[1].default_value = 0.478
    Lk(mxm.outputs[0], gt.inputs[0])
    # distance fade
    ln = N.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; Lk(tc.outputs["Object"], ln.inputs[0])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = fade * 0.4
    mr.inputs["From Max"].default_value = fade; mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0
    Lk(ln.outputs["Value"], mr.inputs["Value"])
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    Lk(gt.outputs[0], mul.inputs[0]); Lk(mr.outputs[0], mul.inputs[1])
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*H(bg), 1); mix.inputs[7].default_value = (*H(line), 1)
    Lk(mul.outputs[0], mix.inputs[0])
    col = mix.outputs[2]
    if axes:
        sp2 = N.new("ShaderNodeSeparateXYZ"); Lk(tc.outputs["Object"], sp2.inputs[0])
        for i, c in ((1, "#c43c3c"), (0, "#6aa832")):           # |y|<w → red X axis; |x|<w → green Y axis
            a = N.new("ShaderNodeMath"); a.operation = "ABSOLUTE"; Lk(sp2.outputs[i], a.inputs[0])
            lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.035
            Lk(a.outputs[0], lt.inputs[0])
            m2 = N.new("ShaderNodeMix"); m2.data_type = "RGBA"
            Lk(lt.outputs[0], m2.inputs[0]); Lk(col, m2.inputs[6]); m2.inputs[7].default_value = (*H(c), 1)
            col = m2.outputs[2]
    Lk(col, b.inputs["Base Color"])
    return m


def viewport_set(sc, size=80, bg="#5e6066"):
    L.hdri_world(sc, "studio_small_09", 0.7, rot_deg=30, backdrop=H(bg), backdrop_strength=1.0)
    fl = D.box(sc.name + "_grid", (size, size, 0.01), (0, 0, -0.005), grid_mat(sc.name + "_gridm"))
    D.sun(sc.name + "_sun", 2.2, (0.35, 0.6, -1), rgb=H("#fff4e6"), angle=6)
    return fl


BONE_M = L.plastic("bone_or", H("#ff8a1f"), rough=0.3, coat=0.2, emit=H("#ff7a10"), emit_strength=2.2)
JOINT_M = L.plastic("bone_teal", H("#2ee6d6"), rough=0.3, coat=0.2, emit=H("#20d8c8"), emit_strength=2.0)
VIZ_BONES = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
             "RightShoulder", "RightArm", "RightForeArm", "RightHand", "LeftUpLeg", "LeftLeg", "LeftFoot",
             "RightUpLeg", "RightLeg", "RightFoot"]


def octa(name, L_, w):
    me = bpy.data.meshes.new(name)
    vs = [(0, 0, 0), (w, L_ * 0.18, 0), (0, L_ * 0.18, w), (-w, L_ * 0.18, 0), (0, L_ * 0.18, -w), (0, L_, 0)]
    fs = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
    me.from_pydata(vs, [], fs)
    return me


def bone_viz(arm, scale=1.0):
    """Blender-style octahedral bones + joint balls, bone-parented, glowing (call while the rig is at rest)."""
    sc = arm.users_scene[0]
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
    vl_of(arm).update()
    objs = []
    for n in VIZ_BONES:
        try:
            pb = D.bone(arm, n)
        except KeyError:
            continue
        c = child_dir_bone(pb)
        h = arm.matrix_world @ pb.head
        t = arm.matrix_world @ (c.head if c else pb.tail)
        if n in ("LeftHand", "RightHand"):
            t = h + (t - h).normalized() * 0.09 * scale
        if n in ("LeftFoot", "RightFoot"):
            t = h + (t - h) * 1.0
        L_ = (t - h).length
        if L_ < 1e-4:
            continue
        q = Vector((0, 1, 0)).rotation_difference((t - h).normalized())
        o = D.link(bpy.data.objects.new("bone_" + n, octa("bone_" + n, L_, max(0.016 * scale, L_ * 0.1))))
        o.data.materials.append(BONE_M)
        o.parent = arm
        o.parent_type = "BONE"
        o.parent_bone = pb.name
        vl_of(arm).update()
        o.matrix_world = Matrix.LocRotScale(h, q, None)
        j = D.sphere("joint_" + n, max(0.014 * scale, L_ * 0.07), (0, 0, 0), JOINT_M, seg=16, rings=8)
        j.parent = arm
        j.parent_type = "BONE"
        j.parent_bone = pb.name
        vl_of(arm).update()
        j.matrix_world = Matrix.Translation(h)
        for x in (o, j):
            x.visible_shadow = False
        objs += [o, j]
    return objs


def xray_mat(name, img=None, tint="#7fe9ff"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, Lk = nt.nodes, nt.links.new
    b = N["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.4
    if img:
        tx = N.new("ShaderNodeTexImage"); tx.image = img
        Lk(tx.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*H("#8a9099"), 1)
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    fa = lw.outputs["Facing"]
    al = N.new("ShaderNodeMapRange"); al.inputs["To Min"].default_value = 0.22; al.inputs["To Max"].default_value = 0.85
    Lk(fa, al.inputs["Value"])
    Lk(al.outputs[0], b.inputs["Alpha"])
    b.inputs["Emission Color"].default_value = (*H(tint), 1)
    em = N.new("ShaderNodeMath"); em.operation = "POWER"; em.inputs[1].default_value = 2.5
    Lk(fa, em.inputs[0])
    Lk(em.outputs[0], b.inputs["Emission Strength"])
    m.surface_render_method = "BLENDED"
    m.use_transparency_overlap = False
    return m


def first_image(mats):
    for m in mats:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    return n.image


def glb(path, keep=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        D.adopt(o)
    vl_of(new[0]).update()
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
    vl_of(objs[0]).update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def shot(name, sc, f0, f1, loc0, loc1, at0, at1, lens0=30, lens1=None, shake=0.004, dof=None, keyf=None):
    c, l = D.camera(name, lens0, dof=dof)
    if keyf:
        keyf(c, l)
    else:
        D.move(c, l, f0, f1, loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    D.cut(sc, f0, c)
    return c, l


def mixamo(path, name, loc=(0, 0, 0), yaw=0.0):
    r, arm, body = D.import_char(path, name)
    r.location, r.rotation_euler = loc, (0, 0, yaw)
    vl_of(r).update()
    return r, arm, body


STAND = {"Spine": (0, 0.02, 1), "Neck": (0, -0.05, 1), "Head": (0, -0.08, 1),
         "LeftArm": (0.22, 0.02, -1), "RightArm": (-0.22, 0.02, -1), "LeftForeArm": (0.08, -0.12, -1),
         "RightForeArm": (-0.08, -0.12, -1), "LeftUpLeg": (0.04, 0, -1), "RightUpLeg": (-0.04, 0, -1),
         "LeftLeg": (0, 0.03, -1), "RightLeg": (0, 0.03, -1)}

# ================================================================= NPCS: one mannequin → a crowd → colour wave
npc = L.new_set("NPCS", main=True)
viewport_set(npc)
L.post(npc, bloom=0.2, vignette=0.26)
SURF = objcolor_mat("npc_surf", rough=0.42)
JNT = objcolor_mat("npc_jnt", rough=0.5, mult=0.32)
hero, harm, hbody = mixamo(XBOT, "npc", (0, 0, 0))
XCLIPS = D.CLIPS[harm.name]
for m in hbody:
    m.data.materials.clear()
    m.data.materials.append(JNT if "Joint" in m.name else SURF)
hbody.sort(key=lambda m: "Joint" in m.name)        # surface first → slot 0
GREY = (0.42, 0.42, 0.43, 1)
PAL = ["#ff3e9a", "#ff9a3c", "#20c7c0", "#ffd23c", "#3d7bff", "#9b5cff", "#3fcf5a", "#ff4d4d", "#ff6fd8", "#00b4ff",
       "#f2f2f2", "#ff7a00"]
# crowd pose meshes: bake the hero at several clip frames
poses = []
for clip, fr in (("idle", 5), ("idle", 30), ("agree", 12), ("headShake", 25), ("sad_pose", 1), ("sneak_pose", 1),
                 ("walk", 4), ("agree", 30)):
    st = play(harm, XCLIPS[clip], 1, 400, blend=0)
    st.extrapolation = "HOLD"
    npc.frame_set(int(fr) + 1)
    poses.append(bake_mesh(npc, hbody, f"crowd_{clip}_{fr}", decimate=0.09))
    harm.animation_data.nla_tracks.remove(harm.animation_data.nla_tracks[-1])
for me in poses:
    me.materials.append(SURF)
    me.materials.append(JNT)
play(harm, XCLIPS["idle"], 1, T(4.4))
for m in hbody:
    m.color = GREY
    m.keyframe_insert("color", frame=1)
    m.keyframe_insert("color", frame=T(2.4))
    m.color = (*H("#ff3e9a"), 1)
    m.keyframe_insert("color", frame=T(2.5))
crowd = []
for j in range(-8, 17):
    for i in range(-9, 10):
        if i == 0 and j == 0:
            continue
        x, y = i * 1.15 + random.uniform(-0.18, 0.18), j * 1.35 + random.uniform(-0.2, 0.2)
        o = D.link(bpy.data.objects.new(f"npc_{i}_{j}", random.choice(poses)))
        o.location = (x, y, 0)
        o.rotation_euler = (0, 0, math.radians(random.uniform(-30, 30)))
        s = random.uniform(0.9, 1.08)
        t0 = 0.6 + abs(i) * 0.035 if j == 0 else 1.0 + abs(j) * 0.055 + abs(i) * 0.012
        o.scale = (0, 0, 0)
        o.keyframe_insert("scale", frame=1)
        D.overshoot(o, "scale", T(t0), T(t0 + 0.2), (0, 0, 0), (s, s, s * random.uniform(0.95, 1.05)), 1.18)
        tw = 2.4 + math.hypot(x, y) / 14.0 * 0.75
        o.color = GREY
        o.keyframe_insert("color", frame=1)
        o.keyframe_insert("color", frame=T(tw))
        o.color = (*H(random.choice(PAL)), 1)
        o.keyframe_insert("color", frame=T(tw) + 3)
        crowd.append(o)
D.area_light("npc_key", 900, (-6, -10, 9), (0, 0, 1), size=8)
D.area_light("npc_rim", 500, (6, 8, 6), (0, 0, 1), size=6, rgb=H("#ffe2c4"))


def npc_cam(c, l):
    for f, p, a, lens in ((1, (0.6, -3.4, 1.35), (0, 0, 1.0), 35), (T(0.6), (0.7, -4.0, 1.5), (0, 0, 1.0), 34),
                          (T(2.2), (0.0, -15, 19.0), (0, 4.5, 0), 30), (T(4.4), (0.0, -16.5, 21.0), (0, 5, 0), 30)):
        D.key(c, "location", f, Vector(p))
        D.key(l, "location", f, Vector(a))
        c.data.lens = lens
        c.data.keyframe_insert("lens", frame=f)
    D.ease_all(c)
    D.ease_all(l)


shot("cam_npcs", npc, 1, T(4.3), None, None, None, None, 35, shake=0.004, keyf=npc_cam)
SHOTS.append(("npcs", "NPCS", 1, T(4.3) - 1))

# ================================================================= RIGSET: X-ray body, glowing bones, lawn-chair elbow
rig = L.new_set("RIGSET")
with L.building(rig):
    viewport_set(rig, bg="#4a4e57")
    L.post(rig, bloom=0.55, bloom_threshold=0.8, vignette=0.3)
    mr, marm, mbody = mixamo(MICH, "mich", (0, 0, 0))
    img = first_image([s for m in mbody for s in m.data.materials])
    xm = xray_mat("xray", img)
    for m in mbody:
        m.data.materials.clear()
        m.data.materials.append(xm)
        m.visible_shadow = False
    bone_viz(marm)
    D.area_light("rig_key", 300, (-2, -3, 3), (0, 0, 1.3), size=3)
    D.area_light("rig_rim", 260, (2.5, 2, 2.5), (0, 0, 1.4), size=2, rgb=H("#ff6ad5"))
    FLEX = STAND | {"LeftArm": (1, -0.25, 0.08), "LeftForeArm": (0.15, -0.35, 1), "Head": (0.35, -0.5, 1)}
    BROKE = FLEX | {"LeftArm": (1, -0.15, 0.1), "LeftForeArm": (-1, -0.3, 0.25), "Head": (0.7, -0.4, 1),
                    "Spine": (-0.1, 0.05, 1)}
    BROKE2 = BROKE | {"LeftForeArm": (-1, -0.45, 0.1)}
    keys = [(1, STAND), (T(0.15), STAND), (T(0.7), FLEX), (T(1.37), FLEX), (T(1.47), BROKE), (T(1.6), BROKE2),
            (T(1.8), BROKE), (T(2.0), BROKE2), (T(2.2), BROKE), (T(2.4), BROKE2), (T(2.56), BROKE),
            (T(2.66), FLEX | {"LeftForeArm": (0.05, -0.3, 1)}), (T(2.8), FLEX), (T(3.6), FLEX)]
    tw = {f: {"LeftForeArm": 175.0, "LeftArm": -60.0} for f, d in keys if d in (BROKE, BROKE2)}
    act = pose_action(marm, mr, keys, "rig_pose", twists=tw)
    fa = D.bone(marm, "LeftForeArm")
    for f, d in keys:
        fa.scale = (1.7, 0.75, 0.45) if d in (BROKE, BROKE2) else (1, 1, 1)
        fa.keyframe_insert("scale", frame=f)
    to_strip(marm, act, 1, T(3.6), blend=0)
    shot("cam_rig", rig, 1, T(3.5), (0.3, -2.3, 1.45), (0.28, -1.9, 1.45), (0.12, 0, 1.3), (0.16, 0, 1.33), 38, 40,
         shake=0.003)
SHOTS.append(("rig", "RIGSET", 1, T(3.5) - 1))

# ================================================================= ANIM: pose-to-pose + onion skin → collapse
anim = L.new_set("ANIM")
with L.building(anim):
    viewport_set(anim, bg="#5a5e66")
    L.post(anim, bloom=0.3, vignette=0.28)
    ar, aarm, abody = mixamo(XBOT, "anim", (0, 0, 0))
    clay = L.plastic("clay", H("#a7a9ad"), rough=0.55, coat=0.1)
    clay_j = L.plastic("clay_j", H("#55585e"), rough=0.5, coat=0.1)
    for m in abody:
        m.data.materials.clear()
        m.data.materials.append(clay_j if "Joint" in m.name else clay)
    abody.sort(key=lambda m: "Joint" in m.name)
    CROUCH = STAND | {"Spine": (0, -0.45, 1), "LeftUpLeg": (0.15, -1, -0.55), "RightUpLeg": (-0.15, -1, -0.55),
                      "LeftLeg": (0, 0.55, -1), "RightLeg": (0, 0.55, -1), "LeftArm": (0.3, 0.7, -0.6),
                      "RightArm": (-0.3, 0.7, -0.6), "LeftForeArm": (0.2, 0.8, -0.5), "RightForeArm": (-0.2, 0.8, -0.5)}
    JUMP = STAND | {"Spine": (0, 0.1, 1), "LeftArm": (0.6, -0.15, 1), "RightArm": (-0.6, -0.15, 1),
                    "LeftForeArm": (0.5, -0.1, 1), "RightForeArm": (-0.5, -0.1, 1), "LeftUpLeg": (0.2, -0.6, -1),
                    "RightUpLeg": (-0.2, -0.2, -1), "LeftLeg": (0, 0.7, -1), "RightLeg": (0, 0.4, -1), "Head": (0, 0.2, 1)}
    LAND = CROUCH | {"LeftArm": (0.8, -0.5, 0.1), "RightArm": (-0.8, -0.5, 0.1), "LeftForeArm": (0.7, -0.6, 0.2),
                     "RightForeArm": (-0.7, -0.6, 0.2)}
    TADA = STAND | {"LeftArm": (1, -0.25, 0.45), "RightArm": (-1, -0.25, 0.45), "LeftForeArm": (1, -0.2, 0.7),
                    "RightForeArm": (-1, -0.2, 0.7), "Head": (0, -0.1, 1), "RightUpLeg": (-0.25, 0, -1)}
    TIRED = STAND | {"Spine": (0, -0.9, 0.5), "Spine1": (0, -1, 0.2), "Neck": (0, -1, -0.2), "Head": (0, -0.8, -0.8),
                     "LeftUpLeg": (0.1, -0.5, -1), "RightUpLeg": (-0.1, -0.5, -1), "LeftLeg": (0, 0.35, -1),
                     "RightLeg": (0, 0.35, -1), "LeftArm": (0.25, -0.4, -1), "RightArm": (-0.25, -0.4, -1),
                     "LeftForeArm": (0.05, -0.2, -1), "RightForeArm": (-0.05, -0.2, -1)}
    FLAT = STAND | {"LeftArm": (0.35, 0.1, -1), "RightArm": (-0.35, 0.1, -1), "LeftForeArm": (0.25, 0.2, -1),
                    "RightForeArm": (-0.25, 0.2, -1), "Head": (0.5, 0, 1), "LeftUpLeg": (0.1, 0, -1),
                    "RightUpLeg": (-0.1, 0, -1)}
    FLAT2 = FLAT | {"RightLeg": (0, 0.7, -0.7)}
    seq = [(1, STAND, 0, 0), (T(0.35), CROUCH, -0.33, 0), (T(0.75), JUMP, 0.55, 0), (T(1.15), LAND, -0.33, 0),
           (T(1.55), TADA, 0, 0), (T(2.15), TIRED, -0.12, 0), (T(2.75), FLAT, 0.13, 84), (T(3.05), FLAT2, 0.13, 84),
           (T(3.2), FLAT, 0.13, 84), (T(3.6), FLAT, 0.13, 84)]
    for f, _, z, rx in seq:
        D.key(ar, "location", f, Vector((0, 0, z if rx == 0 else 0.13)))
        D.key(ar, "rotation_euler", f, (math.radians(rx), 0, 0))
    act = pose_action(aarm, ar, [(f, p) for f, p, _, _ in seq], "anim_pose")
    STEP_END = T(1.55)
    interp_before(ar, STEP_END)
    for fc in D._fcurves(act):
        for k in fc.keyframe_points:
            if k.co.x < STEP_END - 0.5:
                k.interpolation = "CONSTANT"
    to_strip(aarm, act, 1, T(3.6), blend=0)
    # onion skin: bake each pose once the body leaves it
    ghost_cols = ["#2ee6d6", "#ff8a1f", "#2ee6d6", "#ff8a1f", "#ff3e9a"]
    for gi, (f, p, z, rx) in enumerate(seq[1:6]):
        anim.frame_set(f)
        me = bake_mesh(anim, abody, f"ghost{gi}", decimate=0.25, mat_split=False)
        gm = bpy.data.materials.new(f"ghost_m{gi}")
        gm.use_nodes = True
        bs = gm.node_tree.nodes["Principled BSDF"]
        bs.inputs["Base Color"].default_value = (*H(ghost_cols[gi]), 1)
        bs.inputs["Emission Color"].default_value = (*H(ghost_cols[gi]), 1)
        bs.inputs["Emission Strength"].default_value = 0.6
        bs.inputs["Alpha"].default_value = 0.3
        gm.surface_render_method = "BLENDED"
        me.materials.append(gm)
        g = D.link(bpy.data.objects.new(f"ghost{gi}", me))
        g.visible_shadow = False
        nxt = seq[gi + 2][0]
        vis(g, [(nxt, min(nxt + 26, T(3.6)))])
    anim.frame_set(1)
    shot("cam_anim", anim, 1, T(3.5), (1.9, -3.6, 1.4), (1.5, -3.0, 1.15), (0, -0.4, 0.85), (0, -0.7, 0.6), 30, 30,
         shake=0.003)
SHOTS.append(("animate", "ANIM", 1, T(3.5) - 1))

# ================================================================= STREET: Vice-City sunset
street = L.new_set("STREET")
C0, F0, B0 = 0, 200, 400                                   # frame offsets: cycles / fallthrough / bugs


def sky_world(sc):
    w = bpy.data.worlds.new(sc.name + "_sky")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sp.inputs[0])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    els = cr.color_ramp.elements
    stops = [(0.0, "#2a3550"), (0.40, "#4a5a7c"), (0.497, "#7d8aa6"), (0.5, "#ffb15a"), (0.53, "#ff7a45"),
             (0.6, "#ff3e9a"), (0.72, "#8a3fb0"), (1.0, "#231a5c")]
    els[0].position, els[0].color = stops[0][0], (*H(stops[0][1]), 1)
    els[1].position, els[1].color = stops[-1][0], (*H(stops[-1][1]), 1)
    for p, c in stops[1:-1]:
        e = els.new(p)
        e.color = (*H(c), 1)
    mr = nt.nodes.new("ShaderNodeMapRange")                 # z in [-1,1] → [0,1]
    mr.inputs["From Min"].default_value = -1.0
    nt.links.new(sp.outputs[2], mr.inputs["Value"])
    nt.links.new(mr.outputs[0], cr.inputs[0])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.3
    nt.links.new(cr.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], o.inputs[0])
    sc.world = w


def proc_mat(name, c0, c1, scale=6.0, rough=0.75, bump=0.25):
    """Procedural noise surface on object coords (no image tiling streaks at grazing angles)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, Lk = nt.nodes, nt.links.new
    b = N["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 6
    Lk(tc.outputs["Object"], nz.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position, cr.color_ramp.elements[0].color = 0.35, (*H(c0), 1)
    cr.color_ramp.elements[1].position, cr.color_ramp.elements[1].color = 0.7, (*H(c1), 1)
    Lk(nz.outputs["Fac"], cr.inputs[0])
    Lk(cr.outputs[0], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
    Lk(nz.outputs["Fac"], bp.inputs["Height"]); Lk(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def underside(m, col="#56627a"):
    """Backfaces render as flat untextured grey-blue: the 'under the map' look."""
    nt = m.node_tree
    out_n = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    surf = out_n.inputs["Surface"].links[0].from_socket
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    flat = nt.nodes.new("ShaderNodeEmission")
    flat.inputs["Color"].default_value = (*H(col), 1)
    flat.inputs["Strength"].default_value = 0.9
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(surf, mix.inputs[1])
    nt.links.new(flat.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out_n.inputs["Surface"])
    m.use_backface_culling = False
    return m


PALM_M = []


def palm(name, loc, h=7.0, seed=0, lean=0.25):
    rnd = random.Random(seed)
    g = D.empty(name, loc)
    bark, leaf = PALM_M[0], PALM_M[1 + seed % 2]
    n = 9
    pts = []
    for k in range(n + 1):
        t = k / n
        pts.append(Vector((lean * h * t * t, 0, h * t)))
    for k in range(n):
        a, b = pts[k], pts[k + 1]
        r = 0.2 - 0.08 * k / n
        seg = D.cyl(f"{name}_t{k}", r, (b - a).length * 1.06, (a + b) / 2, m=bark, verts=12)
        seg.rotation_euler = Vector((0, 0, 1)).rotation_difference(b - a).to_euler()
        seg.parent = g
        seg.location = (a + b) / 2
    top = pts[-1]
    for k in range(10):
        yaw = k / 10 * math.tau + rnd.uniform(-0.2, 0.2)
        fr = D.sphere(f"{name}_f{k}", 1.0, (0, 0, 0), leaf, seg=12, rings=6)
        fr.scale = (1.55, 0.3, 0.05)
        fr.parent = g
        fr.location = top + Vector((math.cos(yaw) * 1.3, math.sin(yaw) * 1.3, -0.35))
        fr.rotation_euler = (Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(math.radians(rnd.uniform(16, 34)), 4, "Y")).to_euler()
    D.sphere(f"{name}_nut", 0.28, top + Vector((0, 0, -0.1)), L.plastic(name + "_nut", H("#5a3a1e"), rough=0.6),
             seg=12, rings=8).parent = g
    return g



with L.building(street):
    sky_world(street)
    PALM_M += [L.pbr("bark", "wood_table_001", scale=2.0, tint=H("#8a5a3a"), tint_amount=0.6),
               L.plastic("leaf1", H("#1f9e4a"), rough=0.55, coat=0.15), L.plastic("leaf2", H("#2fae55"), rough=0.55, coat=0.15)]
    sun_l = D.sun("st_sun", 3.6, (-0.45, 0.85, -0.32), rgb=H("#ffb27a"), angle=3)
    D.sun("st_fill", 1.2, (0.9, 0.2, -0.4), rgb=H("#3fd0e0"), angle=10)
    D.sun("st_back", 1.5, (0.1, -1, -0.15), rgb=H("#ff4fa0"), angle=5)
    L.post(street, bloom=0.4, bloom_threshold=0.85, vignette=0.26, saturation=1.12)
    road_m = underside(proc_mat("asphalt", "#5a5266", "#7c7388", scale=9.0, rough=0.6))
    walk_m = proc_mat("pave", "#d9b3a6", "#f2d2c4", scale=4.0, rough=0.8)
    gnd_m = underside(proc_mat("gnd", "#c9927e", "#e8b49c", scale=2.0, rough=0.85))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 60, 0))
    road = D.adopt(bpy.context.active_object)
    road.name = "road"
    road.scale = (8, 320, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    D.give(road, road_m)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 60, -0.012))
    g = D.adopt(bpy.context.active_object)
    g.scale = (300, 320, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    D.give(g, gnd_m)
    yel = L.plastic("lane_y", H("#ffcc33"), rough=0.4, coat=0.1)
    wht = L.plastic("lane_w", H("#f4f1ea"), rough=0.4, coat=0.1)
    for k in range(-20, 60):
        D.box("dash", (0.14, 2.2, 0.01), (0, k * 5.0, 0.004), yel)
    for sx in (-1, 1):
        D.box("edge", (0.12, 320, 0.01), (sx * 3.75, 60, 0.004), wht)
        D.box("curb", (0.25, 320, 0.17), (sx * 4.1, 60, 0.085), L.plastic("curb", H("#d9d2c8"), rough=0.6, coat=0))
        D.box("walk", (3.2, 320, 0.15), (sx * 5.8, 60, 0.075), walk_m)
    BCOL = ["#ff8fb1", "#3ec1c9", "#ffb37a", "#b48cff", "#f4efe6", "#ff6f91", "#5fd3b5", "#ffd27a"]
    BMATS = [L.pbr(f"bw{i}", "plastered_wall", scale=0.5, tint=H(c), tint_amount=0.85, normal=0.4) for i, c in enumerate(BCOL)]
    glass = L.plastic("glass", H("#1d2b44"), rough=0.15, coat=0.8)
    neon_p = L.plastic("neon_p", H("#ff3e9a"), rough=0.3, emit=H("#ff3e9a"), emit_strength=4.0)
    neon_c = L.plastic("neon_c", H("#2ee6d6"), rough=0.3, emit=H("#2ee6d6"), emit_strength=4.0)
    rnd = random.Random(11)
    for sx in (-1, 1):
        y = -30.0
        while y < 160:
            w = rnd.uniform(7, 13)
            hgt = rnd.choice([6, 8, 9, 12, 15, 20])
            x = sx * (7.4 + 4.5)
            D.box("bld", (9, w - 0.6, hgt), (x, y + w / 2, hgt / 2), rnd.choice(BMATS))
            fx = sx * 7.4 - sx * 0.02
            for r in range(int(hgt // 3)):
                D.box("win", (0.08, w - 2.0, 1.2), (fx, y + w / 2, 2.2 + r * 3.0), glass)
            D.box("neon", (0.06, w - 1.2, 0.12), (fx - sx * 0.05, y + w / 2, 1.0 if r else 3.4),
                  neon_p if rnd.random() < 0.5 else neon_c)
            y += w
    PALMS = []
    for k, yy in enumerate(range(-12, 150, 11)):
        for sx in (-1, 1):
            p = palm(f"palm{k}{sx}", (sx * 4.9, yy + (5 if sx > 0 else 0), 0.15), h=rnd.uniform(6.5, 8.5), seed=k * 2 + sx,
                     lean=-sx * 0.12)
            PALMS.append(p)

    # ---------------- car (Sketchfab "Fairheaven LT '80", CC-BY DanielZhabotinsky)
    try:
        assert not os.environ.get("NOCAR")
        car_ms = glb(CAR)
    except Exception as e:
        print("CAR FALLBACK", e)
        paint = L.plastic("paint", H("#ff3e9a"), rough=0.25, coat=0.8)
        car_ms = [D.box("cb", (1.9, 4.6, 0.7), (0, 0, 0.6), paint, bevel=0.08),
                  D.box("cc", (1.6, 2.2, 0.55), (0, -0.2, 1.2), L.plastic("cglass", H("#1d2b44"), rough=0.1, coat=1), bevel=0.08)]
        for x in (-0.9, 0.9):
            for y in (-1.45, 1.45):
                car_ms.append(D.cyl("wh", 0.36, 0.3, (x, y, 0.36), (0, math.pi / 2, 0), L.plastic("tyre", H("#111111"), rough=0.8)))
        for o in car_ms:
            o.data.transform(o.matrix_world)
            o.matrix_world = Matrix()
    lo, hi = bounds(car_ms)
    ext = hi - lo
    rotq = Matrix.Rotation(math.pi / 2, 4, "Z") if ext.x > ext.y else Matrix()
    for o in car_ms:
        o.data.transform(rotq)
    lo, hi = bounds(car_ms)
    k_ = 4.8 / (hi.y - lo.y)
    off = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for o in car_ms:
        o.data.transform(Matrix.Scale(k_, 4) @ Matrix.Translation(-off))
        for p in o.data.polygons:
            p.use_smooth = p.use_smooth
        for c in list(o.users_collection):
            c.objects.unlink(o)
    CAR_FLIP = math.pi if os.environ.get("CAR_FLIP") else 0.0

    def car(name, loc, yaw=0.0):
        g = D.empty(name, loc)
        g.rotation_euler = (0, 0, yaw)
        inner = D.empty(name + "_in", (0, 0, 0))
        inner.parent = g
        inner.rotation_euler = (0, 0, CAR_FLIP)
        for t in car_ms:
            o = t.copy()
            D.link(o)
            o.parent = inner
        return g

    # ---------------- hero (Michelle) with Xbot's walk/run clips
    he, hearm, hebody = mixamo(XBOT, "hero", (1.2, -6, 0.15), 0.0)
    WALK, RUN = D.CLIPS[hearm.name]["walk"], D.CLIPS[hearm.name]["run"]
    HERO_S = L.plastic("hero_s", H("#ff9a3c"), rough=0.35, coat=0.5)
    HERO_J = L.plastic("hero_j", H("#2a1f4a"), rough=0.4, coat=0.3)
    for m in hebody:
        m.data.materials.clear()
        m.data.materials.append(HERO_J if "Joint" in m.name else HERO_S)

street_cams = []
with L.building(street):
    # ===== CYCLES 0-3.0 s (frames 1..90): walk | run | trip | car hit
    # hero travels +Y (faces +Y: yaw pi)
    he.rotation_euler = (0, 0, math.pi)
    play(hearm, WALK, 1, T(0.62), speed=1.0, blend=0)
    play(hearm, RUN, T(0.6), T(1.32), speed=1.0, blend=1)
    D.key(he, "location", 1, Vector((1.6, -6.0, 0.0)))
    D.key(he, "location", T(0.6), Vector((1.6, -5.1, 0.0)))
    D.ease_last(he, "LINEAR")
    D.key(he, "location", T(1.1), Vector((1.6, -3.2, 0.0)))     # run cut restarts nearer the camera
    D.key(he, "location", T(1.3), Vector((1.6, -2.4, 0.0)))
    D.key(he, "rotation_euler", T(1.3), (0, 0, math.pi))
    D.key(he, "location", T(1.42), Vector((1.6, -1.6, 0.0)))
    D.key(he, "rotation_euler", T(1.42), (math.radians(45), 0, math.pi))
    D.key(he, "location", T(1.56), Vector((1.6, -0.9, 0.0)))
    D.key(he, "rotation_euler", T(1.56), (math.radians(88), 0, math.pi))
    D.key(he, "location", T(1.6), Vector((1.6, -0.9, 0.0)))
    # hit cut: standing dazed on the road at y=8, car from +X, bonk at 2.0, tumble → frozen at 3.0
    D.key(he, "location", T(1.6) + 1, Vector((0.6, 8.0, 0.0)))
    D.key(he, "rotation_euler", T(1.6) + 1, (0, 0, math.radians(120)))
    D.key(he, "location", T(1.97), Vector((0.6, 8.0, 0.0)))
    D.key(he, "rotation_euler", T(1.97), (0, 0, math.radians(120)))
    D.key(he, "location", T(2.25), Vector((-1.6, 8.6, 2.6)))
    D.key(he, "rotation_euler", T(2.25), (math.radians(160), math.radians(40), math.radians(200)))
    D.key(he, "location", T(2.6), Vector((-3.2, 9.2, 3.0)))
    D.key(he, "rotation_euler", T(2.6), (math.radians(300), math.radians(70), math.radians(260)))
    D.key(he, "location", T(3.0), Vector((-4.0, 9.5, 2.4)))
    D.key(he, "rotation_euler", T(3.0), (math.radians(390), math.radians(95), math.radians(300)))
    for fc in D._fcurves(he.animation_data.action):
        for kp in fc.keyframe_points:
            if abs(kp.co.x - T(1.6)) < 0.1:
                kp.interpolation = "CONSTANT"
    TRIP = STAND | {"Spine": (0, -0.4, 1), "LeftArm": (0.5, -0.8, 0.5), "RightArm": (-0.5, -0.9, 0.3),
                    "LeftForeArm": (0.3, -1, 0.6), "RightForeArm": (-0.3, -1, 0.5), "LeftUpLeg": (0.1, 0.7, -1),
                    "LeftLeg": (0, 1, -0.5), "RightUpLeg": (-0.1, -0.5, -1), "RightLeg": (0, 0.3, -1),
                    "Head": (0, -0.2, 1)}
    PLANK = STAND | {"LeftArm": (0.4, -0.3, 1), "RightArm": (-0.4, -0.3, 1), "LeftForeArm": (0.3, -0.2, 1),
                     "RightForeArm": (-0.3, -0.2, 1), "LeftUpLeg": (0.12, 0.25, -1), "RightUpLeg": (-0.12, 0.1, -1),
                     "LeftLeg": (0, 0.8, -0.6), "RightLeg": (0, 0.4, -1), "Head": (0, 0.6, 1)}
    DAZED = STAND | {"Head": (0.25, -0.2, 1), "Spine": (0.08, 0, 1), "LeftArm": (0.35, -0.1, -1),
                     "RightArm": (-0.45, -0.3, -1)}
    STAR = STAND | {"LeftArm": (1, 0.1, 0.6), "RightArm": (-1, 0.1, 0.7), "LeftForeArm": (1, 0.4, 0.8),
                    "RightForeArm": (-1, -0.3, 0.9), "LeftUpLeg": (0.6, 0.2, -1), "RightUpLeg": (-0.7, -0.3, -1),
                    "LeftLeg": (0.8, 0.5, -0.6), "RightLeg": (-0.6, -0.6, -0.8), "Head": (0, 0.5, 1), "Spine": (0, 0.3, 1)}
    hkeys = [(T(1.3), TRIP), (T(1.42), TRIP), (T(1.56), PLANK), (T(1.6), PLANK), (T(1.6) + 1, DAZED), (T(1.97), DAZED),
             (T(2.1), STAR), (T(3.0), STAR)]
    act = pose_action(hearm, he, hkeys, "hero_pose")
    to_strip(hearm, act, T(1.3), T(3.0) + 1, blend=1)
    vis(he, [(1, T(3.0) - 1)])
    hit_car = car("hit_car", (14, 8.0, 0), math.pi / 2)      # comes from +X heading -X (yaw +90°: +Y → -X)
    D.key(hit_car, "location", T(1.6) + 1, Vector((16, 8.3, 0)))
    D.key(hit_car, "location", T(1.97), Vector((2.7, 8.3, 0)))
    D.ease_last(hit_car, "LINEAR")
    D.key(hit_car, "location", T(2.6), Vector((-2.5, 8.3, 0)))
    D.key(hit_car, "location", T(3.0), Vector((-3.2, 8.3, 0)))
    D.key(hit_car, "rotation_euler", T(1.97), (0, 0, math.pi / 2))
    D.key(hit_car, "rotation_euler", T(2.2), (0, math.radians(-3), math.pi / 2 + 0.25))
    D.key(hit_car, "rotation_euler", T(3.0), (0, 0, math.pi / 2 + 0.35))
    vis(hit_car, [(T(1.6) + 1, T(3.0) - 1)])

    def cyc_cam(c, l):
        cuts = [  # (frame, cam loc, look at, lens)
            (1, (5.2, -5.4, 1.2), (1.6, -5.4, 1.0), 32), (T(0.6) - 1, (5.2, -4.6, 1.2), (1.6, -4.6, 1.0), 32),
            (T(0.6), (2.2, -1.2, 0.55), (1.6, -4.4, 1.0), 32), (T(1.1) - 1, (2.2, -0.9, 0.55), (1.6, -3.4, 0.95), 32),
            (T(1.1), (4.2, -0.4, 0.6), (1.6, -1.8, 0.7), 28), (T(1.6) - 1, (4.0, -0.2, 0.5), (1.6, -1.0, 0.4), 28),
            (T(1.6), (3.0, 2.6, 1.5), (0.6, 8.4, 1.2), 28), (T(1.97), (2.8, 3.0, 1.6), (0.4, 8.4, 1.3), 28),
            (T(3.0) - 1, (1.6, 3.4, 2.4), (-2.8, 9.2, 2.3), 26)]
        prev = None
        for f, p, a, lens in cuts:
            D.key(c, "location", f, Vector(p))
            D.key(l, "location", f, Vector(a))
            c.data.lens = lens
            c.data.keyframe_insert("lens", frame=f)
        for o in (c, l, c.data):
            for fc in D._fcurves(o.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT" if int(kp.co.x) in (T(0.6) - 1, T(1.1) - 1, T(1.6) - 1) else "BEZIER"

    cyc_c, cyc_l = shot("cam_cycles", street, 1, T(3.0), None, None, None, None, 30, shake=0.004, keyf=cyc_cam)
    SHOTS.append(("cycles", "STREET", 1, T(3.0) - 1))

    # ===== FALLTHROUGH (frames F0+1 .. F0+96)
    fcar = car("fall_car", (1.9, 0, 0), 0.0)
    fz = lambda s: F0 + T(s)
    D.key(fcar, "location", fz(0), Vector((1.9, 0, 0)))
    D.key(fcar, "location", fz(1.4), Vector((1.9, 13.0, 0)))
    D.ease_last(fcar, "LINEAR")
    for s in (1.6, 1.8, 2.0, 2.3, 2.6, 3.0, 3.3):
        dt = s - 1.4
        D.key(fcar, "location", fz(s), Vector((1.9, 13.0 + 8.0 * dt, -0.5 * 9.8 * dt * dt)))
        D.ease_last(fcar, "LINEAR")
    D.key(fcar, "rotation_euler", fz(1.4), (0, 0, 0))
    D.key(fcar, "rotation_euler", fz(3.3), (math.radians(-35), math.radians(14), 0))
    for fc in D._fcurves(fcar.animation_data.action):
        if fc.data_path == "location":
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    vis(fcar, [(F0 + 1, F0 + T(3.3))])

    def fall_cam(c, l):
        for s, p, a, lens in ((0, (1.9, -7.0, 2.1), (1.9, 3.0, 0.9), 30), (1.4, (1.9, 5.6, 2.1), (1.9, 16, 0.6), 30),
                              (1.75, (1.9, 7.6, 1.2), (1.9, 16.5, -1.2), 28),
                              (2.3, (1.9, 9.4, -0.9), (1.9, 19.5, -3.8), 26), (3.3, (1.9, 11.2, -2.0), (1.9, 22.5, -8.5), 24)):
            D.key(c, "location", fz(s), Vector(p))
            D.key(l, "location", fz(s), Vector(a))
            c.data.lens = lens
            c.data.keyframe_insert("lens", frame=fz(s))
        for o in (c, l):
            for fc in D._fcurves(o.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"

    shot("cam_fall", street, F0 + 1, F0 + T(3.2), None, None, None, None, 30, shake=0.003, keyf=fall_cam)
    SHOTS.append(("fallthrough", "STREET", F0 + 1, F0 + T(3.2) - 1))

    # ===== BUGS (frames B0+1 .. B0+72)
    bz = lambda s: B0 + T(s)
    bcar = car("bug_car", (1.9, 14.0, 0), math.radians(8))
    D.key(bcar, "location", bz(0), Vector((1.9, 14.0, -0.85)))
    D.key(bcar, "rotation_euler", bz(0), (math.radians(12), math.radians(-8), math.radians(8)))
    D.key(bcar, "location", bz(0.12), Vector((1.9, 14.0, -0.8)))
    D.key(bcar, "location", bz(0.22), Vector((1.9, 14.0, 0.45)))
    D.key(bcar, "rotation_euler", bz(0.22), (0, 0, math.radians(8)))
    D.key(bcar, "location", bz(0.36), Vector((1.9, 14.0, 0.0)))
    D.key(bcar, "scale", bz(0.22), (1, 1, 1))
    D.key(bcar, "scale", bz(0.36), (1.06, 1.06, 0.88))
    D.key(bcar, "scale", bz(0.48), (1, 1, 1))
    vis(bcar, [(B0 + 1, B0 + T(2.5))])
    # glitch 1: T-posing NPC floating in the sky, slowly spinning
    tp, tparm, tpb = mixamo(MICH, "tpose", (-1.2, 17, 6.0), 0.0)
    tp.scale = (1.5, 1.5, 1.5)
    D.key(tp, "rotation_euler", bz(1.0), (0, math.radians(10), 0))
    D.key(tp, "rotation_euler", bz(2.5), (0, math.radians(10), math.radians(140)))
    D.ease_last(tp, "LINEAR")
    TPOSE = {"LeftArm": (1, 0, 0), "RightArm": (-1, 0, 0), "LeftForeArm": (1, 0, 0), "RightForeArm": (-1, 0, 0),
             "LeftUpLeg": (0.05, 0, -1), "RightUpLeg": (-0.05, 0, -1), "LeftLeg": (0, 0, -1), "RightLeg": (0, 0, -1),
             "Spine": (0, 0, 1), "Head": (0, 0, 1)}
    act = pose_action(tparm, tp, [(B0 - 5, TPOSE), (B0 + 80, TPOSE)], "tpose_pose")
    to_strip(tparm, act, 1, B0 + 90, blend=0)
    vis(tp, [(bz(1.0), B0 + T(2.5))])
    # glitch 2: NPC whose mesh explodes into spikes
    sp_r, sparm, spb = mixamo(MICH, "spiky", (-1.0, 13.2, 0.0), math.radians(20))
    act = pose_action(sparm, sp_r, [(B0 - 5, STAND), (B0 + 80, STAND)], "spiky_pose")
    to_strip(sparm, act, 1, B0 + 90, blend=0)
    tex = bpy.data.textures.new("spikes", "NOISE")
    for m in spb:
        ws = 1.0 / m.matrix_world.to_scale().x
        dm = m.modifiers.new("explode", "DISPLACE")
        dm.texture = tex
        dm.mid_level = 0.35
        dm.strength = 0.0
        dm.keyframe_insert("strength", frame=bz(1.0) - 1)
        dm.strength = 0.9 * ws
        dm.keyframe_insert("strength", frame=bz(1.0) + 2)
        dm.strength = 0.7 * ws
        dm.keyframe_insert("strength", frame=bz(1.3))
        dm.strength = 1.1 * ws
        dm.keyframe_insert("strength", frame=bz(2.5))
    vis(sp_r, [(bz(1.0), B0 + T(2.5))])
    # glitch 3: car stuck nose-first inside a palm tree on the sidewalk
    stuck_palm = palm("stuck_palm", (5.2, 19.5, 0.15), h=7.5, seed=99, lean=-0.1)
    scar = car("stuck_car", (5.0, 18.6, 1.3), math.radians(-20))
    scar.rotation_euler = (math.radians(-38), math.radians(10), math.radians(-20))
    for i, f in enumerate(range(bz(1.0), B0 + T(2.5), 2)):
        D.key(scar, "location", f, Vector((5.0 + random.uniform(-0.07, 0.07), 18.6 + random.uniform(-0.07, 0.07),
                                            1.3 + random.uniform(-0.06, 0.06))))
    vis(scar, [(bz(1.0), B0 + T(2.5))])
    vis(stuck_palm, [(B0 - 10, B0 + T(2.5))])

    def bug_cam(c, l):
        base_p, base_a = Vector((0.2, 6.0, 1.7)), Vector((1.0, 17.0, 3.4))
        D.key(c, "location", bz(0), base_p)
        D.key(l, "location", bz(0), base_a)
        D.key(c, "location", bz(1.0) - 1, base_p + Vector((0, 0.4, 0)))
        D.key(l, "location", bz(1.0) - 1, base_a)
        rr = random.Random(5)
        for i, f in enumerate(range(bz(1.0), bz(1.45), 2)):
            amp = 0.12 * (1 - i / 7)
            D.key(c, "location", f, base_p + Vector((0, 0.4 + i * 0.03, 0)) +
                  Vector((rr.uniform(-amp, amp), 0, rr.uniform(-amp, amp))))
            D.key(l, "location", f, base_a)
        D.key(c, "location", bz(2.5), base_p + Vector((0, 1.2, 0.1)))
        D.key(l, "location", bz(2.5), base_a + Vector((0, 0, 0.2)))
        c.data.lens = 24
        c.data.keyframe_insert("lens", frame=bz(0))

    shot("cam_bugs", street, B0 + 1, B0 + T(2.4), None, None, None, None, 22, shake=0.0, keyf=bug_cam)
    SHOTS.append(("bugs", "STREET", B0 + 1, B0 + T(2.4) - 1))
    street.frame_set(1)

# ================================================================= CLEAN: grey viewport, frozen tumble being cleaned
clean = L.new_set("CLEAN")
with L.building(clean):
    viewport_set(clean, bg="#585b62")
    L.post(clean, bloom=0.4, vignette=0.28)
    cr_, carm, cbody = mixamo(MICH, "clean", (0, 0, 1.4), 0.0)
    cclay = xray_mat("cclay", None, tint="#bfe9ff")
    for m in cbody:
        m.data.materials.clear()
        m.data.materials.append(cclay)
    bone_viz(carm)
    cr_.rotation_euler = (math.radians(70), math.radians(80), math.radians(40))
    MESSY = STAR | {"LeftForeArm": (-0.3, -0.9, -0.5), "RightUpLeg": (0.4, -0.8, 0.3), "Head": (-0.7, 0.2, -0.3)}
    MID = STAR | {"LeftForeArm": (0.6, 0.3, -0.4)}
    k91 = T(3.0)
    act = pose_action(carm, cr_, [(k91, MESSY), (k91 + 20, MESSY), (k91 + 21, MID), (k91 + 41, MID), (k91 + 42, STAR),
                                  (k91 + 80, STAR)], "clean_pose")
    for fc in D._fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"
    to_strip(carm, act, 1, k91 + 90, blend=0)
    ccar = car("clean_car", (2.6, -0.4, 0), math.pi / 2 + 0.35)
    ccl = L.plastic("ccar", H("#8f9297"), rough=0.6, coat=0.05)
    for o in ccar.children_recursive:
        if o.type == "MESH":
            o.data = o.data.copy()
            o.data.materials.clear()
            o.data.materials.append(ccl)

    def clean_cam(c, l):
        for i, a in enumerate((0.0, 0.33, 0.66, 1.0)):
            ang = math.radians(-60 + 55 * a)
            f = k91 + int(a * 70)
            D.key(c, "location", f, Vector((4.0 * math.sin(ang), -4.0 * math.cos(ang), 2.0 + 0.3 * a)))
            D.key(l, "location", f, Vector((0.3, 0, 1.35)))
        for o in (c, l):
            for fc in D._fcurves(o.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"

    shot("cam_clean", clean, k91, k91 + 70, None, None, None, None, 30, shake=0.002, keyf=clean_cam)
    SHOTS.append(("cycles", "CLEAN", k91, T(5.3) - 1))

# ================================================================= ROOM: lone dev at night
room = L.new_set("ROOM")
ERIC_S = 1.82 / 186.865
REN = {"hip": "Hips", "spine_01": "Spine", "spine_02": "Spine1", "spine_03": "Spine2", "neck": "Neck", "head": "Head",
       "jaw": "Jaw"}
for _s, _S in (("l", "Left"), ("r", "Right")):
    REN |= {f"shoulder_{_s}": f"{_S}Shoulder", f"upperarm_{_s}": f"{_S}Arm", f"lowerarm_{_s}": f"{_S}ForeArm",
            f"hand_{_s}": f"{_S}Hand", f"upperleg_{_s}": f"{_S}UpLeg", f"lowerleg_{_s}": f"{_S}Leg", f"foot_{_s}": f"{_S}Foot"}
with L.building(room):
    L.hdri_world(room, "studio_small_09", 0.04, backdrop=H("#04060d"))
    D.room("bedroom", (0, 0, 2.5), (7, 7, 5), L.pbr("rwall", "plastered_wall", scale=0.6, tint=H("#26365e"), tint_amount=0.9, normal=0.5))
    D.box("rfloor", (7, 7, 0.02), (0, 0, 0.0), L.pbr("rfl", "laminate_floor_02", scale=0.8, rough_mul=0.7))
    DY = -0.8
    pc = glb(os.path.join(HINDI, "desk_pc.glb"), keep=lambda o: "BezierCurve.003" not in o.name)
    for o in pc:
        o.data.transform(Matrix.Rotation(math.pi / 2, 4, "Z"))
    mon = next(o for o in pc if o.name.startswith("MY SCREEN"))
    slo, shi = bounds([mon])
    k = 0.94 / (shi.x - slo.x)
    for o in pc:
        o.data.transform(Matrix.Translation((-(slo.x + shi.x) / 2 * k, DY - 0.435 - shi.y * k, 1.2 - (slo.z + shi.z) / 2 * k))
                         @ Matrix.Scale(k, 4))
    slab = next(o for o in pc if o.name.startswith("Cube_Material"))
    dlo, dhi = bounds([slab])
    ink = L.plastic("ink", H("#1f2230"), rough=0.4)
    for x in (dlo.x + 0.06, dhi.x - 0.06):
        for y in (dlo.y + 0.06, dhi.y - 0.06):
            D.box("dleg", (0.05, 0.05, dlo.z), (x, y, dlo.z / 2), ink)
    ch = glb(os.path.join(HINDI, "chair.glb"))
    lo, hi = bounds(ch)
    s = 1.3 / (hi.z - lo.z)
    offc = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for o in ch:
        o.data.transform(Matrix.Translation((0, 0.12, 0)) @ Matrix.Scale(s, 4) @ Matrix.Translation(-offc))
        dm = o.modifiers.new("dec", "DECIMATE")
        dm.ratio = 0.2
    scr_m = D.mat("screen", H("#3a4a66"), rough=0.2, emit=H("#7fb2ff"), emit_strength=2.4)
    D.box("screen", (0.94, 0.01, 0.54), (0, DY - 0.42, 1.2), scr_m)
    D.area_light("monglow", 140, (0, DY - 0.3, 1.2), (0, 0.2, 1.1), size=0.9, rgb=H("#bcd4ff"))
    D.area_light("rkey", 60, (-2.2, -2.6, 2.8), (0, -0.2, 1.0), size=2.5, rgb=H("#5c78ff"))
    D.area_light("rrim", 90, (1.8, 2.2, 2.4), (0, 0, 1.2), size=1.5, rgb=H("#4f7dff"))
    win_m = D.mat("winsky", H("#0b1530"), rough=1, emit=H("#162a5e"), emit_strength=0.9)
    D.box("winframe", (1.5, 0.1, 1.2), (-2.0, -3.45, 2.2), L.plastic("wf", H("#cfd6e6"), rough=0.4))
    D.box("winsky", (1.3, 0.05, 1.0), (-2.0, -3.4, 2.2), win_m)
    er, earm, ebody = D.import_char(os.path.join(HINDI, "eric.glb"), "eric")
    for b in earm.data.bones:
        bn = re.sub(r"_\d+$", "", b.name)
        if bn in REN:
            b.name = REN[bn]
    earm.scale = (ERIC_S,) * 3
    er.location = (0, -0.2, 0.6 - 96.9 * ERIC_S)
    for b in ebody:
        for m in b.data.materials:
            bs = m.node_tree.nodes.get("Principled BSDF") if m and m.use_nodes else None
            if bs:
                bs.inputs["Roughness"].default_value = 0.55
    room.frame_set(1)
    vl_of(earm).update()

    def aim_eric(n, d, fr):
        pb = D.bone(earm, n)
        vl_of(earm).update()
        inv = earm.matrix_world.to_3x3().inverted()
        cur = (pb.children[0].head - pb.head).normalized()
        tgt = (inv @ Vector(d)).normalized()
        if n in ("Neck", "Head"):
            rest = (pb.children[0].bone.head_local - pb.bone.head_local).normalized()
            up = (inv @ Vector((0, 0, 1))).normalized()
            tgt = up.rotation_difference(tgt) @ rest
        m = pb.matrix.copy()
        nm = (cur.rotation_difference(tgt).to_matrix() @ m.to_3x3()).to_4x4()
        nm.translation = m.translation
        pb.matrix = nm
        vl_of(earm).update()
        pb.keyframe_insert("rotation_quaternion", frame=fr)

    SIT = {"LeftUpLeg": (0.12, -1, 0.02), "RightUpLeg": (-0.12, -1, 0.02), "LeftLeg": (0, -0.15, -1),
           "RightLeg": (0, -0.15, -1), "Spine": (0, -0.22, 1), "LeftArm": (0.3, -0.7, -0.6),
           "RightArm": (-0.3, -0.7, -0.6), "LeftForeArm": (-0.1, -1, 0.08), "RightForeArm": (0.1, -1, 0.08),
           "Neck": (0, -0.25, 1), "Head": (0, -0.35, 1)}
    for fr in (1, 80):
        for n, d in SIT.items():
            aim_eric(n, d, fr)
    shot("cam_lonely", room, 1, T(2.1), (2.0, -3.0, 1.75), (1.2, -2.05, 1.55), (0, -0.4, 1.1), (0, -0.3, 1.2), 26, 30,
         shake=0.003)
    L.post(room, bloom=0.6, bloom_threshold=0.75, vignette=0.34)
SHOTS.append(("lonely", "ROOM", 1, T(2.1) - 1))

json.dump(SHOTS, open(os.path.join(os.path.dirname(os.path.abspath(out)), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
print("SAVED", out, SHOTS)
