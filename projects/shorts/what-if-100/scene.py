"""blender -b -P scene.py -- <out.blend>: "What if a man tried to sleep with 100 women in one day?" (75.5 s).

Non-explicit by design: mannequin cast, everything happens behind a closed door, the science is told with
infographic sets. Every set is its own Blender scene (own HDRI/world, own lights, own shadow pool, own post),
and out/shots.json maps each shot to (scene, first frame, last frame) for render_shots().

Look: real sky + Poly Haven PBR textures outdoors; saturated single-colour studios (HDRI-lit, glossy floor) for
the infographics; dark neon x-ray room; warm/moonlit bedroom. AgX Punchy + bloom, dispersion and vignette.

  A  0.0  hook: crane down the 100-woman queue to the door        DOOR
  B  3.4  "1,440 minutes"   C 7.35 "÷100 → 14 minutes"          CLOCK
  D 11.6  no sleep / no food / no breaks                          ICONS
  E 15.0  "Woman number 1? Easy."                                  DOOR
  F 17.9  brakes slam (gauge)                                      GAUGE
  G 21.3  refractory period (x-ray man)  G2 26.7 "?"               XRAY
  H 30.0  woman 5, behind schedule                                 DOOR
  I 34.4  the tank runs dry                                        TANK
  J 40.9  ~100 kcal / 130 bpm         J3 46.9 every 14 min         BIO, STAIRS
  K 49.4  "the real danger"                                        DOOR
  L 51.9  1 in 5 → 20 of 100                                       GRID
  M 61.2  "a handful. Maybe less."  N 66.3 the rest go home        DOOR
  O 68.9  he sleeps for a very long time                           BED
"""
import json, math, os, random, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
import bmesh
import bpy
import director as D
import look as L
from director import T

out = sys.argv[sys.argv.index("--") + 1]
WOMAN = os.path.join(HERE, "..", "3d-2d-hat", "assets", "Michelle.glb")
MAN = os.path.join(HERE, "assets", "Xbot.glb")
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
END = 75.5
random.seed(7)
H = D.hex_lin

base = D.reset(frames=T(END) - 1)
D.fast_eevee(base, samples=16, look="AgX - Punchy")
SHOTS = []                                             # (scene, f0, f1)

# ---------------------------------------------------------------- shared materials
ink = L.plastic("ink", H("#1f2230"), rough=0.4)
white = L.plastic("white", H("#f7f4ef"), rough=0.3)
red = L.plastic("red", H("#ff3b47"), rough=0.3, emit=H("#ff3b47"), emit_strength=0.25)
blue = L.plastic("blue", H("#2563eb"), rough=0.3)
yellow = L.plastic("yellow", H("#ffc21a"), rough=0.3)
txt_w = L.plastic("txt_w", H("#ffffff"), rough=0.3, emit=H("#ffffff"), emit_strength=0.2)
VIVID = ["#ff6b6b", "#4ecdc4", "#ffd93d", "#6c5ce7", "#ff9f43", "#1dd1a1", "#54a0ff", "#f368e0", "#ff7eb6"]


def txt(body, size, loc, m, rot=(math.pi / 2, 0, 0), extrude=0.05):
    return D.text3d("t_" + body[:12], body, size, loc, m, extrude=extrude, bevel=size * 0.035, font=FONT, rot=rot)


def pop(o, t, scale=1.0, dur=0.3):
    D.key(o, "scale", 1, (0, 0, 0))
    D.overshoot(o, "scale", T(t), T(t + dur), (0, 0, 0), (scale,) * 3, 1.15)


def hide_after(o, t):
    o.keyframe_insert("hide_render", frame=T(t) - 1)
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=T(t))
    o.hide_render = False


