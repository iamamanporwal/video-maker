"""blender -b -P bake_ao.py -- in.glb out_dir [res=2048] [samples=64]: Cycles ambient-occlusion bake of the FULL-res GLB
onto its own UVs → out_dir/_ao.npy (top-left origin, 0..1). tex_pad.py multiplies it into the base colour.
Why: Roblox renders custom meshes with no AO, so concave detail the source relies on (eye sockets, panel seams,
joint gaps) reads flat. Decimation keeps the original UVs, so the bake lines up with the low-poly export."""
import bpy, sys, os
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], a[1]; R = int(a[2]) if len(a) > 2 else 2048; S = int(a[3]) if len(a) > 3 else 64
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in ms: o.select_set(True)
bpy.context.view_layer.objects.active = ms[0]
if len(ms) > 1: bpy.ops.object.join()
o = bpy.context.view_layer.objects.active
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = S
try:
    sc.cycles.device = "GPU"
    bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "METAL"
    bpy.context.preferences.addons["cycles"].preferences.get_devices()
    for d in bpy.context.preferences.addons["cycles"].preferences.devices: d.use = True
except Exception as e: print("gpu", e)
img = bpy.data.images.new("ao", R, R, float_buffer=True)
for mat in o.data.materials:
    nt = mat.node_tree; n = nt.nodes.new("ShaderNodeTexImage"); n.image = img
    for x in nt.nodes: x.select = False
    n.select = True; nt.nodes.active = n
sc.render.bake.margin = 8
bpy.ops.object.bake(type="AO")
ao = np.array(img.pixels[:], dtype=np.float32).reshape(R, R, 4)[::-1, :, 0]
np.save(os.path.join(out, "_ao.npy"), ao)
print("AO baked", R, "mean %.3f" % ao.mean())
