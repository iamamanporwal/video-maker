---
name: lowpoly-ps2
description: Give a Blender 3D explainer short the LowPolyShorts PS2-era look - 360x640 internal render with nearest-neighbour upscale, no anti-aliasing, 256 px Closest-sampled photo textures, decimated low-poly cast, flat vertex-style lighting, wide lens, night city palettes, small yellow outlined captions and a chunky 3D logo sting - using ps2.py. Use when the user asks for "low poly", "PS2", "retro 3D", "GTA San Andreas style", "LowPolyShorts style", or wants a cheaper/faster-to-render 3D short with meme energy.
---

# Low-poly PS2 look (LowPolyShorts)

Measured from @LowPolyShorts' top Shorts (Nov 2026): "You've Never Touched Anything" 53M, "Why You Shouldn't Point
Lasers At Planes" 24M, "Ancient 30,000 Year Old Virus" 23M, "The Eye Socket Problem" 21M. Library:
`src/reelforge/blender/ps2.py`. Use it with the same pipeline as the `3d-director` skill: script from `3d-explainer-script`,
shots from `3d-shot-grammar` (same vocabulary, slower pace).

## Why it works
The look is a joke on its own: serious science narrated over janky GTA-SA-era graphics. It renders **~10× faster**
than the Zack look (1 sample at 360×640; the test still took about 1 s including Blender startup), so it suits
daily volume. Comedy comes from deadpan VO plus absurd literal visuals (a plane "looks for a parking spot" and nosedives).

## Recipe (in scene.py, after building the set)
```python
import ps2 as P
P.setup(scene)                    # 360x640, 1 sample, filter 0, Standard view, no motion blur, PNG frames
P.flat_light(scene, "#1c1f45")    # night purple-blue sky; day: "#8fb6e6"
P.lowpoly_all(max_tris=2500, prop_tris=600)   # skinned meshes keep 2.5k tris, props go flat-shaded
P.crunch_textures(256)            # every image → ≤256 px + Closest sampling, all materials matte
P.ps2_camera(cam, lens=20)        # wide, no DOF
```
Compose: `ffmpeg ... -vf "scale=1080:1920:flags=neighbor"` (`P.UPSCALE`) **before** overlaying captions, so the
captions stay crisp while the 3D is pixelated. That contrast is part of the look.

## Art direction (from the contact sheets)
- **Photo-textured everything.** Buildings, cockpits and wallpaper are flat boxes with photo textures (Poly Haven
  `red_brick_03`, `plastered_wall`, etc. via `L.pbr`, then crunched). Faces are photo-textured low-poly heads, and
  the uncanny face is the point. Flat untextured colour boxes look like a prototype, not PS2.
- **Palettes**: night city (sky `#1c1f45`, sodium-yellow windows, neon green lasers), suburban day (lavender walls,
  beige carpet, green grass), dark science void (deep blue `#0a1060` with a water-caustic texture) for atoms and cells.
- **Science visuals = game FX**: emissive glowing spheres, particle clouds, laser beams as emissive cylinders, lens
  "star" flares (Glare node, Streaks), thermal-cam false colour (swap materials to blue/magenta emission).
- **Characters**: one recurring everyman (brown leather jacket, jeans), plus role costumes (pilot, cop, orange
  prison jumpsuit, hi-vis vest). Rig = any Mixamo skeleton; animate with stock clips, stiff on purpose.
- **Camera**: wide 18-24 mm, often over-the-shoulder from behind the head, fisheye-ish cockpit interiors, and a
  straight-down TOP shot for falls. Hard cuts only; no whips, no DOF, no motion blur.
- **Pace**: median shot 1.6-1.9 s (slower than Zack); longer 5-10 s holds on the science visuals.
- **Gags**: literal-minded visual punchlines on the button line; a tiny face cam-in-cam (a face cutout on the wall)
  for reactions; the GTA-style "1 in 1,000,000,000,000" counter in red text.

## Captions and branding
- Captions: **small** (~34 px at 1080 w), yellow `#f8e800` (`P.CAPTION_YELLOW`), 2-3 px black outline, a
  4-6-word phrase, centred at **y ≈ 0.67 H** (measured rows 1278-1317 of 1920). Plain sans, e.g. Arial Bold;
  the PS2 subtitle feel matters more than the font.
- Channel sting: a chunky bevelled yellow 3D wordmark with a blue outline that bursts in with particles, about 1 s,
  mid-video (~7-10 s), not at the start. For us: a **Vi3W** wordmark in the same style (`D.text3d`, extrude 0.08,
  then crunch), using the logo colours from (memory: vi3w-brand-assets).

## Gotchas
- `filter_size = 0` plus 1 sample is what gives the jaggies. Don't add bloom/dispersion post (look.post); if you
  need glow, use Glare Streaks only on lasers.
- PNG frames (not JPEG). JPEG ringing at 360 px smears the pixel edges after the upscale.
- Decimation runs after the Armature modifier, so skinning stays intact. If a face collapses, raise `max_tris` for
  that mesh only: `P.lowpoly(head, 4000)`.
- `crunch_textures` modifies images in memory only; it never overwrites the asset files.
- Don't copy LowPolyShorts' characters, logo or exact scenes. Recreate the *style* with our own cast and wordmark.
