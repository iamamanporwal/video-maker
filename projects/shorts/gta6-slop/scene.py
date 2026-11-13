"""blender -b -P scene.py -- <out.blend>: "GTA 6 is AI slop" rage-bait short, PS2 look. Story time = VO time.

  0.0-3.7   official trailer (compose step, not Blender)
  ROOM      3.7 toddler types "make GTA 6" to Claude Opus 5.5 | screen close-ups 5.6 / 33.1 / 39.6 / 43.0 | 45.7 swivel + shades
  SLOP      7.7 crayon Vice City reveal | 9.6 toddler + car, shades drop ("that five-year-old cooked")
  PHONE     11.75 "ur ai slop bores me" comment (fake handle) | 37.35 "Bro." push-in
  MAP       15.4 MOM pin inflates over the map → DELAYED (2D stamp in compose)
  STONE     20.4 "PROMPT #1: MAKE ME A HORSE" tablet, hammer + chisel
  HOUSE     24.2 cottage → 5 wanted stars + police lights
  PERFUME   29.55 "OPUS 5.5 eau de prompt"
  SON       41.8 lumpy low-poly "son" rises on a pedestal
Cast: Renderpeople "Eric" (Sketchfab CC-BY); car: 1995 Fiat Punto GT (Sketchfab CC-BY). Everything else procedural.
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
END = 49.0
T, H = D.T, D.hex_lin
random.seed(11)
TEX = lambda n: os.path.join(HERE, "out", "tex", n)

base = D.reset(w=360, h=640, frames=T(END) - 1)
P.setup(base)
import kit as K  # noqa: E402  (after reset: kit only defines helpers)
from kit import flat, pop, vanish, shot, upd, man, pose_strip, own_vl, A, prop, SIT, STAND  # noqa: E402


# ---------------------------------------------------------------- helpers
def img_mat(name, path, lit=False, alpha=False, emit=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    tex.interpolation = "Closest"
    b = nt.nodes["Principled BSDF"]
    out_ = nt.nodes["Material Output"]
    if lit:
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 1.0
        if emit:
            nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = emit * 0.25
        return m
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = emit
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    if alpha:
        tr, mx = nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(tex.outputs["Alpha"], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out_.inputs["Surface"])
        m.surface_render_method = "DITHERED"
    else:
        nt.links.new(em.outputs[0], out_.inputs["Surface"])
    return m


def plane(name, w, h, loc, m, rot=(0, 0, 0)):
    """Textured card in the XZ plane, facing -Y, full 0-1 UVs (texture reads upright from -Y)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    me.materials.append(m)
    o = D.link(bpy.data.objects.new(name, me))
    o.location, o.rotation_euler = loc, rot
    return o


