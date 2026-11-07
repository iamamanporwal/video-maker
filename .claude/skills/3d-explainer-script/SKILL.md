---
name: 3d-explainer-script
description: Write the VO script for a Zack D. Films / LowPolyShorts-style "What if / Why you shouldn't" 3D explainer short (30-45 s, ~110-130 words) using the measured beat formula - "If you X" hook, the wrong assumption, "But" turn, mechanism with a visual analogy, consequence, and a deadpan twist - plus a word-by-word visual note for every phrase so the shot list falls out of the script. Use before 3d-director/3d-shot-grammar, when the user gives a topic like "what if bullets were ice", "why you shouldn't X", or asks for a 3D explainer idea or script.
---

# 3D explainer script

Measured from reference Shorts (Nov 2026). Treat these numbers as the target.

| Ref | Views | Length | Words | Pace |
|---|---|---|---|---|
| Zack D. "What If Bullets Were Made Of Ice?" | 8.1M | 41 s | ~115 | 3.0 w/s |
| LPS "Why You Shouldn't Point Lasers At Planes" | 24M | 37 s | ~105 | 3.0 w/s |
| LPS "You've Never Touched Anything" | 53M | 39 s | ~120 | 3.2 w/s |

The VO starts at **0.00 s**, with no intro, no music sting and no title card. The first spoken words are the premise.
(This applies only to 3D explainers. Clip-based shorts keep the (memory: vo-silent-first-half) rule; ask the user before
applying that rule here.)

## The beat formula (every reference follows it)

| Beat | Time | Words | Pattern | Zack (ice bullet) | LPS (lasers) |
|---|---|---|---|---|---|
| 1 Premise | 0-3 s | 8-12 | "If you [do vivid physical thing]..." | "If you load a bullet made of ice into a gun, then pull the trigger" | "If you point a laser at a plane" |
| 2 Wrong belief | 3-10 s | 15-20 | "most people assume / you might think" + the tempting payoff | "...it could hit someone then melt before investigators ever find it, making it the perfect murder weapon" | "...you're just hitting it with a tiny harmless dot of light" |
| 3 Turn | ~10 s | 1-4 | "But" | "But the moment the gun fires" | "But if you do this to the wrong aircraft" |
| 4 Mechanism | 10-28 s | 40-60 | 2-3 cause→effect steps. Each step is one picture. Use "See / You see" to signal the science. Use an everyday analogy. | explosion → pressure → ice cracks → fragile chunk → inaccurate | plexiglass "acts like one of those [hi-vis] jackets" → scratches scatter → flash |
| 5 Consequence | 28-36 s | 15-25 | Concrete, visual, a little dark | "they would still find the gunshot wound and plenty of other evidence tying you to the crime" | "This blinds the pilot's retina" |
| 6 Twist / button | last 2-4 s | 5-12 | Deadpan joke, absurd escalation or meme line. Deliver it flat; never explain it. | (button = arrest tableau) | "making the plane look for a parking spot" |

LPS adds a mid-video meme aside ("You've never touched grass and she technically didn't cheat on you"). Use one
per script at most, around 70 % of the way through, where retention dips.

## Writing rules
- **Second person, present tense.** "You" is in the frame, so the viewer is the character.
- **Every phrase must be drawable.** Write a visual note next to each 2-5-word phrase (see the output format). If a
  phrase can't be drawn as one shot, rewrite it. Abstract words ("significant", "factors") are banned.
- **One noun per caption chunk.** Captions show 1-3 words (Zack) or a 4-6-word phrase (LPS). Put the hero noun at
  the end of a chunk so the cut lands on it: "made of ice", "into a gun", "murder weapon".
- **Short sentences around the "But".** Long run-ons are fine in the mechanism; the turn must be crisp.
- **Numbers as images**: "1 in 1,000,000,000,000..." scrolled across the screen beats saying "very unlikely".
- **No hedging, no sources read out loud.** Verify facts yourself (WebSearch) and keep the claim defensible, but
  say it with full confidence.
- **Ending**: land on the image, not a summary. No "follow for more" in the VO. The Vi3W bridge, if any, comes after
  the button, as the shared outro ((memory: vi3w-workflow-outro)).

## Topic picker (what goes viral in this format)
The best titles are one of these shapes, ranked by reference views:
1. **Shocking universal truth**: "You've Never Touched Anything" 53M, "The Eye Socket Problem" 21M.
2. **Dangerous curiosity**: "Why You Shouldn't Point Lasers At Planes" 24M, "Why Stopping Time Is A Bad Idea" 13M.
3. **Weird real case**: "She Is Immortal (kinda)" 22M, "Ancient 30,000 Year Old Virus" 23M.
4. **What-if physics**: "What If Bullets Were Made Of Ice?" 8M, "Why Making The Ocean Soda Is Bad" 2.8M.

Title: 3-7 words with no clickbait punctuation except "?" on a what-if. For Vi3W fit, prefer topics about
games, 3D, game dev, animation and tech (see (memory: game-dev-facts-series), (memory: roblox-dev-facts-series)), but don't force it.

## Output format (hand this to 3d-shot-grammar)
Write `projects/shorts/<id>/SCRIPT.md`:
```
TITLE: Why You Shouldn't ...
VO (for ElevenLabs, one paragraph, ~115 words)

| # | chunk (caption) | beat | visual note (one shot) |
|---|-----------------|------|-------------------------|
| 1 | If you load     | 1    | MACRO: fingers push ice round into revolver cylinder |
| 2 | a bullet        | 1    | INSERT: cylinder spins shut |
| 3 | made of ice     | 1    | MACRO: frosty bullet tip, condensation, slow push-in |
...
```
Aim for 22-35 rows for 40 s. The rows become cuts.

Voice: Brian (ElevenLabs premade, direct API) for the Zack style: neutral, fast, slightly amused. For LPS style, use
a flatter, more deadpan read; set stability ~0.6 and speed ~1.08. Respect (memory: elevenlabs-free-tier) and (memory: no-fal-for-now).
