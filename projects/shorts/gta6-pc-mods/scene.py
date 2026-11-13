"""blender -b -P scene.py -- <out.blend>: "Why GTA 6 isn't coming to PC" — PS2 look. Story time = VO time.

  0.0-3.3   RADAL clip (compose)            | 17.9-26.1 RADAL mod montage (compose)
  STAGE  3.3 consoles on the VIP podium, PC behind the rope | 14.5 GTA VI disc → PC shakes, smokes, explodes
  WAIT   7.3 skeleton waiting at "GTA V — PC: coming soon", calendar pages fly (MONTH 1→19 HUD in compose)
  OFFICE 11.5 exec in the dark ("Rockstar won't say why") | 37.1 exec unplugs THE INTERNET → blackout
  BOARD  13.1 conspiracy board ("But I know why")
  STREET 26.1 day one: 29.5 everyone's a giant, 31.9 raining cows, 34.2 T-posing cops slide, 40.1 final chaos
Cast: Renderpeople "Eric" (CC-BY). Props: Fiat Punto (lionsharp), Low Poly Cow (kenchoo), Skeleton Sitting (Buzzie)
— Sketchfab CC-BY. Everything else procedural / Poly Haven.
"""
import math, os, random, sys, json
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
sys.path.insert(0, HERE)
import bpy
import director as D
import look as L
import ps2 as P

out = sys.argv[sys.argv.index("--") + 1]
END = 42.3
T, H = D.T, D.hex_lin
random.seed(19)
TEX = lambda n: os.path.join(HERE, "out", "tex", n)

base = D.reset(w=360, h=640, frames=T(END) - 1)
P.setup(base)
import kit as K  # noqa: E402
from kit import flat, shot, upd, man, pose_strip, own_vl, A, prop, SIT, STAND, LISTEN, cyl_between  # noqa: E402


