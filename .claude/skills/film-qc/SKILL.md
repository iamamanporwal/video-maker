---
name: film-qc
description: Quality-check a rendered short film or reel - technical spec, loudness, black/frozen frames, safe zones, contact-sheet visual review, and a scored rubric loop (score → fix list → re-render) until it reaches ~9/10. Use after any render, when the user asks to "review", "QC", "check quality", "is it good enough", or before copying a video to FinalUploads.
---

# Film QC

Nothing ships without evidence. Write every pass to `REVIEW.md` in the project: the score table, the evidence, the fix list, and what changed.

## 1. Technical gate (automated, must all pass)

```bash
f=out/film.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt -show_entries format=duration -of json "$f"
ffmpeg -nostats -i "$f" -af ebur128=peak=true -f null - 2>&1 | tail -12           # I ≈ -14 LUFS, TP ≤ -1.0
ffmpeg -nostats -i "$f" -vf blackdetect=d=0.25:pix_th=0.06 -an -f null - 2>&1 | grep black_   # only intended blacks
ffmpeg -nostats -i "$f" -vf freezedetect=n=0.002:d=1.5 -an -f null - 2>&1 | grep freeze_     # no accidental freezes
ffmpeg -nostats -i "$f" -af silencedetect=n=-45dB:d=1.2 -vn -f null - 2>&1 | grep silence_  # only intended silences
```

The spec: 1080x1920 for vertical, h264 + yuv420p, AAC 48 kHz, 30 fps, and the duration within ±0.5 s of plan.

## 2. Visual evidence

- **Contact sheet:** one frame per second, 6 columns, `ffmpeg -i f -vf "fps=1,scale=270:-1,tile=6x8" sheet_%02d.png`. Read every sheet.
- **Shot midpoints:** a full-res still at the midpoint of every shot. Check type kerning, safe zones (top 220 px, bottom 380 px, right rail), and focus.
- **Transitions:** 3 frames each side of every cut. No one-frame flashes of the wrong shot, no empty frames.
- **Colour arc:** sample average saturation every 2 s (`signalstats` SATAVG) and check that the curve matches the colour script.

## 3. Audio evidence

- Waveform image: `ffmpeg -i f -filter_complex showwavespic=s=1600x300 -frames:v 1 wave.png`.
- VO intelligibility: music must sit ≥ 10 dB under the voice during speech. Measure the music bus vs the VO bus, or the dips in short-term loudness.
- No clipped words, no music cut mid-phrase, and the ending resolves (fade or a hard button on a beat).

## 4. Scored rubric (each out of 10, cite evidence for every score)

| # | Criterion | 9-10 looks like |
|---|---|---|
| 1 | Hook (0-3 s) | Thumb stops. A loaded image or line, no logo. |
| 2 | Story clarity | A stranger can retell it after one watch. |
| 3 | Emotional arc | The temperature rises to the payoff and lands the quote. |
| 4 | Visual craft | Every frame is composed, with motivated motion and no dead stills. |
| 5 | Colour and texture | The colour script reads. FX support it and never distract. |
| 6 | Typography | Classy, legible on a phone, inside safe zones, no orphans. |
| 7 | Voice | Natural, documentary gravity, correct pronunciation ("View"). |
| 8 | Sound mix | Voice is always clear, music swells on cue, clean ending. |
| 9 | Brand bridge | Vi3W feels earned. Real product and models shown. |
| 10 | Accuracy and rights | Facts verified. Every asset logged in RIGHTS.md. |

**Overall** is the mean, but any single criterion below 7 blocks shipping.

## 5. The loop

1. Score with evidence, and write it to REVIEW.md.
2. Write a fix list ordered by impact (biggest score gain per unit of effort).
3. Apply the fixes. Reuse the assets; no new paid generation unless a fix needs it, and log the spend if it does.
4. Re-render, re-run sections 1-4, and re-score.
5. Stop at ≥ 9.0 overall with nothing below 8, or after 4 passes. Then list what still holds it back.

Be a harsh reviewer. Score as a stranger seeing it on their phone, not as the person who built it. Ask "would I rewatch this?" and "would I share this?".

## 6. Ship

- ≥ 8.5 → `FinalUploads/<name>.mp4` plus `<name>.txt` (caption, credits, and any rights warnings first).
- Below that → `FinalUploads/Drafts/`.
