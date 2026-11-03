"""blender -b -P showcase.py -- <out.blend>: the 3D layer of the shared Vi3W outro (7 s, no text — Remotion adds it).

Twelve real Vi3W generations on a neon turntable: they pop in one after another, the camera pulls back to reveal
the ring, the ring keeps turning and every model spins on its own plinth. Text safe zones are left clear:
top ~0-560 px (headline) and bottom ~1250-1750 px (CTA); the models live in the middle band.
"""
import math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "reelforge", "blender"))
import bpy
import director as D
import look as L
from director import T

out = sys.argv[sys.argv.index("--") + 1]
END = 7.0
H = D.hex_lin
# (file, height m): only models generated in Vi3W
MODELS = [
    ("Input/roblox.glb", 1.15), ("Ko-nJWvMxKKBSoCf-5w9K_model.glb", 1.15), ("Input/panda.glb", 1.1),
    ("projects/shorts/roblox-explainer/public/baddie.glb", 1.3), ("Input/bread.glb", 1.0), ("Input/forest-deer.glb", 1.35),
    ("projects/launch/one-sketch-away/public/assets/frog.glb", 1.2), ("k3CTDgrIgTP9jLL3HXRdB_model.glb", 1.15),
    ("Input/robot.glb", 1.2), ("projects/shorts/playground-serpent/assets/model.glb", 0.75),
    ("Input/brickguy.glb", 1.15), ("projects/launch/one-sketch-away/public/assets/cat.glb", 0.75),
]

s = D.reset(frames=T(END) - 1)
D.fast_eevee(s, samples=16, look="AgX - Punchy", raytrace=True)


