"""blender -b -P scene.py -- <out.blend>: "This GitHub repo gives AI 94 Blender skills" (informative, no Vi3W outro).

Every set is built by following the installed blender-skills SKILL.md rules (that is the point of the video):
  BAD    h1    the no-skills attempt: grey boxes, one point light, a cube
  HALL   h2    horror-style: 1.4 m wide, 2.3 m ceiling, single flickering fluorescent, fog, sparse foreground
               (overturned chair, note, CRT glow), cold vs warm clash through an ajar door
  WALL   b1    94 skill tiles, coloured by category, fly in; camera pulls back
  CRATE  b2    hard-surface crate through the pipeline: blockout → hard surface → topology (wire) → UV checker →
               PBR materials → lighting (rim lights in)
  PIPE   b3    blender-director routing: prompt → director → hard-surface → uv-workflow → materials → export-pipeline
  STYLE  b4    one mushroom house: clay → lowpoly-style (decimate, flat) → anime-style (toon ramp + inverted hull) →
               voxel-style (block remesh) → horror-style (night fog, red window)
  MCP    b5    viewport-look set: the island assembles itself on a Blender grid (clay, axis lines)
  ISL    p2    the same island, finished: lowpoly + cozy-wholesome (warm key, rounded props, water)
  payoff p1-p4: HALL wide, CRATE hero, ISL, WALL backdrop for the install card, HALL door → lights out.
Times come from out/words.json (vo.py); VO_AT must match build.py.
"""
import json, math, os, random, re, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
import bpy
import director as D
import look as L

out = sys.argv[sys.argv.index("--") + 1]
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MONO = "/System/Library/Fonts/Menlo.ttc"
T, H = D.T, D.hex_lin
VO_AT = 0.15
VO = json.load(open(os.path.join(HERE, "out", "words.json")))
W, LN = VO["words"], VO["lines"]


def ws(key, i=0):
    return VO_AT + W[LN[key][0] + i][0]


def we(key, i=-1):
    a, b = LN[key]
    return VO_AT + W[(b if i == -1 else a + i + 1) - 1][1]


END = we("p4") + 1.3
random.seed(11)
base = D.reset(w=720, h=1280, frames=T(END))
D.fast_eevee(base, samples=10, look="AgX - Punchy")
SHOTS = []
REN = {"hip": "Hips", "spine_01": "Spine", "spine_02": "Spine1", "spine_03": "Spine2", "neck": "Neck", "head": "Head", "jaw": "Jaw"}
for _s, _S in (("l", "Left"), ("r", "Right")):
    REN |= {f"shoulder_{_s}": f"{_S}Shoulder", f"upperarm_{_s}": f"{_S}Arm", f"lowerarm_{_s}": f"{_S}ForeArm",
            f"hand_{_s}": f"{_S}Hand", f"upperleg_{_s}": f"{_S}UpLeg", f"lowerleg_{_s}": f"{_S}Leg", f"foot_{_s}": f"{_S}Foot"}
json.dump({"END": END}, open(os.path.join(HERE, "out", "timing.json"), "w"))


# ---------------------------------------------------------------- helpers
def flat(name, hexc, rough=0.8, emit=0.0, metal=0.0):
    return D.mat(name, H(hexc), rough=rough, metal=metal, emit=H(hexc) if emit else None, emit_strength=emit)