def star(name, r, loc, m, depth=0.08):
    pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.42
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    v = [(x, -depth / 2, z) for x, z in pts] + [(x, depth / 2, z) for x, z in pts] + [(0, -depth / 2, 0), (0, depth / 2, 0)]
    f = [(20, i, (i + 1) % 10) for i in range(10)] + [(21, 10 + (i + 1) % 10, 10 + i) for i in range(10)]
    f += [(i, 10 + i, 10 + (i + 1) % 10, (i + 1) % 10) for i in range(10)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.materials.append(m)
    o = D.link(bpy.data.objects.new(name, me))
    o.location = loc
    return o


def show(o, spans):
    """Visible only inside [(t0, t1)] spans (constant scale keys)."""
    s = tuple(o.scale)
    D.key(o, "scale", 1, (0, 0, 0), "CONSTANT")
    for a, b in spans:
        D.key(o, "scale", max(1, T(a)), s, "CONSTANT")
        D.key(o, "scale", T(b), (0, 0, 0), "CONSTANT")


def burst(name, origin, t, n=14, m=None, dist=0.4, dur=0.4, r=(0.008, 0.02), up=0.3):
    o = Vector(origin)
    for i in range(n):
        s = D.ico(f"{name}{i}", random.uniform(*r), origin, m=m, sub=1)
        d = Vector((random.uniform(-1, 1), random.uniform(-1, 0.2), random.uniform(-0.3, 1))).normalized()
        D.key(s, "scale", 1, (0, 0, 0), "CONSTANT")
        D.key(s, "scale", T(t), (1, 1, 1), "CONSTANT")
        D.key(s, "location", T(t), o)
        D.key(s, "location", T(t + dur), o + d * dist * random.uniform(0.5, 1) + Vector((0, 0, up * random.uniform(0, 1))))
        D.key(s, "scale", T(t + dur), (0, 0, 0), "CONSTANT")


def shades(arm, root, t_on, name):
    """Black pixel sunglasses bone-parented to Head; drop in from above at t_on."""
    own_vl(arm).update()
    R = root.matrix_world.to_quaternion().to_matrix().to_4x4()
    e = [arm.matrix_world @ arm.data.bones[b].head_local for b in ("eye_l_011", "eye_r_013")]
    s = D.empty(name + "_sock", (0, 0, 0))
    s.parent, s.parent_type, s.parent_bone = arm, "BONE", "Head"
    own_vl(arm).update()
    s.matrix_world = Matrix.Translation((e[0] + e[1]) / 2) @ R @ Matrix.Scale(root.scale.x, 4)
    g = D.empty(name, (0, 0, 0), parent=s)
    for nm, size, loc, m in (("lL", (0.05, 0.008, 0.032), (0.033, -0.028, 0), SHADE), ("lR", (0.05, 0.008, 0.032), (-0.033, -0.028, 0), SHADE),
                             ("br", (0.03, 0.006, 0.008), (0, -0.028, 0.01), SHADE), ("gl", (0.018, 0.004, 0.005), (0.042, -0.033, 0.008), GLINT),
                             ("tL", (0.005, 0.1, 0.008), (0.06, 0.02, 0.008), SHADE), ("tR", (0.005, 0.1, 0.008), (-0.06, 0.02, 0.008), SHADE)):
        o = D.box(f"{name}_{nm}", size, (0, 0, 0), m)
        o.parent, o.location = g, loc
    D.key(g, "scale", 1, (0, 0, 0), "CONSTANT")
    D.key(g, "scale", T(t_on), (1, 1, 1), "CONSTANT")
    D.key(g, "location", T(t_on), (0, 0, 0.35))
    D.key(g, "location", T(t_on + 0.22), (0, 0, 0), "CONSTANT")
    return g


def sit_on(root, arm, seat_z):
    own_vl(arm).update()
    hips = arm.matrix_world @ arm.data.bones["Hips"].head_local
    root.location.z += seat_z - hips.z + 0.03


CR = {}


def crayon(name):
    if name not in CR:
        CR[name] = img_mat("cr_" + name, TEX(f"cr_{name}.png"), lit=True, emit=0.6)
    return CR[name]


SHADE = flat("shade", "#0a0a0a")
GLINT = flat("glint", "#ffffff", 2.0)
YEL = flat("yel", "#ffd400", 1.4)
WHITE_E = flat("white_e", "#ffffff", 2.0)
TYPE_A = SIT | {"LeftArm": (0.22, -0.75, -0.45), "RightArm": (-0.22, -0.75, -0.45),
                "LeftForeArm": (-0.12, -1, 0.08), "RightForeArm": (0.12, -1, 0.0), "Head": (0, -0.05, 1)}
TYPE_B = TYPE_A | {"LeftForeArm": (-0.12, -1, 0.0), "RightForeArm": (0.12, -1, 0.1)}
SIT_COOL = SIT | {"LeftArm": (0.3, 0.05, -1), "RightArm": (-0.25, -0.75, -0.45), "RightForeArm": (0.15, -0.4, 0.9),
                  "Head": (0.0, -0.05, 1)}
COOL = STAND | {"LeftArm": (0.3, 0.1, -1), "RightArm": (-0.45, 0.05, -0.9), "Head": (0.0, -0.18, 1),
                "LeftForeArm": (0.2, -0.2, -1), "RightForeArm": (-0.2, -0.2, -1)}

# ================================================================= ROOM: toddler at the computer
room = L.new_set("ROOM", main=True)
P.flat_light(room, "#a9d6ff", ambient=1.5, sun=1.1)
D.room("kroom", (0, 0, 1.2), (4, 4, 2.4), L.pbr("kwall", "painted_plaster_wall", scale=0.8, tint=H("#9fd0ff"), tint_amount=0.85))
D.box("kfloor", (4, 4, 0.02), (0, 0, 0.0), crayon("orange"))
plane("draw_sun", 0.7, 0.7, (-0.9, -1.97, 1.45), img_mat("draw_sun", TEX("sun.png"), alpha=True), rot=(0, 0, math.pi))
plane("draw_a", 0.55, 0.4, (0.85, -1.97, 1.55), crayon("pink"), rot=(0, 0, math.pi))
plane("draw_b", 0.45, 0.6, (1.45, -1.97, 1.2), crayon("teal"), rot=(0, 0, math.pi))
plane("poster", 0.6, 0.9, (-1.2, 1.97, 1.4), crayon("orange"))
wood = L.pbr("kwood", "wood_table_001", scale=1.5, tint=H("#ffffff"), tint_amount=0.0)
D.box("desk", (0.9, 0.45, 0.04), (0, -0.42, 0.5), wood)
for x in (-0.42, 0.42):
    D.box("dleg", (0.04, 0.4, 0.48), (x, -0.42, 0.24), wood)
chair = D.empty("chair", (0, 0.05, 0))
for _o in (D.box("seat", (0.32, 0.32, 0.05), (0, 0.05, 0.28), flat("chair", "#e63946")),
           D.box("chback", (0.32, 0.04, 0.35), (0, 0.22, 0.47), flat("chair2", "#e63946"))):
    _o.parent = chair
    _o.location -= Vector((0, 0.05, 0))
D.cyl("chpole", 0.025, 0.26, (0, 0.05, 0.13), m=flat("pole", "#555555"), verts=8)
D.box("kbd", (0.34, 0.12, 0.02), (0, -0.32, 0.53), flat("kbd", "#2b2b33"))
D.box("mon", (0.44, 0.03, 0.29), (0, -0.565, 0.69), flat("monb", "#15151a"))
D.box("monst", (0.05, 0.03, 0.12), (0, -0.58, 0.58), flat("monb2", "#15151a"))
SCR = Vector((0, -0.548, 0.69))
SW, SH = 0.4, 0.25
scr = {}
for nm, spans in (("scr_gta", [(0, 33.1)]), ("scr_mom", [(33.1, 35.19)]), ("scr_refuse", [(35.19, 39.6)]),
                  ("scr_son", [(39.6, 43.0)]), ("scr_regen", [(43.0, END + 1)])):
    scr[nm] = plane(nm, SW, SH, SCR, img_mat(nm, TEX(nm + ".png")), rot=(0, 0, math.pi))
    show(scr[nm], spans)
# progress bar over scr_gta (texture bar x 40..760, y 330..380 of 800x500); screen faces +Y so texture x → world -x
bar = D.box("bar", (1, 0.004, (50 / 500) * SH * 0.8), (0, 0, 0), flat("barf", "#3d5afe", 1.5))
bar.data.transform(Matrix.Translation((-0.5, 0, 0)))          # origin at the bar's right end in mesh → grows toward -x
bx0 = SW / 2 - 40 / 800 * SW
bar.location = (bx0, SCR.y + 0.003, SCR.z + (0.5 - 355 / 500) * SH)
full = 720 / 800 * SW
for t, f in ((0, 0.0), (5.9, 0.02), (6.6, 0.35), (7.0, 0.42), (7.5, 1.0), (33.0, 1.0)):
    D.key(bar, "scale", T(t), (max(f * full, 0.0001), 1, 1))
D.key(bar, "scale", T(33.1), (0, 0, 0), "CONSTANT")
# cursor over the Regenerate button (button centre x=400, y=425)
cur = D.cone("cursor", 0.012, 0.03, (0, 0, 0), m=flat("curs", "#ffffff", 1.5), verts=3)
cur.rotation_euler = (0, math.radians(25), 0)
cur.scale = (1, 0.3, 1)
btn = Vector((0, SCR.y + 0.006, SCR.z + (0.5 - 425 / 500) * SH))
for t, p in ((43.0, (-0.14, 0, 0.06)), (43.5, (-0.1, 0, 0.03)), (43.9, (-0.005, 0, -0.005)), (44.35, (0.002, 0, -0.008)),
             (44.55, (0.0, 0, -0.006)), (44.9, (0.17, 0, 0.09)), (END, (0.17, 0, 0.09))):
    D.key(cur, "location", T(t), btn + Vector(p))
show(cur, [(43.0, END + 1)])

kid, karm, kbody = man("kid", (0, 0.05, 0), scale=0.5)
sit_on(kid, karm, 0.305)
shades(karm, kid, 46.8, "kshades")
keys = [(1, TYPE_A)]
t = 3.7
while t < 7.8:
    keys += [(T(t), TYPE_A), (T(t + 0.12), TYPE_B)]
    t += 0.24
keys += [(T(7.9), TYPE_A), (T(45.7), TYPE_A), (T(45.95), SIT_COOL), (T(END), SIT_COOL)]
pose_strip(karm, kid, keys, 1, T(END), blend=1)
D.key(kid, "rotation_euler", T(46.4), (0, 0, 0))
D.key(kid, "rotation_euler", T(46.68), (0, 0, math.pi * 1.04))
D.key(kid, "rotation_euler", T(46.8), (0, 0, math.pi))
for _t, _r in ((46.4, 0), (46.68, math.pi * 1.04), (46.8, math.pi)):
    D.key(chair, "rotation_euler", T(_t), (0, 0, _r))
scr_cam = dict(loc0=(0, -0.13, 0.69), loc1=(0, -0.17, 0.69), at0=(0, -0.55, 0.69), at1=(0, -0.55, 0.69), lens0=17)
shot(room, "K1_typing", 3.7, 5.6, (0.95, -0.05, 0.9), (0.8, -0.1, 0.82), (0, -0.25, 0.62), (0, -0.28, 0.64), 20)
shot(room, "K2_screen", 5.6, 7.7, **scr_cam)
shot(room, "K3_mom", 33.1, 37.35, **scr_cam)
shot(room, "K4_son", 39.6, 41.8, **scr_cam)
shot(room, "K5_regen", 43.0, 45.7, (0, -0.15, 0.66), (0, -0.25, 0.64), (0, -0.55, 0.66), (0, -0.55, 0.64), 17)
shot(room, "E1_reveal", 45.7, END, (0.25, 1.35, 0.85), (0.1, 0.85, 0.72), (0, 0.0, 0.62), (0, 0.05, 0.66), 24)

# ================================================================= SLOP: crayon Vice City
slop = L.new_set("SLOP")
with L.building(slop):
    P.flat_light(slop, "#ff9ec7", ambient=1.6, sun=1.2)
    D.box("ground", (120, 120, 0.02), (0, 0, -0.01), crayon("green"))
    D.box("road", (5, 120, 0.02), (0, 0, 0.0), crayon("road"))
    D.box("beach", (30, 6, 0.02), (14, 30, 0.005), crayon("sand"))
    for k in range(18):
        D.box("dash", (0.15, 1.2, 0.005), (random.uniform(-0.08, 0.08), -20 + k * 4, 0.012), flat("dashm", "#fff6a0", 0.4))
    cols = ["pink", "teal", "orange", "purple", "yellow", "blue", "red"]
    for side in (-1, 1):
        y = -6
        while y < 40:
            w, d, h = random.uniform(2, 4), random.uniform(2, 4), random.uniform(3, 11)
            x = side * (4.2 + w / 2 + random.uniform(0, 1.5))
            b = D.box("bld", (w, d, h), (x, y + d / 2, h / 2), crayon(random.choice(cols)))
            b.rotation_euler = (random.uniform(-0.06, 0.06), random.uniform(-0.08, 0.08), random.uniform(-0.15, 0.15))
            for _ in range(random.randint(3, 7)):              # wonky windows, some float off the wall
                wz = random.uniform(1, h - 0.5)
                wy = y + d / 2 + random.uniform(-d / 3, d / 3)
                off = 0 if random.random() > 0.2 else random.uniform(0.3, 1.2)
                D.box("win", (0.05, random.uniform(0.4, 0.9), random.uniform(0.4, 0.8)),
                      (x - side * (w / 2 + 0.03 + off), wy, wz), flat("winm", random.choice(("#fff3b0", "#7ad7ff")), 0.8))
            y += d + random.uniform(0.5, 2.5)
    for k in range(12):                                         # crooked crayon palm trees
        side = -1 if k % 2 else 1
        p = D.empty("palm", (side * random.uniform(2.9, 3.4), -4 + k * 3.2, 0))
        p.rotation_euler = (random.uniform(-0.25, 0.25), side * random.uniform(0.1, 0.35), 0)
        tr = D.cyl("trunk", 0.13, 3.6, (0, 0, 1.8), m=crayon("brown"), verts=6)
        tr.parent = p
        tr.location = (0, 0, 1.8)
        for j in range(6):
            lf = D.box("leaf", (1.5, 0.35, 0.06), (0, 0, 0), crayon("green"))
            lf.parent = p
            a = j / 6 * 2 * math.pi + random.uniform(-0.3, 0.3)
            lf.location = (0.6 * math.cos(a), 0.6 * math.sin(a), 3.5)
            lf.rotation_euler = (0, random.uniform(0.3, 0.7), a)
    sun = plane("sun", 14, 14, (-8, 55, 16), img_mat("sun_m", TEX("sun.png"), alpha=True, emit=1.4))
    D.key(sun, "rotation_euler", T(7.7), (0, math.radians(-8), 0))
    D.key(sun, "rotation_euler", T(11.75), (0, math.radians(8), 0))
    for k in range(5):
        c = D.ico("cloud", random.uniform(2, 3.5), (random.uniform(-25, 25), random.uniform(45, 60), random.uniform(10, 20)),
                  m=flat("cloudm", "#ffffff", 0.9), sub=1)
        c.scale = (1.8, 0.6, 0.7)
    car = D.empty("car", (0.9, 18, 0))
    cb, cms = prop(A("car.glb"), 4.1, 1, (0, 0, 0), keep=lambda o: not any(m and ("Hemi" in m.name or "shadow" in m.name)
                                                                           for m in o.data.materials), name="carbody")
    cb.parent = car
    for o in cms:
        P.lowpoly(o, 2500, flat=True)
    D.key(car, "location", T(7.7), (0.9, 22, 0))
    D.key(car, "location", T(9.4), (0.9, 1.2, 0))
    D.key(car, "rotation_euler", T(9.2), (0, 0, 0))
    D.key(car, "rotation_euler", T(9.45), (0, 0, math.radians(14)))
    D.key(car, "rotation_euler", T(9.6), (0, 0, math.radians(10)))
    kid2, k2arm, _ = man("kid2", (-1.0, -0.9, 0), math.radians(-12), 0.5)
    upd()
    shades(k2arm, kid2, 10.75, "k2shades")
    pose_strip(k2arm, kid2, [(1, STAND), (T(10.3), STAND), (T(10.6), COOL), (T(END), COOL)], 1, T(END), blend=1)
    shot(slop, "V1_reveal", 7.7, 9.6, (3.2, -7.5, 0.5), (2.6, -8.5, 4.2), (0, 8, 1.2), (0, 12, 4.5), 20)
    shot(slop, "V2_cooked", 9.6, 11.75, (-0.55, -2.5, 0.2), (-0.65, -2.1, 0.22), (-0.95, -0.9, 0.82), (-0.97, -0.9, 0.84), 20)

# ================================================================= PHONE: the comment
ph = L.new_set("PHONE")
with L.building(ph):
    P.flat_light(ph, "#1a0b2e", ambient=1.2, sun=1.0)
    D.area_light("phrim", 80, (1.5, 1.0, 2.5), (0, 0, 1), size=1.5, rgb=H("#ff3b6b"))
    phone = D.empty("phone", (0, 0, 1.0))
    phone.rotation_euler = (0, math.radians(-4), math.radians(6))
    body = D.box("phbody", (0.62, 0.06, 1.24), (0, 0, 0), flat("phb", "#111114"))
    body.parent = phone
    pscr = plane("phscr", 0.56, 1.12, (0, -0.031, 0), img_mat("comment", TEX("comment.png")))
    pscr.parent = phone
    for i in range(18):                                          # floating angry red pixels / embers
        e = D.ico("ember", random.uniform(0.01, 0.03), (random.uniform(-1.4, 1.4), random.uniform(0.2, 1.5), random.uniform(0, 2.2)),
                  m=flat("emb", "#ff3b3b", 1.5), sub=0)
        D.key(e, "location", T(11.75), e.location.copy())
        D.key(e, "location", T(39.6), e.location + Vector((0, 0, 0.6)))
    shot(ph, "P1_comment", 11.75, 15.4, (0.3, -2.4, 1.1), (0.04, -0.85, 1.07), (0, 0, 1.0), (0, 0, 1.05), 22)
    shot(ph, "P2_bro", 37.35, 39.6, (0, -1.4, 1.03), (0, -0.62, 1.03), (0, 0, 1.03), (0, 0, 1.03), 22, 26, shake=0.004)

# ================================================================= MAP: mom pin delays GTA 6
mp = L.new_set("MAP")
with L.building(mp):
    P.flat_light(mp, "#2b2d42", ambient=1.5, sun=1.2)
    D.box("table", (2.6, 2.6, 0.08), (0, 0, 0.72), L.pbr("mwood", "wood_table_001", scale=1.0))
    plane("map", 2.2, 2.2, (0, 0, 0.765), img_mat("map", TEX("map.png"), lit=True, emit=0.8), rot=(-math.pi / 2, 0, 0))
    pin = D.empty("pin", (-0.06, 0.26, 0.77))
    hd = D.sphere("pinhead", 0.08, (0, 0, 0), m=flat("pinm", "#ff2d95", 0.5), seg=10, rings=6)
    hd.parent, hd.location = pin, (0, 0, 0.2)
    nd = D.cone("pinneedle", 0.025, 0.14, (0, 0, 0), m=flat("pinn", "#cccccc"), verts=6)
    nd.parent, nd.location, nd.rotation_euler = pin, (0, 0, 0.07), (math.pi, 0, 0)
    D.key(pin, "scale", 1, (0, 0, 0), "CONSTANT")
    D.overshoot(pin, "scale", T(16.05), T(16.35), (0, 0, 0), (1, 1, 1), 1.3)
    for t, s in ((16.8, 1.4), (17.6, 2.4), (18.4, 3.6), (19.2, 5.2), (19.8, 7.0), (19.95, 12.0), (20.1, 10.5), (20.4, 11.0)):
        D.key(pin, "scale", T(t), (s, s, s))
    for i in range(9):                                            # toy buildings that get shoved off the map
        p0 = Vector((random.uniform(-0.25, 0.3), random.uniform(-0.6, 0.6), 0.77))
        hb = random.uniform(0.04, 0.12)
        b = D.box("toyb", (0.06, 0.06, hb), p0 + Vector((0, 0, hb / 2)), crayon(random.choice(("pink", "teal", "yellow", "purple"))))
        dirv = (p0 - Vector((-0.06, 0.26, 0.77))).normalized()
        D.key(b, "location", T(18.6), b.location.copy())
        D.key(b, "location", T(19.95), b.location + dirv * 1.6 + Vector((0, 0, 0.9)))
        D.key(b, "rotation_euler", T(18.6), (0, 0, 0))
        D.key(b, "rotation_euler", T(19.95), (3, 2, 1))
    shot(mp, "J1a_map", 15.4, 17.9, (0, -0.35, 2.9), (0, -0.4, 3.6), (0, 0.05, 0.76), (0, 0.05, 0.76), 22)
    shot(mp, "J1b_huge", 17.9, 20.4, (1.4, -2.3, 1.1), (2.4, -3.6, 1.9), (0, 0.2, 1.1), (0, 0.2, 2.0), 20, shake=0.003)

# ================================================================= STONE: first prompt carved in stone
st = L.new_set("STONE")
with L.building(st):
    P.flat_light(st, "#2a1a10", ambient=1.3, sun=1.0)
    D.area_light("torchL", 40, (-0.9, -0.6, 1.2), (0, 0, 0.5), size=0.5, rgb=H("#ff8a3d"))
    D.box("sand", (30, 30, 0.02), (0, 0, -0.01), crayon("sand"))
    D.box("tablet", (0.66, 0.14, 0.86), (0, 0, 0.43), flat("stone", "#8d8a83"))
    plane("tabface", 0.6, 0.8, (0, -0.072, 0.44), img_mat("tablet", TEX("tablet.png"), lit=True, emit=0.6))
    for x in (-0.75, 0.75):
        D.cyl("torch", 0.03, 0.9, (x, 0.1, 0.45), m=crayon("brown"), verts=6)
        fl = D.cone("flame", 0.07, 0.2, (x, 0.1, 1.0), m=flat("flame", "#ffb000", 2.5), verts=6)
        for k, s in enumerate((1, 1.25, 0.9, 1.15, 1.0)):
            D.key(fl, "scale", T(20.4 + k * 0.8), (1, 1, s))
    chisel = D.cyl("chisel", 0.012, 0.2, (0.2, -0.18, 0.2), rot=(math.radians(70), 0, 0), m=flat("steel", "#b0b4bb"), verts=6)
    hammer = D.empty("hammer", (0.3, -0.38, 0.12))
    hh = D.box("hhead", (0.12, 0.05, 0.05), (0, 0, 0), flat("hmet", "#5a5d63"))
    hh.parent, hh.location = hammer, (-0.05, 0.03, 0.2)
    hs = D.cyl("hstick", 0.012, 0.24, (0, 0, 0), m=crayon("brown"), verts=6)
    hs.parent, hs.location = hammer, (0, 0, 0.1)
    for th in (20.7, 21.3, 21.9, 22.5, 23.65):
        D.key(hammer, "rotation_euler", T(th - 0.2), (math.radians(-55), 0, 0))
        D.key(hammer, "rotation_euler", T(th), (math.radians(10), 0, 0))
        burst(f"dust{th}", (0.2, -0.1, 0.24), th, n=8, m=flat("dust", "#c9c3b5", 0.3), dist=0.25, dur=0.35)
    shot(st, "S1_tablet", 20.4, 24.2, (0.45, -2.1, 0.75), (0.2, -1.45, 0.55), (0, 0, 0.5), (0, 0, 0.47), 22)

# ================================================================= HOUSE: 5 stars in a cosy game
hs_ = L.new_set("HOUSE")
with L.building(hs_):
    P.flat_light(hs_, "#8fd3ff", ambient=1.6, sun=1.3)
    D.box("hgrass", (60, 60, 0.02), (0, 0, -0.01), crayon("green"))
    D.box("house", (2.2, 1.6, 1.4), (0, 0, 0.7), crayon("pink"))
    roof = D.cone("roof", 1.75, 1.0, (0, 0, 1.9), m=crayon("red"), verts=4)
    roof.rotation_euler = (0, 0, math.pi / 4)
    roof.scale = (1, 0.75, 1)
    D.box("door", (0.45, 0.04, 0.8), (0, -0.81, 0.4), crayon("brown"))
    for x in (-0.7, 0.7):
        D.box("hwin", (0.4, 0.04, 0.35), (x, -0.81, 0.9), flat("hwinm", "#fff3b0", 0.8))
    L.toy_tree((2.4, 1.0, 0), scale=0.7, seed=2)
    L.toy_tree((-2.6, 1.6, 0), scale=0.6, seed=5)
    L.bush((-1.4, -1.3, 0), scale=0.8, seed=1)
    L.bush((1.5, -1.2, 0), scale=0.7, seed=3)
    for i in range(5):
        s = star(f"star{i}", 0.26, ((i - 2) * 0.62, -0.4, 3.0 + (0.12 if i % 2 else 0)), YEL)
        D.key(s, "scale", 1, (0, 0, 0), "CONSTANT")
        D.overshoot(s, "scale", T(26.27 + i * 0.13), T(26.27 + i * 0.13 + 0.2), (0, 0, 0), (1, 1, 1), 1.35)
        D.key(s, "rotation_euler", T(26.3), (0, 0, 0))
        D.key(s, "rotation_euler", T(29.55), (0, 0, math.radians(40 if i % 2 else -40)))
    pc = D.empty("pcar", (-2.7, -2.2, 0))
    pc.rotation_euler = (0, 0, math.radians(35))
    pb, pms = prop(A("car.glb"), 4.1, 1, (0, 0, 0), keep=lambda o: not any(m and ("Hemi" in m.name or "shadow" in m.name)
                                                                           for m in o.data.materials), name="pcarbody")
    pb.parent = pc
    for o in pms:
        P.lowpoly(o, 2500, flat=True)
    upd()
    lo, hi = K.bounds(pms)
    red, blue = D.mat("sirR", H("#ff1a1a"), emit=H("#ff1a1a"), emit_strength=0), D.mat("sirB", H("#1a4dff"), emit=H("#1a4dff"), emit_strength=0)
    for x, m in ((-0.3, red), (0.3, blue)):
        o = D.box("siren", (0.5, 0.25, 0.14), (0, 0, 0), m)
        o.parent, o.location = pc, (x, 0.2, hi.z + 0.07)
    for k in range(int((29.6 - 26.9) / 0.15)):
        t = 26.9 + k * 0.15
        for m, on in ((red, k % 2 == 0), (blue, k % 2 == 1)):
            es = m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
            es.default_value = 6.0 if on else 0.2
            es.keyframe_insert("default_value", frame=T(t))
    shot(hs_, "H1_house", 24.2, 26.2, (0.3, -7.2, 1.5), (0.2, -6.2, 1.6), (0, 0, 1.4), (0, 0, 1.5), 22)
    shot(hs_, "H2_stars", 26.2, 29.55, (1.6, -4.8, 0.5), (1.2, -4.0, 0.6), (0.3, -0.5, 2.3), (0.3, -0.5, 2.5), 20, shake=0.004)

# ================================================================= PERFUME: OPUS 5.5 eau de prompt
pf = L.new_set("PERFUME")
with L.building(pf):
    P.flat_light(pf, "#1a0b2e", ambient=1.2, sun=1.0)
    D.area_light("pfspot", 120, (0.6, -0.8, 2.4), (0, 0, 0.9), size=0.8, rgb=H("#ffd9f0"))
    D.box("pffloor", (20, 20, 0.02), (0, 0, -0.01), flat("velvet", "#3c1053"))
    D.cyl("pedestal", 0.32, 0.8, (0, 0, 0.4), m=flat("ped", "#f2e9dc"), verts=12)
    D.torus("pedring", 0.32, 0.02, (0, 0, 0.8), m=flat("gold", "#d4af37", 0.8))
    bot = D.empty("bottle", (0, 0, 0.8))
    bb = D.box("bbody", (0.22, 0.12, 0.26), (0, 0, 0), flat("glass", "#ff8fd0", 0.7))
    bb.parent, bb.location = bot, (0, 0, 0.13)
    lab = plane("label", 0.17, 0.17, (0, 0, 0), img_mat("label", TEX("label.png"), emit=1.2))
    lab.parent, lab.location = bot, (0, -0.0615, 0.13)
    for nm, r_, h_, z in (("neck", 0.025, 0.04, 0.28), ("cap", 0.045, 0.07, 0.33)):
        c = D.cyl(nm, r_, h_, (0, 0, 0), m=flat("gold2", "#d4af37", 1.0), verts=8)
        c.parent, c.location = bot, (0, 0, z)
    D.key(bot, "rotation_euler", T(29.55), (0, 0, math.radians(-35)))
    D.key(bot, "rotation_euler", T(33.1), (0, 0, math.radians(30)))
    for i in range(14):
        sp = star(f"spark{i}", random.uniform(0.012, 0.025), (random.uniform(-0.4, 0.4), random.uniform(-0.25, 0.1), random.uniform(0.8, 1.35)),
                  WHITE_E, depth=0.004)
        t0 = 29.6 + random.uniform(0, 3.2)
        D.key(sp, "scale", 1, (0, 0, 0), "CONSTANT")
        D.key(sp, "scale", T(t0), (0, 0, 0))
        D.key(sp, "scale", T(t0 + 0.15), (1, 1, 1))
        D.key(sp, "scale", T(t0 + 0.35), (0, 0, 0))
    shot(pf, "F1_perfume", 29.55, 33.1, (0.25, -1.1, 1.02), (0.05, -0.55, 0.96), (0, 0, 0.94), (0, 0, 0.93), 24)

# ================================================================= SON: the un-regenerated son
sn = L.new_set("SON")
with L.building(sn):
    P.flat_light(sn, "#0b0b18", ambient=1.3, sun=0.9)
    D.area_light("snspot", 150, (0, -0.4, 2.6), (0, 0, 0.6), size=0.6, rgb=H("#bff3ff"))
    D.box("snfloor", (20, 20, 0.02), (0, 0, -0.01), flat("snfl", "#14142a"))
    D.cyl("snped", 0.42, 0.3, (0, 0, 0.15), m=flat("snpedm", "#222233"), verts=10)
    D.torus("snring", 0.42, 0.02, (0, 0, 0.3), m=flat("cyan", "#30f0ff", 2.0))
    son, sarm, sbody = man("son", (0, 0, 0.3), math.radians(8), 0.6)
    for b in sbody:                                              # crunch it to a lumpy blob
        md = b.modifiers.get("ps2_decimate") or b.modifiers.new("ps2_decimate", "DECIMATE")
        md.ratio = 0.005
        md.use_collapse_triangulate = True
    pose_strip(sarm, son, [(1, STAND | {"LeftArm": (0.9, -0.2, 0.4), "RightArm": (-1, 0.1, -0.2), "Head": (0.35, -0.1, 1)}),
                           (T(END), STAND | {"LeftArm": (0.9, -0.2, 0.4), "RightArm": (-1, 0.1, -0.2), "Head": (0.35, -0.1, 1)})],
               1, T(END), blend=1)
    hb = sarm.pose.bones["Head"]
    hb.scale = (1.6, 1.6, 1.6)
    hb.keyframe_insert("scale", frame=1)
    D.key(son, "location", T(41.8), (0, 0, -1.3))
    D.overshoot(son, "location", T(41.8), T(42.1), (0, 0, -1.3), (0, 0, 0.3), 1.0)
    for t, z in ((42.1, 8), (42.5, -6), (43.0, 10)):
        D.key(son, "rotation_euler", T(t), (0, 0, math.radians(z)))
    shot(sn, "N1_son", 41.8, 43.0, (0.45, -2.3, 0.85), (0.3, -1.85, 0.8), (0, 0, 0.75), (0, 0, 0.78), 24)

# ---------------------------------------------------------------- PS2 pass
P.crunch_textures(512)
K.SHOTS.sort(key=lambda x: x[1])
json.dump(K.SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(K.SHOTS), [s.name for s in bpy.data.scenes])
