# product builder: an AI-directed product-film pipeline (build spec)

This is the full write-up of how the Vi3W launch film was made. It's structured as a spec for turning that work into a reusable, Python-driven workflow that Claude Code can run as a plugin (skill + MCP server), with a small UI on top.

You give it **an ad idea, a story, a setting, a brand kit and labelled assets**. It gives back **finished, spec-exact reels in every aspect ratio**, plus the evidence it used to judge them.

---

## 0. Ground rules the whole system is built on

1. **Python does the operations; AI only makes decisions.**
   - Capture, file handling, rendering, mastering, measuring and logging are deterministic Python (plus Node for Playwright and Remotion).
   - The LLM is called only at named **decision points** (§5). Each takes structured input and returns structured JSON that Python validates.
2. **Everything is data.**
   - The film is a `timeline.json`: scenes, timings, cues, captions and music segments. The renderer is a pure function of that file.
   - AI edits data, not code. Code changes are for new *capabilities*, not new films.
3. **Never fake the product.**
   - Every UI frame, image and 3D model comes from a real run of the product.
   - Allowed: framing (crop, zoom, tilt), re-timing, cursor and highlight overlays, and material/lighting/camera for 3D.
   - Not allowed: invented UI, retouched outputs, edited geometry.
   - Generated b-roll (fal video) is allowed **only for non-product shots**, and is logged as generated.
4. **Deterministic renders.** No `Math.random()` at render time; seeded noise only, and every animation is driven by the frame number. The same inputs always produce the same video.
5. **Measure, don't guess.** Every render is verified with ffprobe and ebur128, a dark-frame scan, contact sheets and a waveform. Scores need cited evidence.
6. **Idempotent, cached stages.** Each stage writes to the project folder with a content hash. Re-running skips finished work, so you can iterate on stage 7 without re-capturing.

---

## 1. Inputs (what you give it)

### 1.1 `brief.yaml` (the only required file)
```yaml
project: vi3w-launch
product:
  name: Vi3W
  url: http://localhost:8080          # app under test (local or staging)
  auth: { method: test_token, script: scripts/mint-test-token.mjs }   # or: storage_state, none
idea: "A 3D artist gets an impossible car request at 2:47 AM; Vi3W saves the night."
story:                                 # free text OR beat list; AI normalises it to beats
  - "Dev asks for a car model in one hour"
  - "Artist sketches a sedan → image"
  - "Sketches mods ON the image → sports car"
  - "Generates 3D, delivers"
  - "Twist: it needs to fly → thrusters → new 3D"
  - "Cinematic finale; tagline"
tagline: "We built Vi3W so 3D artists can catch more sleep."
setting: "dark late-night room, cold monitor glow, wry Pixar-style humour"
cuts:
  - { name: hero,   seconds: 80, formats: [16x9, 9x16, 4x5] }
  - { name: social, seconds: 45, formats: [9x16, 4x5, 16x9], hook_seconds: 1.5 }
voiceover: false
music: { bpm: 120, mood: "minimal electronic, felt piano, confident" }
providers: { music: fal:elevenlabs/music, sfx: elevenlabs, video: fal:<model>, llm: claude }
budgets: { app_credits: 600, fal_usd: 10, max_iterations: 10, target_score: 9.0 }
rules:
  trademark_avoid: ["BMW"]             # never on screen; badges must not be legible
  honesty_labels: true
```

### 1.2 `brand.json` (editable in the UI)
```json
{
  "colors": {"ink":"#0B0B0C","accent":"#D4F77C","text":"#E2E6DA","muted":["#8E9686","#585E54","#3A3F36"],"accentShadow":"#2E3A12"},
  "accent_rules": "accent only for strokes, cursor, highlighted words, thruster glow",
  "fonts": {"display":"Urbanist:800","body":"Urbanist:600","mono":"JetBrains Mono:400"},
  "tracking": {"headline":"-0.035em"},
  "motion": {"default_ease":"outExpo","ui_spring":{"damping":13},"linear_allowed":["caret","camera_drift"]},
  "logo": {"mark":"assets/logo-still.png","wordmark":"text"},
  "motif": "a lime line that becomes the next object"
}
```

