"""Earth-at-night shots: hook (traffic goes red), uk (record spike), edges (servers pop worldwide), wave (midnight rolls).

blender -b -P globe.py -- <shot> <out.blend> <seconds>
"""
import math, os, random, sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403,E402

shot, blend, dur = sys.argv[sys.argv.index("--") + 1:][:3]
s, NF = start(float(dur), samples=24, raytrace=False)
random.seed(7)

CITIES = {"london": (51.5, -0.1), "newyork": (40.7, -74.0), "la": (34.0, -118.2), "saopaulo": (-23.5, -46.6), "tokyo": (35.7, 139.7),
          "sydney": (-33.9, 151.2), "mumbai": (19.1, 72.9), "delhi": (28.6, 77.2), "dubai": (25.2, 55.3), "paris": (48.9, 2.3),
          "berlin": (52.5, 13.4), "moscow": (55.8, 37.6), "lagos": (6.5, 3.4), "joburg": (-26.2, 28.0), "mexico": (19.4, -99.1),
          "toronto": (43.7, -79.4), "seoul": (37.6, 127.0), "singapore": (1.35, 103.8), "jakarta": (-6.2, 106.8), "cairo": (30.0, 31.2),
          "madrid": (40.4, -3.7), "chicago": (41.9, -87.6), "miami": (25.8, -80.2), "buenosaires": (-34.6, -58.4), "istanbul": (41.0, 29.0),
          "beijing": (39.9, 116.4), "shanghai": (31.2, 121.5), "hongkong": (22.3, 114.2), "bangkok": (13.8, 100.5), "seattle": (47.6, -122.3),
          "dallas": (32.8, -96.8), "stockholm": (59.3, 18.1), "rome": (41.9, 12.5), "bogota": (4.7, -74.1), "lima": (-12.0, -77.0),
          "nairobi": (-1.3, 36.8), "riyadh": (24.7, 46.7), "manila": (14.6, 121.0), "melbourne": (-37.8, 145.0), "edinburgh": (55.95, -3.2)}


def ll(lat, lon, r=1.0):
    la, lo = math.radians(lat), math.radians(lon)
    return Vector((r * math.cos(la) * math.cos(lo), r * math.cos(la) * math.sin(lo), r * math.sin(la)))


def unit(lat, lon):
    return ll(lat, lon).normalized()


# ------------------------------------------------------------------ per-shot staging
CFG = {
    "hook": dict(sun=(25, 95), cam0=(38, -28, 4.3), cam1=(47, -12, 2.55), spin=0.0),
    "uk": dict(sun=(10, 150), cam0=(47, -4, 1.75), cam1=(52, -2, 1.42), spin=0.0),
    "edges": dict(sun=(15, 60), cam0=(28, -95, 3.6), cam1=(30, -55, 3.3), spin=0.0),
    "wave": dict(sun=(0, 180), cam0=(22, 0, 3.9), cam1=(22, 0, 3.6), spin=150.0),
}[shot]
SUN = unit(*CFG["sun"])
MID = (-Vector((SUN.x, SUN.y, 0))).normalized()                 # centre of the night side on the equator
EAST = Vector((0, 0, 1)).cross(MID).normalized()                # direction places move as Earth spins (→ dawn)

# ------------------------------------------------------------------ world: stars
w = bpy.data.worlds.new("space")
try:
    w.use_nodes = True
except Exception:
    pass
s.world = w
w.node_tree.nodes.clear()
wn = NT(w.node_tree)
wout = wn.n("ShaderNodeOutputWorld")
noise = wn.n("ShaderNodeTexNoise", ins={"Scale": 900.0, "Detail": 0.0})
star = wn.maprange(noise.outputs[0], 0.77, 0.82, 0.0, 1.0)
star = wn.math("POWER", star, 2.0)
tw = wn.n("ShaderNodeTexNoise", ins={"Scale": 3.0})
bgc = wn.n("ShaderNodeBackground")
wn.set(bgc.inputs["Color"], wn.mix(tw.outputs[0], (0.75, 0.85, 1.0, 1), (1.0, 0.92, 0.8, 1)))
wn.set(bgc.inputs["Strength"], wn.math("MULTIPLY", star, 1.4))
wn.t.links.new(bgc.outputs[0], wout.inputs[0])

