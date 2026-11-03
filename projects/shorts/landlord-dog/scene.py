"""blender -b -P scene.py -- <out.blend>: "You stepped on the landlord's dog's tail" (33 s comedy short).

  HALL   0.0  sneak past the sleeping dog (silent hook)  →  ~2.3 squish on the tail  →  dog wakes, red eyes
         5.2  dog GROWS  /  7.9 offer it a snack (Vi3W bread)  /  10.6 gulp  /  12.6 "wants dessert"  /  14.0 lunge
  YARD  14.5  RUN: out of the door, circles round the tree  /  18.4 landlord in the doorway  /  21.2 RENT ↑
  SHOW  24.0  the Vi3W props on turntables: bread, panda, robot  →  "MADE IN Vi3W" / Vi3W.in

Cast: Xbot (three.js/Mixamo) for you + the landlord, Quaternius "Husky" (CC0) for the dog — stand-ins, NOT Vi3W.
Only bread/panda/robot are Vi3W generations, so only they appear on the "made in Vi3W" card.
Writes out/shots.json (scene, f0, f1) and out/meta.json (the measured tail-step time for the SFX).
"""
import json, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
import bpy
import director as D
import look as L
from director import T

out = sys.argv[sys.argv.index("--") + 1]
A = os.path.join(HERE, "assets")
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
END = 33.0
H = D.hex_lin
DOG_S, DOG_BIG = 0.42, 0.7

base = D.reset(frames=T(END) - 1)
D.fast_eevee(base, samples=16, look="AgX - Punchy")
SHOTS = []

ink = L.plastic("ink", H("#1f2230"), rough=0.4)
white = L.plastic("white", H("#f7f4ef"), rough=0.3)
red = L.plastic("red", H("#ff3b47"), rough=0.3, emit=H("#ff3b47"), emit_strength=0.3)
SUIT_YOU = L.plastic("suit_you", H("#ff7a1a"), rough=0.35, coat=0.4)
SUIT_LL = L.plastic("suit_ll", H("#5b2a86"), rough=0.35, coat=0.4)
JOINT = L.plastic("joint", H("#f5f1ea"), rough=0.3)
GLOW = L.plastic("eye_glow", H("#ff1a1a"), rough=0.2, emit=H("#ff1a1a"), emit_strength=0.0)


def key(o, p, t, v):
    D.key(o, p, T(t), v)


