import bpy, sys, math
from mathutils import Vector
views = [("ROAD", 31.0, (8, -6, 5), (1.5, 0, 0.6)), ("ROAD", 32.2, (5, -3, 3), None),
         ("CLINIC", 35.8, (11, -2.5, 3.0), (8, 0.4, 0.6)), ("PLAY", 13.6, (34, -6, 3), (30, 0, 0.6)),
         ("PLAY", 6.3, (6, -12, 4), (-1, 6, 2)), ("VOID", 9.3, (1.5, -2.5, 1.3), (0.1, 0, 1.0)),
         ("CLINIC", 18.5, (4.5, -3.5, 2.6), (0.2, 0, 1.0))]
for i, (sc, t, loc, at) in enumerate(views):
    s = bpy.data.scenes[sc]
    f = int(round(t * 30)) + 1
    if at is None:
        car = bpy.data.objects["car"]
        s.frame_set(f)
        at = car.matrix_world.translation
        loc = at + Vector(loc)
    cd = bpy.data.cameras.new("dbg"); cd.lens = 18; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36
    c = bpy.data.objects.new("dbg", cd); s.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    s.timeline_markers.clear(); s.camera = c
    s.frame_set(f)
    s.render.filepath = f"//dbg_{i}.png"
    bpy.ops.render.render(write_still=True, scene=sc)
