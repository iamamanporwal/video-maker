"""blender -b -P scene.py -- <shot> <out.blend>: cash shots for "Where did GTA 6's billion dollars go?" (agent A).

Shots (1080x1920, 30 fps): rocket 4.8 s | cashrain 6.0 s | vault 4.6 s | printer 5.9 s.
Cash = real $100 bills (public/img/bill_front.jpg, public domain) on bent/curled grid meshes, instanced by
particle systems (baked into the .blend). Every shot has a PRE-roll so frame 1 is already in motion: the render
range is PRE+1 .. PRE+NF (build.py renumbers). Logos: Rockstar Games / Take-Two SVGs imported as extruded curves.
"""
import math, os, random, sys
import bpy, bmesh
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "src", "reelforge", "blender"))
import director as D
import look as L

args = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = args[0], args[1]
DUR = {"rocket": 4.8, "cashrain": 6.0, "vault": 4.6, "printer": 5.9}[SHOT]
PRE = {"rocket": 40, "cashrain": 240, "vault": 20, "printer": 90}[SHOT]
NF = int(round(DUR * 30))
H = D.hex_lin
random.seed(7)

sc = D.reset(frames=PRE + NF)
D.fast_eevee(sc, samples=16, look="AgX - Punchy")
sc.name = SHOT


def F(sec):
    """Shot seconds → scene frame (shot t=0 is frame PRE+1)."""
    return PRE + 1 + int(round(sec * 30))


BILL = os.path.join(PROJ, "public", "img", "bill_front.jpg")
BILL_W, BILL_H = 0.156, 0.066


# ================================================================ materials

def bill_mat():
    m = bpy.data.materials.get("bill")
    if m:
        return m
    m = bpy.data.materials.new("bill")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(BILL, check_existing=True)
    tex.interpolation = "Cubic"
    uv = nt.nodes.new("ShaderNodeUVMap")
    nt.links.new(uv.outputs[0], tex.inputs[0])
    # back side: same print, mirrored feel via a green/grey tint (no reverse scan available)
    back = nt.nodes.new("ShaderNodeMix")
    back.data_type, back.blend_type = "RGBA", "MULTIPLY"
    back.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs[0], back.inputs[6])
    back.inputs[7].default_value = (0.55, 0.8, 0.58, 1)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(tex.outputs[0], mix.inputs[6])
    nt.links.new(back.outputs[2], mix.inputs[7])
    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type, tint.blend_type = "RGBA", "MULTIPLY"
    tint.inputs[0].default_value = 1.0
    nt.links.new(mix.outputs[2], tint.inputs[6])
    tint.inputs[7].default_value = (0.78, 0.92, 0.8, 1)
    sat = nt.nodes.new("ShaderNodeHueSaturation")
    sat.inputs["Saturation"].default_value = 1.1
    nt.links.new(tint.outputs[2], sat.inputs["Color"])
    nt.links.new(sat.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.58
    b.inputs["Specular IOR Level"].default_value = 0.35
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = 0.3
    m.use_backface_culling = False
    return m


def edge_mat():
    m = bpy.data.materials.get("paper_edge")
    if m:
        return m
    m = D.mat("paper_edge", H("#E6E1C9"), rough=0.8)
    nt = m.node_tree
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type, w.bands_direction = "BANDS", "Z"
    w.inputs["Scale"].default_value = 60
    w.inputs["Distortion"].default_value = 1.5
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*H("#B9B79E"), 1)
    ramp.color_ramp.elements[1].color = (*H("#F2EED8"), 1)
    nt.links.new(w.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return m


def band_mat():
    return bpy.data.materials.get("band") or L.plastic("band", H("#E2A11B"), rough=0.4, coat=0.2)


def gold_mat(name="gold", rgb="#FFB52E", rough=0.22):
    m = D.mat(name, H(rgb), rough=rough, metal=1.0)
    return m


def glow(name, rgb, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*rgb, 1)
    e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs[0])
    return m


# ================================================================ geometry

def bill_mesh(name, scale=1.0, bend=0.0, curl=0.0, twist=0.0, nx=10, ny=3):
    """A $100 bill as a bent grid: bend = arc along the length, curl = lift of one corner, twist = along x."""
    w, h = BILL_W * scale, BILL_H * scale
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new()
    vs = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            u, v = i / nx, j / ny
            x, y = (u - 0.5) * w, (v - 0.5) * h
            z = bend * w * (math.sin(math.pi * u) - 0.5) + curl * w * (u ** 2) * v + twist * x * y / max(h, 1e-6) * 2
            vs[i, j] = bm.verts.new((x, y, z))
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
            for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = (a / nx, b / ny)
            f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bill_mat())
    return me


