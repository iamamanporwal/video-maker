"""blender -b -P scene.py -- <out.blend>: build the 10 s "reach into the 2D world" pilot and save it.

Story beats keyed to the reference VO word times (ref/words.json):
  S1 0.0-2.0  "You reach into the 2D world"       over-shoulder, arm rises toward the board
  S2 2.0-3.9  "and take off the girl's hat"       close-up, fingers close, hat lifts off and pops to 3D
  S3 3.9-6.5  "flip it around ... put it on backward"  3/4 close-up, hat spins 180°, goes back on, flattens
  S4 6.5-10.0 "Now if the girl has only ever existed in 2D"  wide push-in, girl feels her hat, "2D" pops at 9.2 s
"""
import math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
import bpy
import director as D
from director import T

out = sys.argv[sys.argv.index("--") + 1]
CHAR = os.path.join(HERE, "assets", "Michelle.glb")
FLAT = 0.03                                   # depth squash that turns a 3D body into a "2D drawing"

s = D.reset(frames=300)
D.fast_eevee(s, samples=8)

# ---------------------------------------------------------------- set: light-blue studio, whiteboard on a stand
BLUE = D.hex_lin("#8fd0e3")
D.world(s, D.hex_lin("#a9dcec"), 0.55)
D.cyclorama(D.mat("cyc", BLUE, rough=0.9), y_wall=3.5, radius=2.5)
D.sun("sun", 4.6, (0.35, 0.8, -0.75), angle=14)
D.area_light("key", 300, (-1.6, -2.4, 3.0), (0, 0, 1.4), size=2.5)
D.area_light("fill", 70, (2.2, -2.0, 1.6), (0, 0, 1.3), size=3.0, rgb=(0.92, 0.96, 1.0))

white = D.mat("board", (0.78, 0.8, 0.81), rough=0.22)
alu = D.mat("alu", (0.75, 0.76, 0.78), rough=0.32, metal=1.0)
ink = D.mat("ink", (0.02, 0.02, 0.025), rough=0.6)
BW, BH, BZ = 2.2, 1.4, 1.38                   # board width / height / centre height; surface at y=0
D.box("board", (BW, 0.02, BH), (0, 0.01, BZ), white)
for x in (-BW / 2, BW / 2):
    D.box("frame_v", (0.03, 0.035, BH + 0.03), (x, 0.012, BZ), alu, bevel=0.006)
for z in (BZ - BH / 2, BZ + BH / 2):
    D.box("frame_h", (BW + 0.03, 0.035, 0.03), (0, 0.012, z), alu, bevel=0.006)
D.box("tray", (BW * 0.9, 0.07, 0.02), (0, -0.02, BZ - BH / 2 - 0.02), alu, bevel=0.004)
for x in (-BW / 2 + 0.06, BW / 2 - 0.06):
    D.cyl("leg", 0.018, BZ - BH / 2, (x, 0.04, (BZ - BH / 2) / 2), m=alu)
    D.cyl("foot", 0.016, 0.7, (x, 0.04, 0.03), (math.pi / 2, 0, 0), m=alu)

# doodles: ground line, sun, a bird and a cloud scribble (marker on the board)
Y = -0.002
D.stroke("ground", [(-1.0, Y, 0.745), (-0.5, Y, 0.735), (0.0, Y, 0.742), (0.5, Y, 0.738), (1.0, Y, 0.745)], ink)
c, r = Vector((0.72, Y, 1.86)), 0.09
D.stroke("sun", [tuple(c + Vector((r * math.cos(a), 0, r * math.sin(a))))
                 for a in [i * math.tau / 12 for i in range(12)]], ink, cyclic=True)
for i in range(8):
    a = i * math.tau / 8
    d = Vector((math.cos(a), 0, math.sin(a)))
    D.stroke(f"ray{i}", [tuple(c + d * 0.13), tuple(c + d * 0.17), tuple(c + d * 0.2)], ink)
D.stroke("bird", [(0.25, Y, 1.78), (0.29, Y, 1.81), (0.32, Y, 1.785), (0.35, Y, 1.81), (0.39, Y, 1.78)], ink)
D.stroke("cloud", [(-0.95, Y, 1.8), (-0.88, Y, 1.86), (-0.8, Y, 1.84), (-0.73, Y, 1.89), (-0.64, Y, 1.84),
                   (-0.6, Y, 1.79)], ink)

# ---------------------------------------------------------------- the 2D girl: a real rig, squashed onto the board
GX, GS = -0.22, 0.6
flat = D.empty("flat", (0, -0.012, 0))
girl, grig, gbody = D.import_char(CHAR, "girl")
for m in gbody:
    m.visible_shadow = False                  # a drawing casts no shadow
girl.parent, girl.location, girl.rotation_euler, girl.scale = flat, (GX, 0, 0.745), (0, 0, math.pi / 2), (GS,) * 3
bpy.context.view_layer.update()