### 1.3 `assets/manifest.yaml` (labelled assets: what each is and when to use it)
```yaml
- file: assets/logo-still.png
  kind: logo
  use: [title_sting, end_card]
  never: [over_product_ui]
- file: assets/music/hero.mp3
  kind: music
  licence: "generated, ElevenLabs via fal"
  use: [hero]
- file: assets/hdri/studio_small_03_1k.hdr
  kind: hdri
  use: [3d_stage]
- file: assets/photos/desk-real.jpg
  kind: photo
  use: [cold_open, end_room]
  notes: "real desk; preferred over the vector room"
```
The UI writes this file. AI reads it at the planning decision points to pick assets per beat, and Python enforces the `never` rules.

---

## 2. Pipeline overview

```
brief.yaml + brand.json + assets/
   │
S0 init ──► S1 treatment* ──► S2 beat sheet & timeline* ──► S3 storyboard (stills/animatic)
                                                              │
S4 product capture (Playwright) ◄── capture plan* ◄───────────┘
   │   └─ variant judging* (vision)
S5 audio & generative assets (music, SFX, fal video b-roll)
   │   └─ audio analysis (tempo/drops) → beat grid alignment
S6 data prep (frames→takes, GLB normalise, crops)
S7 compose (Remotion, timeline.json-driven)
S8 render + master + posters + SRT + spec verify
S9 review loop: evidence → score* (self + fresh reviewer) → fix plan* → apply → re-render (≤ N)
S10 handover (files, scoreboard, credits, director's note)

* = AI decision point. Everything else is plain Python/Node.
```

**Project folder layout (one per film):**
```
projects/<name>/
  brief.yaml  brand.json  assets/manifest.yaml
  state.json                 # stage status, hashes, costs, current iteration
  research/  treatment.md
  plan/      beats.json  timeline.json  capture_plan.json  shotlist.md
  capture/   <take>/frames/*.jpg frames.json events.json mouse.json out.jpg model.glb
  audio/     music/*.mp3 sfx/*.mp3 analysis.json
  video_gen/ <clip>.mp4 + prompt.json      # fal b-roll
  render/    out/*.mp4 *.png *.srt  raw/
  review/    itNN/ (sheets, stills, wave, scores.json)  SCOREBOARD.md
  logs/      capture-log.md  decisions.jsonl  costs.jsonl
```

---

## 3. Stage by stage: what was done, and how to automate it

For each stage: **what happened in the Vi3W run**, then **ops (Python)**, **AI decisions**, and **gotchas found the hard way**.

### S0: Init and environment check (ops)
- Check the tools: node, ffmpeg/ffprobe, Python with Pillow and numpy, Chrome, the Remotion deps installed, and that the app URL returns 200.
- **Ports:** never assume 3000 is free (a Next.js server was squatting on it). Pin the Remotion server port (`--port 3700`) and give `renderStill` random free ports.
- Load secrets from `.env` (git-ignored): `ELEVENLABS_API_KEY`, `FAL_KEY`, and the app auth.
- `git init` the project and commit after every stage.

### S1: Taste research and treatment (AI, optional)
- **Done:** a web search on Apple, Linear, Vercel, Figma, Arc, the AI-3D tools and Pixar story principles produced a taste board ("what to steal") and a one-page treatment. The treatment covered the logline, tone, colour script, music plan, camera language, transition motif and three screenshot frames.
- **Automate:**
  - One LLM call with web search, cached per *genre*, not per film.
  - Output: `treatment.md` plus `treatment.json` (motif, colour script per act, pacing targets, hook rule).
- **Keep it cheap:** reuse the taste board across films in the same category.

### S2: Beat sheet → `timeline.json` (AI, then validated by Python)
- **Done:**
  - The story became 12 hero beats and 12 social beats on a **120 BPM grid**: 1 beat = 15 frames, 1 bar = 60 frames at 30 fps.
  - Major events sit on bar lines: title sting at 8.0 s, reveal drop, twist silence, finale drop.
