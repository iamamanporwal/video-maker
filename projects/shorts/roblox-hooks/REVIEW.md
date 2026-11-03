# Edit reviews: 06-deer-67, 07-noob-train, 09-vip-baddie

Each pass: score out of 10, what was wrong (with the measurement or frame that shows it), and the fix list for the
next pass. Audio numbers come from `python -m reelforge.mix <reel>`. They're measured on the VO and FX stems in
50 ms windows: the speech-to-background ratio (SNR) on voiced frames, SFX that start on a spoken word, and FX
bursts in the gaps.

## v1: deer 5/10, noob train 5/10

**Audio**
1. **SFX land on words.** Train: coil 7.47 s on "him", boing 10.73 s and button 11.50 s inside "Now the noob is a real 3D model". Deer: eat 9.87 s and button 10.70 s inside "Now he's a real 3D model". The `[laughs]` tag added about 0.4 s before the first word, so every later line ran long.
2. **The ducking pumps.** The side-chain compressor lets the hook music swell back between words (gap bursts at 0.4 and 1.5–1.7 s on the train). It sounds like breathing, not a mix.
3. **Back-to-back lines.** Train VO3 ends at 11.97 s and VO4 starts at 12.03 s, with no breath. VO3 also crosses the cut into the CTA, so its caption jumps to the top band mid-sentence (deer at 10.5 s too).
4. **Hidden auto-whoosh.** The default `sfx` adds a whoosh at the CTA cut (11.3 s) that the timeline never planned.
5. **Audit bug.** It reported SNR median 145 dB because silent FX frames weren't floored. The p10 (15 dB) was the real number.

**Picture**
6. **Black bars on the hook.** The deer clip uses 1080×1468 of the frame and the train only 1080×1080, so about 40% of the first, most important seconds is black.
7. **Tiny subject at the freeze.** The train noob is about 100 px tall when the scan starts, so the "this becomes 3D" moment is hard to read.
8. **Dead air at the end.** The CTA holds a static spin for about 2 s after the last word (deer 13.0–15.2 s, train 13.9–16.0 s).
9. **Captions over the model.** On the train CTA, the "WHO JUMPS INTO" caption covers the noob's head. On the deer CTA it touches the antlers.

**Story**
10. **Long hook lines.** The deer hook line runs 4.2 s, past the 3 s guideline, but it pays off the "67". It stays, with nothing else talking over it.

### Fix list for v2
- [ ] Replace the side-chain with smooth volume automation: the FX bus dips -11 dB from 120 ms before each line to 250 ms after it. No pumping.
- [ ] Measure the real word times, then place every SFX in a gap of at least 0.25 s from any word, checked by the audit.
- [ ] Drop `[laughs]` where it delays a line. Leave at least 0.3 s between lines, and make sure no line crosses a segment cut.
- [ ] Turn off the auto whoosh (`sfx: false`). The morph already has its own pop and whoosh.
- [ ] Fill the hook frame: crop out the bars, enlarge the content (1.2×) and put a blurred copy behind it.
- [ ] Shorten the CTA to 3.2 s so it ends on the last word plus a beat.
- [ ] Shrink and lower the CTA spin (spin_zoom/center_y) so captions clear the model.
- [ ] Floor FX at -60 dB in the audit.

## v2–v3: deer 7/10, noob train 7/10

v2 changed the mixer (smooth envelope instead of side-chain), filled the frame, tightened the CTA and turned off the
auto whoosh. Its audit showed the hook music still competing (deer SNR p10 4.1 dB, 20% of voiced frames under 8 dB,
all inside the hook) and the new "Boom" lines dragging (train 3.0 s, deer 2.2 s). v3 deepened the dip to -15 dB and
used `[excited]` to speed up the train line (3.0 s → 1.7 s).

**v3 audit:** deer SNR median 32.8 / p10 8.1 dB, 9.9% under 8 dB, 0 SFX on words. Train SNR median 34.2 / p10
11.6 dB, 7.8% under 8 dB, 1 SFX on a word. Both master at -14 LUFS, true peak ≤ -1.5 dB.

