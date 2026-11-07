# exec'd by scene.py (names: D L C B W END F H MAT shot txt pose room dark_world spot point key_val ...). HOOK → DESERT.
A = C.A


def bg_node(sc):
    return next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")


def glow_textures(objs, strength):
    """Lightbox: feed each material's base-colour texture into its emission (the film glows from behind)."""
    for o in objs:
        for sl in o.material_slots:
            m = sl.material
            bs = m.node_tree.nodes.get("Principled BSDF") if m and m.use_nodes else None
            if bs and bs.inputs["Base Color"].is_linked:
                m.node_tree.links.new(bs.inputs["Base Color"].links[0].from_socket, bs.inputs["Emission Color"])
                bs.inputs["Emission Strength"].default_value = strength


def desert_floor(sc, tex="red_sand", scale=0.35):
    D.box(sc.name + "_ground", (600, 600, 0.02), (0, 0, -0.01), L.pbr(sc.name + "_sand", tex, scale=scale,
                                                                       tint=H("#d9a066"), tint_amount=0.35))
    for i in range(70):                                   # scrub + rocks out to the horizon
        x, y = random.uniform(-60, 60), random.uniform(-10, 120)
        if abs(x) < 6 and y < 14:
            continue
        if i % 3:
            L.bush((x, y, 0), scale=random.uniform(0.4, 1.0), seed=i, leaf=(0.16, 0.17, 0.07))
        else:
            r = D.ico("rock", random.uniform(0.3, 1.4), (x, y, 0), m=L.pbr("rock_" + sc.name, "dry_ground_rocks", 0.8),
                      sub=2)
            r.scale = (1.3, 1.0, 0.45)


RV = C.template(A("rv.glb"), 7.6, axis=1)

# ================================================================= HOOK: Heisenberg in the desert at dusk (also the final)
hk = L.new_set("HOOK", main=True)
L.hdri_world(hk, "goegap_road", 0.9, rot_deg=150)
D.sun("h_sun", 4.5, (-0.55, -0.75, -0.22), rgb=H("#ffb066"), angle=3)
desert_floor(hk)
C.copy(RV, "rv_h", (-3.6, 7.5, 0), yaw=0.55)
walt, warm, _ = C.walt("walt_h", (0, 0, 0), 0.0, hat=True)
pose(warm, walt, [(0, C.WSTAND)])
L.post(hk, bloom=0.3, vignette=0.38, saturation=1.05, contrast=0.08)
shot(hk, "H_hook", 0.0, B[1], (0.6, -5.2, 0.4), (0.25, -2.4, 1.05), (0, 0, 1.35), (0, 0, 1.62), 26, 38)
shot(hk, "H_final", B[12], END, (0.18, -1.15, 1.6), (1.8, -8.5, 0.55), (0, 0, 1.66), (-0.4, 0, 1.4), 45, 28, shake=0.003)

# ================================================================= XRAY: the scan on the lightbox; the shadow fades on "clean"
xr = L.new_set("XRAY")
with L.building(xr):
    dark_world(xr, "#06090a", 1.0)
    wall = L.pbr("x_wall", "painted_plaster_wall", 0.6, tint=H("#6f8a86"), tint_amount=0.8)
    room(xr, 5, 5, 3, wall, L.pbr("x_floor", "old_linoleum_flooring_01", 0.6))
    XR = C.template(A("xray.glb"), 1.55, axis=0, base=False)
    box = C.copy(XR, "xray", (0, 2.38, 1.6))
    glow_textures([o for o in box.children], 1.6)
    D.area_light("x_glow", 120, (0, 1.9, 1.6), (0, -2, 1.4), size=1.4, rgb=H("#d8f2ff"))
    D.area_light("x_fill", 25, (-2, -1.5, 2.6), (0, 2, 1.4), size=2, rgb=H("#9fd0c0"))
    tumor = D.cyl("tumor", 0.026, 0.004, (0.33, 2.245, 1.70), rot=(math.pi / 2, 0, 0),
                  m=D.mat("tumor", H("#f4f8fa"), rough=0.6, emit=H("#dfe9ee"), emit_strength=0.5), verts=32)
    tumor.scale = (1.0, 1.25, 1.0)
    D.key(tumor, "scale", F(W["clean"] + 0.05), (1.0, 1.25, 1.0))
    D.key(tumor, "scale", F(W["clean"] + 0.45), (0, 0, 1.0))
    L.post(xr, bloom=0.5, vignette=0.4)
    shot(xr, "X_room", B[1], W["the"], (0.6, -1.0, 1.45), (0.4, -0.2, 1.55),
         (0, 2.3, 1.55), (0.1, 2.3, 1.6), 30)
    shot(xr, "X_lung", W["the"], B[3], (0.42, 1.25, 1.72), (0.36, 1.62, 1.71), (0.33, 2.3, 1.70), (0.33, 2.3, 1.70), 40,
         shake=0.002)