def plane(name, sx, sy, loc, rot=(0, 0, 0)):
    """Single quad with +Z normal (particle emitter that only emits one way)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0)], [], [(0, 1, 2, 3)])
    o = D.link(bpy.data.objects.new(name, me))
    o.location, o.rotation_euler = loc, rot
    return o


def bills_collection(scale=1.0, n=7, lie=False):
    """Collection of bill variants (not linked to the scene) for particle instancing. lie=True: bill normal along
    +X so NOR-aligned hair instances lie flat on the emitter surface."""
    c = bpy.data.collections.new(f"BILLS_{scale}_{lie}")
    rnd = random.Random(3)
    for k in range(n):
        me = bill_mesh(f"bill_{scale}_{k}", scale, bend=rnd.uniform(-0.18, 0.22), curl=rnd.uniform(-0.15, 0.25),
                       twist=rnd.uniform(-0.12, 0.12))
        o = bpy.data.objects.new(me.name, me)
        o.rotation_euler = (0, math.pi / 2, 0) if lie else (0, 0, 0)
        c.objects.link(o)
    return c


def add_box(bm, uvl, mtx, sx, sy, sz, mi_front, mi_side, matidx):
    """Box centred at origin (local), transformed by mtx; faces with local ±Y normals get mi_front + full UV."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    c = [Vector((x, y, z)) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
    V = [bm.verts.new(mtx @ p) for p in c]
    idx = lambda x, y, z: x * 4 + y * 2 + z  # noqa: E731
    quads = {
        "-Y": [idx(0, 0, 0), idx(1, 0, 0), idx(1, 0, 1), idx(0, 0, 1)],
        "+Y": [idx(1, 1, 0), idx(0, 1, 0), idx(0, 1, 1), idx(1, 1, 1)],
        "-X": [idx(0, 1, 0), idx(0, 0, 0), idx(0, 0, 1), idx(0, 1, 1)],
        "+X": [idx(1, 0, 0), idx(1, 1, 0), idx(1, 1, 1), idx(1, 0, 1)],
        "-Z": [idx(0, 1, 0), idx(1, 1, 0), idx(1, 0, 0), idx(0, 0, 0)],
        "+Z": [idx(0, 0, 1), idx(1, 0, 1), idx(1, 1, 1), idx(0, 1, 1)],
    }
    for k, q in quads.items():
        f = bm.faces.new([V[i] for i in q])
        if k in ("-Y", "+Y"):
            f.material_index = matidx[mi_front]
            for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                lp[uvl].uv = uv
        else:
            f.material_index = matidx[mi_side]
            for lp, uv in zip(f.loops, ((0, 0), (0.02, 0), (0.02, 0.02), (0, 0.02))):
                lp[uvl].uv = uv


