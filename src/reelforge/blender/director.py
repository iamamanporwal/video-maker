"""Shared toolkit for 3D-director shorts (Zack D. Films style): runs inside Blender.

A shot script does `sys.path.insert(0, <this dir>); import director as D`, builds its scene with these helpers,
then saves a .blend. Rendering happens outside Blender through `render.py`, which splits the frame range over
several background Blender processes.

Rig approach: any Mixamo-standard skeleton (Sketchfab / Mixamo / Vi3W auto-rig exports all map to it). Bodies
are posed by world directions (`aim`) instead of raw bone angles, so one pose call works on any Mixamo rig no
matter how its bones are rolled. Hands that touch props use 2-bone IK whose target is parented to the prop, so
the prop is the animated hero and the arm follows it.
"""
import math
import bpy
from mathutils import Euler, Quaternion, Vector

FPS = 30


def T(sec):
    """Seconds → frame (frame 1 is t=0)."""
    return int(round(sec * FPS)) + 1


# ---------------------------------------------------------------- scene / render

def reset(w=1080, h=1920, frames=300, fps=FPS):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = w, h, 100
    s.render.fps, s.frame_start, s.frame_end = fps, 1, frames
    return s


def fast_eevee(s, samples=16, motion_blur=True, look="AgX - Medium High Contrast", raytrace=False):
    """EEVEE tuned for speed: few samples, no ray tracing, cheap shadows, one-step motion blur, JPEG frames."""
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    s.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    e = s.eevee
    e.taa_render_samples = samples
    for k, v in (("use_raytracing", False), ("use_shadows", True), ("shadow_ray_count", 1),
                 ("shadow_step_count", 4), ("use_volumetric_shadows", False), ("motion_blur_steps", 1),
                 ("shadow_resolution_scale", 0.5), ("fast_gi_resolution", "4"), ("use_fast_gi", True)):
        if hasattr(e, k):
            try:
                setattr(e, k, v)
            except Exception:
                pass
    s.render.use_motion_blur = motion_blur
    if hasattr(s.render, "motion_blur_shutter"):
        s.render.motion_blur_shutter = 0.35
    s.render.film_transparent = False
    s.render.use_persistent_data = True
    s.view_settings.view_transform = "AgX"
    try:
        s.view_settings.look = look
    except TypeError:
        pass
    # anti-flicker: a full shadow pool drops shadow tiles frame to frame; wider pixel filter calms thin-detail shimmer
    if hasattr(e, "shadow_pool_size"):
        e.shadow_pool_size = "1024"
    s.render.filter_size = 1.8
    if raytrace:                                   # screen-space reflections/GI: contact reflections on glossy floors
        e.use_raytracing, e.ray_tracing_method = True, "SCREEN"
    im = s.render.image_settings
    im.file_format, im.quality = "JPEG", 94


def world(s, rgb, strength=1.0):
    w = bpy.data.worlds.new("world")
    w.use_nodes = True
    s.world = w
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*rgb, 1)
    bg.inputs[1].default_value = strength
    return w


def hex_lin(h):
    """'#rrggbb' → linear RGB tuple (what Blender colour sockets expect)."""
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


TARGET = None          # collection new objects go into (look.building() points it at a set's scene)


def link(o, coll=None):
    (coll or TARGET or bpy.context.scene.collection).objects.link(o)
    return o


def adopt(o):
    """Move an operator-created object (it lands in the context scene) into TARGET."""
    if TARGET is None or o.name in TARGET.objects:
        return o
    for c in list(o.users_collection):
        c.objects.unlink(o)
    TARGET.objects.link(o)
    return o


def _prim(op, name, m=None, smooth_=True, **kw):
    op(**kw)
    o = bpy.context.active_object
    o.name = name
    if smooth_:
        smooth(o)
    if m:
        give(o, m)
    return adopt(o)


def sphere(name, r, loc, m=None, seg=40, rings=20):
    return _prim(bpy.ops.mesh.primitive_uv_sphere_add, name, m, radius=r, location=loc, segments=seg, ring_count=rings)


def ico(name, r, loc, m=None, sub=3):
    return _prim(bpy.ops.mesh.primitive_ico_sphere_add, name, m, radius=r, location=loc, subdivisions=sub)


def cone(name, r, depth, loc, m=None, verts=32):
    return _prim(bpy.ops.mesh.primitive_cone_add, name, m, radius1=r, depth=depth, location=loc, vertices=verts)


def torus(name, R, r, loc, rot=(0, 0, 0), m=None):
    return _prim(bpy.ops.mesh.primitive_torus_add, name, m, major_radius=R, minor_radius=r, location=loc, rotation=rot)