- **AI:** turns the brief into `beats.json`: `{id, start, dur, kind, copy, caption, sfx_hints, music_section}`.
- **Python validates:**
  - Durations sum exactly to the cut length.
  - Cuts land on beats (±1 frame).
  - The hook happens within `hook_seconds`.
  - Copy is ≤ 4 words per headline.
  - Trademark terms are absent from all on-screen copy.
  - On failure, the reason goes back to the LLM for a retry.
- **Scene kinds**, which map 1:1 to reusable components (§4): `cold_open`, `chat`, `url_to_logo`, `product_shot`, `before_after`, `triptych`, `image_to_3d`, `plot_twist`, `finale_3d`, `end_room`, `end_card`, `video_clip` (fal b-roll), `photo_insert`.

### S3: Storyboard and animatic (ops)
- **Done:**
  - The real compositions were rendered as stills at key frames: one bundle, many stills, via `@remotion/renderer` `renderStill` with `puppeteerInstance` reuse.
  - Stills were tiled into contact sheets per format with ffmpeg/Pillow.
- **Automate:** `render_stills(comp, frames, scale)` and `contact_sheet(dir)`. Placeholder boxes are used before capture exists.
- **AI (optional):** a vision check of the storyboard against the rubric *before* capture. Story problems are cheap to fix here.

### S4: Real product capture (ops, with AI judging)
This is the most valuable and most fragile stage.

**Ops (Playwright + system Chrome), `scripts/capture.mjs`:**
- **Auth.** Seed the app's session into `localStorage` via `addInitScript`; Vi3W used the project's `mint-test-token.mjs` and a throwaway test user. Tokens expire after 1 hour, so re-mint before each capture batch.
- **Profile.** A persistent browser profile (`launchPersistentContext`) keeps the app state between steps.
- **Recording.**
  - Viewport 1920×1080 at **deviceScaleFactor 2**.
  - CDP `Page.startScreencast` gives JPEG frames with timestamps; the OS cursor isn't captured.
  - A 1 px element animated by `requestAnimationFrame` keeps frames flowing.
  - Every frame time, every **named event** (click, strokeStart, typeStart, generateClicked, imageReady…) and **every pointer position** (`mouse.json`) is logged. The film's cursor, click ripples and lime stroke overlays are all rebuilt from these logs.
- **Humanised input.**
  - Eased Bézier glides with a slight arc for cursor moves.
  - Strokes are drawn with slow-in/slow-out spacing.
  - Typing uses `pressSequentially` with a 30 ms delay, after `fill('')` to clear the field.
- **Cosmetics, applied only during capture.** A MutationObserver swaps the test email for "Vi3W Studio". No product UI is altered.
- **Step commands:**
  - `sketch` (draw on canvas → Draw mode → Generate)
  - `edit` (open sketch tools on the image → draw → prompt → ReGen)
  - `to3d` (pick model → Generate 3D → wait → Download GLB)
  - `look` / `models` (UI dumps)
- **Each run saves:** stage screenshots, `out.jpg` (the real generated image, downloaded) and `model.glb`.
- **Selectors.** Use visible text and aria roles from a UI dump (`dumpUI`). The model picker label changes after a choice ("Trellis" becomes "Hunyuan…"), so match a regex over every model name.

**The stroke designer (`scripts/strokes.py`):**
- Sketches are **code**: Bézier paths, ellipses and line segments in normalised 0..1 canvas space, humanised with seeded wobble.
- **Overlay strokes** (mods and thrusters) are placed on the *actual generated image*. The AI reads `out.jpg` and returns pixel coordinates for the parts (wheel centres and radii, deck line, hood centreline), and Python builds the strokes from them.
- A preview PNG is drawn over the image for a vision check before spending credits.

**AI decision points in S4:**
1. **Capture plan:** the prompts to type, which features to sketch, and the model choices. The prompts appear on screen, so trademark rules apply.
2. **Stroke placement:** a vision call on `out.jpg` returns part coordinates as JSON.
3. **Variant judge:** a vision call on N candidate outputs returns `{best, reasons, rejects[]}`, with hard checks:
   - No legible brand badge.
   - The change is dramatic at a 320 px thumbnail.
   - The requested feature is present (e.g. "all wheels gone", "car visibly hovering").
   - Composition matches the sketch.
4. **Retry policy:** if the judge rejects, strengthen the prompt and re-run (bounded by the budget).