def shot(sc, name, t0, t1, loc0, loc1, at0, at1, lens0=30, lens1=None, shake=0.004, dof=None):
    c, l = D.camera(name, lens0, dof=dof)
    D.move(c, l, T(t0), T(t1), loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    D.cut(sc, T(t0), c)
    SHOTS.append((sc.name, T(t0), T(t1) - 1 if t1 < END else T(END) - 1))
    return c, l


def pop(o, t, scale=1.0, dur=0.3):
    D.key(o, "scale", 1, (0, 0, 0))
    D.key(o, "scale", T(t), (0, 0, 0))
    D.overshoot(o, "scale", T(t), T(t + dur), (0, 0, 0), (scale,) * 3, 1.18)


def rotz(v, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


# ---------------------------------------------------------------- characters

def person(name, loc, yaw, suit):
    r, arm, body = D.import_char(os.path.join(A, "Xbot.glb"), name)
    r.location, r.rotation_euler = loc, (0, 0, yaw)
    for b in body:
        j = "joint" in (b.data.materials[0].name if b.data.materials else "").lower()
        D.give(b, JOINT if j else suit)
    return r, arm, body


def dog(name, loc, yaw, scale=DOG_S, eyes_on=True):
    r, arm, body = D.import_char(os.path.join(A, "husky.glb"), name)
    r.location, r.rotation_euler, r.scale = loc, (0, 0, yaw), (scale,) * 3
    for b in body:
        for i, m in enumerate(b.data.materials):
            if m and m.name.startswith("Eyes_White"):
                b.data.materials[i] = GLOW
            elif m and m.name.startswith("Main") and not m.name.startswith("Main_Light"):
                bsdf = m.node_tree.nodes.get("Principled BSDF")
                if bsdf and not bsdf.inputs["Base Color"].is_linked:      # darker, meaner coat
                    c = bsdf.inputs["Base Color"].default_value
                    bsdf.inputs["Base Color"].default_value = (c[0] * 0.55, c[1] * 0.55, c[2] * 0.6, 1)
    return r, arm, body


def aim_limb(arm, n, world_dir, frame):
    """Point the limb (this joint → its child joint) along world_dir. glTF-imported Xbot bones have arbitrary
    tails, so D.aim (bone Y axis) misses; the joint-to-joint vector is the real limb."""
    pb = D.bone(arm, n)
    bpy.context.view_layer.update()
    cur = (pb.children[0].head - pb.head).normalized()
    tgt = (arm.matrix_world.to_3x3().inverted() @ Vector(world_dir)).normalized()
    m = pb.matrix.copy()
    r = cur.rotation_difference(tgt).to_matrix() @ m.to_3x3()
    nm = r.to_4x4()
    nm.translation = m.translation
    pb.matrix = nm
    bpy.context.view_layer.update()
    pb.keyframe_insert("rotation_quaternion", frame=frame)


def pose_strip(arm, root, keys, f0, f1, blend=4):
    """Scripted acting on top of the stock clips: keys = [(frame, {bone: local_dir})]; dirs are in the character's
    own frame (−Y forward, +X its left) and turned by the root yaw. Lives in its own NLA strip f0..f1."""
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions.new(f"{arm.name}_pose_{f0}")
    ad.use_nla = False
    ad.action = act
    for fr, dirs in keys:
        bpy.context.scene.frame_set(fr)
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
        bpy.context.view_layer.update()
        yaw = root.matrix_world.to_euler().z
        for n, d in dirs.items():
            aim_limb(arm, n, rotz(d, yaw), fr)
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
    return st


def hold(arm, clip, f0, f1, at=None):
    """Freeze one frame of a stock clip (default: its last) over f0..f1."""
    act = D.CLIPS[arm.name][clip]
    a = act.frame_range[1] if at is None else at
    ad = arm.animation_data or arm.animation_data_create()
    tr = ad.nla_tracks.new()
    st = tr.strips.new(f"{clip}_hold_{f0}", int(f0), act)
    st.action_frame_start, st.action_frame_end = a - 0.5, a
    st.scale = (f1 - f0) / 0.5
    st.blend_in = st.blend_out = 0
    st.extrapolation = "NOTHING"
    return st


def follow(root, t0, t1, fn, face=True, step=2):
    """Root along fn(t)→(x,y) from t0..t1 (seconds); yaw follows the velocity (characters face −Y at yaw 0)."""
    prev_yaw = None
    f = T(t0)
    while f <= T(t1):
        t = (f - 1) / D.FPS
        x, y = fn(t)
        root.location = (x, y, root.location.z)
        root.keyframe_insert("location", frame=f)
        if face:
            x2, y2 = fn(t + 0.05)
            vx, vy = x2 - x, y2 - y
            if abs(vx) + abs(vy) > 1e-5:
                yaw = math.atan2(vx, -vy)
                if prev_yaw is not None:
                    while yaw - prev_yaw > math.pi:
                        yaw -= 2 * math.pi
                    while yaw - prev_yaw < -math.pi:
                        yaw += 2 * math.pi
                prev_yaw = yaw
                root.rotation_euler = (0, 0, yaw)
                root.keyframe_insert("rotation_euler", frame=f)
        f += step


def attach(o, arm, bone_name):
    """Parent o to a bone, keeping its current world placement (call at rest pose)."""
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    o.parent, o.parent_type, o.parent_bone = arm, "BONE", D.bone(arm, bone_name).name
    bpy.context.view_layer.update()
    o.matrix_world = mw


def vi3w_model(path, name, height, decimate=0.12):
    """Vi3W GLB → one decimated mesh standing on z=0, ~`height` m tall. Returns (object, mesh) for re-use."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    ms = [o for o in new if o.type == "MESH"]
    for o in new:
        D.adopt(o)
    m = ms[0]
    bpy.context.view_layer.update()
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = mw
    for o in new:
        if o is not m:
            bpy.data.objects.remove(o)
    m.data.transform(m.matrix_world)
    m.matrix_world = Matrix()
    if decimate and len(m.data.polygons) > 80_000:
        mod = m.modifiers.new("dec", "DECIMATE")
        mod.ratio = decimate
        bpy.context.view_layer.objects.active = m
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(m.evaluated_get(dg))
        m.modifiers.clear()
        old = m.data
        m.data = me
        bpy.data.meshes.remove(old)
    vs = [v.co for v in m.data.vertices]
    mn = Vector([min(v[i] for v in vs) for i in range(3)])
    mx = Vector([max(v[i] for v in vs) for i in range(3)])
    s = height / (mx.z - mn.z)
    c = (mn + mx) / 2
    m.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-c.x, -c.y, -mn.z)))
    for p in m.data.polygons:
        p.use_smooth = True
    m.name = name
    return m, m.data


def clone(me, name, loc, rz=0.0, scale=1.0):
    o = D.link(bpy.data.objects.new(name, me))
    o.location, o.rotation_euler, o.scale = loc, (0, 0, rz), (scale,) * 3
    return o


# ================================================================= HALL
hall = L.new_set("HALL", main=True)
L.hdri_world(hall, "studio_small_09", 0.25, rot_deg=30, backdrop=H("#20262e"), backdrop_strength=0.3)
HW, HL0, HL1, HH = 2.3, -5.0, 7.0, 2.9
wall = L.pbr("hall_wall", "plastered_wall", scale=0.7, tint=H("#3fb6a8"), tint_amount=0.8, normal=0.5)
D.box("floor", (2 * HW, HL1 - HL0, 0.1), (0, (HL0 + HL1) / 2, -0.05), L.pbr("hfloor", "laminate_floor_02", scale=0.8))
D.box("ceiling", (2 * HW, HL1 - HL0, 0.1), (0, (HL0 + HL1) / 2, HH + 0.05), L.plastic("ceil", H("#f4efe6"), rough=0.8))
for sx in (-1, 1):
    D.box("wall", (0.1, HL1 - HL0, HH), (sx * (HW + 0.05), (HL0 + HL1) / 2, HH / 2), wall)
    D.box("skirting", (0.04, HL1 - HL0, 0.12), (sx * (HW - 0.02), (HL0 + HL1) / 2, 0.06), white)
D.box("endwall", (2 * HW, 0.1, HH), (0, HL1 + 0.05, HH / 2), wall)
D.box("frontwall", (2 * HW, 0.1, HH), (0, HL0 - 0.05, HH / 2), wall)
D.box("enddoor", (1.0, 0.06, 2.15), (0, HL1 - 0.03, 1.075), L.plastic("hdoor", H("#1d4ed8"), rough=0.3, coat=0.6), bevel=0.01)
D.box("rug", (1.1, 7.5, 0.012), (0.1, 1.2, 0.006), L.pbr("rug", "fabric_pattern_07", scale=2.5, tint=H("#d62839"),
                                                          tint_amount=0.75))
D.box("console", (0.4, 1.1, 0.06), (HW - 0.22, 3.2, 0.82), L.pbr("ctop", "wood_table_001", scale=2), bevel=0.01)
for dy in (-0.48, 0.48):
    D.box("cleg", (0.05, 0.05, 0.8), (HW - 0.22, 3.2 + dy, 0.4), ink)
robot_o, robot_me = vi3w_model(os.path.join(A, "robot.glb"), "robot_hall", 0.55)
robot_o.location, robot_o.rotation_euler = (HW - 0.22, 3.2, 0.85), (0, 0, math.radians(-110))
L.prop("potted_plant_02", (-HW + 0.3, 5.6, 0.0), scale=1.1)
L.prop("fancy_picture_frame_01", (HW - 0.03, 3.2, 1.65), rot_z=-90, scale=1.6)
for i, y in enumerate((-2.5, 1.0, 4.5)):
    D.cyl("lamp", 0.22, 0.04, (0, y, HH - 0.02), m=L.plastic(f"lampc{i}", H("#fff4d6"), emit=H("#ffe2a8"), emit_strength=2.0))
    D.area_light(f"ceil{i}", 120, (0, y, HH - 0.08), (0, y, 0), size=1.2, rgb=H("#ffe0b5"))
D.area_light("fill", 90, (1.2, -4.5, 1.8), (0, 1, 1), size=2, rgb=H("#b8d8ff"))
L.post(hall, bloom=0.4, vignette=0.28)

# you: sneak from the far end toward the camera
STOP_T = 2.6
you, yarm, _ = person("you", (0.3, 3.6, 0), 0.0, SUIT_YOU)
D.key(you, "location", 1, (0.3, 3.6, 0))
D.key(you, "location", T(STOP_T), (0.3, 1.3, 0))
for fc in D._fcurves(you.animation_data.action):
    for k in fc.keyframe_points:
        k.interpolation = "LINEAR"
D.play(yarm, "walk", 1, T(STOP_T) + 2, speed=0.62, blend=0)

# measure: the right foot's plant (lowest point, after its swing) in 1.9–2.4 s is the squish
zs = []
for f in range(T(1.6), T(2.45)):
    hall.frame_set(f)
    zs.append((f, D.bone_world(yarm, "RightToeBase").copy()))
peak = max(range(len(zs)), key=lambda i: zs[i][1].z)
STEP_F, FOOT = min(zs[peak:], key=lambda fp: fp[1].z)
hall.frame_set(STEP_F + 2)
halt = you.location.copy()
you.keyframe_delete("location", frame=T(STOP_T))
D.key(you, "location", STEP_F + 2, halt)
D.play(yarm, "idle", STEP_F + 2, T(14.6), blend=4)
STEP = (STEP_F - 1) / D.FPS

# dog asleep (Death clip's last frame held), its tail tip moved under that foot
rover, darm, dbody = dog("dog", (0, 0, 0), 0.0)
hold(darm, "Death", 1, STEP_F)
hall.frame_set(STEP_F - 1)
tail = D.bone_world(darm, "Tail3") * 0.5 + D.bone_world(darm, "Tail2") * 0.5
rover.location = (FOOT.x - tail.x, FOOT.y - tail.y + 0.02, 0)
D.key(rover, "location", STEP_F, rover.location.copy())
D.key(rover, "rotation_euler", STEP_F, (0, 0, 0))
D.key(rover, "scale", STEP_F, (DOG_S,) * 3)
panda_o, panda_me = vi3w_model(os.path.join(A, "panda.glb"), "panda_hall", 0.42, decimate=0)
panda_o.location, panda_o.rotation_euler = (rover.location.x + 0.75, rover.location.y - 1.25, 0), (0, 0, math.radians(-20))

# wake: yelp → spin to face you → growl; then GROW
DOG_Y = FOOT.y - 2.35
D.play(darm, "Idle_HitReact_Left", STEP_F, STEP_F + 22, speed=0.8, blend=2)
D.play(darm, "Idle_2_HeadLow", STEP_F + 20, T(10.5), speed=0.9, blend=6)
D.key(rover, "location", STEP_F + 18, (0.3, DOG_Y, 0))
D.key(rover, "rotation_euler", STEP_F + 18, (0, 0, math.pi))
D.ease_all(rover)
GLOW.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.0
GLOW.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].keyframe_insert("default_value", frame=T(3.2))
GLOW.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 9.0
GLOW.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].keyframe_insert("default_value", frame=T(3.45))
key(rover, "scale", 5.4, (DOG_S,) * 3)
D.overshoot(rover, "scale", T(5.4), T(6.4), (DOG_S,) * 3, (DOG_BIG,) * 3, 1.08)

# you: hands up (4.2), pull the bread (8.6), wind-up, THROW (9.9)
UP = {"LeftArm": (0.35, -0.2, 1), "LeftForeArm": (0.05, -0.15, 1), "RightArm": (-0.35, -0.2, 1),
      "RightForeArm": (-0.05, -0.15, 1), "Head": (0, 0.25, 1)}
DOWN_L = {"LeftArm": (0.25, 0, -1), "LeftForeArm": (0.15, -0.2, -1)}
HOLD = DOWN_L | {"RightArm": (-0.4, -0.65, -0.35), "RightForeArm": (-0.05, -1, 0.25)}
WIND = DOWN_L | {"RightArm": (-0.45, 0.35, 0.75), "RightForeArm": (-0.1, 0.55, 1)}
THROW = DOWN_L | {"RightArm": (-0.15, -1, 0.45), "RightForeArm": (-0.05, -1, 0.15)}
pose_strip(yarm, you, [(T(4.15), UP), (T(8.2), UP), (T(8.55), HOLD), (T(9.55), HOLD), (T(9.75), WIND),
                       (T(9.92), THROW), (T(10.6), THROW), (T(11.0), UP), (T(14.4), UP)], T(4.05), T(14.6))
D.play(yarm, "run", T(14.4), T(14.6) + 2, speed=1.3, blend=2)

# bread: pops into the hand, arcs to the floor in front of the dog, gulped
bread_o, bread_me = vi3w_model(os.path.join(A, "bread.glb"), "bread_hall", 0.3)
RH = lambda f: (hall.frame_set(f), D.bone_world(yarm, "RightHand").copy())[1]
EAT0, EAT1 = 10.55, 12.5
D.play(darm, "Eating", T(EAT0), T(EAT1), speed=0.9, blend=5)
hall.frame_set(T(11.2))
mouth = D.bone_world(darm, "Head")
land = Vector((mouth.x, mouth.y + 0.12 * DOG_BIG / DOG_S * DOG_S, 0.0))
bread_o.rotation_euler = (0, 0, 0.6)
D.key(bread_o, "scale", 1, (0, 0, 0))
D.key(bread_o, "scale", T(8.5), (0, 0, 0))
D.overshoot(bread_o, "scale", T(8.5), T(8.8), (0, 0, 0), (1, 1, 1), 1.25)
for f in range(T(8.5), T(9.92) + 1, 2):
    D.key(bread_o, "location", f, RH(f) + Vector((0, 0, -0.1)))
p0 = RH(T(9.92)) + Vector((0, 0, -0.1))
n = T(10.6) - T(9.92)
for i in range(n + 1):
    u = i / n
    p = p0.lerp(land, u) + Vector((0, 0, 0.9 * 4 * u * (1 - u)))
    D.key(bread_o, "location", T(9.92) + i, p)
    D.key(bread_o, "rotation_euler", T(9.92) + i, (u * 7, 0, 0.6 + u * 3))
D.key(bread_o, "scale", T(11.15), (1, 1, 1))
D.key(bread_o, "scale", T(11.3), (0, 0, 0))

# dessert: head up, slow menace, LUNGE
D.play(darm, "Idle", T(EAT1) - 4, T(14.0), speed=0.7, blend=6)
D.play(darm, "Attack", T(14.0), T(14.6) + 2, speed=1.1, blend=3)
key(rover, "location", 14.0, (0.3, DOG_Y, 0))
key(rover, "location", 14.5, (0.3, DOG_Y + 0.9, 0))

# --- HALL cameras
F = FOOT
shot(hall, "A_wide", 0.0, STEP - 0.75, (1.15, -3.6, 0.55), (1.05, -3.2, 0.6), (-0.2, 2.0, 0.75), (-0.1, 2.0, 0.75), 22)
shot(hall, "B_tail", STEP - 0.75, 2.9, (F.x + 0.95, F.y - 0.45, 0.32), (F.x + 0.8, F.y - 0.38, 0.28),
     (F.x, F.y + 0.05, 0.12), (F.x, F.y, 0.1), 38, dof=4)
hall.frame_set(T(3.5))
hd = D.bone_world(darm, "Head").copy()
shot(hall, "C_eyes", 2.9, 4.1, hd + Vector((0.75, 0.75, 0.0)), hd + Vector((0.5, 0.55, 0.02)), hd, hd, 40, dof=4)
yh = Vector((0.3, F.y + 0.2, 1.55))
shot(hall, "D_you", 4.1, 5.2, (1.5, yh.y - 2.1, 1.35), (1.25, yh.y - 1.7, 1.4), yh - Vector((0, 0, 0.25)), yh - Vector((0, 0, 0.15)), 30)
hall.frame_set(T(7.0))
hd = D.bone_world(darm, "Head").copy()
shot(hall, "E_ots", 5.2, 7.9, (-0.55, F.y + 1.9, 0.95), (-0.45, F.y + 1.6, 0.9), hd - Vector((0, 0, 0.5)), hd, 22)
mid = Vector((0.2, (F.y + DOG_Y) / 2, 1.0))
mid = Vector((0.2, F.y - 0.75, 1.0))
shot(hall, "F_side", 7.9, 10.55, (2.2, mid.y + 0.25, 1.2), (2.1, mid.y + 0.2, 1.15), mid, mid + Vector((0, 0, 0.05)), 16)
shot(hall, "G_gulp", 10.55, 12.6, land + Vector((1.1, 0.7, 0.35)), land + Vector((0.9, 0.55, 0.3)),
     land + Vector((0, -0.1, 0.35)), land + Vector((0, -0.1, 0.45)), 30, dof=5)
hall.frame_set(T(13.5))
hd = D.bone_world(darm, "Head").copy()
pov = hd + Vector((1.5, 1.3, -0.15))
shot(hall, "H_pov", 12.6, 14.0, pov, pov + (hd - pov) * 0.3, hd, hd, 26, lens1=42, shake=0.008)
shot(hall, "H2_lunge", 14.0, 14.5, (0.85, F.y + 2.4, 1.2), (0.95, F.y + 2.7, 1.25), (0.3, DOG_Y + 1.8, 1.3),
     (0.3, DOG_Y + 2.0, 1.3), 20, shake=0.012)

# ================================================================= YARD
yard = L.new_set("YARD")
with L.building(yard):
    L.hdri_world(yard, "kloofendal_48d_partly_cloudy_puresky", 1.0, rot_deg=150)
    D.sun("sun", 3.2, (0.5, 0.65, -0.62), rgb=H("#fff0dc"), angle=2.5)
    D.box("lawn", (200, 200, 0.1), (0, -40, -0.05), L.pbr("lawn", "leafy_grass", scale=0.45, tint=H("#7bc96f"),
                                                          tint_amount=0.35))
    D.box("path", (1.6, 4.5, 0.03), (0, -2.5, 0.0), L.pbr("paving", "pavement_02", scale=1.1))
    plaster = L.pbr("house_paint", "plastered_wall", scale=0.6, tint=H("#ffd166"), tint_amount=0.8, normal=0.6)
    trim = L.plastic("trim", H("#fffaf2"), rough=0.4)
    D.box("house", (9, 2, 5.2), (0, 1.0, 2.6), plaster)
    D.box("plinth", (9.05, 2.05, 0.55), (0, 1.0, 0.275), L.pbr("brick", "red_brick_03", scale=1.2))
    D.box("roof", (9.7, 2.7, 0.38), (0, 0.9, 5.35), L.plastic("roof", H("#2b2d42"), rough=0.5), bevel=0.04)
    D.box("doorway", (1.3, 0.2, 2.35), (0, -0.02, 1.17), L.plastic("inside", H("#2a1b1f"), rough=0.9))
    for x in (-0.72, 0.72):
        D.box("jamb", (0.14, 0.16, 2.5), (x, -0.06, 1.25), trim, bevel=0.01)
    D.box("lintel", (1.6, 0.16, 0.16), (0, -0.06, 2.45), trim, bevel=0.01)
    hinge = D.empty("hinge", (-0.65, -0.08, 0.0))
    D.box("door", (1.25, 0.07, 2.3), (0.62, 0, 1.15), L.plastic("ydoor", H("#1d4ed8"), rough=0.25, coat=0.6),
          bevel=0.012).parent = hinge
    hinge.rotation_euler = (0, 0, math.radians(-105))
    glow = L.plastic("window", H("#ffe2a8"), rough=0.15, emit=H("#ffcf70"), emit_strength=1.0)
    for x in (-2.8, 2.8):
        D.box("window", (1.3, 0.12, 1.3), (x, -0.02, 2.6), glow)
        D.box("wsill", (1.5, 0.16, 0.1), (x, -0.08, 1.9), trim, bevel=0.01)
    D.box("rentsign", (1.2, 0.08, 0.5), (2.8, -0.12, 1.25), white, bevel=0.03)
    for i, (x, y, s_) in enumerate(((-6.0, -2.0, 1.3), (7.5, -3.0, 1.1), (-9, -10, 1.4), (9, -14, 1.2))):
        L.toy_tree((x, y, 0), scale=s_, seed=i)
    TR = 2.0
    RUN0, LOOP0, CHASE1 = 14.5, 15.3, 18.4
    V = 4.6

    # path end (0,-3.8) is the circle's west point: centre = (TR, -3.8)
    CC = Vector((TR, -3.8, 0))
    L.toy_tree((CC.x, CC.y, 0), scale=0.9, seed=12)

    def chase(t):
        if t < LOOP0:
            u = (t - RUN0) / (LOOP0 - RUN0)
            return (0.0, -0.8 - 3.0 * u)
        a = math.pi - (t - LOOP0) * V / TR
        return (CC.x + TR * math.cos(a), CC.y + TR * math.sin(a))

    me_y, me_arm, _ = person("you_y", (0, -0.8, 0), 0.0, SUIT_YOU)
    follow(me_y, RUN0, CHASE1 - 0.04, chase)
    D.play(me_arm, "run", T(RUN0) - 2, T(CHASE1) + 2, speed=1.25, blend=1)
    D.key(me_y, "location", T(CHASE1), (0.9, -4.6, 0))
    D.key(me_y, "rotation_euler", T(CHASE1), (0, 0, math.pi))
    D.play(me_arm, "sad_pose", T(CHASE1), T(END), blend=1)

    ydog, ydarm, _ = dog("dog_y", (0, -0.5, 0), 0.0, scale=DOG_BIG * 0.8)
    LAG = 0.8
    follow(ydog, RUN0, CHASE1 - 0.04, lambda t: chase(t - LAG) if t - LAG >= RUN0 else (0.0, -0.8 + 2.0 * (RUN0 + LAG - t)))
    D.play(ydarm, "Gallop", T(RUN0), T(CHASE1) + 2, speed=1.0, blend=1)
    D.key(ydog, "location", T(CHASE1), (-1.25, -0.55, 0))
    D.key(ydog, "rotation_euler", T(CHASE1), (0, 0, 0))
    D.key(ydog, "scale", T(CHASE1), (DOG_BIG * 0.8,) * 3)
    D.key(ydog, "scale", T(CHASE1) + 1, (DOG_BIG * 0.62,) * 3)          # back to "good boy" size next to the boss
    D.play(ydarm, "Idle_2", T(CHASE1), T(END), speed=0.8, blend=1)
    for o in (me_y, ydog):
        for fc in D._fcurves(o.animation_data.action):
            for k in fc.keyframe_points:
                k.interpolation = "LINEAR"
    for o, fr in ((me_y, T(CHASE1)), (ydog, T(CHASE1))):
        for fc in D._fcurves(o.animation_data.action):
            for k in fc.keyframe_points:
                if abs(k.co.x - (fr - 1)) < 0.5 or abs(k.co.x - (fr - 2)) < 0.5:
                    k.interpolation = "CONSTANT"

    # landlord: hidden inside until the plot twist, hands on hips, top hat + moustache
    ll, llarm, _ = person("landlord", (0.0, -0.35, 0.0), 0.0, SUIT_LL)
    ll.scale = (1.06,) * 3
    bpy.context.view_layer.update()
    top = D.bone_world(llarm, "HeadTop_End")
    head = D.bone_world(llarm, "Head")
    hat = D.cyl("hat", 0.13, 0.26, top + Vector((0, 0, 0.1)), m=ink)
    brim = D.cyl("brim", 0.21, 0.02, top + Vector((0, 0, -0.02)), m=ink)
    band = D.cyl("band", 0.133, 0.05, top + Vector((0, 0, 0.0)), m=red)
    eye_h = head.z + (top.z - head.z) * 0.35
    stache = D.box("stache", (0.17, 0.035, 0.035), (0, head.y - 0.105, eye_h - 0.07), ink, bevel=0.012)
    for o in (hat, brim, band, stache):
        attach(o, llarm, "Head")
    HIPS = {"LeftArm": (0.85, 0.15, -0.5), "LeftForeArm": (-0.8, -0.1, -0.25),
            "RightArm": (-0.85, 0.15, -0.5), "RightForeArm": (0.8, -0.1, -0.25)}
    D.play(llarm, "idle", 1, T(END), speed=0.8)
    pose_strip(llarm, ll, [(T(CHASE1), HIPS), (T(END), HIPS)], T(CHASE1), T(END), blend=1)
    D.play(llarm, "headShake", T(21.4), T(23.2), speed=1.0, blend=4)
    ll.location.y = 3.0                                    # indoors, out of sight, until 18.4
    D.key(ll, "location", 1, (0, 3.0, 0))
    D.key(ll, "location", T(CHASE1) - 1, (0, 3.0, 0))
    D.key(ll, "location", T(CHASE1), (0, -0.35, 0))

    # RENT ↑ : arrow shoots up out of the lawn, the +300% pops
    arrow = D.empty("arrow", (-2.5, -0.9, 0))
    D.box("ashaft", (0.32, 0.14, 1.6), (0, 0, 0.8), red, bevel=0.03).parent = arrow
    D.cone("ahead", 0.45, 0.6, (0, 0, 1.9), m=red, verts=4).parent = arrow
    for o in arrow.children:
        o.rotation_euler.z = math.radians(45) if o.name.startswith("ahead") else 0
    rent = D.text3d("rent", "RENT", 0.5, (0, 0.0, 2.65), white, extrude=0.06, bevel=0.015, font=FONT)
    rent.parent = arrow
    pct = D.text3d("pct", "+300%", 0.38, (-2.5, -1.2, 0.45), L.plastic("gold", H("#ffc21a"), rough=0.3),
                   extrude=0.05, bevel=0.012, font=FONT)
    key(arrow, "scale", 0, (0, 0, 0))
    key(arrow, "scale", 21.3, (0, 0, 0))
    D.overshoot(arrow, "scale", T(21.3), T(21.75), (0.2, 0.2, 0.2), (1, 1, 1), 1.25)
    key(arrow, "location", 21.3, (-2.5, -0.9, -1.0))
    key(arrow, "location", 22.1, (-2.5, -0.9, 0.6))
    D.ease_all(arrow)
    pop(pct, 22.1, 1.0, 0.3)

    # --- YARD cameras: track the run, high wide laps, push on the boss, wide payoff
    cI, lI = D.camera("I_run", 26)
    for f in range(T(RUN0), T(16.6) + 1, 3):
        x, y = chase((f - 1) / D.FPS)
        D.key(lI, "location", f, (x * 0.6, y, 1.0))
        D.key(cI, "location", f, (-2.4 + x * 0.3, y - 4.2 - 0.4 * ((f - T(RUN0)) / 60), 1.05))
    D.cut(yard, T(RUN0), cI)
    SHOTS.append((yard.name, T(RUN0), T(16.6) - 1))
    shot(yard, "J_laps", 16.6, CHASE1, (CC.x - 0.5, CC.y - 9.5, 6.0), (CC.x - 0.3, CC.y - 9.0, 5.6),
         (CC.x, CC.y, 0.2), (CC.x, CC.y + 0.2, 0.3), 30)
    shot(yard, "K_boss", CHASE1, 21.2, (0.25, -5.0, 1.45), (0.12, -2.6, 1.68), (0, -0.35, 1.45), (0, -0.35, 1.72),
         32, lens1=55, shake=0.003)
    shot(yard, "L_rent", 21.2, 24.0, (-1.0, -9.6, 1.9), (-0.9, -8.8, 2.1), (-1.0, -0.6, 1.7), (-1.0, -0.6, 1.95), 28)

# ================================================================= SHOW: the Vi3W props, on turntables
show = L.new_set("SHOW")
with L.building(show):
    col = H("#7c3aed")
    L.hdri_world(show, "studio_small_09", 0.9, rot_deg=40, backdrop=col, backdrop_strength=0.9)
    D.cyclorama(L.plastic("show_cyc", col, rough=0.75, coat=0.0), width=40, depth=30, y_wall=8, radius=4, height=20)
    D.area_light("s_key", 450, (-3, -5, 6), (0, 0, 1.0), size=4)
    D.area_light("s_rim", 280, (3, 4, 4), (0, 0, 1.0), size=3, rgb=H("#fff1dc"))
    L.post(show, bloom=0.3, vignette=0.26)
    items = ((-1.2, bread_me, 24.2, 0.62, 1.6), (0.0, panda_me, 24.85, 0.8, 0.0), (1.2, robot_me, 25.6, 0.95, 0.4))
    for x, me, t, h, rz in items:
        plinth = D.cyl("plinth", 0.42, 0.5, (x, 0, 0.25), m=white, verts=48)
        tt = D.empty("tt", (x, 0, 0.5))
        dims = max(v.co.z for v in me.vertices)
        o = clone(me, "show_" + me.name, (0, 0, 0), rz, h / dims)
        o.parent = tt
        pop(tt, t, 1.0, 0.35)
        key(tt, "rotation_euler", 24.0, (0, 0, 0))
        key(tt, "rotation_euler", END, (0, 0, math.radians(200)))
        for fc in D._fcurves(tt.animation_data.action):
            if fc.data_path == "rotation_euler":
                for k in fc.keyframe_points:
                    k.interpolation = "LINEAR"
        pop(plinth, t - 0.08, 1.0, 0.3)
    title = D.text3d("made", "MADE IN Vi3W", 0.34, (0, 0.2, 2.15), L.plastic("tw", H("#ffffff"), rough=0.3),
                     extrude=0.05, bevel=0.012, font=FONT)
    pop(title, 27.1, 1.0, 0.3)
    url = D.text3d("url", "Vi3W.in", 0.42, (0, 0.2, 1.62), L.plastic("ty", H("#ffd23f"), rough=0.3),
                   extrude=0.06, bevel=0.014, font=FONT)
    pop(url, 30.7, 1.0, 0.3)
    shot(show, "M_show", 24.0, END, (0, -5.0, 1.25), (0, -4.4, 1.2), (0, 0, 1.2), (0, 0, 1.2), 30, shake=0.003)

for s in bpy.data.scenes:
    s.frame_start, s.frame_end = 1, T(END) - 1
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(os.path.join(os.path.dirname(out), "shots.json"), "w") as fh:
    json.dump(SHOTS, fh)
with open(os.path.join(os.path.dirname(out), "meta.json"), "w") as fh:
    json.dump({"step": STEP}, fh)
bpy.ops.wm.save_as_mainfile(filepath=out)
print("STEP", round(STEP, 2), "FOOT", tuple(round(v, 2) for v in FOOT), "shots", len(SHOTS))