# ------------------------------------------------------------------ earth
bpy.ops.mesh.primitive_uv_sphere_add(segments=192, ring_count=96, radius=1.0)
earth = bpy.context.object
earth.name = "earth"
bpy.ops.object.shade_smooth()
m, nt, out = new_mat("earth")
uv = nt.n("ShaderNodeTexCoord")
day = nt.image(os.path.join(TEX, "8k_earth_daymap.jpg"), uv.outputs["UV"])
night = nt.image(os.path.join(TEX, "8k_earth_nightmap.jpg"), uv.outputs["UV"])
spec = nt.image(os.path.join(TEX, "spec3.jpg"), uv.outputs["UV"], colorspace="Non-Color")
geo = nt.n("ShaderNodeNewGeometry")
sunv = nt.n("ShaderNodeCombineXYZ", ins={"X": SUN.x, "Y": SUN.y, "Z": SUN.z})
ndl = nt.vmath("DOT_PRODUCT", geo.outputs["Normal"], sunv.outputs[0]).outputs["Value"]
nightfac = nt.maprange(ndl, -0.22, 0.06, 1.0, 0.0, smooth=True)
lum = nt.n("ShaderNodeRGBToBW", ins={"Color": night.outputs["Color"]}).outputs[0]
lum = nt.math("POWER", lum, 1.25)
p = nt.n("ShaderNodeBsdfPrincipled")
nt.set(p.inputs["Base Color"], nt.mix(1.0, day.outputs["Color"], (0.82, 0.9, 1.0, 1), "MULTIPLY"))
nt.set(p.inputs["Roughness"], nt.maprange(spec.outputs["Color"], 0.0, 1.0, 0.85, 0.32))
p.inputs["Specular IOR Level"].default_value = 0.35
warm = (1.0, 0.62, 0.25, 1)
ecol = warm
estr = 9.0 if shot == "uk" else 34.0
V_UNLOCK = nt.value(0.0)
if shot == "wave":
    eastv = nt.n("ShaderNodeCombineXYZ", ins={"X": EAST.x, "Y": EAST.y, "Z": EAST.z})
    nde = nt.vmath("DOT_PRODUCT", geo.outputs["Normal"], eastv.outputs[0]).outputs["Value"]
    passed = nt.maprange(nde, -0.015, 0.015, 0.0, 1.0)
    band = nt.maprange(nt.math("ABSOLUTE", nde), 0.0, 0.07, 1.0, 0.0, smooth=True)
    ecol = nt.mix(passed, warm, (0.12, 1.0, 0.38, 1))
    ecol = nt.mix(band, ecol, (0.75, 1.0, 0.85, 1))
    lum = nt.math("MULTIPLY", lum, nt.math("ADD", 1.0, nt.math("MULTIPLY", band, 5.0)))
nt.set(p.inputs["Emission Color"], ecol)
nt.set(p.inputs["Emission Strength"], nt.math("MULTIPLY", nt.math("MULTIPLY", lum, nightfac), estr))
nt.t.links.new(p.outputs[0], out.inputs[0])
earth.data.materials.append(m)

# clouds
bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1.006)
clouds = bpy.context.object
bpy.ops.object.shade_smooth()
m, nt, out = new_mat("clouds", blended=True)
uv = nt.n("ShaderNodeTexCoord")
ct = nt.image(os.path.join(TEX, "8k_earth_clouds.jpg"), uv.outputs["UV"], colorspace="Non-Color")
p = nt.n("ShaderNodeBsdfPrincipled", ins={"Base Color": (1, 1, 1, 1), "Roughness": 0.9})
nt.set(p.inputs["Alpha"], nt.math("MULTIPLY", nt.math("POWER", ct.outputs["Color"], 1.3), 0.85 if shot != "uk" else 0.35))
nt.t.links.new(p.outputs[0], out.inputs[0])
clouds.data.materials.append(m)
clouds.parent = earth
try:
    clouds.visible_shadow = False