**Gotchas found (encode these as automatic checks):**
- **Stale state.** A reused studio showed the *previous* image while generating, and the prompt field kept old text. Use a **New Studio per chain** and clear inputs.
- **History order is unstable.** Select images by **pixel-matching** against `out.jpg` (`find_index.py`), never by position.
- **Image waits.** "Image ready" means a new `http` image src that wasn't on the page before. Counting images fires early.
- **Trademark leaks.** The generator drew a BMW roundel even when told not to. The fix was to **re-run the chain** with an unbranded prompt; retouching wasn't allowed. Run a badge check on every output.
- **Credits and plan gates.** Free users can't pick premium 3D models. Grant XP, or put the test user on the unlimited list, then **restart the dev server so it re-reads its env**.
- **Big 3D models** (Hunyuan, about 50 MB) take time to download into the app's viewer. Capture its *loaded* state for the Export beat.
- **Log real timings** (the app's own toast and wall clock). They become honest on-screen tags ("3 min 7 s · real time").

### S5: Audio and generative assets (ops, with small AI prompts)
- **Music.**
  - **ElevenLabs Music needs a paid plan on direct API keys.** It works through **fal** (`fal-ai/elevenlabs/music`), using a *composition plan* whose section durations match the edit (intro, drop at the sting, build, groove, break at the twist, rebuild, drop 2, outro).
  - Generate 2 variants; also generate a separate 9 s **outro cue** so the tagline isn't silent.
- **SFX.** ElevenLabs `/v1/sound-generation` produced 21 cues (ping, click, pencil, whoosh, riser, impact, lock-in, chime, scratch, ignite, hover, fly-by, snore…). **Maximum 4 concurrent requests**, otherwise 429.
- **Audio analysis (numpy, no AI):**
  - Low-band onset envelope gives the kick positions, so tempo and **beat phase**.
  - The biggest energy rises give the drops.
  - Solve the **music offsets** so drops land on the edit's bar lines. In Vi3W, delaying the music 1.15 s put its entry on the 8.0 s sting, and re-entering at 52.85 s put drop 2 on the 62.0 s lift-off.
- **fal video generation (new, recommended).**
  - Use it for **non-product** shots only: a human at a desk at 2:47 AM, hands on a tablet, an establishing room shot, abstract transitions. This closes the review's biggest "missing asset" gap (there's no human in the story).
  - **Ops:** queue submit, poll, download, then conform with ffmpeg (fps 30, scale/crop per format, trim, colour-match LUT toward the brand ink).
  - **AI:** writes the prompts from the beat and brand, and a vision judge picks the best of N.
  - **Rules:** never depict the product UI or outputs, and label generated clips as generated in `CREDITS.md`.
- Record every licence in `CREDITS.md` and every cost in `costs.jsonl`.

### S6: Data prep (ops)
- **Frames to takes.**
  - Convert each take's variable-rate screencast into data the renderer can index: frame times, files, events and the mouse log rebased to recording start (`make_takes.py` → `takes.ts`, or JSON).
  - Serve frames over a local HTTP server. Don't copy gigabytes into the Remotion `public/` folder.
- **GLB normalisation (Python + three.js at load):**
  - Read the glTF JSON (bounds, node transforms, materials, textures).
  - At load, bake the node transform (Hunyuan exports Z-up under a rotated node), centre it, and scale it uniformly to length 1. This is a rigid transform, not a geometry edit.
  - Keep the model's own PBR maps.
- **Automatic texture check.**
  - Extract the base-colour texture and render one frame unlit. If the paint is baked lighter than the source image (as Hunyuan did), allow a base-colour factor only. Log it.
  - Check whether the front view shows a badge, and if so ban front-on cameras for that model.
- **Anchor detection.** Thruster or wheel anchors are the centroids of the lowest vertices in each quadrant.

### S7: Composition in Remotion (ops; the AI edits only `timeline.json`)
**Architecture to keep (and make data-driven):**
- `brand.ts` is generated from `brand.json`: colour tokens, fonts via `@remotion/google-fonts`, named easings. No linear motion, except the caret and camera drift.
- `layout.ts` provides `useFormat()`, which returns `16x9 | 9x16 | 4x5 | 5x4` plus **safe zones**:
  - 9:16 avoids the top 220 px, the bottom 420 px and the right 120 px.
  - 4:5 keeps a 60 px margin.
  - Every scene **re-composes**; nothing is cropped or letterboxed from the 16:9 master.
