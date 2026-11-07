"""Blender previsual for the Zack-D-style 'studio three clicks' short.

Usage: Blender -b -P scene.py -- out/scene.blend
The camera travels through four motivated sets.  All copy is composited later;
these objects deliberately represent an idea, not a fabricated product UI.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "reelforge", "blender"))
import bpy
from mathutils import Vector
import director as D

out = sys.argv[sys.argv.index("--") + 1]
words = json.load(open(os.path.join(HERE, "out", "words.json")))
END = words["dur"] + 0.6
T = D.T
s = D.reset(frames=T(END))
D.fast_eevee(s, samples=8, look="AgX - Medium High Contrast")

# Palette: red means friction. Lime only arrives after the first click.
INK = D.mat("ink", D.hex_lin("#12151C"), rough=0.62)
FLOOR = D.mat("floor", D.hex_lin("#262B35"), rough=0.75)
WHITE = D.mat("white", D.hex_lin("#EAF0F2"), rough=0.35)
RED = D.mat("friction_red", D.hex_lin("#ED3E49"), rough=0.3, emit=D.hex_lin("#ED3E49"), emit_strength=0.3)
LIME = D.mat("lime", D.hex_lin("#C9FF5C"), rough=0.28, emit=D.hex_lin("#A0D93A"), emit_strength=0.28)
BLUE = D.mat("blue", D.hex_lin("#68C8FF"), rough=0.32)
VIOLET = D.mat("violet", D.hex_lin("#A889FF"), rough=0.32)

D.world(s, D.hex_lin("#101319"), 0.35)
D.cyclorama(FLOOR, width=40, depth=42, height=12, radius=3.5, y_wall=15)
D.area_light("key", 1250, (-4, -5, 7), (8, 1, 1.3), 6)
D.area_light("fill", 700, (22, -3, 5), (20, 2, 1.5), 5, rgb=(0.55, 0.78, 1.0))
D.sun("rim", 2.0, (-0.3, 0.6, -0.8), rgb=(0.8, 1.0, 0.55), angle=12)


def key(obj, prop, t, val):
    D.key(obj, prop, T(t), val)


def visible(obj, a, b):
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=1)
    obj.hide_render = False
    obj.keyframe_insert("hide_render", frame=T(a))
    obj.hide_render = False
    obj.keyframe_insert("hide_render", frame=T(b))
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=T(b) + 1)


def label(text, x, z, material, size=0.45):
    return D.text3d("type_" + text[:10], text, size, (x, 1.4, z), material, rot=(math.pi / 2, 0, 0), extrude=0.012,
                    bevel=0.006, font="/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf")


def robot(x, y, scale=1.0, mat=WHITE):
    """Original, simple hero robot: deliberately procedural rather than a copied character."""
    root = D.empty("robot_root", (x, y, 0))
    parts = [
        D.box("bot_body", (1.1, 0.55, 1.15), (x, y, 1.48), mat, bevel=0.14),
        D.box("bot_head", (1.0, 0.56, 0.7), (x, y, 2.45), mat, bevel=0.16),
        D.sphere("bot_eye_l", 0.09, (x - 0.23, y - 0.3, 2.48), LIME),
        D.sphere("bot_eye_r", 0.09, (x + 0.23, y - 0.3, 2.48), LIME),
        D.cyl("bot_arm_l", 0.12, 0.92, (x - 0.72, y, 1.5), (0, math.pi / 2, 0), mat),
        D.cyl("bot_arm_r", 0.12, 0.92, (x + 0.72, y, 1.5), (0, math.pi / 2, 0), mat),
        D.cyl("bot_leg_l", 0.14, 0.75, (x - 0.28, y, 0.55), m=mat),
        D.cyl("bot_leg_r", 0.14, 0.75, (x + 0.28, y, 0.55), m=mat),
    ]
    for p in parts:
        p.parent = root
    root.scale = (scale, scale, scale)
    return root


# SET 1: an artist hemmed in by red workflow blocks. Existing CC-BY Sketchfab assets are imported as set dressing.
try:
    artist, rig, _ = D.import_char(os.path.join(ROOT, "projects/shorts/learn-blender-hindi/assets/eric.glb"), "artist")
    artist.location, artist.rotation_euler, artist.scale = (0, 1.7, 0), (0, 0, math.pi), (0.95, 0.95, 0.95)
except Exception as e:
    print("Artist import skipped:", e)
for i, x in enumerate((-2.2, -1.1, 0.0, 1.1, 2.2)):
    block = D.box(f"workflow_{i}", (0.7, 0.45, 2.2 + (i % 2) * 0.7), (x, 1.6, 1.1), RED, bevel=0.08)
    visible(block, 0, 14.0)
bar = D.box("render_bar", (5.7, 0.22, 0.25), (0, 0.1, 4.2), RED, bevel=0.08)
visible(bar, 0, 14.0)
label("WAITING", 0, 4.7, WHITE, 0.35)

# SET 2: the idea is trapped in a maze, then releases on the first click.
sketch = robot(8.0, 1.0, 0.62, WHITE)
for p in sketch.children:
    if p.type == "MESH":
        p.scale.y = 0.06
for i, (dx, dz) in enumerate(((-1.8, 0.8), (-1.0, 2.8), (0.5, 0.6), (1.7, 2.5))):
    wall = D.box(f"maze_{i}", (0.22, 0.4, 2.2), (8 + dx, 1.0, dz), RED, bevel=0.04)
    visible(wall, 7.8, 14.2)
label("DAYS", 8, 4.5, RED, 0.42)

# SET 3: a full 3D robot, lime orbit and three click tokens.
hero = robot(16.0, 1.2, 1.05, WHITE)
for deg in (0, 120, 240):
    a = math.radians(deg)
    orb = D.torus("orbit", 1.65, 0.035, (16, 1.2, 1.6), (math.radians(70), 0, a), LIME)
    key(orb, "rotation_euler", 14.0, orb.rotation_euler)
    key(orb, "rotation_euler", 28.0, (orb.rotation_euler.x, orb.rotation_euler.y, orb.rotation_euler.z + math.tau))
for n, x in enumerate((14.2, 16.0, 17.8), 1):
    token = D.cyl(f"click_{n}", 0.32, 0.12, (x, 0.3, 3.65), (math.pi / 2, 0, 0), LIME)
    label(str(n), x, 3.55, INK, 0.27)
    visible(token, 14.0 + n * 1.1, END)

# SET 4: three destinations share the exact same robot silhouette.
for x, mat, name in ((22.0, BLUE, "GAME"), (26.0, LIME, "PRODUCT"), (30.0, VIOLET, "FILM")):
    D.box("portal_" + name, (4.2, 0.45, 4.8), (x, 2.2, 2.4), mat, bevel=0.28)
    mini = robot(x, 0.3, 0.62, WHITE)
    label(name, x, 4.95, WHITE, 0.34)
final = label("3D IN THREE CLICKS", 30.0, 5.8, LIME, 0.38)
visible(final, 38.0, END)

# One continuous, curved-feeling rail move: each arrival is a fresh visual chapter.
cam, look = D.camera("master_camera", 32, dof=5.6)
points = [
    (0.0, (-0.1, -6.8, 2.2), (0, 1.1, 2.0)),
    (7.8, (7.6, -5.8, 2.1), (8, 1.0, 1.8)),
    (14.0, (15.3, -6.3, 2.5), (16, 1.2, 1.75)),
    (28.0, (23.0, -7.2, 2.4), (25.0, 1.8, 2.1)),
    (38.0, (30.0, -7.9, 3.0), (30.0, 1.5, 2.3)),
    (END, (30.0, -8.8, 3.1), (30.0, 1.5, 2.3)),
]
for t, loc, target in points:
    D.key(cam, "location", T(t), loc)
    D.key(look, "location", T(t), target)
D.ease_all(cam)
D.ease_all(look)
D.handheld(look, 0.004, seed=21)
D.cut(s, 1, cam)

bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "duration", END)
