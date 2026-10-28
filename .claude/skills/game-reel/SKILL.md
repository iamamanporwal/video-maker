---
name: game-reel
description: Turn gameplay footage of a game someone built with Vi3W into a 9:16 Instagram Reel / YouTube Short with a hook, ElevenLabs voiceover, karaoke captions, a sketch → 3D reveal and a comment-driven CTA. Use when the user points at game videos (e.g. the Input/ folder), asks for a game reel, a community showcase, or "make reels from these games".
---

# Game reel (community games made with Vi3W)

Goal of every reel: a viewer who builds games thinks "I could make my assets like that" and taps the link in bio.
The product moment is the **sketch → Vi3W 3D model** step; gameplay is the proof it ships.

Tooling: `.venv/bin/python -m reelforge.shorts …` (Remotion `GameReel` composition, 1080×1920, 30 fps).
Spec format: [reference.md](reference.md). A finished example: `projects/shorts/doodle-derby/reel.yaml`.

## Steps

1. **Look before you write.** For each source video:
   `python -m reelforge.shorts sheet "<video>" <scratch>/sheet.jpg --fps 1` and Read the sheet.
   Note timecodes for: the most surprising 2-3 s (the hook), any sketch / 3D-model frames, and 3-4 strong action beats.
2. **Check the creator.** Creators must have agreed to be featured (the user confirmed this for the Input/ games).
   Put their name or handle in `credit:` and the caption. Ask the user for a handle if you only have a name.
3. **Find the real Vi3W step.** Never fake the product.
   - If the footage contains the sketch and the Vi3W output (Doodle Derby's trailer does at 3-11 s), extract both:
     `python -m reelforge.shorts frame "<video>" <sec> <reel>/assets/x.png --crop x,y,w,h`.
   - Otherwise ask the user for a real Vi3W capture: a screenshot of the subject run through Vi3W, screen-recorded,
     or the exported GLB. Label it honestly, e.g. `label: "Recreated in Vi3W · real output"`.
   - No real output available → drop the `reveal` segment; keep the "made with Vi3W" claim in VO/credit only.
4. **Write `projects/shorts/<slug>/reel.yaml`** (16-24 s total):
   - `open` clip (2.5-3 s): the most visual moment, mid-action, legible at phone size. Hook text ≤ 6 words, one `*accent*` word.
   - `reveal` (5-6 s), then 2-4 gameplay clips of 2.5-3 s (vary `fit: crop` for close action, `fit: frame` for split
     screens / wide views), then `cta` (3 s).
   - VO: 4-5 lines, ≤ 55 words total, written for Laura (excited, young, social-media). Sound like a friend
     reacting, not a narrator: short bursts, questions, "wait", "okay", "nope!", "annnd it's gone".
     Use eleven_v3 audio tags sparingly (1 per line max): `[excited]` `[gasps]` `[laughs]`. Tags never show in captions.
     Line 1 is the hook spoken. Name the creator once. Write "Vi3W" (it's spoken "View"; captions show Vi3W).
   - CTA: never "free". Ask for an action people enjoy: comment (their doodle, dream car, a name for the
     character, which zone kills them), tag a friend, or save. Card line points to *Vi3W.in*.
5. **Layout check:** `build <dir> --no-render --stills 0,<reveal+40>,<mid>,<cta+20>`, tile and Read them. Check: hook
   legible on frame 0, nothing important under the bottom 380 px or the right 150 px, captions don't cover the subject.
6. **Render:** `build <dir>`. Read `out/contact.jpg`. Verify VO matches pictures and nothing is cut mid-action.
   Builder errors (VO longer than the reel, unknown segment id) mean fix the spec, not the builder.
7. **Hand over** `out/<slug>-9x16.mp4`, `out/poster.jpg`, `out/caption.txt`, plus a music pick (below).

## Hooks that work for this audience (game devs / 3D artists)

- Origin twist: "These karts were *pencil doodles*." / "This robot was a *10-second* sketch."
- Scale: "One person. *Every* 3D model." / "Built in a weekend, assets in *3 clicks*."
- Payoff tease: "Wait for the *upside-down* track." / "Zone 5 is *unreal*."
- Avoid: "Mario Kart", "Unreal Engine" or any trademark as a comparison on screen; claims you can't show ("in 5 minutes")
  unless the timing is real and logged.

## Music (added in the app, never baked in)

Reels are exported with VO + SFX only so trending audio can be added in Instagram / YouTube, where it is licensed and
gets reach. Cuts sit on short beats, so most 120-130 BPM tracks fit. Recommend a vibe, then tell the user to pick the
top match from Instagram's "Trending ↗" audio or the Shorts sound library that day:
- neon / synthwave games (Neon Drift, Heli Rush, Neon Velocity): synthwave, phonk, dark electronic
- cute / playful games (Doodle Derby, Coin Rush): upbeat pop, chiptune, meme-trend audio
- Keep the in-app music at ~15-25 % so the VO stays clear.

## Weak footage

Short or static recordings (e.g. Street Dodge, Neon Velocity) go into a compilation reel ("5 games built with
Vi3W models"): one 2-3 s clip per game, a `label:` with the game name, one credit line listing all creators.