def shot(sc, name, t0, t1, loc0, loc1, at0, at1, lens0=30, lens1=None, shake=0.004, dof=None):
    c, l = D.camera(name, lens0, dof=dof)
    D.move(c, l, T(t0), T(t1), loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    D.cut(sc, T(t0), c)
    SHOTS.append((sc.name, T(t0), T(t1) - 1 if t1 < END else T(END) - 1))
    return c, l


def studio(sc, colour, hdri_strength=0.9, rough=0.72, key=450, key_from=(-3, -5, 6), at=(0, 0, 1.2), x=0.0):
    """Saturated single-colour studio: coloured sweep + soft key; HDRI gives the glossy reflections."""
    L.hdri_world(sc, "studio_small_09", hdri_strength, rot_deg=40, backdrop=colour, backdrop_strength=0.9)
    cyc = D.cyclorama(L.plastic(sc.name + "_cyc", colour, rough=rough, coat=0.0), width=40, depth=30, y_wall=8,
                      radius=4, height=20)
    cyc.location.x = x
    D.area_light(sc.name + "_key", key, (x + key_from[0], key_from[1], key_from[2]), (x + at[0], at[1], at[2]), size=4)
    D.area_light(sc.name + "_rim", key * 0.6, (x + 3, 4, 4), (x + at[0], at[1], at[2]), size=3, rgb=H("#fff1dc"))
    L.post(sc)


# ---------------------------------------------------------------- cast: one woman baked into 3 poses for the crowd
w_root, w_rig, w_body = D.import_char(WOMAN, "w")
crowd_mat = D.tint_mat("crowd", tex_from=w_body[0].data.materials[0], lo=0.38, rough=0.5)
POSES = [
    {"LeftArm": (-0.15, 0, -1), "LeftForeArm": (-0.1, -0.1, -1), "RightArm": (0.15, 0, -1), "RightForeArm": (0.1, -0.1, -1)},
    {"LeftArm": (-0.6, 0.1, -0.8), "LeftForeArm": (0.5, -0.1, -0.4), "RightArm": (0.15, 0, -1), "RightForeArm": (0.1, -0.15, -1),
     "Head": (0.12, -0.1, 1)},
    {"LeftArm": (-0.15, 0, -1), "LeftForeArm": (-0.05, -0.2, -1), "RightArm": (0.25, -0.2, -1), "RightForeArm": (-0.1, -1, 0.35),
     "RightHand": (-0.2, -1, 0.5), "Head": (0, -0.35, 1)},
]
meshes = []
for i, p in enumerate(POSES):
    for pb in w_rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    for n, d in p.items():
        D.aim(w_rig, n, d)
    me = D.bake(w_rig, w_body, f"woman_pose{i}")
    me.materials.append(crowd_mat)
    meshes.append(me)
for o in [w_root, w_rig] + w_body:
    bpy.data.objects.remove(o)


def woman(loc, yaw, k=None, color=None, scale=None):
    o = D.link(bpy.data.objects.new("woman", meshes[(k if k is not None else random.randrange(3))]))
    o.location, o.rotation_euler = loc, (0, 0, yaw)
    o.scale = (scale or random.uniform(0.95, 1.05),) * 3
    o.color = (*H(color or random.choice(VIVID)), 1)
    return o


SUIT = L.plastic("suit", H("#1e3a8a"), rough=0.35, coat=0.4)
JOINT = L.plastic("joint", H("#f5f1ea"), rough=0.3)


def man(name, loc, yaw=0.0, mat=None):
    r, arm, body = D.import_char(MAN, name)
    r.location, r.rotation_euler = loc, (0, 0, yaw)
    for b in body:
        is_joint = "joint" in (b.data.materials[0].name if b.data.materials else "").lower()
        D.give(b, mat or (JOINT if is_joint else SUIT))
    return r, arm, body


key = lambda o, p, t, v: D.key(o, p, T(t), v)

# ================================================================= DOOR: a real street — sky, lawn, paving, house
door_sc = L.new_set("DOOR", main=True)
L.hdri_world(door_sc, "kloofendal_48d_partly_cloudy_puresky", 1.0, rot_deg=150)
D.sun("sun", 3.2, (0.5, 0.65, -0.62), rgb=H("#fff0dc"), angle=2.5)
lawn = D.box("lawn", (260, 260, 0.1), (0, -40, -0.05), L.pbr("lawn", "leafy_grass", scale=0.45, tint=H("#7bc96f"),
                                                                tint_amount=0.35))
D.box("plaza", (13, 60, 0.04), (0, -29.5, 0.0), L.pbr("paving", "pavement_02", scale=1.1, rough_add=0.05))
plaster = L.pbr("house_paint", "plastered_wall", scale=0.6, tint=H("#ffb3a7"), tint_amount=0.85, normal=0.6)
trim = L.plastic("trim", H("#fffaf2"), rough=0.4)
D.box("house", (8, 2, 5.2), (0, 1.0, 2.6), plaster)
D.box("plinth", (8.05, 2.05, 0.55), (0, 1.0, 0.275), L.pbr("brick", "red_brick_03", scale=1.2))
D.box("roof", (8.7, 2.7, 0.38), (0, 0.9, 5.35), L.plastic("roof", H("#2b2d42"), rough=0.5), bevel=0.04)
D.box("doorway", (1.2, 0.2, 2.3), (0, -0.02, 1.15), L.plastic("inside", H("#2a1b1f"), rough=0.9))
for x in (-0.68, 0.68):
    D.box("jamb", (0.14, 0.16, 2.45), (x, -0.06, 1.22), trim, bevel=0.01)
D.box("lintel", (1.5, 0.16, 0.16), (0, -0.06, 2.42), trim, bevel=0.01)
D.box("step", (2.0, 0.6, 0.16), (0, -0.3, 0.08), L.pbr("step", "concrete_floor_02", scale=1.0), bevel=0.01)
hinge = D.empty("hinge", (-0.6, -0.08, 0.14))
door = D.box("door", (1.18, 0.07, 2.22), (0.59, 0, 1.11), L.plastic("doorc", H("#1d4ed8"), rough=0.25, coat=0.6), bevel=0.012)
door.parent = hinge
D.cyl("knob", 0.045, 0.08, (1.05, -0.06, 1.05), (math.pi / 2, 0, 0), m=L.plastic("brass", H("#e0b04a"), rough=0.2)).parent = hinge
glow = L.plastic("window", H("#ffe2a8"), rough=0.15, emit=H("#ffcf70"), emit_strength=1.2)
for x in (-2.6, 2.6):
    D.box("window", (1.3, 0.12, 1.3), (x, -0.02, 2.6), glow)
    D.box("wframe", (1.5, 0.14, 0.12), (x, -0.07, 1.9), trim, bevel=0.01)
    D.box("wframe_t", (1.5, 0.14, 0.12), (x, -0.07, 3.3), trim, bevel=0.01)
D.box("sign", (1.9, 0.12, 0.72), (0, -0.08, 3.25), ink, bevel=0.06)
counter = [txt(t, 0.42, (0, -0.16, 3.1), txt_w) for t in ("0/100", "1/100", "5/100", "6/100", "?/100")]
D.swap([(counter[0], 1), (counter[1], T(17.0)), (counter[2], T(29.9)), (counter[3], T(64.3)), (counter[4], T(65.4))])
for x, rz in ((-1.25, 0), (1.25, 90)):
    L.prop("potted_plant_02", (x, -0.45, 0.0), rot_z=rz, scale=1.4)
for i, (x, y, s_) in enumerate(((-6.5, -1.5, 1.3), (6.8, -2.5, 1.1), (-8.5, -9, 1.4), (9, -13, 1.2), (-9, -22, 1.3),
                                (9.5, -27, 1.4), (-10, -35, 1.2), (10, -42, 1.3))):
    L.toy_tree((x, y, 0), scale=s_, seed=i)
for i in range(26):                                       # hedges along the plaza edges
    side = 1 if i % 2 else -1
    L.bush((side * random.uniform(6.9, 7.6), -2.5 - i * 1.8, 0), scale=random.uniform(0.9, 1.3), seed=100 + i)
key(hinge, "rotation_euler", 0, (0, 0, math.radians(-100)))
key(hinge, "rotation_euler", 16.3, (0, 0, math.radians(-100)))
key(hinge, "rotation_euler", 16.75, (0, 0, 0))
key(hinge, "rotation_euler", 29.8, (0, 0, 0))
key(hinge, "rotation_euler", 29.9, (0, 0, math.radians(-100)))
D.ease_all(hinge)

D.cyl("wclock", 0.42, 0.08, (-2.6, -0.12, 4.15), (math.pi / 2, 0, 0), m=white, verts=48)
D.cyl("wclock_rim", 0.46, 0.06, (-2.6, -0.09, 4.15), (math.pi / 2, 0, 0), m=ink, verts=48)
whand = D.empty("whand", (-2.6, -0.18, 4.15))
D.box("whand_m", (0.04, 0.02, 0.34), (0, 0, 0.15), ink).parent = whand
key(whand, "rotation_euler", 30.0, (0, 0, 0))
key(whand, "rotation_euler", 34.4, (0, math.radians(-4 * 360), 0))
late = txt("BEHIND SCHEDULE", 0.3, (-1.3, -0.07, 4.8), red, extrude=0.03)
pop(late, 33.2)
late.keyframe_insert("hide_render", frame=T(34.4) - 1)
late.hide_render = True
late.keyframe_insert("hide_render", frame=T(34.4))

pts = [Vector((4.2 * math.sin(u / 7.5) * min(1, u / 5), -1.25 - u * 0.62, 0)) for u in (i * 0.02 for i in range(4000))]
queue_pts, last, acc = [pts[0]], pts[0], 0.0
for p in pts[1:]:
    acc += (p - last).length
    last = p
    if acc >= 0.72:
        queue_pts.append(p)
        acc = 0.0
    if len(queue_pts) == 100:
        break
queue = []
for i, p in enumerate(queue_pts):
    ahead = queue_pts[i - 1] if i else Vector((0, 0.5, 0))
    yaw = math.atan2(-(ahead - p).x, (ahead - p).y)
    jitter = Vector((random.uniform(-0.12, 0.12), random.uniform(-0.08, 0.08), 0))
    queue.append(woman(p + jitter, yaw + random.uniform(-0.3, 0.3)))
q0 = queue[0]
D.key(q0, "location", T(15.25), q0.location.copy())
D.key(q0, "location", T(16.2), Vector((0, 0.35, 0)))
D.ease_all(q0)
for i, t in ((0, 16.3), (1, 29.9), (2, 29.9), (3, 29.9), (4, 29.9), (5, 64.3)):
    o = queue[i]
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=T(t) - 1)
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=T(t))
for i, o in enumerate(queue[6:60]):
    t = 66.5 + i * 0.045
    yaw = o.rotation_euler.z
    D.key(o, "rotation_euler", T(t), (0, 0, yaw))
    D.key(o, "rotation_euler", T(t + 0.35), (0, 0, yaw + math.pi))
    D.key(o, "location", T(t + 0.2), o.location.copy())
    D.key(o, "location", T(t + 2.6), o.location + Vector((random.uniform(-1, 1), -4.5, 0)))
    D.ease_all(o)

