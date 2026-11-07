"""blender -b -P scene.py -- <shot> <out.blend>: environment/prop shots for "GTA 6 by hand" (agent A).

Visual language: a 3D artist's viewport becoming GTA. Unfinished = Blender-workbench clay on a grid floor with the
orange "selected" outline + glowing wireframe; finished = Vice-City sunset (pink/orange sky, teal shadows, AgX Punchy).
Every material goes through stage(): clay -> UV checker -> final texture, driven by a shared CTRL node group whose
`time` output is seconds since shot start. Per-object start times are custom props (chk0/tex0) read by an OBJECT
Attribute node, optionally offset by world position so the change sweeps across the object like a wipe.

Shots: trashcan 5.4 | props 2.4 | citypull 2.2 | pipeline 4.4 | florida 2.5 | office 3.6 (seconds, 30 fps, 1080x1920)
No 3D text, numbers or logos.
"""
import math, os, random, sys
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "src", "reelforge", "blender"))
import director as D
import look as L
from director import T

args = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = args[0], args[1]
DUR = {"trashcan": 5.4, "props": 2.4, "citypull": 2.2, "pipeline": 4.4, "florida": 2.5, "office": 3.6}[SHOT]
NF = int(round(DUR * 30))
H = D.hex_lin
PINK, ORANGE, TEAL, PURPLE = H("#FF3E9A"), H("#FF9A3C"), H("#19C3B5"), H("#3B1C5A")
SEL = H("#FFA53A")                    # Blender's active-object outline orange
WIRE = H("#59D7FF")                   # glowing wireframe overlay
CLAY = (0.42, 0.42, 0.42)
VPBG = H("#6A6A70")                   # viewport background grey
ASSETS = os.path.join(HERE, "assets")
random.seed(11)
np.random.seed(11)

sc = D.reset(frames=NF)
D.fast_eevee(sc, samples=16, look="AgX - Punchy")
sc.name = SHOT


# ================================================================ node helpers

def _sock(nt, v, node, i):
    if v is None:
        return
    if isinstance(v, (int, float)):
        node.inputs[i].default_value = v
    elif isinstance(v, tuple):
        node.inputs[i].default_value = (*v[:3], 1) if len(node.inputs[i].default_value) == 4 else v
    else:
        nt.links.new(v, node.inputs[i])