# ---------------------------------------------------------------- helpers
def img_mat(name, path, lit=False, emit=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    tex.interpolation = "Closest"
    b = nt.nodes["Principled BSDF"]
    if lit:
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 1.0
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit * 0.3
        return m
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = emit
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


def plane(name, w, h, loc, m, rot=(0, 0, 0)):
    """Card in the XZ plane facing -Y with full UVs."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    me.materials.append(m)
    o = D.link(bpy.data.objects.new(name, me))
    o.location, o.rotation_euler = loc, rot
    return o


def show(o, spans):
    s = tuple(o.scale)
    D.key(o, "scale", 1, (0, 0, 0), "CONSTANT")
    for a, b in spans:
        D.key(o, "scale", max(1, T(a)), s, "CONSTANT")
        D.key(o, "scale", T(b), (0, 0, 0), "CONSTANT")


def burst(name, origin, t, n=14, m=None, dist=0.4, dur=0.4, r=(0.008, 0.02), up=0.3, grow=1.0):
    o = Vector(origin)
    for i in range(n):
        s = D.ico(f"{name}{i}", random.uniform(*r), origin, m=m, sub=1)
        d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.3, 1))).normalized()
        D.key(s, "scale", 1, (0, 0, 0), "CONSTANT")
        D.key(s, "scale", T(t), (1, 1, 1))
        D.key(s, "location", T(t), o)
        D.key(s, "location", T(t + dur), o + d * dist * random.uniform(0.5, 1) + Vector((0, 0, up * random.uniform(0, 1))))
        D.key(s, "scale", T(t + dur), (grow,) * 3)
        D.key(s, "scale", T(t + dur) + 1, (0, 0, 0), "CONSTANT")


def sit_on(root, arm, seat_z):
    own_vl(arm).update()
    hips = arm.matrix_world @ arm.data.bones["Hips"].head_local
    root.location.z += seat_z - hips.z + 0.03


def head_socket(arm, root, name):
    own_vl(arm).update()
    R = root.matrix_world.to_quaternion().to_matrix().to_4x4()
    e = [arm.matrix_world @ arm.data.bones[b].head_local for b in ("eye_l_011", "eye_r_013")]
    s = D.empty(name, (0, 0, 0))
    s.parent, s.parent_type, s.parent_bone = arm, "BONE", "Head"
    own_vl(arm).update()
    s.matrix_world = Matrix.Translation((e[0] + e[1]) / 2) @ R @ Matrix.Scale(root.scale.x, 4)
    return s


def dup(objs, name, loc, rot=(0, 0, 0), scale=1.0):
    """Linked duplicate of an imported prop's meshes under a new empty."""
    g = D.empty(name, loc)
    g.rotation_euler, g.scale = rot, (scale,) * 3
    for o in objs:
        c = o.copy()
        D.link(c)
        c.parent = g
    return g


def tint(mats, rgb, amount=0.75):
    out = {}
    for m in mats:
        if m is None or m.name in out:
            continue
        c = m.copy()
        nt = c.node_tree
        b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b and b.inputs["Base Color"].is_linked:
            src = b.inputs["Base Color"].links[0].from_socket
            mx = nt.nodes.new("ShaderNodeMix")
            mx.data_type, mx.blend_type = "RGBA", "MULTIPLY"
            mx.inputs["Factor"].default_value = amount
            mx.inputs[7].default_value = (*rgb, 1)
            nt.links.new(src, mx.inputs[6])
            nt.links.new(mx.outputs[2], b.inputs["Base Color"])
        elif b:
            b.inputs["Base Color"].default_value = (*rgb, 1)
        out[m.name] = c
    return out


def key_world(scene, t, amb, sky=None):
    for n in scene.world.node_tree.nodes:
        if n.type == "BACKGROUND":
            n.inputs[1].keyframe_insert("default_value", frame=T(t) - 1)
    for i, n in enumerate(x for x in scene.world.node_tree.nodes if x.type == "BACKGROUND"):
        n.inputs[1].default_value = amb if i else (sky if sky is not None else amb)
        n.inputs[1].keyframe_insert("default_value", frame=T(t))


TPOSE = {"LeftUpLeg": (0.04, 0, -1), "RightUpLeg": (-0.04, 0, -1), "LeftLeg": (0, 0, -1), "RightLeg": (0, 0, -1),
         "Spine": (0, 0, 1), "LeftArm": (1, 0, 0), "RightArm": (-1, 0, 0), "LeftForeArm": (1, 0, 0), "RightForeArm": (-1, 0, 0)}
DESK = SIT | {"LeftArm": (0.25, -0.7, -0.5), "RightArm": (-0.25, -0.7, -0.5), "LeftForeArm": (-0.25, -1, 0.15),
              "RightForeArm": (0.25, -1, 0.15), "Head": (0, -0.12, 1)}
REACH = STAND | {"Spine": (0, -0.15, 1), "LeftArm": (0.1, -0.9, -0.35), "RightArm": (-0.1, -0.9, -0.35),
                 "LeftForeArm": (0.05, -1, -0.1), "RightForeArm": (-0.05, -1, -0.1), "Head": (0, -0.2, 1)}
YANK = STAND | {"Spine": (0, 0.3, 1), "Neck": (0, 0.2, 1), "LeftArm": (0.15, -0.9, -0.2), "RightArm": (-0.15, -0.9, -0.2),
                "LeftForeArm": (0, -1, 0.1), "RightForeArm": (0, -1, 0.1)}
LOOKDOWN = STAND | {"Neck": (0, -0.4, 1), "Head": (0, -0.7, 1), "LeftArm": (0.35, -0.1, -1), "RightArm": (-0.35, -0.1, -1)}
SHOCK = STAND | {"LeftArm": (0.6, -0.3, 0.7), "RightArm": (-0.6, -0.3, 0.7), "LeftForeArm": (0.2, -0.2, 1),
                 "RightForeArm": (-0.2, -0.2, 1), "Head": (0, 0.05, 1)}
WHITE_E = flat("white_e", "#ffffff", 3.0)
GOLD = flat("gold", "#d4af37", 0.6)
SMOKE = flat("smoke", "#3a3a3a")
SPARK = flat("spark", "#ffd34d", 4.0)

# ================================================================= STAGE: consoles VIP, PC behind the rope
stg = L.new_set("STAGE", main=True)
P.flat_light(stg, "#140c26", ambient=1.0, sun=0.6)
D.area_light("spotA", 300, (-1.2, 0.0, 4.0), (0, 2, 0.6), size=1.0, rgb=H("#bfe0ff"))
D.area_light("spotB", 300, (1.2, 0.0, 4.0), (0, 2, 0.6), size=1.0, rgb=H("#ffd0f0"))
D.box("stfloor", (20, 20, 0.02), (0, 0, -0.01), flat("stfl", "#221a33"))
D.box("stwall", (20, 0.1, 8), (0, 6, 4), flat("stw", "#2c2145"))
plane("cal", 2.4, 2.8, (0, 5.9, 3.0), img_mat("cal", TEX("calendar.png"), emit=0.9))
D.cyl("podium", 1.3, 0.35, (0, 2, 0.175), m=flat("pod", "#f2f2f2", 0.2), verts=20)
D.torus("podring", 1.3, 0.03, (0, 2, 0.35), m=flat("podr", "#ffd400", 2.0))
cons = []
for x, size, body, glow in ((-0.45, (0.26, 0.5, 0.62), "#f4f4f4", "#3a86ff"), (0.45, (0.34, 0.34, 0.64), "#111111", "#2bd94a")):
    g = D.empty("console", (x, 2, 0.35))
    b = D.box("cbody", size, (0, 0, 0), flat("cb" + body, body))
    b.parent, b.location = g, (0, 0, size[2] / 2)
    s = D.box("cglow", (size[0] * 1.02, size[1] * 0.15, size[2] * 0.9), (0, 0, 0), flat("cg" + glow, glow, 3.0))
    s.parent, s.location = g, (0, 0, size[2] / 2)
    D.key(g, "rotation_euler", T(3.3), (0, 0, math.radians(-20)))
    D.key(g, "rotation_euler", T(7.3), (0, 0, math.radians(25)))
    cons.append(g)
for x in (-1.6, 1.6):
    D.cyl("post", 0.04, 0.9, (x, 0.4, 0.45), m=GOLD, verts=8)
    D.sphere("postb", 0.06, (x, 0.4, 0.93), m=GOLD, seg=8, rings=4)
rope = cyl_between("rope", (-1.6, 0.4, 0.8), (1.6, 0.4, 0.8), 0.03, flat("ropem", "#b0001e", 0.3))
# the PC, outside the rope
pc = D.empty("pc", (2.0, -0.5, 0))
PCB = flat("pcb", "#141418")
b = D.box("pcbody", (0.26, 0.5, 0.5), (0, 0, 0), PCB)
b.parent, b.location = pc, (0, 0, 0.25)
RGB = D.mat("rgb", H("#ff2dd2"), emit=H("#ff2dd2"), emit_strength=3.0)
for z in (0.08, 0.42):
    s = D.box("rgbstrip", (0.27, 0.48, 0.02), (0, 0, 0), RGB)
    s.parent, s.location = pc, (0, 0, z)
slot = D.box("slot", (0.18, 0.01, 0.015), (0, 0, 0), flat("slotm", "#000000"))
slot.parent, slot.location = pc, (0, -0.255, 0.38)
es = RGB.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
ec = RGB.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
for t, v in ((3.3, 3.0), (6.2, 3.0), (6.6, 0.3), (14.4, 0.3), (15.2, 3.0)):
    es.default_value = v
    es.keyframe_insert("default_value", frame=T(t))
for t, c in ((15.3, "#ff2dd2"), (16.5, "#ff2dd2"), (16.6, "#ff0000")):
    ec.default_value = (*H(c), 1)
    ec.keyframe_insert("default_value", frame=T(t))
disc = D.cyl("disc", 0.06, 0.004, (0, 0, 0), rot=(math.pi / 2, 0, 0), m=img_mat("discm", TEX("disc.png"), emit=1.3), verts=24)
for t, p in ((14.5, (2.0, -1.25, 0.55)), (14.9, (2.0, -0.9, 0.4)), (15.3, (2.0, -0.72, 0.38)), (15.35, (2.0, -0.6, 0.38))):
    D.key(disc, "location", T(t), p)
D.key(disc, "rotation_euler", T(14.5), (math.pi / 2, 0, 0))
D.key(disc, "rotation_euler", T(15.3), (math.pi / 2, math.radians(720), 0))
show(disc, [(14.5, 15.35)])
for k in range(int((17.9 - 15.7) * 15)):                         # shaking, harder and harder
    t = 15.7 + k / 15
    a = 0.004 + 0.03 * k / 33
    D.key(pc, "location", T(t), (2.0 + random.uniform(-a, a), -0.5 + random.uniform(-a, a), random.uniform(0, a)))
    D.key(pc, "rotation_euler", T(t), (0, 0, random.uniform(-a, a) * 3))
for i in range(10):                                              # smoke puffs
    t0 = 16.6 + i * 0.12
    s = D.ico(f"smk{i}", 0.06, (2.0, -0.5, 0.5), m=SMOKE, sub=1)
    D.key(s, "scale", 1, (0, 0, 0), "CONSTANT")
    D.key(s, "scale", T(t0), (1, 1, 1))
    D.key(s, "location", T(t0), (2.0 + random.uniform(-0.1, 0.1), -0.5 + random.uniform(-0.15, 0.15), 0.52))
    D.key(s, "location", T(t0 + 1.0), (2.0 + random.uniform(-0.4, 0.4), -0.5 + random.uniform(-0.3, 0.3), 1.3 + random.uniform(0, 0.5)))
    D.key(s, "scale", T(t0 + 1.0), (4, 4, 4))
burst("pcsp", (2.0, -0.6, 0.45), 16.7, n=16, m=SPARK, dist=0.6, dur=0.35)
burst("pcsp2", (2.0, -0.6, 0.3), 17.2, n=16, m=SPARK, dist=0.7, dur=0.35)
flash = D.sphere("flash", 0.3, (2.0, -0.5, 0.35), m=WHITE_E, seg=12, rings=8)
D.key(flash, "scale", 1, (0, 0, 0), "CONSTANT")
D.key(flash, "scale", T(17.45), (0.2, 0.2, 0.2))
D.key(flash, "scale", T(17.9), (14, 14, 14))
shot(stg, "S1_vip", 3.3, 5.0, (0.25, -2.6, 1.15), (0.05, -1.9, 1.0), (0, 2, 0.8), (0, 2, 0.75), 34, 40)
shot(stg, "S2_rope", 5.0, 7.3, (2.75, -1.75, 0.42), (2.6, -1.55, 0.42), (1.2, 1.6, 0.65), (1.0, 1.8, 0.6), 22)
shot(stg, "S3_disc", 14.5, 16.5, (2.45, -1.75, 0.6), (2.3, -1.45, 0.5), (2.0, -0.6, 0.42), (2.0, -0.6, 0.4), 22)
shot(stg, "S4_boom", 16.5, 17.9, (3.0, -2.6, 0.95), (3.4, -3.3, 1.2), (2.0, -0.5, 0.45), (2.0, -0.5, 0.5), 20, shake=0.01)

# ================================================================= WAIT: skeleton waiting for GTA V on PC
wt = L.new_set("WAIT")
with L.building(wt):
    P.flat_light(wt, "#1d1a24", ambient=1.2, sun=0.8)
    D.area_light("wlamp", 60, (0.6, -0.8, 2.2), (0, 0.4, 0.8), size=0.8, rgb=H("#fff0c8"))
    D.room("wroom", (0, 0, 1.4), (5, 5, 2.8), L.pbr("wwall", "painted_plaster_wall", scale=0.8, tint=H("#8a8f7a"), tint_amount=0.8))
    D.box("wfloor", (5, 5, 0.02), (0, 0, 0), L.pbr("wwood", "wood_table_001", scale=1.0))
    wood = L.pbr("wdesk", "wood_table_001", scale=1.5)
    D.box("wdesk", (1.3, 0.65, 0.05), (0, 0.55, 0.74), wood)
    for x in (-0.6, 0.6):
        D.box("wleg", (0.05, 0.6, 0.72), (x, 0.55, 0.36), wood)
    D.box("wmon", (0.62, 0.04, 0.4), (0, 0.78, 1.0), flat("wmb", "#111111"))
    plane("wscr", 0.58, 0.36, (0, 0.755, 1.0), img_mat("wscrm", TEX("waiting.png"), emit=1.2))
    D.box("wkbd", (0.45, 0.15, 0.02), (0, 0.42, 0.77), flat("wkb", "#222222"))
    D.box("wseat", (0.45, 0.45, 0.06), (0, 0.0, 0.46), flat("wseatm", "#2b2b2b"))
    old, oarm, obody = man("oldman", (0, -0.05, 0), math.pi, 1.0)
    sit_on(old, oarm, 0.49)
    dusty = tint({m for b in obody for m in b.data.materials}, H("#b8b8b0"), 0.85)
    for b in obody:
        for si, slot in enumerate(b.material_slots):
            if slot.material and slot.material.name in dusty:
                b.material_slots[si].material = dusty[slot.material.name]
    hs = head_socket(oarm, old, "oldsock")
    BEARD = flat("beard", "#f4f4f0", 0.3)
    for k, (dx, ln) in enumerate(((0, 0.55), (-0.03, 0.45), (0.03, 0.45))):
        bc = D.cone(f"beard{k}", 0.05, ln, (0, 0, 0), m=BEARD, verts=8)
        bc.parent, bc.location, bc.rotation_euler = hs, (dx, -0.075, -0.09 - ln / 2), (math.pi, 0, 0)
    for k, (dx) in enumerate((-0.09, 0.09)):
        hr = D.cone(f"hair{k}", 0.05, 0.35, (0, 0, 0), m=BEARD, verts=6)
        hr.parent, hr.location, hr.rotation_euler = hs, (dx, 0.02, -0.12), (math.pi, 0, 0)
    SLUMP = DESK | {"Spine": (0, -0.25, 1), "Neck": (0, -0.45, 1), "Head": (0, -0.55, 1)}
    pose_strip(oarm, old, [(1, SLUMP), (T(END), SLUMP)], 1, T(END), blend=1)
    WEB = flat("web", "#e8e8e8", 0.4)
    for a, b in (((-0.22, -0.26, 1.1), (0.0, -0.1, 0.62)), ((0.22, -0.26, 1.1), (0.1, 0.0, 0.7)), ((-0.6, 0.85, 0.77), (-0.3, 0.78, 1.18)),
                 ((0.6, 0.85, 0.77), (0.3, 0.78, 1.18)), ((-0.3, 0.42, 0.78), (0.0, 0.3, 0.9)), ((-2.4, 2.4, 2.7), (-1.6, 2.4, 2.0)),
                 ((-2.4, 2.4, 2.7), (-2.4, 1.6, 2.0)), ((2.4, 2.4, 2.7), (1.7, 2.4, 2.1))):
        cyl_between("web", a, b, 0.0025, WEB, verts=4)
    # wall calendar: 19 pages tear off
    plane("wcalb", 0.42, 0.5, (1.1, 2.47, 1.6), flat("wcalbm", "#ffffff"), rot=(0, 0, math.pi))
    for n in range(19, 0, -1):
        pg = plane(f"pg{n}", 0.4, 0.48, (1.1, 2.46 - (19 - n) * 0.0005, 1.6), img_mat(f"pgm{n}", TEX(f"page_{n:02d}.png"), lit=True),
                   rot=(0, 0, math.pi))
        if n < 19:
            t0 = 8.9 + (n - 1) * 0.12
            D.key(pg, "location", T(t0), pg.location.copy())
            D.key(pg, "location", T(t0 + 0.5), pg.location + Vector((random.uniform(-0.8, 0.2), -1.2, -1.4)))
            D.key(pg, "rotation_euler", T(t0), (0, 0, math.pi))
            D.key(pg, "rotation_euler", T(t0 + 0.5), (random.uniform(-2, 2), random.uniform(-2, 2), math.pi + random.uniform(-1, 1)))
            D.key(pg, "scale", T(t0 + 0.5), (1, 1, 1), "CONSTANT")
            D.key(pg, "scale", T(t0 + 0.5) + 1, (0, 0, 0), "CONSTANT")
    shot(wt, "W1_wait", 7.3, 9.0, (1.35, 1.6, 1.35), (1.05, 1.25, 1.25), (0, -0.05, 1.0), (0, -0.05, 1.0), 22)
    shot(wt, "W2_pages", 9.0, 11.5, (-0.3, -0.9, 1.25), (-0.15, -0.6, 1.3), (0.7, 2.0, 1.25), (0.9, 2.3, 1.45), 22)

# ================================================================= OFFICE: exec in the dark / unplugs the internet
of = L.new_set("OFFICE")
with L.building(of):
    P.flat_light(of, "#0e0c12", ambient=0.9, sun=0.5)
    D.area_light("blindlight", 120, (0, 3.2, 1.8), (0, 0, 1.0), size=1.5, rgb=H("#ffb066"))
    D.area_light("okey", 40, (-1.2, -1.5, 2.2), (0, 1, 1.2), size=1.0, rgb=H("#9fb8ff"))
    D.room("oroom", (0, 0, 1.5), (6, 6, 3), L.pbr("owall", "painted_plaster_wall", scale=0.8, tint=H("#3a3f4a"), tint_amount=0.9))
    D.box("ofloor", (6, 6, 0.02), (0, 0, 0), L.pbr("ofl", "wood_table_001", scale=0.8, tint=H("#5a3a22"), tint_amount=0.5))
    plane("owin", 2.0, 1.4, (0, 2.95, 1.7), flat("owinm", "#ffcf8a", 1.6), rot=(0, 0, math.pi))
    for k in range(12):
        D.box("slat", (2.05, 0.02, 0.055), (0, 2.9, 1.05 + k * 0.115), flat("slatm", "#1a140f"))
    odesk = L.pbr("odesk", "wood_table_001", scale=1.5, tint=H("#4a2a14"), tint_amount=0.7)
    D.box("odesk", (1.8, 0.8, 0.06), (0, 0.6, 0.76), odesk)
    D.box("odfront", (1.8, 0.05, 0.72), (0, 0.2, 0.38), odesk)
    D.box("ochair", (0.55, 0.15, 0.95), (0, 1.55, 0.85), flat("leather", "#2a1410"))
    exA, axA, _ = man("execA", (0, 1.3, 0), 0.0, 1.0)
    sit_on(exA, axA, 0.5)
    pose_strip(axA, exA, [(1, DESK), (T(END), DESK)], 1, T(END), blend=1)
    # socket wall (+X), plug, cable, THE INTERNET server
    D.box("socket", (0.04, 0.14, 0.14), (2.97, -1.25, 1.0), flat("sockm", "#e8e8e8"))
    srv = D.box("server", (0.6, 0.7, 1.9), (2.55, 0.0, 0.95), flat("srvm", "#18181c"))
    plane("srvlab", 0.6, 0.16, (2.55, -0.355, 1.7), img_mat("internet", TEX("internet.png"), emit=1.2))
    LEDS = D.mat("leds", H("#3dff6a"), emit=H("#3dff6a"), emit_strength=3.0)
    for k in range(18):
        D.box("led", (0.03, 0.01, 0.015), (2.33 + (k % 6) * 0.08, -0.36, 0.5 + (k // 6) * 0.25), LEDS)
    plug = D.empty("plug", (2.85, -1.25, 1.0))
    pb_ = D.box("plugb", (0.2, 0.12, 0.12), (0, 0, 0), flat("plugm", "#f0f0f0"))
    pb_.parent = plug
    for t, p in ((37.1, (2.85, -1.25, 1.0)), (38.35, (2.85, -1.25, 1.0)), (38.55, (2.55, -1.25, 1.12)), (39.0, (2.5, -1.25, 1.1))):
        D.key(plug, "location", T(t), p)
    cable = D.cyl("cable", 0.02, 1.0, (0, 0, 0), m=flat("cablem", "#111111"), verts=6)
    cable.data.transform(Matrix.Translation((0, 0, 0.5)))
    cable.location = (2.55, -0.4, 0.05)
    c = cable.constraints.new("STRETCH_TO")
    c.target, c.rest_length, c.volume = plug, 1.0, "NO_VOLUME"
    exB, axB, _ = man("execB", (2.2, -1.25, 0), math.radians(90), 1.0)
    pose_strip(axB, exB, [(1, REACH), (T(38.3), REACH), (T(38.55), YANK), (T(39.4), YANK), (T(39.7), SHOCK), (T(END), SHOCK)],
               1, T(END), blend=1)
    burst("osp", (2.92, -1.25, 1.0), 38.38, n=22, m=SPARK, dist=0.6, dur=0.4)
    burst("osp2", (2.92, -1.25, 1.0), 39.35, n=30, m=SPARK, dist=0.9, dur=0.5)
    # blackout at 39.4
    key_world(of, 39.4, 0.3, sky=0.3)
    for o in of.collection.objects:
        if o.type == "LIGHT":
            o.data.keyframe_insert("energy", frame=T(39.4) - 1)
            o.data.energy = o.data.energy * 0.08
            o.data.keyframe_insert("energy", frame=T(39.4))
    lb = LEDS.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    lb.keyframe_insert("default_value", frame=T(39.4) - 1)
    lb.default_value = 0.0
    lb.keyframe_insert("default_value", frame=T(39.4))
    upd()
    FACE = axA.matrix_world @ axA.data.bones["Head"].head_local
    shot(of, "O1_exec", 11.5, 13.1, FACE + Vector((0.35, -2.4, 0.1)), FACE + Vector((0.1, -1.1, 0.05)), FACE + Vector((0, 0, 0.05)),
         FACE + Vector((0, 0, 0.05)), 26)
    shot(of, "O2_unplug", 37.1, 40.1, (1.0, -2.8, 1.5), (1.2, -2.7, 1.4), (2.5, -1.0, 0.9), (2.5, -1.0, 0.85), 20, shake=0.003)

# ================================================================= BOARD: conspiracy board
bd = L.new_set("BOARD")
with L.building(bd):
    P.flat_light(bd, "#120e0a", ambient=1.0, sun=0.6)
    D.area_light("bdlamp", 90, (0.3, -1.2, 2.3), (0, 0, 1.4), size=0.6, rgb=H("#ffd9a0"))
    D.box("bdwall", (8, 0.1, 5), (0, 0.15, 2.0), flat("bdw", "#2a2420"))
    plane("cork", 2.6, 1.7, (0, 0.09, 1.45), L.pbr("cork", "wood_table_001", scale=2, tint=H("#b07a46"), tint_amount=0.8))
    pos = {"pc": (-0.85, 1.9), "mods": (0.0, 1.95), "cows": (0.85, 1.85), "toilet": (-0.7, 1.0), "day1": (0.75, 1.05),
           "nopc": (0.02, 1.15)}
    for k, (x, z) in pos.items():
        cd = plane(f"card_{k}", 0.5, 0.39, (x, 0.07, z), img_mat(f"cardm_{k}", TEX(f"card_{k}.png"), lit=True, emit=0.6))
        cd.rotation_euler = (0, random.uniform(-0.12, 0.12), 0)
        D.sphere("pin", 0.018, (x, 0.05, z + 0.17), m=flat("pinr", "#e01b24", 0.5), seg=8, rings=4)
    RED = flat("string", "#e01b24", 0.8)
    for a, b in (("pc", "mods"), ("mods", "cows"), ("mods", "nopc"), ("pc", "toilet"), ("cows", "day1"), ("toilet", "nopc"),
                 ("day1", "nopc"), ("pc", "nopc")):
        pa, pb2 = pos[a], pos[b]
        cyl_between("str", (pa[0], 0.04, pa[1] + 0.17), (pb2[0], 0.04, pb2[1] + 0.17), 0.006, RED, verts=4)
    shot(bd, "B1_board", 13.1, 14.5, (0.6, -2.4, 1.4), (0.05, -1.05, 1.5), (0, 0.1, 1.45), (0, 0.1, 1.5), 22, shake=0.006)

# ================================================================= STREET: day one on PC
st = L.new_set("STREET")
with L.building(st):
    P.flat_light(st, "#ff9a6b", ambient=1.5, sun=1.3, sun_dir=(-0.5, 0.6, -0.7))
    D.box("asph", (8, 160, 0.02), (0, 20, 0), L.pbr("asph", "asphalt_02", scale=0.4))
    for k in range(30):
        D.box("dash", (0.15, 1.6, 0.005), (0, -20 + k * 5, 0.012), flat("dashm", "#f5f0d8", 0.3))
    for side in (-1, 1):
        D.box("walk", (3, 160, 0.16), (side * 5.5, 20, 0.08), flat("walkm", "#cfc6b8"))
        D.box("grass", (60, 160, 0.02), (side * 37, 20, -0.01), flat("grassm", "#5aa04a"))
    pastel = ["#ffb3c7", "#9de3d8", "#ffd8a8", "#c8b6ff", "#fff1a8", "#a8e6ff"]
    WIN = flat("swin", "#9fe0ff", 0.9)
    for side in (-1, 1):
        y = -14
        while y < 70:
            w, d, h = random.uniform(4, 7), random.uniform(5, 9), random.uniform(6, 18)
            x = side * (7.2 + w / 2)
            col = random.choice(pastel)
            D.box("bld", (w, d, h), (x, y + d / 2, h / 2),
                  L.pbr("bld" + col, "painted_plaster_wall", scale=0.4, tint=H(col), tint_amount=0.9))
            for row in range(int(h // 2.2)):
                for cc in range(int(d // 2)):
                    D.box("w", (0.05, 0.9, 1.0), (x - side * (w / 2 + 0.02), y + 1 + cc * 2, 1.6 + row * 2.2), WIN)
            y += d + random.uniform(0.3, 1.5)
    TRK, LEAF = flat("trunk", "#8a5a3a"), flat("leaf", "#2f9e44", 0.2)
    for k in range(16):
        side = -1 if k % 2 else 1
        p = D.empty("palm", (side * 4.6, -10 + k * 5.5, 0.16))
        p.rotation_euler = (random.uniform(-0.12, 0.12), side * random.uniform(0.05, 0.18), 0)
        tr = D.cyl("trunk", 0.15, 5.0, (0, 0, 0), m=TRK, verts=6)
        tr.parent, tr.location = p, (0, 0, 2.5)
        for j in range(7):
            lf = D.box("leaf", (2.0, 0.4, 0.05), (0, 0, 0), LEAF)
            lf.parent = p
            a = j / 7 * 2 * math.pi
            lf.location = (0.85 * math.cos(a), 0.85 * math.sin(a), 4.8)
            lf.rotation_euler = (0, 0.45, a)
    D.sphere("sundisc", 9, (-20, 140, 18), m=flat("sund", "#ffcf5a", 2.0), seg=16, rings=8)
    car = D.empty("car", (2.0, 7.0, 0))
    car.rotation_euler = (0, 0, math.radians(8))
    cbody, cms = prop(A("car.glb"), 4.1, 1, (0, 0, 0), keep=lambda o: not any(m and ("Hemi" in m.name or "shadow" in m.name)
                                                                              for m in o.data.materials), name="carbody")
    cbody.parent = car
    for o in cms:
        P.lowpoly(o, 2500, flat=True)
    # pedestrians → giants at 29.6
    giants = []
    for i, (loc, yaw, pose) in enumerate((((-2.6, 3.0, 0.16), math.radians(-20), LOOKDOWN), ((3.2, 1.0, 0.16), math.radians(25), LOOKDOWN),
                                          ((-1.2, 11.0, 0.0), math.radians(5), STAND))):
        r, a, _ = man(f"ped{i}", loc, yaw, 1.0)
        pose_strip(a, r, [(1, STAND), (T(30.5), STAND), (T(31.0), pose), (T(END), pose)], 1, T(END), blend=1)
        s = 6.5 - i * 0.8
        D.key(r, "scale", T(30.5), (1, 1, 1))
        D.overshoot(r, "scale", T(30.55 + i * 0.08), T(31.2 + i * 0.05), (1, 1, 1), (s, s, s), 1.12)
        giants.append(r)
    # raining cows
    cow0, cms0 = prop(A("cow.glb"), 1.4, 2, (0, 0, -100), tris=1500, name="cow0")
    for i in range(16):
        x, y = random.uniform(-3.5, 3.5), random.uniform(-3.0, 15.0)
        t0 = 31.95 + random.uniform(0, 1.6)
        g = dup(cms0, f"cow{i}", (x, y, 28), rot=(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6)))
        D.key(g, "scale", 1, (0, 0, 0), "CONSTANT")
        D.key(g, "scale", T(t0 - 0.05), (1, 1, 1), "CONSTANT")
        D.key(g, "location", T(t0), (x, y, 26))
        D.key(g, "location", T(t0 + 0.6), (x, y, 0.16))
        D.ease_last(g, "LINEAR")
        D.key(g, "location", T(t0 + 0.75), (x, y, 0.8))
        D.key(g, "location", T(t0 + 0.9), (x, y, 0.16))
        land = (0, 0, random.uniform(0, 6)) if random.random() < 0.6 else (math.pi / 2, 0, random.uniform(0, 6))
        D.key(g, "rotation_euler", T(t0), g.rotation_euler.copy())
        D.key(g, "rotation_euler", T(t0 + 0.6), land)
    # T-posing cops sliding across the street
    copmats = None
    for i in range(5):
        y0 = -9 + i * 0.4
        x = -2.2 + i * 1.1
        r, a, body = man(f"cop{i}", (x, y0, 0.0), 0.0, 1.0)
        if copmats is None:
            copmats = tint({m for b in body for m in b.data.materials}, H("#2b4cff"), 0.8)
        for b in body:
            for si, slot in enumerate(b.material_slots):
                if slot.material and slot.material.name in copmats:
                    b.material_slots[si].material = copmats[slot.material.name]
        pose_strip(a, r, [(1, TPOSE), (T(END), TPOSE)], 1, T(END), blend=1)
        hs = head_socket(a, r, f"cap{i}")
        cap = D.cyl(f"capc{i}", 0.105, 0.08, (0, 0, 0), m=flat("capm", "#101a40"), verts=10)
        cap.parent, cap.location = hs, (0, 0.02, 0.12)
        brim = D.box(f"capb{i}", (0.2, 0.09, 0.012), (0, 0, 0), flat("capm2", "#101a40"))
        brim.parent, brim.location = hs, (0, -0.085, 0.09)
        D.key(r, "scale", 1, (0, 0, 0), "CONSTANT")
        D.key(r, "scale", T(34.15), (1, 1, 1), "CONSTANT")
        z = 1.8 if i == 2 else 0.16
        D.key(r, "location", T(34.2), (x, y0, z))
        D.key(r, "location", T(37.1), (x, y0 + 6 + i * 0.4, z))
        D.ease_last(r, "LINEAR")
        for fc in D._fcurves(r.animation_data.action):
            if fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        if i == 2:
            D.key(r, "rotation_euler", T(34.2), (0, 0, 0))
            D.key(r, "rotation_euler", T(37.1), (0, math.radians(60), math.radians(720)))
    shot(st, "D0_day1", 26.1, 29.5, (6.0, -16.0, 1.6), (4.5, -18.0, 7.0), (0, 6, 2.2), (0, 10, 4.0), 20)
    shot(st, "D1_giant", 29.5, 31.9, (1.0, -6.5, 0.45), (1.6, -7.8, 0.7), (-1.0, 2.5, 4.0), (-1.0, 2.5, 9.0), 20, shake=0.012)
    shot(st, "D2_cows", 31.9, 34.2, (-4.5, -10.5, 2.6), (-3.8, -9.5, 2.2), (0, 5, 3.5), (0, 5, 1.6), 22)
    shot(st, "D3_cops", 34.2, 37.1, (7.0, -10.5, 2.0), (6.6, -9.0, 2.0), (0, -6.5, 1.3), (0, -4.0, 1.3), 22)
    shot(st, "D5_chaos", 40.1, END, (0.5, -9.0, 2.0), (0.5, -21.0, 11.0), (0, 4, 3.0), (0, 6, 5.0), 20)

# ---------------------------------------------------------------- PS2 pass
P.crunch_textures(512)
K.SHOTS.sort(key=lambda x: x[1])
json.dump(K.SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(K.SHOTS), [s.name for s in bpy.data.scenes])
