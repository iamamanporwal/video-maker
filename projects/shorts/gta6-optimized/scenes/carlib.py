"""Real hatchback (sneeze-eyes/assets/car.glb, 35k tris) → one joined mesh, normalised: +Y = front, z up, wheels on z=0, length 4.2 m.
load_car(ratio) decimates (collapse) so the same car doubles as the LOD0..LOD3 chain."""
import bpy, os, math
from mathutils import Vector
from common import ROOT

CAR = os.path.join(ROOT, "projects", "shorts", "sneeze-eyes", "assets", "car.glb")
LEN = 4.2


def tris(o):
    me = o.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def load_car(ratio=1.0, name="car", flip=True, keep_shadow=False):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=CAR)
    new = [o for o in bpy.data.objects if o not in before]
    bpy.ops.object.select_all(action="DESELECT")
    meshes = [o for o in new if o.type == "MESH" and (keep_shadow or "shadow" not in (o.data.materials[0].name if o.data.materials else ""))]
    for o in new:
        if o not in meshes and o.type == "MESH":
            bpy.data.objects.remove(o)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    car = bpy.context.object
    car.name = name
    for o in list(bpy.data.objects):
        if o.type == "EMPTY" and o not in before:
            bpy.data.objects.remove(o)
    # normalise orientation: long horizontal axis → Y
    bb = [car.matrix_world @ Vector(c) for c in car.bound_box]
    dx = max(v.x for v in bb) - min(v.x for v in bb)
    dy = max(v.y for v in bb) - min(v.y for v in bb)
    if dx > dy:
        car.data.transform(__import__("mathutils").Matrix.Rotation(math.radians(90), 4, "Z"))
    if flip:
        car.data.transform(__import__("mathutils").Matrix.Rotation(math.radians(180), 4, "Z"))
    car.matrix_world.identity()
    vs = [v.co for v in car.data.vertices]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    k = LEN / (mx.y - mn.y)
    car.data.transform(__import__("mathutils").Matrix.Translation(Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z))))
    car.data.transform(__import__("mathutils").Matrix.Scale(k, 4))
    if ratio < 0.999:
        m = car.modifiers.new("lod", "DECIMATE")
        m.decimate_type, m.ratio = "COLLAPSE", ratio
        bpy.context.view_layer.objects.active = car
        bpy.ops.object.modifier_apply(modifier="lod")
    bpy.ops.object.shade_smooth()
    return car