you, yarm, _ = man("you", (1.35, -0.95, 0), 0.0)
D.play(yarm, "idle", 1, T(15.4))
D.play(yarm, "agree", T(15.4), T(17.6), speed=1.2)
key(you, "rotation_euler", 15.9, (0, 0, 0))
key(you, "rotation_euler", 16.15, (0, 0, math.radians(150)))
key(you, "location", 15.9, (1.35, -0.95, 0))
key(you, "location", 16.6, (0.35, 0.3, 0))
key(you, "location", 29.85, (0.35, 0.3, 0))
key(you, "location", 29.9, (1.35, -0.95, 0))
key(you, "rotation_euler", 29.9, (0, 0, math.radians(-10)))
D.play(yarm, "sad_pose", T(29.9), T(END))
key(you, "rotation_euler", 64.9, (0, 0, math.radians(-10)))
key(you, "rotation_euler", 65.45, (math.radians(84), 0, math.radians(-10)))
D.ease_all(you)
L.post(door_sc, bloom=0.25)

# ================================================================= CLOCK: deep blue studio
clock_sc = L.new_set("CLOCK")
with L.building(clock_sc):
    studio(clock_sc, H("#2f6bff"), key=500)
    D.cyl("clock", 1.55, 0.18, (0, 0, 2.7), (math.pi / 2, 0, 0), m=white, verts=64)
    D.cyl("clock_rim", 1.65, 0.14, (0, 0.04, 2.7), (math.pi / 2, 0, 0), m=ink, verts=64)
    for i in range(12):
        a = i * math.tau / 12
        t_ = D.box("tick", (0.06, 0.04, 0.22 if i % 3 == 0 else 0.12), (1.3 * math.sin(a), -0.1, 2.7 + 1.3 * math.cos(a)), ink)
        t_.rotation_euler = (0, a, 0)
    hand_m = D.empty("hand_m", (0, -0.14, 2.7))
    D.box("hm", (0.07, 0.03, 1.1), (0, 0, 0.5), ink).parent = hand_m
    hand_h = D.empty("hand_h", (0, -0.13, 2.7))
    D.box("hh", (0.09, 0.03, 0.7), (0, 0, 0.3), ink).parent = hand_h
    key(hand_m, "rotation_euler", 3.4, (0, 0, 0))
    key(hand_m, "rotation_euler", 11.6, (0, math.radians(24 * 360 / 6), 0))
    key(hand_h, "rotation_euler", 3.4, (0, 0, 0))
    key(hand_h, "rotation_euler", 11.6, (0, math.radians(2 * 360 / 6), 0))
    wedges = []
    for i in range(100):
        piv = D.empty(f"wp{i}", (0, -0.05, 2.7))
        piv.rotation_euler = (0, i * math.tau / 100, 0)
        wdg = D.box(f"wedge{i}", (0.075, 0.08, 0.42), (0, 0, 1.98), yellow if i else red, bevel=0.01)
        wdg.parent = piv
        pop(wdg, 7.55 + i * 0.014, dur=0.18)
        wedges.append((piv, wdg))
    w0 = wedges[0][1]
    key(w0, "location", 9.85, (0, 0, 1.98))
    key(w0, "location", 10.4, (0, -0.55, 2.25))
    key(w0, "scale", 10.4, (1.6, 1.6, 1.25))
    D.ease_all(w0)
    lbl = [txt("1,440 MIN", 0.5, (0, -0.3, 0.5), txt_w), txt("÷ 100", 0.55, (0, -0.3, 0.5), yellow),
           txt("14 MIN", 0.7, (0, -0.3, 0.4), red)]
    for o, t in zip(lbl, (5.3, 8.25, 9.9)):
        pop(o, t)
    D.swap([(lbl[0], 1), (lbl[1], T(8.25)), (lbl[2], T(9.9))])
    shot(clock_sc, "B_day", 3.4, 7.35, (0.25, -6.6, 2.4), (0.1, -5.4, 2.35), (0, 0, 2.15), (0, 0, 2.2), 30)
    shot(clock_sc, "C_div", 7.35, 11.6, (2.6, -5.6, 3.3), (-1.6, -5.5, 3.0), (0, 0, 2.3), (0, -0.3, 2.2), 30)