except Exception:
    pass

# atmosphere rim
bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1.028)
atm = bpy.context.object
bpy.ops.object.shade_smooth()
m, nt, out = new_mat("atmo", blended=True)
geo = nt.n("ShaderNodeNewGeometry")
lw = nt.n("ShaderNodeLayerWeight", ins={"Blend": 0.22})
rim = nt.math("POWER", lw.outputs["Facing"], 2.6)
sunv = nt.n("ShaderNodeCombineXYZ", ins={"X": SUN.x, "Y": SUN.y, "Z": SUN.z})
ndl = nt.vmath("DOT_PRODUCT", geo.outputs["Normal"], sunv.outputs[0]).outputs["Value"]
lit = nt.maprange(ndl, -0.35, 0.35, 0.10, 1.0, smooth=True)
em = nt.n("ShaderNodeEmission", ins={"Color": (0.22, 0.5, 1.0, 1)})
nt.set(em.inputs["Strength"], nt.math("MULTIPLY", nt.math("MULTIPLY", rim, lit), 5.0))
tr = nt.n("ShaderNodeBsdfTransparent")
add = nt.n("ShaderNodeAddShader")
nt.t.links.new(em.outputs[0], add.inputs[0])
nt.t.links.new(tr.outputs[0], add.inputs[1])
nt.t.links.new(add.outputs[0], out.inputs[0])
atm.data.materials.append(m)
try:
    atm.visible_shadow = False
except Exception:
    pass

sun = light(s, "SUN", SUN * 10, 5.5, color=(1.0, 0.96, 0.9), target=(0, 0, 0), name="sun")
sun.data.angle = math.radians(1.0)

# ------------------------------------------------------------------ arcs (data in flight)
ARCMAT = {}


