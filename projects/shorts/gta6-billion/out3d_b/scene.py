"""blender -b -P scene.py -- <shot> <out.blend>: agent-B set shots for "Where did GTA 6's billion dollars go?".

beer 5.8 s | leak 4.8 s | sign 7.7 s   (30 fps, 1080x1920, EEVEE, AgX Punchy, neon Vice-City palette)
Cash = real $100 bills (public/img/bill_front.jpg, public domain), bent linked-duplicate meshes, per-frame baked paths.
Only physical signage text ("BEER" neon, the rooftop "Welcome to VICE CITY" sign). Remotion adds every caption/HUD.
"""
import math, os, random, sys
import numpy as np
import bpy
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJ, "..", "..", "..", "src", "reelforge", "blender"))
import director as D
import look as L

args = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = args[0], args[1]
DUR = {"beer": 5.8, "leak": 4.8, "sign": 7.7}[SHOT]
NF = int(round(DUR * 30))
H = D.hex_lin
PINK, ORANGE, TEAL, PURPLE, CYAN = H("#FF3E9A"), H("#FF9A3C"), H("#19C3B5"), H("#3B1C5A"), H("#38E1FF")
BILL_IMG = os.path.join(PROJ, "public", "img", "bill_front.jpg")
FONT_SCRIPT = "/System/Library/Fonts/Supplemental/Brush Script.ttf"
FONT_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
random.seed(7)
np.random.seed(7)

sc = D.reset(frames=NF)
D.fast_eevee(sc, samples=16, look="AgX - Punchy", raytrace=(SHOT == "sign"))
sc.name = SHOT
F = lambda s: s * 30 + 1  # noqa: E731  seconds → frame (float ok)


# ================================================================ helpers

def bake(o, frames, locs, rots=None, scales=None):
    """Write dense per-frame keys fast (foreach_set) — paths are simulated in Python."""
    chans = [("location", locs)]
    if rots is not None:
        chans.append(("rotation_euler", rots))
    if scales is not None:
        chans.append(("scale", scales))
    for path, vals in chans:
        o.keyframe_insert(path, frame=frames[0])
    fcs = {(fc.data_path, fc.array_index): fc for fc in D._fcurves(o.animation_data.action)}
    for path, vals in chans:
        vals = np.asarray(vals, dtype=np.float64)
        for i in range(3):
            fc = fcs[(path, i)]
            fc.keyframe_points.add(len(frames) - 1)
            co = np.empty(2 * len(frames))
            co[0::2], co[1::2] = frames, vals[:, i]
            fc.keyframe_points.foreach_set("co", co)
            fc.keyframe_points.foreach_set("interpolation", [2] * len(frames))   # LINEAR (dense keys)
            fc.update()


