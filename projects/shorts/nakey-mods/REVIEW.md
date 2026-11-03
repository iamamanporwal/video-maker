# nakey-mods review (2026-11-02)

Loop 1 (stills, short 01) 6/10: 3D robot invisible in the ending (ThreeCanvas parent had no size, then GLB never drew);
active-word pop swallowed the space ("TROUBLEIN"); credit pill too long and covered the footage.
Fix: Blender turntable (tools/robot_tt.py → public/models/robot-tt.webm) looped in Remotion; gap 30 + pop 1.07; credit "@NakeyJakey".

Loop 2 (full render 01) 8.5/10: whisper hyphen tokens showed as "AMONG US -STYLE" / "HALF -LIFE". Fix: merge "-x" into the previous word.

Loop 3 (all five) ~9/10: all -14 LUFS, TP ≤ -1.5, no black frames, captions in sync, profanity masked in captions only.
05 had 2.9 s of dead air (source gap before "now that's more like it"): cut to 1.6 s, keeping the visual gag.

Open notes: the ending is identical across the five (by design, brand consistency); vary the robot for a batch 2.
