"""Look development for director shorts (runs inside Blender): sets as scenes, HDRI light, PBR textures, props, post.

Why each set is its own scene: one world (HDRI) per scene, lights never leak between sets, and the shadow pool
only holds that set's shadows. A shared pool across many sets overflowed and made dark sets flicker (measured:
temporal noise 30-125 vs <2). Shared assets (crowd meshes, materials) are reused across scenes.

    import look as L
    door = L.new_set("DOOR", main=True)          # context scene, renamed
    L.hdri_world(door, "kloofendal_48d_partly_cloudy_puresky")
    clock = L.new_set("CLOCK")                  # new scene with the same render/colour settings
    with L.building(clock): ...                  # every D.* helper now creates into CLOCK
    L.post(scene)                                # bloom + dispersion + vignette + grade
"""
import contextlib, math, os
import bpy
import director as D

PH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "polyhaven")


# ---------------------------------------------------------------- sets = scenes

def new_set(name, main=False):
    base = bpy.data.scenes[0]
    if main:
        base.name = name
        return base
    s = bpy.data.scenes.new(name)
    for attr in ("resolution_x", "resolution_y", "resolution_percentage", "fps", "use_motion_blur",
                 "motion_blur_shutter", "filter_size", "use_persistent_data"):
        setattr(s.render, attr, getattr(base.render, attr))
    s.render.engine = base.render.engine
    s.render.image_settings.file_format = base.render.image_settings.file_format
    s.render.image_settings.quality = base.render.image_settings.quality
    for p in base.eevee.bl_rna.properties:
        if not p.is_readonly:
            try:
                setattr(s.eevee, p.identifier, getattr(base.eevee, p.identifier))
            except Exception:
                pass
    s.view_settings.view_transform = base.view_settings.view_transform
    s.view_settings.look = base.view_settings.look
    s.frame_start, s.frame_end = base.frame_start, base.frame_end
    return s


@contextlib.contextmanager
def building(scene):
    """Route every new object (D.link / D.adopt) into `scene` while the block runs."""
    prev = D.TARGET
    D.TARGET = scene.collection
    try:
        yield scene
    finally:
        D.TARGET = prev


# ---------------------------------------------------------------- light

def hdri_world(scene, hdri, strength=1.0, rot_deg=0.0, backdrop=None, backdrop_strength=1.0):
    """HDRI lights the set; `backdrop` (linear rgb) is what the camera sees instead of the HDRI, if given."""
    w = bpy.data.worlds.new(scene.name + "_world")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(_hdri_path(hdri), check_existing=True)
    tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot_deg))
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    shader = bg.outputs[0]
    if backdrop:
        cam_bg = nt.nodes.new("ShaderNodeBackground")
        cam_bg.inputs["Color"].default_value = (*backdrop, 1)
        cam_bg.inputs["Strength"].default_value = backdrop_strength
        lp, mix = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
        nt.links.new(bg.outputs[0], mix.inputs[1])
        nt.links.new(cam_bg.outputs[0], mix.inputs[2])
        shader = mix.outputs[0]
    nt.links.new(shader, out.inputs["Surface"])
    scene.world = w
    return w


def _hdri_path(hdri):
    if os.path.exists(hdri):
        return hdri
    for res in ("2k", "1k", "4k"):
        p = os.path.join(PH, "hdris", f"{hdri}_{res}.hdr")
        if os.path.exists(p):
            return os.path.abspath(p)
    raise FileNotFoundError(f"{hdri}: run python -m reelforge.polyhaven hdri {hdri}")


# ---------------------------------------------------------------- materials

