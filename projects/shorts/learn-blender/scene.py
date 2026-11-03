"""blender -b -P scene.py -- <out.blend>: "What if you tried to learn Blender today?" (story 55.5 s + shared outro).

Dramatic comedy: one Xbot "you" at a desk grows fat on burgers while a 9-hour render crashes at 99 %; the fix is
Vi3W (a real Vi3W sketch → its real Vi3W model). Each set is its own scene; out/shots.json maps the shots.

  A  0.0  hook: push-in on you, lit by the monitor at night         ROOM
  B  2.4  "Day one" — tiny you vs a giant grey cube                 CUBE
  C  6.6  300 buttons / zero idea                                   CUBE
  D  9.6  donut → tire                                              DONUT
  E 15.2  day 30, 19 h a day, day/night flicker                     ROOM
  F 22.8  render: est. 9 h                                          ROOM (monitor)
  G 26.8  burgers pile up, you grow fat, +20 KG                     ROOM
  H 33.8  99 %  I 36.0 CRASHED / not saved                          ROOM
  J 39.4  six months, zero models                                   ROOM
  K 42.9  sketch → 3D model in Vi3W                                 VI3W
"""
import math, os, random, sys, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
import bpy
import director as D
import look as L
from director import T

out = sys.argv[sys.argv.index("--") + 1]
MAN = os.path.join(HERE, "assets", "Xbot.glb")
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
END = 55.5
random.seed(3)
H = D.hex_lin

base = D.reset(frames=T(END) - 1)
D.fast_eevee(base, samples=10, look="AgX - Punchy")
SHOTS = []

ink = L.plastic("ink", H("#1f2230"), rough=0.4)
white = L.plastic("white", H("#f7f4ef"), rough=0.3)
red = L.plastic("red", H("#ff3b47"), rough=0.3, emit=H("#ff3b47"), emit_strength=0.6)
yellow = L.plastic("yellow", H("#ffc21a"), rough=0.3, emit=H("#ffc21a"), emit_strength=0.3)
txt_w = L.plastic("txt_w", H("#ffffff"), rough=0.3, emit=H("#ffffff"), emit_strength=0.4)
SUIT = L.plastic("suit", H("#1e3a8a"), rough=0.35, coat=0.4)
JOINT = L.plastic("joint", H("#f5f1ea"), rough=0.3)
key = lambda o, p, t, v: D.key(o, p, T(t), v)


def txt(body, size, loc, m, rot=(math.pi / 2, 0, 0), extrude=0.05):
    return D.text3d("t_" + body[:12], body, size, loc, m, extrude=extrude, bevel=size * 0.035, font=FONT, rot=rot)


def pop(o, t, scale=1.0, dur=0.3):
    D.key(o, "scale", 1, (0, 0, 0))
    D.overshoot(o, "scale", T(t), T(t + dur), (0, 0, 0), (scale,) * 3, 1.15)


def vanish(o, t):
    D.key(o, "scale", T(t) - 1, tuple(o.scale))
    D.key(o, "scale", T(t), (0, 0, 0))


