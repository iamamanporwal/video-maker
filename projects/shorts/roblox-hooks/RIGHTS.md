# Rights: roblox-hooks series (DRAFT until every row says yes)

| Short | Hook clip | Creator | Status |
|---|---|---|---|
| 01 | https://www.youtube.com/shorts/CSMTg6j5y7k (0-7 s, original audio) | @Triangle1388 | **needs permission** → 01-butter-noob/assets/permission.md |
| 02 | https://www.youtube.com/shorts/bxubJrfQklM (0-6.9 s, original audio) | @Goldfishiess | **needs permission** → 02-brick-guy/assets/permission.md |
| 03 | https://www.youtube.com/shorts/JxpzriGYG2E (0-7 s, original audio) | @RespawnAnimation | **needs permission** → 03-forest-deer/assets/permission.md |
| 04 | https://www.youtube.com/shorts/7y3hdqAq-8g (played ~twice, original audio) | @ApexViness | **needs permission** → 04-straw-cups/assets/permission.md |
| 05 | https://www.youtube.com/shorts/y1twMWcn7RI (0-7 s, original audio) | @GameZyroii | **needs permission** → 05-gta-panda/assets/permission.md |
| 06 | https://www.youtube.com/shorts/_m5kohWrBmU (0-5.0 s, original audio) | @StumbleCrafts | owner says yes (2026-10-31); add screenshot → 06-deer-67/assets/permission.md |
| 07 | https://www.youtube.com/shorts/q8HPxi--ESM (0-5.8 s, original audio) | @RoxGamers9 | owner says yes (2026-10-31); add screenshot → 07-noob-train/assets/permission.md |
| 08 | https://www.youtube.com/shorts/12V86igxPYI (0-4.07 s, slow-mo, original audio) | @mr.gatatino | **needs permission** → 08-meowl/assets/permission.md |
| 09 | https://www.youtube.com/shorts/p5fkVqjaGHg (2.12-7.80 s, original audio) | @EazyEthan | **granted**: friend, blanket permission for all his videos (2026-11-01) → 09-vip-baddie/assets/permission.md |

Other assets:
- 3D models: Vi3W output of each `subject.png`, made by the channel owner (`assets/model.glb`, unedited; turntables
  rendered by src/reelforge/blender/turntable.py, lighting/camera only).
- `sfx/yt-*.mp3`: Roblox sounds pulled from YouTube for 06/07 (sources in sfx/yt/SOURCES.md), under the owner's Roblox allowance.
- 06/07 reuse the 03/01 Vi3W models and Blender renders (nothing new generated).
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
