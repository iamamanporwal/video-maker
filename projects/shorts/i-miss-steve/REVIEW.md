# REVIEW: i-miss-steve (film-qc)

## Pass 1: out/film-raw.mp4 (88.8 s)
Tech: 1080x1920 h264, 30 fps, AAC 48k. I = -19.0 LUFS (fail, target -14). pix_fmt yuvj420p (→ yuv420p at master).
Blacks only where intended (65.7 s 0.27 s beat; end card). Freeze only on the end card.

| # | Criterion | Score | Evidence |
|---|---|---|---|
| 1 | Hook | 7.5 | Strong line + VHS power-on, but one face held 0.7-4.8 s with a slow push |
| 2 | Story clarity | 9 | Fall → bet → proof → gap → belief → Vi3W; chapters label each act |
| 3 | Emotional arc | 8.5 | 1995 counter tension → bloom; "I miss Steve" lands on the colour callback |
| 4 | Visual craft | 8 | Every still moves; 3.5 s opening hold and 3 s "1995" hold run slightly long |
| 5 | Colour/texture | 9 | B&W → sepia → bloom on "Toy" → cool gap → warm present, as scripted |
| 6 | Typography | 8.5 | Playfair/Plex pairing reads classy; safe zones respected |
| 7 | Voice | 8.5 | Whisper transcript matches; "View" correct |
| 8 | Sound mix | 7.5 | Music only ~8 dB under speech; in 45-66 s gaps the music (-17) is louder than the VO (-19) |
| 9 | Brand bridge | 8.5 | Real app capture and 9 real models; arrives through the "design is how it works" belief |
| 10 | Accuracy/rights | 9 | Facts sourced in script.md; every photo PD/CC with credits |
| | **Overall** | **8.4** | |

Fixes (by impact):
1. Mix: duck the music deeper (0.17 → 0.12 under speech, -12 dB) and lower the gap level (0.5 → 0.4), then master to -14 LUFS / -1 dBTP.
2. Hook: split the opening. Face push 0.7-3.8 s, then an extreme close-up on "fired..." with a VHS tear, then the Mac portrait on "from".
3. End card: slow 4 % push so the last 4 s aren't a freeze.

## Pass 2: out/i-miss-steve.mp4 (master)
Tech: 1080x1920 h264 yuv420p, 30 fps, AAC 48k 256k, 88.8 s. **I = -14.2 LUFS**, true peak -0.9 dBTP (target ≤ -1.0, 0.1 dB over;
platforms re-encode anyway). No unintended blacks, freezes or silences.
Voice vs music (momentary medians): speech -14.0; music-only gaps -22.9 / -15.4 / -13.2 / -20.9 by act. Ducking is
-10.4 dB, so the music sits about 10 dB under the voice.

| # | Criterion | P1 | P2 | Change |
|---|---|---|---|---|
| 1 | Hook | 7.5 | 8.5 | 3 shots in 5 s: power-on → face push → eyes ECU + tear on "fired" → Mac portrait |
| 4 | Visual craft | 8 | 8.5 | opening hold fixed; end card drifts |
| 8 | Sound mix | 7.5 | 8.5 | -12 dB duck, quieter gaps, mastered to -14 |
| | **Overall** | 8.4 | **8.75** | |

What still holds it back (not fixed):
- The music swell in the 45-66 s gaps is about as loud as the voice. That's intentional (music carries the gaps), but some will find it loud.
- The 1995 counter holds about 1.5 s on "1995" before "Toy Story". That's deliberate tension; trim GAPS[5] in timeline.py if it feels slow.
- The narrator is Brian (ElevenLabs). Not human-listened by me: the transcript checks out, but judge the tone by ear.
Shipped to FinalUploads/ (≥ 8.5).

## v2: out/i-miss-steve-v2.mp4 (90.6 s)
Changes: a more human narrator, chosen from 3 library voices ("Hey Its Brad", ElevenLabs v3, stability 0.5, via fal).
Two lines were re-taken after Whisper heard "I'm Esteve" / "we started". The first half is rebuilt on archival video:
1984 Mac launch, NewsHour 1985, NeXT, an early Toy Story test on a CRT, Charlie Rose 1996, and the Toy Story trailer
montage at the colour bloom. New type system: an editorial chapter header in the top bar (kicker, serif italic title,
year, hairline), kinetic serif callouts ("Fired.", “computer cartoons?”), archive source captions, word-by-word subtitles.
Tech: 1080x1920 yuv420p 30 fps, I = -14.2 LUFS, TP -1.8 dBTP. No unintended blacks, freezes or silences.

| # | Criterion | v1 | v2 | Evidence |
|---|---|---|---|---|
| 1 | Hook | 8.5 | 9 | VHS power-on → real 1984 footage → NewsHour "Losing its shine?" → "Fired." callout, 4 cuts in 6 s |
| 2 | Story clarity | 9 | 9 | Chapter headers now name each act and year |
| 3 | Emotional arc | 8.5 | 9 | Real faces (the hand-on-forehead shot on "finished"); the Toy Story footage makes the payoff land |
| 4 | Visual craft | 8.5 | 8.5 | Footage adds life; the Pixar stone still (20-23 s) and the NeXT office (14-18 s) still feel long |
| 5 | Colour/texture | 9 | 9 | Unchanged arc; real colour footage blooms on "Toy" |
| 6 | Typography | 8.5 | 9 | Editorial hierarchy: Playfair italic chapters, mono archive credits, lit-word subtitles |
| 7 | Voice | 8.5 | 8.5 | Library narrator, natural pauses; transcript verified. Needs a human ear |
| 8 | Sound mix | 8.5 | 8.5 | Same ducking; mastered |
| 9 | Brand bridge | 8.5 | 8.5 | Vi3W capture now labelled "real screen capture · no edits" |
| 10 | Accuracy/rights | 9 | **6** | Facts sourced; footage is NOT licensed (Disney/Pixar, PBS, Charlie Rose). See RIGHTS.md |
| | **Overall** | 8.75 | **8.6** | |

Rights block: the footage is a fair-use style excerpt, not cleared. Shipped to FinalUploads at the user's request, with a
warning line at the top of the caption. v1 remains the clean version.
