# Review: vi3w-memes (2026-11-01)

Format: 9:16 split screen. Top half is the setup and bottom half the meme. No on-screen text before 4.5 s (user rule),
so meme audio and motion carry the hook. Then meme captions, a Vi3W reveal on real outputs, and the shared CTA card:
"Try Vi3W.in / Turn sketches and images into 3D in seconds." VO (Laura via fal) speaks only that CTA line, and the mix
ducks everything under it. Build: `python -m reelforge.split <dir>` (body) then `python -m reelforge.shorts build <dir>`.

## Loop 1 (first full renders)
| # | Score | Problems found |
|---|---|---|
| 01 blender-hour-9 | 8.0 | ding SFX on the first VO word (audit `sfx_on_words` 14.6 s); full-frame 640p monkey too blurry (fixed pre-render with a split); top text under platform UI (moved to y 210) |
| 02 more-3d | 8.5 | stray border lines on the sneaker render (cropped copy); Korean clip peaks near 0 LUFS (gain 0.13-0.35) |
| 03 anime-hair | 8.5 | green chibi too dark (`bright` grade on both chibis) |
| 04 baddie-3d | 8.0 | freeze landed on the wrong character / a white flash (now 5.62 s = VIP baddie); reveal section quiet (-18 LUFS) |
| 05 code-vs-models | 8.0 | cube filled the pane (contain + flat bg); rage shot was motion blur (switched to laugh 2.2 s); reveal quiet |
| 06 game-jam | 8.0 | Doodle Derby slides too small (plain sketch/model sheets); reveal quiet |

Audio audit, all six: VO median -16.5 dB, SNR p10 17-33 dB (target ≥ 8). Gap bursts are the meme hooks before
the VO starts, which is intended. Short-term loudness stays between -12.5 and -19 LUFS from hook to CTA.

## Loop 2
- 01: removed the CTA ding. 04/05/06: music 0.22 → 0.32 under the reveal.
- Scores after the fixes: 01 8.5 · 02 8.5 · 03 8.5 · 04 8.5 · 05 8.5 · 06 8.5.

Known limits: 06 opens on two low-res (360p) rage clips, which suits the meme look but is the softest hook of the
set. Every short has at least one uncleared third-party clip, listed in RIGHTS.md and flagged at the top of each
FinalUploads caption file.

# Batch 2: Blender vs Vi3W races (07 chest, 08 car, 09 jet), 2026-11-01

User feedback on batch 1: only about 3 of 6 landed. They named the problem but never SHOWED the solution. New rule: the
real product must be on screen. Format: split-screen race on the SAME asset. Top = Blender timelapse + rage-typing
PIP. Bottom = real Vi3W capture + vibing PIP (Keyboard Cat / Keyboard Dog / the founder himself). Punchline row, then CTA.

| Loop | 07 chest | 08 car | 09 jet | Fixed |
|---|---|---|---|---|
| 1 (body sheets) | 7.0 | 7.0 | 8.0 | Demo 1 UI too small in "contain" (now crop left panel → right panel); baked Demo 1 captions cut at edges; slide transition at 4 s; 08 PIP black first frame, rage PIP on blur frames, punchline top = blur |
| 2 (full renders) | 7.5 | 7.5 | 8.0 | 07 black UI frame at 4.5 s, 1 s of "generating" dark, transition at 14.5 s, CTA opened dark → triptych CTA; 08 rage PIP blur at 7.5/11.5 s; 09 CTA opened on a tiny jet |
| 3 | 8.5 | 8.5 | 8.5 | 07 CTA ran into the "Download GLB" screen (re-timed); punchline dips to -19/-20 LUFS in 07/09 (sad-flute sting) |
| 4 | see below | 8.5 (shipped) | see below | final check: audit, loudness, contact sheet |

## Batch 2, v2 (user re-brief): struggle hook FIRST, then the solution
User: struggle and solution must not play at the same time. New structure for 07/08/09:
0-5 s Blender struggle only (timelapse on top, rage-typer full bottom pane, red crash freeze at 3.8 s, no text) →
5-~14 s real Vi3W flow with numbered steps on top, vibing person below (Keyboard Cat / Keyboard Dog / the founder's
own face cam cropped from demo1) → finished model rotating full screen + "that's it" line → CTA.

| Loop | 07 | 08 | 09 | Fixed |
|---|---|---|---|---|
| 1 (bodies) | 7.5 | 7.0 | 8.0 | final spins letterboxed / cropped; 08 crash pane white blur; 09 finale caught the recording's zoom |
| 2 (renders) | 8.0 | 8.0 | 8.5 | Vi3W section ~5 dB under the hook (music 0.22→0.34, vibing clips 0.55→0.8); 07 step 4 small dark chest + baked caption in finale; 08 "image" step showed the sketch |
| 3 (final) | 8.5 | 8.5 | 8.5 | 08 image step blurred by a recording zoom → clean still with push-in; audit clean (SNR p10 10.9-33.7 dB, no SFX on words), loudness within ~3 dB hook → CTA |