def shot(sc, name, t0, t1, loc0, loc1, at0, at1, lens0=24, lens1=None, shake=0.0):
    c, l = D.camera(name, lens0)
    D.move(c, l, T(t0), T(t1), loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    D.cut(sc, T(t0), c)
    SHOTS.append((sc.name, T(t0), T(t1) - 1))
    return c, l


def visible(o, spans):
    for x in [o] + list(o.children_recursive):
        x.hide_render = True
        x.keyframe_insert("hide_render", frame=1)
        for a, b in spans:
            x.hide_render = False
            x.keyframe_insert("hide_render", frame=max(1, T(a)))
            x.hide_render = True
            x.keyframe_insert("hide_render", frame=T(b))
        for fc in D._fcurves(x.animation_data.action):
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"


def spin(o, t0, t1, turns=0.5, z0=0.0):
    D.key(o, "rotation_euler", T(t0), (0, 0, z0))
    D.key(o, "rotation_euler", T(t1), (0, 0, z0 + turns * 2 * math.pi))
    for fc in D._fcurves(o.animation_data.action):
        if fc.data_path == "rotation_euler":
            for k in fc.keyframe_points:
                k.interpolation = "LINEAR"


def key_input(m, sock, frame, value, node="Principled BSDF"):
    s = m.node_tree.nodes[node].inputs[sock]
    s.default_value = value
    s.keyframe_insert("default_value", frame=frame)


def fog(sc, density, rgb=(0.6, 0.65, 0.7), bg=(0, 0, 0), bg_strength=0.0, anis=0.3):
    w = bpy.data.worlds.new(sc.name + "_w")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes["Background"].inputs[0].default_value = (*bg, 1)
    nt.nodes["Background"].inputs[1].default_value = bg_strength
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = density
    v.inputs["Color"].default_value = (*rgb, 1)
    v.inputs["Anisotropy"].default_value = anis
    nt.links.new(v.outputs[0], nt.nodes["World Output"].inputs["Volume"])
    sc.world = w
    sc.eevee.volumetric_end = 30
    sc.eevee.volumetric_tile_size = "8"
    return w


def obj_copy(o, mat=None):
    """Linked duplicate (shared mesh + animation) whose material is overridden per object."""
    c = o.copy()
    D.link(c)
    if mat and c.type == "MESH":
        for s in c.material_slots:
            s.link = "OBJECT"
            s.material = mat
    return c


# ================================================================ HALL: horror-style hospital corridor (v2)
# horror-style: familiar made wrong, single dominant source, 8:1 key:fill, fog for depth, 1-2 flickers only,
# sparse foreground storytelling (gurney, papers, one smear), warm-vs-cold clash through the far door.
# HALL is the context scene so the Eric rig poses evaluate (D.aim updates bpy.context.view_layer).
hall = L.new_set("HALL", main=True)
hall.eevee.taa_render_samples = 24
for k_, v_ in (("use_volumetric_shadows", True), ("volumetric_samples", 48), ("volumetric_light_clamp", 0.0)):
    if hasattr(hall.eevee, k_):
        setattr(hall.eevee, k_, v_)
hall.eevee.use_raytracing = True
hall.eevee.ray_tracing_method = "SCREEN"
with L.building(hall):
    hall_w = fog(hall, 0.022, rgb=H("#b9c8bf"), anis=0.55)
    LEN, HW, CH = 18.0, 0.8, 2.45
    floor_m = L.pbr("h_lino", "old_linoleum_flooring_01", scale=1.4, tint=H("#7d8a72"), tint_amount=0.45, rough_mul=0.35)
    mint = L.pbr("h_mint", "painted_plaster_wall", scale=1.2, tint=H("#6f9a86"), tint_amount=0.7)
    upper = L.pbr("h_upper", "plastered_wall", scale=1.0, tint=H("#b9b29a"), tint_amount=0.6)
    tile_m = L.pbr("h_ctile", "plastered_wall", scale=2.0, tint=H("#a8a593"), tint_amount=0.6)
    bar_m = flat("h_bar", "#5f625a", 0.5, metal=0.5)
    rail_m = flat("h_rail", "#6b4c33", 0.45)
    puddle = D.mat("h_puddle", H("#0d100e"), rough=0.03, spec=0.8)
    D.box("h_floor", (HW * 2 + 0.4, LEN + 2, 0.1), (0, LEN / 2, -0.05), floor_m)
    for k in range(0):
        p = D.box(f"h_pud{k}", (random.uniform(0.4, 0.9), random.uniform(0.6, 1.6), 0.002),
                  (random.uniform(-0.4, 0.4), 1.5 + k * 3.1, 0.001), puddle)
        p.rotation_euler.z = random.uniform(-0.4, 0.4)
    for sx in (-1, 1):
        D.box(f"h_wl{sx}", (0.1, LEN + 2, 1.05), (sx * (HW + 0.05), LEN / 2, 0.525), mint)
        D.box(f"h_wu{sx}", (0.1, LEN + 2, CH - 1.05), (sx * (HW + 0.05), LEN / 2, 1.05 + (CH - 1.05) / 2), upper)
        D.box(f"h_trim{sx}", (0.03, LEN + 2, 0.05), (sx * (HW - 0.01), LEN / 2, 1.06), bar_m)
        D.box(f"h_skirt{sx}", (0.03, LEN + 2, 0.12), (sx * (HW - 0.01), LEN / 2, 0.06), flat("h_sk", "#2f3a33", 0.6))
        D.cyl(f"h_rail{sx}", 0.025, LEN + 2, (sx * (HW - 0.07), LEN / 2, 0.9), rot=(math.pi / 2, 0, 0), m=rail_m, verts=10)
        for k, y in enumerate((3.4, 7.8, 12.2)):           # numbered doors with wire-glass windows
            dm = flat("h_dm", "#3e4a44", 0.55)
            D.box(f"h_df{sx}{k}", (0.06, 1.12, 2.16), (sx * (HW - 0.0), y, 1.08), bar_m)
            D.box(f"h_d{sx}{k}", (0.07, 0.96, 2.06), (sx * (HW - 0.015), y, 1.03), dm)
            lit = (sx, k) == (-1, 1)
            D.box(f"h_dw{sx}{k}", (0.075, 0.26, 0.36), (sx * (HW - 0.02), y, 1.5),
                  D.mat(f"h_win{sx}{k}", H("#1a2a22"), rough=0.1, emit=H("#7dffb0") if lit else None, emit_strength=1.4))
            D.text3d(f"h_dn{sx}{k}", str(100 + k * 2 + (sx > 0)), 0.09, (sx * (HW - 0.06), y, 1.85),
                     flat("h_num", "#d8d2bd", 0.6), extrude=0.003, bevel=0.0, font=FONT,
                     rot=(math.pi / 2, 0, -sx * math.pi / 2))
    # drop ceiling: T-bar grid, tiles, light panels, one missing tile + one hanging
    D.box("h_void", (HW * 2 + 0.4, LEN + 2, 0.05), (0, LEN / 2, CH + 0.5), flat("h_void_m", "#050605", 1.0))
    panels, PAN = [], {2.0: "fl", 6.6: "off", 11.2: "on", 15.8: "dim"}
    y = 0.0
    while y < LEN:
        for x in (-0.4, 0.4):
            if abs(y - 9.2) < 0.01 and x > 0:
                pass                                       # missing tile: dark hole
            elif abs(y - 13.8) < 0.01 and x < 0:
                t = D.box("h_hang", (0.58, 0.58, 0.015), (x - 0.05, y + 0.1, CH - 0.25), tile_m)
                t.rotation_euler = (math.radians(38), math.radians(8), 0)
            elif any(abs(y + 0.3 - py) < 0.35 for py in PAN) and x < 0:
                pass
            else:
                D.box(f"h_ct{y:.1f}{x}", (0.58, 0.58, 0.015), (x, y + 0.3, CH), tile_m)
        D.box(f"h_tb{y:.1f}", (HW * 2, 0.02, 0.03), (0, y, CH - 0.01), bar_m)
        y += 0.6
    D.box("h_tbx", (0.02, LEN, 0.03), (0, LEN / 2, CH - 0.01), bar_m)
    m_on = D.mat("h_pan_on", H("#e8fff2"), rough=0.4, emit=H("#dcffe9"), emit_strength=9)
    m_fl = D.mat("h_pan_fl", H("#e8fff2"), rough=0.4, emit=H("#dcffe9"), emit_strength=9)
    m_dim = D.mat("h_pan_dim", H("#e8fff2"), rough=0.4, emit=H("#dcffe9"), emit_strength=2.5)
    m_off = flat("h_pan_off", "#2b2e2a", 0.4)
    lights = {}
    for py, st in PAN.items():
        D.box(f"h_pan{py}", (1.18, 0.58, 0.02), (0, py, CH - 0.005), {"fl": m_fl, "on": m_on, "dim": m_dim, "off": m_off}[st])
        if st != "off":
            lights[st] = D.area_light(f"h_al{py}", {"fl": 110, "on": 120, "dim": 40}[st], (0, py, CH - 0.05), (0, py, 0),
                                      size=1.1, rgb=H("#cfffe0"))
    # far end: door ajar, hot orange room behind, EXIT sign
    D.box("h_back_l", (0.42, 0.1, CH), (-0.6, LEN, CH / 2), upper)
    D.box("h_back_r", (0.42, 0.1, CH), (0.6, LEN, CH / 2), upper)
    D.box("h_back_t", (1.8, 0.1, 0.35), (0, LEN, CH - 0.175), upper)
    door_piv = D.empty("h_door_piv", (-0.39, LEN - 0.02, 0))
    door = D.box("h_door", (0.78, 0.05, 2.08), (0.39, 0, 1.04), flat("h_door_m", "#3a2f27", 0.75))
    door.parent = door_piv
    door_piv.rotation_euler = (0, 0, math.radians(-78))
    D.area_light("h_fill", 18, (0, 8, CH - 0.3), (0, 8, 0), size=6, rgb=H("#9fc4b2"))
    rm = flat("h_room_m", "#7a3d1c", 0.9)
    D.box("h_room_back", (4, 0.1, 3.2), (0, LEN + 3.5, 1.5), rm)
    D.box("h_room_l", (0.1, 3.5, 3.2), (-2, LEN + 1.75, 1.5), rm)
    D.box("h_room_r", (0.1, 3.5, 3.2), (2, LEN + 1.75, 1.5), rm)
    D.box("h_room_f", (4, 3.5, 0.1), (0, LEN + 1.75, -0.05), flat("h_room_fl", "#3a2214", 0.8))
    D.box("h_room_c", (4, 3.5, 0.1), (0, LEN + 1.75, 3.05), rm)
    warm = D.area_light("h_warm", 900, (0.3, LEN + 2.6, 2.2), (0, LEN - 3, 0.9), size=1.0, rgb=H("#ff8a3a"))
    exit_m = D.mat("h_exit", H("#ff2a1a"), emit=H("#ff2a1a"), emit_strength=6)
    D.box("h_exit_b", (0.42, 0.06, 0.16), (0, LEN - 0.08, CH - 0.12), exit_m)
    D.text3d("h_exit_t", "EXIT", 0.1, (0, LEN - 0.115, CH - 0.125), flat("h_exit_txt", "#1a0302", 0.6), extrude=0.002,
             bevel=0.0, font=FONT)
    ex = D.link(bpy.data.objects.new("h_exit_l", bpy.data.lights.new("h_exit_l", "POINT")))
    ex.data.energy, ex.data.color, ex.location = 5, H("#ff2a1a"), (0, LEN - 0.3, CH - 0.2)
    # foreground story: gurney with a sheet, fallen IV stand, papers, one smear
    gur = D.empty("h_gurney", (0.42, 4.3, 0))
    gm = flat("h_gm", "#8d918c", 0.35, metal=0.8)
    for o in (D.box("h_gf", (0.62, 1.9, 0.05), (0, 0, 0.68), gm),
              D.box("h_gs", (0.66, 1.95, 0.16), (0, 0, 0.78), flat("h_sheet", "#d9d6c8", 0.85), bevel=0.06),
              D.box("h_gp", (0.3, 0.45, 0.1), (0, -0.7, 0.9), flat("h_pill", "#e4e1d6", 0.9), bevel=0.04),
              *[D.cyl(f"h_gl{i}", 0.02, 0.66, (sx * 0.27, sy * 0.85, 0.33), m=gm, verts=8)
                for i, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1)))]):
        o.parent = gur
    gur.rotation_euler.z = math.radians(-5)
    iv = D.empty("h_iv", (-0.35, 8.9, 0.03))
    for o in (D.cyl("h_ivp", 0.012, 1.8, (0, 0, 0.9), m=gm, verts=8), D.box("h_ivb", (0.12, 0.04, 0.2), (0, 0, 1.7),
              D.mat("h_ivbag", H("#cfe6d8"), rough=0.2))):
        o.parent = iv
    iv.rotation_euler = (math.radians(84), 0, math.radians(70))
    paper = flat("h_paper", "#d6d0b8", 0.9)
    for k in range(9):
        p = D.box(f"h_pp{k}", (0.21, 0.29, 0.002), (random.uniform(-0.6, 0.6), random.uniform(0.6, 12), 0.004), paper)
        p.rotation_euler.z = random.uniform(0, 3)
    sm = D.box("h_smear", (0.012, 0.9, 0.5), (HW - 0.0, 14.6, 1.0), D.mat("h_blood", H("#3b0505"), rough=0.6))
    sm.rotation_euler.x = math.radians(-12)
    # the guy: Eric, dark-clothed, standing in the doorway, head tilted. Moves closer each time we return.
    r_, arm_, body_ = D.import_char(os.path.join(HERE, "assets", "eric.glb"), "guy")
    for b in arm_.data.bones:
        bn = re.sub(r"_\d+$", "", b.name)
        if bn in REN:
            b.name = REN[bn]
    arm_.scale = (1.82 / 186.865,) * 3
    for b in body_:
        b.data.materials.clear()
        b.data.materials.append(D.mat("h_guy", H("#2a2522"), rough=0.55))
    bpy.context.view_layer.update()
    STAND = {"LeftUpLeg": (0.04, 0, -1), "RightUpLeg": (-0.04, 0, -1), "LeftLeg": (0, 0.03, -1), "RightLeg": (0, 0.03, -1),
             "Spine": (0, 0.02, 1), "LeftArm": (0.12, 0.02, -1), "RightArm": (-0.12, 0.02, -1),
             "LeftForeArm": (0.04, -0.03, -1), "RightForeArm": (-0.04, -0.03, -1), "Neck": (0.12, -0.05, 1),
             "Head": (0.38, -0.12, 1)}
    r_.rotation_euler.z = math.pi                           # face down the corridor toward camera
    GUY = [(1, (0.0, LEN + 0.7, 0)), (T(ws("p1")) - 1, (0.0, LEN + 0.7, 0)), (T(ws("p1")), (0.05, 11.55, 0)),
           (T(ws("p4")) - 1, (0.05, 11.55, 0)), (T(ws("p4")), (-0.1, 16.4, 0))]
    for f_, loc_ in GUY:
        D.key(r_, "location", f_, loc_, interp="CONSTANT")
    # flicker on panel 1 (lighting skill: one flicker), panel 4 dim + breathing
    f, fl = 1, lights["fl"]
    while f < T(END):
        on = random.random() > 0.18
        e = 110 if on else random.choice((18, 30, 45))
        fl.data.energy = e
        fl.data.keyframe_insert("energy", frame=f)
        key_input(m_fl, "Emission Strength", f, 9 if on else e / 12)
        f += random.choice((6, 9, 14, 22, 30)) if on else random.choice((1, 2))
    # ending: everything dies on "you animals", 0.35 s later one panel snaps on and the guy is in your face
    off_t, jump_t = we("p4") + 0.15, we("p4") + 0.6
    for l in list(lights.values()) + [ex]:
        e0 = l.data.energy
        l.data.keyframe_insert("energy", frame=T(off_t) - 1)
        l.data.energy = 0
        l.data.keyframe_insert("energy", frame=T(off_t))
    for m in (m_on, m_fl, m_dim, exit_m):
        key_input(m, "Emission Strength", T(off_t) - 1, m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value)
        key_input(m, "Emission Strength", T(off_t), 0)
    jl = D.area_light("h_jump", 0, (0.15, 14.05, 0.7), (0, 14.75, 1.62), size=0.25, rgb=H("#cfffe0"))
    jl.data.volume_factor = 0.0
    jl.data.keyframe_insert("energy", frame=T(jump_t) - 1)
    jl.data.energy = 160
    jl.data.keyframe_insert("energy", frame=T(jump_t))
    D.key(r_, "location", T(jump_t), (0.0, 14.75, 0), interp="CONSTANT")
    D.key(r_, "rotation_euler", 1, (0, 0, math.pi), interp="CONSTANT")
    D.key(r_, "rotation_euler", T(jump_t), (0, 0, 0), interp="CONSTANT")
    vd = next(n for n in hall_w.node_tree.nodes if n.bl_idname == "ShaderNodeVolumePrincipled").inputs["Density"]
    vd.default_value = 0.022
    vd.keyframe_insert("default_value", frame=T(jump_t) - 1)
    vd.default_value = 0.004
    vd.keyframe_insert("default_value", frame=T(jump_t))
    hall.eevee.volumetric_tile_size = "2"
    L.post(hall, bloom=0.55, bloom_threshold=0.8, vignette=0.42, saturation=0.82, contrast=0.12, dispersion=0.01)
    # shots: reveal dolly (h3), snap-zoom on the guy (h4), hero over the gurney (p1-p2), door + jumpscare (p4)
    shot(hall, "c_reveal", ws("h3"), ws("h4"), (0.15, -0.4, 1.25), (0.05, 2.4, 1.3), (0, 12, 1.15), (0, 13, 1.15), 18,
         shake=0.008)
    shot(hall, "c_zoom", ws("h4"), ws("b1"), (-0.32, 2.5, 1.5), (-0.3, 2.7, 1.5), (0, LEN, 1.45), (0, LEN, 1.5), 22, 88,
         shake=0.006)
    shot(hall, "c_hero", ws("p1"), ws("p2", 3), (-0.15, 1.6, 0.95), (-0.1, 3.2, 1.0), (0.05, 11.55, 1.1), (0.05, 11.55, 1.2), 22,
         shake=0.006)
    shot(hall, "c_door", ws("p4"), END, (0.3, 10.8, 1.5), (0.1, 13.3, 1.45), (0, LEN, 1.2), (0, LEN, 1.3), 24,
         shake=0.01)
    c_, l_ = D.camera("c_jump", 26)
    c_.location, l_.location = (0.05, 13.45, 1.5), (0.0, 14.75, 1.55)
    D.cut(hall, T(jump_t), c_)

