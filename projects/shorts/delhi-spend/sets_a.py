# exec'd by scene.py (names: D L C B W END F H MAT shot studio txt pose math random bpy). Sets GATE → POOL.
A = C.A
CASH = C.template(A("cash.glb"), 0.55, join=True)

# ================================================================= GATE: India Gate at golden hour, cash rains on you
gate = L.new_set("GATE", main=True)
L.hdri_world(gate, "belfast_sunset_puresky", 1.0, rot_deg=200)
D.sun("g_sun", 3.0, (0.4, 0.8, -0.5), rgb=H("#ffd2a0"), angle=6)
ig = C.template(A("india_gate.glb"), 42, axis=2, keep=lambda o: "Object_7" not in o.name)   # drop its 100 m ground
C.copy(ig, "india_gate", (0, 70, 0), mat=None)
D.box("g_lawn", (400, 400, 0.02), (0, 0, -0.01), L.pbr("g_grass", "leafy_grass", scale=0.5))
D.box("g_path", (14, 160, 0.03), (0, 40, 0.0), L.pbr("g_pave", "pavement_02", scale=0.6))
you, yarm, _ = C.man("you_g", (0, 0, 0), 0.0)
pose(yarm, you, [(0, C.LOOKUP), (3.6, C.LOOKUP), (3.9, C.CHEER)], t1=B[2])
for i in range(110):                                      # cash bundles tumble out of the sky from "spend"
    t0 = 2.6 + random.uniform(0, 3.4)
    x, y = random.uniform(-3.5, 3.5), random.uniform(-2.5, 4)
    c = C.copy(CASH, f"rain{i}", (x, y, 14), s=random.uniform(1.4, 2.4), yaw=random.uniform(0, 6.3))
    D.key(c, "location", F(t0), (x, y, 14))
    D.key(c, "location", F(t0 + 1.0), (x, y, 0.25 * (i % 5)), interp="LINEAR")
    D.key(c, "rotation_euler", F(t0), (random.uniform(-1, 1), random.uniform(-1, 1), c.rotation_euler.z))
    D.key(c, "rotation_euler", F(t0 + 1.0), (0, 0, c.rotation_euler.z + 1.5))
L.post(gate, bloom=0.4, vignette=0.25, warmth=0.1)
shot(gate, "A_hook", 0.0, B[1], (3.2, -9.5, 0.5), (1.4, -4.2, 1.1), (0, 30, 12), (0, 0, 1.55), 24, 30)
shot(gate, "A_rain", B[1], 4.13, (-1.6, -3.2, 0.9), (-1.2, -2.6, 1.0), (0, 0, 2.2), (0, 0, 2.6), 26)
shot(gate, "A_pile", 4.13, B[2], (2.2, -4.2, 3.2), (3.4, -6.5, 4.2), (0, 0, 1.0), (0, 1, 1.3), 26)

# ================================================================= FOOD: saffron studio, chole bhature towers
food = L.new_set("FOOD")
with L.building(food):
    studio(food, H("#ffb15c"), key_w=500, at=(0, 2, 1.0))
    THALI = C.template(A("thali.glb"), 0.42, join=True)
    wood = L.pbr("f_wood", "wood_table_001", scale=1.2)
    D.box("table", (1.4, 9, 0.08), (0, 4.0, 0.86), wood)
    for x in (-0.6, 0.6):
        for y in (-0.3, 8.3):
            D.box("tleg", (0.08, 0.08, 0.86), (x, y, 0.43), wood)
    cook, carm, _ = C.man("you_f", (0, 8.95, 0), 0.0)                 # at the far head of the table, facing us
    pose(carm, cook, [(0, C.STAND), (9.1, C.STAND), (9.4, C.CHEER)], t1=B[4])
    C.copy(THALI, "first", (0, 8.2, 0.9))
    k = 0
    for row in range(9):                                     # stacks race down the table, then flood the floor
        for x in (-0.38, 0.38):
            n = random.randint(4, 11)
            for j in range(n):
                p = C.copy(THALI, "st", (x, 7.4 - row * 0.9, 0.9 + j * 0.035), yaw=random.uniform(0, 6))
                C.pop(p, F(9.3 + row * 0.12 + j * 0.03), dur_f=6)
    for i in range(46):
        x, y = random.choice((-1, 1)) * random.uniform(1.2, 6), random.uniform(-1, 12)
        for j in range(random.randint(6, 28)):
            p = C.copy(THALI, "fl", (x, y, j * 0.035), yaw=random.uniform(0, 6))
            C.pop(p, F(10.9 + i * 0.03 + j * 0.01), dur_f=5)
    L.post(food, bloom=0.35)
    shot(food, "F_hungry", B[2], B[3], (0.5, 6.4, 1.5), (0.4, 6.9, 1.55), (0, 9, 1.4), (0, 9, 1.5), 32)
    shot(food, "F_stacks", B[3], 10.9, (0.9, -1.6, 1.5), (0.6, 0.2, 1.4), (0, 5, 1.0), (0, 6, 1.1), 26)
    shot(food, "F_flood", 10.9, B[4], (3.2, 1.0, 2.4), (4.4, -1.0, 3.4), (0, 6, 0.8), (0, 6, 0.7), 24)

