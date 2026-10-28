"""blender -b -P turntable.py -- <in.glb> <out_dir> [frames] [only_frame]: render a 360° turntable as PNGs
(1410x840, the reel's card aspect). Encode with ffmpeg; trim a copy from a later second for a CTA that should
open on a different angle.

Dark backdrop matching the reel's cards (#0d0f14), key + fill + blue rim light, Standard view transform so the
Vi3W texture keeps its colours. Frame 0 looks at the model's -Y side (glTF front). The camera distance is fitted
to the model's height and its widest spin, so tall and long models both fill the card. Geometry and materials
untouched.
"""
import math, sys, bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, out = args[:2]
frames = int(args[2]) if len(args) > 2 else 360
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
scn = bpy.context.scene

meshes = [o for o in scn.objects if o.type == "MESH"]
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
center, size = (lo + hi) / 2, max(hi - lo)

# Spin pivot at the model's centre.
pivot = bpy.data.objects.new("pivot", None); scn.collection.objects.link(pivot)
pivot.location = center
bpy.context.view_layer.update()   # so pivot.matrix_world is current before parenting
for o in scn.objects:
    if o.parent is None and o not in (pivot,):
        o.parent = pivot
        o.matrix_parent_inverse = pivot.matrix_world.inverted()

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.data.lens = 50
W, H = 1410, 840
d = Vector((0.12, -1, 0.32)).normalized()
ext = hi - lo
hfov = 2 * math.atan(cam.data.sensor_width / 2 / cam.data.lens)       # sensor fit is horizontal for a wide frame
vfov = 2 * math.atan(math.tan(hfov / 2) * H / W)
span = math.hypot(ext.x, ext.y)                                        # widest the model gets while spinning
dist = max(span / 2 / math.tan(hfov / 2), ext.z / 2 / math.tan(vfov / 2)) * 1.06 + span / 4
cam.location = center + d * dist
cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


def light(name, kind, energy, loc, color=(1, 1, 1), size_=1.0):
    l = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); scn.collection.objects.link(l)
    l.data.energy, l.data.color = energy, color
    if kind == "AREA":
        l.data.size = size_ * size
    l.location = center + Vector(loc) * size
    v = center - l.location
    l.rotation_euler = v.to_track_quat("-Z", "Y").to_euler()


light("key", "AREA", 90, (1.2, -1.6, 1.8), size_=1.2)
light("fill", "AREA", 18, (-1.8, -1.0, 0.6), (0.9, 0.95, 1), size_=1.5)
light("rim", "AREA", 45, (-0.6, 1.8, 1.2), (0.62, 0.83, 1), size_=1.0)

w = bpy.data.worlds.new("w"); w.use_nodes = True; scn.world = w
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.0040, 0.0048, 0.0070, 1)   # ≈ #0d0f14 in linear
bg.inputs[1].default_value = 1.0

engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
scn.view_settings.view_transform = "Standard"
scn.render.resolution_x, scn.render.resolution_y = W, H
scn.render.image_settings.file_format = "PNG"
only = int(args[3]) if len(args) > 3 else None     # render just this frame (look check)
for i in ([only] if only is not None else range(frames)):
    pivot.rotation_euler = (0, 0, 2 * math.pi * i / frames)
    scn.render.filepath = f"{out}/t_{i:04d}.png"
    bpy.ops.render.render(write_still=True)
