# exec'd by scene.py after sets_a.py. ROOF → HAT.

# ================================================================= ROOF: the pizza on the roof → gone
rf = L.new_set("ROOF")
with L.building(rf):
    L.hdri_world(rf, "kloofendal_48d_partly_cloudy_puresky", 1.0, rot_deg=120)
    D.sun("r_sun", 4.0, (0.3, 0.7, -0.6), rgb=H("#fff1d8"), angle=3)
    D.box("lawn", (200, 200, 0.02), (0, 0, -0.01), L.pbr("r_dirt", "dry_ground_rocks", 0.4, tint=H("#a59a6a"),
                                                            tint_amount=0.5))
    D.box("drive", (4, 14, 0.03), (2.5, -3, 0.0), L.pbr("r_conc", "concrete_floor_02", 0.5))
    stucco = L.pbr("r_stucco", "plastered_wall", 0.5, tint=H("#cfae82"), tint_amount=0.85)
    D.box("house", (14, 9, 3.0), (0, 5.5, 1.5), stucco)
    roof = L.pbr("r_roof", "grey_roof_tiles", 0.8, tint=H("#6a6058"), tint_amount=0.4)
    for s in (-1, 1):                                     # low ranch-house gable
        r = D.box("roof", (15, 5.2, 0.15), (0, 5.5 + s * 2.3, 3.45), roof)
        r.rotation_euler = (s * -0.2, 0, 0)
    D.box("fascia", (15, 0.12, 0.25), (0, 0.95, 3.0), MAT["white"])
    D.box("gdoor", (3.2, 0.06, 2.3), (2.5, 0.98, 1.15), L.plastic("gd", H("#ece4d2"), rough=0.5, coat=0))
    for x in (-4.5, -1.8):
        D.box("win", (1.6, 0.06, 1.2), (x, 0.98, 1.6), D.mat("glass", H("#1b2328"), rough=0.08, metal=0.4))
    PZ = C.template(A("pizza.glb"), 0.45, decimate=0.2)
    pz = C.copy(PZ, "pizza", (0.6, 1.9, 3.3), s=1.5)
    pz.rotation_euler = (0.2, 0.0, 0.4)
    C.vanish(pz, F(W["roof"] + 0.25), dur_f=3)
    L.post(rf, bloom=0.25, vignette=0.32)
    shot(rf, "R_roof", B[6], B[7], (-2.2, -6.5, 6.4), (-0.4, -1.6, 4.9), (0.4, 1.6, 3.2), (0.6, 1.9, 3.3), 32, 48)