# ================================================================= ICONS: warm amber studio
icons_sc = L.new_set("ICONS")
with L.building(icons_sc):
    studio(icons_sc, H("#ff9f1c"), key=450, x=2)
    IX = (0, 2, 4)
    for x in IX:
        D.cyl("podium", 0.75, 0.5, (x, 0, 0.25), m=white, verts=48)
    D.box("bed_frame", (1.0, 0.6, 0.18), (IX[0], 0, 0.62), L.pbr("bedwood", "wood_table_001", scale=2.5), bevel=0.03)
    D.box("mattress", (0.95, 0.56, 0.14), (IX[0], 0, 0.76), white, bevel=0.04)
    D.box("pillow", (0.24, 0.42, 0.1), (IX[0] - 0.33, 0, 0.88), white, bevel=0.04)
    D.box("blanket", (0.62, 0.6, 0.06), (IX[0] + 0.16, 0, 0.85), L.pbr("blk", "fabric_pattern_07", scale=3, tint=H("#3b82f6"),
                                                                       tint_amount=0.7), bevel=0.025)
    bun = L.plastic("bun", H("#e9a23b"), rough=0.5, coat=0.2)
    D.cyl("bun_b", 0.38, 0.14, (IX[1], 0, 0.6), m=bun, verts=40)
    D.cyl("patty", 0.4, 0.1, (IX[1], 0, 0.72), m=L.plastic("patty", H("#5a3424"), rough=0.7), verts=40)
    D.cyl("cheese", 0.41, 0.03, (IX[1], 0, 0.78), m=yellow, verts=4)
    D.cyl("lettuce", 0.42, 0.03, (IX[1], 0, 0.81), m=L.plastic("lettuce", H("#5cc94a"), rough=0.5), verts=40)
    top = D.sphere("bun_t", 0.38, (IX[1], 0, 0.84), bun)
    top.scale = (1, 1, 0.55)
    D.cyl("cup", 0.26, 0.5, (IX[2], 0, 0.75), m=white, verts=40)
    D.cyl("coffee", 0.24, 0.02, (IX[2], 0, 1.0), m=L.plastic("coffee", H("#4a2c1d"), rough=0.1), verts=40)
    D.torus("handle", 0.14, 0.035, (IX[2] + 0.3, 0, 0.77), (math.pi / 2, 0, 0), white)
    for x, t in zip(IX, (12.0, 13.0, 14.0)):
        xr = D.empty("X", (x, -0.75, 0.85))
        for a in (45, -45):
            b = D.box("xbar", (0.16, 0.08, 1.25), (0, 0, 0), red, bevel=0.03)
            b.rotation_euler = (0, math.radians(a), 0)
            b.parent = xr
        pop(xr, t, dur=0.25)
    cD, lD = D.camera("D_icons", 30)
    for t, x in ((11.6, IX[0] - 0.4), (12.6, IX[0]), (13.0, IX[1]), (13.7, IX[1] + 0.1), (14.0, IX[2]), (15.0, IX[2] + 0.3)):
        D.key(cD, "location", T(t), (x, -3.7, 1.75))
        D.key(lD, "location", T(t), (x, 0, 0.85))
    D.ease_all(cD)
    D.ease_all(lD)
    D.cut(icons_sc, T(11.6), cD)
    SHOTS.append(("ICONS", T(11.6), T(15.0) - 1))