# ================================================================ BAD: the no-skills attempt (the joke)
bad = L.new_set("BAD")
with L.building(bad):
    D.world(bad, H("#3c3c3c"), 1.0)
    g = flat("default_grey", "#9a9a9a", 0.5)
    D.box("b_floor", (1.6, 12, 0.1), (0, 6, -0.05), g)
    D.box("b_ceil", (1.6, 12, 0.1), (0, 6, 2.55), g)
    D.box("b_wl", (0.1, 12, 2.6), (-0.8, 6, 1.25), g)
    D.box("b_wr", (0.1, 12, 2.6), (0.8, 6, 1.25), g)
    cube = D.box("b_cube", (0.5, 0.5, 0.5), (0, 3.2, 0.25), g)
    D.text3d("b_spooky", "spooky", 0.09, (0, 2.94, 0.27), flat("b_txt", "#333333", 0.6), extrude=0.003, bevel=0.0, font=FONT)
    pl = D.link(bpy.data.objects.new("b_pt", bpy.data.lights.new("b_pt", "POINT")))
    pl.data.energy, pl.location = 160, (0, 1.5, 2.2)
    shot(bad, "c_bad", 0, ws("h2", 8), (0, -0.4, 1.6), (0, 0.6, 1.45), (0, 6, 1.2), (0, 3.2, 0.5), 22)
    shot(bad, "c_bad_cube", ws("h2", 8), ws("h3"), (0.25, 2.1, 0.55), (0.18, 2.35, 0.45), (0, 3.2, 0.3), (0, 3.2, 0.28), 30)

