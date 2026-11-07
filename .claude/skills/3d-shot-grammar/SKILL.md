---
name: 3d-shot-grammar
description: Turn a 3D explainer script into a Zack D. Films-grade shot list and Blender camera/animation plan - a cut every 0.5-1.5 s on caption words, a fixed shot vocabulary (macro hand insert, x-ray cutaway, hero low angle, POV, overhead, object pop-in, whip, rewind), colour-coded cast on a seamless glow void, and the zack.py helpers that build it. Use after 3d-explainer-script and before/with 3d-director whenever a 3D short needs better camera angles, pacing, animation or "make it look like Zack D".
---

# 3D shot grammar (Zack D. Films)

Measured from "What If Bullets Were Made Of Ice?" (i5F2knwWn7w, 8.1M, 41 s), sampled at 2 fps. Library:
`src/reelforge/blender/zack.py` (inside Blender, next to `director.py`). Reference frames:
re-download with `yt-dlp` into the scratchpad when needed; never commit them.

## 1. Pacing: the numbers
- **About 40 camera setups in 41 s.** The median shot is **~1.0 s**, the range is 0.5-2.5 s, and only the "money"
  shot (the x-ray cutaway) holds 4-5 s, and even that moves.
- **Cut on the caption chunk.** Nearly every caption change (1-3 words) is a new angle or a big camera move.
  Same subject, new angle beats a new subject: Zack shows the gun from 6 angles in 4 s.
- LowPolyShorts runs slower (median 1.6-1.9 s, mean ~2 s). That is the floor for this format; never exceed a 2 s
  average.
- No shot is static. Each one has a push-in, an arc, a track or a subject action (see section 4).

## 2. Shot vocabulary (pick per script row)
| Code | Shot | Lens | When | Build |
|---|---|---|---|---|
| MACRO | Extreme close-up of hands + prop (loading the bullet, finger on trigger) | 50-85 mm, f/2.8 DOF | Opening and every physical action | hand IK on the prop (the `3d-director` skill prop-driven hands); camera 15-30 cm away |
| INSERT | The prop alone, tight, slow rotate/push | 50 mm | Naming an object ("a bullet", "into a gun") | prop at frame centre, `D.move` 8 % push |
| XRAY | Cross-section of a machine/body: inner parts animated, arrows | 35 mm, side-on | The mechanism beat, which is the money shot (4-6 s) | `Z.cutaway(obj)` + inner objects + `Z.arrows()` + emissive fire/flash |
| HERO-LOW | Low angle on the "you" character, prop toward lens | 24-28 mm, ~0.6 m high | "the perfect murder weapon", any brag/overconfidence | camera below chest, look up; character smirks/poses |
| POV | Over the muzzle/hand, foreground prop huge | 20-24 mm | Firing, pointing, throwing | prop 30 cm from lens, subject behind |
| PROJ | Follow-cam on a flying object over the void | 35-50 mm | Bullet, ball, debris travelling | camera parented/tracking the object, background is pure void (sells speed via motion blur) |
| IMPACT | Close-up of the hit point: wound, crack, dent | 50 mm | Consequence | decal/material swap + `Z.pop_in` debris |
| WIDE | Full-body tableau, 2-4 characters | 28-35 mm, eye level | Every 4-6 shots to re-orient; the ending | characters in silhouette-clear poses |
| TOP | Straight-down or 60° overhead on a body/floor | 28 mm | Bodies, crime scenes, maps | camera above, slow rotate 5-10° |
| OBJ-POP | Isolated evidence objects pop in one per word on the void | 35 mm | Lists ("casing, footprints, residue, evidence bag") | `Z.pop_in(o, T(word))`, `Z.drop_in` for heavy items |
| WHIP | Camera whips sideways into the cut | any | Linking two physical actions, or 2-3 times per video | `Z.whip(cam, look, f)` + motion blur, cut at peak |
| REWIND | B&W, reversed playback, "REWIND ◀◀" label | (post) | Undoing the wrong belief at the "But" | ffmpeg: reverse + `hue=s=0.1` + noise; `Z.rewind_filter` |