def shot(sc, name, t0, t1, loc0, loc1, at0, at1, lens0=30, lens1=None, shake=0.004, dof=None):
    c, l = D.camera(name, lens0, dof=dof)
    D.move(c, l, T(t0), T(t1), loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    D.cut(sc, T(t0), c)
    SHOTS.append((sc.name, T(t0), T(t1) - 1 if t1 < END else T(END) - 1))
    return c, l


def studio(sc, colour, hdri_strength=0.9, key_w=450, at=(0, 0, 1.2)):
    L.hdri_world(sc, "studio_small_09", hdri_strength, rot_deg=40, backdrop=colour, backdrop_strength=0.9)
    D.cyclorama(L.plastic(sc.name + "_cyc", colour, rough=0.72, coat=0.0), width=40, depth=30, y_wall=8, radius=4, height=20)
    D.area_light(sc.name + "_key", key_w, (-3, -5, 6), at, size=4)
    D.area_light(sc.name + "_rim", key_w * 0.6, (3, 4, 4), at, size=3, rgb=H("#fff1dc"))
    L.post(sc)


def rotz(v, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


def aim_limb(arm, n, world_dir, frame):
    """Joint → child joint along world_dir (Xbot glTF bone tails are arbitrary, so D.aim misses)."""
    pb = D.bone(arm, n)
    bpy.context.view_layer.update()
    cur = (pb.children[0].head - pb.head).normalized()
    tgt = (arm.matrix_world.to_3x3().inverted() @ Vector(world_dir)).normalized()
    m = pb.matrix.copy()
    nm = (cur.rotation_difference(tgt).to_matrix() @ m.to_3x3()).to_4x4()
    nm.translation = m.translation
    pb.matrix = nm
    bpy.context.view_layer.update()
    pb.keyframe_insert("rotation_quaternion", frame=frame)


def pose_strip(arm, root, keys, f0, f1, blend=4):
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


def man(name, loc, yaw=0.0):
    r, arm, body = D.import_char(MAN, name)
    r.location, r.rotation_euler = loc, (0, 0, yaw)
    for b in body:
        is_joint = "joint" in (b.data.materials[0].name if b.data.materials else "").lower()
        D.give(b, JOINT if is_joint else SUIT)
    return r, arm, body


SIT = {"LeftUpLeg": (0.12, -1, 0.02), "RightUpLeg": (-0.12, -1, 0.02), "LeftLeg": (0, -0.15, -1), "RightLeg": (0, -0.15, -1),
       "Spine": (0, -0.12, 1), "LeftArm": (0.35, -0.75, -0.55), "RightArm": (-0.35, -0.75, -0.55),
       "LeftForeArm": (-0.1, -1, 0.05), "RightForeArm": (0.1, -1, 0.05)}
SLUMP = SIT | {"Spine": (0, -0.45, 1), "Neck": (0, -0.6, 1), "Head": (0, -0.8, 0.6),
               "LeftArm": (0.2, -0.1, -1), "RightArm": (-0.2, -0.1, -1), "LeftForeArm": (0.05, -0.3, -1),
               "RightForeArm": (-0.05, -0.3, -1)}
ARMS_UP = SIT | {"LeftArm": (0.5, -0.2, 1), "RightArm": (-0.5, -0.2, 1), "LeftForeArm": (0.3, -0.2, 1),
                 "RightForeArm": (-0.3, -0.2, 1)}


def burger(name, loc, s=1.0):
    g = D.empty(name, loc)
    bun = BUN
    for nm, r, h, z, m in (("bb", 0.12, 0.05, 0.025, bun), ("pt", 0.13, 0.035, 0.065, PATTY), ("ch", 0.135, 0.01, 0.087, yellow),
                           ("lt", 0.14, 0.012, 0.097, LETTUCE)):
        D.cyl(nm, r * s, h * s, (0, 0, z * s), m=m, verts=24).parent = g
    top = D.sphere("bt", 0.12 * s, (0, 0, 0.105 * s), bun, seg=20, rings=10)
    top.scale = (1, 1, 0.55)
    top.parent = g
    return g


BUN = L.plastic("bun", H("#e9a23b"), rough=0.5, coat=0.2)
PATTY = L.plastic("patty", H("#5a3424"), rough=0.7)
LETTUCE = L.plastic("lettuce", H("#5cc94a"), rough=0.5)

# ================================================================= ROOM: messy night bedroom, desk, monitor glow
room = L.new_set("ROOM", main=True)
L.hdri_world(room, "studio_small_09", 0.06, backdrop=H("#05070f"))
D.room("bedroom", (0, 0, 2.5), (9, 9, 5), L.pbr("rwall", "plastered_wall", scale=0.6, tint=H("#3a2f7a"), tint_amount=0.9, normal=0.5))
D.box("rfloor", (9, 9, 0.02), (0, 0, 0.0), L.pbr("rfl", "laminate_floor_02", scale=0.8, rough_mul=0.7))
wood = L.pbr("deskwood", "wood_table_001", scale=1.5)
DY = -0.8                                              # desk front edge in front of you (you face -Y)
D.box("desk", (1.8, 0.8, 0.06), (0, DY - 0.2, 0.74), wood, bevel=0.01)
for x in (-0.85, 0.85):
    D.box("dleg", (0.06, 0.7, 0.72), (x, DY - 0.2, 0.36), ink)
D.box("chair_seat", (0.55, 0.55, 0.08), (0, 0.05, 0.48), L.plastic("chair", H("#e11d48"), rough=0.4))
D.box("chair_back", (0.55, 0.08, 0.7), (0, 0.33, 0.85), L.plastic("chair2", H("#e11d48"), rough=0.4))
D.cyl("chair_post", 0.04, 0.44, (0, 0.05, 0.22), m=ink)
D.box("mon_body", (1.0, 0.05, 0.6), (0, DY - 0.45, 1.2), ink, bevel=0.01)
D.box("mon_stand", (0.08, 0.05, 0.4), (0, DY - 0.5, 0.95), ink)
scr_m = D.mat("screen", H("#3a3a3a"), rough=0.2, emit=H("#3d3f44"), emit_strength=2.2)
scr = D.box("screen", (0.94, 0.01, 0.54), (0, DY - 0.42, 1.2), scr_m)
em = scr_m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
for t, c in ((0, "#3d3f44"), (36.0, "#3d3f44"), (36.05, "#ff1e2d"), (39.3, "#ff1e2d"), (39.35, "#14161c")):
    em.default_value = (*H(c), 1)
    em.keyframe_insert("default_value", frame=max(1, T(t)))
D.box("cube_ui", (0.14, 0.012, 0.14), (0, DY - 0.415, 1.25), D.mat("cubeui", H("#9a9a9a"), emit=H("#b0b0b0"), emit_strength=1.0))
D.box("orange_ui", (0.94, 0.012, 0.04), (0, DY - 0.415, 1.45), D.mat("ui_or", H("#ff8a1f"), emit=H("#ff8a1f"), emit_strength=2.0))
D.box("keyboard", (0.55, 0.18, 0.025), (0, DY + 0.05, 0.78), ink, bevel=0.005)
D.area_light("monglow", 120, (0, DY - 0.3, 1.2), (0, 0.2, 1.1), size=0.9, rgb=H("#cfd8ff"))
D.area_light("rkey", 160, (-2.2, -2.6, 2.8), (0, -0.2, 1.0), size=2.5, rgb=H("#8fa6ff"))
D.area_light("rrim", 200, (1.8, 2.2, 2.4), (0, 0, 1.2), size=1.5, rgb=H("#ff6ad5"))
# window: day/night flicker during "day thirty"
win_m = D.mat("winsky", H("#0b1530"), rough=1, emit=H("#132657"), emit_strength=0.8)
D.box("winframe", (1.5, 0.1, 1.2), (-2.2, -4.45, 2.2), white)
D.box("winsky", (1.3, 0.05, 1.0), (-2.2, -4.4, 2.2), win_m)
we = win_m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
for i in range(16):
    t = 15.3 + i * 0.45
    we.default_value = (*H("#ffd88a" if i % 2 else "#132657"), 1)
    we.keyframe_insert("default_value", frame=T(t))
we.default_value = (*H("#132657"), 1)
we.keyframe_insert("default_value", frame=T(15.3 + 16 * 0.45))
# wall clock spinning through days
D.cyl("wclock", 0.35, 0.06, (1.8, -4.45, 2.6), (math.pi / 2, 0, 0), m=white, verts=48)
whand = D.empty("whand", (1.8, -4.4, 2.6))
D.box("whand_m", (0.04, 0.02, 0.28), (0, 0, 0.12), ink).parent = whand
key(whand, "rotation_euler", 15.2, (0, 0, 0))
key(whand, "rotation_euler", 22.8, (0, math.radians(-30 * 360), 0))
# you
you, yarm, ybody = man("you", (0, 0, -0.42), 0.0)
pose_strip(yarm, you, [(1, SIT), (T(23.4), SIT), (T(23.9), ARMS_UP), (T(24.4), SIT), (T(36.0), SIT), (T(36.4), ARMS_UP),
                       (T(37.6), ARMS_UP), (T(38.3), SLUMP), (T(END), SLUMP)], 1, T(END), blend=1)
for i in range(7):                                        # 19 h a day: fast typing bob on the "sit there" beat
    key(you, "location", 16.4 + i * 0.25, (0, 0, -0.42 + (0.012 if i % 2 else 0)))
# grow fat: 28.4 → 33.2
key(you, "scale", 28.4, (1, 1, 1))
key(you, "scale", 29.4, (1.12, 1.15, 1.02))
key(you, "scale", 30.7, (1.25, 1.3, 1.03))
key(you, "scale", 33.2, (1.7, 1.75, 1.05))
D.ease_all(you)
# burgers: 1 at 28.5, 1 at 29.6, 14 rapid from 30.75
spots = [(-0.55, DY - 0.05, 0.77), (0.55, DY - 0.05, 0.77)]
for i in range(14):
    spots.append((random.uniform(-0.8, 0.8), DY + random.uniform(-0.55, 0.0), 0.77 + (0.14 if i > 7 else 0)))
for i, p in enumerate(spots):
    b = burger(f"burger{i}", p, s=1.0)
    b.rotation_euler = (0, 0, random.uniform(0, 6))
    pop(b, 28.5 if i == 0 else 29.6 if i == 1 else 30.75 + (i - 2) * 0.05, dur=0.2)
# floating labels near the monitor
lbl = {}
for k, (body, size, loc, m) in {
    "19": ("19 HRS/DAY", 0.2, (0, DY - 0.55, 1.75), yellow),
    "est": ("EST: 9:00:00", 0.12, (0, DY - 0.41, 1.33), txt_w),
    "kg": ("+20 KG", 0.3, (0.9, -0.2, 1.75), red),
    "99": ("99%", 0.16, (0, DY - 0.41, 1.03), txt_w),
    "crash": ("CRASHED", 0.17, (0, DY - 0.41, 1.22), txt_w),
    "save": ("NOT SAVED", 0.12, (0, DY - 0.41, 1.05), yellow),
    "zero": ("0 MODELS", 0.28, (0, DY - 0.5, 1.85), red),
}.items():
    on_screen = k in ("est", "99", "crash", "save")                      # screen text faces you (+Y)
    lbl[k] = txt(body, size, loc, m, rot=(math.pi / 2, 0, math.pi if on_screen else 0), extrude=0.01 if on_screen else 0.04)
pop(lbl["19"], 17.05)
vanish(lbl["19"], 19.6)
pop(lbl["est"], 25.58)
vanish(lbl["est"], 36.0)
pop(lbl["kg"], 32.69)
lbl["kg"].rotation_euler = (math.pi / 2, 0, math.radians(40))
vanish(lbl["kg"], 33.8)
pop(lbl["99"], 34.26)
vanish(lbl["99"], 36.0)
pop(lbl["crash"], 36.68)
pop(lbl["save"], 38.43)
vanish(lbl["crash"], 39.35)
vanish(lbl["save"], 39.35)
pop(lbl["zero"], 41.61)
# render progress bar on the screen
D.box("bar_bg", (0.7, 0.012, 0.05), (0, DY - 0.41, 1.12), D.mat("barbg", H("#22324d"), rough=0.6))
bar = D.empty("bar", (-0.35, DY - 0.405, 1.12))
D.box("bar_f", (0.7, 0.014, 0.05), (0.35, 0, 0), D.mat("barf", H("#ff8a1f"), emit=H("#ff8a1f"), emit_strength=2.5)).parent = bar
key(bar, "scale", 1, (0.001, 1, 1))
key(bar, "scale", 23.65, (0.001, 1, 1))
key(bar, "scale", 34.4, (0.99, 1, 1))
key(bar, "scale", 36.0, (0.99, 1, 1))
key(bar, "scale", 36.05, (0.001, 1, 1))
D.ease_all(bar, "LINEAR")
L.post(room, bloom=0.6, bloom_threshold=0.75, vignette=0.32)

# ================================================================= CUBE: grey void, giant default cube, 300 buttons
cube_sc = L.new_set("CUBE")
with L.building(cube_sc):
    studio(cube_sc, H("#474a52"), key_w=380, at=(0, 2, 2))
    giant = D.box("giant_cube", (4, 4, 4), (0, 3.5, 2.0), L.plastic("grey", H("#9a9ca3"), rough=0.5), bevel=0.02)
    tiny, tarm, _ = man("tiny", (0, -0.6, 0), math.pi)
    D.play(tarm, "idle", 1, T(END))
    btn_ms = [L.plastic(f"btn{i}", H(c), rough=0.35, emit=H(c), emit_strength=0.6)
              for i, c in enumerate(("#ff8a1f", "#4ecdc4", "#ffd93d", "#ff6b6b", "#54a0ff", "#e5e7eb"))]
    k = 0
    for r in range(15):
        for c in range(20):
            b = D.box("btn", (0.28, 0.08, 0.2), (-3.8 + c * 0.4, 1.4, 0.4 + r * 0.3), random.choice(btn_ms), bevel=0.02)
            pop(b, 6.7 + random.uniform(0, 0.9), dur=0.15)
            k += 1
    n300 = txt("300", 1.0, (0, 1.2, 5.0), yellow)
    pop(n300, 6.82)
    qm = txt("?", 0.6, (0, -0.6, 2.3), txt_w)
    pop(qm, 8.12)
    key(giant, "rotation_euler", 2.4, (0, 0, math.radians(30)))
    key(giant, "rotation_euler", 6.6, (0, 0, math.radians(42)))
    shot(cube_sc, "B_cube", 2.4, 6.6, (1.2, -4.8, 0.5), (0.6, -3.6, 0.7), (0, 2, 2.2), (0, 2, 2.6), 22, shake=0.005)
    shot(cube_sc, "C_buttons", 6.6, 9.6, (0.0, -6.5, 2.8), (0.0, -5.4, 2.7), (0, 1.4, 2.6), (0, 1.0, 2.5), 26)

# ================================================================= DONUT: pink studio, donut → tire
donut_sc = L.new_set("DONUT")
with L.building(donut_sc):
    studio(donut_sc, H("#ff7eb6"), key_w=450, at=(0, 0, 1.0))
    D.cyl("pod", 0.75, 0.6, (0, 0, 0.3), m=white, verts=48)
    dough = L.plastic("dough", H("#d9a066"), rough=0.6)
    icing = L.plastic("icing", H("#ff4fa3"), rough=0.25, coat=0.6)
    donut = D.empty("donut", (0, 0, 0.85))
    D.torus("dough", 0.38, 0.18, (0, 0, 0), m=dough).parent = donut
    ic = D.torus("icing", 0.38, 0.17, (0, 0, 0.04), m=icing)
    ic.scale = (1.02, 1.02, 0.8)
    ic.parent = donut
    for i in range(18):
        a = random.uniform(0, math.tau)
        sp = D.box("spr", (0.05, 0.012, 0.012), (0.38 * math.cos(a), 0.38 * math.sin(a), 0.2),
                   L.plastic(f"spr{i}", H(random.choice(("#ffd93d", "#4ecdc4", "#ffffff", "#54a0ff"))), rough=0.3))
        sp.rotation_euler = (0, 0, random.uniform(0, 3))
        sp.parent = donut
    tire = D.empty("tire", (0, 0, 0.95))
    D.torus("rubber", 0.4, 0.26, (0, 0, 0), m=L.plastic("rubber", H("#141414"), rough=0.85, coat=0.0)).parent = tire
    D.cyl("rim", 0.2, 0.3, (0, 0, 0), m=L.pbr("chrome", "metal_plate", scale=2, rough_mul=0.4), verts=32).parent = tire
    for o in (donut, tire):
        o.rotation_euler = (math.radians(60), 0, 0)
        key(o, "rotation_euler", 9.6, (math.radians(60), 0, 0))
        key(o, "rotation_euler", 15.2, (math.radians(60), 0, math.radians(120)))
    pop(donut, 10.9)
    vanish(donut, 13.6)
    pop(tire, 13.6, dur=0.25)
    four = txt("4 HOURS LATER", 0.32, (0, 0.6, 2.1), txt_w)
    pop(four, 12.45)
    shot(donut_sc, "D_donut", 9.6, 15.2, (0, -3.6, 1.6), (0, -2.8, 1.45), (0, 0, 1.0), (0, 0, 1.1), 30)

# ================================================================= VI3W: bright studio, real Vi3W sketch → real Vi3W model
v_sc = L.new_set("VI3W")
with L.building(v_sc):
    studio(v_sc, H("#22d3ee"), key_w=500, at=(0, 0, 1.3))
    img = bpy.data.images.load(os.path.join(HERE, "assets", "robot0.jpeg"))
    pm = bpy.data.materials.new("sketch")
    pm.use_nodes = True
    tn = pm.node_tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    bs = pm.node_tree.nodes["Principled BSDF"]
    pm.node_tree.links.new(tn.outputs["Color"], bs.inputs["Base Color"])
    pm.node_tree.links.new(tn.outputs["Color"], bs.inputs["Emission Color"])
    bs.inputs["Emission Strength"].default_value = 0.35
    bs.inputs["Roughness"].default_value = 0.8
    ar = img.size[0] / max(1, img.size[1])
    bpy.ops.mesh.primitive_plane_add(size=1)
    paper = bpy.context.active_object
    D.adopt(paper)
    paper.data.materials.append(pm)
    paper.scale = (1.3 * ar, 1.3, 1)
    paper.location = (-0.9, 0, 1.35)
    paper.rotation_euler = (math.pi / 2, 0, math.radians(12))
    D.box("easel", (0.08, 0.08, 1.4), (-0.9, 0.12, 0.7), wood)
    pop(paper, 44.3)
    D.cyl("vpod", 0.75, 0.5, (0.9, 0, 0.25), m=white, verts=48)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, "assets", "robot.glb"))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        D.adopt(o)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = 1.5 / max(hi - lo)
    piv = D.empty("robot", (0.9, 0, 0.5))
    for o in new:
        if o.parent is None:
            o.parent = piv
            o.location = (o.location - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)))
    piv.scale = (s,) * 3
    D.key(piv, "scale", 1, (0, 0, 0))
    D.overshoot(piv, "scale", T(47.75), T(48.3), (0, 0, 0), (s,) * 3, 1.15)
    key(piv, "rotation_euler", 47.75, (0, 0, math.radians(-40)))
    key(piv, "rotation_euler", END, (0, 0, math.radians(320)))
    D.ease_last(piv, "LINEAR")
    arrow = txt(">", 0.5, (0.0, -0.3, 1.4), yellow)
    pop(arrow, 47.0)
    vlogo = txt("Vi3W", 0.55, (0, 0.3, 2.65), L.plastic("vlogo", H("#ffffff"), emit=H("#ffffff"), emit_strength=0.8))
    pop(vlogo, 45.87)
    sec = txt("< 30 SEC", 0.36, (0.9, -0.4, 0.15), red, extrude=0.03)
    pop(sec, 50.18)
    vanish(sec, 51.45)
    # no cube / no crashes / no burgers: each pops in then gets a red X
    grey = L.plastic("grey2", H("#9a9ca3"), rough=0.5)
    items = [D.box("nocube", (0.35, 0.35, 0.35), (0, 0, 0), grey, bevel=0.01),
             txt("CRASH", 0.16, (0, 0, -0.08), ink, extrude=0.03), burger("noburger", (0, 0, -0.12), s=1.6)]
    for i, (o, t) in enumerate(zip(items, (51.5, 52.7, 53.9))):
        g = D.empty("no", (-0.9 + i * 0.9, -0.75, 0.25))
        o.parent = g
        o.location = (0, 0, 0) if i == 0 else o.location
        xr = D.empty("X", (0, -0.25, 0.0))
        xr.parent = g
        for a in (45, -45):
            b = D.box("xbar", (0.08, 0.04, 0.6), (0, 0, 0), red, bevel=0.02)
            b.rotation_euler = (0, math.radians(a), 0)
            b.parent = xr
        pop(g, t, dur=0.2)
        pop(xr, t + 0.35, dur=0.2)
    happy, harm, _ = man("happy", (2.0, 0.4, 0), math.radians(-30))
    D.play(harm, "idle", 1, T(48.0))
    D.play(harm, "agree", T(48.0), T(END), speed=1.1)
    L.post(v_sc, bloom=0.4)
    shot(v_sc, "K_sketch", 42.9, 47.6, (-0.6, -3.6, 1.5), (-0.4, -3.2, 1.45), (-0.7, 0, 1.3), (-0.3, 0, 1.3), 30)
    shot(v_sc, "K_model", 47.6, 51.4, (0.2, -4.4, 1.7), (0.4, -3.9, 1.6), (0.2, 0, 1.3), (0.5, 0, 1.2), 28)
    shot(v_sc, "K_nos", 51.4, END, (0.3, -4.6, 1.5), (0.2, -4.2, 1.35), (0.1, 0, 0.8), (0.1, 0, 0.75), 28)

