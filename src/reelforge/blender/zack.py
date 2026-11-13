"""Zack D. Films shot kit (runs inside Blender). Measured from "What If Bullets Were Made Of Ice?" (i5F2knwWn7w).

The look: one seamless coloured VOID (edge #66a6be) with a pale glow behind the subject, real-proportion
humans in colour-coded clothes, props as heroes, soft contact shadows, a new angle every 0.5-1.5 s.

    import zack as Z
    Z.void(scene)                          # world + floor that read as one infinite gradient
    Z.pop_in(obj, T(3.2))                  # evidence-style object pop on a word
    Z.whip(cam, look, T(5.0), (2,0,0))     # whip-pan exit into the next cut
    Z.cutaway(gun_body, plane_y=0.0)       # x-ray: slice a prop open to show its insides

Why the void glow is SCREEN-space (Window coords) and not a lamp: Zack's glow always sits behind the subject in
every angle, including top-down and floor-level shots. A screen-space gradient does that for free in every shot.
The floor mixes the same gradient as emission (so it melts into the background, no horizon) with a diffuse part
(so characters still drop contact shadows on it).
"""
import math
import bpy
from mathutils import Vector
import director as D

EDGE, CENTRE = "#66a6be", "#d6e6ea"        # measured corner colour; glow eyeballed from frames at 22-26 s


