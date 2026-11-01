# anime-gf review log

## v1 — 7/10
- End card appeared while line 1 ("…so I'm basically real?") was still playing (giggle lead pushed it to 16.4 s).
- Model faced away during "If I was your girlfriend…" (spin kept looping under the CTA).
- Jessica (premade) reads adult, not anime. Free ElevenLabs tier blocks library voices (Aerisita, Lulu) via API; 544 chars left.

## v2 — 8/10
- Spin tail 156 → 209 frames: line 1 fully over the spin, CTA lands with line 2.
- New `cta_settle`/`cta_sway` in reelforge.morph: model whips to front in 0.6 s and sways ±16° for the CTA line.
- Audit: SNR p10 33.5 dB, no SFX on words.

## v3 — 8.5/10 (pending user's ear)
- VO pitched +3 semitones locally (asetrate 1.19 + atempo, same duration, word timings unchanged).
  Originals in public/vo-orig/. Output: out/anime-gf-9x16-anime-pitch.mp4 vs out/anime-gf-9x16-jessica.mp4.
- Open: permission proof from @Tachibana_Sawa not yet saved (assets/permission.png) — required before posting.

## v4 — 9/10
- User: model misaligned (source camera is slightly above and far) and voice not anime enough.
- Alignment: splash ring ellipse ≈ 1:4 → elev 18°, hair falls to the right → yaw 15°. Box [575,770,1045,1480]
  matched on eyes/mouth/glasses/arms (ref/ov2.jpg). Model now sits on her exactly before the lift.
- Voice: Kawaii Aerisita (library, median F0 286 Hz vs Jessica 182) through fal's ElevenLabs v3 (`voice.provider: fal`),
  since our key is free tier. ~$0.01.
- Retimed: Aerisita is faster → spin tail 162, CTA 4.8 s, total 19.7 s. She faces front on "real?" and the whole CTA line.
- Audit: SNR p10 30.3 dB, no SFX on words.
- Minor/open: back of the model is showing on "Wait… I'm 3D now?". Permission proof still missing.