- **Core components:**
  - **`Capture`:** the real screencast frame for any source time. It uses a **monotone cubic (PCHIP) time-remap** from keyframes `[[localFrame, sourceSec]…]`, so speed ramps are smooth with no stalls. It's cropped by an animated **focus rect** in page coordinates, which `fitCrop` turns into any aspect and clamps to the page. On top it draws the **cursor** (rebuilt from `mouse.json`, with click ripples) and the **lime stroke replay** (pointer-down segments).
  - **`ProductShot`:** a floating window (tilted in 16:9, full-bleed in 9:16), a headline column, an honest timing tag, and an entrance with no fade-to-black.
  - `ChatPanel` (a generic, unbranded chat), `Room` (a monitor in a dark room, an empty chair), `GenericViewport` (an unbranded default cube).
  - **`Headline`:** a per-word opacity, rise and blur-in reveal. *Masked wipes slice glyphs into slivers; the reviewers flagged that every time.* `LimeLine` draws the motif with `evolvePath`. `Tag` is mono and 18 px or larger.
  - **3D (`@remotion/three`):**
    - `Car`: the real GLB with a clearcoat physical material and a **feature-edge scan** (EdgesGeometry lines clipped by a moving plane, then the solid; a triangle wireframe becomes a white blob on dense meshes).
    - `Thrusters`: deterministic particles via `@remotion/noise`, a gradient cone shader, and point lights.
    - Also: `SketchTunnel` (drei `Line` rings), the `Cam` rig, bloom via `@react-three/postprocessing`, `CameraMotionBlur` (16 samples for fast passes; 6 samples looks like ghosting), floor dithering, fog to hide the horizon line, and emissive only on bright texels via a shader patch.
  - `Captions`: word-by-word highlight, unlit words at 72%, in the safe band.
  - `Finish`: grain at 8% (it hides banding) and a vignette.
- **`timeline.json` drives:** scenes (kind, from, duration, props), SFX cues `[frame, name, vol, dur]`, captions `[from, to, text]` and music segments `{from, trimSec, dur, volumeKeys}`. Python generates the Root and compositions for every cut × format, plus Poster compositions.

**Gotchas:**
- ThreeCanvas width and height must be integers.
- `useFrame` is forbidden; drive everything from `useCurrentFrame()`.
- `<Sequence layout="none">` inside a canvas.
- React's `key` prop can't be used as a component prop name.
- An interpolate input range must be monotonic. Guard disabled beats; a `stare: 9999` once crashed the social cut.
- GIF logos with black boxes: use a still PNG with `mixBlendMode: screen`.
- The film must never show the product's previous state (stale panels): check the first frame of each capture scene.

### S8: Render, master, deliver (ops)
- `render_all.sh` for each composition:
  - `remotion render … --codec h264 --crf 17 --pixel-format yuv420p --audio-bitrate 320k --concurrency 4 --timeout 240000 --port 3700 --gl angle`
  - Heavy GLBs need a lower concurrency and a longer timeout.
- **Mastering:**
  - Two-pass `loudnorm` to I=−14 LUFS and TP=−1.5 dB.
  - `aresample=48000`, AAC 320k, `-shortest` (otherwise the AAC tail makes 45.0 s files 45.1 s), and `+faststart`.
  - Video is stream-copied.
- **Posters:** Remotion `Poster-*` compositions (a split before/after on the accent line plus one line of copy), not frame grabs.
- **SRT:** generated from the caption and dialogue cue list for the 16:9 masters.
- **Verification (fail the stage if any check fails):**
  - Duration exact.
  - Resolution, fps, codec and profile, pix_fmt.
  - AAC 48 kHz stereo.
  - −14 ±0.5 LUFS, true peak ≤ −1 dBTP.
  - Zero decode errors.
  - A dark-frame scan (no unintended near-black frames).
  - Output: `spec-table.md`.