def empty(name, loc=(0, 0, 0), parent=None, size=0.05):
    o = link(bpy.data.objects.new(name, None))
    o.empty_display_size = size
    o.parent = parent
    o.location = loc
    return o


def area_light(name, power, loc, target, size=2.0, rgb=(1, 1, 1)):
    l = link(bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")))
    l.data.energy, l.data.size, l.data.color = power, size, rgb
    l.location = loc
    l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return l


def sun(name, strength, direction, rgb=(1, 1, 1), angle=8.0):
    l = link(bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN")))
    l.data.energy, l.data.color, l.data.angle = strength, rgb, math.radians(angle)
    l.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return l


def mat(name, rgb, rough=0.5, metal=0.0, emit=None, emit_strength=1.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m


def give(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def smooth(o, bevel=None, segments=3):
    for p in o.data.polygons:
        p.use_smooth = True
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width, b.segments = bevel, segments
        b.limit_method = "ANGLE"
    return o


def box(name, size, loc, m=None, bevel=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # keep the origin where it was put
    if bevel:
        smooth(o, bevel)
    if m:
        give(o, m)
    return adopt(o)


def cyl(name, r, depth, loc, rot=(0, 0, 0), m=None, verts=24):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    for p in o.data.polygons:                      # smooth sides, flat caps (smooth caps read as a ball)
        p.use_smooth = abs(p.normal.z) < 0.5
    if m:
        give(o, m)
    return adopt(o)


def cyclorama(m, width=30, depth=30, height=12, radius=3.0, y_wall=6.0):
    """Seamless floor-to-wall backdrop (the curved studio sweep), wall behind +Y."""
    import bmesh
    me = bpy.data.meshes.new("cyc")
    bm = bmesh.new()
    prof = [(-depth, 0.0)]
    for i in range(13):                                # quarter circle from floor (z=0) up into the wall (y=y_wall)
        t = i * (math.pi / 2) / 12
        prof.append((y_wall - radius + radius * math.sin(t), radius - radius * math.cos(t)))
    prof.append((y_wall, height))
    rows = []
    for x in (-width / 2, width / 2):
        rows.append([bm.verts.new((x, y, z)) for y, z in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    bm.to_mesh(me)
    o = link(bpy.data.objects.new("cyc", me))
    smooth(o)
    return give(o, m)


# ---------------------------------------------------------------- characters

def import_char(path, name, keep_meshes=None):
    """Import a rigged glTF, drop its animation and stray objects. Returns (root, armature, meshes).

    The root empty is what you place/scale/flatten; the armature sits under it at rest pose. The file's own clips
    stay available as `arm["clips"]` (name → action) for `play()`."""
    before, acts = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        adopt(o)
    clips = {a.name.split(".")[0]: a for a in bpy.data.actions if a not in acts}
    arm = next(o for o in new if o.type == "ARMATURE")
    meshes = [o for o in new if o.type == "MESH" and o.parent == arm]
    for o in new:
        if o is not arm and o not in meshes and o.type != "EMPTY":
            bpy.data.objects.remove(o)
    if arm.animation_data:
        arm.animation_data.action = None
        for tr in list(arm.animation_data.nla_tracks):      # importer stashes clips as muted tracks
            arm.animation_data.nla_tracks.remove(tr)
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    root = empty(name)
    arm.parent = root
    arm.name = name + "_rig"
    for m in meshes:
        m.name = name + "_body"
    CLIPS[arm.name] = clips
    bpy.context.view_layer.update()
    return root, arm, meshes


CLIPS = {}


def play(arm, clip, f0, f1, speed=1.0, blend=4):
    """Stock clip (walk/idle/...) on the rig from f0 to f1 as an NLA strip, looped to fill, eased in/out."""
    act = CLIPS[arm.name][clip]
    ad = arm.animation_data or arm.animation_data_create()
    tr = ad.nla_tracks.new()
    tr.name = f"{clip}_{f0}"
    st = tr.strips.new(tr.name, int(f0), act)
    a0, a1 = act.frame_range
    reps = (f1 - f0) / (max(a1 - a0, 1) / speed)
    if reps > 200:                                 # single-frame poses (sad_pose...): widen the action range; the
        st.action_frame_end = a0 + (f1 - f0)       # pose holds past its last key (repeat/scale both cap at 1000)
        st.repeat, st.scale = 1.0, 1.0
        st.frame_end = f1
    else:
        st.scale, st.repeat = 1.0 / speed, max(0.01, reps)
    st.blend_in = st.blend_out = blend
    st.extrapolation = "NOTHING"
    return st


def bake(arm, meshes, name):
    """Freeze the rig's current pose into one static mesh (world space at the root's transform) for cheap crowds."""
    dg = bpy.context.evaluated_depsgraph_get()
    parts = []
    for m in meshes:
        me = bpy.data.meshes.new_from_object(m.evaluated_get(dg))
        me.transform(m.matrix_world)
        parts.append(me)
    import bmesh
    bm = bmesh.new()
    for me in parts:
        bm.from_mesh(me)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    out.materials.clear()
    for p in out.polygons:
        p.use_smooth = True
    return out


def tint_mat(name, tex_from=None, rough=0.6, lo=0.45):
    """Material coloured by each object's `color` (keyable per instance). If `tex_from` (a material with an image
    texture) is given, that texture's brightness is kept as shading detail under the tint."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    info = nt.nodes.new("ShaderNodeObjectInfo")
    col = info.outputs["Color"]
    img = next((n.image for n in tex_from.node_tree.nodes if n.type == "TEX_IMAGE"), None) if tex_from else None
    if img:
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = img
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(tx.outputs["Color"], bw.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = lo
        nt.links.new(bw.outputs[0], mr.inputs["Value"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        nt.links.new(col, mul.inputs[6])
        nt.links.new(mr.outputs[0], mul.inputs[7])
        col = mul.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    return m


def room(name, center, size, m):
    """Closed box seen from inside (dark 'inner-body' / night sets). Blocks the global sun."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")
    return adopt(give(o, m))


def swap(objs_at, hide_before=True):
    """Show one object at a time: objs_at = [(obj, from_frame), ...] in order (counters, changing labels)."""
    for i, (o, f) in enumerate(objs_at):
        nxt = objs_at[i + 1][1] if i + 1 < len(objs_at) else None
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=1)
        o.hide_render = False
        o.keyframe_insert("hide_render", frame=f)
        if nxt:
            o.hide_render = True
            o.keyframe_insert("hide_render", frame=nxt)


def bone(arm, n):
    pb = arm.pose.bones.get(n) or arm.pose.bones.get("mixamorig:" + n)
    if pb is None:
        raise KeyError(n)
    return pb


def bone_world(arm, n, tail=False):
    pb = bone(arm, n)
    return arm.matrix_world @ (pb.tail if tail else pb.head)


def aim(arm, n, world_dir, frame=None, twist=0.0):
    """Point bone `n` along `world_dir` (keeps the rest of the chain). Key it at `frame` if given."""
    pb = bone(arm, n)
    bpy.context.view_layer.update()
    mw3 = arm.matrix_world.to_3x3()
    d = (mw3.inverted() @ Vector(world_dir)).normalized()
    cur = pb.matrix.copy()
    y = cur.to_3x3().col[1].normalized()
    r = y.rotation_difference(d).to_matrix() @ cur.to_3x3()
    if twist:
        r = Quaternion(d, math.radians(twist)).to_matrix() @ r
    m = r.to_4x4()
    m.translation = cur.translation
    pb.matrix = m
    bpy.context.view_layer.update()
    if frame is not None:
        pb.keyframe_insert("rotation_quaternion", frame=frame)


def pose(arm, frame, dirs, twists=None):
    """dirs: ordered {bone: world_dir}; parents before children. Keys every listed bone at `frame`."""
    bpy.context.scene.frame_set(frame)
    for n, d in dirs.items():
        aim(arm, n, d, frame, (twists or {}).get(n, 0.0))


def key_rot(arm, n, frame, axis="X", deg=0.0):
    pb = bone(arm, n)
    pb.rotation_quaternion = Quaternion(Vector({"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis]),
                                        math.radians(deg))
    pb.keyframe_insert("rotation_quaternion", frame=frame)


FINGERS = ("Index", "Middle", "Ring", "Pinky")


def curl(arm, side, frame, amount, axis="X", thumb=0.5):
    """Close a hand: amount 0 = open, 1 = fist. Keys all finger joints."""
    for f in FINGERS:
        for j, w in ((1, 55), (2, 75), (3, 55)):
            key_rot(arm, f"{side}Hand{f}{j}", frame, axis, w * amount)
    for j, w in ((1, 15), (2, 25), (3, 25)):
        key_rot(arm, f"{side}HandThumb{j}", frame, axis, w * amount * thumb)


def ik_arm(arm, side, target, pole=None, pole_angle=-90.0, influence=1.0):
    """2-bone IK on <side>ForeArm → target object. Returns the constraint (key its influence to blend)."""
    c = bone(arm, f"{side}ForeArm").constraints.new("IK")
    c.target, c.chain_count, c.influence = target, 2, influence
    if pole:
        c.pole_target, c.pole_angle = pole, math.radians(pole_angle)
    return c


def track(arm, n, target, axis="TRACK_Y", influence=1.0):
    c = bone(arm, n).constraints.new("DAMPED_TRACK")
    c.target, c.track_axis, c.influence = target, axis, influence
    return c


# ---------------------------------------------------------------- animation

def key(o, path, frame, value=None, interp=None):
    if value is not None:
        setattr(o, path, value)
    o.keyframe_insert(path, frame=frame)
    if interp:
        ease_last(o, interp)


def ease_all(o, interp="BEZIER", easing="EASE_IN_OUT"):
    ad = o.animation_data
    if not (ad and ad.action):
        return
    for fc in _fcurves(ad.action):
        for k in fc.keyframe_points:
            k.interpolation, k.easing = interp, easing
            k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"


def ease_last(o, interp):
    for fc in _fcurves(o.animation_data.action):
        fc.keyframe_points[-1].interpolation = interp


def _fcurves(action):
    """Blender 5 keeps F-curves in layered channelbags; older builds expose action.fcurves."""
    if hasattr(action, "fcurves") and len(action.fcurves):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


def overshoot(o, path, f0, f1, v0, v1, amount=1.12):
    """Pop: v0 → v1*amount → v1 (scales, reveals)."""
    mid = tuple(a * amount for a in v1) if isinstance(v1, (tuple, list, Vector)) else v1 * amount
    key(o, path, f0, v0)
    key(o, path, f0 + int((f1 - f0) * 0.65), mid)
    key(o, path, f1, v1)


def handheld(o, strength=0.008, scale=45.0, seed=0):
    """Subtle drift on an already-animated location (cameras/look targets): noise modifiers on F-curves."""
    if not (o.animation_data and o.animation_data.action):
        key(o, "location", 1)
    for i, fc in enumerate(c for c in _fcurves(o.animation_data.action) if c.data_path == "location"):
        n = fc.modifiers.new("NOISE")
        n.strength, n.scale, n.phase = strength, scale, seed * 13 + i * 7


# ---------------------------------------------------------------- cameras

def camera(name, lens=30.0, dof=None):
    c = link(bpy.data.objects.new(name, bpy.data.cameras.new(name)))
    c.data.lens, c.data.sensor_fit = lens, "VERTICAL"
    c.data.sensor_height = 36.0                    # 9:16 frame: lens maps to the tall side like a rotated full-frame
    look = empty(name + "_look")
    t = c.constraints.new("TRACK_TO")
    t.target, t.track_axis, t.up_axis = look, "TRACK_NEGATIVE_Z", "UP_Y"
    if dof:
        c.data.dof.use_dof, c.data.dof.focus_object, c.data.dof.aperture_fstop = True, look, dof
    return c, look


def move(cam, look, f0, f1, loc0, loc1, at0, at1, lens0=None, lens1=None):
    """Eased dolly: camera loc0→loc1 while its look target goes at0→at1 (and lens zoom if given)."""
    for o, a, b in ((cam, loc0, loc1), (look, at0, at1)):
        key(o, "location", f0, Vector(a))
        key(o, "location", f1, Vector(b))
        ease_all(o)
    if lens0:
        cam.data.lens = lens0
        cam.data.keyframe_insert("lens", frame=f0)
        cam.data.lens = lens1 or lens0
        cam.data.keyframe_insert("lens", frame=f1)


def cut(s, frame, cam):
    """Hard cut to `cam` at `frame` (timeline marker bound to the camera)."""
    m = s.timeline_markers.new(cam.name, frame=frame)
    m.camera = cam
    if frame <= s.frame_start:
        s.camera = cam


# ---------------------------------------------------------------- graphics

def text3d(name, body, size, loc, m, extrude=0.03, bevel=0.006, font=None, rot=(math.pi / 2, 0, 0)):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body, cu.size, cu.extrude, cu.bevel_depth, cu.bevel_resolution = body, size, extrude, bevel, 2
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    if font:
        cu.font = bpy.data.fonts.load(font)
    o = link(bpy.data.objects.new(name, cu))
    o.location, o.rotation_euler = loc, rot
    o.data.materials.append(m)
    return o


def stroke(name, pts, m, width=0.004, cyclic=False):
    """Hand-drawn marker line through 3D points (doodles on a board)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", width, 2
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, xyz in zip(sp.points, pts):
        p.co = (*xyz, 1)
    sp.order_u, sp.use_endpoint_u, sp.use_cyclic_u = min(4, len(pts)), not cyclic, cyclic
    o = link(bpy.data.objects.new(name, cu))
    o.data.materials.append(m)
    return o
