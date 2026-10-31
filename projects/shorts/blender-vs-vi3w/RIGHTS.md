# Rights: blender-vs-vi3w (DRAFT, do not post yet)

| Footage | Source | Creator | Used | Status |
|---|---|---|---|---|
| Blender armor timelapse | https://www.youtube.com/watch?v=lkLulcqkq7I | Smooth | 0:35-9:01, sped up ~72x, top half 0-9.4 s | **needs permission** |
| Sweaty gamer meme | https://www.youtube.com/watch?v=SK9YpwF7ImM | Just Want Life To Be Funny | 0-7 s with audio, bottom half | **needs permission** (real person on camera) |
| Monkey typing template | https://www.youtube.com/watch?v=sJ3tLYh_s40 | Bengali Trifling | 0.6-3.0 s with audio, bottom half | **needs permission** |
| Doodle Derby sketch, Vi3W output, gameplay | Input/DoodleDerby_trailer (1).mp4, ../doodle-derby/assets | Sagar Prema Rajan | reveal + 7 s gameplay | agreed to be featured (doodle-derby reel) |
| SFX (boom, tick, error, clang, scratch, charge, ting, drop) | assets/sfx | generated with ElevenLabs | throughout | ours |

When a creator says yes, save the screenshot in `assets/` and note it here. If anyone says no, swap that clip:
- Typing meme → a free-license clip (Pexels / Pixabay "cat keyboard", "angry typing").
- Blender timelapse → another timelapse from the shortlist (dollme qs8Zit436zQ, kaixiuuu FGr4EEBN06I).

Permission DM:
> Hey! Loved your [clip]. We make Vi3W (sketch → 3D). Could we use a few seconds of it, sped up, in a meme Short
> about how long modeling takes? You'd be credited on screen and in the caption.

## How assets/intro.mp4 was built
ffmpeg filter graph (run from this folder): armor `-ss 35 -t 506`, `setpts=/72.3`, crop 1241x1080+186, scaled to
1080x940 on top; sweaty scaled to 940 tall, centre-cropped to 1080 underneath; HOUR n PNGs every second at y=890.
Crash (7.0-9.4 s): armor frame 209 frozen, red-tinted, shaking crop + "BLENDER STOPPED RESPONDING"; monkey 0.6-3.0 s
underneath. Then 1 s black "...OR". Audio: clip audio + boom 0 s, tick 0.6 s, error 7.0 s, clang 7.15 s, scratch 9.35 s.