def emit_mat(name, rgb, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*rgb, 1)
    e.inputs[1].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def key_strength(m, pairs):
    """pairs: [(frame, strength)] keyed on the emission node (constant steps → neon flicker)."""
    e = next(n for n in m.node_tree.nodes if n.type == "EMISSION")
    for f, v in pairs:
        e.inputs[1].default_value = v
        e.inputs[1].keyframe_insert("default_value", frame=f)
    for fc in D._fcurves(m.node_tree.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "CONSTANT"


def bill_material():
    m = bpy.data.materials.get("bill")
    if m:
        return m
    m = bpy.data.materials.new("bill")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(BILL_IMG, check_existing=True)
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = 1.25
    hs.inputs["Value"].default_value = 1.05
    nt.links.new(t.outputs[0], hs.inputs["Color"])
    nt.links.new(hs.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = 0.3
    return m


BILL_MESHES = []


def bill_meshes(size=1.6):
    """3 bent variants of a 15.6 x 6.6 cm note (scaled `size` for screen read), UV = whole image."""
    if BILL_MESHES:
        return BILL_MESHES
    for i, bend in enumerate((0.55, -0.35, 0.9)):
        bpy.ops.mesh.primitive_plane_add(size=1)
        o = bpy.context.active_object
        o.scale = (0.156 * size, 0.066 * size, 1)
        bpy.ops.object.transform_apply(scale=True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.subdivide(number_cuts=7)
        bpy.ops.object.mode_set(mode="OBJECT")
        md = o.modifiers.new("bend", "SIMPLE_DEFORM")
        md.deform_method, md.deform_axis, md.angle = "BEND", "Y", bend
        md2 = o.modifiers.new("twist", "SIMPLE_DEFORM")
        md2.deform_method, md2.deform_axis, md2.angle = "TWIST", "X", 0.25 * (i - 1)
        bpy.ops.object.modifier_apply(modifier="bend")
        bpy.ops.object.modifier_apply(modifier="twist")
        o.data.materials.append(bill_material())
        for p in o.data.polygons:
            p.use_smooth = True
        me = o.data
        me.name = f"bill_{i}"
        bpy.data.objects.remove(o)
        BILL_MESHES.append(me)
    return BILL_MESHES


def bill(name):
    me = random.choice(bill_meshes())
    return D.link(bpy.data.objects.new(name, me))


def flight(p0, v0, t0, t1, rot0, w, drag=1.6, g=9.8, floor=0.0, flutter=0.9, term=None, seed=0):
    """Simulate one fluttering note from t0 (s) to t1; before t0 hidden (scale 0) at p0. Frame step 1."""
    rs = np.random.RandomState(seed)
    ph = rs.uniform(0, 6.28, 3)
    frames, locs, rots, scales = [], [], [], []
    p, v, r = np.array(p0, float), np.array(v0, float), np.array(rot0, float)
    landed = False
    dt = 1 / 30
    for f in range(1, NF + 2):
        t = (f - 1) / 30
        if t < t0:
            frames.append(f); locs.append(p0); rots.append(rot0); scales.append((0, 0, 0))
            continue
        if not landed:
            v[2] -= g * dt
            v *= math.exp(-drag * dt)
            fl = flutter * np.array([math.sin(7 * t + ph[0]), math.cos(5.3 * t + ph[1]), 0.6 * math.sin(9 * t + ph[2])])
            p = p + (v + fl) * dt
            r = r + np.array(w) * dt
            if term is not None and term(p):
                landed = True
            if p[2] <= floor + 0.004:
                p[2] = floor + 0.004 + rs.uniform(0, 0.02)
                r = np.array([rs.uniform(-0.08, 0.08), rs.uniform(-0.08, 0.08), r[2]])
                landed = True
        frames.append(f); locs.append(tuple(p)); rots.append(tuple(r)); scales.append((1, 1, 1))
    return frames, locs, rots, scales


def neon_text(name, body, size, loc, rgb, font, strength=12.0, rot=(math.pi / 2, 0, 0), extrude=0.02):
    m = emit_mat(name + "_m", rgb, strength)
    o = D.text3d(name, body, size, loc, m, extrude=extrude, bevel=size * 0.012, font=font, rot=rot)
    return o, m


def palm(loc, h=7.0, seed=0, lean=0.25):
    rs = random.Random(seed)
    trunk_m = bpy.data.materials.get("palm_trunk") or D.mat("palm_trunk", H("#3A2A22"), rough=0.8)
    leaf_m = bpy.data.materials.get("palm_leaf") or D.mat("palm_leaf", H("#0E3B2A"), rough=0.6)
    a = rs.uniform(0, 6.28)
    pts = [(loc[0] + math.cos(a) * lean * h * (i / 6) ** 1.6, loc[1] + math.sin(a) * lean * h * (i / 6) ** 1.6, loc[2] + h * i / 6)
           for i in range(7)]
    tr = D.stroke(f"palm_trunk_{seed}", pts, trunk_m, width=0.16)
    tr.data.bevel_resolution = 1
    top = Vector(pts[-1])
    for k in range(9):
        bpy.ops.mesh.primitive_plane_add(size=1)
        lf = bpy.context.active_object
        lf.name = f"palm_leaf_{seed}_{k}"
        lf.scale = (2.6, 0.42, 1)
        bpy.ops.object.transform_apply(scale=True)
        lf.location = top
        lf.data.transform(__import__("mathutils").Matrix.Translation((1.3, 0, 0)))
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.subdivide(number_cuts=5)
        bpy.ops.object.mode_set(mode="OBJECT")
        md = lf.modifiers.new("droop", "SIMPLE_DEFORM")
        md.deform_method, md.deform_axis, md.angle = "BEND", "Y", -1.1 - rs.uniform(0, 0.5)
        lf.rotation_euler = (rs.uniform(-0.2, 0.2), rs.uniform(-0.15, 0.3), k * 2 * math.pi / 9 + rs.uniform(-0.2, 0.2))
        D.give(lf, leaf_m)
        D.adopt(lf)


def film_card_image():
    """Glowing 'video clip' thumbnail: film-strip border + sprockets + gradient frame + play triangle (no footage)."""
    w, h = 256, 160
    y, x = np.mgrid[0:h, 0:w]
    g = (x / w)[..., None]
    col = (1 - g) * np.array([0.22, 0.88, 1.0]) + g * np.array([1.0, 0.24, 0.6])
    img = np.ones((h, w, 4))
    img[..., :3] = col
    border = (y < 22) | (y > h - 23)
    img[border, :3] = 0.04
    sprocket = border & (((x // 16) % 2) == 0) & (((y > 7) & (y < 15)) | ((y > h - 16) & (y < h - 8)))
    img[sprocket, :3] = 0.9
    cx, cy = w / 2, h / 2
    tri = (x > cx - 18) & (x < cx + 22) & (np.abs(y - cy) < (cx + 22 - x) * 0.55)
    img[tri, :3] = 1.0
    im = bpy.data.images.new("filmcard", w, h, alpha=True)
    im.pixels.foreach_set(img[::-1].astype(np.float32).ravel())
    im.pack()
    return im


def film_material():
    m = bpy.data.materials.new("filmcard")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = film_card_image()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[1].default_value = 3.2
    nt.links.new(t.outputs[0], e.inputs[0])
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def led_material(name, a, b, scale=(1.6, 2.2), strength=4.0):
    """Server-rack front: dark metal with a grid of tiny emissive LEDs (Brick texture mask)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*H("#15171E"), 1)
    bsdf.inputs["Metallic"].default_value = 0.7
    bsdf.inputs["Roughness"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sp.inputs[0])
    cb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sp.outputs["Y"], cb.inputs["X"])
    nt.links.new(sp.outputs["Z"], cb.inputs["Y"])
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale[0], scale[1], 1)
    nt.links.new(cb.outputs[0], mp.inputs["Vector"])
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Brick Width"].default_value = 0.3
    br.inputs["Row Height"].default_value = 0.3
    br.inputs["Mortar Size"].default_value = 0.11
    br.inputs["Color1"].default_value = (*a, 1)
    br.inputs["Color2"].default_value = (*b, 1)
    br.inputs["Mortar"].default_value = (0, 0, 0, 1)
    nt.links.new(mp.outputs[0], br.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 9.0
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    gate = nt.nodes.new("ShaderNodeMath")
    gate.operation = "GREATER_THAN"
    gate.inputs[1].default_value = 0.56
    nt.links.new(nz.outputs[0], gate.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    nt.links.new(br.outputs["Color"], mul.inputs[6])
    nt.links.new(gate.outputs[0], mul.inputs[7])
    nt.links.new(mul.outputs[2], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    return m


def window_material(name, base, lit, scale=(4, 9), strength=3.0, frac=0.45):
    """Skyscraper facade: random lit windows (Brick mask × noise gate)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = 0.3
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale[0], scale[0], scale[1])
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Mortar Size"].default_value = 0.05
    br.inputs["Color1"].default_value = (*lit, 1)
    br.inputs["Color2"].default_value = (*[c * 0.7 for c in lit], 1)
    br.inputs["Mortar"].default_value = (0, 0, 0, 1)
    nt.links.new(mp.outputs[0], br.inputs["Vector"])
    vr = nt.nodes.new("ShaderNodeTexVoronoi")
    vr.inputs["Scale"].default_value = scale[1] * 1.2
    nt.links.new(mp.outputs[0], vr.inputs["Vector"])
    gate = nt.nodes.new("ShaderNodeMath")
    gate.operation = "LESS_THAN"
    gate.inputs[1].default_value = frac
    nt.links.new(vr.outputs["Color"], gate.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    nt.links.new(br.outputs["Color"], mul.inputs[6])
    nt.links.new(gate.outputs[0], mul.inputs[7])
    nt.links.new(mul.outputs[2], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    return m


def point(name, rgb, power, loc, radius=0.2):
    l = D.link(bpy.data.objects.new(name, bpy.data.lights.new(name, "POINT")))
    l.data.color, l.data.energy, l.data.shadow_soft_size = rgb, power, radius
    l.location = loc
    return l


# ================================================================ BEER — neon convenience store, the beer "pipeline"

def shot_beer():
    L.hdri_world(sc, "studio_small_09", strength=0.35, backdrop=H("#1A0B2A"), backdrop_strength=1.0)
    floor = D.box("floor", (12, 12, 0.1), (0, 0, -0.05), L.pbr("tiles", "long_white_tiles", scale=0.8, tint=H("#E9D8F2"), tint_amount=0.35, rough_mul=0.6))
    wall = L.pbr("wall", "painted_plaster_wall", scale=0.6, tint=H("#5B2A86"), tint_amount=0.85)
    D.box("back_wall", (12, 0.2, 4), (0, 3.1, 2), wall)
    D.box("left_wall", (0.2, 8, 4), (-3.2, 0, 2), wall)
    D.box("ceiling", (12, 12, 0.1), (0, 0, 3.4), D.mat("ceil", H("#120A1C"), rough=0.9))
    metal = D.mat("fridge_metal", H("#1C1F2A"), rough=0.3, metal=0.8)
    inner = emit_mat("fridge_light", H("#E8F6FF"), 2.2)
    glass = D.mat("glass", H("#BFE9FF"), rough=0.05, spec=1.0)
    gb = glass.node_tree.nodes["Principled BSDF"]
    gb.inputs["Alpha"].default_value = 0.08
    if hasattr(glass, "surface_render_method"):
        glass.surface_render_method = "BLENDED"
    # fridge unit: 3 doors along x, against the back wall
    x0, x1, y0, y1, hgt = -2.7, -0.3, 2.3, 3.0, 2.2
    cx = (x0 + x1) / 2
    D.box("fridge_back", (x1 - x0, 0.05, hgt), (cx, y1, hgt / 2), metal)
    D.box("fridge_top", (x1 - x0, y1 - y0, 0.08), (cx, (y0 + y1) / 2, hgt - 0.04), metal)
    D.box("fridge_bot", (x1 - x0, y1 - y0, 0.12), (cx, (y0 + y1) / 2, 0.06), metal)
    for sx in (x0, x1):
        D.box(f"fridge_side{sx}", (0.05, y1 - y0, hgt), (sx, (y0 + y1) / 2, hgt / 2), metal)
    for k in (1, 2):
        D.box(f"fridge_mullion{k}", (0.04, y1 - y0, hgt), (x0 + k * (x1 - x0) / 3, (y0 + y1) / 2, hgt / 2), metal)
    point("fridge_in_a", H("#DFF3FF"), 60, (-2.0, 2.65, 1.9), 0.3)
    point("fridge_in_b", H("#DFF3FF"), 60, (-1.0, 2.65, 1.9), 0.3)
    D.box("fridge_back_light", (x1 - x0 - 0.12, 0.04, hgt - 0.2), ((x0 + x1) / 2, y1 - 0.06, hgt / 2), inner)
    shelf_m = D.mat("shelf", H("#D9DDE5"), rough=0.3, metal=0.6)
    label_cols = [H(c) for c in ("#FF3E9A", "#FFD23F", "#38E1FF", "#FF9A3C", "#6FDB6A", "#FFFFFF")]
    label_mats = [L.plastic(f"lab{i}", c, rough=0.3, coat=0.5) for i, c in enumerate(label_cols)]
    brown = D.mat("amber_glass", H("#5A2A08"), rough=0.12, spec=0.9)
    body_me = None
    for si, z in enumerate((0.35, 0.82, 1.29, 1.76)):
        D.box(f"shelf{si}", (x1 - x0 - 0.1, 0.55, 0.025), ((x0 + x1) / 2, 2.66, z), shelf_m)
        for k in range(26):
            bx = x0 + 0.12 + k * (x1 - x0 - 0.24) / 25
            if abs(bx - (-1.5)) < 0.05 and si == 2:
                continue                                              # gap where the hero bottle sits
            for row in range(2):
                o = D.cyl(f"b{si}_{k}_{row}", 0.032, 0.24, (bx, 2.5 + row * 0.12, z + 0.135), m=brown, verts=10)
                o.data.materials.append(label_mats[(k + si) % len(label_mats)])
                for p in o.data.polygons:
                    if abs(p.normal.z) < 0.5 and 0.04 < (p.center.z) + 0.12 < 0.17:
                        p.material_index = 1
    # doors: frames (hinge parents) + glass; hero = middle door, hinge on its left edge
    dw = (x1 - x0) / 3
    hero_hinge = None
    for i in range(3):
        hx = x0 + i * dw
        hinge = D.empty(f"hinge{i}", (hx + 0.02, y0 - 0.02, 0))
        parts = [D.box(f"door{i}_l", (0.05, 0.05, hgt - 0.08), (hx + 0.03, y0 - 0.02, hgt / 2), metal),
                 D.box(f"door{i}_r", (0.05, 0.05, hgt - 0.08), (hx + dw - 0.03, y0 - 0.02, hgt / 2), metal),
                 D.box(f"door{i}_t", (dw - 0.02, 0.05, 0.08), (hx + dw / 2, y0 - 0.02, hgt - 0.08), metal),
                 D.box(f"door{i}_b", (dw - 0.02, 0.05, 0.08), (hx + dw / 2, y0 - 0.02, 0.08), metal),
                 D.box(f"door{i}_g", (dw - 0.08, 0.01, hgt - 0.2), (hx + dw / 2, y0 - 0.02, hgt / 2), glass),
                 D.box(f"door{i}_h", (0.03, 0.06, 0.6), (hx + dw - 0.09, y0 - 0.08, 1.15), shelf_m)]
        for p in parts:
            p.parent = hinge
            p.matrix_parent_inverse = hinge.matrix_world.inverted()
        if i == 1:
            hero_hinge = hinge
    # hero door swings open 1.5 → 2.2 s (overshoot, settle)
    D.key(hero_hinge, "rotation_euler", F(0), (0, 0, 0))
    D.key(hero_hinge, "rotation_euler", F(1.45), (0, 0, 0))
    D.key(hero_hinge, "rotation_euler", F(2.05), (0, 0, math.radians(-112)))
    D.key(hero_hinge, "rotation_euler", F(2.35), (0, 0, math.radians(-100)))
    D.ease_all(hero_hinge)
    # neon "BEER" sign above the fridge + cyan ceiling strip
    neon_text("neon_beer", "BEER", 0.55, (-1.5, 3.0, 2.75), PINK, FONT_SCRIPT, strength=16.0)
    D.box("neon_strip", (5.6, 0.04, 0.04), (0.2, 2.95, 3.25), emit_mat("cyan_neon", CYAN, 14.0))
    D.box("neon_strip2", (0.04, 5.0, 0.04), (-3.05, 0.2, 3.25), emit_mat("pink_neon", PINK, 12.0))
    point("pink_spill", PINK, 260, (-1.5, 2.6, 2.75), 0.4)
    point("cyan_spill", CYAN, 160, (1.2, 2.6, 3.1), 0.4)
    # counter + register
    ctr = L.pbr("counter", "wood_table_001", scale=1.2, tint=H("#2B1530"), tint_amount=0.6, rough_mul=0.7)
    D.box("counter", (2.4, 0.9, 1.0), (1.3, 0.55, 0.5), ctr, bevel=0.01)
    D.box("counter_top", (2.5, 1.0, 0.05), (1.3, 0.55, 1.02), L.plastic("ctop", H("#F2F2F7"), rough=0.25, coat=0.6))
    D.box("counter_neon", (2.4, 0.03, 0.03), (1.3, 0.04, 0.96), emit_mat("ctr_neon", PINK, 10.0))
    reg_m = L.plastic("register", H("#2E3140"), rough=0.35, coat=0.5)
    D.box("reg_body", (0.5, 0.42, 0.22), (1.75, 0.62, 1.16), reg_m, bevel=0.015)
    scr = D.box("reg_screen", (0.32, 0.04, 0.2), (1.75, 0.62, 1.42), emit_mat("screen", H("#6FDB6A"), 4.0))
    scr.rotation_euler = (math.radians(-18), 0, 0)
    drawer = D.box("reg_drawer", (0.46, 0.4, 0.09), (1.75, 0.6, 1.08), reg_m, bevel=0.01)
    tray = D.box("drawer_tray", (0.42, 0.36, 0.01), (1.75, 0.6, 1.115), D.mat("tray", H("#0D0E14"), rough=0.6))
    tray.parent = drawer
    tray.matrix_parent_inverse = drawer.matrix_world.inverted()
    D.key(drawer, "location", F(0), drawer.location.copy())
    D.key(drawer, "location", F(4.75), drawer.location.copy())
    D.key(drawer, "location", F(4.95), drawer.location + Vector((0, -0.42, 0)))
    D.key(drawer, "location", F(5.05), drawer.location + Vector((0, -0.36, 0)))
    D.ease_all(drawer)
    # foreground snack shelf (right) for depth + colour
    sh = D.mat("snack_shelf", H("#E6E8EE"), rough=0.4, metal=0.3)
    for z in (0.3, 0.75, 1.2):
        D.box(f"snack_shelf{z}", (0.5, 1.6, 0.03), (2.9, -1.6, z), sh)
        for k in range(10):
            c = label_mats[random.randrange(len(label_mats))]
            D.box(f"snack{z}_{k}", (0.32, 0.12, random.uniform(0.18, 0.3)), (2.85, -2.3 + k * 0.15, z + 0.13), c, bevel=0.01)
    # hero bottle: shelf 2 → out of the fridge → arc → counter (2.2 → 3.45 s)
    bot = D.empty("hero_bottle", (-1.5, 2.55, 1.29))
    pieces = [D.cyl("hb_body", 0.042, 0.2, (-1.5, 2.55, 1.29 + 0.1), m=brown, verts=24),
              D.cone("hb_neck", 0.042, 0.11, (-1.5, 2.55, 1.29 + 0.255), m=brown, verts=24),
              D.cyl("hb_lab", 0.0435, 0.08, (-1.5, 2.55, 1.29 + 0.1), m=label_mats[1], verts=24),
              D.cyl("hb_cap", 0.016, 0.02, (-1.5, 2.55, 1.29 + 0.32), m=shelf_m, verts=16)]
    for p in pieces:
        p.parent = bot
        p.matrix_parent_inverse = bot.matrix_world.inverted()
    point("bottle_glow", H("#FFD9A0"), 18, (0, 0, 0.18), 0.1).parent = bot
    path = []
    p0, p1 = Vector((-1.5, 2.55, 1.29)), Vector((1.35, 0.55, 1.045))
    for f in range(1, NF + 2):
        t = (f - 1) / 30
        u = min(max((t - 2.15) / 1.3, 0), 1)
        e = u * u * (3 - 2 * u)
        pos = p0.lerp(p1, e) + Vector((0, -0.5 * math.sin(math.pi * e), 0.45 * math.sin(math.pi * e)))
        spin = 2 * math.pi * e
        land = max(0.0, 1 - (t - 3.45) / 0.18) if t > 3.45 else 0.0
        path.append((f, tuple(pos + Vector((0, 0, 0.03 * land))), (0.25 * math.sin(math.pi * e), 0, spin)))
    bake(bot, [p[0] for p in path], [p[1] for p in path], [p[2] for p in path])
    # cash flying into the opened drawer 4.8 → 5.8 s
    tgt = Vector((1.75, 0.18, 1.14))
    for i in range(30):
        t0 = 4.78 + i * 0.03
        start = Vector((random.uniform(0.2, 1.6), random.uniform(-1.6, -0.9), random.uniform(1.9, 2.4)))
        o = bill(f"cash{i}")
        fr, lo, ro, scl = [], [], [], []
        w = Vector((random.uniform(-7, 7), random.uniform(-9, 9), random.uniform(-5, 5)))
        r0 = Vector((random.uniform(0, 6), random.uniform(0, 6), random.uniform(0, 6)))
        for f in range(1, NF + 2):
            t = (f - 1) / 30
            u = min(max((t - t0) / 0.55, 0), 1)
            pos = start.lerp(tgt + Vector((random.uniform(-0.12, 0.12), random.uniform(-0.1, 0.1), 0.01 * i)), u * (2 - u))
            pos.z += 0.35 * math.sin(math.pi * u)
            rot = r0 + w * min(t - t0, 0.55) * (1 - 0.8 * u) if t >= t0 else r0
            if u >= 1:
                rot = Vector((0, 0, rot.z))
            fr.append(f); lo.append(tuple(pos)); ro.append(tuple(rot)); scl.append((1, 1, 1) if t >= t0 else (0, 0, 0))
        bake(o, fr, lo, ro, scl)
    D.area_light("key", 220, (0.5, -1.5, 3.2), (0, 1.5, 0.8), size=3.0, rgb=H("#FFE7F4"))
    # camera: push on the fridge → pan with the bottle → push on the register
    cam, look = D.camera("cam", lens=26, dof=None)
    keys = [(0.0, (-0.25, -2.3, 1.55), (-1.45, 2.4, 1.25)), (2.0, (-0.75, -1.25, 1.45), (-1.5, 2.3, 1.3)),
            (3.6, (0.55, -1.55, 1.7), (1.25, 0.6, 1.1)), (5.8, (1.15, -0.55, 1.62), (1.72, 0.45, 1.1))]
    for t, cl, lk in keys:
        D.key(cam, "location", F(t), Vector(cl))
        D.key(look, "location", F(t), Vector(lk))
    D.ease_all(cam)
    D.ease_all(look)
    D.handheld(cam, strength=0.004, scale=40)
    sc.camera = cam
    L.post(sc, bloom=0.6, bloom_threshold=0.85, vignette=0.26, saturation=1.12)


# ================================================================ LEAK — money pipe bursts in a dark server room

def shot_leak():
    D.world(sc, H("#05060C"), 1.0)
    L.hdri_world(sc, "studio_small_09", strength=0.05, backdrop=H("#04050A"))
    D.box("floor", (14, 20, 0.1), (0, 4, -0.05), L.pbr("floor", "concrete_floor_02", scale=0.7, tint=H("#2A3550"), tint_amount=0.7, rough_mul=0.55))
    D.box("ceiling", (14, 20, 0.1), (0, 4, 3.2), D.mat("ceil", H("#0A0B10"), rough=0.9))
    D.box("back_wall", (14, 0.2, 3.4), (0, 9.5, 1.6), D.mat("bw", H("#0C0E16"), rough=0.8))
    led_a = led_material("rack_led_a", H("#38E1FF"), H("#6FDB6A"))
    led_b = led_material("rack_led_b", H("#FF3E9A"), H("#38E1FF"), scale=(1.4, 2.6))
    for side in (-1, 1):
        for k in range(9):
            y = 0.6 + k * 0.95
            D.box(f"rack{side}_{k}", (0.9, 0.85, 2.3), (side * 2.0, y, 1.15), led_a if (k + (side > 0)) % 2 else led_b)
    # money pipe across the room (y=4.6, z=2.55) + flanges + a vertical feed
    pipe_m = L.pbr("pipe", "rusty_metal", scale=1.5, tint=H("#2F8F5B"), tint_amount=0.55, rough_mul=0.8)
    flange_m = L.plastic("flange", H("#C9A227"), rough=0.3, coat=0.4)
    shake = D.empty("pipe_root", (0, 4.6, 2.55))
    parts = [D.cyl("pipe", 0.34, 14, (0, 4.6, 2.55), rot=(0, math.pi / 2, 0), m=pipe_m, verts=40)]
    for x in (-3.2, -1.1, 1.1, 3.2):
        parts.append(D.cyl(f"flange{x}", 0.42, 0.12, (x, 4.6, 2.55), rot=(0, math.pi / 2, 0), m=flange_m, verts=40))
    parts.append(D.cyl("feed", 0.3, 2.6, (3.9, 4.6, 1.3), m=pipe_m, verts=32))
    for p in parts:
        p.parent = shake
        p.matrix_parent_inverse = shake.matrix_world.inverted()
    fr, lo = [], []
    for f in range(1, NF + 2):
        t = (f - 1) / 30
        a = 0.025 if t < 0.45 else 0.06 * math.exp(-(t - 0.45) * 2.2) + 0.006
        lo.append((a * math.sin(f * 2.7), 4.6 + a * math.cos(f * 3.9), 2.55 + a * math.sin(f * 4.6 + 1)))
        fr.append(f)
    bake(shake, fr, lo)
    # torn shards popping outward at the burst (0.45 s)
    shard_m = D.mat("shard", H("#3E7F5A"), rough=0.5, metal=0.6)
    for i in range(9):
        a = i * 2 * math.pi / 9
        o = D.cone(f"shard{i}", 0.09, 0.42, (0, 4.6 - 0.3, 2.55), m=shard_m, verts=4)
        d = Vector((math.cos(a) * 0.35, -0.2, math.sin(a) * 0.35))
        D.key(o, "scale", F(0.4), (0.01, 0.01, 0.01))
        D.key(o, "scale", F(0.46), (1, 1, 1))
        D.key(o, "location", F(0.44), Vector((0, 4.3, 2.55)))
        D.key(o, "location", F(0.62), Vector((0, 4.3, 2.55)) + d)
        o.rotation_euler = Euler((math.pi / 2 + d.z * 2, 0, a))
    glow = D.sphere("burst_glow", 0.36, (0, 4.25, 2.55), m=emit_mat("burst_glow", H("#FFE7A0"), 6.0))
    key_strength(bpy.data.materials["burst_glow"], [(1, 2.5), (F(0.1), 0.8), (F(0.2), 3.0), (F(0.3), 1.0), (F(0.38), 4.0), (F(0.42), 0.5), (F(0.45), 14.0), (F(0.55), 6.0), (F(1.0), 3.0)])
    gl = point("burst_light", H("#FFD58A"), 0, (0, 3.9, 2.4), 0.3)
    for f, v in [(1, 0), (F(0.44), 0), (F(0.46), 900), (F(0.8), 380)]:
        gl.data.energy = v
        gl.data.keyframe_insert("energy", frame=f)
    # the jet: 230 bills + 36 glowing film-clip cards out of the hole toward camera
    film_m = film_material()
    bpy.ops.mesh.primitive_plane_add(size=1)
    card = bpy.context.active_object
    card.scale = (0.34, 0.21, 1)
    bpy.ops.object.transform_apply(scale=True)
    card.data.materials.append(film_m)
    card_me = card.data
    bpy.data.objects.remove(card)
    hole = Vector((0, 4.22, 2.5))
    for i in range(266):
        is_card = i % 7 == 3
        t0 = 0.45 + (random.random() ** 1.35) * 4.0
        v0 = (random.uniform(-1.6, 1.6), -random.uniform(4.0, 7.5), random.uniform(-0.5, 2.0))
        r0 = (random.uniform(0, 6.3), random.uniform(0, 6.3), random.uniform(0, 6.3))
        w = (random.uniform(-9, 9), random.uniform(-9, 9), random.uniform(-6, 6))
        if is_card:
            o = D.link(bpy.data.objects.new(f"card{i}", card_me))
            w = tuple(c * 0.4 for c in w)
        else:
            o = bill(f"cash{i}")
        p0 = tuple(hole + Vector((random.uniform(-0.12, 0.12), 0, random.uniform(-0.12, 0.12))))
        fr, lo, ro, scl = flight(p0, v0, t0, DUR, r0, w, drag=1.3 if not is_card else 0.9, g=6.5, flutter=0.8, seed=i)
        bake(o, fr, lo, ro, scl)
    # pre-placed pile on the floor (the leak has been going) for depth at frame 1
    for i in range(70):
        o = bill(f"pile{i}")
        o.location = (random.gauss(0, 1.0), random.uniform(1.2, 3.8), 0.01 + random.uniform(0, 0.05))
        o.rotation_euler = (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(0, 6.3))
    # red alarm: beacon + rotating spot, sweeping the room
    beacon = D.cyl("beacon", 0.12, 0.18, (-1.0, 3.6, 3.05), m=emit_mat("beacon", H("#FF1A1A"), 10.0), verts=24)
    rot = D.empty("alarm_rot", (-1.0, 3.6, 2.95))
    for k, ang in enumerate((0, 90, 180, 270)):
        s = D.link(bpy.data.objects.new(f"alarm_spot{k}", bpy.data.lights.new(f"alarm_spot{k}", "SPOT")))
        s.data.color, s.data.energy, s.data.spot_size, s.data.spot_blend = H("#FF2020"), 6000, math.radians(48), 0.4
        s.location = (-1.0, 3.6, 2.95)
        s.rotation_euler = (math.radians(70), 0, math.radians(ang))
        s.parent = rot
        s.matrix_parent_inverse = rot.matrix_world.inverted()
        if k % 2:
            s.data.energy = 0                                         # two opposing beams
    rot.keyframe_insert("rotation_euler", frame=1)
    rot.rotation_euler = (0, 0, math.radians(360 * DUR / 1.1))
    rot.keyframe_insert("rotation_euler", frame=NF + 1)
    for fc in D._fcurves(rot.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"
    point("cyan_fill", CYAN, 220, (2.6, 0.5, 2.6), 1.0)
    point("pipe_under", H("#FFC27A"), 260, (0.3, 3.4, 1.4), 0.6)
    point("pipe_rim", CYAN, 300, (-2.5, 5.6, 2.9), 0.6)
    for i in range(14):
        o = bill(f"trickle{i}")
        fr, lo, ro, scl = flight(tuple(hole), (random.uniform(-0.4, 0.4), -random.uniform(0.6, 1.6), 0.2),
                                 i * 0.03, DUR, (random.uniform(0, 6), 0, random.uniform(0, 6)),
                                 (random.uniform(-6, 6), random.uniform(-6, 6), 2), g=4.0, flutter=0.6, seed=900 + i)
        bake(o, fr, lo, ro, scl)
    point("pink_fill", PINK, 120, (-2.6, 1.0, 2.4), 1.0)
    D.area_light("cash_key", 160, (1.5, 0.0, 2.8), (0, 2.5, 1.4), size=2.5, rgb=H("#FFE9C8"))
    cam, look = D.camera("cam", lens=24)
    D.key(cam, "location", F(0), Vector((0.75, -1.9, 0.75)))
    D.key(look, "location", F(0), Vector((0.0, 4.4, 2.15)))
    D.key(cam, "location", F(DUR), Vector((0.45, -0.6, 0.95)))
    D.key(look, "location", F(DUR), Vector((0.0, 4.4, 2.0)))
    D.ease_all(cam)
    D.ease_all(look)
    D.handheld(cam, strength=0.005, scale=30)
    sc.camera = cam
    L.post(sc, bloom=0.65, bloom_threshold=0.8, vignette=0.3, saturation=1.1)


# ================================================================ SIGN — "Welcome to Vice City" on the arena roof

def sky_world():
    w = bpy.data.worlds.new("night")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sp.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (*H("#FF6A8A"), 1)
    cr.elements[1].position, cr.elements[1].color = 0.35, (*H("#0B0820"), 1)
    e = cr.elements.new(0.1)
    e.color = (*H("#7A2A8C"), 1)
    nt.links.new(sp.outputs["Z"], ramp.inputs[0])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs[1].default_value = 0.9
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])
    sc.world = w


def shot_sign():
    sky_world()
    water = D.box("water", (400, 400, 0.1), (0, 60, -0.3), D.mat("water", H("#0A1230"), rough=0.06, spec=1.0))
    wv = water.modifiers.new("ripple", "WAVE") if False else None  # noqa: F841 (flat water keeps reflections clean)
    ground_m = L.pbr("plaza", "pavement_02", scale=0.25, tint=H("#4A3A5C"), tint_amount=0.6)
    D.box("plaza", (60, 40, 0.6), (0, 4, 0), ground_m)
    # arena: drum + domed roof with ribs + window bands
    concrete = L.pbr("arena", "plastered_wall", scale=0.15, tint=H("#E9E4F2"), tint_amount=0.3)
    drum = D.cyl("drum", 11, 7, (0, 6, 3.8), m=concrete, verts=72)
    for z in (2.0, 4.4):
        D.cyl(f"band{z}", 11.06, 0.7, (0, 6, z + 0.3), m=window_material(f"bandm{z}", H("#18142A"), H("#C77DFF"), scale=(2.5, 1.2), strength=4.0, frac=0.97), verts=72)
    roof = D.sphere("roof", 11.6, (0, 6, 7.3), m=L.plastic("roof", H("#F4F2FA"), rough=0.35, coat=0.4), seg=72, rings=36)
    roof.scale = (1, 1, 0.32)
    rib_m = D.mat("rib", H("#B8B3C9"), rough=0.4, metal=0.5)
    for k in range(24):
        a = k * 2 * math.pi / 24
        o = D.box(f"rib{k}", (0.18, 11.4, 0.18), (math.sin(a) * 5.6, 6 + math.cos(a) * 5.6, 9.6), rib_m)
        o.rotation_euler = (math.radians(-17), 0, -a)
    D.torus("ring_neon", 11.15, 0.06, (0, 6, 7.35), m=emit_mat("ring_neon", CYAN, 9.0))
    # rooftop sign on a scaffold, facing the camera (-y)
    scaf_m = D.mat("scaf", H("#2A2633"), rough=0.5, metal=0.7)
    for x in (-8.5, -3, 3, 8.5):
        D.box(f"post{x}", (0.2, 0.2, 7.5), (x, 1.2, 13.4), scaf_m)
    D.box("beam_top", (18, 0.18, 0.18), (0, 1.2, 16.6), scaf_m)
    D.box("beam_mid", (18, 0.18, 0.18), (0, 1.2, 12.0), scaf_m)
    rot = (math.pi / 2, 0, 0)
    w1, m1 = neon_text("sign_welcome", "Welcome to", 2.6, (0, 0.95, 16.2), H("#FFF0F8"), FONT_SCRIPT, strength=0.0, rot=rot, extrude=0.08)
    w2, m2 = neon_text("sign_vice", "VICE CITY", 3.3, (0, 0.95, 13.0), PINK, FONT_BLACK, strength=0.0, rot=rot, extrude=0.12)
    flick = [(1, 0.0), (F(0.95), 0.0), (F(1.0), 1.0), (F(1.07), 0.0), (F(1.2), 1.0), (F(1.26), 0.15), (F(1.33), 1.0),
             (F(1.5), 0.6), (F(1.55), 1.0)]
    key_strength(m1, [(f, v * 9.0) for f, v in flick])
    key_strength(m2, [(f, (v if f < F(1.15) else min(1.0, v * 1.0)) * 14.0) for f, v in flick[:2] + [(F(1.12), 1.0), (F(1.18), 0.0), (F(1.3), 1.0), (F(1.42), 0.3), (F(1.5), 1.0)]])
    sl = D.area_light("sign_spill", 0, (0, -2.5, 14.0), (0, 6, 9.0), size=16, rgb=PINK)
    for f, v in [(1, 0), (F(0.95), 0), (F(1.0), 3500), (F(1.07), 0), (F(1.3), 3500)]:
        sl.data.energy = v
        sl.data.keyframe_insert("energy", frame=f)
    for fc in D._fcurves(sl.data.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "CONSTANT"
    # skyline across the bay (behind the arena)
    rng = random.Random(3)
    wcols = [H("#FFD9A0"), H("#9AE6FF"), H("#FFB3E0")]
    wms = [window_material(f"win{i}", H("#0B0D16"), c, scale=(1.2, 2.0), strength=1.6, frac=0.28) for i, c in enumerate(wcols)]
    for i in range(46):
        x = rng.uniform(-110, 110)
        y = rng.uniform(95, 140)
        h = rng.uniform(15, 70) * (1.4 if abs(x) < 30 else 1.0)
        wdt = rng.uniform(5, 11)
        D.box(f"tower{i}", (wdt, wdt * rng.uniform(0.7, 1.2), h), (x, y, h / 2 - 0.3), wms[i % 3])
    # waterfront palms (foreground left/right) + moon
    for i, (x, y) in enumerate([(-17, -10), (-13, -14), (-21, -6), (15, -12), (19, -8), (-9, -16), (11, -16), (23, -3)]):
        palm((x, y, 0.3), h=rng.uniform(7, 10), seed=i)
    D.sphere("moon", 6, (-55, 160, 70), m=emit_mat("moon", H("#FFF1DC"), 3.0), seg=32, rings=16)
    # blimp drifting across
    bl = D.empty("blimp", (-48, 30, 26))
    body = D.sphere("blimp_body", 1, (-48, 30, 26), m=L.plastic("blimp_m", H("#D9DCE6"), rough=0.3, coat=0.5), seg=48, rings=24)
    body.scale = (7, 1.9, 1.9)
    band = D.cyl("blimp_band", 1.93, 1.6, (-48, 30, 26), rot=(0, math.pi / 2, 0), m=emit_mat("blimp_band", PINK, 5.0), verts=48)
    gond = D.box("blimp_gond", (2.2, 0.8, 0.6), (-48, 30, 23.9), D.mat("gond", H("#22242E"), rough=0.4))
    blink = D.sphere("blimp_blink", 0.25, (-41, 30, 26), m=emit_mat("blink", H("#FF3030"), 0.0), seg=12, rings=6)
    key_strength(bpy.data.materials["blink"], [(f, 30.0 if (f // 12) % 2 else 0.0) for f in range(1, NF + 2, 6)])
    for p in (body, band, gond, blink):
        p.parent = bl
        p.matrix_parent_inverse = bl.matrix_world.inverted()
    D.key(bl, "location", F(0), Vector((-48, 30, 26)))
    D.key(bl, "location", F(DUR), Vector((-6, 26, 25)))
    for fc in D._fcurves(bl.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"
    D.sun("moonlight", 0.6, (0.4, 1.0, -0.6), rgb=H("#9DB4FF"), angle=3)
    for nm, col, pw, loc in (("plaza_pink", PINK, 2500, (-14, -6, 2.5)), ("plaza_cyan", CYAN, 2500, (14, -4, 2.5))):
        point(nm, col, pw, loc, 0.5).data.specular_factor = 0.0
    D.area_light("arena_wash", 6000, (0, -30, 6), (0, 6, 5), size=20, rgb=H("#C9D4FF")).data.specular_factor = 0.2
    cam, look = D.camera("cam", lens=30)
    keys = [(0.0, (-20, -36, 3.5), (0, 4, 11.5), 26), (5.6, (-7, -33, 5.0), (0, 2, 12.0), 28),
            (7.7, (-1.5, -24, 10.5), (0, 0.9, 14.4), 32)]
    for t, cl, lk, ln in keys:
        D.key(cam, "location", F(t), Vector(cl))
        D.key(look, "location", F(t), Vector(lk))
        cam.data.lens = ln
        cam.data.keyframe_insert("lens", frame=F(t))
    D.ease_all(cam)
    D.ease_all(look)
    D.handheld(cam, strength=0.02, scale=50)
    sc.camera = cam
    L.post(sc, bloom=0.6, bloom_threshold=0.85, vignette=0.28, saturation=1.12)


{"beer": shot_beer, "leak": shot_leak, "sign": shot_sign}[SHOT]()
sc.frame_end = NF
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT, NF)