def _gradient(nt, edge, centre, size):
    """Radial gradient in screen space → colour socket. size ~0.55 = glow radius as a fraction of frame width."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    # aspect-correct distance from the frame centre, glow centre a bit above middle (subject chest height)
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "SUBTRACT"; mx.inputs[1].default_value = 0.5
    my = nt.nodes.new("ShaderNodeMath"); my.operation = "SUBTRACT"; my.inputs[1].default_value = 0.56
    nt.links.new(sep.outputs[0], mx.inputs[0]); nt.links.new(sep.outputs[1], my.inputs[0])
    sy = nt.nodes.new("ShaderNodeMath"); sy.operation = "MULTIPLY"; sy.inputs[1].default_value = 16 / 9
    nt.links.new(my.outputs[0], sy.inputs[0])
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(mx.outputs[0], cmb.inputs[0]); nt.links.new(sy.outputs[0], cmb.inputs[1])
    ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
    nt.links.new(cmb.outputs[0], ln.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.0, size
    mr.interpolation_type = "SMOOTHSTEP"
    nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*D.hex_lin(centre), 1)
    mix.inputs[7].default_value = (*D.hex_lin(edge), 1)
    nt.links.new(mr.outputs[0], mix.inputs[0])
    return mix.outputs[2]


def void(scene, edge=EDGE, centre=CENTRE, glow=0.55, floor_emit=0.72, ambient=0.6, key=True):
    """Infinite colour void + glow + shadow-receiving floor + soft studio light. Returns the floor object."""
    w = bpy.data.worlds.new(scene.name + "_void")
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    cam_bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(_gradient(nt, edge, centre, glow), cam_bg.inputs["Color"])
    amb = nt.nodes.new("ShaderNodeBackground")                       # what lights the scene: flat soft sky
    amb.inputs["Color"].default_value = (*D.hex_lin(centre), 1); amb.inputs["Strength"].default_value = ambient
    lp, mx = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0])
    nt.links.new(amb.outputs[0], mx.inputs[1]); nt.links.new(cam_bg.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    scene.world = w

    m = bpy.data.materials.new(scene.name + "_voidfloor")
    m.use_nodes = True
    mt = m.node_tree; mt.nodes.clear()
    o = mt.nodes.new("ShaderNodeOutputMaterial")
    col = _gradient(mt, edge, centre, glow)
    dif = mt.nodes.new("ShaderNodeBsdfDiffuse"); mt.links.new(col, dif.inputs["Color"])
    em = mt.nodes.new("ShaderNodeEmission"); mt.links.new(col, em.inputs["Color"])
    ms = mt.nodes.new("ShaderNodeMixShader"); ms.inputs[0].default_value = floor_emit
    mt.links.new(dif.outputs[0], ms.inputs[1]); mt.links.new(em.outputs[0], ms.inputs[2])
    mt.links.new(ms.outputs[0], o.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=400)
    floor = bpy.context.active_object; floor.name = scene.name + "_floor"
    D.adopt(floor); D.give(floor, m)
    if key:   # soft top-front key for soft contact shadows (Zack's shadows are soft and short)
        s = D.sun(scene.name + "_key", 2.2, (0.35, 0.55, -1.0), rgb=(1.0, 0.97, 0.93), angle=14.0)
        D.area_light(scene.name + "_fill", 400, (-4, -5, 4), (0, 0, 1), size=6, rgb=(0.9, 0.95, 1.0))
    return floor


def pop_in(o, frame, frames=7, amount=1.15, from_scale=0.0):
    """Object appears on a word: scale 0 → overshoot → 1 (Zack's evidence/props reveal)."""
    s1 = tuple(o.scale)
    D.overshoot(o, "scale", frame, frame + frames, tuple(v * from_scale for v in s1), s1, amount)
    return o


def drop_in(o, frame, height=1.2, frames=8):
    """Object falls into frame and settles with a tiny squash (bags, boxes, bodies)."""
    z = o.location.z
    D.key(o, "location", frame, Vector((o.location.x, o.location.y, z + height)))
    D.key(o, "location", frame + frames, Vector((o.location.x, o.location.y, z)))
    D.key(o, "scale", frame + frames, tuple(o.scale))
    D.key(o, "scale", frame + frames + 2, (o.scale.x * 1.08, o.scale.y * 1.08, o.scale.z * 0.88))
    D.key(o, "scale", frame + frames + 5, tuple(o.scale))


def whip(cam, look, frame, offset=(2.5, 0, 0), frames=5):
    """Whip-pan out: look target swings by `offset` over the last `frames` frames of a shot.
    Motion blur turns it into the streak Zack uses as a transition. Pair with a cut at frame+frames."""
    p = look.location.copy()
    D.key(look, "location", frame, p)
    D.key(look, "location", frame + frames, p + Vector(offset))
    D.ease_last(look, "QUAD")


def cutaway(o, axis="Y", at=0.0, keep="NEG"):
    """X-ray cross-section: boolean-slice `o` with a big box so its insides show (gun barrel, engine, body).
    Model the internals as separate objects; the slice face gets the object's material (make it slightly darker)."""
    import bmesh  # noqa: F401  (ensures mesh ops available in background)
    big = 50.0
    loc = [0.0, 0.0, 0.0]
    i = "XYZ".index(axis)
    loc[i] = at + (big / 2 if keep == "NEG" else -big / 2)
    bpy.ops.mesh.primitive_cube_add(size=big, location=loc)
    cutter = bpy.context.active_object; cutter.name = o.name + "_cutter"
    cutter.hide_render = cutter.hide_viewport = True
    mod = o.modifiers.new("cutaway", "BOOLEAN")
    mod.operation, mod.object, mod.solver = "DIFFERENCE", cutter, "EXACT"
    return cutter


def arrows(name, start, end, n=3, m=None, spread=0.05, frame=None):
    """Force/pressure arrows (Zack's red/blue pressure chevrons). Simple cone+cylinder per arrow."""
    m = m or D.mat(name + "_m", D.hex_lin("#ff4a5a"), rough=0.4, emit=D.hex_lin("#ff4a5a"), emit_strength=1.5)
    a, b = Vector(start), Vector(end)
    d = (b - a); L = d.length; dn = d.normalized()
    out = []
    for k in range(n):
        off = Vector((0, 0, (k - (n - 1) / 2) * spread))
        body = D.cyl(f"{name}{k}", L * 0.012, L * 0.7, a + off + dn * L * 0.35, m=m, verts=12)
        head = D.cone(f"{name}{k}h", L * 0.04, L * 0.3, a + off + dn * L * 0.85, m=m, verts=12)
        for p in (body, head):
            p.rotation_euler = dn.to_track_quat("Z", "Y").to_euler()
            out.append(p)
        if frame is not None:
            for p in (body, head):
                pop_in(p, frame + k * 2, frames=5)
    return out


# ---------------------------------------------------------------- post (ffmpeg, after render)

def rewind_filter(t0, t1, label=True):
    """ffmpeg filter fragment for Zack's 'REWIND' beat: the span [t0,t1] is replayed backwards, desaturated,
    with scanline wobble. Usage: build the rewind clip separately with
      ffmpeg -ss t0 -to t1 -i in.mp4 -vf "reverse,hue=s=0.1,eq=contrast=1.15,noise=alls=12:allf=t" rew.mp4
    then concat it. The 'REWIND ◀◀' label is a PIL card overlaid top-left like the captions."""
    return f"trim={t0}:{t1},setpts=PTS-STARTPTS,reverse,hue=s=0.1,eq=contrast=1.15,noise=alls=12:allf=t"