# ================================================================ WALL: 94 skill tiles
SKILLS = sorted(d for d in os.listdir(os.path.join(HERE, "..", "..", "..", ".claude", "skills"))
                if os.path.isfile(os.path.join(HERE, "..", "..", "..", ".claude", "skills", d, "SKILL.md"))
                and d not in ("3d-director", "3d-explainer-script", "3d-shot-grammar", "3d-lookdev", "cinematography",
                              "film-director", "film-qc", "frontend-design", "game-reel", "hook-to-3d", "lowpoly-ps2",
                              "remotion-best-practices", "story-architect"))
assert len(SKILLS) == 94, len(SKILLS)
CAT = {"#ff6b6b": ("horror", "body-", "eldritch", "liminal", "puppet", "found-footage", "weirdcore", "folk-"),
       "#ffd23f": ("-style",), "#5ec8ff": ("genre-",), "#7cff6b": ("-worlds", "-mood", "neon", "console"),
       "#c792ff": ("export", "lod-", "collision", "asset-opt", "qa-", "scene-assembly", "set-dressing", "archviz",
                   "procedural")}


def cat_col(n):
    if n == "blender-director":
        return "#ffffff"
    for c, keys in CAT.items():
        if any(k in n for k in keys):
            return c
    return "#ff9f43"                                      # modelling / production / technical


