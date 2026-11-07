# REVIEW — Why did GTA 6 take 13 years?

## Pass 1 (preview v1, 86 s)
Evidence: out/contact-preview.jpg (1 fps).
Blockers: Pricedown not loading (serif fallback everywhere — `document.fonts.check` is true for unknown families);
opening frame = GTA VI logo (rz@24), 0:03 black (gp@5 = ESRB card); "REASON 3" title clipped; "polish" chapter on blank
magenta; story 79 s (slow).
Fixes: always load the FontFace; open on Lucia/Jason convertible (rz@26); gp@6.5; chapter title auto-size; TEMPO 1.13→1.16.

## Pass 2 (preview v2, 84 s)
Technical gates: blackdetect / freezedetect / silencedetect — clean. -14.0 LUFS, TP -1.4.
Mix: VO -16.7 LUFS vs ducked music -32 LUFS (15 dB under) → music raised 0.30→0.38 (~13 dB under, still ≥10).

| # | criterion | score | evidence |
|---|---|---|---|
| 1 | Hook | 8 | Lucia close-up → 2013 lifeguard tower; "4,811 days ago" + "you can now legally buy GTA 6" lands by 0:08 |
| 2 | Story clarity | 9 | four numbered reasons with chapter cards; one idea per line |
| 3 | Arc | 8 | money → cowboys → chaos (WASTED-style "leaked") → delays → "mission passed?" |
| 4 | Visual craft | 7 | letterbox bars (fixed via cropdetect), dup captions over chapter cards (hidden now), fallback logo card at 0:17-0:20, sketch on black at end |
| 5 | Colour/texture | 8 | act grades read (money green, RDR warm, chaos red/bw, Vice pink) |
| 6 | Typography | 8.5 | Pricedown captions/HUD; panels inside safe zones |
| 7 | Voice | 8 | Brian, single take, Whisper-checked; 1.16x |
| 8 | Mix | 8 | voice always on top; SFX on overlay hits |
| 9 | Brand bridge | 6.5 | "One sketch." over a sketch on black — abrupt, small |
| 10 | Accuracy/rights | 8.5 | hedged wording from RESEARCH.md; Rockstar footage credited, muted |
Mean 7.95 — #9 blocks.
Fixes: Bridge = loading-screen comic panels (sketch draws on → real Vi3W 3D car slams in) over B&W Vice skyline;
map aerial re-timed (0:56 black tail); NPC shot moved off the pink smoke; waiting on Blender 3D shots (calendar,
consoles, printer, hourglass, vault) to replace the footage fallbacks.

## Pass 3 (final, 84.2 s = 77.2 story + 7.0 shared outro)
Technical: 1080x1920 h264 yuv420p 30 fps, AAC 48 kHz, -14.0 LUFS / TP -1.5. black/freeze/silence detect: clean
(fixed: t2 fades in from black until 6.3 s → 6.6; gp map aerial 22.5 → 26.0; rz polish 46.2 → 46.5; yuvj420p → yuv420p).
3D shots in (Blender agent): calendar (hook), hourglass (title), consoles (3 generations), printer (prints money), vault (polish).

| # | criterion | score | evidence |
|---|---|---|---|
| 1 | Hook | 8 | Lucia → 2013 lifeguard → 3D calendar flipping; "legally buy GTA 6" + 18+ stamp by 0:07 |
| 2 | Story clarity | 9 | 4 numbered reasons, chapter cards, one idea per line |
| 3 | Arc | 8.5 | money (green) → cowboys (warm) → chaos (red/B&W, "leaked" wasted card) → delay cards → "mission passed?" |
| 4 | Visual craft | 8.5 | no dead stills, 3D metaphors, cut on stressed words; consoles slightly small in frame |
| 5 | Colour/texture | 8.5 | per-act grades + grain/vignette; Vice palette payoff |
| 6 | Typography | 8.5 | Pricedown captions/HUD/cards in safe zones; captions hidden under chapter cards |
| 7 | Voice | 8 | Brian, one take, Whisper-verified; 1.16x keeps it brisk |
| 8 | Mix | 8.5 | music ~13 dB under VO (sidechain), SFX on overlay hits |
| 9 | Brand bridge | 8 | loading-screen panels: our sketch → real Vi3W 3D car, then shared outro |
| 10 | Accuracy/rights | 7.5 | facts hedged per RESEARCH.md; Rockstar footage is uncleared commentary use (Content ID risk) |
Mean 8.35, nothing below 7 → FinalUploads/Drafts (ship bar 8.5). Holding it back: rights risk on Rockstar footage,
hook could open on a harder visual gag, consoles shot framing.