### S9: Review and self-improvement loop (ops builds the evidence; AI judges)
**The evidence pack, all Python:**
- Contact sheets at 2 fps with timecode labels (Pillow, since this ffmpeg build lacks drawtext).
- 10 fps strips for transitions.
- Full-res stills at the "screenshot frames".
- 320 px thumbnail tests of posters and wipes.
- The waveform (`showwavespic`).
- The loudness report and the dark-frame list.
- The same pack for every format.

**Scoring:**
- A 10-dimension weighted **rubric** covering hook, story, product clarity, before/after, motion, visual design, the 3D finale, pacing and sync, format adaptation, and tech and honesty.
- Every score must cite a timecode.
- **Self-score first, then a fresh reviewer.** Spawn a fresh reviewer agent each iteration with *only* the evidence pack, the rubric and the hard rules; it never sees the reasoning.
- If the two scores differ by more than 1 on a dimension, **the lower one counts**.
- A 10 needs every dimension at 9.5 or above, plus no medium or high issues.

**The fix loop:**
1. The reviewer returns ranked problems (gain ÷ effort) with fixes, each tagged *craft*, *real-output-bound* or *missing-asset*.
2. **Verify every claim** against full-res stills before acting. Reviewers misread tiled contact sheets: "clipped headline" was a tiling artefact, while "black frame at 20.0 s" was a real one-frame dip.
3. **The AI decides** which fixes to apply. Each is expressed as edits to `timeline.json` or component params, or as a re-capture request.
4. Python applies the edits, renders debug stills of the changed frames, checks them, then re-renders.
5. **If the score drops, revert** the change and log why.
6. **If a dimension is stuck for 2 iterations, change the approach** (a new shot type, layout or asset), not the parameters. In Vi3W, going full-bleed in 9:16, swapping masked text reveals for blur-ins, and **upgrading the 3D model to Hunyuan 3D 3.1 Pro** broke the plateaus.
7. Commit `iteration NN (score A → B)`, and update `SCOREBOARD.md` and `iteration-NN.md`.

**What the Vi3W loop showed:**
- The score went 5.6 → 6.4 → 6.5 → 6.4 → 6.4 → 6.5 → 6.7 → 6.8 → 6.8, then 7.25 with Hunyuan.
- Parameter tweaks plateau. **Asset upgrades move the score most:** a better 3D model, and in future a real human shot and a scored track. The agent should recognise "real-output-bound" and "missing-asset" ceilings early and say what it needs instead of looping.

### S10: Handover (ops, plus one AI note)
- The 6 masters, posters, SRTs, `spec-table.md`, `SCOREBOARD.md`, the final log with honest remaining weaknesses, `CREDITS.md` and `capture-log.md`.
- A director's note (one AI call): the creative choices, which file goes on which platform, and first-line captions.

---

## 4. Scene-kind library (the reusable building blocks)

| Kind | Props (in `timeline.json`) | Built from |
|---|---|---|
| `cold_open` | clock text, chat messages and times, viewport, stare beat, slam text | Room, GenericViewport, ChatPanel, Clock |
| `url_to_logo` | url, logo, sub line, timing | glyph reflow + LimeLine |
| `product_shot` | take, timeKeys (src s), focusKeys (page rects), headlines, tag, lime overlay | Capture + ProductShot |
| `before_after` | before img, after img, wipe keys, labels | masked wipe card |
| `triptych` | images + labels | cards |
| `image_to_3d` | capture take + keys, image, glb, scan timing, export take | Capture + LiftStage (3D) |
| `chat` / `plot_twist` | messages with typing, big text | ChatPanel, slam |
| `finale_3d` | glb, shot list (ignition, lift-off, tunnel, slow-mo, pass-by), blur samples | Car, Thrusters, SketchTunnel, Cam, Bloom |
| `end_room` / `end_card` | clock, monitor capture time, sleep timing, tagline, logo, url, CTA | Room, Headline, LimeLine |
| `video_clip` *(new)* | fal clip, in/out, grade, caption | `<OffthreadVideo>` + LUT |
| `photo_insert` *(new)* | asset id, Ken Burns keys | Img + move |

New products reuse the same kinds. Only the capture plan and the copy change.

