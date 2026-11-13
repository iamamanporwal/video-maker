# 3d-history QC (pass 1, 2026-11-08)

Technical: 1080x1920 h264 yuv420p (tv range), AAC 48 kHz, 30 fps, 73.6 s (66.6 s story + 7.0 s shared outro).
-15.1 LUFS, -0.8 dBFS peak. Freeze-free (the outro concat was fixed). One 0.8 s "black" flag at 50.6 is the empty
navy graph before its line draws (intended). Render 231 s (2,000 frames, 720x1280, EEVEE 8 samples, upscaled).

| # | Criterion | Score | Evidence |
|---|---|---|---|
| 1 | Hook | 8 | 0-2.3 s: one teapot morphs wireframe → flat → gouraud → plastic → PBR while the year card runs 1963→2026, then a hard cut to a lone vertex on a screen: "the hardest part never changed" |
| 2 | Story clarity | 9 | 6 dated eras → same desk 1998-today → vertex drag → graph → Vi3W, one idea per beat |
| 3 | Arc | 8.5 | B&W film 1963-72 → faded 1975 → colour 1995 → photoreal ramp; flat "THE WORK" line sets up the turn |
| 4 | Visual craft | 8 | every era is drawn in its own graphics style; polygons build on the hand one by one; the same-shot monitor gag |
| 5 | Colour/texture | 8.5 | grading arc carries the timeline |
| 6 | Typography | 8 | Georgia serif year cards + captions, yellow counters, green feature chips |
| 7 | Voice | 7? | Kokoro am_michael (local, ElevenLabs credits exhausted). Not checked by ear |
| 8 | Sound mix | 8 | music ducked under VO; projector/whoosh era transitions; clicks on each vertex drag |
| 9 | Brand bridge | 9 | REAL Vi3W capture (demo3: sketch → 3D car), 4 real Vi3W models, the real robot sketch beside its real model, official logo |
| 10 | Accuracy/rights | 8.5 | dated facts verified; no studio footage/logos; "days" per character hedged; rig/animate/export claimed as text over real static models (no faked rig) |

Overall ~8.3 → FinalUploads/Drafts.
Holding it back: the narrator voice is local TTS; the lineup models are small in frame; the graph opens on 0.8 s of empty axes.
