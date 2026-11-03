# Roblox-dev facts: 10 s informative hook → Vi3W

Format: 0-10 s a jaw-drop **verified** Roblox-dev fact over cleared footage → 10-16 s bridge that turns the
fact into "3D models are the bottleneck" → Vi3W makes one live → shared `Vi3WOutro` (8.8 s). Target 28-32 s.

## Research (2026-11-02)
- Informative dev Shorts are a thin genre on their own (RoDev tops out ~1.1M; "Do Roblox devs make money?" 95K).
  The views are in **money / record stories**: Starter Story "24h with Roblox Millionaires" 4.4M, Joe Bartolozzi
  "Life of a Roblox Millionaire" 3.7M, Skatebtw "Richest Dev" 1.5M, RoDev "6 devs make Grow a Garden" 6.5M.
  So lead with a number that sounds impossible, then pay it off.
- Footage that's already cleared: @EazyEthan (friend, blanket OK) has 9-26M-view Steal a Brainrot Shorts
  (p5fkVqjaGHg used; Fb_0KkyDBvg 18M, 3huHG0Az0Yc 17M, Yy_946mRoZs 9.1M unused).
- YouTube rate-limited this IP mid-research (yt-dlp + transcripts). Retry downloads in a few hours.

## Verified facts (source → exact wording we may use)
| fact | source | safe wording |
|---|---|---|
| Steal a Brainrot: 25,868,678 concurrent players, 11 Oct 2025 | Guinness World Records | "25.8 million people playing at the same time" |
| Fortnite's old record 15.3M | PocketGamer.biz, Wikipedia | "Fortnite's record was 15.3 million" |
| Steal a Brainrot launched 16 May 2025, dev SpyderSammy, owned by DoBig | Wikipedia | "made by one dev called Sammy" (he's the credited creator) |
| Grow a Garden: first version built in a few days by a 16-year-old | AP / Fortune 2025-07-30 | "a 16-year-old built it in a few days" |
| Grow a Garden 21.6M CCU, June 2025 | AP | "21.6 million players at once" |
| Grow a Garden: $12M of in-game purchases in May 2025 | Ctech (Calcalist) | "players spent $12 million in one month" (not "he made") |
| Creators earned $1.503B in 2025 ($922.8M in 2024) | Roblox 10-K FY2025 | "Roblox paid creators $1.5 billion last year" |
| Top 10 devs averaged $33.9M, top 1,000 averaged $820K (2024, Robux spent) | Roblox Economic Impact Report 2025-09 | "the top 10 Roblox devs averaged $33.9 million" |
| Median DevEx creator: $1,440 (12 mo to Jun 2025) | Roblox newsroom 2025-12 | "the median dev made $1,440" |

## 01 - brainrot-record (HERO, footage cleared)
| t | picture | VO (Laura) |
|---|---|---|
| 0.0-3.5 | EazyEthan's funniest Steal a Brainrot beat, full screen, game audio up | "This Roblox game broke Fortnite's all-time record." |
| 3.5-7.0 | counter slams 15.3M (Fortnite, grey bar) → 25,868,678 (green), Guinness badge | "Twenty-five point eight million people. Playing at the same time." |
| 7.0-10.0 | quick cuts of brainrots being stolen | "And the whole game is... stealing meme characters." 💀 |
| 10-16 | every brainrot freezes, outlines turn to wireframe, "3D MODEL" tags pop on each | "Every one of those brainrots is a 3D model. That's the part that takes devs weeks." |
| 16-22 | real Vi3W: our own original brainrot sketch → concept → 3D, spins on a baseplate | "So we sketched a new one... and Vi3W made it 3D." |
| 22-30.8 | shared Vi3WOutro | (baked in) |
Caption: "the game is literally stealing memes 💀 and it beat fortnite" + comment bait "name our brainrot 👇".

## 02 - garden-16yo
Hook: "A 16-year-old built this Roblox game in a few days. It beat Fortnite. Players spent 12 million dollars on it in one month."
Bridge: "Every seed, fruit and pet in it is a 3D model..." → Vi3W makes an original fruit/pet.
Footage: needs a source (ask EazyEthan if he has Grow a Garden clips) or our Remotion low-poly recreation.

## 03 - median-dev (twist, fully owned visuals)
Hook: "Roblox paid creators 1.5 billion dollars last year. The top 10 devs averaged 33.9 million each... the median dev? 1,440 dollars."
Bridge: "The difference is how fast you ship. And 3D models are where most devs get stuck." → Vi3W.
Visuals: Remotion data graphics (RobloxExplainer style), no third-party footage.

## Rule change for this series (flag)
Our default is no VO / no text in the first 4-5 s (vo-silent-first-half). An informative hook can't work silently,
so this series has VO + captions from 0 s, with EazyEthan's game audio ducked under the voice.

## Needed from the user
1. Make the Vi3W model of our original brainrot from `assets/brainrot-sketch.png` (export GLB + screen-record the flow).
2. OK the VO-from-0 s exception.

## Built 2026-11-02: 02-04 (`build2.py <id>`, VO in `vo.py <id>` → vo-<id>.json)
Reveal for these three = a real Vi3W screen recording (`DevFact` reveal.demo): sketch, then a hard cut to the 3D model.
| short | hook footage | fact wording used | reveal |
|---|---|---|---|
| 02 median-dev | @EazyEthan Shorts Fb_0KkyDBvg + 3huHG0Az0Yc | "over one billion dollars in a single year" (DevEx, 12 mo to Jun 2025; we don't use $1.5B, which only the 10-K gives); top 10 avg $33.9M (2024); median $1,440 | Input/demo1.mp4 founder jet |
| 03 brookhaven | @EazyEthan long-form C5hwO43G_aw + unZxKg5Pe4M (ref/bh) | Guinness 37.2B visits as of 29 Sep 2023; "over four visits for every human on Earth" (~8B) | Input/demo3.mp4 car |
| 04 garden-16yo | AI illustrations (turbo-mlx, free), labelled "illustration"; no Grow a Garden footage is cleared | AP: 16-year-old, ~3 days, 21.6M at once vs Fortnite 15.3M; Calcalist: $12M spent in one month | Input/Demo 1.mp4 chest |
