# 3D environment & props shots (agent A): gta6-by-hand

To build, run this from the project dir: `../../../.venv/bin/python out3d_a/build.py <shot,...> [--stills] [--full] [--build]`.
- `scene.py <shot> <blend>` writes one .blend per shot to `out3d_a/blend/`.
- `--stills` renders contact sheets (`sheet_<shots>.jpg`).
- `--full` renders with 3 workers and writes `public/3d/<shot>.mp4` (1080x1920, 30 fps, H.264 yuv420p, crf 18, no audio).

## Look system
- Every material passes through `stage()`, which takes it from clay to a colour UV-checker to its final texture.
- Timing comes from a shared `CTRL` node group: `time` is the number of seconds since the shot started, and `sun` blends from the viewport grey to sunset.
- Per-object start times are custom props (`chk0`/`tex0`). Adding `k*world_pos` turns the change into a wipe, with glowing wavefronts at the leading edge.
- Other viewport elements:
  - Blender-orange selection outline: an inverted hull that disappears via `ol_off`.
  - Glowing cyan wireframe overlay: a linked-data duplicate, so it follows the shape keys.
  - Grid floor with red and green axes.
- The world switches between viewport grey and a stylised Vice sunset gradient for camera rays. Lighting comes from the belfast_sunset HDRI.

## Shots (self-scores after 3 look-check iterations)
| shot | dur | score | notes |
|---|---|---|---|
| trashcan | 5.4 s | 9 | Already morphing at frame 1 (cube→cylinder via shape keys). 1.25-1.85: ribs, bands and a wire sweep. 2.4: lid drops in. 2.75/2.95: handles pop. 3.45: checker sweep. 4.05-4.35: galvanised metal wipes up, the floor turns from grid to tiles, sunset rim. |
| props | 2.4 s | 8 | Pink Art-Deco facade on a tiled sidewalk. The bench pops at 0.1 (grey→wood by 0.45). The palm pops at 1.0 (grey→textured by 1.4). The camera trucks right. |
| citypull | 2.2 s | 8 | Starts on the same corner and cranes up to 330 m. About 3k box buildings (single mesh) on a grid with a downtown cluster, fading into an orange haze. |
| pipeline | 4.4 s | 8 | Grey cube until 1.5. Grows into the building 1.5-1.8, floors and crown pop in up to 2.4 with a wire flash. 2.5: checker sweep. 3.3: pastel Art-Deco texture plus the sunset switch. |
| florida | 2.5 s | 8 | Generic peninsula plus keys. The building waves sweep from south to north (12 shape-key bands, 0.12-1.4 s), followed by a colour wipe. The sea goes from grey to teal. Slow rotation. |
| office | 3.6 s | 8 | 4,700 instanced desk units (desk, monitor with glowing screen, chair, seated figure in a random shirt colour). The camera rises from the aisle to about 48 m. Warm haze against cool screens. |

## Fell short / compromises
- Sketchfab downloads crawled at about 10 KB/s and kept stalling, so the trash can and bench are procedural.
  - The trash can is a galvanised ribbed can. Its final shape is the same mesh that morphs, so the reveal has no swap pop.
  - The bench uses slats with a wood texture and green iron legs.
  - Only the palm is a Sketchfab asset (CC-BY credit needed).
- Florida buildings are tiny at this altitude, so they read as coloured speckle and clusters rather than individual houses.
- citypull: the grey boxes read light-lavender under the warm sun. That is clearly "grey-box", but not the darker clay look.
- pipeline: the floor's texture wipe leaves a visible bright ring as it sweeps outward.

## Full render (EEVEE, 16 samples, 3 workers, about 9 min total)
s/frame: trashcan 0.67, props 3.71 (the alpha palm leaves are the cost), citypull 0.58, pipeline 0.40, florida 0.32, office 0.31.
Flicker medians:
- trashcan: 0.9 on the final hold. The 3.4-4.2 window scores 14, which is the intended checker/texture wipe.
- props: 2.7
- pipeline: 1.3
- florida: 0.75
- citypull: 15 and office: 15. Both shots have a fast camera rise over thousands of small boxes. This is real motion parallax, and the frames look clean, but a phone check is still worth doing.