# ================================================================= GAUGE: violet studio
gauge_sc = L.new_set("GAUGE")
with L.building(gauge_sc):
    studio(gauge_sc, H("#7c3aed"), key=450, at=(0, 0, 2.0))
    D.cyl("gauge_bg", 1.45, 0.12, (0, 0.05, 2.0), (math.pi / 2, 0, 0), m=L.plastic("gface", H("#151826"), rough=0.25, coat=0.6), verts=64)
    D.cyl("gauge_ring", 1.55, 0.1, (0, 0.08, 2.0), (math.pi / 2, 0, 0),
          m=L.pbr("chrome", "metal_plate", scale=2, rough_mul=0.4), verts=64)
    for i in range(31):
        a = math.radians(-120 + i * 8)
        c = Vector(H("#22c55e")).lerp(Vector(H("#ff3b47")), i / 30)
        m = D.mat(f"gt{i}", tuple(c), rough=0.4, emit=tuple(c), emit_strength=2.0)
        b = D.box("gtick", (0.07, 0.04, 0.3 if i % 5 == 0 else 0.18), (1.15 * math.sin(a), -0.04, 2.0 + 1.15 * math.cos(a)), m)
        b.rotation_euler = (0, a, 0)
    needle = D.empty("needle", (0, -0.1, 2.0))
    D.box("needle_m", (0.06, 0.03, 1.05), (0, 0, 0.45), red).parent = needle
    D.cyl("hub", 0.12, 0.1, (0, -0.12, 2.0), (math.pi / 2, 0, 0), m=white)
    txt("DRIVE", 0.26, (0, -0.1, 1.35), txt_w)
    for t, deg in ((17.9, 95), (18.6, 108), (19.2, 100), (19.8, 112), (20.25, 106), (20.55, -120), (20.75, -108), (21.0, -118)):
        key(needle, "rotation_euler", t, (0, math.radians(deg), 0))
    D.ease_all(needle)
    shot(gauge_sc, "F_brake", 17.9, 21.3, (0, -4.6, 2.0), (0, -3.6, 2.0), (0, 0, 2.0), (0, 0, 2.0), 30)

# ================================================================= XRAY: dark neon room
xray_sc = L.new_set("XRAY")
with L.building(xray_sc):
    L.hdri_world(xray_sc, "studio_small_09", 0.04, backdrop=H("#060b18"), backdrop_strength=1.0)
    D.room("xroom", (0, 0, 3.5), (16, 16, 7), L.plastic("navy", H("#0b1630"), rough=0.6))
    D.box("xfloor", (16, 16, 0.02), (0, 0, 0.0), L.pbr("xfl", "concrete_floor_02", scale=0.6, tint=H("#13254a"),
                                                         tint_amount=0.9, rough_mul=0.35))
    D.area_light("xkey", 260, (-2.5, -4, 4), (0, 0, 1.4), size=4, rgb=H("#bcd6ff"))
    D.area_light("xrim", 380, (1.5, 3, 3), (0, 0, 1.4), size=3, rgb=H("#38e1ff"))
    D.area_light("xpink", 220, (3.5, -1.5, 2.2), (0, 0, 1.4), size=2, rgb=H("#ff4fd8"))
    xm = bpy.data.materials.new("xray")
    xm.use_nodes = True
    nt = xm.node_tree
    nt.nodes.clear()
    o_, mix = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeMixShader")
    lw, em, tr = nt.nodes.new("ShaderNodeLayerWeight"), nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeBsdfTransparent")
    lw.inputs["Blend"].default_value = 0.35
    em.inputs["Color"].default_value = (*H("#57d8ff"), 1)
    em.inputs["Strength"].default_value = 2.6
    nt.links.new(lw.outputs["Facing"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], o_.inputs["Surface"])
    if hasattr(xm, "surface_render_method"):
        xm.surface_render_method = "BLENDED"
    xr_root, xr_arm, _ = man("xman", (-0.45, 0, 0), 0.0, mat=xm)
    D.play(xr_arm, "idle", 1, T(END))
    xray_sc.frame_set(1)
    hw = D.bone_world(xr_arm, "Head")
    br = D.ico("brain", 0.085, (0, 0, 0), D.mat("brainm", H("#ff5a6e"), emit=H("#ff3355"), emit_strength=3.0))
    br.scale = (1.0, 1.15, 0.85)
    br.parent, br.parent_type, br.parent_bone = xr_arm, "BONE", "mixamorig:Head"
    br.matrix_world = Matrix.Translation(hw + Vector((0, 0.0, 0.11)))
    emit_in = br.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    for i, t in enumerate([21.3 + 0.45 * k for k in range(20)]):
        emit_in.default_value = 6.0 if i % 2 == 0 else 1.5
        emit_in.keyframe_insert("default_value", frame=T(t))
    cyan = D.mat("cyan", H("#57d8ff"), emit=H("#57d8ff"), emit_strength=2.0)
    rp = txt("REFRACTORY\nPERIOD", 0.21, (0.7, -0.3, 2.45), cyan)
    pop(rp, 22.0)
    D.box("bar_bg", (1.3, 0.06, 0.16), (0.7, -0.3, 1.7), D.mat("barbg", H("#22324d"), rough=0.6), bevel=0.04)
    bar = D.empty("bar", (0.05, -0.36, 1.7))
    D.box("bar_f", (1.3, 0.07, 0.14), (0.65, 0, 0), red, bevel=0.03).parent = bar
    key(bar, "scale", 1, (0, 1, 1))
    key(bar, "scale", 24.2, (0.03, 1, 1))
    key(bar, "scale", 26.1, (1, 1, 1))
    D.ease_all(bar)
    t1_ = txt("MINUTES", 0.12, (0.3, -0.3, 1.45), txt_w)
    t2_ = txt("1 DAY", 0.12, (1.15, -0.3, 1.45), txt_w)
    pop(t1_, 24.3)
    pop(t2_, 25.8)
    qm = D.mat("qm", H("#ffc21a"), emit=H("#ffc21a"), emit_strength=1.6)
    for t, off in ((27.0, (-0.38, 0.0, 0.35)), (27.6, (0.32, -0.05, 0.42)), (28.0, (-0.25, -0.1, 0.62)), (28.5, (0.2, -0.1, 0.7))):
        q = txt("?", 0.32, hw + Vector(off), qm)
        pop(q, t)
        key(q, "location", t, q.location.copy())
        key(q, "location", 30.0, q.location + Vector((0, 0, 0.15)))
    L.post(xray_sc, bloom=0.7, bloom_threshold=0.7, bloom_size=0.7, vignette=0.3)
    shot(xray_sc, "G_xray", 21.3, 26.7, (0.25, -4.6, 1.7), (0.3, -3.9, 1.7), (0.25, 0, 1.6), (0.3, 0, 1.65), 30)
    shot(xray_sc, "G2_why", 26.7, 30.0, (-1.6, -1.6, 2.0), (0.7, -1.8, 2.0), (-0.45, 0, 1.6), (-0.45, 0, 1.65), 32, dof=4)