---

## 5. AI decision points (the only places an LLM or vision call happens)

| # | Decision | Input | Output (validated JSON) | Model |
|---|---|---|---|---|
| D1 | Treatment | brief, brand, cached taste board | `treatment.json` | Claude (text + web) |
| D2 | Beats → timeline | brief, treatment, scene-kind catalogue, BPM grid | `beats.json` → `timeline.json` | Claude |
| D3 | Capture plan | beats, app UI dump, product rules | steps, prompts to type, model choices | Claude |
| D4 | Stroke placement | `out.jpg` + feature list | part coordinates (px) | Claude vision |
| D5 | Variant judge | N outputs + checks | best id, pass/fail per check, reasons | Claude vision |
| D6 | Music/SFX/video prompts | beats, mood, durations | composition plan, SFX list, fal prompts | Claude |
| D7 | Asset selection per beat | the labelled asset manifest | asset id per beat (`never` rules enforced by Python) | Claude |
| D8 | Self-score | evidence pack, rubric | per-dimension scores with evidence | Claude vision |
| D9 | Fresh review | evidence pack, rubric, hard rules only | scores and ranked fixes with tags | separate Claude agent |
| D10 | Fix plan | merged review, current timeline | a JSON patch for the timeline/params, or a re-capture request | Claude |
| D11 | Director's note | final scores, files | markdown | Claude |

**Guardrails:**
- Every output is JSON-schema validated, with a retry that includes the validator error.
- Each decision is logged to `decisions.jsonl` with its inputs' hashes.
- Budgets are enforced before any paid call.
- The honesty and trademark rules are injected into D2–D10 *and* checked by Python.

---

## 6. Claude Code integration: plugin = skill + MCP server

**Recommendation:** a Python package **`reelforge`** with three faces:
1. A **CLI** (`reelforge run|stage|review|render …`) for scripting and CI.
2. An **MCP server** (Python, FastMCP) exposing each deterministic operation as a tool, so Claude can call them from any session.
3. A **Claude Code plugin** that bundles the MCP server config, a **skill** (`SKILL.md`) that teaches Claude the workflow and the decision rules, and slash commands.

**MCP tools (ops only; each returns paths plus a short summary):**
```
project_init(brief_path) · env_check() · render_stills(comp, frames) · contact_sheet(dir)
capture_step(kind, take, args) · ui_dump(view) · find_image(ref_path) · mint_auth()
gen_music(plan) · gen_sfx(list) · gen_video(prompt, seconds, aspect) · analyse_audio(file)
make_takes(takes) · inspect_glb(path) · texture_check(glb)
write_timeline(json) · render(cut, formats) · master(file) · posters() · srt()
verify_specs(dir) · scan_dark_frames(file) · evidence_pack(iteration)
git_commit(msg) · costs()
```

**The skill (`skills/reelforge/SKILL.md`) tells Claude:**
- The stage order and the decision points (D1–D11) with their JSON schemas.
- The hard rules: no faked UI, trademarks, honesty labels.
- The loop policy: lower score counts, verify reviewer claims, revert regressions, change the approach after 2 stuck iterations, and stop and ask for a missing asset when it's the ceiling.
- **When to spawn the fresh reviewer subagent**, and what to give it (evidence only).

**Slash commands:** `/reel-new` (wizard → brief), `/reel-run` (the full pipeline), `/reel-review` (one loop iteration), `/reel-render`.

Why this split: the MCP tools make every operation callable and testable without AI. The skill holds the judgement, so it can be improved without code changes.

---

## 7. Small UI (local web app)

**Stack:** FastAPI (or a Next.js app calling the CLI) + SQLite/JSON files. It runs alongside VS Code.

- **Brief:**
  - A form for the idea, story beats, tagline, setting, cuts and formats, providers and budgets.
  - "Normalise with AI" calls D2 and shows the beat table for editing.
- **Brand kit:** colour pickers that preview against ink (with contrast warnings), font pickers, accent rules, easing presets ("snappy", "calm", "Apple"), and a motif description.
- **Asset library:**
  - Drag-and-drop upload.
  - **Labels:** kind, usage beats, never-use, licence, notes.
  - Previews, and auto-tags (dimensions, duration, dominant colours).