def brick_object(name, placements, w, h, d, band=True):
    """One joined mesh of cash bricks. placements: list of 4x4 matrices (brick local: X=bill long side,
    Z=bill short side, Y=thickness/out of the face)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new()
    MI = {"bill": 0, "edge": 1, "band": 2}
    for M in placements:
        add_box(bm, uvl, M, w, d, h, "bill", "edge", MI)
        if band:
            add_box(bm, uvl, M, w * 0.13, d * 1.04, h * 1.03, "band", "band", MI)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in (bill_mat(), edge_mat(), band_mat()):
        me.materials.append(m)
    return D.link(bpy.data.objects.new(name, me))


def logo(svg, width, mats, extrude=0.03, skip_small=0.004, name="logo"):
    """Import an SVG as extruded curve layers (largest at the back) under an empty; returns the empty.
    mats: function(original_rgb) -> material."""
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=os.path.join(PROJ, "public", "logos", svg))
    new = [o for o in bpy.data.objects if o not in before and o.type == "CURVE"]
    dims = [max(o.dimensions.x, o.dimensions.y) for o in new]
    big = max(dims)
    # global bbox for centring
    pts = [o.matrix_world @ Vector(c) for o in new for c in o.bound_box]
    cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2
    cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2
    span = max(max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts))
    s = width / span
    root = D.empty(name)
    order = sorted([o for o, dm in zip(new, dims) if dm >= skip_small],
                   key=lambda o: -(o.dimensions.x * o.dimensions.y))
    dg = bpy.context.evaluated_depsgraph_get()
    for k, o in enumerate(order):
        o.data.dimensions = "2D"
        o.data.fill_mode = "BOTH"
        o.data.extrude = extrude / s
        o.data.bevel_depth = extrude * 0.25 / s
        o.data.bevel_resolution = 2
        rgb = tuple(o.data.materials[0].diffuse_color)[:3] if o.data.materials else (0, 0, 0)
        dg.update()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.materials.clear()
        me.materials.append(mats(rgb))
        ob = D.link(bpy.data.objects.new(f"{name}_{k}", me))
        ob.matrix_world = o.matrix_world
        ob.location -= Vector((cx, cy, 0))
        ob.location.z += k * extrude * 0.9 / s
        ob.parent = root
    for o in [o for o in bpy.data.objects if o not in before and o.type == "CURVE"]:
        bpy.data.objects.remove(o)
    for c in [c for c in bpy.data.collections if c.name.endswith(".svg")]:
        bpy.data.collections.remove(c)
    root.scale = (s, s, s)
    root.rotation_euler = (math.pi / 2, 0, 0)   # stand up: SVG XY → world XZ, facing -Y
    return root


def rockstar_mats(rgb):
    r, g, b = rgb
    if r > 0.9 and g > 0.9:
        return bpy.data.materials.get("logo_white") or L.plastic("logo_white", (0.95, 0.95, 0.95), rough=0.25, coat=0.5)
    if r > 0.8:
        return bpy.data.materials.get("logo_orange") or L.plastic("logo_orange", H("#FCAF17"), rough=0.2, coat=0.7)
    return bpy.data.materials.get("logo_black") or L.plastic("logo_black", (0.01, 0.01, 0.012), rough=0.15, coat=0.8)


def particles(obj, name, coll, count, f0, f1, life, vel, vel_rand, size=1.0, size_rand=0.3, ang=12.0,
              gravity=1.0, damping=0.0, emit_from="FACE", obj_factor=0.0):
    m = obj.modifiers.new(name, "PARTICLE_SYSTEM")
    ps = m.particle_system
    st = ps.settings
    st.name = name
    st.type, st.count, st.frame_start, st.frame_end = "EMITTER", count, f0, f1
    st.lifetime, st.lifetime_random = life, 0.35
    st.emit_from, st.use_emit_random = emit_from, True
    st.normal_factor, st.factor_random, st.object_factor = vel, vel_rand, obj_factor
    st.physics_type = "NEWTON"
    st.damping = damping
    st.effector_weights.gravity = gravity
    st.use_rotations, st.rotation_mode = True, "NOR"
    st.rotation_factor_random, st.phase_factor_random = 1.0, 2.0
    st.angular_velocity_mode, st.angular_velocity_factor = "RAND", ang
    st.use_dynamic_rotation = True
    st.render_type, st.instance_collection, st.use_collection_pick_random = "COLLECTION", coll, True
    st.particle_size, st.size_random = size, size_rand
    st.display_method = "DOT"
    obj.show_instancer_for_render = False
    obj.show_instancer_for_viewport = False
    ps.seed = random.randint(0, 9999)
    ps.point_cache.frame_start, ps.point_cache.frame_end = 1, PRE + NF
    return ps


def collider(o, damp=0.6, fric=0.8):
    o.modifiers.new("collision", "COLLISION")
    o.collision.damping_factor, o.collision.friction_factor = damp, fric
    o.collision.damping_random, o.collision.friction_random = 0.2, 0.2
    return o


def sky_world(stops, hdri="belfast_sunset_puresky", hdri_strength=0.6, horizon=-0.05, top=0.75):
    """Camera sees a vertical colour gradient (stops: [(pos, '#hex'), ...]); lighting comes from an HDRI."""
    w = L.hdri_world(sc, hdri, strength=hdri_strength)
    nt = w.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = horizon, top
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*H(stops[0][1]), 1)
    els[1].position, els[1].color = stops[-1][0], (*H(stops[-1][1]), 1)
    for p, c in stops[1:-1]:
        e = els.new(p)
        e.color = (*H(c), 1)
    nt.links.new(mr.outputs[0], ramp.inputs[0])
    cam_bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(ramp.outputs[0], cam_bg.inputs[0])
    cam_bg.inputs[1].default_value = 1.0
    lp, mix = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    old = out.inputs["Surface"].links[0].from_socket
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(old, mix.inputs[1])
    nt.links.new(cam_bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return w


def key_path(o, frames_vals, path="location", interp="LINEAR"):
    for f, v in frames_vals:
        D.key(o, path, f, v)
    for fc in D._fcurves(o.animation_data.action):
        if fc.data_path == path:
            for k in fc.keyframe_points:
                k.interpolation = interp


def shake(o, f0, frames, amp, path="location", seed=0):
    """Decaying camera kick on top of existing keys (base sampled first, then keyed offsets)."""
    rnd = random.Random(seed)
    fcs = {fc.array_index: fc for fc in D._fcurves(o.animation_data.action) if fc.data_path == path}
    base = [[fcs[i].evaluate(f0 + k) for i in range(3)] for k in range(frames + 1)]
    for k in range(frames + 1):
        a = amp * (1 - k / frames) ** 2
        setattr(o, path, Vector([base[k][i] + rnd.uniform(-a, a) for i in range(3)]))
        o.keyframe_insert(path, frame=f0 + k)


# ================================================================ ROCKET

def rocket_body():
    """Cash-brick rocket: 8 bricks per ring, 13 rings (staggered), gold nose, red fins, Rockstar plaque."""
    R, w, h, d, n, rows = 1.15, 0.92, 0.39, 0.26, 8, 13
    pl = []
    for r in range(rows):
        for k in range(n):
            a = (k + 0.5 * (r % 2)) / n * math.tau
            M = Matrix.Translation((R * math.cos(a), R * math.sin(a), 0.35 + r * (h + 0.012) + h / 2)) @ \
                Matrix.Rotation(a - math.pi / 2, 4, "Z")
            pl.append(M)
    body = brick_object("rocket_bricks", pl, w, h, d)
    top = 0.35 + rows * (h + 0.012)
    core = D.cyl("rocket_core", R - 0.05, top, (0, 0, top / 2), m=D.mat("core", H("#2A2F3A"), rough=0.4, metal=0.6), verts=32)
    nose = D.cone("rocket_nose", R + 0.18, 2.4, (0, 0, top + 1.2), m=gold_mat(), verts=48)
    ring = D.cyl("rocket_ring", R + 0.2, 0.22, (0, 0, top + 0.02), m=gold_mat("gold2", "#FF9A3C", 0.3), verts=48)
    ring2 = D.cyl("rocket_ring2", R + 0.2, 0.22, (0, 0, 0.3), m=bpy.data.materials["gold2"], verts=48)
    noz = D.cone("rocket_nozzle", 0.75, 0.75, (0, 0, -0.05), m=D.mat("nozzle", H("#202228"), rough=0.3, metal=1.0), verts=32)
    noz.rotation_euler = (math.pi, 0, 0)
    fins = []
    fm = L.plastic("fin", H("#FF2E63"), rough=0.25, coat=0.6)
    for k in range(4):
        a = k / 4 * math.tau + math.pi / 4
        f = D.box(f"fin{k}", (1.1, 0.12, 1.9), (0, 0, 0), m=fm)
        bm = bmesh.new()
        bm.from_mesh(f.data)
        for v in bm.verts:                       # sweep the fin: outer edge lower, top edge slanted
            if v.co.x > 0:
                v.co.z -= 0.55
                if v.co.z > 0:
                    v.co.z -= 0.6
        bm.to_mesh(f.data)
        bm.free()
        f.location = ((R + 0.5) * math.cos(a), (R + 0.5) * math.sin(a), 1.0)
        f.rotation_euler = (0, 0, a)
        fins.append(f)
    plaque = logo("Rockstar_Games_Logo.svg", 1.25, rockstar_mats, extrude=0.05, name="rs_logo")
    plaque.location = (0, -(R + d / 2 + 0.05), top * 0.62)
    parts = [body, core, nose, ring, ring2, noz, *fins]
    return parts, plaque, top


def flame_mat():
    m = bpy.data.materials.new("flame")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    out = nt.nodes["Material Output"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")          # generated z: 0 = tip (bottom), 1 = nozzle
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.0, (1.0, 0.98, 0.9, 1)
    e[1].position, e[1].color = 1.0, (*H("#FF3E9A"), 1)
    x = e.new(0.55)
    x.color = (*H("#FF7A1A"), 1)
    y = e.new(0.2)
    y.color = (*H("#FFD34D"), 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(ramp.outputs[0], em.inputs[0])
    em.inputs[1].default_value = 9.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    a = nt.nodes.new("ShaderNodeMapRange")
    a.inputs["From Min"].default_value, a.inputs["From Max"].default_value = 0.5, 1.0
    a.inputs["To Min"].default_value, a.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(sep.outputs["Z"], a.inputs["Value"])
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(a.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    m.surface_render_method = "DITHERED"
    return m


def rocket_z(t):
    return 0.0 if t <= 0 else 1.7 * t + 1.35 * t * t


def build_rocket():
    sky_world([(0.0, "#FF9A3C"), (0.2, "#FF4F8B"), (0.5, "#A03BE8"), (0.8, "#5B2A9A"), (1.0, "#3A1670")],
              hdri_strength=0.5, horizon=-0.03, top=1.0)
    L.post(sc, bloom=0.55, bloom_threshold=0.85, bloom_size=0.7, vignette=0.26, saturation=1.12)
    ground = D.box("ground", (400, 400, 0.2), (0, 0, -0.1), m=L.pbr("ground", "concrete_floor_02", scale=0.25,
                   tint=H("#4A3A55"), tint_amount=0.6, rough_mul=0.8))
    collider(ground)
    pad = D.cyl("pad", 4.5, 0.25, (0, 0, 0.12), m=L.pbr("pad", "metal_plate", scale=0.6, tint=H("#3A3F4A"), tint_amount=0.5))
    for k in range(4):                                    # launch-tower stubs (scale cues)
        a = k / 4 * math.tau + 0.4
        D.box(f"tower{k}", (0.35, 0.35, 3.2), (3.6 * math.cos(a), 3.6 * math.sin(a), 1.7),
              m=D.mat("tower", H("#E8303A"), rough=0.4, metal=0.5))
    # moon
    moon = D.sphere("moon", 46, (60, 330, 300), m=None, seg=64, rings=32)
    mm = L.pbr("moon", "dry_cracked_lake" if os.path.isdir(os.path.join(L.PH, "textures", "dry_cracked_lake")) else "concrete_floor_02",
               scale=0.03, tint=H("#FFE7C4"), tint_amount=0.7)
    bsdf = mm.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Emission Color"].default_value = (*H("#FFE2B8"), 1)
    bsdf.inputs["Emission Strength"].default_value = 1.4
    D.give(moon, mm)
    # light
    D.sun("key", 3.2, (-0.4, 1.0, -0.6), rgb=H("#FFB070"), angle=3)
    D.area_light("rim", 4000, (6, 10, 12), (0, 0, 6), size=8, rgb=H("#7A5CFF"))
    flame_light = D.link(bpy.data.objects.new("flamelight", bpy.data.lights.new("flamelight", "POINT")))
    flame_light.data.energy, flame_light.data.color, flame_light.data.shadow_soft_size = 60000, H("#FF8A2A"), 2.0

    parts, plaque, top = rocket_body()
    globals()["PART_NAMES"] = {p.name for p in parts} | {plaque.name}
    fl_m = flame_mat()
    coll_big = bills_collection(4.0)
    dirv = Vector((0.8, 0.6, 0))
    N_R = 13
    for i in range(N_R):
        root = D.empty(f"ROCKET_{i}")
        base = Vector((0, 0, 0)) + dirv * (11.0 * i) + Vector((random.uniform(-1, 1) if i else 0, 0, 0))
        delay = -0.9 if i == 0 else 0.25 + 0.17 * i + random.uniform(-0.05, 0.05)
        for p in parts + list(plaque.children) + [plaque]:
            if i == 0:
                if p.parent is None:
                    p.parent = root
                continue
        if i > 0:
            src = ROCKET0
            for ch in [c for c in src.children if c.name in PART_NAMES]:
                cp = ch.copy()
                D.link(cp)
                cp.parent = root
                for g in ch.children:
                    gc = g.copy()
                    D.link(gc)
                    gc.parent = cp
        # flame + emitter
        flame = D.cone(f"flame{i}", 0.62, 4.2, (0, 0, 0), m=fl_m, verts=32)
        flame.data.transform(Matrix.Translation((0, 0, 2.1)))   # wide base at the origin, tip +4.2
        flame.rotation_euler = (math.pi, 0, 0)                   # tip points down
        flame.parent = root
        flame.location = (0, 0, -0.3)
        em = plane(f"emit{i}", 0.9, 0.9, (0, 0, -0.45), rot=(math.pi, 0, 0))   # normal → down
        em.parent = root
        t_ign = delay - 0.5
        f_ign = max(1, F(t_ign))
        particles(em, f"exhaust{i}", coll_big, 3200 if i == 0 else 450, f_ign, PRE + NF, 55,
                  vel=10.0, vel_rand=9.0, size=1.0, size_rand=0.35, ang=10.0, gravity=1.0, damping=0.02)
        # flame grows at ignition, flickers smoothly
        for f in range(1, PRE + NF + 1, 3):
            t = (f - PRE - 1) / 30.0
            on = max(0.0, min(1.0, (t - t_ign) / 0.35))
            s = on * (1.0 + 0.12 * math.sin(f * 1.7 + i) + 0.06 * math.sin(f * 3.1))
            D.key(flame, "scale", f, (max(on, 0.001), max(on, 0.001), max(s, 0.001)))
        # rise
        base.z = 0.25
        root.location = base
        for f in range(1, PRE + NF + 1, 2):
            t = (f - PRE - 1) / 30.0
            z = rocket_z(t - delay)
            sway = 0.03 * math.sin(f * 0.25 + i) * min(1, z / 3)
            D.key(root, "location", f, base + Vector((sway, 0, z)))
            D.key(root, "rotation_euler", f, (0.0, sway * 0.4, 0.0))
        if i == 0:
            flame_light.parent = root
            flame_light.location = (0, 0, -1.8)
        # smoke billows at the pad
        if i < 4:
            sm = bpy.data.materials.get("smoke") or D.mat("smoke", H("#F3D2E6"), rough=1.0, emit=H("#FF8A3C"), emit_strength=0.25)
            for k in range(14 if i == 0 else 8):
                a = random.uniform(0, math.tau)
                b = D.ico(f"smoke{i}_{k}", 1.0, tuple(base + Vector((0, 0, 0.6))), m=sm, sub=4)
                disp = b.modifiers.new("d", "DISPLACE")
                tx = bpy.data.textures.get("cloudtex") or bpy.data.textures.new("cloudtex", "CLOUDS")
                tx.noise_scale = 0.6
                disp.texture, disp.strength = tx, 0.35
                f0 = max(1, F(delay - 0.3 + random.uniform(0, 0.4)))
                r_end = random.uniform(2.8, 5.0)
                p0 = base + Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, 0.8))
                p1 = base + Vector((math.cos(a) * r_end, math.sin(a) * r_end, random.uniform(0.8, 2.6)))
                D.key(b, "scale", 1, (0.01,) * 3)
                D.key(b, "scale", f0, (0.4,) * 3)
                D.key(b, "location", f0, p0)
                fe = PRE + NF
                sz = random.uniform(1.0, 1.7)
                D.key(b, "scale", fe, (sz, sz, sz * 0.8))
                D.key(b, "location", fe, p1)
        if i == 0:
            globals()["ROCKET0"] = root

    # ---- cameras
    c1, l1 = D.camera("cam_close", lens=19, dof=None)
    c1.location = (2.2, -9.5, 0.7)
    for f in range(1, PRE + NF + 1, 2):
        t = (f - PRE - 1) / 30.0
        z = rocket_z(t + 0.9)
        D.key(l1, "location", f, Vector((0, 0, 3.0 + z * 0.9)))
    D.key(c1, "location", 1, Vector((2.2, -9.5, 0.7)))
    D.key(c1, "location", F(3.2), Vector((2.6, -8.2, 0.9)))
    D.ease_all(c1)
    D.handheld(c1, strength=0.035, scale=4.0, seed=2)
    c2, l2 = D.camera("cam_wide", lens=17)
    D.move(c2, l2, F(3.2), PRE + NF, (-14, -30, 1.5), (-15, -32, 2.0), (26, 22, 15), (27, 23, 19))
    D.handheld(c2, strength=0.02, scale=6.0, seed=5)
    sc.camera = c1
    D.cut(sc, 1, c1)
    D.cut(sc, F(3.2), c2)


# ================================================================ CASH RAIN

def build_cashrain():
    sky_world([(0.0, "#2A1206"), (0.4, "#5A2A0C"), (0.75, "#8A4A12"), (1.0, "#3A1A08")], hdri="studio_small_09",
              hdri_strength=0.35, horizon=-1.0, top=1.0)
    L.post(sc, bloom=0.5, bloom_threshold=0.8, bloom_size=0.8, vignette=0.3, saturation=1.15)
    coll = bills_collection(2.8)
    em = plane("rain_emitter", 16, 16, (0, 0, 27), rot=(math.pi, 0, 0))   # normal down
    particles(em, "rain", coll, 6500, 1, PRE + NF, 900, vel=0.6, vel_rand=0.8, size=1.0, size_rand=0.3, ang=4.0,
              gravity=0.09, damping=0.012)
    bpy.ops.object.effector_add(type="TURBULENCE", location=(0, 0, 20))
    tb = bpy.context.active_object
    tb.field.strength, tb.field.size, tb.field.flow = 2.2, 3.0, 0.0
    tb.field.noise = 0.0
    # gold bokeh far behind
    bm_mats = [glow("bk_gold", H("#FFC24A"), 6), glow("bk_pink", H("#FF5FA2"), 5), glow("bk_or", H("#FF8A2A"), 6)]
    for k in range(90):
        a = random.uniform(0, math.tau)
        r = random.uniform(22, 40)
        D.ico(f"bokeh{k}", random.uniform(0.25, 0.7), (math.cos(a) * r, math.sin(a) * r, random.uniform(2, 30)),
              m=random.choice(bm_mats), sub=1)
    D.area_light("key", 9000, (-6, -5, 28), (0, 0, 14), size=10, rgb=H("#FFD49A"))
    D.area_light("rim", 4000, (7, 8, 14), (0, 0, 16), size=8, rgb=H("#FF8FC0"))
    D.area_light("front", 5000, (2, -9, 18), (0, 0, 16), size=10, rgb=H("#FFF4E0"))
    D.sun("fill", 1.2, (0.3, 0.2, -1), rgb=H("#FFB36B"))
    cam, look = D.camera("cam", lens=24, dof=2.2)
    cam.data.dof.aperture_fstop = 2.0
    for f in range(PRE + 1, PRE + NF + 1, 3):
        t = (f - PRE - 1) / 30.0
        ang = 0.25 * t
        z = 21.0 - 1.4 * t
        D.key(cam, "location", f, Vector((math.cos(ang) * 1.2, math.sin(ang) * 1.2 - 0.3, z)))
        lk = Vector((math.cos(ang + 1.9) * 3.2, math.sin(ang + 1.9) * 3.2, z - 1.3))
        D.key(look, "location", f, lk)
    sc.camera = cam


# ================================================================ VAULT

def build_vault():
    L.hdri_world(sc, "studio_small_09", strength=0.08, backdrop=H("#07070A"))
    L.post(sc, bloom=0.5, bloom_threshold=0.85, bloom_size=0.6, vignette=0.32, saturation=1.1)
    R = 2.2
    floor = D.box("floor", (40, 40, 0.2), (0, -6, -0.1), m=L.pbr("floor", "concrete_floor_02", scale=0.5,
                  tint=H("#3A3632"), tint_amount=0.4, rough_mul=0.55))
    collider(floor, damp=0.7, fric=0.9)
    wall = D.box("wall", (24, 0.8, 14), (0, 0.4, 6), m=L.pbr("wall", "metal_plate", scale=0.5, tint=H("#2E3540"), tint_amount=0.6))
    hole = D.cyl("hole", R + 0.05, 3, (0, 0.4, R + 0.05), rot=(math.pi / 2, 0, 0), verts=64)
    bo = wall.modifiers.new("hole", "BOOLEAN")
    bo.operation, bo.object = "DIFFERENCE", hole
    hole.hide_render = hole.hide_viewport = True
    steel = L.pbr("steel", "metal_plate", scale=1.2, tint=H("#8A919C"), tint_amount=0.4, rough_mul=0.6)
    frame = D.torus("frame", R + 0.18, 0.22, (0, -0.05, R + 0.05), rot=(math.pi / 2, 0, 0), m=steel)
    # inside the vault: glowing cash pallets
    inner = D.box("inner", (10, 0.2, 8), (0, 6, 4), m=D.mat("inner", H("#2A1A08"), rough=0.6))
    pl = []
    for sx in range(-3, 4):
        for sz in range(5):
            for sy in range(2):
                pl.append(Matrix.Translation((sx * 0.62 + (sz % 2) * 0.1, 2.6 + sy * 0.9, 0.14 + sz * 0.27)) @
                          Matrix.Rotation(math.pi / 2, 4, "X") @ Matrix.Rotation(random.uniform(-0.04, 0.04), 4, "Z"))
    brick_object("pallets", pl, 0.6, 0.26, 0.26)
    D.area_light("inside", 6000, (0, 1.6, 3.8), (0, 3, 0.5), size=3, rgb=H("#FFB347"))
    D.area_light("inside2", 2500, (-1.5, 1.5, 1.0), (0, 3, 0.8), size=2, rgb=H("#FFD27A"))
    # door
    pivot = D.empty("pivot", (-R, -0.05, R + 0.05))
    door_m = L.pbr("door", "metal_plate", scale=0.9, tint=H("#9AA3AE"), tint_amount=0.35, rough_mul=0.5)
    door = D.cyl("door", R, 0.55, (R, -0.25, 0), rot=(math.pi / 2, 0, 0), m=door_m, verts=96)
    D.smooth(door, bevel=0.04)
    door.parent = pivot
    rimg = D.torus("door_rim", R - 0.15, 0.06, (R, -0.53, 0), rot=(math.pi / 2, 0, 0), m=gold_mat("gold_d", "#E89A2E", 0.3))
    rimg.parent = pivot
    for k in range(14):
        a = k / 14 * math.tau
        b = D.cyl(f"bolt{k}", 0.09, 0.5, (R + (R - 0.3) * math.cos(a), -0.6, (R - 0.3) * math.sin(a)),
                  rot=(math.pi / 2, 0, 0), m=steel, verts=16)
        b.parent = pivot
    lg = logo("Rockstar_Games_Logo.svg", 1.75, rockstar_mats, extrude=0.06, name="vault_logo")
    lg.parent = pivot
    lg.location = (R, -0.56, 0.05)
    wheel = D.torus("wheel", 0.42, 0.045, (R + 1.4, -0.72, -1.05), rot=(math.pi / 2, 0, 0), m=bpy.data.materials["gold_d"])
    wheel.parent = pivot
    for k in range(3):
        sp = D.box(f"spoke{k}", (0.84, 0.05, 0.05), (0, 0, 0), m=bpy.data.materials["gold_d"])
        sp.parent = pivot
        sp.location, sp.rotation_euler = (R + 1.4, -0.72, -1.05), (0, k * math.pi / 3, 0)
    hub = D.cyl("hub", 0.12, 0.25, (R + 1.4, -0.7, -1.05), rot=(math.pi / 2, 0, 0), m=bpy.data.materials["gold_d"])
    hub.parent = pivot
    # door swing: open 62° → slam at 1.35 s → bounce
    for f, deg in [(1, -100), (F(0.25), -92), (F(1.35), 0), (F(1.45), -2.2), (F(1.58), 0)]:
        D.key(pivot, "rotation_euler", f, (0, 0, math.radians(deg)))
    fcs = D._fcurves(pivot.animation_data.action)
    for fc in fcs:
        for i, k in enumerate(fc.keyframe_points):
            k.interpolation = "BEZIER"
            if i == 1:
                k.easing = "EASE_IN"
                k.interpolation = "QUAD"
            if i == 2:
                k.interpolation = "SINE"
    # slam dust + a puff of bills from the seam
    dust_m = D.mat("dust", H("#9C8E80"), rough=1.0)
    dc = bpy.data.collections.new("DUST")
    for k in range(3):
        me = bpy.data.meshes.new(f"dust{k}")
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.04 + 0.02 * k)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(dust_m)
        dc.objects.link(bpy.data.objects.new(me.name, me))
    seam = D.torus("seam", R + 0.02, 0.05, (0, -0.7, R + 0.05), rot=(math.pi / 2, 0, 0))
    seam.hide_render = True
    particles(seam, "dust", dc, 700, F(1.33), F(1.45), 60, vel=1.6, vel_rand=2.2, size=1.0, size_rand=0.6, ang=3,
              gravity=0.25, damping=0.06)
    cb = bills_collection(1.6)
    particles(seam, "puff", cb, 60, F(1.33), F(1.4), 200, vel=2.5, vel_rand=3.0, size=1.0, ang=8, gravity=0.35,
              damping=0.04)
    # trail of bills on the floor leading off-left, and the one bill that slides out
    for k in range(46):
        u = k / 45
        p = Vector((0.4 - 4.2 * u + 0.5 * math.sin(u * 7), -0.75 - 4.0 * u, 0.006 + 0.002 * (k % 3)))
        me = bill_mesh(f"trail{k}", 1.9, bend=random.uniform(-0.05, 0.05), curl=random.uniform(0, 0.12))
        o = D.link(bpy.data.objects.new(me.name, me))
        o.location = p + Vector((random.uniform(-0.25, 0.25), random.uniform(-0.15, 0.15), 0))
        o.rotation_euler = (0, 0, random.uniform(-0.9, 0.9) - 0.6)
    hero = D.link(bpy.data.objects.new("hero_bill", bill_mesh("hero_bill", 2.2, bend=0.06, curl=0.1)))
    for f, p, rz in [(1, (0.15, 0.25, 0.008), 0.1), (F(2.75), (0.15, 0.25, 0.008), 0.1), (F(3.3), (0.0, -0.75, 0.012), -0.2),
                     (F(4.6), (-0.9, -2.3, 0.014), -0.7)]:
        D.key(hero, "location", f, Vector(p))
        D.key(hero, "rotation_euler", f, (0, 0, rz))
    D.ease_all(hero)
    # lights
    D.area_light("key", 1800, (-3.5, -5, 6.5), (0, 0, 2.2), size=3, rgb=H("#FFC27A"))
    D.area_light("rim", 1500, (4.5, -2.5, 4.5), (0, 0, 2.2), size=2, rgb=H("#4FD8FF"))
    D.area_light("floorfill", 350, (-2.5, -4.0, 1.5), (-1, -2.5, 0), size=3, rgb=H("#FFD9B0"))
    # camera: 3/4 on the door → slam shake → drops to the floor and follows the escaping bill
    cam, look = D.camera("cam", lens=24, dof=None)
    D.key(cam, "location", 1, Vector((-3.4, -8.6, 2.2)))
    D.key(look, "location", 1, Vector((0.6, 0, 2.2)))
    D.key(cam, "location", F(1.35), Vector((-2.8, -7.6, 2.1)))
    D.key(look, "location", F(1.35), Vector((0.3, 0, 2.15)))
    D.key(cam, "location", F(2.6), Vector((-2.6, -7.2, 2.0)))
    D.key(look, "location", F(2.6), Vector((0.2, 0, 2.0)))
    D.key(cam, "location", F(3.4), Vector((-0.9, -3.6, 0.55)))
    D.key(look, "location", F(3.4), Vector((0.0, -0.7, 0.0)))
    D.key(cam, "location", F(4.6), Vector((-2.4, -5.2, 0.42)))
    D.key(look, "location", F(4.6), Vector((-1.0, -2.4, 0.0)))
    D.ease_all(cam)
    D.ease_all(look)
    shake(cam, F(1.35), 10, 0.09, seed=3)
    sc.camera = cam


# ================================================================ PRINTER

def take_two_mats(rgb):
    return bpy.data.materials.get("t2_black") or L.plastic("t2_black", (0.008, 0.008, 0.01), rough=0.2, coat=0.6)


def build_printer():
    L.hdri_world(sc, "studio_small_09", strength=0.12, backdrop=H("#0B1210"))
    L.post(sc, bloom=0.45, bloom_threshold=0.85, bloom_size=0.6, vignette=0.3, saturation=1.12)
    floor = D.box("floor", (30, 30, 0.2), (0, 0, -0.1), m=L.pbr("floor", "concrete_floor_02", scale=0.5,
                  tint=H("#2E3A34"), tint_amount=0.5, rough_mul=0.6))
    collider(floor, damp=0.8, fric=0.95)
    D.box("backwall", (30, 0.3, 12), (0, 4.5, 6), m=L.pbr("bwall", "red_brick_03", scale=0.6, tint=H("#5A3A30"), tint_amount=0.3))
    paint = L.plastic("press_paint", H("#0F5C46"), rough=0.35, coat=0.5)
    brass = gold_mat("brass", "#D9A441", 0.28)
    dark = D.mat("press_dark", H("#16181C"), rough=0.35, metal=0.8)
    body = D.box("press_body", (3.2, 2.0, 1.9), (0, 1.0, 0.95), m=paint, bevel=0.05)
    D.box("press_top", (3.4, 2.2, 0.18), (0, 1.0, 1.95), m=brass, bevel=0.02)
    D.box("press_base", (3.6, 2.4, 0.22), (0, 1.0, 0.11), m=dark, bevel=0.02)
    rollers = []
    for k, (y, z, r) in enumerate([(0.45, 2.35, 0.36), (1.25, 2.35, 0.36), (0.85, 2.85, 0.3)]):
        ro = D.cyl(f"roller{k}", r, 3.0, (0, y, z), m=dark if k != 2 else brass, verts=40)
        ro.rotation_mode = "ZYX"
        rollers.append(ro)
        for f, ang in [(1, 0), (PRE + NF, (-1 if k % 2 else 1) * 26 * math.pi)]:
            D.key(ro, "rotation_euler", f, (0, math.pi / 2, ang))
        for fc in D._fcurves(ro.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
        for s_ in range(6):                                  # stripes so the spin reads
            a = s_ / 6 * math.tau
            st = D.box(f"stripe{k}_{s_}", (0.07, 0.07, 3.02), (0, 0, 0), m=brass if k != 2 else dark)
            st.parent = ro
            st.location = (r * math.cos(a), r * math.sin(a), 0)
    # paper sheet feeding over the rollers
    sheet = D.box("sheet", (2.6, 1.3, 0.01), (0, 0.85, 2.72), m=bill_mat())
    slot = D.box("slot", (2.0, 0.12, 0.16), (0, -0.02, 1.25), m=D.mat("slotglow", H("#0A0A0A"), rough=0.3, emit=H("#7CFFB0"), emit_strength=3))
    gauge_m = glow("gauge", H("#FF3E3E"), 6)
    for k in range(3):
        D.cyl(f"lamp{k}", 0.08, 0.06, (-1.2 + k * 0.25, -0.02, 1.7), rot=(math.pi / 2, 0, 0), m=gauge_m)
    D.cyl("sign_post_l", 0.05, 1.0, (-1.0, 1.0, 3.5), m=dark)
    D.cyl("sign_post_r", 0.05, 1.0, (1.0, 1.0, 3.5), m=dark)
    D.box("t2_plate", (2.3, 0.08, 1.15), (0, 0.95, 4.05), m=L.plastic("t2_white", (0.92, 0.92, 0.9), rough=0.3, coat=0.4), bevel=0.03)
    D.box("t2_frame", (2.45, 0.06, 1.3), (0, 0.99, 4.05), m=brass, bevel=0.02)
    t2 = logo("Take-Two_Interactive_Logo.svg", 1.9, take_two_mats, extrude=0.02, skip_small=0.0, name="t2_logo")
    t2.location = (0, 0.89, 4.05)
    # bill stream from the slot
    em = plane("printer_emit", 1.8, 0.06, (0, -0.1, 1.25), rot=(math.pi / 2, 0, 0))   # +Z normal → -Y
    cb = bills_collection(2.2)
    cb_lie = bills_collection(2.2, lie=True)
    ps = particles(em, "stream", cb, 1400, 1, PRE + NF, 400, vel=3.4, vel_rand=1.0, size=1.0, size_rand=0.15, ang=5,
                   gravity=1.0, damping=0.01)
    ps.settings.normal_factor = 3.4
    # growing pile
    pile = D.sphere("pile", 1.0, (0, -2.1, -0.15), seg=48, rings=24)
    pile.scale = (1.3, 1.1, 0.5)
    pm = D.mat("pile_base", H("#8FA888"), rough=0.8)
    D.give(pile, pm)
    hair = pile.modifiers.new("pilebills", "PARTICLE_SYSTEM").particle_system
    hs = hair.settings
    hs.type, hs.count, hs.hair_length = "HAIR", 2600, 1.0
    hs.emit_from, hs.use_emit_random = "FACE", True
    hs.render_type, hs.instance_collection, hs.use_collection_pick_random = "COLLECTION", cb_lie, True
    hs.particle_size, hs.size_random = 0.5, 0.25
    hs.use_rotations, hs.rotation_mode, hs.rotation_factor_random = True, "NOR", 0.35
    hs.phase_factor_random = 2.0
    hair.seed = 11
    pile.show_instancer_for_render = True
    for f, s in [(1, 0.55), (F(DUR), 1.35)]:
        D.key(pile, "scale", f, (1.3 * s, 1.1 * s, 0.5 * s))
    for fc in D._fcurves(pile.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    collider(pile, damp=0.9, fric=1.0)
    # flip calendar on the back wall: years 2018 → 2026
    paper = D.mat("calpaper", H("#F4F0E6"), rough=0.7)
    ink = D.mat("calink", H("#C8102E"), rough=0.4)
    D.box("cal_back", (1.75, 0.05, 1.95), (3.2, 2.7, 3.6), m=D.mat("calback", H("#1C1C1C"), rough=0.5))
    D.cyl("cal_ring", 0.05, 1.6, (3.2, 2.62, 4.46), rot=(0, math.pi / 2, 0), m=brass)
    years = list(range(2018, 2027))
    t_flip = [0.25 + k * 0.62 for k in range(len(years) - 1)]
    for k, yr in enumerate(years):
        hinge = D.empty(f"hinge{k}", (3.2, 2.65 - 0.004 * (len(years) - k), 4.45))
        pg = D.box(f"page{k}", (1.6, 0.012, 1.8), (0, 0, 0), m=paper)
        pg.parent = hinge
        pg.location = (0, 0, -0.9)
        tx = D.text3d(f"yr{k}", str(yr), 0.5, (0, 0, 0), ink, extrude=0.006, bevel=0.0)
        tx.parent = hinge
        tx.rotation_euler = (math.pi / 2, 0, 0)
        tx.location = (0, -0.014, -0.95)
        if k < len(years) - 1:
            tf = t_flip[k]
            D.key(hinge, "rotation_euler", 1, (0, 0, 0))
            D.key(hinge, "rotation_euler", F(tf), (0, 0, 0))
            D.key(hinge, "rotation_euler", F(tf + 0.22), (math.radians(-172), 0, 0))
    # lights
    D.area_light("key", 2600, (-3.5, -4.5, 5.5), (0, 0.5, 1.3), size=3, rgb=H("#FFC88A"))
    D.area_light("rim", 2200, (3.5, 3.0, 4.5), (0, 0.5, 1.5), size=2.5, rgb=H("#3FFFA8"))
    D.area_light("cal_spot", 220, (1.8, 0.0, 6.0), (3.2, 2.6, 3.6), size=1.2, rgb=H("#FFE2B0"))
    D.area_light("pile_fill", 900, (1.5, -5.5, 1.6), (0, -2, 0.3), size=3, rgb=H("#FFF0DC"))
    cam, look = D.camera("cam", lens=24, dof=None)
    D.move(cam, look, PRE + 1, PRE + NF, (-3.0, -6.4, 1.5), (-2.2, -5.3, 1.35), (1.2, 0.8, 2.4), (1.3, 0.9, 2.5))
    D.handheld(cam, strength=0.004, scale=30, seed=1)
    sc.camera = cam


# ================================================================ main

{"rocket": build_rocket, "cashrain": build_cashrain, "vault": build_vault, "printer": build_printer}[SHOT]()
sc.frame_start, sc.frame_end = 1, PRE + NF
sc.frame_set(1)
bpy.ops.ptcache.free_bake_all()
bpy.ops.ptcache.bake_all(bake=True)
sc["PRE"], sc["NF"] = PRE, NF
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT, "PRE", PRE, "NF", NF)
