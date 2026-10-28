# reel.yaml reference (`python -m reelforge.shorts build <dir>`)

Paths are relative to the reel folder. Outputs go to `<dir>/out/`: `<title>-9x16.mp4` (mastered to -14 LUFS),
`poster.jpg`, `contact.jpg`, `caption.txt`, `props.json`. Voiceover is cached in `public/vo/` by text + voice, so
re-renders cost nothing; ElevenLabs character usage is logged to `costs.jsonl`.

```yaml
title: my-reel                      # output file name
brand: { accent: "#7CFF6B", ink: "#07080C", text: "#FFFFFF" }   # optional
voice: { id: FGY2WhTYpPnrIDTdsKH5, model: eleven_v3, stability: 0.0 }   # optional; default = Laura (excited, social)
say: { "Vi3W": "View", "Vi3W.in": "view dot in" }   # optional; spoken forms, captions keep the written word
hook: { text: "These karts were *pencil doodles*", seconds: 2.6 }   # big top title from frame 0; *word* = accent
credit: "🎮 Game · by Creator"       # chip shown over gameplay after the hook
sfx: true                           # shared whoosh on cuts + pop on the reveal (generated once)

segments:                           # played in order
  - id: open                        # ids are used by vo[].at
    type: clip                      # own / featured-with-permission footage
    src: ../../../Input/game.mp4
    in: 38.0                        # source seconds
    out: 41.0
    speed: 1.0
    fit: crop                       # crop = fill 9:16 around focus; frame = sharp 16:9 band over blurred fill
    focus: 0.5                      # 0..1 horizontal focus for crop
    zoom: 1.0
    gain: 0                         # source audio volume (0 = muted; leave space for in-app music)
    label: "2 players · 1 keyboard" # small text above the band (frame mode)
  - id: reveal
    type: reveal                    # SKETCH card → 3 click dots → 3D card with flash + pop
    before: assets/sketch.png       # sketch / screenshot / subject crop
    after: assets/models-3d.png     # REAL Vi3W output: image, screen-capture video, or…
    glb: assets/model.glb           # …a GLB exported from Vi3W (rendered as a turntable)
    seconds: 5.6
    label: "Real Vi3W output"       # honesty label under the 3D card
    timer: "27 s · real time"       # only if actually measured
  - id: cta
    type: cta
    seconds: 3.0
    line: "Sketch → 3D in *3 clicks*"
    button: "Comment your doodle ✏️"   # an action, never "free"
    after: assets/models-3d.png     # or glb:, logo:

vo:                                 # lines never overlap; the builder pushes a line later if needed
  - { at: 0.15, text: "…" }         # seconds…
  - { at: reveal, offset: 0.3, text: "…" }   # …or a segment id + offset

source:                             # only with `type: source` segments (third-party clips; see hook-to-3d)
  url: https://…
  creator: "@handle"
  rights: permission                # own | permission | remix | recreate
  proof: assets/permission.png      # required for permission

post: { caption: "…", hashtags: [gamedev, indiegame, sketchto3d] }
```

Layout (1080×1920): hook 230-530 px, gameplay band 560-1320, captions 1420 (top 380 during reveal/CTA).
Bottom 380 px and right 150 px stay clear of text for platform UI.

Other commands: `sheet <video> <out.jpg> [--fps 1]`, `frame <video> <sec> <out.png> [--crop x,y,w,h]`,
`build <dir> --no-render --stills 0,120,300` (PNG stills in `out/stills/`).