# ================================================================= CLASS: chemistry, 25 more years (clock spins)
cl = L.new_set("CLASS")
with L.building(cl):
    dark_world(cl, "#1d211c", 1.0)
    wall = L.pbr("c_wall", "painted_plaster_wall", 0.6, tint=H("#c2c7a2"), tint_amount=0.85)
    room(cl, 9, 9, 3.2, wall, L.pbr("c_floor", "old_linoleum_flooring_01", 0.5), ceil=MAT["white"])
    D.box("board_frame", (4.3, 0.06, 1.55), (0, 4.42, 1.65), L.pbr("c_wood", "wood_table_001", 1.0))
    D.box("board", (4.1, 0.06, 1.35), (0, 4.39, 1.65), D.mat("board", H("#25352b"), rough=0.95))
    rot = (math.pi / 2, 0, math.pi)                       # text faces -Y
    for body, size, loc in (("CHEMISTRY", 0.26, (0, 4.35, 2.08)), ("is the study of", 0.12, (-0.9, 4.35, 1.8)),
                            ("CHANGE.", 0.2, (0.55, 4.35, 1.8)), ("H2O   NaCl   C6H12O6", 0.14, (0, 4.35, 1.45)),
                            ("Mr. White - Chem 101", 0.1, (1.25, 4.35, 1.15))):
        t = txt(body, size, loc, MAT["chalk"], font=CHALK)
        t.rotation_euler = (math.pi / 2, 0, 0)
    DESK = C.template(A("desk.glb"), 1.0, axis=0, decimate=0.5)
    for r in range(3):
        for c in range(3):
            C.copy(DESK, "desk", (-2.6 + c * 2.6, -0.6 - r * 1.6, 0), yaw=math.pi)
    walt, warm, _ = C.walt("walt_c", (-0.7, 3.5, 0), 0.25)
    pose(warm, walt, [(0, C.WPOINT)])
    # wall clock (right wall, facing -X), hands spin through 25 years
    clk = D.empty("clock", (4.4, 1.0, 2.35))
    face = D.cyl("c_face", 0.3, 0.04, (0, 0, 0), rot=(0, math.pi / 2, 0), m=MAT["white"], verts=48)
    rim = D.torus("c_rim", 0.3, 0.025, (0, 0, 0), rot=(0, math.pi / 2, 0), m=MAT["ink"])
    for o in (face, rim):
        o.parent = clk
    hands = []
    for k, (ln, w) in enumerate(((0.24, 0.012), (0.16, 0.02))):
        piv = D.empty(f"hand_piv{k}", (-0.03 - 0.005 * k, 0, 0))
        piv.parent = clk
        hnd = D.box(f"hand{k}", (0.005, w, ln), (0, 0, ln / 2 - 0.03), MAT["ink"])
        hnd.parent = piv
        hands.append(piv)
    for k, turns in ((0, 60), (1, 5)):
        D.key(hands[k], "rotation_euler", F(W["for"] - 0.2), (0.4 * k, 0, 0), interp="LINEAR")
        D.key(hands[k], "rotation_euler", F(B[8] + 0.1), (0.4 * k - turns * 2 * math.pi, 0, 0), interp="LINEAR")
    D.area_light("c_tubes", 420, (0, 0.5, 3.1), (0, 0.5, 0), size=4, rgb=H("#eef7dc"))
    D.area_light("c_win", 160, (-4.3, 0.5, 2.0), (0, 1, 1.2), size=2.5, rgb=H("#fff0c4"))
    L.post(cl, bloom=0.2, vignette=0.35)
    shot(cl, "C_wide", B[7], W["for"], (0.9, -4.0, 1.75), (0.6, -2.6, 1.65), (-0.5, 3.5, 1.4), (-0.6, 3.5, 1.5), 30)
    shot(cl, "C_clock", W["for"], B[8], (2.9, 0.2, 2.15), (3.4, 0.6, 2.3), (4.4, 1.0, 2.35), (4.4, 1.0, 2.35), 40)

# ================================================================= CAKE: 75 candles, alone
ck = L.new_set("CAKE")
with L.building(ck):
    dark_world(ck, "#0a0a08", 1.0)
    wall = L.pbr("k_wall", "decrepit_wallpaper", 0.8, tint=H("#c9b27a"), tint_amount=0.5)
    room(ck, 5, 5, 2.7, wall, L.pbr("k_floor", "laminate_floor_02", 0.8))
    wood = L.pbr("k_wood", "wood_table_001", 1.2)
    D.box("table", (1.6, 0.9, 0.05), (0, 0.4, 0.75), wood)
    for dx in (-0.72, 0.72):
        for dy in (-0.36, 0.36):
            D.box("tleg", (0.06, 0.06, 0.75), (dx, 0.4 + dy, 0.375), wood)
    D.box("chair", (0.48, 0.48, 0.05), (0, 1.15, 0.46), wood)
    D.box("chair_back", (0.48, 0.05, 0.6), (0, 1.39, 0.78), wood)
    CAKE = C.template(A("cake.glb"), 0.26, axis=0)
    C.copy(CAKE, "cake", (0, 0.25, 0.775))
    wax = L.plastic("wax", H("#7fd0ff"), rough=0.4, coat=0)
    flames = []
    for k, (dig, x) in enumerate((("7", -0.045), ("5", 0.045))):
        t = D.text3d("cand" + dig, dig, 0.09, (x, 0.22, 1.04), wax, extrude=0.012, bevel=0.002, font=FONT)
        fl = D.sphere("flame", 0.009, (x, 0.22, 1.105), m=MAT["flame"], seg=12, rings=8)
        fl.scale = (1, 1, 2.0)
        flames.append(fl)
    cl_ = point("k_candle", 6, (0, 0.2, 1.13), rgb=H("#ffae5c"), r=0.02)
    for i in range(0, int((END) * 6)):
        cl_.data.energy = random.uniform(4.8, 7.2)
        cl_.data.keyframe_insert("energy", frame=F(i / 6))
    spot("k_pendant", 420, (0, 0.7, 2.6), (0, 0.7, 0.8), size_deg=70, blend=0.8, rgb=H("#ffd79a"))
    D.area_light("k_fill", 45, (2, -2, 1.6), (0, 0.8, 1.0), size=2, rgb=H("#7d9aa8"))
    walt, warm, _ = C.walt("walt_k", (0, 1.12, -0.52), 0.0)
    D.area_light("k_face", 30, (0.25, 0.1, 1.05), (0, 1.1, 1.25), size=0.4, rgb=H("#ffb46a"))
    pose(warm, walt, [(0, C.WSIT | {"Spine": (0, -0.1, 1), "Neck": (0, -0.15, 1), "Head": (0, -0.4, 1)})])
    L.post(ck, bloom=0.45, vignette=0.45)
    shot(ck, "K_wide", B[8], W["nobody"], (0.7, -2.2, 1.05), (0.45, -1.6, 1.05), (0, 0.6, 1.0), (0, 0.8, 1.05), 30)
    shot(ck, "K_face", W["nobody"], B[9], (0.36, -0.1, 1.2), (0.28, 0.28, 1.22), (0, 1.12, 1.24), (0, 1.12, 1.26),
         50, dof=2.0, shake=0.002)