def arc_mat(name, color, strength):
    m, nt, out = new_mat(name)
    e = nt.n("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1)
    e.inputs[1].default_value = strength
    nt.t.links.new(e.outputs[0], out.inputs[0])
    ARCMAT[name] = e
    return m


def arc(a, b, mat, lift=None, thick=0.0022, n=40):
    va, vb = ll(*a), ll(*b)
    ang = va.angle(vb)
    lift = lift if lift is not None else 0.04 + 0.16 * (ang / math.pi)
    cd = bpy.data.curves.new("arc", "CURVE")
    cd.dimensions = "3D"
    sp = cd.splines.new("POLY")
    sp.points.add(n)
    for i in range(n + 1):
        t = i / n
        v = va.slerp(vb, t) * (1.004 + lift * math.sin(math.pi * t))
        sp.points[i].co = (v.x, v.y, v.z, 1)
    cd.bevel_depth, cd.bevel_resolution = thick, 2
    cd.use_fill_caps = True
    o = bpy.data.objects.new("arc", cd)
    o.data.materials.append(mat)
    link(o, s)
    o.parent = earth
    return o


def flow(o, period, phase, tail=0.35, start_f=1):
    """A streak travelling a→b, looping every `period` frames."""
    cd = o.data
    for f in range(1, NF + 1):
        if f < start_f:
            e = st = 0.0
        else:
            x = (((f - start_f) / period) + phase) % 1.0 * (1 + tail)
            e, st = min(1.0, x), max(0.0, x - tail)
        cd.bevel_factor_end, cd.bevel_factor_start = e, min(st, e)
        cd.keyframe_insert("bevel_factor_end", frame=f)
        cd.keyframe_insert("bevel_factor_start", frame=f)


def dot(lat, lon, r, mat, name="dot"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=r, location=ll(lat, lon, 1.004))
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    o.parent = earth
    return o


names = list(CITIES)
cam = camera(s, lens=50)


def campos(t, k="io"):
    a, b = CFG["cam0"], CFG["cam1"]
    e = ease(t, k)
    return ll(a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e)


if shot == "hook":
    # calm cyan traffic → at ~38 % everything surges red; shockwave ring from the UK
    _a = sys.argv[sys.argv.index('--') + 1:]
    T_RED = float(_a[3]) if len(_a) > 3 and float(_a[3]) > 0 else 0.36
    blue = arc_mat("arc_blue", (0.15, 0.75, 1.0), 14.0)
    hot = arc_mat("arc_hot", (1.0, 0.16, 0.05), 30.0)
    hubs = ["london", "paris", "berlin", "madrid", "newyork", "stockholm", "rome", "istanbul", "cairo", "lagos", "moscow", "toronto",
            "miami", "dubai", "edinburgh", "saopaulo", "chicago"]
    pairs = set()
    while len(pairs) < 46:
        a, b = random.sample(hubs, 2)
        pairs.add((a, b))
    for i, (a, b) in enumerate(sorted(pairs)):
        o = arc(CITIES[a], CITIES[b], blue)
        flow(o, random.uniform(34, 60), random.random(), tail=0.4)
    f_red = int(T_RED * NF)
    extra = [("london", c) for c in hubs if c != "london"] * 3 + [(random.choice(hubs), "london") for _ in range(40)]
    for i, (a, b) in enumerate(extra):
        ja = (CITIES[a][0] + random.uniform(-2, 2), CITIES[a][1] + random.uniform(-2, 2))
        jb = (CITIES[b][0] + random.uniform(-2, 2), CITIES[b][1] + random.uniform(-2, 2))
        o = arc(ja, jb, hot, thick=0.003, lift=random.uniform(0.03, 0.22))
        flow(o, random.uniform(12, 22), random.random(), tail=0.7, start_f=f_red + random.randint(0, 14))
    e = ARCMAT["arc_blue"]
    for f in range(1, NF + 1):
        k = ease((f - f_red) / 8.0)
        e.inputs[0].default_value = (0.15 + 0.85 * k, 0.75 - 0.6 * k, 1.0 - 0.95 * k, 1)
        e.inputs[1].default_value = 14 + 20 * k
        e.inputs[0].keyframe_insert("default_value", frame=f)
        e.inputs[1].keyframe_insert("default_value", frame=f)
    # shockwave rings from the UK
    ringm = emit_mat("ring", (1.0, 0.2, 0.06), 40.0)
    uk = unit(53.5, -1.5)
    for j in range(3):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.012, major_segments=96, minor_segments=8)
        r = bpy.context.object
        r.data.materials.append(ringm)
        r.rotation_euler = uk.to_track_quat("Z", "Y").to_euler()
        f0 = f_red + j * 9
        for f in range(1, NF + 1):
            x = (f - f0) / 34.0
            if x < 0 or x > 1:
                r.scale = (0, 0, 0)
                r.location = uk * 1.01
            else:
                ang = x * 0.55                                   # angular radius on the sphere
                rr = math.sin(ang)
                r.scale = (rr, rr, max(0.05, 1 - x) * 1.0)
                r.location = uk * (math.cos(ang) * 1.012)
            r.keyframe_insert("scale", frame=f)
            r.keyframe_insert("location", frame=f)
    hotdot = emit_mat("hotdot", (1.0, 0.25, 0.08), 80.0)
    d = dot(53.5, -1.5, 0.012, hotdot)
    key(d, "scale", lambda t, f: (0, 0, 0) if f < f_red else tuple([1.0 + 0.5 * math.sin(f * 0.9)] * 3), NF)
    red = light(s, "POINT", uk * 1.25, 0.0, color=(1.0, 0.15, 0.05), size=0.2, name="alarm")
    key(red.data, "energy", lambda t, f: 0.0 if f < f_red else 45.0 * (0.75 + 0.25 * math.sin(f * 0.8)), NF)
    shake = lambda t, f: 0.0 if f < f_red else 0.012 * math.sin(f * 2.3) * max(0.0, 1 - (f - f_red) / 24.0)  # noqa: E731
    for f in range(1, NF + 1):
        t = (f - 1) / (NF - 1)
        tgt = Vector((0, 0, 0)).lerp(uk * 0.55, ease(t))
        look_at(cam, campos(t), tgt, roll=shake(t, f) + math.radians(-6 + 5 * t))
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)

