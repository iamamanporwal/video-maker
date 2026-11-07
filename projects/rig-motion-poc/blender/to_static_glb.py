"""Any GLB/FBX/OBJ -> one static (unrigged) GLB mesh in bind pose, for SkinTokens.

    Blender -b --factory-startup -P blender/to_static_glb.py -- IN OUT.glb
"""
import sys
from pathlib import Path

import bpy

src, dst = (Path(a) for a in sys.argv[sys.argv.index("--") + 1:][:2])
bpy.ops.wm.read_factory_settings(use_empty=True)
{".glb": lambda: bpy.ops.import_scene.gltf(filepath=str(src)),
 ".gltf": lambda: bpy.ops.import_scene.gltf(filepath=str(src)),
 ".fbx": lambda: bpy.ops.import_scene.fbx(filepath=str(src)),
 ".obj": lambda: bpy.ops.wm.obj_import(filepath=str(src))}[src.suffix.lower()]()
shapes = {pb.custom_shape for o in bpy.data.objects if o.type == "ARMATURE" for pb in o.pose.bones if pb.custom_shape}
for o in list(bpy.data.objects):
    if o.type == "MESH" and o not in shapes:
        for m in list(o.modifiers):
            if m.type == "ARMATURE":
                o.modifiers.remove(m)
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        o.vertex_groups.clear()
for o in list(bpy.data.objects):
    if o.type != "MESH" or o in shapes:
        bpy.data.objects.remove(o)
bpy.ops.export_scene.gltf(filepath=str(dst), export_format="GLB", export_animations=False, export_skins=False)
