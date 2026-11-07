# exec'd by scene.py after sets_a.py. Sets GOLD → VI3W.
A = C.A
HEAVY = C.STAND | {"Spine": (0, -0.3, 1), "Neck": (0, -0.5, 1), "Head": (0, -0.9, 0.5),
                   "LeftArm": (0.15, -0.05, -1), "RightArm": (-0.15, -0.05, -1)}
DHOL = C.STAND | {"LeftArm": (0.45, -0.6, -0.6), "RightArm": (-0.45, -0.6, -0.6), "LeftForeArm": (-0.3, -0.9, 0.15),
                  "RightForeArm": (0.3, -0.9, 0.15)}

# ================================================================= GOLD: Karol Bagh jeweller, 80 kg of gold
go = L.new_set("GOLD")
with L.building(go):
    studio(go, H("#7a1027"), key_w=650, at=(0, 0, 1.4))
    BAR = C.template(A("gold_bar.glb"), 0.5, join=True)
    for i in range(70):                                      # walls of bars behind the counter
        x, z = -4.5 + (i % 14) * 0.7, 0.2 + (i // 14) * 0.6
        C.copy(BAR, "bar_w", (x, 3.2, z), yaw=random.uniform(-0.2, 0.2), mat=MAT["gold"])
    D.box("shelf", (10, 0.8, 3.4), (0, 3.6, 1.7), L.plastic("velvet", H("#3b0614"), rough=0.8))
    D.box("counter", (6, 1.0, 1.0), (0, 1.6, 0.5), L.pbr("g_wood", "wood_table_001", scale=1.0))
    for i in range(12):
        C.copy(BAR, "bar_c", (-2.4 + i * 0.42, 1.6, 1.0), yaw=random.uniform(-0.3, 0.3), mat=MAT["gold"])
    CHAIN = C.template(A("chain.glb"), 0.36, base=False, join=True)
    you, yarm, _ = C.man("you_go", (0, -0.4, 0), 0.0)
    pose(yarm, you, [(0, C.STAND), (37.8, C.STAND), (38.1, C.CHEER), (39.9, C.CHEER), (40.2, HEAVY)], t1=B[12])
    for i in range(9):                                      # chains pile on, each one bigger
        ch = C.copy(CHAIN, f"chain{i}", (0, -0.47 - i * 0.012, 1.38 - i * 0.045),
                    s=1.0 + i * 0.12, mat=MAT["gold"])
        ch.rotation_euler = (math.radians(-10), 0, 0)
        ch.parent = you
        ch.location = (0, -0.07 - i * 0.012, 1.38 - i * 0.045)
        C.pop(ch, F(37.9 + i * 0.16), dur_f=5)
    D.key(you, "location", F(40.1), (0, -0.4, 0))
    D.key(you, "location", F(41.0), (0, -0.4, -0.75))                    # sinks through the floor
    crack = D.cyl("crack", 0.9, 0.01, (0, -0.4, 0.005), m=MAT["ink"], verts=7)
    C.pop(crack, F(40.15), dur_f=3)
    L.post(go, bloom=0.5, bloom_threshold=0.8)
    shot(go, "G_shop", B[10], B[11], (-3.5, -6.5, 2.2), (-2.2, -5.2, 1.9), (0, 1.5, 1.2), (0, 1.0, 1.3), 26)
    shot(go, "G_chains", B[11], 39.78, (0.6, -2.0, 1.55), (0.45, -1.7, 1.5), (0, -0.4, 1.35), (0, -0.4, 1.3), 34)
    shot(go, "G_sink", 39.78, B[12], (1.4, -2.6, 0.6), (1.1, -2.2, 0.5), (0, -0.4, 1.0), (0, -0.4, 0.5), 26,
         shake=0.012)

# ================================================================= BARAAT: night street party, dhol crowd, fireworks
ba = L.new_set("BARAAT")
with L.building(ba):
    L.hdri_world(ba, "studio_small_09", 0.12, backdrop=H("#0a0d2b"))
    D.box("b_road", (60, 60, 0.02), (0, 10, 0), L.pbr("b_asph", "asphalt_02", scale=0.4))
    DH = C.template(A("dhol.glb"), 0.62, axis=1, base=False, decimate=0.3, join=True, rot=("Z", math.pi / 2))
    tmp, tarm, tbody = C.man("tmp", (0, 0, 0), 0.0)                       # bake one drummer pose → crowd mesh
    C.pose_strip(tarm, tmp, [(1, DHOL), (2, DHOL)], 1, 2, blend=0)
    ba.frame_set(1)
    drummer = D.bake(tarm, tbody, "drummer")
    for o in [tmp, tarm, *tbody]:
        bpy.data.objects.remove(o)
    kurtas = [L.plastic(f"kurta{i}", H(c), rough=0.5) for i, c in
              enumerate(("#ff8a1f", "#ff4fa3", "#ffd23f", "#2fd1c5", "#ffffff"))]
    drummer.materials.append(kurtas[0])
    for r in range(7):
        for c in range(7):
            x, y = -6 + c * 2.0 + random.uniform(-0.3, 0.3), 2.5 + r * 2.0 + random.uniform(-0.3, 0.3)
            p = bpy.data.objects.new("drummer", drummer)
            D.link(p)
            p.location = (x, y, 0)
            p.material_slots[0].link = "OBJECT"
            p.material_slots[0].material = random.choice(kurtas)
            d = C.copy(DH, "dhol", (x, y - 0.38, 1.05), mat=None)
            for k in range(30):                                  # everyone bounces on the beat
                z = 0.06 if k % 2 else 0.0
                tt = 41.9 + k * 0.25 + random.uniform(0, 0.05)
                D.key(p, "location", F(tt), (x, y, z))
                D.key(d, "location", F(tt), (x, y - 0.38, 1.05 + z))
    for i in range(40):                                          # string lights overhead
        for side in (-1, 1):
            D.sphere("bulb", 0.07, (side * 8 + side * -0.0, -2 + i * 0.6, 4.2 - 0.6 * math.sin(i / 39 * math.pi)),
                     m=L.plastic(f"bulb{i % 3}", H(("#ffcf5a", "#ff5fb0", "#5affd8")[i % 3]),
                                 emit=H(("#ffcf5a", "#ff5fb0", "#5affd8")[i % 3]), emit_strength=6), seg=8, rings=6)
    you, yarm, _ = C.man("you_b", (0, -0.5, 0), 0.0)
    pose(yarm, you, [(0, C.CHEER)], t1=B[14])
    for k in range(24):
        D.key(you, "location", F(41.9 + k * 0.3), (0, -0.5, 0.12 if k % 2 else 0))
    D.area_light("b_key", 600, (-3, -5, 5), (0, 2, 1), size=4, rgb=H("#ffb35a"))
    D.area_light("b_fill", 400, (4, -2, 4), (0, 4, 1), size=4, rgb=H("#7a5cff"))
    for n, (bx, by, bz, col) in enumerate(((-4, 14, 13, "#ff3d6e"), (3, 18, 15, "#ffd23f"), (0, 12, 17, "#3dffb5"),
                                           (5, 10, 12, "#6a8bff"), (-2, 20, 19, "#ff8a1f"))):
        t0 = 47.3 + n * 0.32
        fm = L.plastic(f"fw{n}", H(col), emit=H(col), emit_strength=12)
        for i in range(26):
            u, v = random.uniform(-1, 1), random.uniform(0, 6.3)
            dx, dy, dz = math.sqrt(1 - u * u) * math.cos(v), math.sqrt(1 - u * u) * math.sin(v), u
            s = D.sphere("spark", 0.12, (bx, by, bz), m=fm, seg=8, rings=6)
            D.key(s, "scale", 1, (0, 0, 0))
            D.key(s, "scale", F(t0), (0, 0, 0))
            D.key(s, "scale", F(t0) + 1, (1, 1, 1))
            D.key(s, "location", F(t0), (bx, by, bz))
            D.key(s, "location", F(t0 + 0.9), (bx + 4 * dx, by + 4 * dy, bz + 4 * dz - 0.8))
            D.key(s, "scale", F(t0 + 1.3), (0, 0, 0))
    L.post(ba, bloom=0.8, bloom_threshold=0.7, vignette=0.3)
    shot(ba, "R_hero", B[12], 44.2, (0.6, -3.0, 1.6), (0.5, -2.5, 1.6), (0, -0.5, 1.5), (0, -0.5, 1.55), 30)
    shot(ba, "R_crowd", 44.2, B[13], (-3, -6, 0.6), (-2, -5, 0.8), (0, 6, 1.6), (0, 6, 1.4), 24)
    shot(ba, "R_up", B[13], 47.25, (2, -4, 4.5), (3, -7, 9), (0, 6, 0.5), (0, 8, 1.0), 26)
    shot(ba, "R_fire", 47.25, B[14], (0, -7, 1.2), (0, -7.5, 1.4), (0, 8, 9), (0, 10, 13), 24)

# ================================================================= SMOG: grey Delhi, a fan as tall as Qutub Minar
sm = L.new_set("SMOG")
with L.building(sm):
    w = L.hdri_world(sm, "kloofendal_48d_partly_cloudy_puresky", 0.8, backdrop=H("#8f8a7c"))
    bgc = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND" and not n.inputs["Color"].is_linked)
    for t, c in ((54.3, "#8f8a7c"), (55.4, "#58aaff")):
        bgc.inputs["Color"].default_value = (*H(c), 1)
        bgc.inputs["Color"].keyframe_insert("default_value", frame=F(t))
    D.sun("q_sun", 3.0, (0.4, 0.6, -0.6), rgb=H("#ffe9c9"), angle=8)
    D.box("q_ground", (400, 400, 0.02), (0, 60, 0), L.pbr("q_pave", "pavement_02", scale=0.3))
    for i in range(70):
        h = random.uniform(8, 40)
        x, y = random.uniform(-90, 90), random.uniform(30, 160)
        D.box("tower", (random.uniform(6, 12), random.uniform(6, 12), h), (x, y, h / 2),
              L.pbr(f"q_w{i % 5}", "plastered_wall", scale=0.2,
                    tint=H(("#d9c7a8", "#c9b8d9", "#a8c9d9", "#e3b38f", "#bfbfbf")[i % 5]), tint_amount=0.6))
    fan = D.empty("fan", (-14, 30, 0))                         # 75 m tall, blowing toward +X
    fm = D.mat("fanblue", H("#2aa6ff"), rough=0.3)
    D.cyl("f_pole", 1.6, 60, (0, 0, 30), m=MAT["white"], verts=32).parent = fan
    D.cyl("f_base", 9, 1.6, (0, 0, 0.8), m=MAT["white"], verts=48).parent = fan
    head = D.empty("f_head", (0, 0, 62))
    head.parent = fan
    D.sphere("f_motor", 4.2, (-3, 0, 0), m=MAT["white"]).parent = head
    for k in range(5):
        rg = D.torus("f_guard", 12.5 - k * 2.5, 0.25, (3.5, 0, 0), rot=(0, math.pi / 2, 0), m=D.mat("chrome", H("#d8dde3"), rough=0.2, metal=1.0))
        rg.parent = head
    hub = D.empty("f_hub", (3, 0, 0))
    hub.parent = head
    for k in range(3):
        bl = D.sphere("blade", 5.5, (0, 0, 0), m=fm, seg=24, rings=12)
        bl.scale = (0.12, 0.42, 1.0)
        bl.location = (0, 6.0 * math.sin(k * 2.094), 6.0 * math.cos(k * 2.094))
        bl.rotation_euler = (-k * 2.094, 0.35, 0)
        bl.parent = hub
    D.key(hub, "rotation_euler", F(52.4), (0, 0, 0))
    D.key(hub, "rotation_euler", F(53.4), (math.radians(400), 0, 0))
    D.key(hub, "rotation_euler", F(END), (math.radians(400 + 1500 * (END - 53.4)), 0, 0), interp="LINEAR")
    smog = D.mat("smog", H("#b9b09a"), rough=1.0, emit=H("#8f8878"), emit_strength=0.5)
    smog.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.5
    smog.surface_render_method = "DITHERED"
    for i in range(80):
        x, y, z = random.uniform(-30, 45), random.uniform(8, 80), random.uniform(2, 45)
        s = D.ico("smog", random.uniform(4, 9), (x, y, z), m=smog, sub=3)
        s.visible_shadow = False
        D.key(s, "location", F(53.8 + random.uniform(0, 0.5)), (x, y, z))
        D.key(s, "location", F(55.6 + random.uniform(0, 0.6)), (x + 160, y + 20, z + 25))
        D.key(s, "scale", F(54.0), (1, 1, 1))
        D.key(s, "scale", F(56.0), (0.2, 0.2, 0.2))
    you, yarm, _ = C.man("you_q", (0, -2, 0), 0.25)
    pose(yarm, you, [(0, C.STAND), (50.6, C.SCRATCH), (52.3, C.LOOKUP), (55.5, C.CHEER)], t1=B[16])
    L.post(sm, bloom=0.35)
    shot(sm, "Q_cough", B[14], B[15], (1.6, -6.0, 1.6), (1.2, -5.2, 1.6), (0, -2, 1.4), (0, -2, 1.5), 30)
    shot(sm, "Q_fan", B[15], 54.3, (6, -10, 1.0), (8, -14, 2.0), (-12, 30, 20), (-12, 30, 55), 22)
    shot(sm, "Q_clear", 54.3, B[16], (40, -60, 30), (30, -50, 24), (-10, 30, 35), (-5, 30, 30), 26)

# ================================================================= BANK: midnight cash mountain, you buy the bank
bk = L.new_set("BANK")
with L.building(bk):
    studio(bk, H("#121a3d"), strength=0.5, key_w=700, at=(0, 0, 2), y_wall=45)
    CASH2 = CASH
    for i in range(260):                                        # a cone-shaped mountain of cash
        r = 5.5 * math.sqrt(random.random())
        a = random.uniform(0, 6.3)
        z = max(0.0, 3.6 * (1 - r / 5.5)) + random.uniform(-0.2, 0.1)
        C.copy(CASH2, "mnt", (r * math.cos(a), r * math.sin(a), z), s=1.2, yaw=random.uniform(0, 6.3))
    you, yarm, _ = C.man("you_k", (0, 0, 3.55), 0.0)
    pose(yarm, you, [(0, C.CHEER), (61.3, C.CHEER), (61.6, C.SCRATCH)], t1=B[18])
    phone = D.box("phone", (0.38, 0.04, 0.75), (0, -3.6, 4.8), MAT["ink"], bevel=0.04)
    scr = D.box("phone_scr", (0.33, 0.01, 0.66), (0, -3.625, 4.8),
                L.plastic("pscr", H("#20c05c"), emit=H("#20c05c"), emit_strength=1.2))
    ptxt = txt("BANK", 0.09, (0, -3.64, 4.95), MAT["txt"], extrude=0.005)
    for o in (phone, scr, ptxt):
        C.pop(o, F(61.3), dur_f=5)
        C.vanish(o, F(62.6))
        for k in range(8):                                       # ringing buzz
            D.key(o, "rotation_euler", F(61.4 + k * 0.08), (math.pi / 2 if o is ptxt else 0, 0.12 * (1 if k % 2 else -1), 0))
    bx, by = 0, 22
    marble = L.plastic("marble", H("#eae6dc"), rough=0.35)
    D.box("bank_steps", (16, 6, 1.2), (bx, by - 4, 0.6), marble)
    D.box("bank_body", (14, 8, 9), (bx, by + 2, 5.7), marble)
    for i in range(6):
        D.cyl("col", 0.6, 8, (bx - 6 + i * 2.4, by - 2.5, 5.2), m=marble, verts=24)
    roof = D.cone("pediment", 9.5, 3.0, (bx, by, 11.7), m=marble, verts=3)
    roof.rotation_euler = (math.pi / 2, 0, 0)
    roof.scale = (1, 0.33, 1)
    txt("BANK", 1.6, (bx, by - 2.2, 10.0), MAT["gold"], extrude=0.2)
    sold = D.empty("sold", (bx, by - 3.6, 5.5))
    D.box("sold_bg", (9, 0.2, 2.6), (0, 0, 0), MAT["red"], bevel=0.1).parent = sold
    s_t = txt("SOLD", 1.8, (0, -0.2, 0), MAT["txt"], extrude=0.1)
    s_t.parent = sold
    sold.rotation_euler = (0, math.radians(-12), 0)
    C.pop(sold, F(63.5), dur_f=6, amount=1.3)
    L.post(bk, bloom=0.5)
    shot(bk, "K_mountain", B[16], B[17], (5, -9, 1.5), (4, -9, 6.5), (0, 0, 2.0), (0, 0, 4.4), 26)
    shot(bk, "K_phone", B[17], 62.6, (0.5, -5.0, 5.1), (0.4, -4.7, 5.0), (0, -3.6, 4.8), (0, -3.6, 4.8), 36, dof=4)
    shot(bk, "K_sold", 62.6, B[18], (4, -14, 6), (3, -11, 6.5), (0, by, 5.5), (0, by, 5.8), 24)

# ================================================================= VI3W: real Vi3W sketch → real Vi3W model
v = L.new_set("VI3W")
with L.building(v):
    studio(v, H("#0d1424"), strength=0.6, key_w=550, at=(0, 0, 1.3))
    D.area_light("v_front", 500, (0, -4, 3), (0.9, 0, 1.2), size=3)
    D.area_light("v_rim", 500, (2, 3, 3), (0, 0, 1.2), size=3, rgb=H("#22d3ee"))
    D.area_light("v_rim2", 400, (-3, 2, 3), (0, 0, 1.2), size=3, rgb=H("#ff4fd8"))
    import os as _os
    img = bpy.data.images.load(A("robot0.jpeg"))
    pm = bpy.data.materials.new("sketch")
    pm.use_nodes = True
    tn = pm.node_tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    bs = pm.node_tree.nodes["Principled BSDF"]
    pm.node_tree.links.new(tn.outputs["Color"], bs.inputs["Base Color"])
    pm.node_tree.links.new(tn.outputs["Color"], bs.inputs["Emission Color"])
    bs.inputs["Emission Strength"].default_value = 0.5
    ar = img.size[0] / max(1, img.size[1])
    bpy.ops.mesh.primitive_plane_add(size=1)
    paper = bpy.context.active_object
    D.adopt(paper)
    paper.data.materials.append(pm)
    paper.scale = (1.3 * ar, 1.3, 1)
    paper.location = (-0.9, 0, 1.35)
    paper.rotation_euler = (math.pi / 2, 0, math.radians(12))
    C.pop(paper, F(66.7))
    D.box("easel", (0.08, 0.08, 1.4), (-0.9, 0.12, 0.7), L.pbr("v_wood", "wood_table_001", scale=1.5))
    D.cyl("vpod", 0.75, 0.5, (0.9, 0, 0.25), m=MAT["white"], verts=48)
    rob, _, _ = C.glb(A("robot.glb"))
    vs = [v.co for o in rob for v in o.data.vertices]               # baked data: exact bounds (bound_box is stale
    lo = C.Vector([min(c[i] for c in vs) for i in range(3)])       # outside the context scene's view layer)
    hi = C.Vector([max(c[i] for c in vs) for i in range(3)])
    C.fit(rob, lo, hi, 1.45, axis=2)                       # mesh data: base at z=0, centred, 1.45 m tall
    piv = D.empty("robot", (0.9, 0, 0.5))
    for o in rob:
        o.parent = piv
        o.matrix_parent_inverse.identity()
        o.location = (0, 0, 0)
    C.pop(piv, F(69.6), dur_f=12)
    D.key(piv, "rotation_euler", F(69.6), (0, 0, math.radians(-40)))
    D.key(piv, "rotation_euler", F(END), (0, 0, math.radians(200)), interp="LINEAR")
    arrow = txt(">", 0.5, (0.0, -0.3, 1.4), MAT["yellow"])
    C.pop(arrow, F(68.2))
    sec = txt("< 30 SEC", 0.3, (0.9, -0.8, 0.45), MAT["red"], extrude=0.03)
    C.pop(sec, F(70.85))
    # official logo (Vi3W Assets/), black-backed → brightness becomes alpha
    li = bpy.data.images.load(_os.path.join(HERE, "..", "..", "..", "Vi3W Assets", "Vi3W LOGO.png"))
    lm = bpy.data.materials.new("vlogo")
    lm.use_nodes = True
    nt = lm.node_tree
    nt.nodes.clear()
    t_ = nt.nodes.new("ShaderNodeTexImage")
    t_.image = li
    em, tr, mx = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeMixShader")
    bw, o_ = nt.nodes.new("ShaderNodeRGBToBW"), nt.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Strength"].default_value = 1.6
    nt.links.new(t_.outputs["Color"], em.inputs["Color"])
    nt.links.new(t_.outputs["Color"], bw.inputs["Color"])
    nt.links.new(bw.outputs["Val"], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], o_.inputs["Surface"])
    lm.surface_render_method = "DITHERED"
    bpy.ops.mesh.primitive_plane_add(size=1)
    logo = bpy.context.active_object
    D.adopt(logo)
    logo.data.materials.append(lm)
    logo.scale = (1.0 * li.size[0] / li.size[1], 1.0, 1)
    logo.location = (0, 0.6, 2.75)
    logo.rotation_euler = (math.pi / 2, 0, 0)
    C.pop(logo, F(68.3))
    happy, harm, _ = C.man("you_v", (2.4, 1.3, 0), math.radians(-30))
    pose(harm, happy, [(0, C.SCRATCH), (65.4, C.SCRATCH), (65.7, C.LOOKUP), (69.7, C.CHEER)])
    L.post(v, bloom=0.5)
    shot(v, "V_deal", B[18], B[19], (1.0, -5.5, 1.7), (0.8, -4.8, 1.6), (0.6, 0.5, 1.3), (0.6, 0.5, 1.4), 28)
    shot(v, "V_sketch", B[19], 69.55, (-0.6, -3.6, 1.6), (-0.4, -3.2, 1.55), (-0.6, 0, 1.4), (-0.3, 0, 1.5), 30)
    shot(v, "V_model", 69.55, END, (0.3, -4.6, 1.8), (0.4, -4.0, 1.7), (0.3, 0, 1.4), (0.5, 0, 1.3), 28)
