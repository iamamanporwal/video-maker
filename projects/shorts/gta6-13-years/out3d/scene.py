"""blender -b -P scene.py -- <shot> <out.blend>: props-only 3D inserts for "Why did GTA 6 take 13 years?".

Shots (1080x1920, 30 fps, no text / numbers / logos; 2D text is overlaid later):
  calendar   4 s  tear-off desk calendar, blank pages flying off, sunset through blinds, push-in
  consoles   4 s  three generic consoles drop onto a pedestal (0.4 / 1.3 / 2.2 s), dust puffs, low-angle push-in
  printer    4 s  chunky money printer spitting procedural green bills that arc out and pile up
  hourglass  3 s  glass hourglass, orange-gold sand draining, teal/pink rims, 20 deg orbit
  vault      3 s  round vault door swinging open, pink/orange light spilling out, dust motes
Palette: hot pink #FF3E9A, orange #FF9A3C, teal #19C3B5, money green #6FDB6A, deep ink #07080C.
"""
import math, os, random, sys
import numpy as np
import bpy
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "src", "reelforge", "blender"))
import director as D
import look as L
from director import T

args = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = args[0], args[1]
DUR = {"calendar": 4.0, "consoles": 4.0, "printer": 4.0, "hourglass": 3.0, "vault": 3.0}[SHOT]
NF = int(round(DUR * 30))
H = D.hex_lin
PINK, ORANGE, TEAL, GREEN, INK = H("#FF3E9A"), H("#FF9A3C"), H("#19C3B5"), H("#6FDB6A"), H("#07080C")
random.seed(7)
np.random.seed(7)

sc = D.reset(frames=NF)
D.fast_eevee(sc, samples=10, look="AgX - Punchy")
sc.name = SHOT


# ---------------------------------------------------------------- helpers

def spot(name, power, loc, target, rgb, size_deg=45, blend=0.3, radius=0.05):
    l = D.link(bpy.data.objects.new(name, bpy.data.lights.new(name, "SPOT")))
    l.data.energy, l.data.color = power, rgb
    l.data.spot_size, l.data.spot_blend = math.radians(size_deg), blend
    l.data.shadow_soft_size = radius
    l.location = loc
    l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return l


def card(name, w, h, m, plane="XZ", hinge_top=False, thick=0.0):
    """Flat quad with UVs. XZ faces -Y (camera side); hinge_top puts the origin on the top edge."""
    if plane == "XZ":
        z0, z1 = (-h, 0) if hinge_top else (-h / 2, h / 2)
        verts = [(-w / 2, 0, z0), (w / 2, 0, z0), (w / 2, 0, z1), (-w / 2, 0, z1)]
    else:
        verts = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    o = D.link(bpy.data.objects.new(name, me))
    D.give(o, m)
    if thick:
        s = o.modifiers.new("solid", "SOLIDIFY")
        s.thickness, s.offset = thick, 0
    return o


def img_mat(name, arr, rough=0.55, coat=0.0, bump=0.0, emit=0.0):
    """numpy HxWx3 (sRGB 0-1) → packed image → material on UVs."""
    h, w, _ = arr.shape
    im = bpy.data.images.new(name, w, h, alpha=True)
    rgba = np.concatenate([arr, np.ones((h, w, 1))], axis=2)[::-1]      # Blender rows go bottom-up
    im.pixels.foreach_set(rgba.astype(np.float32).ravel())
    im.pack()
    m = D.mat(name, (1, 1, 1), rough=rough)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = im
    t.interpolation = "Cubic"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if bump:
        bw = nt.nodes.new("ShaderNodeBump")
        bw.inputs["Strength"].default_value = bump
        bw.inputs["Distance"].default_value = 0.0005
        nt.links.new(t.outputs["Color"], bw.inputs["Height"])
        nt.links.new(bw.outputs["Normal"], b.inputs["Normal"])
    if emit:
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    return m


def metal(name, rgb, rough=0.25):
    return D.mat(name, rgb, rough=rough, metal=1.0)


def glow(name, rgb, strength):
    m = D.mat(name, rgb, rough=0.4, emit=rgb, emit_strength=strength)
    return m