F = Vector((1, 0, 0))                          # her forward (profile, facing right)
stand = {"Spine": (0.04, 0, 1), "Neck": (0.12, 0, 1), "Head": (0.1, 0, 1),
         "LeftUpLeg": (0.16, 0, -1), "LeftLeg": (0.02, 0, -1), "LeftFoot": (1, 0, -0.5),
         "RightUpLeg": (-0.1, 0, -1), "RightLeg": (-0.18, 0, -1), "RightFoot": (1, 0, -0.6),
         "LeftArm": (0.12, -0.05, -1), "LeftForeArm": (0.35, -0.05, -1), "LeftHand": (0.3, 0, -1),
         "RightArm": (-0.05, 0.05, -1), "RightForeArm": (0.25, 0.05, -1), "RightHand": (0.2, 0, -1)}
D.pose(grig, 1, stand)
D.pose(grig, T(7.0), stand)
# S4: she looks up and pats the backwards hat ("Now if the girl...")
feel = {"Head": (-0.12, 0, 1), "RightArm": (0.55, 0, 0.3), "RightForeArm": (-0.45, 0, 0.9), "RightHand": (-0.8, 0, 0.6)}
D.pose(grig, T(7.6), feel)
D.pose(grig, T(8.7), feel)
D.pose(grig, T(9.4), {"Head": (0.05, 0, 1), "RightArm": (0.1, 0.05, -1), "RightForeArm": (0.5, 0.05, -1)})
D.curl(grig, "Right", 1, 0.25)
D.curl(grig, "Left", 1, 0.25)

flat.scale = (1, FLAT, 1)
bpy.context.view_layer.update()
head_top = D.bone_world(grig, "HeadTop_End")
head = D.bone_world(grig, "Head")

# ---------------------------------------------------------------- the cap (built here, brim along local +X)
brown = D.mat("cap", D.hex_lin("#7a4a22"), rough=0.55)
bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1)
dome = bpy.context.active_object
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
for v in dome.data.vertices:
    v.select = v.co.z < -0.02
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.delete(type="VERT")
bpy.ops.object.mode_set(mode="OBJECT")
dome.scale = (1.0, 0.94, 0.9)
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=0.11)
brim = bpy.context.active_object
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
for v in brim.data.vertices:
    v.select = v.co.x < 0.05
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.delete(type="VERT")
bpy.ops.object.mode_set(mode="OBJECT")
brim.scale, brim.location, brim.rotation_euler = (1.25, 0.85, 1), (0.42, 0, 0.03), (0, math.radians(8), 0)
for o in (dome, brim):
    o.select_set(True)
bpy.context.view_layer.objects.active = dome
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.join()
hat = D.smooth(dome)
hat.name = "hat"
sol = hat.modifiers.new("thick", "SOLIDIFY")
sol.thickness = 0.04
D.give(hat, brown)
btn = D.cyl("button", 0.09, 0.05, (0, 0, 0.79), m=brown)
btn.parent = hat

HS = 0.068                                    # cap radius in metres (fits the girl's head at GS)
on_head = Vector((head_top.x + 0.005, -0.016, head_top.z - 0.03))
lifted = Vector((GX + 0.02, -0.26, head_top.z + 0.16))
hat.rotation_mode = "XYZ"
F_GRAB, F_UP0, F_UP1 = T(2.5), T(2.72), T(3.55)
F_FLIP0, F_FLIP1 = T(4.55), T(5.3)
F_PUT0, F_PUT1 = T(5.55), T(6.15)


def hat_key(f, loc, yaw, depth):
    D.key(hat, "location", f, Vector(loc))
    D.key(hat, "rotation_euler", f, (0, math.radians(-6 if depth > 0.5 else 0), math.radians(yaw)))
    D.key(hat, "scale", f, (HS, HS * depth, HS))


hat_key(1, on_head, 0, FLAT)
hat_key(F_UP0, on_head, 0, FLAT)
hat_key(T(3.0), on_head + Vector((0, -0.12, 0.08)), 0, 1.0)        # peels off the board, pops to full depth
hat_key(F_UP1, lifted, 0, 1.0)
hat_key(F_FLIP0, lifted + Vector((0, 0, 0.02)), 0, 1.0)
hat_key(F_FLIP1, lifted + Vector((0, 0, 0.03)), 180, 1.0)           # "flip it around"
hat_key(F_PUT0, lifted + Vector((0, 0, 0.0)), 180, 1.0)
hat_key(T(5.95), on_head + Vector((0, -0.1, 0.06)), 180, 1.0)
hat_key(F_PUT1, on_head, 180, FLAT)                                 # back on, and 2D again
D.ease_all(hat)