# ================================================================= STREET: bazaar road, every auto rickshaw → gold
st = L.new_set("STREET")
with L.building(st):
    L.hdri_world(st, "kloofendal_48d_partly_cloudy_puresky", 1.0, rot_deg=60)
    D.sun("s_sun", 3.5, (0.5, 0.6, -0.6), rgb=H("#fff0d6"), angle=6)
    D.box("road", (16, 120, 0.02), (0, 40, 0), L.pbr("s_asph", "asphalt_02", scale=0.4))
    for side in (-1, 1):
        D.box("kerb", (3, 120, 0.15), (side * 9.5, 40, 0.07), L.pbr("s_pave", "pavement_02", scale=0.6))
        for i in range(16):                                  # painted Old-Delhi shopfronts
            h = random.uniform(7, 14)
            col = random.choice(("#ff6fae", "#ffcf3f", "#36c9b4", "#ff8a3d", "#8b6bff", "#5fd35f"))
            D.box("shop", (6, 6.6, h), (side * 14, -6 + i * 7, h / 2),
                  L.pbr(f"s_wall{side}{i}", "plastered_wall", scale=0.4, tint=H(col), tint_amount=0.8))
            D.box("awning", (1.6, 6.0, 0.12), (side * 10.6, -6 + i * 7, 3.2),
                  L.plastic(f"aw{side}{i}", H(random.choice(("#e23b3b", "#1f8fff", "#22b357"))), rough=0.5))
    RICK = C.template(A("rickshaw.glb"), 2.5, axis=1, join=True)
    for r in range(12):
        for c in range(4):
            x, y = -5.4 + c * 3.6 + random.uniform(-0.3, 0.3), 3 + r * 3.3 + random.uniform(-0.3, 0.3)
            yaw = math.pi + random.uniform(-0.12, 0.12)
            a = C.copy(RICK, "rick", (x, y, 0), yaw=yaw)
            g = C.copy(RICK, "rick_g", (x, y, 0), yaw=yaw, mat=MAT["gold"])
            t = 19.35 + r * 0.09 + c * 0.03                 # gold wave rolls up the street on "paint them gold"
            C.vanish(a, F(t))
            C.pop(g, F(t), dur_f=6, amount=1.25)
            for k in range(6):                               # jammed: engines idle-shake
                D.key(a, "location", F(13.6 + k * 0.5 + random.uniform(0, 0.2)), (x, y, 0.025 * (k % 2)))
    you, yarm, _ = C.man("you_s", (0.4, -0.2, 0), 0.0)
    pose(yarm, you, [(0, C.STAND), (14.3, C.SCRATCH), (16.6, C.STAND), (19.9, C.CHEER)], t1=B[6])
    L.post(st, bloom=0.45, vignette=0.22)
    shot(st, "S_jam", B[4], B[5], (1.6, -3.4, 1.2), (1.2, -2.6, 1.3), (0.3, 3, 1.4), (0.3, 3, 1.5), 28)
    shot(st, "S_fleet", B[5], 19.24, (-2.5, -6, 2.0), (-3.5, -10, 7.0), (0, 10, 1.0), (0, 16, 0.5), 26)
    shot(st, "S_gold", 19.24, B[6], (8, -12, 16), (9, -15, 20), (0, 18, 0), (0, 20, 0), 26)