# ================================================================= GARAGE: the box → a formula, 99.1 %, glowing blue
ga = L.new_set("GARAGE")
with L.building(ga):
    dark_world(ga, "#07080a", 1.0)
    room(ga, 6, 6, 2.8, L.pbr("g_wall", "dirty_concrete", 0.5), L.pbr("g_floor", "concrete_floor_02", 0.5))
    wood = L.pbr("g_wood", "wood_table_001", 1.0)
    D.box("bench", (2.4, 0.8, 0.08), (0, 2.5, 0.9), wood)
    for dx in (-1.1, 1.1):
        D.box("bleg", (0.08, 0.7, 0.9), (dx, 2.5, 0.45), wood)
    D.box("pegboard", (2.4, 0.04, 1.0), (0, 2.95, 1.6), L.plastic("peg", H("#a98d62"), rough=0.9, coat=0))
    bx = D.empty("box", (0, 2.45, 0.94))
    bw, bd, bh = 0.5, 0.38, 0.3
    for nm, size, loc in (("b_floor", (bw, bd, 0.01), (0, 0, 0.005)), ("b_front", (bw, 0.01, bh), (0, -bd / 2, bh / 2)),
                          ("b_back", (bw, 0.01, bh), (0, bd / 2, bh / 2)), ("b_l", (0.01, bd, bh), (-bw / 2, 0, bh / 2)),
                          ("b_r", (0.01, bd, bh), (bw / 2, 0, bh / 2))):
        D.box(nm, size, loc, MAT["card"]).parent = bx
    lbl = txt("W.W.", 0.06, (0.0, -bd / 2 - 0.007, bh * 0.6), MAT["ink"], font=FONT)
    lbl.parent = bx
    flaps = []
    for side, (axis, piv_loc, size, off) in {
            "f": ("X", (0, -bd / 2, bh), (bw, bd / 2, 0.008), (0, bd / 4, 0)),
            "b": ("X", (0, bd / 2, bh), (bw, bd / 2, 0.008), (0, -bd / 4, 0))}.items():
        piv = D.empty("flap_" + side, piv_loc)
        piv.parent = bx
        D.box("flap", size, off, MAT["card"]).parent = piv
        flaps.append((piv, -1 if side == "f" else 1))
    for piv, s in flaps:                                  # flaps swing open on "box"
        D.key(piv, "rotation_euler", F(W["box"] - 0.1), (0, 0, 0))
        D.overshoot(piv, "rotation_euler", F(W["box"] - 0.1), F(W["box"] + 0.6), (0, 0, 0), (s * 2.1, 0, 0), 1.06)
    paper = D.box("paper", (0.3, 0.22, 0.004), (-0.06, 0.0, 0.02), MAT["paper"])
    paper.parent = bx
    paper.rotation_euler = (0, 0, 0.12)
    for body, size, loc in (("99.1%", 0.06, (-0.07, -0.02, 0.026)), ("FORMULA - W.W.", 0.018, (-0.07, 0.05, 0.023))):
        t = D.text3d("pt", body, size, loc, MAT["ink"], extrude=0, bevel=0, font=CHALK, rot=(0, 0, 0.12))
        t.parent = bx
    CRY = C.template(A("crystals.glb"), 0.1, axis=2)
    cr = C.copy(CRY, "crystal", (0.14, 0.04, 0.012), mat=D.mat("blue_soft", H("#1e9bff"), rough=0.1, emit=H("#1e8fff"), emit_strength=1.2))
    cr.parent = bx
    glow = point("g_blue", 0, (0.14, 2.49, 1.12), rgb=H("#4cc6ff"), r=0.1)
    glow.data.keyframe_insert("energy", frame=F(W["box"]))
    glow.data.energy = 6
    glow.data.keyframe_insert("energy", frame=F(W["box"] + 0.7))
    bulb = D.empty("bulb_sway", (0, 2.0, 2.8))
    cord = D.cyl("cord", 0.004, 0.75, (0, 0, -0.375), m=MAT["ink"])
    gl = D.sphere("bulb", 0.035, (0, 0, -0.78), m=D.mat("bulb_m", H("#ffd69a"), emit=H("#ffc977"), emit_strength=30))
    lamp = point("g_bulb", 70, (0, 0, -0.84), rgb=H("#ffcf8a"), r=0.03)
    for o in (cord, gl, lamp):
        o.parent = bulb
    for i in range(10):
        D.key(bulb, "rotation_euler", F(B[9] + i * 1.0), (0.05 * (-1) ** i, 0.03 * (-1) ** i, 0))
    L.post(ga, bloom=0.5, vignette=0.45)
    shot(ga, "G_wide", B[9], W["box"], (1.4, -0.8, 1.75), (1.0, 0.0, 1.65), (0, 2.45, 1.05), (0, 2.45, 1.05), 30)
    shot(ga, "G_open", W["box"], W["ninety-nine"], (0.05, 1.75, 1.85), (0.02, 1.98, 1.7), (0, 2.46, 0.95),
         (0, 2.46, 0.95), 42, shake=0.002)
    shot(ga, "G_macro", W["ninety-nine"], B[11], (0.3, 2.18, 1.5), (0.2, 2.28, 1.4), (0.06, 2.47, 0.98),
         (0.1, 2.48, 0.99), 50, dof=2.8, shake=0.0015)

# ================================================================= HAT: the hat on the table, one light comes on
ht = L.new_set("HAT")
with L.building(ht):
    dark_world(ht, "#000000", 0.0)
    D.box("h_table", (3, 2, 0.06), (0, 0, 0.77), L.pbr("h_wood", "wood_table_001", 1.0))
    hat = C.porkpie(None, "hat_t", (0, 0, 0.8))
    hat.rotation_euler = (0, 0, 0.35)
    sp = spot("h_spot", 0, (0, 0.3, 3.0), (0, 0, 0.8), size_deg=22, blend=0.35, rgb=H("#fff3dc"))
    sp.data.keyframe_insert("energy", frame=F(B[11] + 0.05))
    sp.data.energy = 900
    sp.data.keyframe_insert("energy", frame=F(B[11] + 0.25))
    D.area_light("h_rim", 60, (0.8, 1.6, 1.3), (0, 0, 0.85), size=1, rgb=H("#9fc6ff"))
    L.post(ht, bloom=0.2, vignette=0.5)
    shot(ht, "T_hat", B[11], B[12], (0.0, -1.6, 1.15), (0.0, -0.75, 0.98), (0, 0, 0.85), (0, 0, 0.86), 45,
         shake=0.0015)