- **Run monitor:** stage status, live logs, costs, credits left, and approve/skip gates (e.g. "approve the capture variants").
- **Review gallery:** contact sheets, stills, waveform, scores per iteration, a reviewer-vs-self diff, and buttons to *apply fix*, *reject fix* or *re-capture beat*.
- **Deliverables:** players for every master, the spec table, downloads.

---

## 8. fal.ai integration details
- **Endpoints:** `queue.fal.run/<model>` with an `Authorization: Key …` header. Submit, then poll `status_url`, then fetch `response_url`, then download.
- **Video:** choose the model per need (text-to-video for establishing shots, image-to-video to animate a real still subtly). Save `prompt.json` with each clip.
- **Conform:** 30 fps CFR, the cut's resolution, a crop that respects safe zones, a grade toward the brand ink, and a loudness-free audio strip.
- **Honesty:** generated clips can never show the product's UI or outputs, and are listed in `CREDITS.md`.
- **Music:** `fal-ai/elevenlabs/music` with `composition_plan.sections[{section_name, positive_local_styles, negative_local_styles, duration_ms, lines: []}]` and `respect_sections_durations: true`.

---

## 9. Budgets and timings seen in the Vi3W run
- **Image generation:** about 13 s each. **Trellis 3D:** 30–84 s. **Hunyuan 3D 3.1 Pro:** about 3 min, 50–60 MB per model.
- **Full 6-master render:** about 8 min with light models, about 35 min with Hunyuan models (concurrency 4).
- **One review iteration** (render, evidence, review agent, fixes): about 15–20 min.
- **App credits:** about 330 XP across 3 capture chains (including two re-shoots for trademark and stale-state problems).

---

## 10. Build plan (suggested milestones)
1. **M1, Ops core:** project layout, `env_check`, capture driver (port `capture.mjs`), take prep, render, master, verify. Reproduce the Vi3W film from its existing `timeline.json`.
2. **M2, Data-driven timeline:** move scenes, cues, captions and music into `timeline.json`, and generate the Root from it.
3. **M3, Decision points:** D2–D5 and D8–D10 with schemas, validators and logging.
4. **M4, MCP server, skill and plugin:** tools plus `SKILL.md` plus slash commands, tested from Claude Code.
5. **M5, fal video and asset manifest:** the `video_clip` and `photo_insert` scene kinds, D7.
6. **M6, UI:** brief, brand kit, asset library, run monitor, review gallery.
7. **M7, Hardening:** automatic gotcha checks (stale state, badge, dark frames, glyph slicing, port conflicts, token expiry, AAC overrun) as pre-flight and post-render checks.

---

## Appendix A: The "gotchas" checklist (each becomes an automatic check)
| Gotcha | Check / fix |
|---|---|
| Port 3000 taken by another dev server | pin `--port`; random ports for stills |
| Auth token expires after 1 hour | re-mint before each capture batch |
| Stale studio shows the previous output | a New Studio per chain; vision check of the first capture frame |
| The prompt field keeps old text | `fill('')` before typing |
| History order shifts | select by pixel match |
| A brand badge in the output | badge check in D5; re-run, never retouch |
| A premium model is plan-locked | unlimited list or credits; **restart the dev server to reload env** |
| ElevenLabs Music 402 on a free key | route through fal |
| ElevenLabs 429 | maximum 4 concurrent requests |
| ThreeCanvas non-integer size | round the dimensions |
| A non-monotonic interpolate range | guard disabled beats |
| Fade-in dips to black at cuts | product entrances never fade from 0 |
| Masked text reveals slice glyphs | use per-word blur-in |
| A dense mesh wireframe is a white blob | EdgesGeometry feature lines |
| Motion blur ghosting | 16 samples for fast passes |
| Gradient banding | dithering + 8% grain |
| AAC makes files 0.1 s long | `-shortest` in the master |
| A heavy GLB times out the render | concurrency 4, `--timeout 240000` |
| Vertical cuts look like crops | full-bleed product shots in 9:16, re-composed layouts |
| Reviewer misreads contact-sheet tiles | verify claims on full-res stills before acting |
