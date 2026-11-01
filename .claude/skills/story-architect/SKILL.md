---
name: story-architect
description: Shape a raw idea or rough script into a tight, emotional short-documentary / narrative VO script (45-90 s) with a cold open, a turn, a payoff and an earned brand bridge. Use when the user pastes a story idea, a draft narration, "make it a documentary", "tell the story of X", or wants a mini-doc / tribute / origin-story reel that ends on Vi3W.
---

# Story architect

You turn a raw idea into a script a director can shoot. Output: `script.md` (beats + VO lines + on-screen type) and `script.json` (VO lines only, in order) in the project folder.

## 1. Find the spine (before writing a word)

Fill the Pixar story spine in one line each. If a line is weak, the film is weak.

```
Once upon a time ...      (the world, the hero)
Every day ...             (the normal)
Until one day ...         (inciting blow, the lower the better)
Because of that ...       (the bet nobody believed in)
Because of that ...       (the cost, the doubt)
Until finally ...         (the payoff, the proof)
And ever since then ...   (what it changed; this is where the brand bridge lives)
```

Then name:
- **The emotional question** the viewer carries the whole way ("will the bet pay off?").
- **The one image** the viewer remembers (e.g. the colour flooding in).
- **The turn**: the moment that flips the meaning. Every short doc needs exactly one.

## 2. Structure for a 60-90 s vertical doc

| Beat | Share | Job |
|---|---|---|
| Cold open | 0-5 s | One loaded line or image. No logo, no context. Silence or near-silence counts. |
| Fall | ~15 % | The hero at the bottom. Concrete facts (year, place, number). |
| Bet | ~20 % | The unlikely choice. Name the doubters. |
| Grind | ~10 % | Time passing, cost rising (dates, money burned). |
| Payoff | ~15 % | The proof. Biggest visual and musical moment. |
| Echo | ~15 % | The quote or the lesson. Slow down. |
| Bridge | ~15 % | "And yet..." The problem that still exists today, then the brand as the next chapter. |
| Close | ~10 % | Callback to the cold open + CTA. |

The brand must arrive as a consequence of the story, never as a pivot ("Speaking of 3D..."). Test: delete the brand section. If the story still feels finished, the bridge is too weak. If the brand section reads like an ad, it's too strong.

## 3. Writing rules for VO

- **Short lines.** 6-14 words per VO line, one idea each. One line = one shot.
- **Concrete beats abstract.** "1985. He was fired from the company he started." beats "He faced setbacks."
- **Numbers and dates are hooks.** Use them, and verify them (section 5).
- **Rhythm:** after every two long lines, one short line ("Nobody laughed again."). Fragments are allowed.
- **Callback:** the last line echoes the first line or image.
- **Present tense for the payoff** gives immediacy ("And then... Toy Story.").
- **Write for the ear.** Read it aloud and kill any line you stumble on. No parentheses, no semicolons, no "i.e.".
- **Brand pronunciation:** Vi3W is spoken "View", written Vi3W. Site written "Vi3W.in", spoken "view dot in". Never say "free".
- Pacing budget: narration ≈ 2.4 words/s for documentary (slower than reels). 75 s ≈ 160-180 words, with room to breathe.

## 4. On-screen type

- Type carries what the voice doesn't say: year stamps, place names, chapter cards, numbers.
- Never duplicate the VO word for word, except a single hero quote.
- Max 6 words per card. One card per beat.
- First 4-5 s: no captions (house rule), let the image and the line land.

## 5. Fact-check (mandatory for real people and history)

- List every factual claim in the script, verify each one (WebSearch), and record the source in `script.md`.
- Fix overclaims ("the first 3D film" → "the first fully computer-animated feature film").
- Quotes must be real, verbatim and attributed. Note the source (publication, year).
- Dramatic licence is fine for feeling ("everyone laughed") but not for facts.

## 6. Hand-off

`script.md` contains:
1. The logline (one sentence)
2. The spine
3. The beat table: beat, time range, VO line(s), on-screen type, emotional temperature (1-10)
4. The fact list with sources
5. Notes for the director: the one image, the turn, where silence goes

Then load `film-director`.
