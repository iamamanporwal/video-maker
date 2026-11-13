"""blender -b -P decimate_robot.py -- in.glb out.glb maxtris: decimate a Vi3W GLB for Roblox import (<20k tris, 1k texture)."""
import bpy, sys
a = sys.argv[sys.argv.index("--") + 1:]
src, dst, maxt = a[0], a[1], int(a[2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
tot = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ms)
print("tris before", tot)
for o in ms:
    mod = o.modifiers.new("d", "DECIMATE"); mod.ratio = min(1.0, maxt / tot)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.modifier_apply(modifier="d")
for img in bpy.data.images:
    if img.size[0] > 1024:
        img.scale(1024, 1024)
tot = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ms)
print("tris after", tot)
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_image_format="JPEG", export_jpeg_quality=88)
