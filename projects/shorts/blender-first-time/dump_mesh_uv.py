"""blender -b -P dump_mesh_uv.py -- in.glb out_dir [maxtris=57000 → split into 3 Roblox parts] [tex=1024]  then:  python3 tex_pad.py out_dir [tex]
Roblox-ready export of a Vi3W GLB for an EditableMesh rebuild (no asset upload needed for the mesh):
  out_dir/robot_uv.json  {v:[x,y,z..], uv:[u,v..], n:[x,y,z..], f:[vi,ti,ni, vi,ti,ni, vi,ti,ni, ...]}
  out_dir/robot_tex.png  base colour, tex x tex (Roblox's max is 1024), UV islands dilated so mip/seams never pull in black
Roblox space: Y-up, -Z front, height 1.0, feet at 0, centred in X/Z. UVs are Roblox-style (origin top-left).

Why (v1 dump_mesh.py looked bad in-game): it baked the 4K texture into ~13k vertex colours (eyes/smile lost,
seam texels smeared black) and gamma-encoded already-sRGB pixels a second time (blue washed to grey)."""
import bpy, sys, json, os
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], a[1]
maxt = int(a[2]) if len(a) > 2 else 57000
TEX = int(a[3]) if len(a) > 3 else 1024
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in ms: o.select_set(True)
bpy.context.view_layer.objects.active = ms[0]
if len(ms) > 1: bpy.ops.object.join()
o = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# glTF "doubleSided" hides inward-wound faces in Blender/three.js; Roblox culls back faces, so they vanish (v1: pupils).
# Make every face point outward. FLIP_ALL=1 env → also add a reversed copy of each face (true double-sided, 2x tris).
import bmesh
bm = bmesh.new(); bm.from_mesh(o.data)
nflip = 0
before = [f.normal.copy() for f in bm.faces]
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
nflip = sum(1 for f, n0 in zip(bm.faces, before) if f.normal.dot(n0) < 0)
bm.to_mesh(o.data); bm.free()
print("recalc normals: flipped", nflip, "faces")
tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
if tris > maxt:
    m = o.modifiers.new("d", "DECIMATE"); m.ratio = maxt / tris
    m.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="d")
# smooth shading everywhere (auto-smooth by angle keeps hard edges on the boxy parts)
bpy.ops.object.shade_auto_smooth(angle=0.7) if hasattr(bpy.ops.object, "shade_auto_smooth") else bpy.ops.object.shade_smooth()
for mod in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
me = o.data
me.calc_loop_triangles()

# ---- base-colour texture -------------------------------------------------------------------------------
img = None
for mat in me.materials:
    if mat and mat.use_nodes:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf and bsdf.inputs["Base Color"].links:
            nd = bsdf.inputs["Base Color"].links[0].from_node
            if nd.type == "TEX_IMAGE": img = nd.image
        if img is None:
            img = next((n.image for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
    if img: break
assert img, "no base colour texture"
W, H = img.size
# img.pixels are the stored (sRGB) values for 8-bit images - NO extra gamma (that was the v1 grey bug)
px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1]          # flip to top-left origin
uv = me.uv_layers.active.data

# raw texture (top-left origin) + per-triangle UVs go to tex_pad.py (system python: PIL) for gutter dilation + resize
np.save(os.path.join(out, "_tex_src.npy"), (np.clip(px[..., :3], 0, 1) * 255).astype(np.uint8))
json.dump([[round(c, 5) for l in t.loops for c in (uv[l].uv[0] % 1, 1 - uv[l].uv[1] % 1)] for t in me.loop_triangles],
          open(os.path.join(out, "_tex_tris.json"), "w"))

# ---- geometry ------------------------------------------------------------------------------------------
vs = [o.matrix_world @ v.co for v in me.vertices]
mn = Vector([min(p[i] for p in vs) for i in range(3)]); mx = Vector([max(p[i] for p in vs) for i in range(3)])
h = mx.z - mn.z; cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
# Blender Z-up → Roblox Y-up; glTF front (-Y in Blender) → Roblox -Z front
V = []
for p in vs: V += [round((p.x - cx) / h, 5), round((p.z - mn.z) / h, 5), round((p.y - cy) / h, 5)]
cn = me.corner_normals if hasattr(me, "corner_normals") else None
uvi, ni, UV, N, F = {}, {}, [], [], []
for t in me.loop_triangles:
    for l in t.loops:
        u_, v_ = uv[l].uv
        ku = (round(u_, 5), round(1 - v_, 5))
        if ku not in uvi: uvi[ku] = len(UV) // 2; UV += ku
        nn = cn[l].vector if cn else me.loops[l].normal
        kn = (round(nn.x, 3), round(nn.z, 3), round(nn.y, 3))
        if kn not in ni: ni[kn] = len(N) // 3; N += kn
        F += [me.loops[l].vertex_index, uvi[ku], ni[kn]]
json.dump({"v": V, "uv": UV, "n": N, "f": F}, open(os.path.join(out, "robot_uv.json"), "w"), separators=(",", ":"))
print("verts", len(vs), "uvs", len(UV) // 2, "normals", len(N) // 3, "tris", len(F) // 9, "tex", W, H, "->", TEX)
