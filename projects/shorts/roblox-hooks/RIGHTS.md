# Rights: roblox-hooks series (DRAFT until every row says yes)

| Short | Hook clip | Creator | Status |
|---|---|---|---|
| 01 | https://www.youtube.com/shorts/CSMTg6j5y7k (0-7 s, original audio) | @Triangle1388 | **needs permission** → 01-butter-noob/assets/permission.md |
| 02 | https://www.youtube.com/shorts/bxubJrfQklM (0-6.9 s, original audio) | @Goldfishiess | **needs permission** → 02-brick-guy/assets/permission.md |
| 03 | https://www.youtube.com/shorts/JxpzriGYG2E (0-7 s, original audio) | @RespawnAnimation | **needs permission** → 03-forest-deer/assets/permission.md |
| 04 | https://www.youtube.com/shorts/7y3hdqAq-8g (played ~twice, original audio) | @ApexViness | **needs permission** → 04-straw-cups/assets/permission.md |
| 05 | https://www.youtube.com/shorts/y1twMWcn7RI (0-7 s, original audio) | @GameZyroii | **needs permission** → 05-gta-panda/assets/permission.md |

Other assets:
- 3D models: Vi3W output of each `subject.png`, made by the channel owner (`assets/model.glb`, unedited; turntables
  rendered by src/reelforge/blender/turntable.py, lighting/camera only).
- `sfx/uhh.mp3`: generated stand-in. To use the real Roblox sound, save the written Roblox allowance as
  `roblox-permission.md` here (it must cover use on YouTube/Instagram), drop the file over `sfx/uhh.mp3` and rebuild.
- All other SFX: generated with ElevenLabs. Voices: ElevenLabs premade voices (one per short).
- Original hook audio: kept; if a creator's permission excludes the music, set that hook's `gain: 0` and add
  trending audio in-app.

When a yes comes in: save the screenshot/answer in that folder's `assets/permission.md`, remove `-DRAFT` from its
`title:` and rebuild: `.venv/bin/python -m reelforge.shorts build projects/shorts/roblox-hooks/<folder>`.

Permission DM:
> Hey! Loved your Short [link]. We make Vi3W (screenshot → 3D model). Could we use the first ~7 seconds of it in a
> Short where we turn [the subject] into a real 3D model? You'd be credited on screen and in the caption, and we'll
> send you the 3D model.
