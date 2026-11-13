"""blender -b -P render_robot.py -- <out_dir>: the real Vi3W robot.glb rendered RGBA in 3 lighting/angle variants to
composite over the Roblox plates (night_low = reveal, night_kick = punt follow-through, day = ending)."""
import bpy, math, os, sys
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out, exist_ok=True)
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vi3w-outro", "assets", "robot.glb")

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = 900, 1350
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"

bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in sc.objects if o.type == "MESH"]
root = bpy.data.objects.new("RobotRoot", None); sc.collection.objects.link(root)
for o in sc.objects:
    if o.parent is None and o is not root:
        o.parent = root
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
h = mx.z - mn.z
s = 2.0 / h
root.scale = (s, s, s)
root.location = (-(mn.x + mx.x) / 2 * s, -(mn.y + mx.y) / 2 * s, -mn.z * s)
bpy.context.view_layer.update()

world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 35


def light(name, kind, loc, rot, energy, color):
    d = bpy.data.lights.new(name, kind); d.energy = energy; d.color = color
    if kind == "AREA":
        d.size = 3
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    return o


def clear_lights():
    for o in [o for o in sc.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o)


def aim(cam, loc, target):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


VARIANTS = {
    # name: (robot yaw, robot tilt(x,y), cam loc, cam target, lights, world color, strength)
    "night_low": (-25, (0, 0), (1.2, -4.6, 0.25), (0, 0, 1.2),
                  [("Moon", "SUN", (0, 0, 5), (55, 0, 140), 1.6, (0.55, 0.62, 1.0)),
                   ("Warm", "AREA", (2.5, -2.5, 1.5), (70, 0, 45), 300, (1.0, 0.72, 0.5)),
                   ("Rim", "AREA", (-2, 2.5, 3), (-60, 0, 200), 400, (0.6, 0.7, 1.0))], (0.03, 0.04, 0.1), 0.6),
    "night_kick": (-40, (0, -18), (0.8, -4.4, 0.6), (0, 0, 1.1),
                   [("Moon", "SUN", (0, 0, 5), (55, 0, 140), 1.6, (0.55, 0.62, 1.0)),
                    ("Warm", "AREA", (2.5, -2.5, 1.5), (70, 0, 45), 300, (1.0, 0.72, 0.5)),
                    ("Rim", "AREA", (-2, 2.5, 3), (-60, 0, 200), 400, (0.6, 0.7, 1.0))], (0.03, 0.04, 0.1), 0.6),
    "day": (-15, (0, 0), (0.6, -4.8, 1.0), (0, 0, 1.0),
            [("Sun", "SUN", (0, 0, 5), (50, 0, 30), 4.0, (1.0, 0.95, 0.85)),
             ("Fill", "AREA", (-3, -3, 2), (70, 0, -45), 250, (0.8, 0.9, 1.0))], (0.55, 0.7, 0.95), 1.0),
}
for name, (yaw, tilt, cl, ct, lights, wcol, wstr) in VARIANTS.items():
    clear_lights()
    for L in lights:
        light(*L)
    bg.inputs[0].default_value = (*wcol, 1); bg.inputs[1].default_value = wstr
    root.rotation_euler = (math.radians(tilt[0]), math.radians(tilt[1]), math.radians(yaw))
    aim(cam, cl, ct)
    sc.render.filepath = os.path.join(out, f"robot_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)
