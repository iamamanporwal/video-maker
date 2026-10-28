"""blender -b -P clean.py -- <in.glb> <out.glb>: weld UV seams, delete the loose parts past the tail tip, export GLB.

Past the tail (x < -0.4) Vi3W rebuilt the playground pole that occluded it in the source frame, plus a hollow,
detached fragment of the tail fin. Both are loose parts, so they come off without cutting the body.
"""
import sys, bpy, bmesh

src, dst = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bm = bmesh.new(); bm.from_mesh(o.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.verts.ensure_lookup_table()

seen, islands = set(), []
for v in bm.verts:
    if v.index in seen:
        continue
    stack, isl = [v], []
    seen.add(v.index)
    while stack:
        a = stack.pop(); isl.append(a)
        for e in a.link_edges:
            b = e.other_vert(a)
            if b.index not in seen:
                seen.add(b.index); stack.append(b)
    islands.append(isl)

mw = o.matrix_world
poses = [[mw @ v.co for v in i] for i in islands]
junk = [i for i, p in zip(islands, poses) if max(c.x for c in p) < -0.4]
assert len(junk) == 2, f"expected pole + fin fragment past the tail, found {len(junk)}"
print(f"REMOVING {[len(i) for i in junk]} verts of {len(bm.verts)}")
bmesh.ops.delete(bm, geom=[v for i in junk for v in i], context="VERTS")
bm.to_mesh(o.data); bm.free()
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_apply=True)