def pbr(name, tex, scale=1.0, tint=None, tint_amount=1.0, rough_mul=1.0, rough_add=0.0, normal=1.0, spec=0.5,
        clearcoat=0.0, blend=0.2):
    """Poly Haven texture set as a material. Box-projected on object coordinates (metres), so it never stretches
    on scaled primitives; `scale` = texture repeats per metre. `tint` recolours (paint over plaster, dyed fabric)
    while the texture's light/dark detail stays."""
    d = os.path.join(PH, "textures", tex)
    if not os.path.isdir(d):
        raise FileNotFoundError(f"{tex}: run python -m reelforge.polyhaven texture {tex}")
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(fname, color=True):
        p = next((os.path.join(d, f) for f in os.listdir(d) if f.startswith(fname + ".")), None)
        if not p:
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.abspath(p), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if color else "Non-Color"
        n.projection, n.projection_blend = "BOX", blend
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n

    diff, rough, nor, ao = img("diff"), img("rough", False), img("nor", False), img("ao", False)
    col = diff.outputs["Color"] if diff else None
    if tint and col is not None:
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(col, bw.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["To Min"].default_value = 0.0, 0.55
        nt.links.new(bw.outputs[0], mr.inputs["Value"])
        tinted = nt.nodes.new("ShaderNodeMix")
        tinted.data_type, tinted.blend_type = "RGBA", "MULTIPLY"
        tinted.inputs["Factor"].default_value = 1.0
        tinted.inputs[6].default_value = (*tint, 1)
        nt.links.new(mr.outputs[0], tinted.inputs[7])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["Factor"].default_value = tint_amount
        nt.links.new(col, mix.inputs[6])
        nt.links.new(tinted.outputs[2], mix.inputs[7])
        col = mix.outputs[2]
    if ao and col is not None:
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
        mul.inputs["Factor"].default_value = 0.6
        nt.links.new(col, mul.inputs[6])
        nt.links.new(ao.outputs["Color"], mul.inputs[7])
        col = mul.outputs[2]
    if col is not None:
        nt.links.new(col, b.inputs["Base Color"])
    if rough:
        mr = nt.nodes.new("ShaderNodeMath")
        mr.operation, mr.use_clamp = "MULTIPLY_ADD", True
        mr.inputs[1].default_value, mr.inputs[2].default_value = rough_mul, rough_add
        nt.links.new(rough.outputs["Color"], mr.inputs[0])
        nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    if nor and normal:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal
        nt.links.new(nor.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    if clearcoat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = clearcoat
    return m


def plastic(name, rgb, rough=0.35, coat=0.3, emit=None, emit_strength=0.0):
    """Toy-like glossy plastic (labels, props): base colour + clearcoat for crisp highlights."""
    m = D.mat(name, rgb, rough=rough, emit=emit, emit_strength=emit_strength)
    b = m.node_tree.nodes["Principled BSDF"]
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    return m


# ---------------------------------------------------------------- props

def prop(asset, loc=(0, 0, 0), rot_z=0.0, scale=1.0, name=None):
    """Import a Poly Haven model (glTF, real-world scale) as one parented group. Returns the root empty."""
    d = os.path.join(PH, "models", asset)
    g = next((os.path.join(d, f) for f in os.listdir(d) if f.endswith(".gltf")), None) if os.path.isdir(d) else None
    if not g:
        raise FileNotFoundError(f"{asset}: run python -m reelforge.polyhaven model {asset}")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(g))
    new = [o for o in bpy.data.objects if o not in before]
    root = D.empty(name or asset, loc)
    root.rotation_euler, root.scale = (0, 0, math.radians(rot_z)), (scale,) * 3
    faces = 0
    for o in new:
        D.adopt(o)
        if o.parent is None:
            o.parent = root
        if o.type == "MESH":
            faces += len(o.data.polygons)
            for m in o.data.materials:                 # alpha cutouts: dithered + opaque shadows (blended = slow)
                if m and getattr(m, "surface_render_method", "") == "BLENDED":
                    m.surface_render_method = "DITHERED"
                    if hasattr(m, "use_transparent_shadow"):
                        m.use_transparent_shadow = False
    if faces > 300_000:
        print(f"WARNING prop {asset}: {faces:,} faces — too heavy for EEVEE shorts (measured: 2M-face tree = +0.6 s/frame)")
    return root


def _foliage_mat(name, rgb):
    """Soft stylised foliage: colour + large noise bump + subtle colour variation; cheap and reads at any distance."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = plastic(name, rgb, rough=0.65, coat=0.0)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 6.0, 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    ramp = nt.nodes.new("ShaderNodeMix")
    ramp.data_type = "RGBA"
    ramp.inputs[6].default_value = (*[c * 0.6 for c in rgb], 1)
    ramp.inputs[7].default_value = (*[min(1, c * 1.25) for c in rgb], 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Factor"])
    nt.links.new(ramp.outputs[2], b.inputs["Base Color"])
    return m


def toy_tree(loc, scale=1.0, seed=0, leaf=(0.12, 0.42, 0.1), bark_tex="wood_table_001"):
    """Stylised tree (~3k faces): tapered wood trunk + 4 lumpy foliage blobs."""
    import random
    r = random.Random(seed)
    root = D.empty("toy_tree", loc)
    root.scale = (scale,) * 3
    bark = bpy.data.materials.get("bark") or pbr("bark", bark_tex, scale=3, tint=(0.25, 0.14, 0.07), tint_amount=0.6)
    trunk = D.cyl("trunk", 0.16, 2.2, (0, 0, 1.1), m=bark, verts=12)
    trunk.parent = root
    leaves = _foliage_mat("leaves_toy", leaf)
    for i in range(4):
        b = D.ico("canopy", r.uniform(0.75, 1.05), (r.uniform(-0.45, 0.45), r.uniform(-0.45, 0.45), r.uniform(2.3, 3.0)),
                  leaves, sub=3)
        d = b.modifiers.new("lumps", "DISPLACE")
        tx = bpy.data.textures.get("lumps") or bpy.data.textures.new("lumps", "CLOUDS")
        tx.noise_scale = 0.6
        d.texture, d.strength = tx, 0.35
        b.parent = root
    return root


def bush(loc, scale=1.0, seed=0, leaf=(0.15, 0.48, 0.12)):
    import random
    r = random.Random(seed)
    root = D.empty("bush", loc)
    root.scale = (scale,) * 3
    for i in range(3):
        b = D.ico("bushpart", r.uniform(0.35, 0.5), (r.uniform(-0.35, 0.35), r.uniform(-0.2, 0.2), 0.3), _foliage_mat("leaves_toy", leaf), sub=2)
        b.parent = root
    return root


# ---------------------------------------------------------------- post

def post(scene, bloom=0.35, bloom_threshold=0.9, bloom_size=0.6, dispersion=0.006, vignette=0.22,
         warmth=0.0, saturation=1.08, contrast=0.04):
    """Compositor finish: bloom → slight lens dispersion → vignette → saturation/contrast. Blender 5 node API."""
    ng = bpy.data.node_groups.new(scene.name + "_post", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, Lk = ng.nodes, ng.links.new
    rl = N.new("CompositorNodeRLayers")
    rl.scene = scene
    img = rl.outputs["Image"]
    if bloom:
        g = N.new("CompositorNodeGlare")
        g.inputs["Type"].default_value = "Bloom"
        g.inputs["Quality"].default_value = "High"
        g.inputs["Threshold"].default_value = bloom_threshold
        g.inputs["Strength"].default_value = bloom
        g.inputs["Size"].default_value = bloom_size
        Lk(img, g.inputs["Image"])
        img = g.outputs["Image"]
    if dispersion:
        ld = N.new("CompositorNodeLensdist")
        ld.inputs["Dispersion"].default_value = dispersion
        ld.inputs["Fit"].default_value = True
        Lk(img, ld.inputs["Image"])
        img = ld.outputs["Image"]
    if saturation != 1.0 or warmth:
        hs = N.new("CompositorNodeHueSat")
        hs.inputs["Saturation"].default_value = saturation
        Lk(img, hs.inputs["Image"])
        img = hs.outputs["Image"]
    if contrast:
        bc = N.new("CompositorNodeBrightContrast")
        bc.inputs["Contrast"].default_value = contrast * 100
        Lk(img, bc.inputs["Image"])
        img = bc.outputs["Image"]
    if vignette:
        el = N.new("CompositorNodeEllipseMask")
        el.inputs["Size"].default_value = (0.92, 0.82)
        bl = N.new("CompositorNodeBlur")
        bl.inputs["Size"].default_value = (220, 220)
        Lk(el.outputs["Mask"], bl.inputs["Image"])
        mr = N.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = 1.0 - vignette
        Lk(bl.outputs["Image"], mr.inputs["Value"])
        mul = N.new("ShaderNodeMix")
        mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        Lk(img, mul.inputs[6])
        Lk(mr.outputs[0], mul.inputs[7])
        img = mul.outputs[2]
    go = N.new("NodeGroupOutput")
    Lk(img, go.inputs[0])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True
    return ng