**Still wrong**
1. **Train: boing on "noob!".** The boing (10.67 s) lands on the word that ends at 10.63 s, because the regenerated line starts 0.3 s later than the test take.
2. **Deer: coil too loud.** The coil at 6.67 s peaks 6 dB above the voice level in a gap (`gap_bursts` 6.8 s), so it's louder than the voice around it.
3. **Captions cover the model.** "HE'S REAL 3D" and "REAL 3D NOOB!" sit on the model's feet (spin centred at y 960/990), and "COMMENT 67 FOR" touches the antlers on the CTA.
4. **Arrow sliver.** A sliver of the creator's red arrow is still at the bottom of the train hook (crop too tall by about 30 px).
5. **Dark deer.** The brown deer on the near-black stage is low contrast (gamma 1.7).
6. **Credit badge on the game UI.** The deer's credit badge sits on top of the game's top-left UI icons. Small, but it adds clutter to the first frame.

### Fix list for v4
- [ ] Boing → 10.95 s. Coil gain 0.45 → 0.28 on both.
- [ ] Spin center_y 880–900 with spin_zoom ~0.82, so captions clear the feet (y≈1400) and the head (y≈330).
- [ ] Crop the train hook to 1000 px tall.
- [ ] Raise deer gamma to 2.1.

## v4–v5 (final): deer 8.5/10, noob train 8.5/10

v4 moved the spin (captions clear the feet and head), raised the deer's gamma, fixed the boing timing, lowered the coil
and tightened the train crop. v5 added `fx_gain` to morph.py, which halves the deer's baked lift-whoosh (the last
gap burst), and trimmed the train hook to 955 px so no part of the creator's arrow remains.

**Final audit:**

| reel | SNR median | SNR p10 | voiced < 8 dB | SFX on words | gap bursts | loudness |
|---|---|---|---|---|---|---|
| deer | 32.8 dB | 8.1 dB | 9.9% | 0 | 0 | -14.1 LUFS / -2.0 dBTP |
| train | 34.2 dB | 11.6 dB | 7.8% | 0 | 0 | -14.0 LUFS / -1.5 dBTP |

Every SFX now lands in a gap (uhh on the freeze, coil on the lift, ting on the spin, eat/boing as the punchline,
button on the CTA). The voice sits 30+ dB above the background on a typical word.

**What still keeps it from 10**
1. **Nobody has listened yet.** These are measurements, not a listen. Play both on a phone speaker and note any line that sounds off; v3 TTS can mispronounce.
2. **Deer hook music.** The p10 of 8.1 dB comes from the hook music under "Nobody told you…". If it still feels busy on a phone, set the deer clip `gain` 0.8 → 0.6.
3. **Dark deer.** The deer model's own texture is dark brown, so even at gamma 2.1 it reads darker than the noob.
4. **Credit badge.** On the deer it still sits over the game's top-left icons (small).
5. **Mid-spin beat.** The 1 s between the punchline and the CTA (deer 9.8–10.7 s, train 10.6–11.5 s) is carried by one SFX. A zoom punch on that beat would add energy.

---

# 09-vip-baddie

Brief from the user: **no voice in the first half.** The creator's own clip audio and an on-screen hook card ("STOLE A
BRAINROT. GOT CAGED.") carry 0–5.6 s, and the first spoken word comes at 7.8 s of 14.8 s. Model: the user's Vi3W
output, rendered at yaw 0 / elev 0, which matches the screenshot pose.

## v1: 6/10
1. **Line 1 drags.** "[excited] Wait. She's real 3D now!" runs 2.1 s because of the pause after "Wait."
2. **Line 2 crosses the CTA cut.** "From one screenshot." (10.3–11.67 s) runs past the cut at 11.38 s and lands on the button click (`sfx_on_words` 11.63).
3. **Aura on a word.** The aura sting at 10.4 s is inside line 2.
4. **CTA line ends on the last frame.** It ends at 14.43 s of 14.47 s, so there's no breath.
5. **Hook louder than the voice.** The hook plays at -13.2 LUFS against -14.7 for the voice sections, so the second half feels like a step down.

## v2–v3: 8/10
- Cut line 2; the CTA's "ONE SCREENSHOT → 3D" card already says it.
- Line 1 is now "[excited] Boom! She's real 3D now!" (7.8–9.8 s). CTA is 3.4 s, so its line ends 0.8 s before the end.
- Aura moved to 10.15 s, in the gap. Clip gain 0.8 → 0.55, so the hook and voice sections are within 0.1 LU (-13.4 vs -13.5).

**Still wrong:** the spun model reads dark on the black stage, and the aura sting is too loud (gap bursts at 10.4–10.6 s).

## v4–v5 (final): 8.5/10
- Aura gain 0.5 → 0.3.
- Gamma 1.5. At 2.0 her black pants turned royal blue and no longer matched the clip.