# ================================================================= METRO: one train, one stop — your house
me = L.new_set("METRO")
with L.building(me):
    studio(me, H("#7ad3ff"), key_w=700, at=(0, 0, 2), hdri="kloofendal_48d_partly_cloudy_puresky", y_wall=60)
    D.sun("m_sun", 3.0, (0.4, 0.5, -0.7), angle=6)
    metro = D.empty("metro", (0, -90, 0))
    steel = D.mat("m_body", H("#d9dde2"), rough=0.25, metal=0.7)
    glass = D.mat("m_glass", H("#0d1b2a"), rough=0.05, emit=H("#1d3b5a"), emit_strength=0.4)
    stripe = L.plastic("m_red", H("#e8202a"), rough=0.3)
    for k in range(4):
        y = -k * 10.4
        D.box("car", (3.0, 10.0, 3.4), (0, y, 2.0), steel, bevel=0.25).parent = metro
        for side in (-1, 1):
            D.box("win", (0.04, 8.6, 1.0), (side * 1.51, y, 2.55), glass).parent = metro
            D.box("stripe", (0.04, 10.0, 0.22), (side * 1.51, y, 1.6), stripe).parent = metro
            for dy in (-2.8, 2.8):
                D.box("door", (0.05, 1.3, 2.4), (side * 1.52, y + dy, 1.75), D.mat("m_door", H("#8e959e"), rough=0.3, metal=0.8)).parent = metro
    D.box("nose", (2.8, 0.3, 2.0), (0, 5.1, 2.6), glass).parent = metro
    D.box("nose_red", (3.0, 0.2, 0.5), (0, 5.05, 1.3), stripe).parent = metro
    for x in (-0.75, 0.75):
        D.box("rail", (0.1, 200, 0.12), (x, 0, 0.06), D.mat("steel", H("#9aa3ad"), rough=0.3, metal=1.0))
    for i in range(60):
        D.box("sleeper", (2.4, 0.25, 0.08), (0, -100 + i * 3.4, 0.02), MAT["ink"])
    D.box("platform", (4, 30, 1.0), (4.2, 8, 0.5), L.pbr("m_conc", "concrete_floor_02", scale=0.5))
    D.box("p_edge", (0.4, 30, 1.02), (2.35, 8, 0.5), MAT["yellow"])
    hx, hy = 5.0, 22.0                                         # your little house where the line now ends
    D.box("h_wall", (4.5, 4, 3.2), (hx, hy, 2.6), L.pbr("h_wall", "plastered_wall", scale=0.6, tint=H("#ffd9a0")))
    roof = D.cone("h_roof", 3.6, 2.2, (hx, hy, 5.3), m=L.pbr("h_brick", "red_brick_03", scale=0.8), verts=4)
    roof.rotation_euler = (0, 0, math.pi / 4)
    D.box("h_door", (1.0, 0.08, 1.9), (hx - 0.6, hy - 2.02, 1.95), MAT["red"])
    D.box("h_win", (0.9, 0.08, 0.8), (hx + 1.2, hy - 2.02, 2.7), MAT["txt"])
    sign = txt("YOUR HOUSE", 0.45, (hx - 1.7, 11.5, 3.4), MAT["txt"], rot=(math.pi / 2, 0, -0.4))
    D.cyl("sign_post", 0.06, 3.0, (hx - 1.7, 11.6, 1.5), m=MAT["ink"])
    D.box("sign_bg", (2.9, 0.06, 0.7), (hx - 1.7, 11.62, 3.4), MAT["red"]).rotation_euler = (0, 0, -0.4)
    D.key(metro, "location", F(B[6] + 0.1), (0, -110, 0))
    D.key(metro, "location", F(23.6), (0, 120, 0), interp="LINEAR")     # crowded train blasts past
    D.key(metro, "location", F(25.3), (0, -70, 0))
    D.key(metro, "location", F(26.95), (0, 14, 0))                       # ...then glides in and stops at your door
    you, yarm, _ = C.man("you_m", (hx - 0.6, 15.0, 1.0), 0.6)
    pose(yarm, you, [(0, C.STAND), (26.7, C.STAND), (27.0, C.CHEER)], t1=B[8])
    L.post(me, bloom=0.35)
    shot(me, "M_rush", B[6], B[7], (5.5, -6, 2.2), (5.2, -4, 2.3), (0, 4, 2.2), (0, 8, 2.2), 24, shake=0.012)
    shot(me, "M_buy", B[7], 25.42, (-9, -4, 7), (-11, -8, 9), (2, 14, 2.5), (2, 16, 2.5), 26)
    shot(me, "M_house", 25.42, B[8], (-9, -3, 7.5), (-8, 1, 6.5), (2.5, 18, 2.2), (3.5, 19, 2.4), 26)

