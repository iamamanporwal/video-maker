---
name: 3d-director
description: Build a Zack D. Films / LowPolyShorts-style 3D explainer short (9:16, 10-90 s) in Blender EEVEE - rigged characters posed and animated by script, prop-driven IK hands, shot list cut on VO word times, parallel fast render, captions + VO via ffmpeg. Use when the user wants a "Zack D style", "3D documentary/infographic short", "3D explainer", or shares such a reel and asks "can we make this".
---

# 3D director

Pilot and template: `projects/shorts/3d-2d-hat/` (scene.py + build.py). Library: `src/reelforge/blender/director.py`
(runs inside Blender) and `src/reelforge/blender/render.py` (parallel renderer). Copy the pilot folder for a new short.

## Pipeline (one command: `.venv/bin/python projects/shorts/<id>/build.py [--preview]`)

1. **VO first.** ElevenLabs direct API (never fal for now), then word timestamps (mlx-whisper, or ElevenLabs
   with-timestamps) → `ref/words.json`. Every shot boundary and action key is in seconds from these words: `T(sec)`.
2. **scene.py** (`blender -b -P scene.py -- out/scene.blend`): set, characters, props, animation, one camera per shot,
   `D.cut()` markers. Builds in ~1 s; no clicking.
3. **Look-check stills** before any full render:
   `python -m reelforge.blender.render out/scene.blend out/stills --stills 30,80,140,240 --scale 50` (~2 s).
   Tile them, look, fix, repeat. Most of the iteration happens here.
4. **Render** with 3 workers, frames as JPEG. **Compose** with ffmpeg: PIL caption PNGs (one per phrase) overlaid on word
   times, VO plus loudnorm −14 LUFS. Then copy to `FinalUploads/Drafts/` with a caption .txt.
5. **QC** with `film-qc`: ffprobe spec, ebur128, black/freeze detect, contact sheet on phrase frames.

## Rig solution
- Any **Mixamo-standard skeleton** (Mixamo, Sketchfab rigged downloads, Vi3W auto-rig exports). Pilot uses three.js
  sample `Michelle.glb` (Mixamo, royalty-free).
- **Pose by world direction**: `D.pose(rig, frame, {"RightArm": (x,y,z), ...})` aims bones regardless of bone roll, so the
  same pose dict works on any Mixamo rig. Parents before children.
- **Props drive hands**: animate the prop (the hero), then bake the IK target to a grip offset on the prop every frame
  (`wrist_at`), and Damped-Track the hand to the prop. Add `D.curl()` on grab and release. Add a pole empty for the elbow.
- **"2D" bodies**: pose the rig in 3D, then parent it under an empty scaled Y=0.03 against the board, with
  `visible_shadow=False`. Props pop 2D → 3D by keying their depth scale.
- Use stock animations (Mixamo/Sketchfab clips) for locomotion. Script only the acting beats.

## Camera and light language (Zack D)
- Cut on every phrase (1.5-3 s shots): over-shoulder establish → close-up on the action → 3/4 close-up → wide payoff.
- Every shot moves: eased dolly or push-in of 5-15 %, plus `D.handheld()` noise of 5-8 mm. Lens 28-38 mm on the
  vertical sensor. DOF f/4 only on close-ups.
- High-key soft studio: light-blue cyclorama, soft sun (14° angle) for contact shadows, a big area key front-left, a
  cool fill on the right, and a world ambient at about 0.55. AgX Medium High Contrast. Strong saturated accents
  (labels, props); avoid high emission because AgX bleaches it to white.

## Speed (10 s of 1080×1920 in under 100 s; the pilot does it in about 49 s)
- EEVEE, **8 samples** (looks the same as 16 here), no ray tracing, shadow res ×0.5, 1-step motion blur, JPEG frames.
- 3 parallel Blender workers. The GPU is the bottleneck, so more than 3 workers gains nothing.
- Text and captions are composited after rendering (ffmpeg, about 3 s), so copy changes never re-render 3D.
- Preview: `--preview` (50 % scale, every 2nd frame).
- Measured on M5/24 GB: 0.16 s per frame at 8 samples, 0.29 s at 16.

## Assets
- Sketchfab (needs `SKETCHFAB_API_TOKEN`): CC0/CC-BY only, credit CC-BY in the caption, never NC. Kenney/Quaternius for
  CC0 low-poly packs, Poly Haven for HDRIs and textures. Re-material imports to one palette per video. Build simple
  props procedurally (the pilot's cap is about 30 lines).
- Never use another creator's VO in a posted video. The pilot's Zack D. audio is a temp track and stays in Drafts.