# ================================================================= ROOM shots
SIDE = lambda d: (2.2 * d, -2.4 * d, 1.5)
shot(room, "A_hook", 0.0, 2.4, (2.6, -3.6, 1.9), (1.4, -2.1, 1.35), (0, -0.3, 1.0), (0, -0.3, 1.05), 26, 32, shake=0.006)
shot(room, "E_day30", 15.2, 19.6, (-2.8, -3.4, 2.5), (-2.4, -2.9, 2.2), (0, -0.5, 1.2), (0, -0.6, 1.3), 24)
shot(room, "E2_alone", 19.6, 22.8, (0.0, 3.2, 3.2), (0.0, 2.6, 2.6), (0, -0.4, 1.0), (0, -0.4, 1.0), 26)
shot(room, "F_render", 22.8, 26.8, (0.75, -0.45, 1.55), (0.55, -0.55, 1.45), (0, DY - 0.42, 1.2), (0, DY - 0.42, 1.2), 30)
shot(room, "G_burgers", 26.8, 33.8, (2.3, -2.6, 1.8), (1.6, -2.1, 1.6), (0, -0.4, 0.95), (0, -0.3, 1.05), 26, 22)
shot(room, "H_99", 33.8, 36.0, (0.5, -0.55, 1.3), (0.4, -0.65, 1.25), (0, DY - 0.42, 1.12), (0, DY - 0.42, 1.12), 32, shake=0.003)
shot(room, "I_crash", 36.0, 39.4, (0.8, -0.4, 1.6), (0.7, -0.5, 1.55), (0, DY - 0.42, 1.18), (0, DY - 0.42, 1.18), 26, shake=0.02)
shot(room, "J_months", 39.4, 42.9, (1.4, -2.2, 1.5), (2.8, -3.6, 2.4), (0, -0.4, 1.1), (0, -0.4, 1.3), 28, 24)

SHOTS.sort(key=lambda x: x[1])
json.dump(SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(SHOTS), "scenes", [s.name for s in bpy.data.scenes])
