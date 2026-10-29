"""blender -b -P morph.py -- <in.glb> <out_dir> <yaw_deg> <elev_deg> [spin_frames] [only]: renders for the
"screenshot lifts into 3D" transition, all RGBA on a transparent background (1600x1600, orthographic):

    aligned.png      shaded model seen from (yaw, elev), to sit on top of the frozen screenshot
    wire.png         the same view as a glowing accent wireframe (decimated copy), for the scan pass
    spin/s_####.png  the model turning 360° from that same view, so the spin starts where the still ends

yaw 0 looks at the glTF front (-Y); positive yaw orbits the camera counter-clockwise seen from above. Same lights
and Standard view transform as turntable.py. Geometry and materials of the model itself are untouched; the
wireframe is a separate decimated copy used only for the effect.
"""
import math, sys, bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, out, yaw, elev = args[0], args[1], math.radians(float(args[2])), math.radians(float(args[3]))
frames = int(args[4]) if len(args) > 4 else 150
only = args[5] if len(args) > 5 else None          # "still" = aligned + wire only
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
scn = bpy.context.scene
model = [o for o in scn.objects if o.type == "MESH"][0]

# Pivot at the mean vertex position: the body's centre of mass, not the bbox (a long tail would skew a bbox centre).
mw = model.matrix_world
pts = [mw @ v.co for v in model.data.vertices]
center = sum(pts, Vector()) / len(pts)
lo = Vector([min(p[k] for p in pts) for k in range(3)])
hi = Vector([max(p[k] for p in pts) for k in range(3)])
reach = max((p - center).length for p in pts)

pivot = bpy.data.objects.new("pivot", None); scn.collection.objects.link(pivot)
pivot.location = center
bpy.context.view_layer.update()
for o in list(scn.objects):
    if o.parent is None and o is not pivot:
        o.parent = pivot
        o.matrix_parent_inverse = pivot.matrix_world.inverted()

W = H = 1600
# Orthographic, sized to the farthest vertex from the pivot so every spin angle fits the same frame.
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = reach * 2.05
d = Vector((math.sin(yaw) * math.cos(elev), -math.cos(yaw) * math.cos(elev), math.sin(elev)))
cam.location = center + d * reach * 4
cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


def light(name, energy, loc, color=(1, 1, 1), size_=1.0):
    l = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")); scn.collection.objects.link(l)
    l.data.energy, l.data.color, l.data.size = energy, color, size_ * reach * 2
    l.location = center + Vector(loc) * reach * 2
    l.rotation_euler = (center - l.location).to_track_quat("-Z", "Y").to_euler()


light("key", 90, (1.2, -1.6, 1.8), size_=1.2)
light("fill", 25, (-1.8, -1.0, 0.6), (0.9, 0.95, 1), size_=1.5)
light("rim", 55, (-0.6, 1.8, 1.2), (0.62, 0.83, 1), size_=1.0)
w = bpy.data.worlds.new("w"); w.use_nodes = True; scn.world = w
w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6

engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
scn.view_settings.view_transform = "Standard"
scn.render.film_transparent = True
scn.render.resolution_x, scn.render.resolution_y = W, H
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_mode = "RGBA"


def shot(path):
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)


shot(f"{out}/aligned.png")

# Wireframe pass: decimated copy with a thin wireframe modifier and an emissive accent material.
wire = model.copy(); wire.data = model.data.copy(); scn.collection.objects.link(wire)
import bmesh  # noqa: E402  (weld UV-seam splits first, or decimation leaves long stray edges)
bm = bmesh.new(); bm.from_mesh(wire.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(wire.data); bm.free()
dec = wire.modifiers.new("dec", "DECIMATE"); dec.ratio = 0.015
wf = wire.modifiers.new("wf", "WIREFRAME"); wf.thickness = reach * 0.004; wf.use_replace = True
mat = bpy.data.materials.new("glow"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (0.49, 1.0, 0.42, 1); em.inputs[1].default_value = 1.0
outn = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], outn.inputs[0])
wire.data.materials.clear(); wire.data.materials.append(mat)
model.hide_render = True
shot(f"{out}/wire.png")
wire.hide_render = True
model.hide_render = False

if only != "still":
    for i in range(frames):
        pivot.rotation_euler = (0, 0, -2 * math.pi * i / frames)   # turn the model; camera stays at the aligned view
        shot(f"{out}/spin/s_{i:04d}.png")
