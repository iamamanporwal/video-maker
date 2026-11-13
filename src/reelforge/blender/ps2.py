"""PS2-era 'LowPolyShorts' look (runs inside Blender). Measured from @LowPolyShorts top Shorts
(0U6OcfxYZ7U 53M, WIbdD9S5Vwo 24M, ZLoPJ0JHPxg 23M, NEfh6uA_PLA 21M).

What makes it read as PS2, in order of importance:
  1. low internal resolution, nearest-neighbour upscale (render 360x640 → 1080x1920 with flags=neighbor)
  2. no anti-aliasing (1 sample, filter 0) → stair-step edges
  3. small textures sampled with Closest (blocky texels), photo-textured faces on low-poly heads
  4. flat/vertex-style lighting: high ambient, no or hard shadows, Standard view transform (no filmic roll-off)
  5. low poly silhouettes (characters ~1-3k tris, props a few hundred) with flat shading on hard props
  6. wide lens (18-24 mm), hard cuts, no DOF, no motion blur
  7. distance fog / dark night skies hide the small world

    import ps2 as P
    P.setup(scene)                  # 360x640, 1 sample, Standard, no blur/AO
    P.lowpoly_all(max_tris=2500)    # decimate every mesh above budget
    P.crunch_textures(256)          # downscale + Closest-sample every image texture
    P.flat_light(scene, "#2a2d52")  # ambient world + one hard sun
then ffmpeg:  P.UPSCALE  (scale=1080:1920:flags=neighbor)
"""
import bpy

UPSCALE = "scale=1080:1920:flags=neighbor"      # use in the compose step, before captions
CAPTION_YELLOW = "#f8e800"                      # measured; small (~34 px at 1080w), 2-3 px black outline, y≈0.67


def setup(scene, w=360, h=640, fps=30):
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage, r.fps = w, h, 100, fps
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    e = scene.eevee
    e.taa_render_samples = 1
    for k, v in (("use_raytracing", False), ("use_fast_gi", False), ("use_shadows", True),
                 ("shadow_ray_count", 1), ("shadow_step_count", 1), ("use_volumetric_shadows", False)):
        if hasattr(e, k):
            try:
                setattr(e, k, v)
            except Exception:
                pass
    r.filter_size = 0.0                          # no AA blur → jaggies
    r.use_motion_blur = False
    r.film_transparent = False
    r.use_persistent_data = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    im = r.image_settings
    im.file_format = "PNG"                      # lossless at low res; JPEG ringing would blur the pixel look
    return scene


def lowpoly(o, max_tris=2000, flat=False):
    """Decimate one mesh to ~max_tris (keeps UVs/skin weights). flat=True for hard props (boxes, cars, buildings)."""
    if o.type != "MESH":
        return
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if tris > max_tris:
        m = o.modifiers.new("ps2_decimate", "DECIMATE")
        m.ratio = max(0.01, max_tris / tris)
        m.use_collapse_triangulate = True        # added after Armature: decimates the deformed mesh, skinning intact
    if flat:
        for p in o.data.polygons:
            p.use_smooth = False


def lowpoly_all(max_tris=2500, prop_tris=600):
    """Characters (skinned meshes) get max_tris, everything else prop_tris and flat shading."""
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        skinned = any(md.type == "ARMATURE" for md in o.modifiers)
        lowpoly(o, max_tris if skinned else prop_tris, flat=not skinned)


def crunch_textures(max_px=256):
    """Every image: downscale to max_px and sample with Closest (blocky texels, no mip blur)."""
    for img in bpy.data.images:
        if img.type != "IMAGE" or not img.has_data and not img.filepath:
            continue
        try:
            w, h = img.size
            if max(w, h) > max_px:
                k = max_px / max(w, h)
                img.scale(max(1, int(w * k)), max(1, int(h * k)))
        except Exception:
            pass
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE":
                n.interpolation = "Closest"
            if n.type == "BSDF_PRINCIPLED":       # PS2 had no PBR spec: matte everything
                n.inputs["Roughness"].default_value = 1.0
                if "Specular IOR Level" in n.inputs:
                    n.inputs["Specular IOR Level"].default_value = 0.1
                if "Coat Weight" in n.inputs:
                    n.inputs["Coat Weight"].default_value = 0.0


def flat_light(scene, sky="#2a2d52", ambient=1.4, sun=1.6, sun_dir=(0.4, 0.3, -1.0), shadows=False):
    """PS2 lighting: strong flat ambient (vertex-lit feel) + one hard sun. `sky` is what the camera sees.
    Day: sky '#8fb6e6', ambient 1.6. Night: sky '#1c1f45' (LowPolyShorts' purple-blue night), ambient 1.1."""
    from mathutils import Vector
    w = bpy.data.worlds.new(scene.name + "_ps2sky")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    h = sky.lstrip("#")
    lin = tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))
    bg.inputs[0].default_value = (*lin, 1)
    bg.inputs[1].default_value = 1.0
    # ambient that lights objects regardless of sky colour: light-path mix (camera sees sky, objects see grey)
    nt = w.node_tree
    amb = nt.nodes.new("ShaderNodeBackground")
    amb.inputs[0].default_value = (1, 1, 1, 1); amb.inputs[1].default_value = ambient
    lp, mx = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes["World Output"]
    nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0])
    nt.links.new(amb.outputs[0], mx.inputs[1]); nt.links.new(bg.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    scene.world = w
    ld = bpy.data.lights.new(scene.name + "_ps2sun", "SUN")
    ld.energy, ld.angle, ld.use_shadow = sun, 0.0, shadows
    o = bpy.data.objects.new(ld.name, ld)
    o.rotation_euler = Vector(sun_dir).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(o)
    return w


def ps2_camera(cam, lens=20.0):
    """Wide, no DOF: PS2 cutscene framing."""
    cam.data.lens = lens
    cam.data.dof.use_dof = False
    return cam
