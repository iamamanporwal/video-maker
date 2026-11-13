"""blender -b -P dump_mesh.py -- in.glb out.json maxtris: Vi3W GLB -> {v:[x,y,z..], c:[hex per vertex], f:[i,j,k..]}
(Y-up, height 1.0, feet at 0) for rebuilding inside Roblox with EditableMesh; texture baked to vertex colours."""
import bpy, bmesh, sys, json
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
src, dst, maxt = a[0], a[1], int(a[2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in ms: o.select_set(True)
bpy.context.view_layer.objects.active = ms[0]
if len(ms) > 1: bpy.ops.object.join()
o = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
if tris > maxt:
    m = o.modifiers.new("d", "DECIMATE"); m.ratio = maxt / tris
    bpy.ops.object.modifier_apply(modifier="d")
me = o.data
me.calc_loop_triangles()
# texture lookup
img = None
for mat in me.materials:
    if mat and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image: img = n.image; break
px = list(img.pixels) if img else None
W, H = (img.size if img else (0, 0))
uv = me.uv_layers.active.data if me.uv_layers.active else None
acc = [[0, 0, 0, 0] for _ in me.vertices]
if px and uv:
    for li, loop in enumerate(me.loops):
        u, v = uv[li].uv
        x = min(W - 1, max(0, int((u % 1) * W))); y = min(H - 1, max(0, int((v % 1) * H)))
        i = (y * W + x) * 4
        a_ = acc[loop.vertex_index]; a_[0] += px[i]; a_[1] += px[i+1]; a_[2] += px[i+2]; a_[3] += 1
vs = [o.matrix_world @ v.co for v in me.vertices]
mn = Vector([min(p[i] for p in vs) for i in range(3)]); mx = Vector([max(p[i] for p in vs) for i in range(3)])
h = mx.z - mn.z; cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
def lin2srgb(c): return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
out_v, out_c = [], []
for p, a_ in zip(vs, acc):
    # Blender Z-up -> Roblox Y-up; glTF front (-Y in Blender) -> Roblox -Z front
    out_v += [round((p.x - cx) / h, 4), round((p.z - mn.z) / h, 4), round((p.y - cy) / h, 4)]
    n = max(1, a_[3]); rgb = [int(max(0, min(1, lin2srgb(a_[k] / n))) * 255) for k in range(3)]
    out_c.append("%02x%02x%02x" % tuple(rgb))
out_f = [i for t in me.loop_triangles for i in t.vertices]
json.dump({"v": out_v, "c": out_c, "f": out_f}, open(dst, "w"), separators=(",", ":"))
print("verts", len(vs), "tris", len(out_f) // 3, "tex", W, H)