# ================================================================= TANK: mint studio
tank_sc = L.new_set("TANK")
with L.building(tank_sc):
    studio(tank_sc, H("#10b981"), key=450, at=(0, 0, 1.5))
    steel = L.pbr("steel", "metal_plate", scale=2, rough_mul=0.5)
    D.cyl("tank_base", 0.85, 0.25, (0, 0, 0.125), m=steel, verts=48)
    D.cyl("tank_cap", 0.85, 0.2, (0, 0, 2.75), m=steel, verts=48)
    glass = bpy.data.materials.new("glass")
    glass.use_nodes = True
    gb = glass.node_tree.nodes["Principled BSDF"]
    gb.inputs["Base Color"].default_value = (0.92, 0.97, 1, 1)
    gb.inputs["Roughness"].default_value = 0.04
    gb.inputs["Alpha"].default_value = 0.16
    if hasattr(glass, "surface_render_method"):
        glass.surface_render_method = "BLENDED"
    D.cyl("tank_glass", 0.75, 2.4, (0, 0, 1.45), m=glass, verts=48)
    liq = D.cyl("liquid", 0.68, 2.3, (0, 0, 0), m=D.mat("liq", H("#e6f6ff"), rough=0.1, emit=H("#bfe8ff"), emit_strength=0.6), verts=48)
    liq.data.transform(Matrix.Translation((0, 0, 1.15)))
    liq.location = (0, 0, 0.27)
    key(liq, "scale", 35.0, (1, 1, 1))
    key(liq, "scale", 38.6, (1, 1, 0.05))
    D.ease_all(liq, "LINEAR")
    txt("RESERVES", 0.34, (0, -0.2, 3.25), txt_w)
    pct = [txt(p, 0.42, (0, -0.85, 1.25), ink) for p in ("100%", "60%", "25%", "5%")]
    refill = txt("REFILL:\nDAYS", 0.36, (0, -0.85, 1.35), red)
    D.swap([(pct[0], 1), (pct[1], T(36.5)), (pct[2], T(37.85)), (pct[3], T(38.6)), (refill, T(39.8))])
    shot(tank_sc, "I_tank", 34.4, 40.9, (0.4, -5.6, 1.8), (0.4, -4.5, 1.7), (0.3, 0, 1.6), (0.4, 0, 1.55), 30)

# ================================================================= BIO: teal studio — flame (x=0) and heart (x=5)
bio_sc = L.new_set("BIO")
with L.building(bio_sc):
    studio(bio_sc, H("#0e7490"), key=420, x=2.5, at=(0, 0, 1.4))
    FX, HX = 0, 5
    D.cyl("fl_pod", 0.6, 0.4, (FX, 0, 0.2), m=white, verts=48)
    fire = D.empty("fire", (FX, 0, 0.4))
    for x, y, r, h, c, e in ((0, 0.05, 0.42, 1.35, "#ff5a1f", 3.0), (-0.3, -0.05, 0.26, 0.85, "#ff8a2a", 3.0),
                             (0.28, -0.08, 0.24, 0.75, "#ff8a2a", 3.0), (0.02, -0.22, 0.25, 0.8, "#ffd23f", 3.5)):
        cn = D.cone("flame", r, h, (x, y, h / 2), D.mat("flame", H(c), emit=H(c), emit_strength=e))
        cn.parent = fire
    for i in range(12):
        key(fire, "scale", 41.0 + i * 0.25, (1 + 0.05 * (i % 2), 1 + 0.05 * (i % 2), 1 + 0.12 * ((i + 1) % 2)))
    kcal = txt("100 kcal", 0.42, (FX, -0.2, 2.35), txt_w)
    pop(kcal, 42.85)
    D.cyl("ht_pod", 0.6, 0.4, (HX, 0, 0.2), m=white, verts=48)
    bm = bmesh.new()
    vs = []
    for i in range(1, 96):
        t_ = i * math.tau / 96
        vs.append(bm.verts.new((16 * math.sin(t_) ** 3 * 0.042, 0,
                                (13 * math.cos(t_) - 5 * math.cos(2 * t_) - 2 * math.cos(3 * t_) - math.cos(4 * t_)) * 0.042)))
    bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    hme = bpy.data.meshes.new("heart")
    bm.to_mesh(hme)
    heart = D.link(bpy.data.objects.new("heart", hme))
    so = heart.modifiers.new("puff", "SOLIDIFY")
    so.thickness, so.offset = 0.32, 0.0
    sub = heart.modifiers.new("round", "SUBSURF")
    sub.levels = sub.render_levels = 3
    D.smooth(heart)
    heart.location = (HX, 0, 1.65)
    heart.data.materials.append(L.plastic("heartm", H("#ff2d55"), rough=0.25, coat=0.6, emit=H("#ff2d55"), emit_strength=0.4))
    t, beat = 43.5, 0.8
    while t < 47.2:
        key(heart, "scale", t, (1, 1, 1))
        key(heart, "scale", t + beat * 0.18, (1.14, 1.14, 1.14))
        key(heart, "scale", t + beat * 0.45, (1, 1, 1))
        t += beat
        beat = max(0.4, beat * 0.88)
    bpm = [txt(b, 0.5, (HX + 0.15, -0.3, 0.75), txt_w) for b in ("72", "95", "112", "130")]
    for o in bpm:
        o.data.align_x = "RIGHT"
    D.swap([(bpm[0], 1), (bpm[1], T(44.1)), (bpm[2], T(44.6)), (bpm[3], T(45.2))])
    txt("BPM", 0.3, (HX + 0.55, -0.3, 0.72), yellow)
    shot(bio_sc, "J1_kcal", 40.9, 43.8, (FX, -4.0, 1.6), (FX, -3.3, 1.7), (FX, 0, 1.45), (FX, 0, 1.5), 30)
    shot(bio_sc, "J2_bpm", 43.8, 46.9, (HX, -3.9, 1.35), (HX, -3.1, 1.35), (HX, 0, 1.2), (HX, 0, 1.25), 30)