def M(nt, op, a, b=None, c=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation, n.use_clamp = op, clamp
    for i, v in enumerate((a, b, c)):
        _sock(nt, v, n, i)
    return n.outputs[0]


def MIX(nt, fac, a, b, blend="MIX"):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type, n.blend_type = "RGBA", blend
    _sock(nt, fac, n, 0)
    _sock(nt, a, n, 6)
    _sock(nt, b, n, 7)
    return n.outputs[2]


def RGB(nt, rgb):
    n = nt.nodes.new("ShaderNodeRGB")
    n.outputs[0].default_value = (*rgb, 1)
    return n.outputs[0]


def attr(nt, name, kind="OBJECT"):
    n = nt.nodes.new("ShaderNodeAttribute")
    n.attribute_type, n.attribute_name = kind, name
    return n


def world_pos(nt):
    s = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"], s.inputs[0])
    return s.outputs


def clamp01(nt, x):
    return M(nt, "ADD", x, 0.0, clamp=True)


def smooth01(nt, x):
    """smoothstep on an already 0-1 clamped value."""
    x = clamp01(nt, x)
    return M(nt, "MULTIPLY", M(nt, "MULTIPLY", x, x), M(nt, "SUBTRACT", 3.0, M(nt, "MULTIPLY", x, 2.0)))


SUN_T, SUN_D = 0.0, 0.3


def ctrl():
    """Shared node group: time (s since shot start, linear keyframes) and sun (0 grey viewport -> 1 sunset)."""
    ng = bpy.data.node_groups.get("CTRL")
    if ng:
        return ng
    ng = bpy.data.node_groups.new("CTRL", "ShaderNodeTree")
    ng.interface.new_socket("time", in_out="OUTPUT", socket_type="NodeSocketFloat")
    ng.interface.new_socket("sun", in_out="OUTPUT", socket_type="NodeSocketFloat")
    out = ng.nodes.new("NodeGroupOutput")
    v = ng.nodes.new("ShaderNodeValue")
    v.name = "T"
    v.outputs[0].default_value = 0.0
    v.outputs[0].keyframe_insert("default_value", frame=1)
    v.outputs[0].default_value = 1000 / 30
    v.outputs[0].keyframe_insert("default_value", frame=1001)
    for fc in D._fcurves(ng.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"
    ng.links.new(v.outputs[0], out.inputs[0])
    sun = smooth01(ng, M(ng, "DIVIDE", M(ng, "SUBTRACT", v.outputs[0], SUN_T), SUN_D))
    ng.links.new(sun, out.inputs[1])
    return ng


def ctrl_node(nt):
    g = nt.nodes.new("ShaderNodeGroup")
    g.node_tree = ctrl()
    return g


def add_emission(nt, b, col_socket):
    ec = b.inputs["Emission Color"]
    es = b.inputs["Emission Strength"].default_value
    if not ec.is_linked and es > 0 and max(tuple(ec.default_value)[:3]) > 0:
        col_socket = MIX(nt, 1.0, RGB(nt, tuple(c * es for c in tuple(ec.default_value)[:3])), col_socket, "ADD")
    if ec.is_linked:
        col_socket = MIX(nt, 1.0, ec.links[0].from_socket, col_socket, "ADD")
    nt.links.new(col_socket, ec)
    b.inputs["Emission Strength"].default_value = 1.0


def checker_col(nt):
    """Blender-style colour UV grid: checker on object coords, hue by cell."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (9, 9, 9)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 1.0
    ck.inputs["Color1"].default_value = (0.9, 0.9, 0.9, 1)
    ck.inputs["Color2"].default_value = (0.05, 0.05, 0.05, 1)
    nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mp2 = nt.nodes.new("ShaderNodeMapping")
    mp2.inputs["Scale"].default_value = (1.1, 1.1, 1.1)
    nt.links.new(tc.outputs["Object"], mp2.inputs["Vector"])
    nt.links.new(mp2.outputs["Vector"], sep.inputs[0])
    hue = M(nt, "FRACT", M(nt, "ADD", M(nt, "ADD", sep.outputs[0], sep.outputs[2]), M(nt, "MULTIPLY", sep.outputs[1], 0.6)))
    hsv = nt.nodes.new("ShaderNodeCombineColor")
    hsv.mode = "HSV"
    nt.links.new(hue, hsv.inputs[0])
    hsv.inputs[1].default_value, hsv.inputs[2].default_value = 0.75, 1.0
    return MIX(nt, 0.75, ck.outputs["Color"], hsv.outputs[0], "MULTIPLY")


def stage(m, axis=None, k=0.0, chk_dur=0.1, tex_dur=0.14, glow=True, clay=CLAY, radial=False, final_col=None, gw=0.05, gs=1.0):
    """Wrap a material: clay -> UV checker -> its own look. Start times: object props chk0/tex0 (+k*pos[axis])."""
    if m is None or not m.use_nodes or m.get("staged"):
        return m
    m["staged"] = 1
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b is None:
        return m
    bc = b.inputs["Base Color"]
    final = final_col or (bc.links[0].from_socket if bc.is_linked else RGB(nt, tuple(bc.default_value)[:3]))
    t = ctrl_node(nt).outputs["time"]
    off = 0.0
    if axis is not None or radial:
        p = world_pos(nt)
        if radial:
            off = M(nt, "MULTIPLY", M(nt, "SQRT", M(nt, "ADD", M(nt, "MULTIPLY", p[0], p[0]), M(nt, "MULTIPLY", p[1], p[1]))), k)
        else:
            off = M(nt, "MULTIPLY", p["XYZ".index(axis)], k)
    te_c = M(nt, "SUBTRACT", M(nt, "SUBTRACT", t, attr(nt, "chk0").outputs["Fac"]), off)
    te_t = M(nt, "SUBTRACT", M(nt, "SUBTRACT", t, attr(nt, "tex0").outputs["Fac"]), off)
    fc = clamp01(nt, M(nt, "DIVIDE", te_c, chk_dur))
    ft = clamp01(nt, M(nt, "DIVIDE", te_t, tex_dur))
    c1 = MIX(nt, fc, RGB(nt, clay), checker_col(nt))
    nt.links.new(MIX(nt, ft, c1, final), bc)
    for name, clay_v in (("Roughness", 0.55), ("Metallic", 0.0), ("Coat Weight", 0.0)):
        s = b.inputs.get(name)
        if s is None:
            continue
        src = s.links[0].from_socket if s.is_linked else s.default_value
        n = nt.nodes.new("ShaderNodeMix")
        n.data_type = "FLOAT"
        nt.links.new(ft, n.inputs[0])
        n.inputs[2].default_value = clay_v
        _sock(nt, src, n, 3)
        nt.links.new(n.outputs[0], s)
    if glow:                                           # bright wavefronts where checker / texture arrive
        gc = M(nt, "MAXIMUM", M(nt, "SUBTRACT", 1.0, M(nt, "ABSOLUTE", M(nt, "DIVIDE", te_c, gw))), 0.0)
        gt = M(nt, "MAXIMUM", M(nt, "SUBTRACT", 1.0, M(nt, "ABSOLUTE", M(nt, "DIVIDE", te_t, gw * 1.2))), 0.0)
        e = MIX(nt, 1.0, MIX(nt, gc, (0, 0, 0), tuple(c * 3.5 * gs for c in WIRE)),
                MIX(nt, gt, (0, 0, 0), tuple(c * 3 * gs for c in H("#FFD2A8"))), "ADD")
        add_emission(nt, b, e)
    return m


def fog(m, near, far, col_grey, col_sun, power=1.0, strength=1.0):
    """Distance haze: base colour fades out, emission fades in to the horizon colour (grey -> sunset with CTRL.sun)."""
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    cd = nt.nodes.new("ShaderNodeCameraData")
    f = clamp01(nt, M(nt, "DIVIDE", M(nt, "SUBTRACT", cd.outputs["View Distance"], near), far - near))
    if power != 1.0:
        f = M(nt, "POWER", f, power)
    bc = b.inputs["Base Color"]
    src = bc.links[0].from_socket if bc.is_linked else RGB(nt, tuple(bc.default_value)[:3])
    nt.links.new(MIX(nt, f, src, (0, 0, 0)), bc)
    hc = MIX(nt, ctrl_node(nt).outputs["sun"], RGB(nt, col_grey), RGB(nt, col_sun))
    add_emission(nt, b, MIX(nt, M(nt, "MULTIPLY", f, strength), (0, 0, 0), hc))
    return m


def grid_mat(name, minor=0.25, major=1.0, base=H("#3d3d3d"), line=H("#5a5a5a"), majc=H("#6e6e6e"), w=0.012,
             axes=True, fade=(6, 30)):
    """Blender viewport floor: grey with minor/major lines and red X / green Y axes, lines fade with distance."""
    m = D.mat(name, base, rough=0.75)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    p = world_pos(nt)

    def lines(sp, width):
        acc = None
        for ax in (p[0], p[1]):
            d = M(nt, "MULTIPLY", M(nt, "ABSOLUTE", M(nt, "SUBTRACT", M(nt, "FRACT", M(nt, "ADD", M(nt, "DIVIDE", ax, sp), 0.5)), 0.5)), sp)
            l = M(nt, "SUBTRACT", 1.0, clamp01(nt, M(nt, "DIVIDE", d, width)))
            acc = l if acc is None else M(nt, "MAXIMUM", acc, l)
        return acc

    cd = nt.nodes.new("ShaderNodeCameraData")
    fadek = M(nt, "SUBTRACT", 1.0, clamp01(nt, M(nt, "DIVIDE", M(nt, "SUBTRACT", cd.outputs["View Distance"], fade[0]), fade[1] - fade[0])))
    col = MIX(nt, M(nt, "MULTIPLY", lines(minor, w), fadek), base, line)
    col = MIX(nt, M(nt, "MULTIPLY", lines(major, w * 1.6), fadek), col, majc)
    if axes:
        for ax, c in ((p[1], H("#FF3352")), (p[0], H("#8BDC00"))):
            l = M(nt, "SUBTRACT", 1.0, clamp01(nt, M(nt, "DIVIDE", M(nt, "ABSOLUTE", ax), w * 2.2)))
            col = MIX(nt, l, col, c)
    nt.links.new(col, b.inputs["Base Color"])
    return m


def outline_mat(name="sel_outline", col=SEL, strength=3.0):
    """Inverted-hull outline (solidify flipped shell, backface culled); visible while time < object's ol_off."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*col, 1)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    t = ctrl_node(nt).outputs["time"]
    vis = clamp01(nt, M(nt, "DIVIDE", M(nt, "SUBTRACT", attr(nt, "ol_off").outputs["Fac"], t), 0.08))
    nt.links.new(vis, mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


def outline(o, thick=0.012, off=99.0):
    o.data.materials.append(outline_mat())
    s = o.modifiers.new("outline", "SOLIDIFY")
    s.thickness, s.offset, s.use_flip_normals, s.use_rim = thick, 1.0, True, False
    s.material_offset = len(o.data.materials) - 1
    o["ol_off"] = off
    return o


def wire_mat(name, col=WIRE, strength=4.0, axis="Z", k=1.0):
    """Glowing wire: appears with a sweep from w0 (+k*pos) and fades out at w1 (object props)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*col, 1)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    t = ctrl_node(nt).outputs["time"]
    p = world_pos(nt)
    on = clamp01(nt, M(nt, "DIVIDE", M(nt, "SUBTRACT", M(nt, "SUBTRACT", t, attr(nt, "w0").outputs["Fac"]),
                                      M(nt, "MULTIPLY", p["XYZ".index(axis)], k)), 0.06))
    offf = clamp01(nt, M(nt, "DIVIDE", M(nt, "SUBTRACT", attr(nt, "w1").outputs["Fac"], t), 0.25))
    nt.links.new(M(nt, "MULTIPLY", on, offf), mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


def wire_overlay(o, m, w0, w1, thick=0.004, grow=1.004):
    """Linked duplicate (shares mesh + shape keys) drawn as glowing wireframe."""
    w = D.link(bpy.data.objects.new(o.name + "_wire", o.data))
    w.parent = o.parent
    w.matrix_world = o.matrix_world.copy()
    w.scale = tuple(s * grow for s in o.scale)
    mod = w.modifiers.new("wf", "WIREFRAME")
    mod.thickness, mod.use_replace, mod.use_even_offset = thick, True, True
    mod.material_offset = 0
    w.data.materials  # shared
    w.material_slots and None
    # per-object material override on the duplicate
    w.material_slots[0].link = "OBJECT" if len(w.material_slots) else None
    for sl in w.material_slots:
        sl.link = "OBJECT"
        sl.material = m
    w["w0"], w["w1"] = w0, w1
    w.visible_shadow = False
    return w


def key(o, path, f, v):
    setattr(o, path, v)
    o.keyframe_insert(path, frame=f)


def pop(o, f0, s=1.0, dur=12, squash=True):
    """Squash-and-stretch pop in from 0 at frame f0 (origin should sit on the base)."""
    sv = lambda a, b: (a * s, a * s, b * s)
    key(o, "scale", max(1, f0 - 1), (0.001,) * 3)
    if squash:
        key(o, "scale", f0 + dur * 3 // 12, sv(0.8, 1.3))
        key(o, "scale", f0 + dur * 6 // 12, sv(1.14, 0.84))
        key(o, "scale", f0 + dur * 9 // 12, sv(0.96, 1.04))
    else:
        key(o, "scale", f0 + dur // 2, (1.12 * s,) * 3)
    key(o, "scale", f0 + dur, (s,) * 3)
    if f0 - 1 > 1:
        key(o, "scale", 1, (0.001,) * 3)


def hide_until(o, f):
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=1)
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=f)


def hide_from(o, f):
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=f - 1)
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=f)


def setprops(o, **kw):
    objs = [o] + list(o.children_recursive)
    for x in objs:
        for k, v in kw.items():
            x[k] = v


def import_glb(path, name, height=None, keep=None):
    """Import a glTF/GLB under one root empty sitting on z=0, centred in xy; scaled to `height` metres."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        D.adopt(o)
    meshes = [o for o in new if o.type == "MESH"]
    if keep:
        drop = [o for o in meshes if not keep(o)]
        for o in drop:
            bpy.data.objects.remove(o)
        meshes = [o for o in meshes if o not in drop]
        new = [o for o in new if o.name in bpy.data.objects]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    root = D.empty(name)
    sc_ = (height / (hi.z - lo.z)) if height else 1.0
    piv = D.empty(name + "_pivot")
    piv.parent = root
    piv.location = (-(lo.x + hi.x) / 2 * sc_, -(lo.y + hi.y) / 2 * sc_, -lo.z * sc_)
    piv.scale = (sc_,) * 3
    for o in new:
        if o.parent is None:
            o.parent = piv
    for o in meshes:
        for sl in o.material_slots:
            m = sl.material
            if m and getattr(m, "surface_render_method", "") == "BLENDED":
                m.surface_render_method = "DITHERED"
    root["size"] = tuple((hi - lo) * sc_)
    return root, meshes


def glb(n):
    p = os.path.join(ASSETS, n, "model.glb")
    if not os.path.exists(p):
        return None
    import struct
    with open(p, "rb") as fh:
        hdr = fh.read(12)
    return p if len(hdr) == 12 and struct.unpack("<4sII", hdr)[2] == os.path.getsize(p) else None


def camera(name, lens, dof=None):
    c, l = D.camera(name, lens, dof)
    c.data.clip_start, c.data.clip_end = 0.05, 6000
    sc.camera = c
    return c, l


def keypath(o, f0, f1, fn, step=2):
    """Key o.location along fn(u) for u in 0..1 (eased by caller), every `step` frames, linear interp."""
    for f in list(range(f0, f1, step)) + [f1]:
        o.location = fn((f - f0) / max(1, f1 - f0))
        o.keyframe_insert("location", frame=f)
    for fc in D._fcurves(o.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def ease_io(u, p=2.0):
    return u ** p / (u ** p + (1 - u) ** p) if 0 < u < 1 else float(u >= 1)


def ease_out(u, p=2.0):
    return 1 - (1 - u) ** p


# ================================================================ world / light

def sky_world(grey_to_sun=True, hdri="belfast_sunset_puresky", light=1.0, grey_light=0.45, rot=0.0,
              horizon=ORANGE, mid=PINK, top=PURPLE):
    """Camera sees a stylised Vice sunset gradient (or viewport grey before CTRL.sun); lighting from the HDRI."""
    w = bpy.data.worlds.new(SHOT + "_world")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    sun = ctrl_node(nt).outputs["sun"] if grey_to_sun else 1.0
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(L._hdri_path(hdri), check_existing=True)
    tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    lightc = MIX(nt, sun, (grey_light,) * 3, MIX(nt, 1.0, env.outputs["Color"], (light,) * 3, "MULTIPLY"))
    # stylised sky for camera rays
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (*horizon, 1)
    cr.elements[1].position, cr.elements[1].color = 0.5, (*top, 1)
    e = cr.elements.new(0.13)
    e.color = (*mid, 1)
    e2 = cr.elements.new(0.04)
    e2.color = (*[min(1, c * 1.0) for c in H("#FFB45A")], 1)
    nt.links.new(clamp01(nt, sep.outputs[2]), ramp.inputs[0])
    skyc = MIX(nt, sun, VPBG, MIX(nt, 1.0, ramp.outputs[0], (1.25,) * 3, "MULTIPLY"))
    bg_l, bg_c = nt.nodes.new("ShaderNodeBackground"), nt.nodes.new("ShaderNodeBackground")
    nt.links.new(lightc, bg_l.inputs[0])
    nt.links.new(skyc, bg_c.inputs[0])
    lp, mix = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg_l.outputs[0], mix.inputs[1])
    nt.links.new(bg_c.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    sc.world = w
    return w


def light_fade(l, f0, f1, e0, e1, c0=None, c1=None):
    l.data.energy = e0
    l.data.keyframe_insert("energy", frame=f0)
    l.data.energy = e1
    l.data.keyframe_insert("energy", frame=f1)
    if c0:
        l.data.color = c0
        l.data.keyframe_insert("color", frame=f0)
        l.data.color = c1
        l.data.keyframe_insert("color", frame=f1)


def floor(size, m, z=0.0, name="floor"):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    o = D.adopt(bpy.context.active_object)
    o.name = name
    D.give(o, m)
    return o


def mat_tex(name, tex, scale, tint=None, amt=1.0, **kw):
    try:
        return L.pbr(name, tex, scale=scale, tint=tint, tint_amount=amt, **kw)
    except FileNotFoundError:
        return D.mat(name, tint or (0.5, 0.5, 0.5), rough=0.7)


def sunset_floor_mat(name="sidewalk"):
    return mat_tex(name, "pavement_02", 0.9, tint=H("#E9C9B4"), amt=0.35)


# ================================================================ shared street props

def make_can_parts():
    """Procedural trash can that morphs: cube basis -> tapered cylinder key -> vertical ribs key."""
    N, RINGS = 48, 14
    me = bpy.data.meshes.new("can")
    verts, faces = [], []
    for r in range(RINGS + 1):
        for i in range(N):
            verts.append((0, 0, 0))
    bot = len(verts)
    verts.append((0, 0, 0))
    top = len(verts)
    verts.append((0, 0, 0))
    for r in range(RINGS):
        for i in range(N):
            a, b_ = r * N + i, r * N + (i + 1) % N
            faces.append((a, b_, b_ + N, a + N))
    for i in range(N):
        faces.append((bot, (i + 1) % N, i))
        faces.append((top, RINGS * N + i, RINGS * N + (i + 1) % N))
    me.from_pydata(verts, [], faces)
    o = D.link(bpy.data.objects.new("can", me))

    def shape(kind):
        out = []
        for r in range(RINGS + 1):
            h = r / RINGS
            for i in range(N):
                a = 2 * math.pi * i / N
                cx, cy = math.cos(a), math.sin(a)
                if kind == "cube":
                    m_ = max(abs(cx), abs(cy))
                    out.append((cx / m_ * 0.24, cy / m_ * 0.24, h * 0.48))
                else:
                    rad = 0.235 + 0.03 * h
                    if kind == "ribs":
                        rad += 0.008 * (1 if i % 2 == 0 else -1) * (1 if 0.06 < h < 0.94 else 0)
                    out.append((cx * rad, cy * rad, h * 0.7))
        if kind == "cube":
            out += [(0, 0, 0), (0, 0, 0.48)]
        else:
            out += [(0, 0, 0), (0, 0, 0.7)]
        return out

    for v, p in zip(me.vertices, shape("cube")):
        v.co = p
    o.shape_key_add(name="Basis")
    for kind in ("cyl", "ribs"):
        sk = o.shape_key_add(name=kind, from_mix=False)
        for d, p in zip(sk.data, shape(kind)):
            d.co = p
        if kind == "ribs":
            sk.relative_key = o.data.shape_keys.key_blocks["cyl"]
    for p in me.polygons:
        p.use_smooth = True
    bv = o.modifiers.new("bevel", "BEVEL")
    bv.width, bv.segments, bv.limit_method, bv.angle_limit = 0.018, 3, "ANGLE", math.radians(40)
    return o


# ================================================================ SHOT 1: trashcan (hook)


def galv_mat(name, dirt=True):
    """Galvanised steel: zinc spangle colour noise, varying roughness, fine bump, grime at the base."""
    m = D.mat(name, H("#9ea4aa"), rough=0.35, metal=1.0)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    def noise(scale, detail=6):
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = scale, detail
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        return n.outputs["Fac"]
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 60
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    col = MIX(nt, M(nt, "MULTIPLY", vor.outputs["Distance"], 0.6), H("#b9bec3"), H("#7b8187"))
    col = MIX(nt, M(nt, "MULTIPLY", noise(6), 0.5), col, H("#9a9488"))
    rough = M(nt, "ADD", 0.18, M(nt, "MULTIPLY", noise(9), 0.35))
    if dirt:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        g = clamp01(nt, M(nt, "SUBTRACT", 1.0, M(nt, "DIVIDE", sep.outputs[2], 0.22)))
        g = clamp01(nt, M(nt, "MULTIPLY", g, M(nt, "ADD", 0.4, noise(14))))
        col = MIX(nt, g, col, H("#4b4136"))
        rough = M(nt, "ADD", rough, M(nt, "MULTIPLY", g, 0.4))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(rough, b.inputs["Roughness"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.06
    nt.links.new(noise(120, 3), bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def can_assembly(body_m, part_m, outlines=True):
    """Procedural ribbed trash can: morphing body (shape keys), 3 bands, lid (root at 0.7), 2 side handles."""
    can = make_can_parts()
    D.give(can, body_m)
    if outlines:
        outline(can, 0.01)
    bands = []
    for i, z in enumerate((0.07, 0.35, 0.63)):
        rad = 0.235 + 0.03 * z / 0.7 + 0.004
        bpy.ops.mesh.primitive_torus_add(major_radius=rad, minor_radius=0.011, major_segments=64, minor_segments=10,
                                         location=(0, 0, z))
        b = D.adopt(bpy.context.active_object)
        b.name = f"band{i}"
        for p_ in b.data.polygons:
            p_.use_smooth = True
        D.give(b, part_m)
        if outlines:
            outline(b, 0.006)
        bands.append(b)
    lid_root = D.empty("lid_root", (0, 0, 0.7))
    lid = D.cyl("lid", 0.285, 0.035, (0, 0, 0.0175), m=part_m, verts=64)
    dome = D.sphere("dome", 0.28, (0, 0, 0.02), part_m, seg=64, rings=24)
    dome.scale = (1, 1, 0.22)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.07, minor_radius=0.012, location=(0, 0, 0.075),
                                     rotation=(math.pi / 2, 0, 0), major_segments=40, minor_segments=10)
    th = D.adopt(bpy.context.active_object)
    th.name = "lid_handle"
    D.give(th, part_m)
    lidparts = [lid, dome, th]
    for o in lidparts:
        o.parent = lid_root
        for p_ in o.data.polygons:
            p_.use_smooth = True
        if outlines:
            outline(o, 0.006)
    handles = []
    for i, sx in enumerate((1, -1)):
        hr = D.empty(f"handle_root{i}", (sx * 0.262, 0, 0.58))
        bpy.ops.mesh.primitive_torus_add(major_radius=0.06, minor_radius=0.012, location=(0, 0, 0),
                                         rotation=(math.pi / 2, 0, 0), major_segments=40, minor_segments=10)
        hd = D.adopt(bpy.context.active_object)
        hd.name = f"handle{i}"
        hd.scale = (1, 1, 0.7)
        for p_ in hd.data.polygons:
            p_.use_smooth = True
        D.give(hd, part_m)
        hd.parent = hr
        if outlines:
            outline(hd, 0.006)
        handles.append(hr)
    return can, bands, lid_root, lidparts, handles


def static_can(loc, rot_deg=0.0, scale=1.0):
    gm = bpy.data.materials.get("galv_body") or galv_mat("galv_body")
    gp = bpy.data.materials.get("galv_part") or galv_mat("galv_part", dirt=False)
    root = D.empty("can", loc)
    can, bands, lid_root, lidparts, handles = can_assembly(gm, gp, outlines=False)
    kb = can.data.shape_keys.key_blocks
    kb["cyl"].value, kb["ribs"].value = 1.0, 1.0
    lid_root.rotation_euler = (math.radians(4), 0, 0)
    for o in [can, lid_root] + bands + handles:
        o.parent = root
    root.rotation_euler = (0, 0, math.radians(rot_deg))
    root.scale = (scale * 1.2,) * 3
    return root


def shot_trashcan():
    global SUN_T, SUN_D
    SUN_T, SUN_D = 4.0, 0.4
    sky_world(True, light=0.9, grey_light=0.5, rot=200)
    final = sunset_floor_mat()
    fl = floor(80, final)
    grid_into(final)
    fl["chk0"], fl["tex0"] = 99.0, 4.05
    fog(final, 8, 40, VPBG, ORANGE, power=1.2)
    TX = 4.05
    body_m, part_m = galv_mat("galv_body"), galv_mat("galv_part", dirt=False)
    stage(body_m, axis="Z", k=0.4)
    stage(part_m, axis="Z", k=0.4)
    can, bands, lid_root, lidparts, handles = can_assembly(body_m, part_m)
    for o in [can] + bands + lidparts + [h.children[0] for h in handles]:
        o["chk0"], o["tex0"], o["ol_off"] = 3.45, TX, TX
    kb = can.data.shape_keys.key_blocks
    kb["cyl"].value = 0.0
    kb["cyl"].keyframe_insert("value", frame=-5)
    for nm, f0, f1 in (("cyl", None, T(1.15)), ("ribs", T(1.25), T(1.85))):
        if f0:
            kb[nm].value = 0.0
            kb[nm].keyframe_insert("value", frame=f0)
        kb[nm].value = 1.06
        kb[nm].keyframe_insert("value", frame=f1 - 4)
        kb[nm].value = 1.0
        kb[nm].keyframe_insert("value", frame=f1)
    key(can, "rotation_euler", -5, (0, 0, math.radians(-35)))
    key(can, "rotation_euler", T(1.3), (0, 0, 0))
    for i, b in enumerate(bands):
        t0 = T(1.35 + 0.18 * i)
        hide_until(b, t0)
        key(b, "scale", t0, (0.8, 0.8, 0.2))
        key(b, "scale", t0 + 4, (1.05, 1.05, 1.3))
        key(b, "scale", t0 + 8, (1, 1, 1))
    wm = wire_mat("wire", WIRE, 5.0, "Z", 0.9)
    wire_overlay(can, wm, 1.2, 3.35, thick=0.0035, grow=1.006)
    f = T(2.4)
    key(lid_root, "location", 1, (0, 0, 1.15))
    key(lid_root, "location", f - 1, (0, 0, 1.15))
    key(lid_root, "location", f + 5, (0, 0, 0.7))
    key(lid_root, "scale", f + 5, (1.12, 1.12, 0.7))
    key(lid_root, "scale", f + 9, (0.97, 0.97, 1.06))
    key(lid_root, "scale", f + 13, (1, 1, 1))
    hide_until_tree(lid_root, f)
    for hr, t0 in zip(handles, (2.75, 2.95)):
        pop(hr, T(t0), 1.0, dur=9, squash=False)
    # final beat: tiny settle bounce as the texture lands
    key(can, "scale", T(4.0), (1, 1, 1))
    key(can, "scale", T(4.12), (1.025, 1.025, 0.985))
    key(can, "scale", T(4.3), (1, 1, 1))
    # lights: neutral studio while grey; warm sunset rim + pink fill + teal shadow after 4.0
    key_l = D.area_light("key", 60, (-1.6, -1.8, 2.0), (0, 0, 0.4), size=1.5, rgb=(1, 1, 1))
    light_fade(key_l, T(4.0), T(4.4), 60, 26, (1, 1, 1), H("#FFB98A"))
    rim = D.area_light("rim", 0, (1.2, 2.0, 1.4), (0, 0, 0.5), size=1.0, rgb=ORANGE)
    light_fade(rim, T(4.0), T(4.35), 25, 520)
    rim2 = D.area_light("rim2", 0, (-1.8, 1.6, 1.0), (0, 0, 0.5), size=1.0, rgb=PINK)
    light_fade(rim2, T(4.0), T(4.35), 10, 320)
    D.area_light("cool", 30, (1.8, -1.0, 1.2), (0, 0, 0.4), size=2.0, rgb=H("#9FD8FF"))
    sun = D.sun("sun", 0, (-0.6, -0.9, -0.35), ORANGE, angle=2.5)
    light_fade(sun, T(4.0), T(4.35), 0.0, 3.0)
    c, l = camera("cam", 48)
    def cam_at(u):
        e = ease_out(u, 1.6)
        a = math.radians(-62 + 50 * e)
        r = 1.95 - 0.4 * e
        z = 0.9 - 0.18 * e
        return Vector((math.cos(a) * r, math.sin(a) * r, z))
    keypath(c, 1, NF, cam_at, step=2)
    keypath(l, 1, NF, lambda u: Vector((0, 0, 0.36 + 0.06 * ease_out(u))), step=6)
    D.handheld(c, 0.002, scale=50, seed=2)
    L.post(sc, bloom=0.45, bloom_threshold=0.85, vignette=0.28, saturation=1.1, contrast=0.05)


def hide_until_tree(root, f):
    for o in [root] + list(root.children_recursive):
        if o.type == "MESH":
            hide_until(o, f)


def grid_into(m):
    """Insert the viewport-grid colour as the clay stage of material m (floor)."""
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bc = b.inputs["Base Color"]
    final = bc.links[0].from_socket if bc.is_linked else RGB(nt, tuple(bc.default_value)[:3])
    p = world_pos(nt)
    base, line, majc, w = H("#4c4c50"), H("#6c6c70"), H("#86868a"), 0.006
    cd = nt.nodes.new("ShaderNodeCameraData")
    fadek = M(nt, "SUBTRACT", 1.0, clamp01(nt, M(nt, "DIVIDE", M(nt, "SUBTRACT", cd.outputs["View Distance"], GRID[2]), GRID[3] - GRID[2])))

    def lines(sp, width):
        acc = None
        for ax in (p[0], p[1]):
            d = M(nt, "MULTIPLY", M(nt, "ABSOLUTE", M(nt, "SUBTRACT", M(nt, "FRACT", M(nt, "ADD", M(nt, "DIVIDE", ax, sp), 0.5)), 0.5)), sp)
            ln = M(nt, "SUBTRACT", 1.0, clamp01(nt, M(nt, "DIVIDE", d, width)))
            acc = ln if acc is None else M(nt, "MAXIMUM", acc, ln)
        return acc
    w = GRID[4]
    col = MIX(nt, M(nt, "MULTIPLY", lines(GRID[0], w), fadek), base, line)
    col = MIX(nt, M(nt, "MULTIPLY", lines(GRID[1], w * 1.6), fadek), col, majc)
    for ax, c in ((p[1], H("#FF3352")), (p[0], H("#8BDC00"))):
        ln = M(nt, "SUBTRACT", 1.0, clamp01(nt, M(nt, "DIVIDE", M(nt, "ABSOLUTE", ax), w * 2.2)))
        col = MIX(nt, ln, col, c)
    # stage: grid -> final, radial sweep
    t = ctrl_node(nt).outputs["time"]
    rad = M(nt, "SQRT", M(nt, "ADD", M(nt, "MULTIPLY", p[0], p[0]), M(nt, "MULTIPLY", p[1], p[1])))
    te = M(nt, "SUBTRACT", M(nt, "SUBTRACT", t, attr(nt, "tex0").outputs["Fac"]), M(nt, "MULTIPLY", rad, GRID[5]))
    ft = clamp01(nt, M(nt, "DIVIDE", te, 0.12))
    nt.links.new(MIX(nt, ft, col, final), bc)
    rs = b.inputs["Roughness"]
    if rs.is_linked:
        n = nt.nodes.new("ShaderNodeMix")
        n.data_type = "FLOAT"
        nt.links.new(ft, n.inputs[0])
        n.inputs[2].default_value = 0.8
        nt.links.new(rs.links[0].from_socket, n.inputs[3])
        nt.links.new(n.outputs[0], rs)
    gt = M(nt, "MAXIMUM", M(nt, "SUBTRACT", 1.0, M(nt, "ABSOLUTE", M(nt, "DIVIDE", te, 0.035))), 0.0)
    add_emission(nt, b, MIX(nt, gt, (0, 0, 0), tuple(c * 1.5 for c in H("#FFD2A8"))))
    return m


GRID = (0.1, 0.5, 3, 12, 0.006, 0.12)     # minor, major, fade near, fade far, width, sweep s/m


# ================================================================ street corner (props + citypull)

def street_corner(t_bench=None, t_palm=None, fog_far=60):
    """Sidewalk + curb + road + pastel facade + real can; bench and palm (pop + grey->texture if times given)."""
    side = sunset_floor_mat()
    fog(side, 15, fog_far, VPBG, ORANGE, 1.3)
    s = D.box("sidewalk", (40, 4.0, 0.15), (0, 0.5, -0.075), side)
    road_m = mat_tex("road", "asphalt_02", 0.5, tint=H("#5a5468"), amt=0.4)
    fog(road_m, 15, fog_far, VPBG, ORANGE, 1.3)
    road = D.box("road", (400, 30, 0.1), (0, -16.5, -0.2), road_m)
    curb_m = mat_tex("curb", "concrete_floor_02", 1.5, tint=H("#F2E3D8"), amt=0.5)
    D.box("curb", (40, 0.25, 0.2), (0, -1.6, -0.05), curb_m)
    # pastel facade: pink plaster, teal base, white trim, arched windows hint
    wall_m = mat_tex("wall", "plastered_wall", 0.6, tint=H("#F7A3C0"), amt=0.85)
    base_m = mat_tex("wallbase", "plastered_wall", 0.6, tint=H("#2EC4B6"), amt=0.9)
    trim_m = L.plastic("trim", H("#FFF4E8"), rough=0.5, coat=0.1)
    glass = D.mat("glass", H("#1d5f6e"), rough=0.08, metal=0.3)
    D.box("facade", (16, 1.0, 9), (0, 3.0, 4.5), wall_m)
    D.box("facade_base", (16.05, 1.05, 0.9), (0, 3.0, 0.45), base_m)
    D.box("trim1", (16.1, 1.1, 0.16), (0, 3.0, 3.2), trim_m)
    D.box("trim2", (16.1, 1.1, 0.25), (0, 3.0, 8.9), trim_m)
    for x in (-5.5, -2.0, 1.5, 5.0):
        D.box("win", (1.6, 0.1, 1.9), (x, 2.47, 1.95), glass)
        D.box("winframe", (1.8, 0.08, 2.1), (x, 2.5, 1.95), trim_m)
        D.box("win_u", (1.3, 0.1, 1.6), (x, 2.47, 5.4), glass)
        D.box("awn", (1.7, 0.6, 0.08), (x, 2.2, 3.05), L.plastic("awning", TEAL, rough=0.4))
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.name.startswith(("facade", "trim", "win", "awn")):
            pass
    can = static_can((-0.75, -0.55, 0), 20)
    p = glb("bench")
    if p:
        bench, bm = import_glb(p, "bench", height=0.85)
    else:
        bench, bm = proc_bench()
    bench.location = (0.75, 1.0, 0)
    # palm
    palm, pm = make_palm(6.5)
    palm.location = (2.1, 1.75, 0)
    for root, ms, t in ((bench, bm, t_bench), (palm, pm, t_palm)):
        if t is None:
            continue
        for o in ms:
            for sl in o.material_slots:
                stage(sl.material, axis="Z", k=0.04 if root is palm else 0.15, tex_dur=0.12)
            o["chk0"], o["tex0"] = 99.0, t + 0.22
        sz = root.scale[0]
        pop(root, T(t), sz, dur=11)
    return can, bench, palm


def proc_bench():
    root = D.empty("bench")
    wood = mat_tex("bench_wood", "wood_table_001", 2.0, tint=H("#9a5a2e"), amt=0.5)
    iron = D.mat("bench_iron", H("#1f3b33"), rough=0.35, metal=0.7)
    ms = []
    for i, y in enumerate((-0.18, -0.06, 0.06, 0.18)):
        ms.append(D.box("slat", (1.8, 0.1, 0.035), (0, y, 0.45), wood, bevel=0.008))
    for i, z in enumerate((0.62, 0.76)):
        o = D.box("bslat", (1.8, 0.035, 0.11), (0, 0.27 + 0.03 * i, z), wood, bevel=0.008)
        o.rotation_euler = (math.radians(-12), 0, 0)
        ms.append(o)
    for x in (-0.78, 0.78):
        ms.append(D.box("leg_f", (0.05, 0.05, 0.45), (x, -0.2, 0.225), iron, bevel=0.01))
        ms.append(D.box("leg_b", (0.05, 0.05, 0.85), (x, 0.26, 0.425), iron, bevel=0.01))
        ms.append(D.box("arm", (0.05, 0.5, 0.04), (x, 0.0, 0.62), iron, bevel=0.01))
        ms.append(D.box("rail", (0.04, 0.5, 0.04), (x, 0.03, 0.43), iron, bevel=0.01))
    for o in ms:
        o.parent = root
    return root, ms


def make_palm(height):
    p = glb("palms")
    if p:
        root, ms = import_glb(p, "palmpack", height=None)
        # pick the tallest single tree: group meshes by xy cluster
        bpy.context.view_layer.update()
        cents = {}
        for o in ms:
            c = sum((o.matrix_world @ Vector(b) for b in o.bound_box), Vector()) / 8
            cents[o] = c
        # largest bounding height mesh as anchor
        def hgt(o):
            zs = [(o.matrix_world @ Vector(b)).z for b in o.bound_box]
            return max(zs) - min(zs)
        anchor = max(ms, key=hgt)
        ax = cents[anchor]
        span = max(hgt(anchor) * 0.45, 0.01)
        keep = [o for o in ms if (Vector((cents[o].x, cents[o].y)) - Vector((ax.x, ax.y))).length < span]
        for o in ms:
            if o not in keep:
                bpy.data.objects.remove(o)
        bpy.data.objects.remove(root.children[0]) if False else None
        # re-root the kept tree
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in keep for c in o.bound_box]
        lo = Vector((min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts)))
        hi = Vector((max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts)))
        s = height / (hi.z - lo.z)
        r2 = D.empty("palm")
        pv = D.empty("palm_pv")
        pv.parent = r2
        pv.scale = (s,) * 3
        pv.location = (-(lo.x + hi.x) / 2 * s, -(lo.y + hi.y) / 2 * s, -lo.z * s)
        for o in keep:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
            o.parent = pv
            o.matrix_parent_inverse = pv.matrix_world.inverted() if False else Matrix.Identity(4)
            o.matrix_basis = mw
        return r2, keep
    r2 = D.empty("palm")
    trunk = D.cyl("trunk", 0.15, height, (0, 0, height / 2), m=D.mat("bark", H("#7a5a3a")), verts=12)
    trunk.parent = r2
    for i in range(7):
        a = i / 7 * 2 * math.pi
        lf = D.box("leaf", (2.2, 0.5, 0.04), (math.cos(a) * 1.0, math.sin(a) * 1.0, height), D.mat("leafm", H("#3f8f3a")))
        lf.rotation_euler = (0, math.radians(20), a)
        lf.parent = r2
    return r2, [o for o in r2.children]


# ================================================================ SHOT 2: props

def shot_props():
    global SUN_T
    SUN_T = -10
    sky_world(False, light=1.0, rot=200)
    can, bench, palm = street_corner(t_bench=0.1, t_palm=1.0)
    D.sun("sun", 3.2, (-0.55, 0.8, -0.32), H("#FFB070"), angle=2.5)
    D.area_light("fill", 300, (-3, -6, 3), (0.5, 1, 1), size=5, rgb=H("#FF8FC0"))
    D.area_light("tealfill", 200, (5, -4, 2), (0.5, 1, 1), size=4, rgb=TEAL)
    c, l = camera("cam", 26)
    keypath(c, 1, NF, lambda u: Vector((-0.35 + 0.9 * u, -4.3, 0.95 + 0.05 * u)), step=3)
    keypath(l, 1, NF, lambda u: Vector((0.55 + 0.9 * u, 1.0, 2.35)), step=3)
    D.handheld(c, 0.003, scale=50, seed=4)
    L.post(sc, bloom=0.35, bloom_threshold=0.9, vignette=0.26, saturation=1.1, contrast=0.05)


# ================================================================ SHOT 3: citypull

def box_mesh(name, boxes, m):
    """One mesh from many boxes: rows (cx, cy, w, d, h)."""
    b = np.asarray(boxes, dtype=np.float32)
    n = len(b)
    cube = np.array([[-.5, -.5, 0], [.5, -.5, 0], [.5, .5, 0], [-.5, .5, 0],
                     [-.5, -.5, 1], [.5, -.5, 1], [.5, .5, 1], [-.5, .5, 1]], np.float32)
    fq = np.array([[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])
    v = cube[None] * b[:, None, 2:5] + np.stack([b[:, 0], b[:, 1], np.zeros(n)], 1)[:, None]
    f = (fq[None] + 8 * np.arange(n)[:, None, None]).reshape(-1, 4)
    me = bpy.data.meshes.new(name)
    me.from_pydata(v.reshape(-1, 3).tolist(), [], f.tolist())
    o = D.link(bpy.data.objects.new(name, me))
    D.give(o, m)
    return o, v


def city_boxes(extent_x=1400, y0=-600, y1=2600, block=64, street=16, seed=3, excl=None):
    rng = np.random.default_rng(seed)
    out = []
    pitch = block + street
    for bx in np.arange(-extent_x, extent_x, pitch):
        for by in np.arange(y0, y1, pitch):
            cx, cy = bx + block / 2, by + block / 2
            d = math.hypot(cx * 0.7, cy - 1300)
            downtown = math.exp(-(d / 420) ** 2)
            nx, ny = rng.integers(2, 4), rng.integers(2, 4)
            lw, ld = block / nx, block / ny
            for i in range(nx):
                for j in range(ny):
                    x = bx + lw * (i + 0.5)
                    y = by + ld * (j + 0.5)
                    if excl and excl(x, y):
                        continue
                    h = rng.lognormal(2.4, 0.5) + downtown * rng.uniform(20, 160)
                    w = lw * rng.uniform(0.7, 0.95)
                    dd = ld * rng.uniform(0.7, 0.95)
                    out.append((x, y, w, dd, h))
                    if rng.random() < 0.25:            # setback tier
                        out.append((x, y, w * 0.6, dd * 0.6, h * rng.uniform(1.2, 1.6)))
    return out


def shot_citypull():
    global SUN_T
    SUN_T = -10
    sky_world(False, light=1.0, rot=200)
    street_corner(fog_far=900)
    # the corner block sits at the origin; city blocks avoid it and the street in front
    city_m = D.mat("city_clay", (0.26, 0.26, 0.27), rough=0.7)
    fog(city_m, 120, 2600, VPBG, H("#FF8A5C"), power=0.8, strength=1.15)
    excl = lambda x, y: (abs(x) < 14 and -40 < y < 30) or (-34 < y < 2)
    boxes = city_boxes(excl=excl)
    city, _ = box_mesh("city", boxes, city_m)
    print("city boxes", len(boxes))
    # ground: grey grid (viewport) under the city
    gm = grid_mat("cgrid", minor=16, major=80, base=H("#454545"), line=H("#525252"), majc=H("#5c5c5c"), w=0.6,
                  axes=False, fade=(200, 1500))
    fog(gm, 120, 2600, VPBG, H("#FF8A5C"), power=0.8, strength=1.15)
    floor(8000, gm, z=-0.26, name="cityfloor")
    # few palms along the avenue near camera
    palm, pm = make_palm(9)
    palm.location = (-9, -1.2, 0)
    for i, (x, y) in enumerate(((22, -1.2), (40, -1.2), (-30, -1.2), (60, -33), (-55, -33), (90, -1.2), (-80, -1.2))):
        r = D.empty(f"palm_inst{i}", (x, y, 0))
        r.scale = (random.uniform(0.9, 1.2),) * 3
        r.rotation_euler = (0, 0, random.uniform(0, 6.28))
        for o in pm:
            d = D.link(bpy.data.objects.new(o.name + f"_i{i}", o.data))
            d.parent = r
            d.matrix_basis = palm.matrix_world.inverted() @ o.matrix_world if False else (o.matrix_world.copy())
    D.sun("sun", 3.2, (-0.55, 0.8, -0.32), H("#FFB070"), angle=2.5)
    D.area_light("fill", 400, (-3, -8, 4), (0, 1, 1), size=6, rgb=H("#FF8FC0"))
    c, l = camera("cam", 26)
    def cam_at(u):
        e = ease_io(u, 2.4)
        return Vector((0.55 - 0.55 * e, -4.3 - 230 * e, 1.0 + 330 * e ** 0.85))
    def look_at(u):
        e = ease_io(u, 2.0)
        return Vector((1.45 - 1.45 * e, 1.0 + 900 * e, 2.35 - 2.35 * e))
    keypath(c, 1, NF, cam_at, step=1)
    keypath(l, 1, NF, look_at, step=1)
    sc.render.motion_blur_shutter = 0.6
    L.post(sc, bloom=0.35, bloom_threshold=0.9, vignette=0.26, saturation=1.1, contrast=0.05)


# ================================================================ SHOT 4: pipeline

def shot_pipeline():
    global SUN_T, SUN_D, GRID
    SUN_T, SUN_D = 3.3, 0.35
    GRID = (1.0, 5.0, 25, 80, 0.035, 0.03)
    sky_world(True, light=1.0, grey_light=0.5, rot=200)
    final = mat_tex("lawn", "pavement_02", 0.25, tint=H("#E9C9B4"), amt=0.35)
    grid_into(final)
    fl = floor(600, final)
    fl["tex0"] = 3.3
    fog(final, 40, 220, VPBG, ORANGE, 1.2)
    TX = 3.3
    root = D.empty("bld")
    W, Dp, Hh = 9.0, 7.0, 17.0
    # materials (each staged; clay before, checker at 2.5, texture at 3.3)
    plaster = mat_tex("plaster", "plastered_wall", 0.35, tint=H("#F6A6C1"), amt=0.85)
    mint = mat_tex("mint", "plastered_wall", 0.35, tint=H("#7FE0CF"), amt=0.85)
    white = L.plastic("deco_white", H("#FFF3E6"), rough=0.45, coat=0.15)
    glass = D.mat("bglass", H("#2a7f95"), rough=0.08, metal=0.2, emit=H("#FFC08A"), emit_strength=0.1)
    rail = D.mat("rail", H("#FFF8F0"), rough=0.3, metal=0.6)
    for m in (plaster, mint, white, glass, rail):
        stage(m, axis="Z", k=0.022, chk_dur=0.08, tex_dur=0.12, gw=0.012, gs=0.8)
    body = D.box("body", (1, 1, 1), (0, 0, 0.5), plaster)
    body.location = (0, 0, 0)
    me = body.data
    for v in me.vertices:
        v.co.z += 0.5
    body.parent = root
    outline(body, 0.02, off=TX)
    # cube 4 m -> building
    key(body, "scale", 1, (4, 4, 4))
    key(body, "scale", T(1.5), (4, 4, 4))
    key(body, "scale", T(1.5) + 5, (W * 1.04, Dp * 1.04, Hh * 1.06))
    key(body, "scale", T(1.5) + 9, (W, Dp, Hh))
    parts = [body]
    fronty = -Dp / 2
    floors = 5
    fh = Hh / floors
    for fi in range(floors):
        z0 = fi * fh
        tpop = 1.62 + 0.11 * fi
        grp = D.empty(f"floor{fi}", (0, fronty, z0))
        grp.parent = root
        if fi > 0:
            eb = D.box("eyebrow", (W + 0.6, 0.9, 0.18), (0, -0.35, 0.0), white)
            eb.parent = grp
        for xi, x in enumerate((-3.3, -1.6, 1.6, 3.3)):
            fr = D.box("wframe", (1.25, 0.3, 1.7), (x, -0.1, fh * 0.5), white)
            fr.parent = grp
            gl = D.box("wglass", (1.0, 0.1, 1.45), (x, -0.27, fh * 0.5), glass)
            gl.parent = grp
            parts += [fr, gl]
        if fi > 0:
            bal = D.box("balcony", (2.4, 1.3, 0.18), (0, -0.65, 0.12), mint)
            bal.parent = grp
            rl = D.box("brail", (2.4, 0.06, 0.9), (0, -1.28, 0.6), rail)
            rl.parent = grp
            parts += [bal, rl]
        else:
            door = D.box("door", (2.0, 0.3, 2.6), (0, -0.1, 1.3), glass)
            door.parent = grp
            can = D.box("canopy", (3.4, 1.6, 0.2), (0, -0.8, 2.9), mint)
            can.parent = grp
            parts += [door, can]
        hide_until(grp, 1)
        pop(grp, T(tpop), 1.0, dur=8, squash=False)
    # art-deco crown: stepped parapet + central fin
    crown = D.empty("crown", (0, 0, Hh))
    crown.parent = root
    for o in (D.box("step1", (W * 0.7, Dp * 0.8, 1.2), (0, 0, 0.6), plaster),
              D.box("step2", (W * 0.4, Dp * 0.6, 2.4), (0, 0, 1.2), plaster),
              D.box("fin", (0.8, Dp * 0.5 + 1.0, 4.6), (0, -0.4, 2.3), mint),
              D.box("crownband", (W * 0.72, Dp * 0.82, 0.2), (0, 0, 1.2), white)):
        o.parent = crown
        parts.append(o)
    pop(crown, T(2.15), 1.0, dur=8)
    for side in (-1, 1):
        pil = D.box("pilaster", (0.5, 0.5, Hh + 0.6), (side * (W / 2 + 0.05), fronty - 0.05, (Hh + 0.6) / 2), mint)
        pil.parent = root
        key(pil, "scale", 1, (1, 1, 0.0))
        key(pil, "scale", T(1.6), (1, 1, 0.0))
        key(pil, "scale", T(2.0), (1, 1, 1))
        parts.append(pil)
    for o in parts + list(root.children_recursive):
        if o.type == "MESH":
            o["chk0"], o["tex0"] = 2.5, TX
    # outlines on details while grey
    # wireframe flash over the body during modelling
    wm = wire_mat("bwire", WIRE, 4.0, "Z", 0.02)
    bodyw = wire_overlay(body, wm, 1.5, 2.6, thick=0.006, grow=1.004)
    bodyw.parent = root
    key(bodyw, "scale", 1, (4.02, 4.02, 4.02))
    key(bodyw, "scale", T(1.5), (4.02, 4.02, 4.02))
    key(bodyw, "scale", T(1.5) + 5, (W * 1.044, Dp * 1.044, Hh * 1.064))
    key(bodyw, "scale", T(1.5) + 9, (W * 1.004, Dp * 1.004, Hh * 1.004))
    # subdivide body mesh so the wireframe shows edge loops
    bm_ = bmesh.new()
    bm_.from_mesh(body.data)
    bmesh.ops.subdivide_edges(bm_, edges=bm_.edges[:], cuts=5, use_grid_fill=True)
    bm_.to_mesh(body.data)
    bm_.free()
    # light
    key_l = D.area_light("key", 6000, (-25, -30, 30), (0, 0, 8), size=12, rgb=(1, 1, 1))
    light_fade(key_l, T(3.3), T(3.7), 6000, 2500, (1, 1, 1), H("#FFC9A0"))
    sun = D.sun("sun", 0, (0.65, 0.55, -0.3), ORANGE, angle=2.5)
    light_fade(sun, T(3.3), T(3.7), 0.0, 4.0)
    rim = D.area_light("rim", 0, (20, 25, 18), (0, 0, 8), size=10, rgb=PINK)
    light_fade(rim, T(3.3), T(3.7), 0, 25000)
    c, l = camera("cam", 32)
    def cam_at(u):
        a = math.radians(-118 + 26 * u)
        grow = ease_io(min(1, max(0, (u * DUR - 1.4) / 1.0)), 2)
        r = 14 + 18 * grow
        z = 3.0 + 5.0 * grow
        return Vector((math.cos(a) * r, math.sin(a) * r, z))
    def look_at(u):
        grow = ease_io(min(1, max(0, (u * DUR - 1.4) / 1.0)), 2)
        return Vector((0, 0, 2.0 + 8.8 * grow))
    keypath(c, 1, NF, cam_at, step=2)
    keypath(l, 1, NF, look_at, step=2)
    D.handheld(c, 0.004, scale=60, seed=5)
    L.post(sc, bloom=0.4, bloom_threshold=0.85, vignette=0.26, saturation=1.1, contrast=0.05)


# ================================================================ SHOT 5: florida

FLA = [(-62, 46), (-40, 44), (-22, 41), (-10, 40), (0, 41), (8, 44), (14, 46), (16, 40), (19, 30), (23, 18),
       (27, 6), (31, -8), (34, -22), (35, -34), (33, -44), (28, -50), (22, -52), (18, -47), (13, -38), (8, -30),
       (4, -24), (1, -16), (-1, -6), (-3, 4), (-6, 14), (-9, 24), (-14, 31), (-22, 33), (-32, 36), (-44, 37),
       (-55, 38), (-62, 39)]
KEYS = [(16, -55), (12, -58), (8, -60.5), (4, -62.5), (0, -64), (-4, -65), (-8, -65.5), (-12, -66)]


def inside(px, py, poly):
    poly = np.asarray(poly)
    x, y = poly[:, 0], poly[:, 1]
    xj, yj = np.roll(x, 1), np.roll(y, 1)
    res = np.zeros(px.shape, bool)
    for a, b, c, d in zip(x, y, xj, yj):
        cond = ((b > py) != (d > py)) & (px < (c - a) * (py - b) / (d - b + 1e-9) + a)
        res ^= cond
    return res


def shot_florida():
    global SUN_T
    SUN_T = -10
    sky_world(False, light=1.0, rot=160)
    # land (extruded polygon) + keys
    land_m = D.mat("land", H("#4f9a46"), rough=0.8)
    nt = land_m.node_tree
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.08
    nz.inputs["Detail"].default_value = 8
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(MIX(nt, nz.outputs["Fac"], H("#2f7d3c"), H("#9cc25a")), nt.nodes["Principled BSDF"].inputs["Base Color"])
    stage(land_m, axis="Y", k=0.014, chk_dur=0.1, tex_dur=0.25, glow=False)

    def slab(name, pts, h=0.6):
        me = bpy.data.meshes.new(name)
        me.from_pydata([(x, y, 0) for x, y in pts], [], [list(range(len(pts)))])
        o = D.link(bpy.data.objects.new(name, me))
        bm_ = bmesh.new()
        bm_.from_mesh(me)
        r = bmesh.ops.extrude_face_region(bm_, geom=bm_.faces[:])
        for v in r["geom"]:
            if isinstance(v, bmesh.types.BMVert):
                v.co.z = h
        bmesh.ops.recalc_face_normals(bm_, faces=bm_.faces[:])
        bm_.to_mesh(me)
        bm_.free()
        D.give(o, land_m)
        bv = o.modifiers.new("bev", "BEVEL")
        bv.width, bv.segments = 0.3, 2
        o["chk0"], o["tex0"] = 0.4, 0.55
        return o
    slab("land", FLA)
    for i, (x, y) in enumerate(KEYS):
        r = 1.6 - i * 0.08
        slab(f"key{i}", [(x + math.cos(a) * r * 1.6, y + math.sin(a) * r * 0.7) for a in np.linspace(0, 2 * math.pi, 10)[:-1]])
    # sea
    sea = D.mat("sea", H("#0f6f7a"), rough=0.12)
    snt = sea.node_tree
    nz = snt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.6
    bp = snt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.08
    snt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    snt.links.new(bp.outputs["Normal"], snt.nodes["Principled BSDF"].inputs["Normal"])
    stage(sea, axis=None, chk_dur=0.1, tex_dur=0.6, glow=False, clay=(0.06, 0.06, 0.065))
    fog(sea, 260, 900, VPBG, H("#FF8A5C"), 1.0, 1.0)
    so = floor(2000, sea, z=0.1, name="sea")
    so["chk0"], so["tex0"] = 99.0, 0.9
    # buildings: sample points inside the polygon, clustered around cities
    rng = np.random.default_rng(5)
    cities = [(28, -40, 5, 1500), (5, -10, 5, 500), (12, 8, 4, 700), (12, 40, 4, 500), (-20, 38, 3, 250),
              (24, -20, 3, 400), (-50, 42, 3, 150)]
    pts = []
    for cx, cy, s, n in cities:
        pts.append(rng.normal((cx, cy), s, (n, 2)))
    pts.append(np.stack([rng.uniform(-62, 36, 4000), rng.uniform(-55, 46, 4000)], 1))
    pts = np.concatenate(pts)
    pts = pts[inside(pts[:, 0], pts[:, 1], FLA)]
    kp = np.concatenate([rng.normal(k, (1.2, 0.4), (25, 2)) for k in KEYS])
    pts = np.concatenate([pts, kp])
    n = len(pts)
    dens = np.zeros(n)
    for cx, cy, s, _ in cities:
        dens += np.exp(-((pts[:, 0] - cx) ** 2 + (pts[:, 1] - cy) ** 2) / (2 * (s * 1.3) ** 2))
    hgt = 0.3 + rng.lognormal(-1.0, 0.5, n) + dens * rng.uniform(0.8, 4.0, n)
    fp = rng.uniform(0.35, 0.7, n)
    is_palm = rng.random(n) < 0.18
    bx = [(x, y, f, f * rng.uniform(0.8, 1.2), h) for (x, y), f, h, pm in zip(pts, fp, hgt, is_palm) if not pm]
    bld_m = D.mat("bld", (1, 1, 1), rough=0.5)
    bnt = bld_m.node_tree
    at = bnt.nodes.new("ShaderNodeAttribute")
    at.attribute_type, at.attribute_name = "GEOMETRY", "col"
    bnt.links.new(at.outputs["Color"], bnt.nodes["Principled BSDF"].inputs["Base Color"])
    stage(bld_m, axis="Y", k=0.014, chk_dur=0.05, tex_dur=0.12, glow=True)
    bo, verts = box_mesh("buildings", bx, bld_m)
    bo.location.z = 0.6
    bo["chk0"], bo["tex0"] = 99.0, 0.55
    pal = [H(c) for c in ("#FFB3C7", "#FFFFFF", "#7FE0CF", "#FFD39A", "#F6A6C1", "#BDE7FF", "#FFE9D6")]
    cols = np.array([pal[i] for i in rng.integers(0, len(pal), len(bx))])
    ca = bo.data.color_attributes.new("col", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", np.concatenate([np.repeat(cols, 8, 0), np.ones((len(bx) * 8, 1))], 1).ravel().astype(np.float32))
    # palms: tiny cones (trunk) with green ico tops -> a second box mesh (squat green "crowns")
    pp = [(x, y, 0.5, 0.5, 0.9) for (x, y), pm in zip(pts, is_palm) if pm]
    palm_m = D.mat("palmdot", H("#2fae4a"), rough=0.6)
    stage(palm_m, axis="Y", k=0.014, chk_dur=0.05, tex_dur=0.12)
    po, pverts = box_mesh("palms", pp, palm_m)
    po.location.z = 0.6
    po["chk0"], po["tex0"] = 99.0, 0.55
    # waves south -> north: shape keys per band; basis = flattened
    for o, vv in ((bo, verts), (po, pverts)):
        flat = vv.copy()
        flat[:, :, 2] = 0.0
        full = vv.reshape(-1, 3)
        for v, p in zip(o.data.vertices, flat.reshape(-1, 3)):
            v.co = p
        o.shape_key_add(name="Basis")
        ys = vv[:, 0, 1]
        NB = 12
        edges = np.linspace(-67, 47, NB + 1)
        for bi in range(NB):
            sel = (ys >= edges[bi]) & (ys < edges[bi + 1])
            sk = o.shape_key_add(name=f"b{bi}", from_mix=False)
            co = flat.copy()
            co[sel] = vv[sel]
            sk.data.foreach_set("co", co.reshape(-1).astype(np.float32))
            t0 = 0.12 + bi * 0.115
            f0 = T(t0)
            sk.value = 0
            sk.keyframe_insert("value", frame=max(1, f0 - 1))
            sk.value = 1.35
            sk.keyframe_insert("value", frame=f0 + 3)
            sk.value = 1.0
            sk.keyframe_insert("value", frame=f0 + 7)
            if f0 - 1 > 1:
                sk.value = 0
                sk.keyframe_insert("value", frame=1)
    D.sun("sun", 3.0, (-0.5, 0.75, -0.35), H("#FFB070"), angle=3)
    D.area_light("fill", 3e5, (60, -140, 120), (0, 0, 0), size=80, rgb=H("#FF8FC0"))
    c, l = camera("cam", 27)
    def cam_at(u):
        a = math.radians(-96 + 12 * u)
        r = 62 - 6 * u
        return Vector((math.cos(a) * r - 6, math.sin(a) * r - 8, 150 - 12 * u))
    keypath(c, 1, NF, cam_at, step=2)
    keypath(l, 1, NF, lambda u: Vector((-16 + 2 * u, -6 + 3 * u, 0)), step=4)
    L.post(sc, bloom=0.35, bloom_threshold=0.9, vignette=0.26, saturation=1.12, contrast=0.05)


# ================================================================ SHOT 6: office

def shot_office():
    global SUN_T
    SUN_T = -10
    HAZE = H("#E79A6A")
    sky_world(False, light=0.35, rot=90, horizon=H("#FFB07A"), mid=H("#F07FA8"), top=H("#3a2a5a"))
    # floor: dark blue carpet, fog to warm haze
    carpet = D.mat("carpet", H("#1e2538"), rough=0.9)
    fog(carpet, 25, 260, HAZE, HAZE, 0.9, 1.0)
    floor(2000, carpet)
    # one desk unit (joined mesh, several materials)
    parts = []
    desk = L.plastic("desk", H("#E9E4DC"), rough=0.4, coat=0.1)
    metal = D.mat("legs", H("#2a2d33"), rough=0.35, metal=0.8)
    mon = D.mat("monitor", H("#15161a"), rough=0.3)
    scr = D.mat("screen", H("#0a1a2a"), rough=0.2, emit=H("#56C7FF"), emit_strength=6.0)
    chair = D.mat("chair", H("#1d2230"), rough=0.6)
    skin = D.mat("skin", H("#c98e6b"), rough=0.6)
    shirt = D.mat("shirt", (1, 1, 1), rough=0.6)
    snt = shirt.node_tree
    oi = snt.nodes.new("ShaderNodeObjectInfo")
    ramp = snt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].color, els[1].color = (*H("#FF6B9A"), 1), (*H("#2EC4B6"), 1)
    e = els.new(0.33)
    e.color = (*H("#FFD166"), 1)
    e = els.new(0.66)
    e.color = (*H("#7AA2FF"), 1)
    ramp.color_ramp.interpolation = "CONSTANT"
    snt.links.new(oi.outputs["Random"], ramp.inputs[0])
    snt.links.new(ramp.outputs[0], snt.nodes["Principled BSDF"].inputs["Base Color"])
    for m in (desk, metal, mon, scr, chair, skin, shirt):
        fog(m, 25, 260, HAZE, HAZE, 0.9, 1.0)
    parts.append(D.box("top", (1.4, 0.72, 0.04), (0, 0, 0.74), desk))
    parts.append(D.box("legL", (0.04, 0.66, 0.72), (-0.66, 0, 0.36), metal))
    parts.append(D.box("legR", (0.04, 0.66, 0.72), (0.66, 0, 0.36), metal))
    parts.append(D.box("divider", (1.4, 0.03, 0.42), (0, 0.37, 0.95), D.mat("divm", H("#8C93A8"), rough=0.8)))
    fog(bpy.data.materials["divm"], 25, 260, HAZE, HAZE, 0.9, 1.0)
    parts.append(D.box("mon", (0.58, 0.035, 0.36), (0, 0.18, 1.08), mon))
    parts.append(D.box("scr", (0.54, 0.01, 0.32), (0, 0.16, 1.08), scr))
    parts.append(D.box("stand", (0.05, 0.05, 0.2), (0, 0.21, 0.86), metal))
    parts.append(D.box("seat", (0.48, 0.46, 0.08), (0, -0.55, 0.48), chair))
    parts.append(D.box("back", (0.46, 0.06, 0.55), (0, -0.8, 0.82), chair))
    parts.append(D.box("torso", (0.4, 0.24, 0.55), (0, -0.6, 0.8), shirt))
    parts.append(D.sphere("head", 0.12, (0, -0.55, 1.2), skin, seg=12, rings=8))
    parts.append(D.box("armL", (0.09, 0.42, 0.09), (-0.17, -0.32, 0.8), shirt))
    parts.append(D.box("armR", (0.09, 0.42, 0.09), (0.17, -0.32, 0.8), shirt))
    parts.append(D.box("thighs", (0.38, 0.4, 0.14), (0, -0.4, 0.55), H and D.mat("pants", H("#2c2f3a"), rough=0.7)))
    fog(bpy.data.materials["pants"], 25, 260, HAZE, HAZE, 0.9, 1.0)
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    unit = bpy.context.active_object
    unit.name = "desk_unit"
    # 4,700 positions: 47 columns x 100 rows, aisles every 5 desks
    NX, NY = 47, 100
    xs = np.array([i * 1.55 + (i // 5) * 2.2 for i in range(NX)])
    xs -= xs.mean()
    ys = np.array([j * 2.1 + (j // 4) * 1.8 for j in range(NY)])
    gx, gy = np.meshgrid(xs, ys)
    pts = np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], 1)
    me = bpy.data.meshes.new("desk_pts")
    me.from_pydata(pts.tolist(), [], [])
    holder = D.link(bpy.data.objects.new("desks", me))
    holder.instance_type = "VERTS"
    unit.parent = holder
    unit.location = (0, 0, 0)
    print("desks", len(pts))
    # columns for scale
    colm = L.plastic("col", H("#F2EDE6"), rough=0.6, coat=0.0)
    fog(colm, 25, 260, HAZE, HAZE, 0.9, 1.0)
    cpts = [(x, y, 0) for x in np.arange(-36, 37, 14.4) for y in np.arange(4, 260, 17.0)]
    cm = bpy.data.meshes.new("col_pts")
    cm.from_pydata(cpts, [], [])
    ch = D.link(bpy.data.objects.new("cols", cm))
    ch.instance_type = "VERTS"
    cu = D.box("column", (0.7, 0.7, 4.5), (0, 0, 2.25), colm)
    cu.parent = ch
    # ceiling light strips floating (warm) - only low, the camera rises past them
    D.sun("sun", 2.2, (-0.4, 0.8, -0.45), H("#FFC27A"), angle=4)
    D.area_light("cool", 2e4, (0, 40, 30), (0, 40, 0), size=60, rgb=H("#6FB8FF"))
    c, l = camera("cam", 30)
    def cam_at(u):
        e = ease_io(u, 1.8)
        return Vector((0.95 + 1.0 * e, -6 - 22 * e, 1.75 + 46 * e))
    def look_at(u):
        e = ease_io(u, 1.8)
        return Vector((0.95, 30 + 40 * e, 1.0 - 1.0 * e))
    keypath(c, 1, NF, cam_at, step=1)
    keypath(l, 1, NF, look_at, step=1)
    D.handheld(c, 0.003, scale=60, seed=6)
    L.post(sc, bloom=0.5, bloom_threshold=0.8, vignette=0.28, saturation=1.1, contrast=0.05)


# ================================================================ main

{"trashcan": shot_trashcan, "props": shot_props, "citypull": shot_citypull, "pipeline": shot_pipeline,
 "florida": shot_florida, "office": shot_office}[SHOT]()
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT))
print("saved", OUT)
