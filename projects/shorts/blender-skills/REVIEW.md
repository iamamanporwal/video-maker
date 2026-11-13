# blender-skills v2 QC (2026-11-10): funny rewrite + visual loops

User feedback on v1: "horror hallway is really bad, not watchable, add jokes + cuss words, run the self-improvement loop
3+ times to a 10/10 visual language score." v2 = 59.5 s, 1080x1920, -14.1 LUFS, no unintended black/frozen spans.

## Visual-language loops (stills/contact sheets each pass)
| Loop | Score | Main fixes |
|---|---|---|
| 1 | 6.0 | hallway rebuilt (hospital wing, drop ceiling, wet floor, gurney, EXIT, doors); guy invisible (posing broke rig: lying flat); flicker blacked out frames; gurney blocked zoom; blocky fog; donut gag unreadable |
| 2 | 7.5 | rest-pose T-pose guy; flicker floor; brighter panels + fill; door light x3.5; vol tiles 2; crate smaller for donut splat |
| 3 | 8.8 | room behind door was a solid box (blocked light + guy) → open room; black puddles removed; hero cam; door opened wide; guy under lit panel |
| 4 | 9.0 | jumpscare showed his back + fog hid his head → face camera on the jump frame, fog keyed to 0.004, light volume_factor 0, underlit grin; stab SFX fixed |
| 5 | 9.5 | stamp clipped → fits; caption vs last pipeline node; horror mushroom lifted |

Remaining honest gaps: narration is local Chatterbox (not checked by ear); the guy is a static T-pose (no walk anim).
Captions are lightly censored (f*cking, sh*t, a**hole); audio is uncensored.
