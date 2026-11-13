"""blender -b -P scene.py -- <out.blend>: "Cars aren't machines" - Lightning McQueen anatomy cutaway (parody).

Timeline seconds = VO word time + VO_AT (0.3). Sets are separate scenes:

  GUTS   0.0  hook push on McQueen → laser slice → near half flies off → brain / heart / guts / brain again
  FACE   9.7  windshield eyelid blink;  21.5 bumper mouth with teeth;  24.8 pit stop: T-posing strangers, tires shot off
  STRETCH 19.6 intestine unspools for metres
  CRASH  30.9 slams a wall → chalk outline + tape;  35.0 Mater tows him away ("hearse")

Cast: Sketchfab "Lightning McQueen" (DinseyPixarCarsModels, CC-BY), "Tom Mater 3DS" (joseclaudio162001, CC-BY),
Renderpeople "Eric" (CC-BY). Organs are procedural.
"""
import math, os, random, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
import bpy, bmesh
import director as D
import look as L
import zack as Z

out = sys.argv[sys.argv.index("--") + 1]
A = lambda n: os.path.join(HERE, "assets", n)
VO = 0.3
END = 41.4
T = lambda s: D.T(s)
H = D.hex_lin
random.seed(3)
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

base = D.reset(w=1080, h=1920, frames=T(END) - 1)
D.fast_eevee(base, samples=12, look="AgX - Punchy")
SHOTS = []


def v(t):           # VO word time → timeline
    return t + VO


# ---------------------------------------------------------------- helpers
def upd():
    for sc in bpy.data.scenes:
        sc.view_layers[0].update()


def shot(sc, name, t0, t1, loc0, loc1, at0, at1, lens0=35, lens1=None, shake=0.0):
    c, l = D.camera(name, lens0)
    D.move(c, l, T(t0), T(t1), loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    D.cut(sc, T(t0), c)
    SHOTS.append((sc.name, T(t0), T(t1) - 1))
    return c, l


def glb(path):
    """Import → list of mesh objects with transforms applied (non-mesh helpers removed)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ms = []
    for o in new:
        if o.type == "MESH" and o.data.materials and len(o.data.polygons) > 4:
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            me.transform(o.matrix_world)
            ms.append(D.link(bpy.data.objects.new(o.name, me)))
    for o in new:
        bpy.data.objects.remove(o)
    return ms


def group(name, ms, loc=(0, 0, 0), rotz=0.0, scale=1.0):
    g = D.empty(name, loc)
    g.rotation_euler = (0, 0, rotz)
    g.scale = (scale,) * 3
    for o in ms:
        o.parent = g
    return g


def car(name, loc=(0, 0, 0), rotz=0.0):
    """McQueen: 4.65 long along Y, nose at -Y, wheels on z=0. Returns (group, {part: obj})."""
    ms = glb(A("mcqueen.glb"))
    parts = {}
    for o in ms:
        k = o.name.split("_")[0].split(".")[0].lower()
        o.name = f"{name}_{k}"
        parts[k] = o
    return group(name, ms, loc, rotz), parts


def split_tires(tires):
    """One mesh with four tyres → four objects with their origin at each hub (so they can spin/fly)."""
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            o = tires.copy()
            o.data = tires.data.copy()
            D.link(o)
            bm = bmesh.new(); bm.from_mesh(o.data)
            bmesh.ops.delete(bm, geom=[q for q in bm.verts if (q.co.x > 0) != (sx > 0) or (q.co.y > 0) != (sy > 0)],
                             context="VERTS")
            bm.to_mesh(o.data); bm.free()
            c = sum((q.co for q in o.data.vertices), Vector()) / max(1, len(o.data.vertices))
            o.data.transform(Matrix.Translation(-c))
            o.location = c
            o.name = f"{tires.name}_{'LR'[sx > 0]}{'FB'[sy > 0]}"
            out.append(o)
    bpy.data.objects.remove(tires)
    return out


def bisect(o, keep_pos, cap_mat=None):
    """Cut o at x=0, keep x>0 (keep_pos) or x<0, and fill the cut loops with cap_mat."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                               clear_inner=keep_pos, clear_outer=not keep_pos, dist=1e-5)
    cut = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if cap_mat is not None and cut:
        if cap_mat.name not in [m.name for m in o.data.materials if m]:
            o.data.materials.append(cap_mat)
        mi = [m.name for m in o.data.materials].index(cap_mat.name)
        f = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=cut)
        for fc in f["geom"]:
            if isinstance(fc, bmesh.types.BMFace):
                fc.material_index = mi
                fc.smooth = False
    bm.to_mesh(o.data); bm.free()