# ================================================================= STAIRS: sunny yellow studio
stairs_sc = L.new_set("STAIRS")
with L.building(stairs_sc):
    studio(stairs_sc, H("#ffbf1f"), key=420, x=2, at=(0, 0, 1.6))
    SX = 0.0
    step_m = L.pbr("stairs", "concrete_floor_02", scale=1.5, tint=H("#fff7ea"), tint_amount=0.6)
    for i in range(18):
        D.box("stair", (0.38, 1.6, 0.2 * (i + 1)), (SX + i * 0.38, 0, 0.1 * (i + 1)), step_m, bevel=0.01)
    climber, carm, _ = man("climber", (SX - 0.5, 0, 0), math.radians(90))
    D.play(carm, "walk", T(46.4), T(49.6), speed=1.25)
    key(climber, "location", 46.9, (SX + 0.1, 0, 0.2))
    key(climber, "location", 49.5, (SX + 3.4, 0, 0.2 + 3.3 / 0.38 * 0.2))
    every = txt("EVERY 14 MIN", 0.34, (SX + 2.2, -1.0, 4.4), ink)
    allday = txt("ALL DAY", 0.42, (SX + 2.2, -1.0, 3.85), red)
    pop(every, 47.3)
    pop(allday, 48.4)
    shot(stairs_sc, "J3_stairs", 46.9, 49.4, (SX + 1.2, -7.2, 2.6), (SX + 2.4, -7.0, 3.4), (SX + 1.0, 0, 1.6),
         (SX + 2.5, 0, 2.7), 30)

# ================================================================= GRID: 1 in 5 → 20 of 100 (soft aqua studio)
grid_sc = L.new_set("GRID")
with L.building(grid_sc):
    studio(grid_sc, H("#9ee6e0"), key=500, at=(0, -4, 0.8), key_from=(-4, -10, 9))
    GRY = -4.0
    grid, reds = [], set(random.sample(range(100), 20))
    for i in range(100):
        r_, c_ = divmod(i, 10)
        grid.append(woman((-3.8 + c_ * 0.85, GRY - 3.8 + r_ * 0.85, 0), random.uniform(-0.4, 0.4),
                          color=random.choice(["#f1ece4", "#e7e0d6", "#faf6ef"]), scale=1.0))
    for n, i in enumerate(sorted(reds, key=lambda k: random.random())):
        o, t = grid[i], 59.85 + n * 0.05
        o.keyframe_insert("color", frame=T(t) - 1)
        o.color = (*H("#ff2d3d"), 1)
        o.keyframe_insert("color", frame=T(t))
        D.overshoot(o, "scale", T(t), T(t + 0.3), (1, 1, 1), (1, 1, 1), 1.2)
    one5 = txt("1 in 5", 1.35, (0, GRY, 3.4), red, rot=(math.radians(62), 0, 0))
    pop(one5, 53.55)
    twenty = txt("20", 1.6, (0, GRY, 3.2), red, rot=(math.radians(70), 0, 0))
    pop(twenty, 60.25)
    D.swap([(one5, 1), (twenty, T(60.25))])
    shot(grid_sc, "L1_onein5", 51.9, 57.6, (0, -16, 7.5), (0, -14.2, 6.8), (0, GRY, 1.0), (0, GRY, 1.2), 30)
    shot(grid_sc, "L2_twenty", 57.6, 61.2, (0.5, -9.5, 12), (0, -8.0, 13.5), (0, GRY, 0.5), (0, GRY, 0.6), 30)