def noisy(name, rgb, rough=0.6, scale=60.0, bump=0.25, var=0.25):
    """Colour with fine noise variation + bump (sand, dust, felt)."""
    m = D.mat(name, rgb, rough=rough)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 6
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = var
    mix.inputs[6].default_value = (*rgb, 1)
    nt.links.new(n.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    nt.links.new(n.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def bake(o, f, loc=None, rot=None, scale=None):
    if loc is not None:
        o.location = loc
        o.keyframe_insert("location", frame=f)
    if rot is not None:
        o.rotation_euler = rot
        o.keyframe_insert("rotation_euler", frame=f)
    if scale is not None:
        o.scale = (scale,) * 3 if isinstance(scale, (int, float)) else scale
        o.keyframe_insert("scale", frame=f)


def linear(o, interp="LINEAR"):
    if o.animation_data and o.animation_data.action:
        for fc in D._fcurves(o.animation_data.action):
            for k in fc.keyframe_points:
                k.interpolation = interp


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def push(cam_name, loc0, loc1, at0, at1, lens, shake=0.003, f0=1, f1=None):
    c, l = D.camera(cam_name, lens)
    D.move(c, l, f0, f1 or NF, loc0, loc1, at0, at1)
    for o in (c, l):                                         # gentle constant-ish drift: ease-out only
        for fc in D._fcurves(o.animation_data.action):
            for k in fc.keyframe_points:
                k.interpolation, k.easing = "SINE", "EASE_OUT"
    if shake:
        D.handheld(l, shake, scale=60, seed=3)
    sc.camera = c
    return c, l


def volume_box(size, center, density, rgb=(1, 1, 1), aniso=0.4):
    o = D.box("haze", size, center)
    m = bpy.data.materials.new("haze")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = density
    v.inputs["Color"].default_value = (*rgb, 1)
    v.inputs["Anisotropy"].default_value = aniso
    nt.links.new(v.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    D.give(o, m)
    o.visible_shadow = False
    e = sc.eevee
    for k, val in (("use_volumetric_shadows", True), ("volumetric_tile_size", "8"), ("volumetric_samples", 48),
                   ("volumetric_shadow_samples", 8)):
        if hasattr(e, k):
            try:
                setattr(e, k, val)
            except Exception:
                pass
    return o


def dark_world(rgb, strength, hdri=True):
    if hdri:
        L.hdri_world(sc, "studio_small_09", strength, rot_deg=30, backdrop=rgb, backdrop_strength=1.0)
    else:
        D.world(sc, rgb, strength)


# ---------------------------------------------------------------- textures (numpy)

def page_texture(w=320, h=420, seed=0):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    paper = np.array([0.95, 0.92, 0.84])
    a = np.ones((h, w, 3)) * paper
    a *= (1 - 0.04 * rng.random((h, w, 1)))                                   # paper grain
    head = y < h * 0.2
    a[head] = np.array([1.0, 0.24, 0.6])                                       # hot-pink header band
    a[(y > h * 0.2) & (y < h * 0.215)] = np.array([0.55, 0.1, 0.3])
    a[(np.abs(y - h * 0.10) < h * 0.014) & (np.abs(x - w / 2) < w * 0.30)] = np.array([1, 0.85, 0.92])  # header line
    # abstract "big day" block: one wide ink slab with two thin scribble lines under it (no digit, no face)
    a[(y > h * 0.27) & (y < h * 0.40) & (np.abs(x - w / 2) < w * 0.34)] = np.array([0.08, 0.08, 0.12])
    for ly, lw in ((0.45, 0.30), (0.50, 0.22)):
        a[(np.abs(y - h * ly) < h * 0.008) & (np.abs(x - w / 2) < w * lw)] = np.array([0.45, 0.42, 0.44])
    # grid of thin lines (week rows)
    gy0, gy1, gx0, gx1 = h * 0.58, h * 0.94, w * 0.08, w * 0.92
    grid = (y > gy0) & (y < gy1) & (x > gx0) & (x < gx1)
    rows = np.abs(((y - gy0) / ((gy1 - gy0) / 5)) % 1) < 0.035
    cols = np.abs(((x - gx0) / ((gx1 - gx0) / 7)) % 1) < 0.03
    a[grid & (rows | cols)] = np.array([0.55, 0.52, 0.5])
    a[(y > h * 0.55) & (y < h * 0.565) & (x > gx0) & (x < gx1)] = np.array([1.0, 0.6, 0.24])  # orange rule
    cxm = gx0 + (gx1 - gx0) / 7 * (2.5 + (seed % 3) * 1.5)
    cym = gy0 + (gy1 - gy0) / 5 * (1.5 + seed % 2)
    rr = np.sqrt(((x - cxm) / (w * 0.09)) ** 2 + ((y - cym) / (h * 0.055)) ** 2)
    a[np.abs(rr - 1) < 0.12] = np.array([0.9, 0.1, 0.25])                    # red "deadline" marker ring
    return np.clip(a, 0, 1)


def bill_texture(w=600, h=256):
    y, x = np.mgrid[0:h, 0:w].astype(float)
    u, v = x / w, y / h
    base = np.array([0.36, 0.66, 0.34])
    dark = np.array([0.09, 0.30, 0.14])
    light = np.array([0.78, 0.93, 0.72])
    a = np.ones((h, w, 3)) * base
    # guilloche waves
    g = (np.sin(u * 90 + np.sin(v * 12) * 3) * np.sin(v * 70 + np.cos(u * 9) * 2))
    a += (g[..., None] * 0.07)
    border = (u < 0.035) | (u > 0.965) | (v < 0.08) | (v > 0.92)
    a[border] = dark
    inner = ((np.abs(u - 0.035) < 0.006) | (np.abs(u - 0.965) < 0.006) | (np.abs(v - 0.08) < 0.014) |
             (np.abs(v - 0.92) < 0.014)) & (u > 0.03) & (u < 0.97) & (v > 0.07) & (v < 0.93)
    a[inner] = light
    # central oval portrait frame (empty, just rings)
    r = np.sqrt(((u - 0.5) / 0.17) ** 2 + ((v - 0.5) / 0.33) ** 2)
    a[r < 1] = a[r < 1] * 0.6 + light * 0.4
    a[np.abs(r - 1) < 0.05] = dark
    a[np.abs(r - 0.82) < 0.025] = dark
    # corner rosettes
    for cu, cv in ((0.13, 0.27), (0.87, 0.27), (0.13, 0.73), (0.87, 0.73)):
        rr = np.sqrt(((u - cu) * w) ** 2 + ((v - cv) * h) ** 2) / (h * 0.15)
        m = rr < 1
        a[m] = dark * 0.6 + base * 0.4 + (np.sin(np.arctan2(v - cv, u - cu)[m] * 14)[:, None] * 0.08)
        a[np.abs(rr - 1) < 0.08] = light
    # side lines
    for vv in (0.42, 0.5, 0.58):
        a[(np.abs(v - vv) < 0.008) & (((u > 0.22) & (u < 0.3)) | ((u > 0.7) & (u < 0.78)))] = dark
    return np.clip(a, 0, 1)


# ================================================================ SHOTS

def calendar():
    dark_world(H("#0b0710"), 0.06)
    sc.view_settings.look = "AgX - Punchy"
    wall_m = L.pbr("wall", "plastered_wall", scale=1.2, tint=H("#3a1f3d"), tint_amount=0.85)
    desk_m = L.pbr("desk", "wood_table_001", scale=1.6, tint=H("#6b3a24"), tint_amount=0.35, clearcoat=0.25)
    D.box("desk", (4, 2.4, 0.06), (0, 0.4, -0.03), desk_m)
    D.box("wall", (6, 0.1, 4), (0, 1.0, 1.5), wall_m)
    ink = L.plastic("stand", H("#14101c"), rough=0.3, coat=0.6)
    brass = metal("brass", H("#d9a441"), 0.25)
    pinkp = L.plastic("pinkp", PINK, rough=0.3, coat=0.5)
    # stand: slanted base + back board
    base = D.box("base", (0.42, 0.20, 0.06), (0, 0.05, 0.03), ink, bevel=0.012)
    D.box("trim", (0.425, 0.205, 0.006), (0, 0.05, 0.062), pinkp, bevel=0.002)
    TILT = math.radians(-12)
    piv = D.empty("piv", (0, 0.08, 0.06))
    piv.rotation_euler = (TILT, 0, 0)
    back = D.box("back", (0.36, 0.035, 0.46), (0, 0.02, 0.23), ink, bevel=0.01)
    back.parent = piv
    paper_side = noisy("paperside", H("#efe7d6"), rough=0.8, scale=900, bump=0.4, var=0.2)
    block = D.box("block", (0.30, 0.03, 0.38), (0, -0.012, 0.21), paper_side, bevel=0.003)
    block.parent = piv
    for i, xx in enumerate((-0.08, 0.08)):                          # binding rings
        r = D.torus(f"ring{i}", 0.018, 0.0035, (xx, -0.03, 0.40), rot=(0, math.pi / 2, 0), m=brass)
        r.parent = piv
    pages = []
    NP = 18
    mats = [img_mat(f"page{k}", page_texture(seed=k), rough=0.7, bump=0.15) for k in range(3)]
    for i in range(NP):
        p = card(f"page{i}", 0.30, 0.38, mats[i % 3], hinge_top=True, thick=0.0012)
        p.parent = piv
        y = -0.028 - (NP - i) * 0.0013
        p.location = (0, y, 0.40)
        pages.append(p)
    # tear-off: top page first (i = NP-1), one every ~0.19 s from 0.25 s
    order = list(reversed(pages))
    for k, p in enumerate(order[:-1]):
        t0 = 0.25 + k * 0.19
        f0 = T(t0)
        rest = p.location.copy()
        side = random.choice((-1, 1))
        spin = random.uniform(-1, 1)
        bake(p, 1, loc=rest, rot=(0, 0, 0))
        bake(p, f0, loc=rest, rot=(0, 0, 0))
        for j in range(1, 46):
            f = f0 + j
            if f > NF + 2:
                break
            s = j / 45
            lift = ease(min(1, j / 6))
            rx = -1.9 * lift - 1.2 * s                              # flip up toward camera over the hinge
            loc = (rest.x + side * (0.75 * s ** 1.3), rest.y - 0.12 * lift - 0.55 * s, rest.z + 0.06 * lift + 0.45 * s - 0.25 * s * s)
            bake(p, f, loc=loc, rot=(rx, spin * 3.0 * s, side * 2.2 * s * s + spin * s))
        linear(p)
    # props: mug, pen, ashtray-ish dish, slatted light
    mug = D.cyl("mug", 0.045, 0.1, (0.32, -0.05, 0.05), m=L.plastic("mugm", ORANGE, rough=0.35, coat=0.5), verts=32)
    D.cyl("coffee", 0.04, 0.005, (0.32, -0.05, 0.096), m=D.mat("coffee", H("#2a140a"), rough=0.1), verts=32)
    D.torus("handle", 0.028, 0.008, (0.37, -0.05, 0.05), rot=(math.pi / 2, 0, 0), m=mug.data.materials[0])
    pen = D.cyl("pen", 0.006, 0.18, (-0.3, -0.12, 0.007), rot=(0, math.pi / 2, 0.5), m=L.plastic("penm", TEAL, rough=0.3))
    D.cyl("pencap", 0.0065, 0.04, (-0.3 + 0.07 * math.cos(0.5), -0.12 + 0.07 * math.sin(0.5), 0.007),
          rot=(0, math.pi / 2, 0.5), m=brass)
    for k in range(4):                                              # torn pages already on desk
        q = card(f"torn{k}", 0.30, 0.38, mats[k % 3], plane="XY", thick=0.001)
        q.location = (random.uniform(-0.45, 0.45), random.uniform(-0.35, -0.15), 0.002 + k * 0.0015)
        q.rotation_euler = (0, 0, random.uniform(-1.2, 1.2))
    # sunset through blinds: hard spot behind slats (slats invisible to camera)
    sp = spot("sunset", 3200, (-2.2, -1.6, 1.7), (0.1, 0.4, 0.25), H("#ff7a3a"), size_deg=55, blend=0.1, radius=0.01)
    piv_l = Vector((-2.2, -1.6, 1.7))
    to = (Vector((0.1, 0.4, 0.25)) - piv_l).normalized()
    for k in range(14):
        c = piv_l + to * 0.55
        sl = D.box(f"slat{k}", (0.9, 0.02, 0.012), (c.x, c.y, c.z - 0.3 + k * 0.045))
        sl.rotation_euler = (math.radians(-20), 0, math.atan2(to.y, to.x) + math.pi / 2)
        sl.visible_camera = False
        sl.visible_glossy = False
    D.area_light("pinkfill", 60, (1.2, -1.0, 0.8), (0, 0.1, 0.2), size=1.5, rgb=PINK)
    D.area_light("tealrim", 110, (0.9, 0.7, 0.9), (0, 0, 0.25), size=0.8, rgb=TEAL)
    D.area_light("tealbounce", 35, (1.6, -0.6, 0.15), (0, 0.2, 0.2), size=1.5, rgb=TEAL)
    D.area_light("front", 12, (0, -1.5, 0.5), (0, 0, 0.2), size=2.0, rgb=H("#ffd9b0"))
    volume_box((4, 3.5, 3), (0, 0, 1.4), 0.06, rgb=H("#ffd2b0"))
    push("cam", (0.22, -1.35, 0.42), (0.12, -0.95, 0.36), (0.0, 0.05, 0.26), (0.0, 0.05, 0.27), lens=42)
    L.post(sc, bloom=0.55, bloom_threshold=0.85, vignette=0.32, saturation=1.12, contrast=0.06)


def consoles():
    dark_world(H("#120a1c"), 0.25)
    cyc = L.plastic("cyc", H("#2a1238"), rough=0.75, coat=0.0)
    D.cyclorama(cyc, width=30, depth=20, y_wall=4, radius=2.5, height=14)
    ink = L.plastic("pedink", H("#12101a"), rough=0.22, coat=0.8)
    concrete = L.pbr("ped", "concrete_floor_02", scale=1.5, tint=H("#3c2b4a"), tint_amount=0.6)
    D.cyl("ped", 1.5, 0.9, (0, 0, 0.45), m=concrete, verts=96)
    D.cyl("pedtop", 1.52, 0.06, (0, 0, 0.93), m=ink, verts=96)
    D.torus("pedring", 1.52, 0.012, (0, 0, 0.9), m=glow("ringglow", PINK, 6.0))
    D.torus("pedring2", 1.52, 0.008, (0, 0, 0.6), m=glow("ringglow2", ORANGE, 4.0))
    TOP = 0.96
    gloss = L.plastic("gloss", H("#0c0c10"), rough=0.12, coat=1.0)
    matte = L.plastic("matte", H("#1b1b22"), rough=0.45, coat=0.2)
    white = L.plastic("whitec", H("#f3f1ee"), rough=0.3, coat=0.5)
    led_g = glow("ledg", GREEN, 8)
    led_b = glow("ledb", TEAL, 8)
    led_p = glow("ledp", PINK, 8)

    def grp(name, x):
        g = D.empty(name, (x, 0, TOP))
        g.delta_scale = (1.32, 1.32, 1.32)
        return g

    # A: old curvy glossy black (fat rounded slab with a hump)
    A = grp("A", -0.8)
    a1 = D.box("a_body", (0.62, 0.48, 0.16), (0, 0, 0.08), gloss, bevel=0.07)
    a2 = D.box("a_hump", (0.46, 0.4, 0.14), (0, 0.02, 0.19), gloss, bevel=0.06)
    a3 = D.box("a_strip", (0.5, 0.01, 0.012), (0, -0.242, 0.09), led_g, bevel=0.004)
    a4 = D.cyl("a_disc", 0.12, 0.012, (0.06, 0.02, 0.265), m=matte, verts=48)
    for o in (a1, a2, a3, a4):
        o.parent = A
    # B: slim flat black (lying, wedge-ish slab)
    B = grp("B", 0.0)
    b1 = D.box("b_body", (0.62, 0.42, 0.08), (0, 0, 0.04), matte, bevel=0.012)
    b2 = D.box("b_top", (0.6, 0.4, 0.012), (0, 0, 0.086), gloss, bevel=0.005)
    b3 = D.box("b_led", (0.008, 0.008, 0.05), (0.27, -0.212, 0.04), led_b)
    b4 = D.box("b_slot", (0.3, 0.004, 0.006), (-0.05, -0.211, 0.05), led_b)
    for o in (b1, b2, b3, b4):
        o.parent = B
    # C: tall white + black modern tower (two white shells, black core)
    C = grp("C", 0.8)
    c1 = D.box("c_core", (0.16, 0.36, 0.62), (0, 0, 0.31), gloss, bevel=0.01)
    c2 = D.box("c_shellL", (0.05, 0.38, 0.66), (-0.1, 0, 0.33), white, bevel=0.022)
    c3 = D.box("c_shellR", (0.05, 0.38, 0.66), (0.1, 0, 0.33), white, bevel=0.022)
    c4 = D.box("c_led", (0.12, 0.004, 0.006), (0, -0.185, 0.6), led_p)
    c5 = D.cyl("c_vent", 0.06, 0.01, (0, 0, 0.625), m=matte, verts=32)
    for o in (c1, c2, c3, c4, c5):
        o.parent = C
    for o in (b1, b2, b3, b4):                                   # stand the slim console on its edge, broad face 3/4 to camera
        o.matrix_parent_inverse = (Matrix.Rotation(math.radians(-62), 4, "Z") @ Matrix.Translation((0, 0, 0.31))
                                   @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    C.rotation_euler = (0, 0, math.radians(-12))
    A.rotation_euler = (0, 0, math.radians(14))
    dust_m = noisy("dust", H("#c9a78f"), rough=0.9, scale=8, bump=0.6, var=0.4)
    spots = []
    for k, (g, t, x) in enumerate(((A, 0.4, -0.8), (B, 1.3, 0.0), (C, 2.2, 0.8))):
        f = T(t)
        rz = g.rotation_euler.z
        g.location = (x, 0, TOP + 5.6)
        g.keyframe_insert("location", frame=1)
        g.keyframe_insert("location", frame=f - 9)
        for j, (dz, sq) in enumerate(((0, 1.0), (0.0, 1.0), (0.09, 1.0), (0, 1.0), (0.02, 1.0), (0, 1.0))):
            fr = f + (0, 0, 4, 8, 11, 14)[j]
            if j == 0:
                fr = f
            g.location = (x, 0, TOP + dz)
            g.keyframe_insert("location", frame=fr)
        # squash on landing
        g.scale = (1, 1, 1)
        g.keyframe_insert("scale", frame=f - 1)
        g.scale = (1.06, 1.06, 0.86)
        g.keyframe_insert("scale", frame=f + 1)
        g.scale = (0.98, 0.98, 1.04)
        g.keyframe_insert("scale", frame=f + 5)
        g.scale = (1, 1, 1)
        g.keyframe_insert("scale", frame=f + 9)
        g.rotation_euler = (0, 0, rz + 0.25)
        g.keyframe_insert("rotation_euler", frame=f - 9)
        g.rotation_euler = (0.03 * (1 if k % 2 else -1), 0, rz)
        g.keyframe_insert("rotation_euler", frame=f + 2)
        g.rotation_euler = (0, 0, rz)
        g.keyframe_insert("rotation_euler", frame=f + 8)
        for fc in D._fcurves(g.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
            for kp in fc.keyframe_points:
                if fc.data_path == "location" and abs(kp.co[0] - (f - 9)) < 0.5:
                    kp.interpolation, kp.easing = "QUAD", "EASE_IN"        # gravity fall
        # dust puff
        for d in range(36):
            ang = d / 36 * math.tau + random.uniform(-0.15, 0.15)
            rad = random.uniform(0.35, 0.55)
            o = D.ico(f"dust{k}_{d}", 1.0, (x, 0, TOP + 0.02), dust_m, sub=2)
            sz = random.uniform(0.008, 0.02)
            o.visible_shadow = False
            bake(o, 1, scale=0.0)
            bake(o, f - 1, loc=(x + math.cos(ang) * rad * 0.5, math.sin(ang) * rad * 0.5, TOP + 0.03), scale=0.0)
            bake(o, f + 3, loc=(x + math.cos(ang) * rad * 0.9, math.sin(ang) * rad * 0.9, TOP + 0.06), scale=sz)
            bake(o, f + 18, loc=(x + math.cos(ang) * rad * 1.6, math.sin(ang) * rad * 1.6, TOP + 0.14 + random.uniform(0, 0.08)), scale=sz * 1.4)
            bake(o, f + 30, loc=(x + math.cos(ang) * rad * 1.8, math.sin(ang) * rad * 1.8, TOP + 0.2), scale=0.0)
        pf = D.ico(f"puff{k}", 1.0, (x, -0.05, TOP + 0.1), sub=3)
        pf.visible_shadow = False
        pm = bpy.data.materials.new(f"puffm{k}")
        pm.use_nodes = True
        pnt = pm.node_tree
        pnt.nodes.remove(pnt.nodes["Principled BSDF"])
        vv = pnt.nodes.new("ShaderNodeVolumePrincipled")
        vv.inputs["Color"].default_value = (*H("#d8b8a8"), 1)
        nz = pnt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 3.0
        mm = pnt.nodes.new("ShaderNodeMath")
        mm.operation = "MULTIPLY"
        pnt.links.new(nz.outputs["Fac"], mm.inputs[0])
        pnt.links.new(mm.outputs[0], vv.inputs["Density"])
        pnt.links.new(vv.outputs[0], pnt.nodes["Material Output"].inputs["Volume"])
        D.give(pf, pm)
        for fr, dens in ((1, 0.0), (f - 1, 0.0), (f + 2, 6.0), (f + 14, 2.0), (f + 28, 0.0)):
            mm.inputs[1].default_value = dens
            mm.inputs[1].keyframe_insert("default_value", frame=fr)
        bake(pf, 1, scale=(0.3, 0.3, 0.1))
        bake(pf, f - 1, scale=(0.3, 0.3, 0.1))
        bake(pf, f + 4, scale=(0.75, 0.6, 0.18))
        bake(pf, f + 28, scale=(1.05, 0.85, 0.32))
        # spotlight per drop (fade up just before landing)
        col = (H("#ffb37a"), H("#ff7ab8"), H("#8af0e6"))[k]
        s = spot(f"spot{k}", 0, (x * 1.1, -0.6, TOP + 3.2), (x, 0, TOP), col, size_deg=30, blend=0.35, radius=0.08)
        s.data.keyframe_insert("energy", frame=1)
        s.data.keyframe_insert("energy", frame=f - 5)
        s.data.energy = 2600
        s.data.keyframe_insert("energy", frame=f + 1)
        s.data.energy = 1300
        s.data.keyframe_insert("energy", frame=f + 15)
    D.area_light("key", 250, (-2.5, -3.5, 2.6), (0, 0, 1.2), size=3, rgb=H("#ffd7b5"))
    D.area_light("rimL", 600, (-3, 2.5, 2.0), (0, 0, 1.2), size=2, rgb=PINK)
    D.area_light("rimR", 600, (3, 2.5, 2.0), (0, 0, 1.2), size=2, rgb=TEAL)
    D.area_light("wallwash", 2500, (0, 2.3, 0.4), (0, 4, 3.0), size=4, rgb=ORANGE)
    D.area_light("wallwash2", 1500, (0, 2.3, 5.5), (0, 4, 3.0), size=4, rgb=PINK)
    push("cam", (0.0, -3.0, 1.08), (0.0, -2.55, 1.1), (0, 0, 1.42), (0, 0, 1.4), lens=19)
    L.post(sc, bloom=0.6, bloom_threshold=0.85, vignette=0.28, saturation=1.12, contrast=0.05)


def printer():
    dark_world(H("#071512"), 0.3)
    cyc = L.plastic("cyc", H("#0c2a26"), rough=0.75, coat=0.0)
    D.cyclorama(cyc, width=30, depth=20, y_wall=3.5, radius=2.0, height=12)
    floor = L.pbr("floor", "concrete_floor_02", scale=1.2, tint=H("#203a35"), tint_amount=0.6)
    D.box("floor", (8, 6, 0.02), (0, 0, -0.01), floor)
    body_m = L.plastic("body", H("#d6286f"), rough=0.3, coat=0.7)
    plate = L.pbr("plate", "metal_plate", scale=3, tint=H("#c9a76a"), tint_amount=0.4, clearcoat=0.3)
    pinkp = L.plastic("pinkp", H("#14101c"), rough=0.3, coat=0.6)
    orangep = L.plastic("orangep", ORANGE, rough=0.3, coat=0.6)
    inkp = L.plastic("inkp", H("#101015"), rough=0.3, coat=0.6)
    brass = metal("brass", H("#e0b04a"), 0.22)
    chrome = metal("chrome", H("#d8dde0"), 0.12)
    # body
    D.box("body", (1.2, 0.9, 0.9), (0, 0.2, 0.55), body_m, bevel=0.06)
    D.box("legs", (1.1, 0.8, 0.1), (0, 0.2, 0.05), inkp, bevel=0.03)
    D.box("front", (1.0, 0.04, 0.55), (0, -0.25, 0.6), plate, bevel=0.015)
    D.box("stripe", (1.22, 0.92, 0.06), (0, 0.2, 0.92), pinkp, bevel=0.02)
    # hopper on top
    D.box("hopper", (0.7, 0.55, 0.25), (0, 0.25, 1.15), orangep, bevel=0.05)
    D.box("hopper_in", (0.6, 0.45, 0.02), (0, 0.25, 1.28), inkp)
    # output slot + rollers
    D.box("slot", (0.62, 0.12, 0.06), (0, -0.3, 0.42), inkp, bevel=0.01)
    for i, z in enumerate((0.45, 0.39)):
        D.cyl(f"roller{i}", 0.025, 0.6, (0, -0.33, z), rot=(0, math.pi / 2, 0), m=chrome)
    D.box("lip", (0.66, 0.2, 0.02), (0, -0.4, 0.37), chrome, bevel=0.005)
    # gauges & lights
    for i, x in enumerate((-0.32, 0.0, 0.32)):
        D.cyl(f"gauge{i}", 0.085, 0.03, (x, -0.28, 0.72), rot=(math.pi / 2, 0, 0), m=brass, verts=40)
        D.cyl(f"face{i}", 0.07, 0.032, (x, -0.282, 0.72), rot=(math.pi / 2, 0, 0), m=glow(f"gf{i}", GREEN, 2.5), verts=40)
        nd = D.box(f"needle{i}", (0.006, 0.004, 0.06), (x, -0.3, 0.72), inkp)
        nd.location.z += 0.0
        bake(nd, 1, rot=(0, 0.6, 0))
        for f in range(1, NF + 1, 6):
            bake(nd, f, rot=(0, math.sin(f * 0.35 + i) * 0.9, 0))
    for i in range(4):
        b = D.sphere(f"bulb{i}", 0.03, (-0.45 + i * 0.3, -0.26, 0.98), glow(f"bulbm{i}", (PINK, ORANGE, GREEN, TEAL)[i], 6), seg=16, rings=8)
    # side gears (turning)
    for i, (z, r) in enumerate(((0.62, 0.22), (0.35, 0.14))):
        g = D.cyl(f"gear{i}", r, 0.05, (0.62, 0.0 + i * 0.25, z), rot=(0, math.pi / 2, 0), m=brass, verts=24)
        tm = g.modifiers.new("teeth", "SCREW")
        g.modifiers.remove(tm)
        for t in range(14 if i == 0 else 10):
            a = t / (14 if i == 0 else 10) * math.tau
            th = D.box(f"tooth{i}_{t}", (0.05, 0.05, 0.05), (0, math.cos(a) * r, math.sin(a) * r), brass)
            th.rotation_euler = (a, 0, 0)
            th.parent = g
            th.location = (0, math.cos(a) * r, math.sin(a) * r)
        bake(g, 1, rot=(0, math.pi / 2, 0))
        g.rotation_mode = "XYZ"
        g.rotation_euler = (math.tau * (1 if i else -1) * 0.7, math.pi / 2, 0)
        g.keyframe_insert("rotation_euler", frame=NF)
        linear(g)
    # crank wheel on left
    w = D.torus("crank", 0.18, 0.02, (-0.63, 0.15, 0.6), rot=(0, math.pi / 2, 0), m=chrome)
    # bills
    bill_m = img_mat("bill", bill_texture(), rough=0.55, bump=0.2)
    BW, BH = 0.30, 0.13
    pile_c = Vector((0.0, -1.05, 0.0))
    # pre-existing pile
    for i in range(70):
        b = card(f"pile{i}", BW, BH, bill_m, plane="XY", thick=0.0015)
        r = random.random() ** 0.6 * 0.42
        a = random.uniform(0, math.tau)
        hgt = max(0.0, 0.16 - r * 0.38) * random.uniform(0.6, 1.0)
        b.location = (pile_c.x + math.cos(a) * r * 1.2, pile_c.y + math.sin(a) * r * 0.8, 0.003 + hgt)
        b.rotation_euler = (random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25), random.uniform(0, math.tau))
    # flying bills: one every 0.07 s
    slot = Vector((0, -0.38, 0.42))
    t = 0.0
    n = 0
    while t < DUR - 0.1:
        b = card(f"bill{n}", BW, BH, bill_m, plane="XY", thick=0.0015)
        f0 = T(t)
        land = pile_c + Vector((random.uniform(-0.45, 0.45), random.uniform(-0.25, 0.3), 0))
        land.z = 0.12 + random.uniform(0.0, 0.12)
        v0 = Vector((random.uniform(-0.9, 0.9), random.uniform(-1.6, -1.1), random.uniform(1.0, 1.8)))
        g = Vector((0, 0, -4.2))
        spinz = random.uniform(-6, 6)
        flut = random.uniform(5, 9)
        ph = random.uniform(0, 6)
        bake(b, 1, loc=slot, rot=(0, 0, 0), scale=0.0)
        if f0 > 1:
            bake(b, f0 - 1, loc=slot, rot=(0, 0, 0), scale=0.0)
        landed = False
        for j in range(0, 60):
            f = f0 + j
            if f > NF + 1:
                break
            s = j / 30
            p = slot + v0 * s + g * (0.5 * s * s)
            drag = 1 / (1 + 0.6 * s)
            p.x = slot.x + v0.x * s * drag
            p.y = slot.y + v0.y * s * drag
            rot = (math.sin(s * flut + ph) * 0.8 + s * 2, math.cos(s * flut * 0.7 + ph) * 0.6, spinz * s)
            if p.z <= land.z and j > 4:
                bake(b, f, loc=(p.x, p.y, land.z), rot=(random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), spinz * s), scale=1.0)
                landed = True
                break
            sc_ = min(1.0, 0.3 + j / 3)
            bake(b, f, loc=p, rot=rot, scale=sc_)
        linear(b)
        n += 1
        t += 0.07
    D.area_light("greenkey", 700, (-1.8, -2.2, 2.2), (0, -0.3, 0.6), size=2.5, rgb=H("#8af07f"))
    D.area_light("pinkrim", 1100, (1.8, 1.8, 1.8), (0, 0, 0.8), size=1.5, rgb=PINK)
    D.area_light("orangetop", 350, (0.5, -0.5, 3.0), (0, -0.5, 0.4), size=2, rgb=ORANGE)
    D.area_light("fill", 120, (2.2, -2.5, 0.8), (0, -0.5, 0.5), size=2, rgb=TEAL)
    D.area_light("wall", 900, (0, 1.2, 0.2), (0, 3.5, 3), size=3, rgb=H("#1fae7a"))
    push("cam", (1.25, -3.3, 1.05), (0.95, -2.75, 0.95), (0.0, -0.35, 0.62), (0.0, -0.4, 0.6), lens=34)
    L.post(sc, bloom=0.5, bloom_threshold=0.85, vignette=0.28, saturation=1.12, contrast=0.05)


def hourglass():
    dark_world(H("#0a0812"), 0.35)
    cyc = L.plastic("cyc", H("#160d22"), rough=0.8, coat=0.0)
    D.cyclorama(cyc, width=20, depth=14, y_wall=2.5, radius=1.5, height=10)
    wood = L.pbr("wood", "wood_table_001", scale=4, tint=H("#3b1d12"), tint_amount=0.4, clearcoat=0.4)
    brass = metal("brass", H("#e3b45a"), 0.2)
    table = L.pbr("table", "wood_table_001", scale=1.5, tint=H("#2a1410"), tint_amount=0.5, clearcoat=0.3)
    D.cyl("table", 1.2, 0.05, (0, 0, -0.025), m=table, verts=64)
    # glass: lathe profile
    import bmesh
    prof = []
    N = 24
    for i in range(N + 1):
        z = i / N * 0.56
        u = (z - 0.28) / 0.28
        r = 0.018 + 0.135 * (abs(u) ** 1.3) * (1 - 0.35 * abs(u) ** 6)
        prof.append((r, z + 0.03))
    me = bpy.data.meshes.new("glass")
    bm = bmesh.new()
    SEG = 48
    rings = []
    for r, z in prof:
        rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in (k / SEG * math.tau for k in range(SEG))])
    for i in range(len(rings) - 1):
        for k in range(SEG):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % SEG], rings[i + 1][(k + 1) % SEG], rings[i + 1][k]))
    bm.to_mesh(me)
    gl = D.link(bpy.data.objects.new("glass", me))
    D.smooth(gl)
    sol = gl.modifiers.new("sol", "SOLIDIFY")
    sol.thickness = 0.004
    gm = D.mat("glassm", (0.95, 0.97, 1.0), rough=0.03)
    b = gm.node_tree.nodes["Principled BSDF"]
    b.inputs["Alpha"].default_value = 0.14
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.03
    gm.surface_render_method = "BLENDED"
    gm.use_backface_culling = False
    D.give(gl, gm)
    D.cyl("capB", 0.2, 0.035, (0, 0, 0.0175), m=wood, verts=6)
    D.cyl("capT", 0.2, 0.035, (0, 0, 0.6125), m=wood, verts=6)
    D.cyl("rimB", 0.17, 0.012, (0, 0, 0.041), m=brass, verts=48)
    D.cyl("rimT", 0.17, 0.012, (0, 0, 0.589), m=brass, verts=48)
    for k in range(3):
        a = k / 3 * math.tau + 0.5
        D.cyl(f"post{k}", 0.011, 0.56, (0.175 * math.cos(a), 0.175 * math.sin(a), 0.315), m=brass, verts=16)
    sand = noisy("sand", H("#ff8000"), rough=0.6, scale=400, bump=0.5, var=0.3)
    sb = sand.node_tree.nodes["Principled BSDF"]
    sb.inputs["Emission Color"].default_value = (*H("#ff6a00"), 1)
    sb.inputs["Emission Strength"].default_value = 0.15
    # upper sand: cone pointing down (apex at neck), shrinking
    up = D.cone("sandTop", 0.115, 0.17, (0, 0, 0.0), sand, verts=48)
    up.rotation_euler = (math.pi, 0, 0)
    up.location = (0, 0, 0.31 + 0.085)
    bake(up, 1, scale=(1, 1, 1))
    up.scale = (0.72, 0.72, 0.45)
    up.keyframe_insert("scale", frame=NF)
    up.location = (0, 0, 0.31 + 0.085 * 0.45)
    D.key(up, "location", 1, (0, 0, 0.31 + 0.085))
    D.key(up, "location", NF, (0, 0, 0.31 + 0.085 * 0.45))
    linear(up)
    lo = D.cone("sandBot", 0.14, 0.12, (0, 0, 0.042 + 0.06), sand, verts=48)
    bake(lo, 1, scale=(0.82, 0.82, 0.6))
    bake(lo, NF, scale=(1.0, 1.0, 1.15))
    linear(lo)
    stream = D.cyl("stream", 0.006, 0.22, (0, 0, 0.2), m=sand, verts=12)
    # grains falling in the stream
    for k in range(10):
        gr = D.ico(f"grain{k}", 0.004, (0, 0, 0.3), sand, sub=1)
        for f in range(1, NF + 1, 3):
            ph = ((f / 9.0) + k / 10) % 1
            bake(gr, f, loc=(random.uniform(-0.003, 0.003), random.uniform(-0.003, 0.003), 0.3 - ph * 0.2))
        linear(gr)
    D.area_light("teal", 300, (-1.0, 0.8, 0.8), (0, 0, 0.3), size=0.8, rgb=TEAL)
    D.area_light("pink", 300, (1.0, 0.8, 0.8), (0, 0, 0.3), size=0.8, rgb=PINK)
    D.area_light("warm", 160, (0.2, -1.2, 0.15), (0, 0, 0.25), size=1.0, rgb=ORANGE)
    D.area_light("under", 40, (0, -0.6, 0.9), (0, 0, 0.2), size=1.0, rgb=H("#ffe0c0"))
    D.area_light("wall", 120, (0, 1.0, 0.05), (0, 2.5, 0.0), size=2, rgb=H("#ff6a3a"))
    rig = D.empty("orbit", (0, 0, 0))
    c, l = D.camera("cam", 50)
    c.parent = rig
    c.location = (0, -1.55, 0.28)
    l.location = (0, 0, 0.42)
    bake(rig, 1, rot=(0, 0, math.radians(-10)))
    bake(rig, NF, rot=(0, 0, math.radians(10)))
    linear(rig)
    sc.camera = c
    L.post(sc, bloom=0.55, bloom_threshold=0.8, vignette=0.34, saturation=1.12, contrast=0.05)