def nmat(name, base_hex, rough=0.45, bump_scale=8.0, bump=0.6, wave=False, emit=0.0, sss=0.0, dark_hex=None, pos=(0.35, 0.65)):
    """Procedural organ material: base colour × noise/wave bump, optional darker crevices."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    bs.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if wave:
        tx = nt.nodes.new("ShaderNodeTexWave")
        tx.inputs["Scale"].default_value = bump_scale
        tx.inputs["Distortion"].default_value = 14.0
        tx.inputs["Detail"].default_value = 3.0
    else:
        tx = nt.nodes.new("ShaderNodeTexNoise")
        tx.inputs["Scale"].default_value = bump_scale
        tx.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], tx.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*H(dark_hex or base_hex), 1) if dark_hex else (*[c * 0.55 for c in H(base_hex)], 1)
    ramp.color_ramp.elements[1].color = (*H(base_hex), 1)
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = pos
    nt.links.new(tx.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    nt.links.new(tx.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bs.inputs["Normal"])
    if "Coat Weight" in bs.inputs:
        bs.inputs["Coat Weight"].default_value = 0.35     # wet look
    if emit:
        bs.inputs["Emission Color"].default_value = (*H(base_hex), 1)
        bs.inputs["Emission Strength"].default_value = emit
    return m


def tube(name, pts, r, m, res=10):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution, cu.resolution_u = "3D", r, 4, res
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = D.link(bpy.data.objects.new(name, cu))
    o.data.materials.append(m)
    return o


def pop(o, t, dur=0.22, amt=1.2):
    Z.pop_in(o, T(t), frames=max(3, int(dur * 30)), amount=amt)


def hide_until(o, t):
    s = tuple(o.scale)
    D.key(o, "scale", 1, (0, 0, 0)); D.key(o, "scale", T(t) - 1, (0, 0, 0)); D.key(o, "scale", T(t), s)
    D.ease_all(o, "CONSTANT")


# ---------------------------------------------------------------- materials
FLESH = nmat("flesh", "#d9505a", bump_scale=6, bump=0.35, dark_hex="#8e1f2c", rough=0.35)
FAT = nmat("fat", "#f2d27a", bump_scale=14, bump=0.25, rough=0.4)
BRAIN = nmat("brain", "#f3a9b0", bump_scale=4.0, bump=1.2, wave=True, dark_hex="#7a2a38", rough=0.3, pos=(0.12, 0.3))
GUT = nmat("gut", "#f39aa0", bump_scale=30, bump=0.4, dark_hex="#d9707a", rough=0.3)
HEART = nmat("heart", "#c3122a", bump_scale=9, bump=0.5, dark_hex="#5e0612", rough=0.3)
VEIN = nmat("vein", "#3d63d6", bump_scale=20, bump=0.2, rough=0.3)
GAS = D.mat("gas", H("#ffd21a"), rough=0.2, emit=H("#ffb800"), emit_strength=3.0)
METAL = D.mat("engine", H("#6c7178"), rough=0.32, metal=1.0)
CHROME = D.mat("chrome", H("#d8dde3"), rough=0.12, metal=1.0)
TOOTH = D.mat("tooth", H("#fbf6e4"), rough=0.25)
GUM = nmat("gum", "#e86f86", bump_scale=12, bump=0.3, rough=0.3)
DARK = D.mat("throat", H("#2a0508"), rough=0.6)
EYEW = D.mat("eyew", H("#f6f3ee"), rough=0.15)
IRIS = D.mat("iris", H("#2f8fe0"), rough=0.2, emit=H("#2f8fe0"), emit_strength=0.4)
PUP = D.mat("pupil", H("#050505"), rough=0.1)
LASER = D.mat("laser", H("#ff1a1a"), emit=H("#ff2a2a"), emit_strength=25.0)
CHALK = D.mat("chalk", H("#ffffff"), rough=1.0, emit=H("#ffffff"), emit_strength=1.2)
TAPE = D.mat("tape", H("#ffd400"), rough=0.6, emit=H("#ffd400"), emit_strength=0.4)
WALL = L.pbr("wall", "red_brick_03", scale=2.0) if os.path.isdir(os.path.join(L.PH, "textures", "red_brick_03")) else \
    D.mat("wall", H("#9a4b3a"), rough=0.9)
SKIN_RED = D.mat("lid", H("#d4141b"), rough=0.25, spec=0.6)
BLACKM = D.mat("blk", H("#000000"), rough=1.0)

# ================================================================ GUTS set: the anatomy cutaway
guts = L.new_set("GUTS", main=True)
with L.building(guts):
    Z.void(guts, edge="#c9b48a", centre="#fbf3e1", glow=0.6, ambient=0.75)
    L.post(guts, bloom=0.25, vignette=0.28, saturation=1.1)
    g_far, far = car("mcq")                  # x>0 half (stays): cut face looks at the camera on -X
    g_near, near = car("mcqN")               # x<0 half (flies off in the hook)
    for k, o in list(far.items()):
        if k == "tires":
            for t in split_tires(o):
                (t.parent if False else None)
                if t.location.x < 0:
                    bpy.data.objects.remove(t)
                else:
                    t.parent = g_far
            continue
        bisect(o, True, FLESH if k == "body" else (FAT if k == "glass" else None))
    for k, o in list(near.items()):
        if k == "tires":
            for t in split_tires(o):
                if t.location.x > 0:
                    bpy.data.objects.remove(t)
                else:
                    t.parent = g_near
            continue
        bisect(o, False, FLESH if k == "body" else (FAT if k == "glass" else None))
    upd()

    # ---- cross-section slab: yellow fat rim + red flesh (the triangle-filled caps are too patchy to rely on)
    TOP = [(-2.22, 0.45), (-2.2, 0.72), (-2.0, 0.88), (-1.6, 0.99), (-1.0, 1.03), (-0.65, 1.06), (-0.3, 1.38),
           (0.0, 1.48), (0.5, 1.49), (0.9, 1.41), (1.4, 1.2), (1.8, 1.14), (2.2, 1.1), (2.38, 0.95), (2.38, 0.5)]
    BOT = [(2.2, 0.36), (1.88, 0.4)] + [(1.3 + 0.55 * math.cos(math.radians(a)), 0.45 + 0.55 * math.sin(math.radians(a)))
                                         for a in range(10, 180, 17)] + \
          [(0.7, 0.3), (-0.75, 0.25)] + [(-1.35 + 0.55 * math.cos(math.radians(a)), 0.45 + 0.55 * math.sin(math.radians(a)))
                                         for a in range(10, 180, 17)] + [(-1.95, 0.3), (-2.15, 0.3)]
    PROF = TOP + BOT

    def slab(name, prof, x, m, shrink=0.0):
        cy = sum(p[0] for p in prof) / len(prof); cz = sum(p[1] for p in prof) / len(prof)
        vs = [(x, y + (cy - y) * shrink * 0.35, z + (cz - z) * shrink) for y, z in prof]
        me = bpy.data.meshes.new(name)
        me.from_pydata(vs, [], [list(range(len(vs)))])
        o = D.link(bpy.data.objects.new(name, me))
        o.data.materials.append(m)
        o.parent = g_far
        return o
    slab("fatslab", PROF, 0.03, FAT)
    slab("fleshslab", PROF, 0.02, FLESH, shrink=0.12)

    # ---- organs (car coords: nose -Y, cabin y≈-0.3..1.8 z≈1.0..1.45, hood y≈-2.2..-0.6)
    def organ(o):
        o.parent = g_far
        return o

    brain = organ(D.sphere("brain", 1.0, (0, 0.55, 1.08), m=BRAIN, seg=64, rings=32))
    brain.scale = (0.34, 0.62, 0.3)
    tex = bpy.data.textures.new("brainfold", "MARBLE")
    tex.noise_scale, tex.turbulence, tex.marble_type = 0.22, 9.0, "SHARPER"
    sub = brain.modifiers.new("sub", "SUBSURF"); sub.levels = sub.render_levels = 2
    dm = brain.modifiers.new("fold", "DISPLACE"); dm.texture, dm.strength, dm.mid_level = tex, -0.06, 0.0
    dm.texture_coords = "LOCAL"
    fis = organ(D.box("fissure", (0.02, 1.1, 0.04), (-0.34 * 0.98 + 0.33, 0.55, 1.37), m=DARK))   # mid-line groove
    fis.location = (0.0, 0.55, 1.36)
    stem = organ(tube("brainstem", [(0, 0.85, 0.85), (0, 1.0, 0.6), (0, 1.15, 0.42)], 0.07, BRAIN))
    spine = organ(tube("spine", [(0, 1.15, 0.42), (0, 1.6, 0.4), (0, 2.1, 0.45)], 0.05, FAT))

    # eyeball behind the windshield (looks out the front)
    eye = organ(D.sphere("eye", 0.2, (0.0, -0.32, 1.17), m=EYEW))
    iris = organ(D.sphere("iris", 0.11, (0.0, -0.46, 1.17), m=IRIS)); iris.scale = (1, 0.35, 1)
    pup = organ(D.sphere("pup", 0.06, (0.0, -0.5, 1.17), m=PUP)); pup.scale = (1, 0.35, 1)
    optic = organ(tube("optic", [(0, -0.15, 1.15), (0, 0.05, 1.0), (0, 0.2, 1.02)], 0.035, nmat("optic", "#e0c7a0")))

    # engine block + heart with veins (hood)
    eng = organ(D.box("engine", (0.5, 0.75, 0.32), (0.0, -1.35, 0.62), m=METAL, bevel=0.03))
    for i in range(4):
        organ(D.cyl(f"piston{i}", 0.07, 0.25, (0.0, -1.62 + i * 0.18, 0.86), m=CHROME))
    heart = organ(D.sphere("heart", 0.22, (0.0, -0.42, 0.6), m=HEART, seg=40, rings=20))
    heart.scale = (0.9, 1.0, 1.15)
    aorta = organ(tube("aorta", [(0, -0.42, 0.78), (0, -0.6, 0.95), (0, -0.95, 0.85), (0, -1.1, 0.8)], 0.06, HEART))
    vein = organ(tube("vein", [(0, -0.3, 0.45), (0, -0.7, 0.36), (0, -1.15, 0.42)], 0.045, VEIN))
    fuel = organ(tube("fuel", [(0, -0.25, 0.62), (0, 0.15, 0.5), (0, 0.6, 0.45)], 0.04, GAS))
    for k in range(70):                                  # heartbeat 90 bpm
        f = T(k * 0.62)
        D.key(heart, "scale", f, (0.9, 1.0, 1.15))
        D.key(heart, "scale", f + 3, (1.08, 1.2, 1.38))
        D.key(heart, "scale", f + 7, (0.9, 1.0, 1.15))
    # gasoline drops racing along the fuel line
    drops = []
    for k in range(6):
        dp = organ(D.sphere(f"drop{k}", 0.05, (0, -1.1, 0.42), m=GAS, seg=12, rings=8))
        cst = dp.constraints.new("FOLLOW_PATH")
        drops.append(dp)
    fpath = vein                                       # gasoline pulse = emissive drops along the vein path
    for k, dp in enumerate(drops):
        dp.constraints.clear()
        p0, p1 = Vector((0, -0.3, 0.45)), Vector((0, -1.15, 0.42))
        for c in range(0, 60):
            f = T(12.0 + c * 0.35 + k * 0.06)
            D.key(dp, "location", f, p0 + (p1 - p0) * 0.0 + Vector((-0.05, 0, 0)))
            D.key(dp, "location", f + 10, p1 + Vector((-0.05, 0, 0.02)))
        D.ease_all(dp, "LINEAR")
        dp.location = p0

    # intestines: a meandering pink tube in the lower body
    pts = []
    rows = 4
    for r in range(rows):
        z = 0.28 + r * 0.12
        ys = [0.1 + i * 0.16 for i in range(12)]
        if r % 2:
            ys = ys[::-1]
        for y in ys:
            pts.append((0.0 + random.uniform(-0.03, 0.03), y, z + random.uniform(-0.04, 0.04)))
    gut = organ(tube("guts", pts, 0.065, GUT, res=6))

    # mouth: tongue + teeth in the front bumper
    tongue = organ(D.sphere("tongue", 0.2, (0, -1.95, 0.32), m=GUM)); tongue.scale = (0.9, 1.4, 0.45)
    teeth = []
    for i in range(7):
        y = -2.17 + i * 0.03
        for z, sz in ((0.48, -1), (0.2, 1)):
            t_ = organ(D.cone(f"tooth{i}{z}", 0.04, 0.1, (0.0, -2.12 + i * 0.0, z), m=TOOTH, verts=8))
            t_.location = (0, -2.16 + i * 0.045 - 0.0, z)
            t_.rotation_euler = (0 if sz > 0 else math.pi, 0, 0)
            teeth.append(t_)

    # laser slicing line (hook)
    laser = D.box("laser", (0.012, 5.6, 0.012), (-0.02, 0.05, 1.9), m=LASER)
    D.key(laser, "location", 1, (-0.02, 0.05, 2.4))
    D.key(laser, "location", T(1.2), (-0.02, 0.05, 1.7))
    D.key(laser, "location", T(2.6), (-0.02, 0.05, -0.05))
    D.key(laser, "scale", T(2.6), (1, 1, 1))
    D.key(laser, "scale", T(2.7), (0, 0, 0))
    # near half: lifts and flies toward the camera side then out of frame (on "machines")
    D.key(g_near, "location", T(2.75), (0, 0, 0))
    D.key(g_near, "rotation_euler", T(2.75), (0, 0, 0))
    D.key(g_near, "location", T(3.25), (-5.5, -0.6, 2.4))
    D.key(g_near, "rotation_euler", T(3.25), (0.4, -1.2, 0.5))
    D.key(g_near, "location", T(3.4), (-30, 0, 9))
    # organs only exist once the car is open
    for o in g_far.children:            # organs + flesh slab poke through the shell: invisible until the cut opens
        if o.type in ("MESH", "CURVE") and not o.name.startswith("mcq_"):
            o.hide_render = True; o.keyframe_insert("hide_render", frame=1)
            o.hide_render = False; o.keyframe_insert("hide_render", frame=T(2.75))

    # ---- shots
    # hook: low push on the face, laser comes down, near half flies off
    shot(guts, "c_hook", 0.0, 2.75, (-3.6, -5.8, 0.9), (-2.7, -4.6, 1.0), (0, -0.9, 0.8), (0, -0.6, 0.85), 30, 34)
    shot(guts, "c_open", 2.75, v(3.31), (-7.5, -0.6, 1.4), (-6.8, -0.3, 1.5), (0, 0.1, 0.75), (0, 0.1, 0.75), 30, 32,
         shake=0.01)
    shot(guts, "c_top", v(4.22), v(5.45), (-3.0, -3.6, 3.4), (-3.2, -2.4, 3.0), (0, 0.2, 0.8), (0, 0.4, 0.8), 28, 30)
    shot(guts, "c_inside", v(3.31), v(4.22), (-5.6, -0.4, 1.3), (-3.6, 0.2, 1.25), (0, 0.15, 0.8), (0, 0.4, 0.95), 32, 36)
    # BRAIN reveal: snap zoom
    shot(guts, "c_brain", v(5.45), v(7.58), (-2.1, 0.55, 1.2), (-1.6, 0.55, 1.15), (0, 0.55, 1.1), (0, 0.55, 1.1), 50, 62,
         shake=0.02)
    shot(guts, "c_wind", v(7.58), v(9.44), (-2.4, -1.4, 1.45), (-2.2, -0.9, 1.4), (0, 0.1, 1.15), (0, 0.25, 1.1), 40, 44)
    shot(guts, "c_engine", v(12.2), v(13.56), (-2.2, -1.2, 0.75), (-1.9, -1.0, 0.75), (0, -1.1, 0.65), (0, -0.95, 0.65),
         40, 46)
    shot(guts, "c_gas", v(14.97), v(16.75), (-1.5, -0.55, 0.6), (-1.35, -0.95, 0.55), (0, -0.7, 0.48), (0, -0.85, 0.45), 38, 42)
    shot(guts, "c_heart", v(13.56), v(14.97), (-1.6, -0.45, 0.7), (-1.3, -0.6, 0.62), (0, -0.55, 0.6), (0, -0.6, 0.55),
         50, 56)
    shot(guts, "c_gut2", v(18.16), v(19.6), (-0.9, 1.7, 0.36), (-0.8, 1.1, 0.42), (0, 0.7, 0.45), (0, 0.4, 0.45), 28, 30, shake=0.01)
    shot(guts, "c_gut", v(16.75), v(18.16), (-2.0, 0.3, 1.5), (-1.7, 0.6, 0.6), (0, 0.4, 0.9), (0, 0.6, 0.48), 40, 46)
    shot(guts, "c_end", v(38.6), END, (-3.2, 0.1, 1.3), (-1.9, 0.5, 1.2), (0, 0.4, 1.0), (0, 0.55, 1.1), 36, 50, shake=0.015)

# ================================================================ STRETCH set: intestines for metres
stretch = L.new_set("STRETCH")
with L.building(stretch):
    Z.void(stretch, edge="#c96f86", centre="#ffe3ea", glow=0.6)
    L.post(stretch, bloom=0.25, vignette=0.25)
    pts = [(0, 0, 0.35)]
    for i in range(1, 30):
        pts.append((math.sin(i * 1.3) * 0.35, -i * 0.7, 0.35 + abs(math.sin(i * 0.7)) * 0.15))
    long_gut = tube("longgut", pts, 0.15, GUT, res=8)
    long_gut.data.bevel_factor_mapping_end = "SPLINE"
    long_gut.data.bevel_factor_end = 0.0
    long_gut.data.keyframe_insert("bevel_factor_end", frame=T(v(19.6)))
    long_gut.data.bevel_factor_end = 1.0
    long_gut.data.keyframe_insert("bevel_factor_end", frame=T(v(21.29)))
    # ruler ticks every metre, numbers pop as the gut passes
    for i in range(1, 15):
        tk = D.box(f"tick{i}", (0.6, 0.03, 0.01), (0.9, -i * 1.4, 0.01), m=CHALK)
        num = D.text3d(f"m{i}", f"{i}m", 0.32, (1.5, -i * 1.4, 0.02), TAPE, extrude=0.02, font=FONT, rot=(0, 0, -math.pi / 2))
    shot(stretch, "c_stretch", v(19.6), v(21.29), (-1.9, 1.6, 1.5), (-2.1, -15.5, 1.9), (0, -1.5, 0.3), (0, -18, 0.3), 30, 28)

# ================================================================ FACE set: eyelids, mouth, pit stop
face = L.new_set("FACE")
with L.building(face):
    Z.void(face)
    L.post(face, bloom=0.3, vignette=0.22)
    g_f, fp = car("mcqF")
    tires = split_tires(fp["tires"])
    for t_ in tires:
        t_.parent = g_f
    # eyelid: a red shell slab that slides down over the windshield eyes (blink on "eyelids")
    lid = D.box("lid", (1.5, 0.05, 0.5), (0, -0.6, 1.62), m=SKIN_RED, bevel=0.04)
    lid.rotation_euler = (math.radians(-62), 0, 0)
    lid.parent = g_f
    lid.hide_render = True
    up_, dn_ = Vector((0, -0.42, 1.62)), Vector((0, -0.62, 1.22))
    D.key(lid, "location", 1, up_)
    D.key(lid, "scale", 1, (0, 0, 0)); D.key(lid, "scale", T(v(10.9)), (0, 0, 0)); D.key(lid, "scale", T(v(10.9)) + 1, (1, 1, 1))
    D.key(lid, "scale", T(v(11.4)) + 8, (1, 1, 1)); D.key(lid, "scale", T(v(11.4)) + 9, (0, 0, 0))
    for tb in (v(10.99), v(11.4)):
        D.key(lid, "location", T(tb), up_)
        D.key(lid, "location", T(tb) + 3, dn_)
        D.key(lid, "location", T(tb) + 7, up_)
    # mouth: dark cavity + teeth that pop on "teeth"
    mouth = D.sphere("mouth", 0.5, (0, -2.19, 0.42), m=DARK); mouth.scale = (0.95, 0.1, 0.26); mouth.parent = g_f
    hide_until(mouth, v(22.01))
    fteeth = []
    for i in range(9):
        x = -0.4 + i * 0.1
        for z, rx in ((0.52, math.pi), (0.32, 0.0)):
            t_ = D.cone(f"ft{i}{z}", 0.045, 0.12, (x, -2.16, z), m=TOOTH, verts=8)
            t_.rotation_euler = (rx, 0, 0)
            t_.parent = g_f
            hide_until(t_, v(23.33))
            fteeth.append(t_)
    # pit crew: four T-posing strangers (Eric meshes, rest pose) pop in on "Four strangers"
    crew = []
    eric_ms = glb(A("eric.glb"))
    lo = Vector((min(min((o.matrix_world @ Vector(c)).x for c in o.bound_box) for o in eric_ms), 0, 0))
    pts_ = [(o.matrix_world @ Vector(c)) for o in eric_ms for c in o.bound_box]
    lo = Vector((min(p.x for p in pts_), min(p.y for p in pts_), min(p.z for p in pts_)))
    hi = Vector((max(p.x for p in pts_), max(p.y for p in pts_), max(p.z for p in pts_)))
    s = 1.8 / (hi.z - lo.z)
    for o in eric_ms:
        o.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))
    spots = [(-2.1, -1.75, -math.pi / 2), (2.1, -1.75, math.pi / 2), (-2.1, 1.8, -math.pi / 2), (2.1, 1.8, math.pi / 2)]
    for k, (x, y, rz) in enumerate(spots):
        cg = D.empty(f"crew{k}", (x, y, 0))
        cg.rotation_euler = (0, 0, rz + math.pi)
        for o in eric_ms:
            c = o.copy() if k else o
            if k:
                D.link(c)
            c.parent = cg
        hide_until(cg, v(26.02) + k * 0.12)
        crew.append(cg)
    # tyres get shot off one by one on "rip his feet off" (gunshot SFX in build.py)
    rip = [v(26.88), v(27.04), v(27.24), v(27.45)]
    for t_, tt in zip(sorted(tires, key=lambda o: (o.location.y, o.location.x)), rip):
        p0 = t_.location.copy()
        side = 1 if p0.x > 0 else -1
        D.key(t_, "location", T(tt), p0)
        D.key(t_, "rotation_euler", T(tt), (0, 0, 0))
        D.key(t_, "location", T(tt) + 10, p0 + Vector((side * 6, random.uniform(-1, 1), 2.5)))
        D.key(t_, "location", T(tt) + 24, p0 + Vector((side * 12, random.uniform(-2, 2), -2)))
        D.key(t_, "rotation_euler", T(tt) + 24, (random.uniform(4, 9), random.uniform(2, 6), 0))
    # car drops onto its belly once the feet are gone, eyes shake while awake
    D.key(g_f, "location", T(v(27.45)), (0, 0, 0))
    D.key(g_f, "location", T(v(27.45)) + 4, (0, 0, -0.38))
    for k in range(18):
        f = T(v(27.66)) + k * 2
        D.key(g_f, "rotation_euler", f, (0, random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02)))
    D.key(g_f, "rotation_euler", T(v(28.8)), (0, 0, 0))
    eyes = fp["eyes"]

    shot(face, "f_lids", v(9.44), v(12.2), (-1.4, -5.2, 1.5), (-1.0, -4.3, 1.45), (0, -0.6, 1.15), (0, -0.6, 1.2), 38, 46)
    shot(face, "f_teeth", v(23.14), v(24.5), (0.3, -4.6, 0.62), (0.2, -4.0, 0.5), (0, -2.1, 0.42), (0, -2.1, 0.42), 50, 55, shake=0.01)
    shot(face, "f_mouth", v(21.29), v(23.14), (0.9, -5.6, 0.75), (0.5, -4.4, 0.6), (0, -1.6, 0.6), (0, -1.8, 0.45), 40, 55,
         shake=0.004)
    shot(face, "f_crew", v(26.02), v(26.85), (0.1, -0.6, 9.5), (0.1, -0.5, 8.0), (0, 0, 0), (0, 0, 0), 26, 26)
    shot(face, "f_pit", v(24.5), v(26.02), (-6.5, -7.5, 4.2), (-6.0, -6.8, 3.8), (0, 0, 0.6), (0, 0, 0.6), 28, 30)
    shot(face, "f_rip", v(26.85), v(28.0), (-7.5, -8.5, 3.2), (-8.2, -9.4, 3.4), (0, 0, 0.6), (0, 0, 0.6), 24, 24, shake=0.03)
    shot(face, "f_awake", v(28.0), v(29.12), (0.6, -4.2, 1.0), (0.4, -3.6, 0.95), (0, -0.5, 0.95), (0, -0.5, 0.95), 50, 60,
         shake=0.02)
    shot(face, "f_thanks", v(29.12), v(30.86), (-5.0, -6.0, 1.6), (-4.6, -5.6, 1.5), (0, 0, 0.5), (0, 0, 0.5), 30, 32)

# ================================================================ CRASH set: wall, crime scene, Mater
crash = L.new_set("CRASH")
with L.building(crash):
    Z.void(crash, edge="#141c40", centre="#3b4d88", glow=0.6, ambient=0.7)
    L.post(crash, bloom=0.5, vignette=0.32, saturation=1.15)
    g_c, cp = car("mcqC", (0, 8, 0))
    D.sun("crash_moon", 3.5, (0.3, 0.6, -1.0), rgb=(0.75, 0.82, 1.0), angle=10.0)
    D.area_light("crash_top", 1800, (-3, 1, 7), (0, 1, 0), size=8, rgb=(0.85, 0.9, 1.0))
    wall = D.box("wall", (8, 1.2, 4), (0, -3.4, 2), m=WALL, bevel=0.02)
    # drive in fast, smash, crumple (squash) - "A car crash"
    D.key(g_c, "location", T(v(30.86)), (0, 8, 0))
    D.key(g_c, "location", T(v(32.63)), (0, -0.55, 0))
    D.ease_last(g_c, "LINEAR")
    D.key(g_c, "scale", T(v(32.63)), (1, 1, 1))
    D.key(g_c, "scale", T(v(32.63)) + 3, (1.08, 0.82, 1.05))
    # crime scene: car on its side, chalk outline on the floor, tape, red/blue strobes
    D.key(g_c, "location", T(v(33.1)) - 1, (0, -0.55, 0))
    D.key(g_c, "location", T(v(33.1)), (0.75, 0.8, 1.18))
    D.key(g_c, "rotation_euler", T(v(33.1)) - 1, (0, 0, 0))
    D.key(g_c, "rotation_euler", T(v(33.1)), (0, math.radians(-88), math.radians(8)))
    D.ease_all(g_c, "CONSTANT")
    outline = []
    for i in range(40):
        a = i / 40 * 2 * math.pi
        x, y = 2.0 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a)), 2.9 * math.copysign(abs(math.sin(a)) ** 0.6, math.sin(a))
        outline.append((x + 0.0, y + 0.8, 0.005))
    chalk = D.stroke("chalk", outline + [outline[0]], CHALK, width=0.045)
    hide_until(chalk, v(33.1))
    for k, (x, y) in enumerate(((-3.5, -1.8), (-3.5, 3.6), (5.0, 3.6))):
        post = D.cyl(f"post{k}", 0.05, 1.0, (x, y, 0.5), m=TAPE)
        hide_until(post, v(33.1))
    tp1 = D.box("tape1", (0.02, 5.4, 0.12), (-3.5, 0.9, 0.85), m=TAPE); hide_until(tp1, v(33.1))
    tp2 = D.box("tape2", (8.5, 0.02, 0.12), (0.75, 3.6, 0.85), m=TAPE); hide_until(tp2, v(33.1))
    for k in range(3):
        mk = D.cone(f"marker{k}", 0.16, 0.3, (1.0 + k * 1.1, -1.4 + k * 0.6, 0.15), m=TAPE, verts=4)
        hide_until(mk, v(33.4) + k * 0.12)
    red = D.area_light("red", 0, (-4, -2, 4), (0, 0, 0), size=3, rgb=(1, 0.05, 0.05))
    blue = D.area_light("blue", 0, (5, -2, 4), (0, 0, 0), size=3, rgb=(0.1, 0.25, 1))
    for k in range(30):
        f = T(v(33.1)) + k * 6
        for lt, ph in ((red, 0), (blue, 3)):
            lt.data.energy = 0; lt.data.keyframe_insert("energy", frame=f + ph - 1)
            lt.data.energy = 1500; lt.data.keyframe_insert("energy", frame=f + ph)
            lt.data.energy = 0; lt.data.keyframe_insert("energy", frame=f + ph + 3)
    # Mater: rolls in and drags McQueen away (hearse)
    mat_ms = glb(A("mater.glb"))
    g_m = group("mater", mat_ms, (2.6, 14, 0), rotz=math.pi)
    g_m.scale = (1.05,) * 3
    D.key(g_m, "location", T(v(34.76)), (2.4, 12, 0))
    D.key(g_m, "location", T(v(36.6)), (2.4, 7.0, 0))
    D.key(g_m, "location", T(v(37.2)), (2.4, 7.0, 0))
    D.key(g_m, "location", T(v(38.6)), (2.4, 12.5, 0))
    # hook up: McQueen follows Mater out after "hearse"
    D.key(g_c, "location", T(v(37.2)), (0.75, 0.8, 1.18))
    D.key(g_c, "location", T(v(38.6)), (0.75, 7.5, 1.18))
    D.ease_all(g_c, "LINEAR")
    D.ease_last(g_c, "LINEAR")

    shot(crash, "k_drive", v(30.86), v(32.63), (0.9, -2.6, 0.75), (0.7, -2.6, 0.7), (0, 6, 0.7), (0, 2, 0.6), 24, 22)
    shot(crash, "k_hit", v(32.63), v(33.1), (-4.0, 1.5, 1.4), (-4.4, 2.0, 1.6), (0, -1.0, 0.7), (0, -1.0, 0.7), 26, 26,
         shake=0.05)
    shot(crash, "k_scene", v(33.1), v(34.76), (0.0, 0.3, 13.0), (0.0, 0.4, 11.5), (0.0, 0.9, 0), (0.0, 0.9, 0), 24, 24)
    shot(crash, "k_mater2", v(35.85), v(37.16), (3.7, 1.6, 0.5), (3.7, 2.4, 0.5), (2.4, 6.5, 1.2), (2.4, 6.0, 1.2), 26, 26)
    shot(crash, "k_mater", v(34.76), v(35.85), (-5.5, -3.0, 1.8), (-5.0, -2.5, 1.7), (1.5, 3.5, 0.8), (1.8, 5.0, 0.9), 28, 30)
    shot(crash, "k_hearse", v(37.16), v(38.6), (9.0, 1.0, 4.5), (9.0, 4.0, 4.5), (1.5, 5.0, 0.8), (1.5, 8.5, 0.8), 20, 20)

# ---------------------------------------------------------------- the timeline lives on the GUTS scene's markers;
# render.py renders (scene, f0, f1) jobs, so every set just needs its own markers (added by shot()).
import json
upd()
json.dump(sorted(SHOTS, key=lambda s: s[1]), open(os.path.join(HERE, "out", "shots.json"), "w"))
for sc in bpy.data.scenes:
    sc.frame_end = T(END) - 1
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SHOTS", len(SHOTS))