# ================================================================= BED: moonlit bedroom, warm lamp
bed_sc = L.new_set("BED")
with L.building(bed_sc):
    L.hdri_world(bed_sc, "studio_small_09", 0.05, backdrop=H("#05070f"))
    D.room("bedroom", (0, 0, 2.5), (10, 9, 5), L.pbr("bwall", "plastered_wall", scale=0.6, tint=H("#2b3a8f"),
                                                       tint_amount=0.95, normal=0.5))
    D.box("bfloor", (10, 9, 0.02), (0, 0, 0.0), L.pbr("bfl", "laminate_floor_02", scale=0.8, rough_mul=0.7))
    D.area_light("moonl", 320, (-1.5, 2.5, 3.2), (0, 0.4, 0.8), size=1.2, rgb=H("#8fb0ff"))
    D.area_light("lamp", 300, (1.6, -0.4, 1.4), (0, 0.4, 0.7), size=0.4, rgb=H("#ffb15e"))
    D.area_light("bfill", 140, (0, -3.5, 2.5), (0, 0.4, 0.8), size=3, rgb=H("#7d95e0"))
    D.box("winframe", (1.5, 0.1, 1.2), (-1.3, 4.45, 2.4), trim)
    D.box("winsky", (1.3, 0.05, 1.0), (-1.3, 4.4, 2.4), D.mat("sky", H("#0b1530"), rough=1, emit=H("#132657"), emit_strength=0.6))
    D.cyl("moon", 0.2, 0.02, (-1.0, 4.36, 2.6), (math.pi / 2, 0, 0), m=D.mat("moonm", H("#fff4d0"), emit=H("#fff4d0"), emit_strength=5))
    wood = L.pbr("bedwood2", "wood_table_001", scale=1.5)
    D.box("bframe", (2.3, 1.4, 0.4), (0, 0.4, 0.2), wood, bevel=0.04)
    D.box("bmatt", (2.2, 1.3, 0.24), (0, 0.4, 0.52), white, bevel=0.08)
    D.box("bhead", (0.12, 1.4, 1.1), (-1.15, 0.4, 0.55), wood, bevel=0.04)
    D.box("bpillow", (0.45, 0.8, 0.12), (-0.85, 0.4, 0.69), L.pbr("pil", "fabric_pattern_07", scale=4, tint=H("#ffffff"),
                                                                  tint_amount=0.8), bevel=0.06)
    sleeper, sarm, _ = man("sleeper", (0.85, 0.4, 0.83), 0.0)
    sleeper.rotation_euler = (math.radians(-90), 0, math.radians(90))
    D.play(sarm, "idle", 1, T(END), speed=0.5)
    D.box("blanket2", (1.55, 1.36, 0.3), (0.3, 0.4, 0.86), L.pbr("blank", "fabric_pattern_07", scale=2.5, tint=H("#2563eb"),
                                                                  tint_amount=0.75), bevel=0.07)
    D.box("nightstand", (0.5, 0.5, 0.6), (1.6, -0.1, 0.3), wood, bevel=0.03)
    L.prop("alarm_clock_01", (1.55, -0.1, 0.6), rot_z=200, scale=1.6)
    L.prop("potted_plant_04", (-2.3, 1.6, 0.0), rot_z=30, scale=1.2)
    L.prop("fancy_picture_frame_01", (1.4, 4.42, 2.1), rot_z=0, scale=1.3)
    zm = D.mat("zm", H("#ffffff"), emit=H("#cfe0ff"), emit_strength=2.0)
    for i in range(7):
        t0 = 69.6 + i * 0.85
        z = txt("Z", 0.16 + 0.05 * (i % 3), (-0.8, 0.2, 1.0), zm, rot=(math.radians(80), 0, 0))
        pop(z, t0, dur=0.25)
        key(z, "location", t0, (-0.8, 0.2, 1.0))
        key(z, "location", t0 + 2.4, (-0.35 + 0.15 * (i % 2), 0.1, 2.0))
        key(z, "scale", t0 + 2.0, (1, 1, 1))
        key(z, "scale", t0 + 2.4, (0, 0, 0))
    L.post(bed_sc, bloom=0.55, bloom_threshold=0.75, vignette=0.32)
    shot(bed_sc, "O_sleep", 68.9, END, (1.4, -3.4, 1.9), (0.3, -2.3, 1.55), (-0.2, 0.4, 0.9), (-0.45, 0.4, 0.85), 30)

# ================================================================= DOOR shots (cameras live in the DOOR scene)
shot(door_sc, "A_hook", 0.0, 3.4, (4.8, -19, 5.5), (-2.7, -5.8, 2.4), (1.6, -9, 0.9), (0.2, 0, 1.9), 22, 28, shake=0.006)
shot(door_sc, "E_easy", 15.0, 17.9, (-2.5, -4.6, 1.8), (-2.0, -3.8, 1.75), (0.5, 0, 1.4), (0.5, 0, 1.5), 28)
shot(door_sc, "H_late", 30.0, 34.4, (-0.9, -6.4, 2.7), (-1.1, -5.6, 2.9), (-1.0, 0, 3.0), (-1.2, 0, 3.4), 26)
shot(door_sc, "K_danger", 49.4, 51.9, (-1.2, -7.8, 0.35), (-0.9, -7.0, 0.4), (2.4, -4.2, 1.35), (2.3, -3.8, 1.45), 20, 22, shake=0.006)
shot(door_sc, "M_handful", 61.2, 66.3, (-2.0, -5.4, 2.1), (-1.6, -4.6, 1.9), (0.9, -0.6, 1.8), (1.0, -0.8, 1.5), 26)
shot(door_sc, "N_home", 66.3, 68.9, (0.6, -1.4, 6.5), (0.8, -1.6, 8.0), (0.6, -14, 0), (0.2, -18, 0), 24)

SHOTS.sort(key=lambda x: x[1])
json.dump(SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(SHOTS), "scenes", [s.name for s in bpy.data.scenes])
