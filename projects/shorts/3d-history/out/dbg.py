import bpy
from mathutils import Vector
for i, (sc, t, loc, at) in enumerate([("LAB", 0.3, (3, -6, 3), (0, 0, 0.6)), ("HAND", 17.5, (0.3, -1.0, 1.9), (0.2, 0, 1.9))]):
    s = bpy.data.scenes[sc]
    cd = bpy.data.cameras.new("dbg"); cd.lens = 24; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36
    c = bpy.data.objects.new("dbg", cd); s.collection.objects.link(c)
    c.location = loc; c.rotation_euler = (Vector(at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    s.timeline_markers.clear(); s.camera = c; s.frame_set(int(t * 30) + 1)
    s.render.resolution_percentage = 50
    s.render.filepath = f"//dbg_{i}.jpg"
    bpy.ops.render.render(write_still=True, scene=sc)
    if sc == "LAB":
        for o in s.objects:
            if o.type == "MESH" and not o.hide_render and o.visible_get():
                pass
        big = [(o.name, [round(x, 1) for x in o.dimensions]) for o in s.objects if o.type == "MESH" and max(o.dimensions) > 3]
        print("BIG", big)