# ---------------------------------------------------------------- "you": a full-size rig whose right hand follows the hat
RX = -0.52
you, yrig, _ = D.import_char(CHAR, "you")
you.location, you.rotation_euler, you.scale = (RX, -0.44, 0), (0, 0, math.pi), (1.08,) * 3
bpy.context.view_layer.update()
D.pose(yrig, 1, {"Spine": (0, 0.06, 1), "Head": (0.12, 0.25, 1),
                 "LeftArm": (-0.15, 0.05, -1), "LeftForeArm": (-0.08, 0.2, -1)})
D.curl(yrig, "Left", 1, 0.35)

ik = D.empty("ik", (RX + 0.25, -0.5, 0.95))
pole = D.empty("pole", (RX + 0.55, -0.95, 0.9))
D.ik_arm(yrig, "Right", ik, pole, pole_angle=-90)
D.track(yrig, "RightHand", hat, influence=0.85)
look = D.track(yrig, "Head", hat, axis="TRACK_Z", influence=0.0)

GRIP = Vector((0.035, -0.115, 0.02))             # wrist sits in front of the cap (camera side) while pinching it


def wrist_at(f):
    s.frame_set(f)
    m = hat.matrix_world
    loc, rot, _ = m.decompose()
    return loc + rot @ GRIP + Vector((0, 0, -0.012))


D.key(ik, "location", 1, Vector((RX + 0.28, -0.52, 0.92)))
D.key(ik, "location", T(0.35), Vector((RX + 0.3, -0.5, 0.98)))
reach = wrist_at(F_GRAB)
D.key(ik, "location", T(1.9), reach + Vector((0.02, -0.06, -0.05)))
D.key(ik, "location", F_GRAB, reach)
D.ease_all(ik)
for f in range(F_GRAB + 1, F_PUT1 + 1):        # bake: the wrist rides the cap through lift, flip and put-back
    D.key(ik, "location", f, wrist_at(f), interp="LINEAR")
D.key(ik, "location", T(6.5), wrist_at(F_PUT1) + Vector((0.06, -0.18, -0.12)))

D.curl(yrig, "Right", 1, 0.15)
D.curl(yrig, "Right", T(2.3), 0.15)
D.curl(yrig, "Right", F_GRAB, 0.62)
D.curl(yrig, "Right", F_PUT1, 0.62)
D.curl(yrig, "Right", T(6.4), 0.2)
for o in [you] + [c for c in you.children_recursive]:
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=T(6.5) - 1)
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=T(6.5))

# ---------------------------------------------------------------- "2D" pops beside her on "2D" (9.2 s)
blue = D.mat("label", D.hex_lin("#0a46c8"), rough=0.18, emit=D.hex_lin("#0a46c8"), emit_strength=0.25)
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
label = D.text3d("2D", "2D", 0.38, (GX + 0.58, -0.09, 1.52), blue, extrude=0.035, bevel=0.008, font=FONT)
label.scale = (0, 0, 0)
D.key(label, "scale", 1)
D.overshoot(label, "scale", T(9.1), T(9.45), (0, 0, 0), (1, 1, 1), 1.15)
D.key(label, "rotation_euler", T(9.1), (math.pi / 2, 0, math.radians(-25)))
D.key(label, "rotation_euler", T(10.0), (math.pi / 2, 0, math.radians(8)))
D.ease_all(label)

# ---------------------------------------------------------------- cameras (cuts on the VO phrases)
hz = head_top.z
c1, l1 = D.camera("S1_overshoulder", 30)
D.move(c1, l1, 1, T(2.0), (0.32, -2.15, 1.9), (0.2, -1.8, 1.86), (-0.32, 0, 1.5), (-0.28, 0, 1.56), 28, 31)
D.handheld(l1, 0.006)

c2, l2 = D.camera("S2_closeup", 38, dof=4.0)
D.move(c2, l2, T(2.0), T(3.9), (0.05, -0.95, hz + 0.02), (0.0, -0.9, hz + 0.1),
       (GX + 0.02, -0.05, hz - 0.06), (GX + 0.0, -0.18, hz + 0.1))
D.handheld(l2, 0.005, seed=1)

c3, l3 = D.camera("S3_flip", 36, dof=4.0)
D.move(c3, l3, T(3.9), T(6.5), (0.5, -1.0, hz + 0.3), (0.38, -1.12, hz + 0.16),
       lifted + Vector((0, 0.05, -0.05)), on_head + Vector((0, -0.05, 0.02)))
D.handheld(l3, 0.005, seed=2)

c4, l4 = D.camera("S4_wide", 30)
D.move(c4, l4, T(6.5), T(10.0), (0.1, -2.75, 1.42), (0.05, -2.3, 1.4), (0.02, 0, 1.3), (0.06, 0, 1.33))
D.handheld(l4, 0.005, seed=3)

for f, c in ((1, c1), (T(2.0), c2), (T(3.9), c3), (T(6.5), c4)):
    D.cut(s, f, c)

bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "head_top", tuple(round(x, 3) for x in head_top))
