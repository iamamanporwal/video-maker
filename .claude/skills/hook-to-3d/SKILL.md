---
name: hook-to-3d
description: Make a "viral hook → we turned it into 3D" short for Vi3W - borrow the attention of a trending gaming reel (with permission, via platform Remix, or by recreating its format), freeze on its subject, convert that subject to a 3D model in Vi3W, and pitch "image to 3D in under 30 seconds" with a comment-driven CTA. Use when the user shares a trending/viral reel or Short, or asks for this hook-then-3D format.
---

# Hook → 3D

Format (15-22 s): **trending hook (≤ 7 s) → freeze + "what if this was 3D?" → real Vi3W conversion → 3D turntable →
"image to 3D in under 30 s · make yours at Vi3W.in"**.

Tooling and spec: same builder as the game-reel skill. Read [../game-reel/reference.md](../game-reel/reference.md).
Third-party footage uses `type: source` segments plus a `source:` block; the builder refuses to render without it.

## 0. Find a hook (when the user didn't bring one)

Search for Shorts in the niche (game devs / 3D artists: games, creatures, vehicles, weapons, builds):

```bash
.venv/bin/python -m reelforge.shorts find "<niche query>" --top 10   # ≤ 90 s, ranked by views, + views_per_day
.venv/bin/python -m reelforge.shorts find "#gta5mods" --top 10       # hashtag Shorts tab: Shorts only, far better
```

Keyword search often returns long videos for big games (GTA gave none); prefer 2-4 hashtags of the niche. Popular
mod niches are flooded with licensed IP (Marvel, Spider-Man, Disney, Mario, real car brands): skip those titles and
check the contact sheet too, since titles lie (a "Super Cow" short was Simba and Venom).

The `youtube` MCP (`search_videos`, `get_channel_videos sort=popular`, `get_comments`) does the same when it's
loaded; use it to dig into a channel's other hits. Shortlist 3 for the user with views, views/day and the subject
you'd 3D. Prefer **high views/day** (still trending) over old evergreen hits, and original subjects over trademarked
ones (§2). The user picks; then do §1 before anything is downloaded into the reel.

To study a candidate (decide the hook window and subject frame), download a reference copy into `ref/`, which is
for analysis only and never rendered:

```bash
.venv/bin/python -m reelforge.shorts fetch <url> projects/shorts/<title>/ref/source.mp4 --to 10
.venv/bin/python -m reelforge.shorts sheet projects/shorts/<title>/ref/source.mp4 projects/shorts/<title>/ref/sheet.jpg --fps 2
```

Or, with the `claudetube` MCP loaded: `process_video_tool` → `get_scenes` / `find_moments_tool("<subject> clearly
visible")` → `get_hq_frames` at the best moment. Instagram / TikTok links need browser cookies
(`yt-dlp --cookies-from-browser chrome`).

## 1. Pick the rights route first (ask the user if it isn't clear)

Never download and repost someone's clip without one of these. Reposted clips get Content ID claims, are demoted
by Instagram's originality ranking, and copyright strikes can take down the Vi3W channel.

| `rights` | When | What gets built |
|---|---|---|
| `permission` | The creator said yes (DM/email). Save a screenshot as `source.proof`. | Full reel with their first 5-7 s as the hook, credited on screen and in the caption. Only after the yes: `fetch <url> assets/source.mp4 --to 8`. |
| `remix` | No permission, but the platform allows remixing (YouTube Shorts "Remix → Use this segment", Instagram Remix). | Builder drops `source` segments and renders `<title>-remix-9x16.mp4`: the "after" half only. The user attaches it to the original **inside the app**, so the platform supplies and credits the hook. The hook title is skipped. Start the VO with a bridge ("Okay, but what if that was 3D?"). |
| `recreate` | Copy the trending *format*, not the footage. | The user films or captures their own version (or uses footage from a game a creator agreed to feature). |
| `own` | The user's own video. | Full reel. |

Permission DM template to offer the user:
> Hey @handle, loved your [clip]! We make Vi3W (sketch/image → 3D in 3 clicks). Could we feature the first few
> seconds in a Short where we turn your [subject] into a 3D model? You'd be credited on screen and in the caption,
> and we'll send you the model.

## 2. Choose the subject

- Read a contact sheet of the source (`sheet`). Pick a frame where the subject (character, vehicle, creature, prop)
  is large, unoccluded and side- or 3/4-on. Extract it: `frame <video> <sec> assets/subject.png --crop x,y,w,h`.
- Skip subjects that are trademarked characters (Nintendo, Pokémon, Marvel…) or real people without their consent.
  Original indie characters, objects and creatures are ideal.

## 3. The real Vi3W step (the user does this, you direct it)

Ask the user to run `assets/subject.png` through Vi3W while screen-recording, then export the GLB. Put the
recording in `assets/vi3w.mov` and the model in `assets/model.glb`. Time it: if it really took under 30 s, say so
(`timer: "24 s · real time"`). If it took longer, don't claim "under 30 seconds". Use the real number or drop the timer.
Nothing in the 3D card may be generated or retouched.

## 4. Spec

```yaml
title: <slug>
source: { url: <link>, creator: "@handle", rights: permission, proof: assets/permission.png }
hook: { text: "Wait… what if this was *3D*?", seconds: 2.5 }
credit: "🎥 Clip: @handle"
segments:
  - { id: hook, type: source, src: assets/source.mp4, in: 0, out: 6.0, fit: crop, gain: 0.8 }
  - { id: reveal, type: reveal, before: assets/subject.png, after: assets/vi3w.mov, seconds: 6, timer: "24 s · real time",
      label: "Real Vi3W output" }
  - { id: spin, type: cta, seconds: 3.5, glb: assets/model.glb, line: "Image → 3D in *under 30 s*" }
vo:
  - { at: reveal, offset: 0.2, text: "Okay, but what if that was a 3D model? One screenshot into Vi3W…" }
  - { at: spin, offset: 0.1, text: "…and it's game-ready. Under 30 seconds. [excited] What should we 3D next? Comment it!" }
```

The source hook keeps its own audio (`gain`); our VO starts at the freeze. For `remix`, keep the same file: the
builder removes the source segment, the hook title and VO lines anchored to it.

## 5. Render, check, hand over

`build <dir> --no-render --stills …` → Read → `build <dir>` → Read `out/contact.jpg`. Hand over the mp4, poster,
caption (credit the creator first line), and for `remix` the exact in-app steps:
YouTube: open the original Short → Remix → Use this segment → trim to the hook → add our clip.
Instagram: on the original reel → ⋯ → Remix → "Add to end" → pick our clip.
Music: same rule as game-reel (add trending audio in-app, ~20 %).