# ================================================================= HOSP: Walt on the hospital bed — relief
hs = L.new_set("HOSP")
with L.building(hs):
    dark_world(hs, "#202826", 1.0)
    wall = L.pbr("h_wall", "painted_plaster_wall", 0.6, tint=H("#a9bfae"), tint_amount=0.85)
    room(hs, 6, 6, 3, wall, L.pbr("h_floor", "old_linoleum_flooring_01", 0.6), ceil=MAT["white"])
    BED = C.template(A("bed.glb"), 2.0, axis=0)
    C.copy(BED, "bed", (0, 1.25, 0))
    D.box("curtain", (2.6, 0.05, 2.3), (2.4, 1.6, 1.25), L.plastic("curt", H("#7fa59a"), rough=0.9, coat=0))
    D.box("lamp", (1.4, 0.3, 0.06), (0, 0.6, 2.95), D.mat("tube", H("#eaffef"), emit=H("#eaffef"), emit_strength=8))
    D.area_light("h_tube", 260, (0, 0.6, 2.85), (0, 0.6, 0), size=1.4, rgb=H("#e2fbe6"))
    D.area_light("h_win", 90, (-2.8, -0.5, 1.8), (0, 1, 1.0), size=1.5, rgb=H("#ffe2b0"))
    walt, warm, _ = C.walt("walt_hs", (0, 0.72, -0.36), 0.0)
    pose(warm, walt, [(0, C.WSLUMP), (W["walt"] - 0.2, C.WSLUMP), (W["home"], C.WSIT)], t1=B[4] + 0.1)
    L.post(hs, bloom=0.25, vignette=0.38)
    shot(hs, "Hs_med", B[3], W["so"], (0.8, -2.9, 1.2), (0.6, -2.3, 1.15), (0, 0.8, 0.95), (0, 0.8, 1.0), 30)
    shot(hs, "Hs_face", W["so"], B[4], (0.35, -0.45, 1.22), (0.25, -0.2, 1.26), (0, 0.72, 1.28), (0, 0.72, 1.32), 48,
         dof=2.8, shake=0.003)

# ================================================================= DESERT: RV + blue; erased on "RV" / "desert" / "blue"
de = L.new_set("DESERT")
with L.building(de):
    L.hdri_world(de, "dry_cracked_lake", 1.0, rot_deg=40)
    sun = D.sun("d_sun", 5.0, (0.45, 0.55, -0.7), rgb=H("#fff0cc"), angle=2)
    desert_floor(de)
    rv = C.copy(RV, "rv_d", (0, 4.2, 0), yaw=-1.2)
    tbl = D.box("table", (1.3, 0.7, 0.04), (0.4, 0.6, 0.74), L.plastic("tb", H("#cfcfc6"), rough=0.6, coat=0))
    for dx in (-0.6, 0.6):
        for dy in (-0.3, 0.3):
            D.cyl("leg", 0.015, 0.74, (0.4 + dx, 0.6 + dy, 0.37), m=MAT["steel"])
    D.box("tray", (1.0, 0.5, 0.03), (0.4, 0.6, 0.775), MAT["steel"])
    CRY = C.template(A("crystals.glb"), 0.12, axis=2)
    crys = []
    for i in range(34):
        c = C.copy(CRY, "cr", (0.4 + random.uniform(-0.44, 0.44), 0.6 + random.uniform(-0.2, 0.2), 0.79),
                   s=random.uniform(0.6, 1.5), yaw=random.uniform(0, 6.3), mat=MAT["blue"])
        c.rotation_euler = (random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), c.rotation_euler.z)
        crys.append(c)
    blue_l = point("d_blue", 30, (0.4, 0.6, 1.0), rgb=H("#55c8ff"), r=0.3)
    # "no RV": it flattens into the sand
    D.key(rv, "scale", F(W["rv"]), (1, 1, 1))
    D.key(rv, "scale", F(W["rv"] + 0.35), (1, 1, 0))
    # "no desert": the world goes out — only the blue still glows
    bg = bg_node(de)
    key_val(bg, bg.inputs["Strength"], F(W["desert"]), 1.0)
    key_val(bg, bg.inputs["Strength"], F(W["desert"] + 0.4), 0.0)
    sun.data.energy = 5.0
    sun.data.keyframe_insert("energy", frame=F(W["desert"]))
    sun.data.energy = 0.0
    sun.data.keyframe_insert("energy", frame=F(W["desert"] + 0.4))
    for o in [o for o in de.collection.all_objects if o.name.startswith(("table", "leg", "tray"))]:
        D.key(o, "scale", F(W["desert"]), tuple(o.scale))
        D.key(o, "scale", F(W["desert"] + 0.3), (0, 0, 0))
    # "no blue": crystals wink out one by one
    for i, c in enumerate(crys):
        C.vanish(c, F(W["blue"] + 0.02 * i), dur_f=2)
    blue_l.data.keyframe_insert("energy", frame=F(W["blue"]))
    blue_l.data.energy = 0
    blue_l.data.keyframe_insert("energy", frame=F(W["blue"] + 0.4))
    L.post(de, bloom=0.4, vignette=0.32, contrast=0.08)
    shot(de, "D_wide", B[4], 16.51, (14, -16, 8), (10, -12, 4.5), (0, 3, 1.0), (0, 3, 1.2), 30, shake=0.006)
    shot(de, "D_low", 16.51, B[5], (-1.6, -1.9, 0.95), (-1.0, -1.2, 0.95), (0.4, 0.6, 0.8), (0.4, 1.4, 1.0), 26)
    shot(de, "D_void", B[5], B[6], (3.6, -6.2, 1.7), (3.0, -5.0, 1.5), (0.2, 2.2, 1.0), (0.3, 1.2, 0.85), 30)