| reel | SNR median | SNR p10 | voiced < 8 dB | SFX on words | gap bursts | loudness |
|---|---|---|---|---|---|---|
| vip-baddie | 42.6 dB | 32.8 dB | 1.4% | 0 | 0.4–0.6 s (creator's own opening sound, nothing to fight) | -13.9 LUFS / -2.2 dBFS |

**What still keeps it from 10**
1. **Nothing explains the freeze-and-scan.** With no voice before the midpoint, 5.6–7.4 s has no caption saying "screenshot". The wireframe has to carry it.
2. **Hook card on the guard's face.** On frame 0 the card sits over the pink guard's head, and frame 0 is the thumbnail.
3. **Navy legs.** Even at gamma 1.5 the model's pants read navy against the clip's near-black.
4. **Nobody has listened yet.** Same as the others: these are measurements. Play it on a phone speaker.

## v6: user changes, 8.5/10
Brief: **no text on screen over the hook**, use "redhead baddie" (a known meme term), and end on a brainrot joke.
- Removed the hook card. Added `credit_from` (reel.yaml → `creditFrom` prop), so the @EazyEthan badge waits for the freeze at 5.68 s. The only text before then is the creator's own burned-in "BRO SAID NOT TODAY" caption.
- VO 1 is "[excited] Redhead baddie is real 3D now!" (7.67–9.8 s). The "..." version ran 3.2 s and put the aura sting on a word.
- CTA joke: "[excited] Steal from her? Minus a million aura!" (12.07–14.67 s). "…Comment baddie!" ran past the end, so the comment ask lives on the button ("Comment BADDIE 👇"). CTA is 3.8 s.
- Caption leads with "redhead baddie", and #redheadbaddie is added.

Audit: SNR median 43.7 / p10 33.3 dB, 1.1% of voiced frames under 8 dB, 0 SFX on words, 0 gap bursts, -14.0 LUFS / -2.5 dBFS.

---

# 10-14: noob series (2026-11-02)

Five 10M+ noob hooks → the existing Vi3W noob model (01-butter-noob renders, nothing new generated). The 09 rules
apply: no VO and no added text before the freeze, the credit appears at the freeze, and the CTA lands a joke.
Voices go through fal (premade Lily, Charlotte, Alice and River, plus Kawaii Aerisita).

| # | Hook | Views | Freeze |
|---|---|---|---|
| 10 visa | @GameAnimania deer-vs-noob PT2 | 240M | 10.0 s: smirking noob after paying with the NOOB ROBLOX Visa |
| 11 team | @GameAnimania "When a noob is looking for a team" | 45M | 5.25 s: noob begging the blue-haired player (0/4) |
| 12 shoe | @RoblotopiaRoblox wrong-shoe AR noob | 42M | 7.0 s: smug noob holding the wrong shoe |
| 13 tsunami | @ShapeDudesPlus sponge noob vs tsunami | 36M | 8.0 s: sponge noob next to the green sponge face |
| 14 iq | @PiAnimation01 different-IQ noobs vs train | 15M | 9.5 s: +911 IQ noob with the Nokia (box sized so the model's head sits on his) |

## v1: 7.5-8.5/10
1. **fal takes run long.** The fal lines last 3-3.8 s. In 10, line 1 crossed the CTA cut and the button landed on "noob!".
2. **Boing on a word.** The boing landed on a word in all five.
3. **Tsunami opens slow.** It opened on 1.5 s of a still noob in water.
4. **IQ caption.** It read "NINE HUNDRED ELEVEN".
5. **Visa CTA too long.** "Rich noob era. Who's next?" ran past the end.

## v2-v3 (shipped): 8.5/10
- spin_tail 96 → 132. Each cut now lands about 0.9 s after line 1, with the boing 0.2 s after its last word.
- The tsunami hook starts at source 1.5 s. The IQ caption shows "+911" (`say:` map, spoken "nine hundred eleven"). The visa CTA is "Rich noob era!".
- Audit, all five: 0 SFX on words, SNR p10 ≥ 29.7 dB, 0% of voiced frames under 8 dB. The only gap bursts are inside the hooks (the creators' own audio, nothing to fight).

**What still keeps it from 10**
1. **Credit badge clutter.** At the freeze the credit badge touches burned-in creator text (11's caption, 14's IQ label).
2. **Model mismatch.** The model doesn't match the clip noob's pose or style (the 10 smirk, the 14 car). The scan sells it, but it isn't a perfect overlay.
3. **CTA spin jump.** cta-full continues from the morph's last frame, not the cut, so the spin jumps 3-10 frames at the CTA cut.
4. **Nobody has listened.** As before, these are measurements; play them on a phone.