# ================================================================= POOL: a swimming pool of butter chicken
po = L.new_set("POOL")
with L.building(po):
    studio(po, H("#5ad1c4"), key_w=600, at=(0, 0, 0.6))
    BC = C.template(A("butter_chicken.glb"), 0.6, decimate=0.25, join=True)
    tile = L.plastic("tile", H("#e8fbff"), rough=0.25)
    for (sx, sy, x, y) in ((9.2, 0.4, 0, -2.7), (9.2, 0.4, 0, 2.7), (0.4, 5.8, -4.4, 0), (0.4, 5.8, 4.4, 0)):
        D.box("pool_wall", (sx, sy, 0.7), (x, y, 0.35), tile, bevel=0.03)
    gravy = D.mat("gravy", H("#e8661c"), rough=0.3, emit=H("#c94a12"), emit_strength=0.15)
    gb = gravy.node_tree.nodes["Principled BSDF"]
    if "Coat Weight" in gb.inputs:
        gb.inputs["Coat Weight"].default_value = 0.8
    surf = D.box("gravy", (8.4, 5.0, 0.04), (0, 0, 0.6), gravy)
    md = surf.modifiers.new("sub", "SUBSURF")
    md.levels = md.render_levels = 4
    md.subdivision_type = "SIMPLE"
    wv = surf.modifiers.new("wave", "WAVE")
    wv.height, wv.width, wv.speed = 0.03, 0.9, 0.12
    for (x, y) in ((-2.8, -3.6), (2.6, -3.7), (5.2, 1.4), (-5.2, -1.0), (0.2, 3.6)):
        C.copy(BC, "bc", (x, y, 0), s=1.0, yaw=random.uniform(0, 6))
    hero = C.copy(BC, "bc_hero", (2.2, -4.4, 0.75), s=1.0, yaw=0.4)
    D.cyl("ped", 0.5, 0.75, (2.2, -4.4, 0.375), m=MAT["white"], verts=40)
    you, yarm, _ = C.man("you_p", (-0.6, -3.4, 0), 0.0)
    pose(yarm, you, [(0, C.STAND), (32.9, C.STAND), (33.15, C.CHEER)], t1=B[10])
    for t, loc in ((33.2, (-0.6, -3.4, 0)), (33.5, (-0.4, -2.0, 1.5)), (33.75, (-0.2, -0.8, 0.6)), (34.0, (0, -0.2, -2.4))):
        D.key(you, "location", F(t), loc)
    for i in range(40):                                          # gravy splash
        ang, r = random.uniform(0, 6.3), random.uniform(0.6, 2.4)
        d = D.sphere("drop", random.uniform(0.05, 0.13), (-0.1, -0.5, 0.65), m=gravy, seg=12, rings=8)
        D.key(d, "scale", 1, (0, 0, 0))
        D.key(d, "scale", F(33.8), (0, 0, 0))
        D.key(d, "scale", F(33.85), (1, 1, 1))
        D.key(d, "location", F(33.85), (-0.1, -0.5, 0.65))
        D.key(d, "location", F(34.15), (-0.1 + r * math.cos(ang), -0.5 + r * math.sin(ang), random.uniform(1.4, 2.8)))
        D.key(d, "location", F(34.6), (-0.1 + 1.6 * r * math.cos(ang), -0.5 + 1.6 * r * math.sin(ang), 0.6))
        D.key(d, "scale", F(34.6), (0.6, 0.6, 0.6))
        D.key(d, "scale", F(34.65), (0, 0, 0))
    L.post(po, bloom=0.35)
    shot(po, "P_bowl", B[8], B[9], (2.7, -5.6, 1.35), (2.5, -5.3, 1.2), (2.2, -4.4, 0.85), (2.2, -4.4, 0.82), 40, dof=4)
    shot(po, "P_pool", B[9], 32.9, (-6.5, -8.5, 6.5), (-4.5, -7.0, 4.8), (0, 0, 0.5), (0, -0.8, 0.6), 26)
    shot(po, "P_jump", 32.9, B[10], (5.5, -6.0, 1.6), (4.8, -5.2, 1.7), (-0.3, -1.4, 1.1), (-0.2, -0.6, 0.9), 26,
         shake=0.01)