elif shot == "uk":
    # close on Britain at night: every town a download streak, one giant spike of light
    hot = arc_mat("arc_hot", (1.0, 0.3, 0.08), 7.0)
    towns = [(51.5, -0.1), (53.48, -2.24), (52.48, -1.9), (53.8, -1.55), (55.95, -3.2), (55.86, -4.25), (51.45, -2.6), (53.4, -3.0),
             (54.98, -1.6), (50.9, -1.4), (52.63, 1.3), (51.48, -3.18), (53.96, -1.08), (53.38, -1.47), (54.6, -5.93), (52.2, 0.12),
             (50.72, -3.53), (57.15, -2.1), (53.75, -0.34), (52.95, -1.15)]
    srcs = [(50.1, 8.7), (52.37, 4.9), (48.9, 2.3), (53.35, -6.26), (51.5, -0.1)]
    for i in range(70):
        a = random.choice(srcs)
        b = random.choice(towns)
        if a == b:
            continue
        b = (b[0] + random.uniform(-0.3, 0.3), b[1] + random.uniform(-0.3, 0.3))
        o = arc(a, b, hot, thick=0.0005, lift=random.uniform(0.008, 0.04), n=24)
        flow(o, random.uniform(14, 26), random.random(), tail=0.6)
    beam = emit_mat("beam", (1.0, 0.3, 0.08), 12.0)
    yk = unit(53.9, -1.3)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0014, depth=1.0, vertices=16)
    b = bpy.context.object
    b.data.materials.append(beam)
    b.rotation_euler = yk.to_track_quat("Z", "Y").to_euler()

    def grow(t, f):
        h = 0.02 + 0.33 * ease(min(1.0, t / 0.55), "out") + 0.01 * math.sin(f * 0.7)
        b.location = yk * (1.004 + h / 2)
        b.keyframe_insert("location", frame=f)
        return (1, 1, h)
    key(b, "scale", grow, NF)
    red = light(s, "POINT", yk * 1.08, 1.5, color=(1.0, 0.3, 0.08), size=0.05, name="glow")
    tgt = unit(53.6, -2.0)
    cam_path(cam, NF, lambda t: campos(t, "out"), lambda t: tgt * (0.98 + 0.06 * ease(t)), lambda t: math.radians(4 - 3 * t))