Coverage rule for one action: **MACRO → INSERT → WIDE (or POV)**, with 3 angles, then move on.
Ordering rule: never put two shots with the same code back to back unless the subject changes.

## 3. Set, cast, colour (the "void")
- **One seamless colour void per video**: `Z.void(scene)` gives edge `#66a6be` (measured) with a pale glow behind
  the subject. Because the glow is screen-space, it follows every camera, and the floor has no horizon but still
  catches soft contact shadows. Change the void hue per video for channel variety (mint, peach, lavender), but
  keep it desaturated and mid-light.
- **No environments.** Context comes from props (police caps, an evidence bag), not rooms. This is also why it
  renders fast.
- **Colour-code the cast**: one saturated shirt per role (victim lime `#a8e05a`, perpetrator/"you" red `#e3262b`,
  authority near-black navy). The viewer tracks roles by colour across 40 cuts.
- **Realistic humans** with readable faces (Renderpeople/Sketchfab rigged, see (memory: realistic-cast-sketchfab)), with
  exaggerated expressions only on HERO-LOW and close-ups.
- **Props are photoreal heroes** (metal revolver, frosted ice, brass casing). Spend the asset budget here.
- Light: soft top-front key (sun angle 14°), ambient from the void colour, AgX Medium High Contrast. No coloured rims.

## 4. Motion inside every shot
- Camera: eased push-in of 5-12 % over the shot, or a 10-20° arc around the subject; `D.handheld` 4-6 mm.
- Subject: something must change within 0.3 s of the cut (hand moves, object rotates, character turns, an object
  pops). A cut onto a frozen frame reads as a slideshow.
- Overlapping action: start the next motion before the previous one settles; use ease-in-out curves, never linear.
- Exaggerate physics 1.3-2×: recoil, debris spread, falls. Hold the end pose 4-6 frames before cutting.
- Cuts land on the word *onset* (from `ref/words.json`), 1-2 frames early, never late.

## 5. Captions (composited in ffmpeg, never rendered in 3D)
- Zack: white, bold rounded sans, soft dark drop shadow, **1-3 words**, centred at **y ≈ 0.78 H**, with no box and
  no colour highlight. Show each chunk exactly while its words are spoken.
- LPS: see the `lowpoly-ps2` skill (small yellow, outlined, y ≈ 0.67 H).
- No other text on screen except diegetic labels (EVIDENCE bag, gauge numbers) and the REWIND tag.

## 6. Audio
- VO from 0.00 s. A quiet music bed under it (Zack mixes it audibly but low; integrated ≈ −11 LUFS overall, so
  master to −14 for us). Free YouTube music only, see (memory: music-free-youtube).
- SFX on every physical action: click, shot, crack, whoosh on WHIP, thud on drop_in. Place SFX in the VO gaps and
  duck under the words ((memory: audio-mix-and-self-review)).

## 7. Shot-list output → scene.py
From SCRIPT.md, write `shots.json`: `[{"id":1,"code":"MACRO","t0":0.00,"t1":0.62,"subject":"hand+bullet","cam":"..." ,"action":"push ice round in"}]`,
with t0/t1 taken from word onsets. Then build one camera per row in scene.py (`D.camera`, `D.move`, `D.cut`).
Before rendering, check with `--stills` at each shot's midpoint and tile them. The contact sheet should look like
the reference sheet: 30+ distinct framings with no two neighbours alike.

## 8. Self-review checklist (score /10 each, loop until ≥9, see film-qc)
1. Median shot ≤1.2 s, nothing static >2.5 s except the XRAY.
2. Every row's visual note is literally on screen when its word is spoken.
3. At least 1 MACRO, 1 XRAY (if there's a mechanism), 1 HERO-LOW, 1 OBJ-POP list, 1 WIDE ending tableau.
4. Cast colours read at thumbnail size.
5. Captions are never covered by props and sit inside the Shorts safe zone (bottom 20 % is UI).