wall = L.new_set("WALL")
with L.building(wall):
    D.world(wall, H("#070a14"), 1.0)
    tile_m = flat("w_tile", "#141a2c", 0.45)
    txt_m = D.mat("w_txt", H("#f2f2f2"), emit=H("#f2f2f2"), emit_strength=1.2)
    COLS, TW, TH, GX, GY = 4, 1.42, 0.34, 1.52, 0.42
    rows = -(-len(SKILLS) // COLS)
    t0 = ws("b1")
    order = SKILLS[:]
    order.remove("blender-director")
    order.insert((rows // 2) * COLS + 1, "blender-director")   # director sits mid-wall, centre column
    for i, n in enumerate(order):
        r, c = divmod(i, COLS)
        x, z = (c - (COLS - 1) / 2) * GX, (rows / 2 - r) * GY
        g = D.empty(f"w_{n}", (x, 0, z))
        col = cat_col(n)
        stripe = D.mat(f"w_s_{n}", H(col), emit=H(col), emit_strength=2.0 if n != "blender-director" else 0.7)
        D.box(f"w_t_{n}", (TW, 0.06, TH), (0, 0, 0), tile_m if n != "blender-director" else stripe, bevel=0.02).parent = g
        D.box(f"w_st_{n}", (0.05, 0.07, TH * 0.8), (-TW / 2 + 0.06, -0.01, 0), stripe).parent = g
        size = min(0.12, 1.18 / (0.6 * len(n)))
        tm = txt_m if n != "blender-director" else flat("w_txt_d", "#05070d", 0.6)
        D.text3d(f"w_x_{n}", n, size, (0.04, -0.035, 0), tm, extrude=0.005, bevel=0.0, font=MONO).parent = g
        dist = math.hypot(c - 1.5, r - rows / 2)
        tp = t0 + 0.05 + dist * 0.07 + random.random() * 0.15
        D.key(g, "location", 1, (x, -9, z))
        D.key(g, "location", T(tp), (x, -9, z))
        D.key(g, "location", T(tp + 0.35), (x, 0, z))
        D.ease_all(g)
        D.key(g, "rotation_euler", T(tp), (math.radians(80), 0, 0))
        D.key(g, "rotation_euler", T(tp + 0.35), (0, 0, 0))
    D.area_light("w_key", 300, (0, -6, 4), (0, 0, 0), size=8)
    L.post(wall, bloom=0.5, vignette=0.3)
    dz = ((rows // 2) * 0 + rows / 2 - rows // 2) * GY        # director tile row height
    shot(wall, "c_wall", t0, ws("b2"), (-0.76, -3.4, dz + 0.05), (0, -12.5, 0.0), (-0.76, 0, dz), (0, 0, 0.0), 30, 32)
    shot(wall, "c_wall_bg", ws("p3", 7), ws("p3", 12), (2.2, -3.6, 2.4), (1.4, -3.9, -1.6), (0.6, 0, 1.6), (0.2, 0, -2.0), 40)

# ================================================================ CRATE: hard-surface pipeline
crate = L.new_set("CRATE")
with L.building(crate):
    L.hdri_world(crate, "studio_small_09", 0.6, backdrop=H("#0d1018"), backdrop_strength=1.0)
    D.box("c_floor", (30, 30, 0.1), (0, 0, -0.05), D.mat("c_floor_m", H("#11141c"), rough=0.25))
    clay = flat("c_clay", "#b8b8b4", 0.55)
    clay_d = flat("c_clay_d", "#3a3d44", 0.6)
    wire = D.mat("c_wire", H("#36e0ff"), emit=H("#36e0ff"), emit_strength=4)
    chk = bpy.data.materials.new("c_checker")
    chk.use_nodes = True
    nt = chk.node_tree
    tc, ck = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 9
    ck.inputs["Color1"].default_value = (*H("#ffffff"), 1)
    ck.inputs["Color2"].default_value = (*H("#ff4fa0"), 1)
    nt.links.new(tc.outputs["Object"], ck.inputs["Vector"])
    nt.links.new(ck.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    frame_m = L.pbr("c_frame", "metal_plate", scale=2.0, tint=H("#2b2f38"), tint_amount=0.75)
    paint_m = L.pbr("c_paint", "metal_plate", scale=1.5, tint=H("#ff7a1a"), tint_amount=0.85)
    strip_m = D.mat("c_strip", H("#36e0ff"), emit=H("#36e0ff"), emit_strength=8)
    dark_m = flat("c_dark", "#14161b", 0.4, metal=0.6)

    def make_crate(tag, m):
        g = D.empty(f"cr_{tag}", (0, 0, 0))
        parts = []
        S, B = 1.0, 0.11
        parts.append(D.box(f"cr_{tag}_body", (S - 0.08, S - 0.08, S - 0.08), (0, 0, S / 2), m["paint"], bevel=0.01))
        for ax in range(3):                                   # 12 edge bars = manufacturing frame (primary forms)
            for a in (-1, 1):
                for b in (-1, 1):
                    loc, size = [0, 0, 0], [B, B, B]
                    size[ax] = S
                    o = [i for i in range(3) if i != ax]
                    loc[o[0]], loc[o[1]] = a * (S - B) / 2, b * (S - B) / 2
                    loc[2] += S / 2
                    parts.append(D.box(f"cr_{tag}_e", tuple(size), tuple(loc), m["frame"], bevel=0.012))
        for sx in (-1, 1):                                    # panel insets + vents (secondary), strip (tertiary)
            parts.append(D.box(f"cr_{tag}_pn", (0.5, 0.03, 0.5), (sx * 0.0, -(S / 2 - 0.04) * 1, S / 2), m["frame"], bevel=0.008)) if sx < 0 else None
            for k in range(3):
                parts.append(D.box(f"cr_{tag}_v", (0.03, 0.36, 0.05), ((S / 2 - 0.03) * sx, 0, S / 2 + 0.12 - k * 0.12),
                                   m["dark"], bevel=0.006))
        parts.append(D.box(f"cr_{tag}_strip", (0.36, 0.02, 0.04), (0, -(S / 2 - 0.0), S / 2 + 0.18), m["strip"]))
        parts.append(D.box(f"cr_{tag}_hd", (0.22, 0.05, 0.05), (0, -(S / 2 + 0.02), S / 2 - 0.12), m["dark"], bevel=0.01))
        parts.append(D.cyl(f"cr_{tag}_hatch", 0.24, 0.04, (0, 0, S + 0.0), m=m["frame"], verts=32))
        parts.append(D.cyl(f"cr_{tag}_hatch2", 0.12, 0.05, (0, 0, S + 0.01), m=m["dark"], verts=6))
        for p in parts:
            if p:
                wn = p.modifiers.new("wn", "WEIGHTED_NORMAL")
                wn.keep_sharp = True
                p.parent = g
        return g, [p for p in parts if p]

    t_b2 = ws("b2")
    st = [ws("b2", i) for i in (4, 6, 7, 11, 12)]                       # Hard surface / Topology / UVs / Materials / Lighting
    t_end_b2 = ws("b3")
    hero = (ws("p2", 3), ws("p2", 6))
    blk_g = D.empty("cr_blk", (0, 0, 0))
    D.box("cr_blk_box", (1, 1, 1), (0, 0, 0.5), clay).parent = blk_g
    clay_g, _ = make_crate("clay", {"paint": clay, "frame": clay, "dark": clay, "strip": clay})
    topo_g, tparts = make_crate("topo", {"paint": clay_d, "frame": clay_d, "dark": clay_d, "strip": clay_d})
    for p in tparts:
        wc = p.copy()
        wc.data = p.data.copy()
        D.link(wc)
        wc.modifiers.clear()
        wm = wc.modifiers.new("w", "WIREFRAME")
        wm.thickness, wm.use_even_offset, wm.use_replace = 0.006, False, True
        wc.data.materials.clear()
        wc.data.materials.append(wire)
        wc.parent = topo_g
        wc.matrix_parent_inverse = p.matrix_parent_inverse
    uv_g, _ = make_crate("uv", {"paint": chk, "frame": chk, "dark": chk, "strip": chk})
    pbr_g, _ = make_crate("pbr", {"paint": paint_m, "frame": frame_m, "dark": dark_m, "strip": strip_m})
    visible(blk_g, [(t_b2, st[0])])
    visible(clay_g, [(st[0], st[1])])
    visible(topo_g, [(st[1], st[2])])
    visible(uv_g, [(st[2], st[3])])
    visible(pbr_g, [(st[3], t_end_b2 + 0.1), (hero[0], hero[1] + 0.1)])
    piv = D.empty("cr_spin", (0, 0, 0))
    for g in (blk_g, clay_g, topo_g, uv_g, pbr_g):
        g.parent = piv
    spin(piv, t_b2, t_end_b2, 0.35, math.radians(-20))
    key_l = D.area_light("c_key", 260, (-2.5, -3, 3.5), (0, 0, 0.5), size=3)
    rims = [D.area_light("c_rimc", 0, (2.2, 1.8, 1.6), (0, 0, 0.5), size=1.5, rgb=H("#36e0ff")),
            D.area_light("c_rimo", 0, (-2.2, 2.0, 1.2), (0, 0, 0.5), size=1.5, rgb=H("#ff7a1a"))]
    for l in rims:
        l.data.energy = 0
        l.data.keyframe_insert("energy", frame=T(st[4]))
        l.data.energy = 420
        l.data.keyframe_insert("energy", frame=T(st[4] + 0.3))
    key_l.data.keyframe_insert("energy", frame=T(st[4]))
    key_l.data.energy = 110
    key_l.data.keyframe_insert("energy", frame=T(st[4] + 0.3))
    L.post(crate, bloom=0.45, vignette=0.3)
    shot(crate, "c_crate", t_b2, t_end_b2, (0.2, -3.4, 1.9), (0.1, -2.9, 1.5), (0, 0, 0.55), (0, 0, 0.55), 34)
    shot(crate, "c_crate_hero", hero[0], hero[1], (-1.3, -1.6, 0.25), (-0.9, -1.9, 0.35), (0, 0, 0.75), (0, 0, 0.6), 22)

# ================================================================ PIPE: director routing
pipe = L.new_set("PIPE")
with L.building(pipe):
    D.world(pipe, H("#06080f"), 1.0)
    NODES = [("your prompt", "#ffffff"), ("blender-director", "#ffffff"), ("hard-surface", "#ff9f43"),
             ("uv-workflow", "#ff9f43"), ("materials", "#ff9f43"), ("export-pipeline", "#c792ff")]
    t0, t1 = ws("b3"), ws("b4")
    arrive = [ws("b3", 4), ws("b3", 6)] + [ws("b3", 8) + k * (ws("b3", 12) - ws("b3", 8)) / 3 for k in range(4)]
    GAPZ = 1.25
    body = flat("p_body", "#121829", 0.45)
    for i, (n, col) in enumerate(NODES):
        z = -i * GAPZ
        glow = D.mat(f"p_g{i}", H(col), emit=H(col), emit_strength=0.0)
        D.box(f"p_n{i}", (2.5, 0.25, 0.62), (0, 0, z), body, bevel=0.05)
        D.box(f"p_rim{i}", (2.56, 0.2, 0.68), (0, 0.04, z), glow, bevel=0.05)
        D.text3d(f"p_t{i}", n if i else "> " + n, 0.2, (0, -0.14, z), D.mat(f"p_tm{i}", H("#f4f4f4"), emit=H("#f4f4f4"),
                 emit_strength=1.0), extrude=0.01, bevel=0.0, font=MONO)
        key_input(glow, "Emission Strength", T(arrive[i]) - 1, 0.15)
        key_input(glow, "Emission Strength", T(arrive[i]) + 2, 9.0)
        key_input(glow, "Emission Strength", T(arrive[i]) + 10, 3.5)
        if i:
            D.cyl(f"p_c{i}", 0.025, GAPZ - 0.62, (0, 0.02, z + GAPZ / 2), m=flat("p_wire", "#2a3350", 0.5), verts=8)
    pulse = D.sphere("p_pulse", 0.09, (0, -0.05, 0), D.mat("p_pm", H("#fff4c2"), emit=H("#fff4c2"), emit_strength=30))
    for i, ta in enumerate(arrive):
        D.key(pulse, "location", T(ta), (0, -0.2, -i * GAPZ + 0.36))
    D.ease_all(pulse)
    L.post(pipe, bloom=0.6, vignette=0.3)
    c, l = shot(pipe, "c_pipe", t0, t1, (1.6, -5.2, 0.4), (1.2, -5.9, -5.2), (0, 0, -0.9), (0, 0, -5.6), 32)

# ================================================================ STYLE: one prop, five rule sets
STY = [("S_CLAY", ws("b4"), ws("b4", 5)), ("S_LOW", ws("b4", 5), ws("b4", 7)), ("S_ANIME", ws("b4", 7), ws("b4", 8)),
       ("S_VOX", ws("b4", 8), ws("b4", 9)), ("S_HORR", ws("b4", 9), ws("b5"))]


def mushroom(tag, cols):
    g = D.empty(f"m_{tag}", (0, 0, 0))
    parts = [D.cyl(f"m_{tag}_base", 1.1, 0.24, (0, 0, 0.12), m=cols["grass"], verts=48),
             D.cone(f"m_{tag}_stem", 0.5, 1.0, (0, 0, 0.74), m=cols["stem"], verts=32),
             D.sphere(f"m_{tag}_cap", 0.9, (0, 0, 1.35), cols["cap"], seg=40, rings=20),
             D.box(f"m_{tag}_door", (0.26, 0.08, 0.4), (0, -0.44, 0.44), cols["door"], bevel=0.04),
             D.cyl(f"m_{tag}_win", 0.11, 0.06, (0.32, -0.33, 0.85), rot=(math.pi / 2, 0, math.radians(-40)), m=cols["win"], verts=20)]
    parts[2].scale = (1, 1, 0.62)
    for k in range(7):                                         # spots on the cap
        a = k * 2 * math.pi / 7 + 0.3
        e = 0.5 if k % 2 else 0.9
        v = Vector((math.cos(a) * math.sin(e), math.sin(a) * math.sin(e), math.cos(e) * 0.62))
        parts.append(D.sphere(f"m_{tag}_spot{k}", 0.13, tuple(Vector((0, 0, 1.35)) + v * 0.9), cols["spot"], seg=16, rings=8))
        parts[-1].scale = (1, 1, 0.45)
        parts[-1].rotation_euler = v.to_track_quat("Z", "Y").to_euler()
    for k, (x, y) in enumerate(((0.05, -0.75), (-0.12, -0.95))):
        parts.append(D.cyl(f"m_{tag}_st{k}", 0.1, 0.04, (x, y, 0.25), m=cols["stone"], verts=12))
    for p in parts:
        p.parent = g
    return g, parts


def toon(name, hexc, shade=0.55):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    c = H(hexc)
    ramp.color_ramp.elements[0].color = (*[x * shade for x in c], 1)
    ramp.color_ramp.elements[1].position = 0.32
    ramp.color_ramp.elements[1].color = (*c, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(d.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], o.inputs["Surface"])
    return m


outline_m = D.mat("m_outline", (0, 0, 0), rough=1.0)
outline_m.use_backface_culling = True
PAL = {"cap": "#e8433f", "stem": "#f3e2c0", "grass": "#58c24a", "door": "#7a4a2a", "win": "#ffd23f", "spot": "#fff8ec",
       "stone": "#9a9a92"}
for name, a, b in STY:
    sc = L.new_set(name)
    with L.building(sc):
        if name == "S_CLAY":
            L.hdri_world(sc, "studio_small_09", 0.8, backdrop=H("#2a2c31"))
            cols = {k: flat(f"{name}_{k}", "#b9b7b1", 0.55) for k in PAL}
        elif name == "S_LOW":
            L.hdri_world(sc, "kloofendal_48d_partly_cloudy_puresky", 0.7, backdrop=H("#8fd3ff"))
            cols = {k: flat(f"{name}_{k}", v, 0.9, emit=1.5 if k == "win" else 0) for k, v in PAL.items()}
            D.sun("s_low_sun", 3.5, (-0.6, 0.8, -0.7), rgb=H("#fff0d6"))
        elif name == "S_ANIME":
            D.world(sc, H("#ffd1e8"), 1.0)
            cols = {k: toon(f"{name}_{k}", v) for k, v in PAL.items()}
            D.sun("s_an_sun", 4.0, (-0.8, 0.5, -0.6))
        elif name == "S_VOX":
            L.hdri_world(sc, "kloofendal_48d_partly_cloudy_puresky", 0.7, backdrop=H("#7fe0c8"))
            cols = {k: flat(f"{name}_{k}", v, 0.95, emit=1.5 if k == "win" else 0) for k, v in PAL.items()}
            D.sun("s_vox_sun", 3.5, (-0.6, 0.8, -0.7), rgb=H("#fff0d6"))
        else:
            fog(sc, 0.015, rgb=H("#8fa0c8"), bg=H("#0b1020"), bg_strength=1.0)
            cols = {"cap": flat("hz_cap", "#3a1416", 0.6), "stem": flat("hz_stem", "#4c463c", 0.8),
                    "grass": flat("hz_gr", "#1c2a1a", 0.9), "door": flat("hz_door", "#1a120c", 0.8),
                    "win": D.mat("hz_win", H("#ff2a1a"), emit=H("#ff2a1a"), emit_strength=14),
                    "spot": flat("hz_spot", "#6d675c", 0.7), "stone": flat("hz_st", "#2e2e2c", 0.9)}
            D.sun("s_hz_moon", 7.0, (0.7, 0.6, -0.5), rgb=H("#8fa8ff"))
            rl = D.link(bpy.data.objects.new("hz_red", bpy.data.lights.new("hz_red", "POINT")))
            rl.data.energy, rl.data.color, rl.location = 120, H("#ff2a1a"), (0.55, -0.75, 0.9)
            D.area_light("hz_rim", 450, (-1.5, 2.0, 2.5), (0, 0, 1.0), size=2, rgb=H("#7f9bff"))
        g, parts = mushroom(name, cols)
        if name == "S_HORR":
            cl = D.empty("hz_cloud", (0, 0, 2.55))
            cm_ = flat("hz_cloud_m", "#2a2d36", 0.9)
            for k, (x_, y_, r_) in enumerate(((0, 0, 0.32), (0.3, 0.05, 0.25), (-0.3, -0.02, 0.24), (0.12, 0.1, 0.27),
                                              (-0.12, -0.08, 0.22))):
                D.sphere(f"hz_c{k}", r_, (x_, y_, 0), cm_, seg=16, rings=8).parent = cl
            drop = D.mat("hz_drop", H("#9fb6ff"), emit=H("#9fb6ff"), emit_strength=1.2)
            for k in range(14):
                d_ = D.sphere(f"hz_d{k}", 0.02, (0, 0, 0), drop, seg=8, rings=4)
                d_.scale = (1, 1, 2.5)
                x_, y_ = random.uniform(-0.4, 0.4), random.uniform(-0.25, 0.25)
                t_ = a + random.uniform(0, 0.5)
                while t_ < b + 0.1:
                    D.key(d_, "location", T(t_), (x_, y_, 2.35), interp="LINEAR")
                    D.key(d_, "location", T(t_ + 0.45) - 1, (x_, y_, 1.25), interp="CONSTANT")
                    t_ += 0.45
        D.box(f"{name}_ground", (40, 40, 0.1), (0, 0, -0.05), cols["grass"] if name != "S_CLAY" else cols["stone"])
        for p in parts:
            if name == "S_LOW" and len(p.data.polygons) > 40:
                d = p.modifiers.new("dec", "DECIMATE")
                d.ratio = 0.08
            if name in ("S_LOW", "S_VOX"):
                for f_ in p.data.polygons:
                    f_.use_smooth = False
            if name == "S_VOX":
                r = p.modifiers.new("vox", "REMESH")
                r.mode, r.octree_depth, r.scale, r.use_remove_disconnected = "BLOCKS", 5, 0.95, False
                r.use_smooth_shade = False
            if name == "S_ANIME":
                p.data.materials.append(outline_m)
                s_ = p.modifiers.new("ol", "SOLIDIFY")
                s_.thickness, s_.use_flip_normals, s_.material_offset = 0.025, True, 1
                s_.offset = 1.0
        spin(g, a, b + 0.05, 0.12, math.radians(-25))
        if name == "S_HORR":
            L.post(sc, bloom=0.6, vignette=0.45, saturation=0.9)
        else:
            L.post(sc, bloom=0.25, vignette=0.2, saturation=1.1)
        lens = 30
        shot(sc, f"c_{name}", a, b, (1.4, -4.2, 2.2), (1.1, -3.6, 1.9), (0, 0, 0.95), (0, 0, 0.95), lens)

# ================================================================ ISL (final) + MCP (viewport) island
isl = L.new_set("ISL")
mcp = L.new_set("MCP")
t_b5, t_p1 = ws("b5"), ws("p1")
with L.building(isl):
    L.hdri_world(isl, "belfast_sunset_puresky", 0.9, rot_deg=120)
    D.sun("i_sun", 3.2, (-0.5, 0.7, -0.45), rgb=H("#ffd2a0"), angle=3)
    water = D.box("i_water", (60, 60, 0.1), (0, 0, -0.05),
                  D.mat("i_water_m", H("#1fa6c9"), rough=0.08, spec=0.7))
    PI = {"sand": flat("i_sand", "#f2d29b", 0.95), "grass": flat("i_grass", "#69c24f", 0.9),
          "trunk": flat("i_trunk", "#a0703f", 0.9), "leaf": flat("i_leaf", "#3fae4a", 0.85),
          "wall": flat("i_wall", "#f5e3c3", 0.85), "roof": flat("i_roof", "#d9573b", 0.8),
          "wood": flat("i_wood", "#8a5a32", 0.9), "rock": flat("i_rock", "#8d8f94", 0.95),
          "boat": flat("i_boat", "#ff5a4f", 0.7), "fire": D.mat("i_fire", H("#ffb43a"), emit=H("#ffb43a"), emit_strength=8)}

    def lowpoly(o, jitter=0.06, seed=0):
        rnd = random.Random(seed)
        for v in o.data.vertices:
            v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.5, 0.5))) * jitter
        for f_ in o.data.polygons:
            f_.use_smooth = False
        return o

    pieces = []
    isle = lowpoly(D.ico("i_isle", 1, (0, 0, -0.15), PI["sand"], sub=2), 0.06, 1)
    isle.scale = (2.4, 2.0, 0.55)
    top = lowpoly(D.ico("i_top", 1, (0.15, 0.25, 0.08), PI["grass"], sub=2), 0.05, 2)
    top.scale = (1.8, 1.45, 0.32)
    pieces += [isle, top]
    hut = D.empty("i_hut", (0.55, 0.55, 0.38))
    for p in (D.box("i_hw", (0.6, 0.55, 0.42), (0, 0, 0.21), PI["wall"]),
              D.cone("i_hr", 0.55, 0.42, (0, 0, 0.62), PI["roof"], verts=4),
              D.box("i_hd", (0.16, 0.02, 0.26), (0, -0.28, 0.13), PI["wood"])):
        p.parent = hut
        for f_ in p.data.polygons:
            f_.use_smooth = False
    hut.children[1].rotation_euler.z = math.pi / 4
    pieces.append(hut)
    for k, (x, y, lean) in enumerate(((-0.75, 0.15, -0.25), (-0.35, 0.85, 0.2))):
        palm = D.empty(f"i_palm{k}", (x, y, 0.33))
        for s_ in range(5):
            D.cyl(f"i_pt{k}{s_}", 0.08 - s_ * 0.008, 0.3, (lean * s_ * 0.08, 0, 0.15 + s_ * 0.28), m=PI["trunk"],
                  verts=6).parent = palm
        for j in range(6):
            lf = D.cone(f"i_pl{k}{j}", 0.18, 0.9, (lean * 0.4, 0, 1.45), PI["leaf"], verts=4)
            lf.scale = (1, 0.25, 1)
            a = j * math.pi / 3
            lf.rotation_euler = (math.radians(70), 0, a)
            lf.location += Vector((math.sin(a) * 0.38, -math.cos(a) * 0.38, -0.12))
            lf.parent = palm
        pieces.append(palm)
    dock = D.empty("i_dock", (0.9, -1.2, 0.12))
    for j in range(6):
        D.box(f"i_dp{j}", (0.42, 0.13, 0.05), (0, -j * 0.16, 0), PI["wood"]).parent = dock
    for sx in (-1, 1):
        D.cyl("i_dpost", 0.035, 0.5, (sx * 0.19, -0.85, -0.15), m=PI["wood"], verts=6).parent = dock
    pieces.append(dock)
    rocks = D.empty("i_rocks", (-1.3, -0.9, 0.05))
    for j, (x, y, r) in enumerate(((0, 0, 0.2), (0.25, 0.1, 0.13), (-0.1, 0.3, 0.1))):
        lowpoly(D.ico(f"i_rk{j}", r, (x, y, r * 0.4), PI["rock"], sub=1), 0.02, 10 + j).parent = rocks
    pieces.append(rocks)
    boat = D.empty("i_boat", (1.6, -2.1, 0.06))
    D.box("i_bh", (0.32, 0.75, 0.14), (0, 0, 0), PI["boat"], bevel=0.04).parent = boat
    D.box("i_bs", (0.3, 0.1, 0.03), (0, 0.05, 0.07), PI["wood"]).parent = boat
    pieces.append(boat)
    fire = D.empty("i_fire", (-0.1, -0.35, 0.36))
    for j in range(4):
        D.cyl(f"i_fl{j}", 0.025, 0.28, (0, 0, 0.03), rot=(math.pi / 2, 0, j * math.pi / 4), m=PI["wood"], verts=5).parent = fire
    D.cone("i_ff", 0.09, 0.22, (0, 0, 0.13), PI["fire"], verts=5).parent = fire
    fl_l = D.link(bpy.data.objects.new("i_fire_l", bpy.data.lights.new("i_fire_l", "POINT")))
    fl_l.data.energy, fl_l.data.color, fl_l.location, fl_l.parent = 25, H("#ffa040"), (0, 0, 0.3), fire
    pieces.append(fire)
    # assembly: each piece drops in during b5 (in both ISL and MCP since they share objects + actions)
    n = len(pieces)
    span = (t_p1 - 0.5) - (t_b5 + 0.3)
    for k, p in enumerate(pieces):
        tk = t_b5 + 0.3 + k * span / n
        fin, fs = tuple(p.location), tuple(p.scale)
        D.key(p, "location", 1, (fin[0], fin[1], fin[2] + 6))
        D.key(p, "location", T(tk), (fin[0], fin[1], fin[2] + 6))
        D.key(p, "location", T(tk + 0.3), fin)
        D.overshoot(p, "scale", T(tk), T(tk + 0.35), tuple(x * 0.3 for x in fs), fs, 1.15)
        D.key(p, "scale", 1, tuple(x * 0.3 for x in fs))
    L.post(isl, bloom=0.35, vignette=0.2, saturation=1.12)
    tI = ws("p2", 6)
    shot(isl, "c_isl", tI, ws("p3", 7), (5.4, -5.2, 2.0), (3.0, -6.6, 2.2), (0, -0.2, 0.4), (0, -0.2, 0.5), 28)

with L.building(mcp):
    D.world(mcp, H("#393939"), 1.0)                            # Blender's default viewport grey
    clay_v = flat("v_clay", "#c8c8c8", 0.6)
    copies = {}
    for p in pieces:                                          # linked duplicates: same mesh + same action, clay slots
        for o in [p] + list(p.children_recursive):
            if o.type == "LIGHT":
                continue
            copies[o] = obj_copy(o, clay_v)
    for o, c in copies.items():
        if o.parent in copies:
            c.parent = copies[o.parent]
    line_m = D.mat("v_line", H("#4f4f4f"), emit=H("#4f4f4f"), emit_strength=1.0)
    D.box("v_floor", (30, 30, 0.01), (0, 0, -0.43), flat("v_floor_m", "#3a3a3a", 1.0))
    for k in range(-14, 15):
        D.box(f"v_gx{k}", (30, 0.012, 0.003), (0, k * 0.5, -0.42), line_m)
        D.box(f"v_gy{k}", (0.012, 30, 0.003), (k * 0.5, 0, -0.42), line_m)
    D.box("v_xaxis", (30, 0.02, 0.004), (0, 0, -0.418), D.mat("v_x", H("#ff3352"), emit=H("#ff3352"), emit_strength=1.5))
    D.box("v_yaxis", (0.02, 30, 0.004), (0, 0, -0.418), D.mat("v_y", H("#8bdc00"), emit=H("#8bdc00"), emit_strength=1.5))
    D.area_light("v_key", 500, (-3, -4, 6), (0, 0, 0), size=6)
    D.area_light("v_fill", 150, (4, 2, 3), (0, 0, 0), size=6)
    shot(mcp, "c_mcp", t_b5, t_p1, (5.6, -6.0, 4.4), (4.0, -7.0, 3.6), (0, -0.3, 0.3), (0, -0.3, 0.4), 28)

# ================================================================ DONUT: "stop jerking off to donut tutorials"
dn = L.new_set("DONUT")
t_d0, t_d1 = ws("p3", 12), ws("p4")
with L.building(dn):
    L.hdri_world(dn, "studio_small_09", 0.7, backdrop=H("#ffd9e6"))
    D.box("dn_floor", (30, 30, 0.1), (0, 0, -0.05), flat("dn_tab", "#ffe9f0", 0.6))
    D.cyl("dn_plate", 0.75, 0.04, (0, 0, 0.02), m=D.mat("dn_plate_m", H("#f4f4f4"), rough=0.15), verts=48)
    dg = D.empty("dn_g", (0, 0, 0.04))
    D.torus("dn_dough", 0.42, 0.2, (0, 0, 0.2), m=D.mat("dn_dough_m", H("#d89a55"), rough=0.6)).parent = dg
    ic = D.torus("dn_icing", 0.42, 0.205, (0, 0, 0.245), m=D.mat("dn_ice", H("#ff6fae"), rough=0.25))
    ic.scale = (1.02, 1.02, 0.72)
    ic.parent = dg
    for k in range(40):
        a_ = random.uniform(0, 2 * math.pi)
        r_ = 0.42 + random.uniform(-0.14, 0.14)
        sp = D.cyl(f"dn_sp{k}", 0.012, 0.06, (math.cos(a_) * r_, math.sin(a_) * r_, 0.39), rot=(math.pi / 2, 0, random.uniform(0, 3)),
                   m=flat(f"dn_spm{k % 5}", ("#ffe14d", "#4dd2ff", "#7cff6b", "#ffffff", "#c792ff")[k % 5], 0.5), verts=6)
        sp.parent = dg
    crg, _ = make_crate("dn", {"paint": paint_m, "frame": frame_m, "dark": dark_m, "strip": strip_m})
    crg.scale = (0.72, 0.72, 0.72)
    hit = t_d0 + 0.75
    D.key(crg, "location", 1, (0, 0, 6))
    D.key(crg, "location", T(hit) - 6, (0, 0, 6))
    D.key(crg, "location", T(hit), (0, 0, 0.09), interp="CONSTANT")
    D.key(dg, "scale", T(hit) - 1, (1, 1, 1))
    D.key(dg, "scale", T(hit), (1.55, 1.55, 0.1))
    D.key(dg, "location", T(hit), (0, 0, 0.0))
    D.area_light("dn_key", 400, (-2, -3, 4), (0, 0, 0.3), size=3)
    L.post(dn, bloom=0.3, vignette=0.2, saturation=1.1)
    shot(dn, "c_donut", t_d0, t_d1, (0.0, -2.6, 1.35), (0.0, -2.9, 1.7), (0, 0, 0.3), (0, 0, 0.45), 30, shake=0.004)

SHOTS.sort(key=lambda x: x[1])
json.dump(SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(SHOTS), [s.name for s in bpy.data.scenes], "END", END)
