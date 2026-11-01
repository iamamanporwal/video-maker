---
name: film-director
description: Direct a short film / mini-documentary / cinematic reel at a Disney-Pixar craft level - color script, shot list keyed to VO word times, camera and motion language, typography, transitions, sound design - and build it in Remotion. Use after story-architect, or when the user asks for "cinematic", "documentary style", "storytelling visuals", "make it look premium", or a 45-120 s narrative piece.
---

# Film director

You own every frame. You get the script from `story-architect` and produce `direction.md` (treatment, color script, shot list) and then the Remotion composition. Use `remotion-best-practices` for API details, `cinematography` for shot language and `frontend-design` for type taste.

## 1. Treatment (half a page)

- **Look in one sentence** ("1980s archival documentary that bleeds into colour as the dream comes true").
- **Rules of the world:** what is allowed on screen and what never is. Rules give a film its signature.
- **The one image** from the script, and how it's staged.

## 2. Color script (Pixar practice)

Draw the emotional arc as colour before any shot. One row per beat: saturation, temperature, contrast, key light, grain. Colour is the score you can see:
- Low points: desaturated, cool, high contrast, heavy grain.
- Payoff: full saturation, warm, light leak or bloom.
- Changes must be **gradual and motivated**. Colour arriving is a story event, not a filter.

## 3. Shot list, keyed to the voice

Generate the VO first. Then cut picture to the **real word timestamps**, never to estimates.

For each shot: id, VO words it covers, frame in/out, source (archival / generated / 3D / type), framing, camera move, transition in, and the type on screen.

Shot grammar:
- **One idea per shot.** Cut on the stressed word of a line, or 2-4 frames before it.
- **Every still moves:** Ken Burns pushes (2-6 % scale over the shot), drift, parallax split (foreground cut-out vs plate). Never a static still longer than 1.5 s.
- **Motivated transitions:** a match cut (shape, motion or colour), a whip, a film burn, a VHS tracking glitch, a hard cut to black for weight. No random wipes.
- **Rhythm:** shots shorten towards the payoff (3 s → 1.5 s → 0.8 s), then one long held shot on the payoff and on the quote.
- **Breathing room:** 0.5-1 s of picture with no VO after big lines. Silence is a tool.

## 4. Animation principles (the Disney 12, applied to motion graphics)

- **Slow in / slow out:** every move eases. Use outExpo for arrivals and inOutCubic for camera. Linear only for drift and timecode.
- **Anticipation:** a 2-4 frame counter-move before a big entrance.
- **Follow-through and overlapping action:** letters or elements stagger by 1-3 frames; never everything at once.
- **Staging:** one focal point per frame. Dim, blur or vignette the rest.
- **Timing:** heavy things move slowly, light things move fast. Text in 8-14 frames, a camera push across the whole shot.
- **Arcs:** camera and objects travel on curves, not straight lines.
- **Exaggeration:** the payoff gets the biggest scale change in the film.
- **Appeal:** fewer, better elements. If in doubt, remove it.

## 5. Typography

- Pair a **classic serif display** (Playfair Display, Cormorant, DM Serif) with a **restrained sans or mono** for the metadata (Inter, IBM Plex Mono). Year stamps go in mono or typewriter.
- Track caps out (+0.2em) for small labels and tighten large serif headlines (-0.02em).
- Text reveals by mask, letter-spacing collapse, or typewriter. Never a bounce in a documentary.
- Keep platform safe zones: nothing important in the top 220 px or the bottom 380 px of a 1080x1920 frame. Mind the right-hand action rail.

## 6. Texture and period FX (taste, not noise)

Film grain (seeded), gate weave (sub-pixel), vignette, halation and bloom, VHS chroma split, tracking lines, head-switching noise, a REC/timecode overlay. Use them **in bursts at transitions** and lightly underneath elsewhere. They must never fight the face or the type. Effects decay as the story moves to the present: the past is textured, the present is clean.

## 7. Sound design

- Music: a single emotional track (free YouTube licence, see memory). Its swell should land on the payoff. Re-cut it to the picture with measured cue points.
- VO: -16 LUFS integrated per line. Music ducks 10-14 dB under speech. Final master -14 LUFS, true peak ≤ -1 dBTP.
- Foley that sells the period: projector whirr, VHS clunk, camera shutter, typewriter keys. Put them in the gaps between lines, never on words.

## 8. Build

- One Remotion composition per film, under `node/remotion/src/shorts/`, registered in `shorts/Root.tsx`.
- Every animation is a function of the frame; noise is seeded. Load GLBs before mounting the Three stage.
- Render stills at each shot's midpoint first and review them as contact sheets. Render the full film only after the stills pass.
- Then hand off to `film-qc`.
