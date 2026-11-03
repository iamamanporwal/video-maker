# Roblox-dev series: hook → info → shared Vi3W outro

## The shared outro
`out/roblox-dev-outro-9x16.mp4` (8.8 s, 1080x1920, VO + SFX baked in, -14 LUFS). Remotion `Vi3WOutro`
(node/remotion/src/shorts/Vi3WOutro.tsx). Append it as the last segment of any reel.yaml:

```yaml
- {id: outro, type: clip, src: ../../roblox-dev-outro/out/roblox-dev-outro-9x16.mp4, fit: crop, gain: 1.0}
```

| time | VO (Laura, eleven_v3 via fal) | picture |
|---|---|---|
| 0.0-2.8 | "Need 3D models for your Roblox game?" | Vi3W noob on a baseplate, confused; "⏳ Blender: 6 hours… 💀" chip + bruh |
| 2.8-6.0 | "Just sketch it… and Vi3W makes it 3D!" | real Vi3W output: sketch → concept → 3D chest panels |
| 6.0-8.8 | "Try Vi3W.in!" | noob slams onto the baseplate, logo, Vi3W.in, "comment what we should 3D next 👇" |

Re-render: `npx remotion render src/shorts/index.ts Vi3WOutro <out> --public-dir ../../projects/shorts/roblox-dev-outro/public --gl angle`
(from node/remotion), then `media.master`.

## Hook research (2026-11-02): what stops a Roblox dev
Pulled ~1,000 Shorts from #robloxdev / #robloxstudio / #robloxscripting / dev searches, ranked by views.

| views | id | channel (subs) | format |
|---|---|---|---|
| 10.9M | F7y61toloEQ | Mehdiskan (24K) | "Developers keep taking it too far": frog-crossing game escalates, "one more feature" |
| 7.0M | 2YSbGRB4Yh0 | Cen (89K) | "beauty of roblox physics constraints 😱": 11 s raw Studio clip |
| 6.0M | EVI_4AmBEBo | Cen | "realistic beyblades in roblox 😱🤯" |
| 4.7M | oyn7eSq1CKw | Cen | "roblox dev teams be like": team-roles meme in Studio |
| 4.4M | O9Zp21FqXGg | Cen | "realistic rain in roblox" |
| 3.3M | Yyx62RDCCkA | Cen | "it wont let me swim bro 💔": bug-as-meme, 7 s |
| 2.3M | IqWOYhiYA0I | Cen | "my laser wont do damage bro 💔" |
| 2.0M | CSMGo6WtLl0 | Exfaultio (8K) | "the least depressed roblox dev": dev-life sadness meme |
| 1.9M | vkFl9epc-Ns | BloxDude (27K) | "I recreated Flappy Bird in Roblox" |
| 1.4M | gRAFdHx6kiQ | OldMario (1M) | "When scripting went wrong 💀" |
| 1.3M | ET8OMXz45Lc | Cracked Cannoli (615) | "In game vs Blender": split, game top / Blender bottom |
| 1.1M | Xj3po1BTack | MeltyWeather (345) | "roblox devs 0.0005 microseconds after they see an indie game" → meme face → their own tool in Studio → "AMAZING" |

What the winners share:
1. **Tiny channels hit millions.** Cen is 89K subs averaging 2-7M. MeltyWeather had 345 subs and got 1.1M while plugging its own module. The niche rewards format, not audience size.
2. **Raw Roblox Studio footage + a 3-6 word lowercase caption + 💔/😱/💀.** No VO in the hook, 7-15 s total.
3. **Four hook families that work:**
   - *Bug-as-meme:* "it wont let me swim bro 💔". Studio physics breaking, and every dev relates.
   - *Impossible realism:* "realistic X in roblox 🤯". Rain, water, lightning, beyblades.
   - *Dev-life POV:* "roblox dev teams be like", "the least depressed roblox dev". Pain only devs know (the modeler who never delivers, scope creep, 0 players).
   - *"I recreated X in Roblox"*, plus "X vs Blender" splits.
4. **MeltyWeather is our exact blueprint:** a meme caption makes the plug feel like a joke, and the tool appears as the punchline.

### Recommended first batch (hook 0-5 s → 20-35 s info → outro)
| # | hook (0-5 s, creator audio, no added text) | info middle |
|---|---|---|
| 1 | Cen-style physics bug ("it wont let me swim 💔") | why Roblox physics breaks + the one setting that fixes it |
| 2 | "roblox dev teams be like" | the 5 roles in a Roblox studio, and the modeler is always the bottleneck |
| 3 | "realistic rain in roblox 🤯" | how it's done: particles + sound + lighting, 3 steps |
| 4 | "When scripting went wrong 💀" (OldMario) | 3 Luau bugs every beginner hits |
| 5 | "In game vs Blender" split | low-poly budget: why Roblox models must stay under ~10k tris |

Borrowed hooks need the creator's OK (same rights routes as before: ask, Remix, or recreate the format with our own Studio footage).
Format recreation is the safest: hook families 1-3 can be rebuilt in Remotion low-poly 3D without filming anything.