elif shot == "edges":
    # one origin → thousands of edge servers light up across the planet, wave by distance
    cy = arc_mat("arc_cy", (0.2, 0.85, 1.0), 16.0)
    dm = emit_mat("edge", (0.25, 1.0, 0.75), 30.0)
    origin = CITIES["newyork"]
    vo = ll(*origin)
    # one shared mesh of many dots, revealed by distance-from-origin through the shader (cheap: no per-dot keys)
    import bmesh
    bm = bmesh.new()
    pts = []
    for nme, (la, lo) in CITIES.items():
        for _ in range(26):
            g = random.gauss
            pts.append((la + g(0, 3.2), lo + g(0, 4.2)))
    for _ in range(260):
        la, lo = random.choice(list(CITIES.values()))
        pts.append((la + random.gauss(0, 9), lo + random.gauss(0, 12)))
    for la, lo in pts:
        la = max(-80, min(80, la))
        c = ll(la, lo, 1.005)
        r = random.uniform(0.0035, 0.007)
        mtx = __import__("mathutils").Matrix.Translation(c)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r, matrix=mtx)
    me = bpy.data.meshes.new("edges")
    bm.to_mesh(me)
    bm.free()
    eo = bpy.data.objects.new("edges", me)
    link(eo, s)
    eo.parent = earth
    m, nt, out = new_mat("edge_reveal")
    geo = nt.n("ShaderNodeNewGeometry")
    ov = nt.n("ShaderNodeCombineXYZ", ins={"X": vo.x, "Y": vo.y, "Z": vo.z})
    dist = nt.vmath("DISTANCE", geo.outputs["Position"], ov.outputs[0]).outputs["Value"]
    front = nt.value(0.0)
    on = nt.maprange(nt.math("SUBTRACT", front, dist), 0.0, 0.05, 0.0, 1.0)
    flash = nt.maprange(nt.math("ABSOLUTE", nt.math("SUBTRACT", front, dist)), 0.0, 0.12, 1.0, 0.0)
    em = nt.n("ShaderNodeEmission")
    nt.set(em.inputs["Color"], nt.mix(flash, (0.2, 1.0, 0.7, 1), (1, 1, 1, 1)))
    nt.set(em.inputs["Strength"], nt.math("MULTIPLY", on, nt.math("ADD", 22.0, nt.math("MULTIPLY", flash, 80.0))))
    tr = nt.n("ShaderNodeBsdfTransparent")
    mx = nt.n("ShaderNodeMixShader")
    nt.set(mx.inputs[0], on)
    nt.t.links.new(tr.outputs[0], mx.inputs[1])
    nt.t.links.new(em.outputs[0], mx.inputs[2])
    nt.t.links.new(mx.outputs[0], out.inputs[0])
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    eo.data.materials.append(m)
    key_sock(front, lambda t, f: 2.15 * ease(min(1.0, t / 0.8), "lin"), NF)
    for nme, c in CITIES.items():
        if nme == "newyork":
            continue
        d = (ll(*c) - vo).length
        o = arc(origin, c, cy, thick=0.0026)
        f0 = 1 + int(d / 2.15 * 0.8 * NF * 0.55)
        flow(o, max(16, NF * 0.38), 0.0, tail=1.0, start_f=f0)
    od = dot(origin[0], origin[1], 0.016, emit_mat("origin", (1.0, 0.75, 0.2), 90.0))
    cam_path(cam, NF, lambda t: campos(t, "lin"), lambda t: Vector((0, 0, 0.05)))

elif shot == "wave":
    # Earth time-lapse: cities cross the fixed midnight line and flip amber → green
    key(earth, "rotation_euler", lambda t, f: math.radians(-40 + CFG["spin"] * t), NF, index=2)
    linem = emit_mat("midline", (0.6, 1.0, 0.8), 26.0)
    cd = bpy.data.curves.new("mid", "CURVE")
    cd.dimensions = "3D"
    sp = cd.splines.new("POLY")
    n = 64
    sp.points.add(n)
    for i in range(n + 1):
        a = math.radians(-88 + 176 * i / n)
        v = (MID * math.cos(a) + Vector((0, 0, 1)) * math.sin(a)) * 1.035
        sp.points[i].co = (v.x, v.y, v.z, 1)
    cd.bevel_depth = 0.004
    link(bpy.data.objects.new("midline", cd), s).data.materials.append(linem)
    cpos = (MID * math.cos(math.radians(20)) + Vector((0, 0, 1)) * math.sin(math.radians(20)))
    side = EAST * -0.12
    cam_path(cam, NF, lambda t: (cpos + side * (1 - t)).normalized() * (CFG["cam0"][2] + (CFG["cam1"][2] - CFG["cam0"][2]) * ease(t)),
             lambda t: Vector((0, 0, 0.02)))

L.post(s, bloom=0.55, bloom_threshold=1.2, bloom_size=0.55, dispersion=0.004, vignette=0.28, saturation=1.1, contrast=0.06)
save(s, blend)
