"""Shared helpers for the gta6-download Blender shots (runs inside Blender 5.x)."""
import math, os, random, sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(PROJ, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "reelforge", "blender"))
import director as D  # noqa: E402
import look as L  # noqa: E402

TEX = os.path.join(PROJ, "tex")
FPS = 30


def start(dur, samples=24, raytrace=True):
    nf = max(2, int(round(dur * FPS)))
    s = D.reset(frames=nf)
    D.fast_eevee(s, samples=samples, raytrace=raytrace, look="AgX - Punchy")
    try:
        s.view_settings.look = "AgX - Punchy"
    except TypeError:
        try:
            s.view_settings.look = "Punchy"
        except TypeError:
            pass
    s.render.use_motion_blur = True
    return s, nf


def ease(x, kind="io"):
    x = min(1.0, max(0.0, x))
    if kind == "lin":
        return x
    if kind == "out":
        return 1 - (1 - x) ** 3
    if kind == "in":
        return x ** 3
    return x * x * (3 - 2 * x)


def key(obj, path, fn, nf, index=-1):
    """Bake fn(t01, frame) → value on every frame (no f-curve access needed)."""
    for f in range(1, nf + 1):
        v = fn((f - 1) / max(1, nf - 1), f)
        if index >= 0:
            getattr(obj, path)[index] = v
        else:
            setattr(obj, path, v)
        obj.keyframe_insert(path, frame=f, index=index)


def key_sock(sock, fn, nf):
    for f in range(1, nf + 1):
        sock.default_value = fn((f - 1) / max(1, nf - 1), f)
        sock.keyframe_insert("default_value", frame=f)


def link(o, scene=None):
    (scene or bpy.context.scene).collection.objects.link(o)
    return o


# ------------------------------------------------------------------ node sugar
class NT:
    def __init__(self, tree):
        self.t = tree

    def n(self, typ, **kw):
        node = self.t.nodes.new(typ)
        ins = kw.pop("ins", {})
        for k, v in kw.items():
            setattr(node, k, v)
        for k, v in ins.items():
            self.set(node.inputs[k], v)
        return node

    def set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.t.links.new(v, sock)
        elif isinstance(v, bpy.types.Node):
            self.t.links.new(v.outputs[0], sock)
        else:
            sock.default_value = v

    def math(self, op, a, b=None, c=None, clamp=False):
        node = self.t.nodes.new("ShaderNodeMath")
        node.operation, node.use_clamp = op, clamp
        self.set(node.inputs[0], a)
        if b is not None:
            self.set(node.inputs[1], b)
        if c is not None:
            self.set(node.inputs[2], c)
        return node.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        node = self.t.nodes.new("ShaderNodeVectorMath")
        node.operation = op
        self.set(node.inputs[0], a)
        if b is not None:
            self.set(node.inputs[1], b)
        if scale is not None:
            self.set(node.inputs["Scale"], scale)
        return node

    def maprange(self, v, a, b, c=0.0, d=1.0, smooth=False):
        node = self.t.nodes.new("ShaderNodeMapRange")
        node.clamp = True
        if smooth:
            node.interpolation_type = "SMOOTHSTEP"
        self.set(node.inputs["Value"], v)
        for k, x in (("From Min", a), ("From Max", b), ("To Min", c), ("To Max", d)):
            self.set(node.inputs[k], x)
        return node.outputs[0]

    def mix(self, fac, a, b, blend="MIX"):
        node = self.t.nodes.new("ShaderNodeMix")
        node.data_type, node.blend_type = "RGBA", blend
        self.set(node.inputs[0], fac)
        self.set(node.inputs[6], a)
        self.set(node.inputs[7], b)
        return node.outputs[2]

    def value(self, v=0.0):
        node = self.t.nodes.new("ShaderNodeValue")
        node.outputs[0].default_value = v
        return node.outputs[0]

    def image(self, path, vec=None, colorspace="sRGB", ext="REPEAT", interp="Linear"):
        node = self.t.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(path, check_existing=True)
        node.image.colorspace_settings.name = colorspace
        node.extension, node.interpolation = ext, interp
        if vec is not None:
            self.set(node.inputs["Vector"], vec)
        return node


def new_mat(name, blended=False):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    m.node_tree.nodes.clear()
    nt = NT(m.node_tree)
    out = nt.n("ShaderNodeOutputMaterial")
    if blended:
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    return m, nt, out


def pbr(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emit=None, emit_strength=0.0, coat=0.0, alpha=1.0, spec=0.5,
        transmission=0.0, ior=1.45):
    m, nt, out = new_mat(name, blended=alpha < 1.0)
    p = nt.n("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color[:3], 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Alpha"].default_value = alpha
    for k, v in (("Coat Weight", coat), ("Specular IOR Level", spec), ("Transmission Weight", transmission), ("IOR", ior)):
        if k in p.inputs:
            p.inputs[k].default_value = v
    if emit is not None:
        p.inputs["Emission Color"].default_value = (*emit[:3], 1)
        p.inputs["Emission Strength"].default_value = emit_strength
    nt.t.links.new(p.outputs[0], out.inputs[0])
    m["p"] = p.name
    return m


def emit_mat(name, color, strength=5.0):
    m, nt, out = new_mat(name)
    e = nt.n("ShaderNodeEmission")
    e.inputs[0].default_value = (*color[:3], 1)
    e.inputs[1].default_value = strength
    nt.t.links.new(e.outputs[0], out.inputs[0])
    return m


def box(name, size, loc=(0, 0, 0), mat=None, bevel=0.0, segs=3, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width, b.segments = bevel, segs
        try:
            b.harden_normals = True
        except Exception:
            pass
    bpy.ops.object.shade_smooth()
    try:
        o.data.use_auto_smooth = True
    except Exception:
        pass
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
    except Exception:
        pass
    if mat:
        o.data.materials.append(mat)
    return o


def cyl(name, r, h, loc=(0, 0, 0), mat=None, verts=48, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    bpy.ops.object.shade_smooth()
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
    except Exception:
        pass
    if mat:
        o.data.materials.append(mat)
    return o


def camera(scene, lens=50, dof=None, fstop=2.0):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start, cd.clip_end = 0.01, 500
    cam = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    if dof is not None:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        if isinstance(dof, bpy.types.Object):
            cd.dof.focus_object = dof
        else:
            cd.dof.focus_distance = dof
    return cam


def look_at(cam, pos, target, roll=0.0):
    cam.location = pos
    d = Vector(target) - Vector(pos)
    q = d.to_track_quat("-Z", "Y")
    cam.rotation_euler = q.to_euler()
    cam.rotation_euler.rotate_axis("Z", roll)


def cam_path(cam, nf, pos_fn, tgt_fn, roll_fn=None):
    for f in range(1, nf + 1):
        t = (f - 1) / max(1, nf - 1)
        look_at(cam, pos_fn(t), tgt_fn(t), roll_fn(t) if roll_fn else 0.0)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)


def light(scene, kind, loc, energy, color=(1, 1, 1), size=1.0, target=(0, 0, 0), name="light", spot=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy, ld.color = energy, color
    if kind == "AREA":
        ld.size = size
    elif kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    if kind == "SPOT" and spot:
        ld.spot_size, ld.spot_blend = math.radians(spot), 0.5
    o = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(o)
    look_at(o, loc, target)
    return o


def save(scene, blend):
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("SAVED", blend)
