# Shot plan — gta6-billion (VO: Kokoro am_fenrir, out/words_am_fenrir.json, story ≈ 66 s + 7 s outro)

All new 3D: Blender EEVEE, 1080x1920, 30 fps, H.264 yuv420p crf 18, no audio → `public/3d/<name>.mp4`.
Follow the 3d-lookdev skill (saturated, textured, bloom, AgX Punchy, flicker-free, ≤ ~0.6 s/frame).
Cash = real-looking $100 bills: `public/img/bill_front.jpg` (public domain, 1200x505). Bills need slight bend/flutter, not flat cards.
Logos (SVG, import as curves or render to texture): `public/logos/Rockstar_Games_Logo.svg`, `Take-Two_Interactive_Logo.svg`;
GTA VI logo with alpha: `public/logos/gta6_logo.png`. Remotion adds all text/HUD — **no 3D text** except physical signage.
Frame 1 of every shot must already be moving (no empty/black lead-in). Leave the bottom ~380 px free of key action (platform UI).

| shot | owner | VO it sits under | len | brief |
|---|---|---|---|---|
| rocket | A | h1 "may have cost more than India's Moon landing. Thirteen times." | 4.8 s | THE HOOK. Low angle: a rocket built from stacked $100-bill bricks blasts off, exhaust is a storm of flying bills; big moon in a purple/orange Vice-sunset sky. Explosive from frame 1. Late beat (~3.2 s): camera tilts up/back to reveal 13 cash rockets lifting off in a row. |
| cashrain | A | h2 "over a billion dollars" + reused REVERSED under r1/r2 | 6.0 s | Camera falling/drifting through a dense storm of fluttering $100 bills, shallow DOF, warm key + gold bloom. Must also look good played backwards (money flying UP/back). |
| vault | A | h3 "Rockstar says that's wrong. And won't say what's right." + h4 "follow the money" | 4.6 s | Huge round steel vault door with the Rockstar logo embossed/painted in gold-orange; it SLAMS shut by ~1.5 s (dust, camera shake), hold; ~2.8 s a single bill slides out under the door and the camera follows it along the floor (a trail of bills leading off). |
| printer | A | p2 "a hundred grand a year… half a billion. Every. Single. Year." | 5.9 s | Money-printing press going full speed: rollers, bills shooting out onto a growing pile; a wall flip-calendar beside it flipping years (2018→2026, physical paper pages, no text needed beyond years). Take-Two logo plate on the machine. |
| beer | B | c2 "argued about how you buy a beer. Grab it from the fridge? Walk it to the counter? Pay?" | 5.8 s | Neon Vice-City convenience store. A beer bottle: fridge door swings open (~2.0 s), bottle floats/slides to the counter (~3.4 s), register drawer pops open (~4.8 s), bills fly into it. Can be "dev viewport" flavoured (grey props popping to textured) like gta6-by-hand. Simple stylised clerk/hands optional. |
| leak | B | l1 "leaked ninety clips… cleanup cost five million dollars." | 4.8 s | A pipe/dam in a dark server room bursts: a jet of $100 bills (mixed with glowing film-strip/video-thumbnail cards — blank, no real footage) sprays out; red alarm light sweeps. |
| sign | B | a1 "a Vice City sign on the Miami Heat's arena… $975,000. For one sign." | 7.7 s | Night, Miami-style arena dome by the water, palms, purple/pink sky. A giant pink-neon "WELCOME TO VICE CITY"-style rooftop sign flickers on (~1.0 s). A blimp drifts past. Camera slow orbit/push. Final ~2 s: push in close on the sign. |

Reused (gta6-by-hand/public/3d): office (p1), florida + citypull + props + trashcan (f1/f2), animate/rig (c1), lonely (b1).
Official trailer clips (muted, ≤2.5 s each): Vice City beach for f1 "Miami", end cards "COMING 2025" / "MAY 26 2026".
