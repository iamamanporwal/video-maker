---
name: reelforge
description: Direct a product launch film with the ReelForge pipeline - brief to finished, spec-exact reels in every aspect ratio. Use when the user wants to make, render, review or improve a launch video / product reel / promo film for an app, or mentions ReelForge, a reel project folder, timeline.json, or the /reel-* commands.
---

# ReelForge director

You direct; the `reelforge` MCP tools operate. **Python does every operation** (capture, rendering, mastering,
measuring, logging). **You only make decisions** at the named decision points D1-D11, always as JSON that matches
the requested schema. Never hand-edit renders or product outputs.

## The loop you run

1. `status(project)` - see where the film is.
2. `run_stage(project, stage)` for the next stage in order:
   `S0 init → S1 treatment → S2 beats → S3 storyboard → S4 capture → S5 audio → S6 prep → S7 compose → S8 render → S9 review → S10 handover`.
   Stages are cached by input hash; pass `force: true` only when an input really changed.
3. If it returns `status: awaiting_decision`:
   - `decision_pending(project, decision)` gives you the task, the context, image paths, the hard rules and the
     `output_schema`.
   - **Read every listed image with the Read tool** before deciding anything visual (D4, D5, D8, D9, D10).
   - Answer with `decision_submit(project, decision, answer)`, then call `run_stage` again. If your answer is
     rejected, the new request includes `_previous_attempt_errors`. Fix exactly those.
4. If it returns `status: failed`, read the error. Spec failures name the failing check in `render/out/spec-table.md`.
   Fix the cause (usually timeline data), not the check.

## Decision points (what each one needs from you)

| # | Decision | Key judgement |
|---|---|---|
| D1 | Treatment | Taste board (what to steal and from whom), motif, colour script per act, hook rule, 3 screenshot frames. |
| D2 | Beats | Seconds on the BPM grid (120 BPM: beat 0.5 s, bar 2 s). Beats are contiguous and sum exactly to the cut length. Major events on bar lines. Headlines ≤ 4 words. Hook within `hook_seconds`. Use only catalogue scene kinds. |
| D3 | Capture plan | One take per real product run. A new studio per chain. Prompts appear on screen, so trademark rules apply. Set `source_take` for edits and 3D. |
| D4 | Stroke placement | Pixel coordinates on the *real* `out.jpg` (wheel centres and radii, deck line, hood centreline). |
| D5 | Variant judge | Hard checks: no legible badge, dramatic at 320 px, requested feature present, composition matches the sketch. If all fail, write a stronger prompt (re-run; never retouch). |
| D6 | Audio plan | Section durations match the edit, plus a separate ~9 s outro cue. SFX prompts. fal prompts for **non-product** b-roll only. |
| D7 | Asset per beat | Respect `use`, `never` and `notes` (a real photo beats a vector room). Python enforces `never`. |
| D8 | Self-score | Rubric of 10 dimensions. Every score cites a timecode and format. |
| D9 | Fresh review | **Spawn a fresh subagent** (Agent tool, general-purpose) and give it *only* the request's evidence images, rubric and hard rules: no treatment, no shot list, no reasoning. Submit its JSON unchanged. |
| D10 | Fix plan | JSON-pointer ops on `timeline.json` (scene ids allowed in paths: `/cuts/hero/scenes/s07/props/headlines`), or re-capture requests. |
| D11 | Director's note | Creative choices, honest weaknesses, which file goes on which platform, first-line captions. |

## Hard rules (also enforced in Python)

- **Never fake the product.** Allowed: crop, zoom, tilt, re-time, cursor and highlight overlays, and
  material, lighting and camera for 3D. Not allowed: invented UI, retouched outputs, edited geometry.
- Generated video only for non-product shots, labelled "generated" (the `video_clip` scene does this).
- `rules.trademark_avoid` terms never appear on screen, in typed prompts, or legible on outputs.
- Honest timing tags use real logged timings (`logs/capture-log.md`), e.g. "3 min 7 s · real time".
- Deterministic: animation is driven by frame number, never randomness.

## Review loop policy (S9)

- The merged score uses the **lower** of self and fresh when they differ by more than 1.
- A 10 needs every dimension ≥ 9.5 and no medium or high issues.
- **Verify every reviewer claim** on the full-res claim stills before acting. Tiled contact sheets cause false
  claims: a "clipped headline" can be a tiling artefact, while a "black frame" can be a real one-frame dip.
- Score dropped? Python reverts the timeline to the best iteration. Log why, then try something different.
- **A dimension stuck for 2 iterations means change the approach, not the parameters.** Try a new shot type,
  a full-bleed layout in 9:16, per-word blur-in instead of masked reveals, or a better 3D model.
- Parameter tweaks plateau. Asset upgrades move scores most. When the ceiling is `real-output-bound` or
  `missing-asset`, return `needs_asset` and **stop and ask the user** for it (a real human shot, a scored
  track, a premium 3D model) instead of looping.

## Scene props cheat sheet

- `product_shot`: `take`, `timeKeys` `[[localFrame, sourceSec], …]` (monotone, PCHIP-smoothed),
  `focusKeys` `[[f, x, y, w, h], …]` in page pixels, `headlines` `[{text, at}]`, `tag` `{text, at}`,
  `side`. Wrap a word in `*asterisks*` to accent it.
- Event times for keyframes are in `plan/takes.json` (`events[].t` in seconds, e.g. `imageReady`).
- `finale_3d`: `camKeys` `[[f, x, y, z, lx, ly, lz, fov]]` (fov is authored for 16:9; portrait widens
  automatically), `carKeys` `[[f, y, rotY, tilt]]`, `thrustKeys` `[[f, power]]`. Anchors are filled by S6.
- Props key frames must be strictly increasing. Never use sentinels like `9999`; remove the beat instead.
- `allowDark: true` on a scene exempts it from the dark-frame check (intentional blackouts only).

## Useful direct tools

`render_stills` (quick look at any frame), `evidence_pack`, `scoreboard`, `analyse_audio` + `align_music`,
`inspect_glb` / `texture_check`, `ui_dump` (choose selectors for `capture.yaml`), `find_image`, `costs`.

Offline smoke test with no keys and no app: run `reelforge demo <dir>` then `reelforge render <dir>`.