def vault():
    dark_world(H("#0b0a10"), 0.15)
    wall = L.pbr("wall", "concrete_floor_02", scale=1.0, tint=H("#3b3540"), tint_amount=0.5)
    floor = L.pbr("floor", "concrete_floor_02", scale=1.5, tint=H("#2a2530"), tint_amount=0.5)
    steel = L.pbr("steel", "metal_plate", scale=2, tint=H("#9aa0aa"), tint_amount=0.3, clearcoat=0.3)
    chrome = metal("chrome", H("#e6e8ea"), 0.15)
    brass = metal("brass", H("#e3b45a"), 0.22)
    R = 0.9
    # wall with round opening: two boxes around + ring frame (approximate with boolean)
    w = D.box("wall", (6, 0.4, 5), (0, 0.2, 2.0), wall)
    hole = D.cyl("hole", R + 0.02, 1.0, (0, 0.2, 1.2), rot=(math.pi / 2, 0, 0), verts=64)
    bm_ = w.modifiers.new("hole", "BOOLEAN")
    bm_.object, bm_.operation = hole, "DIFFERENCE"
    hole.hide_render = True
    hole.hide_viewport = True
    D.box("floor", (8, 6, 0.02), (0, -1.5, -0.01), floor)
    frame = D.torus("frame", R + 0.06, 0.07, (0, -0.02, 1.2), rot=(math.pi / 2, 0, 0), m=chrome)
    # interior glow room
    D.box("inner", (3, 0.05, 3), (0, 2.2, 1.2), glow("innerglow", H("#ff4f7e"), 0.9))
    gold = metal("goldbars", H("#ffb23a"), 0.2)
    for i in range(12):
        D.box(f"bar{i}", (0.3, 0.14, 0.1), (-0.5 + (i % 4) * 0.33, 1.2 + (i // 4) * 0.16, 0.32 + (i // 4) * 0.11), gold, bevel=0.015)
    D.box("shelf", (1.6, 0.6, 0.3), (0, 1.3, 0.12), L.plastic("shelf", H("#2a1830"), rough=0.4))
    inl = D.area_light("innerlight", 700, (0, 1.8, 1.4), (0, -2, 1.0), size=1.2, rgb=PINK)
    inl2 = D.area_light("innerlight2", 900, (0.5, 1.0, 0.9), (0, 1.3, 0.3), size=1.0, rgb=ORANGE)
    # door: hinge on left (x = -R)
    hinge = D.empty("hinge", (-R - 0.05, -0.1, 1.2))
    door = D.cyl("door", R, 0.28, (0, 0, 0), rot=(math.pi / 2, 0, 0), m=steel, verts=96)
    D.smooth(door, bevel=0.03)
    door.parent = hinge
    door.location = (R + 0.05, -0.14, 0)
    parts = [D.cyl("ring", R * 0.72, 0.02, (0, -0.15, 0), rot=(math.pi / 2, 0, 0), m=chrome, verts=96),
             D.cyl("hub", 0.12, 0.08, (0, -0.19, 0), rot=(math.pi / 2, 0, 0), m=brass, verts=32),
             D.torus("wheel", 0.36, 0.025, (0, -0.24, 0), rot=(math.pi / 2, 0, 0), m=chrome)]
    for k in range(3):
        a = k / 3 * math.pi
        sp_ = D.cyl(f"spoke{k}", 0.018, 0.72, (0, -0.24, 0), rot=(0, a, 0), m=chrome, verts=12)
        parts.append(sp_)
    for k in range(16):
        a = k / 16 * math.tau
        parts.append(D.cyl(f"bolt{k}", 0.035, 0.03, (math.cos(a) * R * 0.85, -0.15, math.sin(a) * R * 0.85),
                           rot=(math.pi / 2, 0, 0), m=brass, verts=16))
    for p in parts:
        p.parent = hinge
        p.location = (p.location.x + R + 0.05, p.location.y - 0.14 + 0.15 - 0.15, p.location.z)
    for k in range(3):
        D.cyl(f"hingepin{k}", 0.06, 0.25, (-R - 0.05, -0.1, 0.6 + k * 0.6), m=chrome, verts=24)
    bake(hinge, 1, rot=(0, 0, 0))
    bake(hinge, T(0.35), rot=(0, 0, 0))
    bake(hinge, NF, rot=(0, 0, math.radians(-105)))
    for fc in D._fcurves(hinge.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation, kp.easing = "SINE", "EASE_IN_OUT"
    # dust motes
    mote = glow("mote", H("#ffd0b0"), 3.0)
    for k in range(70):
        m = D.ico(f"mote{k}", random.uniform(0.004, 0.009), (0, 0, 0), mote, sub=1)
        p0 = Vector((random.uniform(-1.1, 1.1), random.uniform(-1.8, 0.4), random.uniform(0.3, 2.2)))
        dv = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.15, 0.05), random.uniform(-0.05, 0.12)))
        bake(m, 1, loc=p0)
        bake(m, NF, loc=p0 + dv)
        linear(m)
    volume_box((5, 4, 3.5), (0, -1.0, 1.5), 0.04, rgb=H("#ffd8c8"))
    D.area_light("key", 120, (-2.0, -3, 2.5), (0, 0, 1.2), size=3, rgb=H("#8fd8e0"))
    D.area_light("rim", 200, (2.5, -0.8, 2.6), (0, 0, 1.2), size=1.5, rgb=TEAL)
    push("cam", (0.9, -4.6, 1.0), (0.7, -3.8, 1.05), (0.0, 0, 1.2), (0.0, 0, 1.25), lens=34)
    L.post(sc, bloom=0.65, bloom_threshold=0.8, vignette=0.3, saturation=1.12, contrast=0.05)


{"calendar": calendar, "consoles": consoles, "printer": printer, "hourglass": hourglass, "vault": vault}[SHOT]()
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT))
print("saved", OUT)
