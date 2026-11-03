"""blender -b -P outro.py -- <out.blend>: the shared Vi3W outro (6 s, rendered ONCE → outro.mp4, silent).

Real Vi3W generations (bread, panda, robot) pop onto plinths and spin; "MADE WITH THE / Vi3W WORKFLOW" lands at
TITLE_AT, "Vi3W.in" at URL_AT. Each short records its own fresh VO line ("And this whole video? Made with the Vi3W
workflow. Vi3W.in") and aligns the spoken URL to URL_AT — see projects/shorts/vi3w-outro/README.md.
"""
import json, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
import bpy
import director as D
import look as L
from director import T

out = sys.argv[sys.argv.index("--") + 1]
A = os.path.join(HERE, "assets")
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
END, TITLE_AT, URL_AT = 6.0, 1.2, 3.2
H = D.hex_lin

show = D.reset(frames=T(END) - 1)
D.fast_eevee(show, samples=16, look="AgX - Punchy")
white = L.plastic("white", H("#f7f4ef"), rough=0.3)


def key(o, p, t, v):
    D.key(o, p, T(t), v)


def pop(o, t, scale=1.0, dur=0.3):
    D.key(o, "scale", 1, (0, 0, 0))
    D.key(o, "scale", T(t), (0, 0, 0))
    D.overshoot(o, "scale", T(t), T(t + dur), (0, 0, 0), (scale,) * 3, 1.18)


def vi3w_model(path, name, height, decimate=0.12):
    """Vi3W GLB → one decimated mesh standing on z=0, ~`height` m tall. Returns (object, mesh) for re-use."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    ms = [o for o in new if o.type == "MESH"]
    for o in new:
        D.adopt(o)
    m = ms[0]
    bpy.context.view_layer.update()
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = mw
    for o in new:
        if o is not m:
            bpy.data.objects.remove(o)
    m.data.transform(m.matrix_world)
    m.matrix_world = Matrix()
    if decimate and len(m.data.polygons) > 80_000:
        mod = m.modifiers.new("dec", "DECIMATE")
        mod.ratio = decimate
        bpy.context.view_layer.objects.active = m
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(m.evaluated_get(dg))
        m.modifiers.clear()
        old = m.data
        m.data = me
        bpy.data.meshes.remove(old)
    vs = [v.co for v in m.data.vertices]
    mn = Vector([min(v[i] for v in vs) for i in range(3)])
    mx = Vector([max(v[i] for v in vs) for i in range(3)])
    s = height / (mx.z - mn.z)
    c = (mn + mx) / 2
    m.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-c.x, -c.y, -mn.z)))
    for p in m.data.polygons:
        p.use_smooth = True
    m.name = name
    return m, m.data


def clone(me, name, loc, rz=0.0, scale=1.0):
    o = D.link(bpy.data.objects.new(name, me))
    o.location, o.rotation_euler, o.scale = loc, (0, 0, rz), (scale,) * 3
    return o



col = H("#7c3aed")
L.hdri_world(show, "studio_small_09", 0.9, rot_deg=40, backdrop=col, backdrop_strength=0.9)
D.cyclorama(L.plastic("show_cyc", col, rough=0.75, coat=0.0), width=40, depth=30, y_wall=8, radius=4, height=20)
D.area_light("s_key", 450, (-3, -5, 6), (0, 0, 1.0), size=4)
D.area_light("s_rim", 280, (3, 4, 4), (0, 0, 1.0), size=3, rgb=H("#fff1dc"))
L.post(show, bloom=0.3, vignette=0.26)
items = (("bread", -1.2, 0.15, 0.62, 1.6), ("panda", 0.0, 0.35, 0.8, 0.0), ("robot", 1.2, 0.55, 0.95, 0.4))
for name, x, t, h, rz in items:
    plinth = D.cyl("plinth", 0.42, 0.5, (x, 0, 0.25), m=white, verts=48)
    tt = D.empty("tt", (x, 0, 0.5))
    o, _ = vi3w_model(os.path.join(A, name + ".glb"), name, h, decimate=0.12 if name != "panda" else 0)
    o.parent, o.rotation_euler = tt, (0, 0, rz)
    pop(plinth, t, 1.0, 0.3)
    pop(tt, t + 0.08, 1.0, 0.35)
    key(tt, "rotation_euler", 0, (0, 0, 0))
    key(tt, "rotation_euler", END, (0, 0, math.radians(150)))
    for fc in D._fcurves(tt.animation_data.action):
        if fc.data_path == "rotation_euler":
            for k in fc.keyframe_points:
                k.interpolation = "LINEAR"
tw = L.plastic("tw", H("#ffffff"), rough=0.3)
for i, line in enumerate(("MADE WITH THE", "Vi3W WORKFLOW")):
    t = D.text3d("title", line, 0.3, (0, 0.2, 2.55 - i * 0.4), tw, extrude=0.05, bevel=0.012, font=FONT)
    pop(t, TITLE_AT + i * 0.12, 1.0, 0.3)
url = D.text3d("url", "Vi3W.in", 0.46, (0, 0.2, 1.72), L.plastic("ty", H("#ffd23f"), rough=0.3),
               extrude=0.06, bevel=0.014, font=FONT)
pop(url, URL_AT, 1.0, 0.3)
c, l = D.camera("cam", 30)
D.move(c, l, 1, T(END), (0, -5.3, 1.3), (0, -4.6, 1.25), (0, 0, 1.3), (0, 0, 1.3), 30, 30)
D.handheld(l, 0.003)
D.cut(show, 1, c)
bpy.ops.wm.save_as_mainfile(filepath=out)
with open(os.path.join(os.path.dirname(out), "..", "outro.json"), "w") as fh:
    json.dump({"dur": END, "title_at": TITLE_AT, "url_at": URL_AT, "fps": 30}, fh)
