---
name: 3d-lookdev
description: Make 3D director shorts look premium and colourful - sets as separate scenes, Poly Haven HDRIs/PBR textures/props, saturated studio palettes, bloom/vignette/dispersion post, AgX Punchy, and measured anti-flicker + render-budget rules. Use with 3d-director whenever a Blender short looks flat, grey, "black and white", cheap, flickery, or the user asks for better textures, lighting, colour or post-processing.
---

# 3D look development

Library: `src/reelforge/blender/look.py` (inside Blender), `src/reelforge/polyhaven.py` (asset fetcher).
Reference build: `projects/shorts/what-if-100/scene.py`.

## 1. Structure: one scene per set (non-negotiable)
`L.new_set("NAME")` + `with L.building(scene):` routes every `D.*` helper into that scene. Each set gets its own
world, lights, shadow pool and post. Shots are `(scene, f0, f1)` in `out/shots.json`, rendered by
`render_shots()`. Use `build.py --stills 1.0,5.0,...` for look checks (it picks each still's scene).
- Why: with every set in one scene, the shared shadow pool overflowed. Dark rooms flickered at a temporal-noise score
  of 30-125 (clean shots score under 2).

## 2. Light
- Outdoors: `L.hdri_world(sc, "kloofendal_48d_partly_cloudy_puresky")` (real sky) + a sun at about 2.5° angle, warm.
- Studios: `studio(sc, colour)` pattern = `studio_small_09` HDRI for reflections, with `backdrop=colour` so the camera
  sees the colour. Use a colour sweep at roughness ≥0.7 (glossier sweeps streak with HDRI softboxes), a soft key, and
  a warm rim.
- Dark sets: HDRI at about 0.04 + coloured practicals (cyan/magenta rims) + bloom 0.6-0.7.

## 3. Colour
- Look: `AgX - Punchy`. Avoid high emission on coloured labels (AgX bleaches it to white); use `L.plastic` with a
  clearcoat instead.
- One saturated backdrop per infographic set, in a different hue each time (blue, amber, violet, mint, teal,
  yellow, aqua), with white/ink objects and red reserved for danger.
- Crowds: vivid tints over the texture (`D.tint_mat`, lo≈0.38), so the detail survives the tint.

## 4. Materials
- `L.pbr(name, poly_haven_id, scale=repeats_per_m, tint=..., tint_amount=...)` box-projects diff/rough/normal/AO on
  object coordinates, so it never stretches. Use `tint` for paint over plaster or dyed fabric.
- Starter kit (`python -m reelforge.polyhaven kit`):
  - Lighting environments: kloofendal_puresky, studio_small_09, noon_grass, blue_photo_studio.
  - Textures: laminate_floor_02, plastered_wall, wood_table_001, fabric_pattern_07, pavement_02, leafy_grass,
    red_brick_03, concrete_floor_02, asphalt_02, metal_plate, leather_red_02.
- `L.plastic` for props, labels and toys (rough 0.3 + coat 0.3-0.6).

## 5. Props and budget (measured on M5, full 1080×1920, 16 samples)
- Target ≤0.45 s/frame per set (the what-if-100 sets measure 0.31-0.45).
- Poly Haven vegetation is photogrammetry: `tree_small_02` is 2M faces. Six trees cost +3.7 s/frame.
  `prop()` warns above 300k faces. Use `L.toy_tree` / `L.bush` (about 3k faces) for foliage, and Poly Haven props
  for hero objects (plants, alarm clock, frames: light).
- Alpha cutouts must be DITHERED with opaque shadows (`prop()` does this); BLENDED is much slower.

## 6. Post (`L.post(scene, ...)`, Blender 5 compositor node group)
- Bloom (Glare node, Bloom type): 0.25 outdoors, 0.55-0.7 for dark or neon sets.
- Lens dispersion 0.006 (subtle chromatic edge).
- Vignette 0.22-0.32.
- Saturation 1.08, contrast +4. Costs about 0.06 s/frame.

## 7. Anti-flicker (measured, not guessed)
- With a locked camera, EEVEE frames are deterministic (noise ≈0). Flicker comes from: an overflowing shadow pool
  (→ one scene per set, pool 1024), thin detail shimmering under camera motion (→ 16 samples, filter 1.8,
  1-step motion blur), and handheld noise (keep it ≤6 mm).
- Check every render: `python -m reelforge.flicker out/frames out/shots.json` gives a second-difference score per shot
  (|2·f_t - f_t-1 - f_t+1|).
  Over ~5 means look closely; over 20 means something is broken.

## 8. Rig / animation sources (research, Nov 2026)
- Now: Mixamo-standard rigs (Xbot/Michelle), `D.play` NLA clips, `D.pose` direction posing, prop-driven IK.
- Future APIs (not used yet; the user said no fal for now):
  - fal-ai/meshy rigging + multi-animation (auto-rig a humanoid mesh, apply preset clips).
  - Uthana auto-rig-1.0 + text-to-motion on Replicate (returns rig confidence).
  - Cartwheel via Scenario (text/image → motion).
  - Meshy direct API (rigging + 500 animation presets).
- Local add-ons (MPFB for MakeHuman humans) need user approval to install. The classifier blocked it once.
