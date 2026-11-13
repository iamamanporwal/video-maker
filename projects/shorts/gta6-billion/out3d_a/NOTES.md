# Agent A cash shots (gta6-billion)
`../../../../.venv/bin/python out3d_a/build.py <shot,...> [--stills|--full]` (from the project dir). scene.py builds one .blend per shot,
bakes particles into it, renders frames PRE+1..PRE+NF (pre-roll so frame 1 is already moving) → public/3d/<shot>.mp4.
Bills: bill_front.jpg on bent grid meshes (7 variants), instanced by particle systems. Logos: SVG → extruded curve layers.

| shot | len | s/frame | flicker median (motion, not shadow flicker) |
|---|---|---|---|
| rocket | 4.8 s | 0.46 | 10.6 (max 49.6 = the hard cut to the wide at 3.2 s) |
| cashrain | 6.0 s | 0.45 | 37.8 (thousands of tumbling bills; frames clean) |
| vault | 4.6 s | 0.57 | 15.1 (slam shake + fast low dolly over textured floor) |
| printer | 5.9 s | 0.47 | 14.4 (bill stream) |
Known: vault door reaches closed ~0.8-1.0 s (slam keyed 1.35 s, ease reads early); calendar page text small.