def load(path, height, name):
    """GLB → one decimated mesh, standing on z=0, centred, `height` m tall."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, path))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        D.adopt(o)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    import bmesh
    bm = bmesh.new()
    mats = []
    for o in new:
        if o.type != "MESH":
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(o.matrix_world)
        off = len(mats)
        mats += list(o.data.materials)
        for p in me.polygons:
            p.material_index += off
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    m = bpy.data.meshes.new(name)
    bm.to_mesh(m)
    bm.free()
    for mt in mats:
        m.materials.append(mt)
    for o in new:
        bpy.data.objects.remove(o)
    o = D.link(bpy.data.objects.new(name, m))
    if len(m.polygons) > 60_000:
        mod = o.modifiers.new("dec", "DECIMATE")
        mod.ratio = 40_000 / len(m.polygons)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        o.modifiers.clear()
        o.data = me
        bpy.data.meshes.remove(m)
        m = me
    vs = [v.co for v in m.vertices]
    mn = Vector([min(v[i] for v in vs) for i in range(3)])
    mx = Vector([max(v[i] for v in vs) for i in range(3)])
    k = height / (mx.z - mn.z)
    if max(mx.x - mn.x, mx.y - mn.y) * k > 1.3:               # long models (serpent): fit the footprint instead
        k = 1.3 / max(mx.x - mn.x, mx.y - mn.y)
    c = (mn + mx) / 2
    m.transform(Matrix.Scale(k, 4) @ Matrix.Translation((-c.x, -c.y, -mn.z)))
    for p in m.polygons:
        p.use_smooth = True
    return o


# ---------------------------------------------------------------- stage: violet sweep, neon turntable
L.hdri_world(s, "studio_small_09", 0.55, rot_deg=40, backdrop=H("#2a0f5c"), backdrop_strength=1.0)
D.cyclorama(L.plastic("cyc", H("#3b1785"), rough=0.8, coat=0.0), width=60, depth=40, y_wall=9, radius=5, height=25)
disc_mat = L.plastic("disc", H("#160a33"), rough=0.12, coat=0.9)
neon_c = L.plastic("neon_c", H("#22e1ff"), rough=0.3, emit=H("#22e1ff"), emit_strength=6.0)
neon_p = L.plastic("neon_p", H("#ff3df2"), rough=0.3, emit=H("#ff3df2"), emit_strength=6.0)
ring = D.empty("ring")
D.cyl("disc", 3.75, 0.22, (0, 0, 0.11), m=disc_mat, verts=128).parent = ring
D.torus("rim_c", 3.78, 0.035, (0, 0, 0.2), m=neon_c).parent = ring
D.torus("rim_p", 3.78, 0.03, (0, 0, 0.02), m=neon_p).parent = ring
D.torus("inner", 2.05, 0.02, (0, 0, 0.225), m=neon_c).parent = ring
D.area_light("key", 1200, (-3.5, -7, 6.5), (0, 0, 1), size=5)
D.area_light("pink", 900, (-6, 4, 3), (0, 0, 1), size=4, rgb=H("#ff4fd8"))
D.area_light("cyan", 900, (6, 4, 3), (0, 0, 1), size=4, rgb=H("#3fd4ff"))
D.area_light("fill", 520, (0, -9, 1.5), (0, 0, 1), size=6, rgb=H("#e6ddff"))
L.post(s, bloom=0.5, bloom_threshold=0.85, vignette=0.3, saturation=1.1)

# ---------------------------------------------------------------- the models
plinth_m = L.plastic("plinth", H("#f4f1ff"), rough=0.25, coat=0.6)
N, R = len(MODELS), 2.9
for i, (path, h) in enumerate(MODELS):
    a = -math.pi / 2 + i * 2 * math.pi / N                     # i=0 sits front-centre (−Y, toward camera)
    p = Vector((R * math.cos(a), R * math.sin(a), 0.22))
    base = D.empty(f"slot{i}", p)
    base.parent = ring
    D.cyl("plinth", 0.48, 0.16, (0, 0, 0.08), m=plinth_m, verts=48).parent = base
    D.torus("pl_neon", 0.485, 0.012, (0, 0, 0.16), m=neon_p if i % 2 else neon_c).parent = base
    spin = D.empty(f"spin{i}", (0, 0, 0.16))
    spin.parent = base
    o = load(path, h, f"m{i}")
    o.parent = spin
    order = min(i, N - i)                                      # pop from the front outwards
    t0 = order * 0.1
    v0 = (0.35,) * 3 if order == 0 else (0, 0, 0)               # the hero is already arriving on frame 1
    D.overshoot(base, "scale", max(1, T(t0)), T(t0 + 0.35), v0, (1, 1, 1), 1.22)
    face = math.atan2(-p.x, p.y) + math.pi                       # face the camera-ish (outward)
    D.key(spin, "rotation_euler", 1, (0, 0, face - 0.5))
    D.key(spin, "rotation_euler", T(END), (0, 0, face + 1.6))
    for fc in D._fcurves(spin.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"

D.key(ring, "rotation_euler", 1, (0, 0, 0))
D.key(ring, "rotation_euler", T(END), (0, 0, math.radians(140)))
for fc in D._fcurves(ring.animation_data.action):
    for k in fc.keyframe_points:
        k.interpolation, k.easing = "SINE", "EASE_OUT"

# ---------------------------------------------------------------- camera: close on the hero → reveal → slow settle
c, look = D.camera("cam", 28)
D.key(c, "location", 1, Vector((0.3, -6.2, 1.25)))
D.key(c, "location", T(2.3), Vector((0, -8.9, 3.0)))
D.key(c, "location", T(END), Vector((-0.3, -8.3, 2.7)))
D.key(look, "location", 1, Vector((0, -2.9, 0.95)))
D.key(look, "location", T(2.3), Vector((0, 0.2, 0.75)))
D.key(look, "location", T(END), Vector((0, 0.2, 0.8)))
D.ease_all(c)
D.ease_all(look)
D.handheld(look, 0.003)
D.cut(s, 1, c)
bpy.ops.wm.save_as_mainfile(filepath=out)
print("saved", out)
