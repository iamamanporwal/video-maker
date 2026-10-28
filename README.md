# ReelForge

An AI-directed product-film pipeline, built from [workflow.md](workflow.md). You give it an ad idea, a story, a
setting, a brand kit and labelled assets. It gives back spec-exact reels in every aspect ratio, plus the evidence
it used to judge them.

**Python does the operations. Claude only makes decisions** at eleven named points (D1–D11), and every
decision is schema-validated JSON.

```
brief.yaml + brand.json + assets/ ─► S0 init ─► S1 treatment* ─► S2 beats → timeline.json* ─► S3 storyboard
   ─► S4 real product capture (Playwright, D3/D4/D5*) ─► S5 music/SFX/b-roll (D6*) + beat-grid alignment
   ─► S6 takes + GLB prep ─► S7 compose (D7*) ─► S8 render + master + posters + SRT + spec verify
   ─► S9 review loop (D8 self + D9 fresh reviewer → D10 fix plan → re-render, revert on regressions) ─► S10 handover (D11*)
```

## Three faces, one core

| Face | Entry point | Use it for |
|---|---|---|
| CLI | `reelforge …` | Scripting and CI. With `ANTHROPIC_API_KEY` set, decisions call the Claude API directly. |
| MCP server | `reelforge-mcp` (32 ops tools) | Claude Code calls each deterministic op. No tool calls an LLM. |
| Claude Code plugin | `plugin/` (skill, MCP config, `/reel-new`, `/reel-run`, `/reel-review`, `/reel-render`) | Claude Code itself is the director. Stages pause on a decision; Claude answers with `decision_submit`. |
| Web UI | `reelforge ui` | Brief, brand kit with contrast checks, asset library with labels and auto-tags, run monitor and approval gates, review gallery with a self-vs-fresh diff, deliverables. |

**Decision backends.** `REELFORGE_DECIDER=api` calls Claude (`claude-opus-5-5` by default, override with
`REELFORGE_MODEL`). `REELFORGE_DECIDER=agent` writes `plan/decisions/<id>.request.json` and stops with exit
code 3; you answer with the MCP tool, `reelforge answer`, or the UI. The default is `api` when a key is set and
`agent` otherwise. Decisions are cached by input hash and logged to `logs/decisions.jsonl`.

## Quick start

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"
.venv/bin/reelforge setup                    # npm install node/remotion + node/capture
.venv/bin/reelforge env                      # node, ffmpeg, Chrome, port 3700, keys

# Offline smoke test: synthetic capture/music/GLB, no keys, no app
.venv/bin/reelforge demo projects/demo
.venv/bin/reelforge render projects/demo     # 4 masters, posters, SRT, spec-table.md
.venv/bin/reelforge ui --projects projects   # http://127.0.0.1:8765

# A real film
.venv/bin/reelforge init projects/my-launch --template examples/vi3w
#   edit brief.yaml, brand.json, assets/manifest.yaml, and capture.yaml (your app's flows as macros)
.venv/bin/reelforge run projects/my-launch   # resumable; re-running skips finished stages
.venv/bin/reelforge status projects/my-launch
.venv/bin/reelforge review projects/my-launch --iterations 2
```

Secrets go in `.env` (git-ignored): `ANTHROPIC_API_KEY`, `FAL_KEY`, `ELEVENLABS_API_KEY`. See `.env.example`.

### In Claude Code

```text
/plugin marketplace add /path/to/this/repo
/plugin install reelforge@reelforge-local
/reel-new projects/my-launch
/reel-run projects/my-launch
```

The skill ([plugin/skills/reelforge/SKILL.md](plugin/skills/reelforge/SKILL.md)) holds the judgement: decision
rules, hard rules, and the loop policy (lower score counts, verify claims on full-res stills, revert
regressions, change approach after 2 stuck iterations, ask for missing assets instead of looping). For D9 it
tells Claude to spawn a fresh subagent that sees only the evidence.

## Project layout

```
src/reelforge/
  schemas.py      every file + decision contract (Brief, Brand, Asset, Beat, Timeline, D1–D11 outputs)
  project.py      project folder, state.json, content hashes, logs, costs/budgets, per-stage git commits
  llm.py          Decider: the only LLM call site (api / agent backends, retries with validator errors)
  validate.py     beat grid, contiguity, hook, ≤4-word headlines, trademarks, monotone keys, `never` rules
  plan.py         beats → timeline (frames on the grid), JSON-pointer patches with scene ids
  stages.py       S0–S10
  review.py       evidence packs, rubric, score merge, stuck detection, SCOREBOARD.md
  ops/            media (master, verify, dark frames, sheets, SRT, conform), audio (kicks, tempo, phase,
                  drops, offset solving), capture (macro expansion, auth minting), takes (+ asset server),
                  glb (bounds, texture check, anchors), strokes (stroke designer), images (pixel match),
                  providers (fal queue, ElevenLabs SFX), remotion (brand.ts codegen, render, stills)
  mcp_server.py   MCP tools          ui/   FastAPI + single-page UI          demo.py   offline fixture
node/remotion/    data-driven compositor: Root registers <cut>-<format> + Poster-* from timeline.json
  src/components  Capture (PCHIP time-remap, focus-rect fitCrop, cursor + ripples + stroke replay from logs),
                  Headline (per-word blur-in), LimeLine, Tag, Captions, Finish (grain + vignette), Room, ChatPanel
  src/scenes      all 13 scene kinds          src/three   Car (feature-edge scan), Thrusters, SketchTunnel, CamRig
node/capture/     capture.mjs: Playwright + CDP screencast, humanised pointer, events + mouse logs
plugin/           Claude Code plugin          examples/vi3w/   brief, brand, manifest, capture.yaml
```

## What's verified

- `pytest` (13 tests) covers: the grid; the beat and timeline validators (off-grid, sums, hook, headline
  length, trademarks, sentinels); patching; score merging; music offset solving; GLB inspection and anchors;
  stroke determinism; macro substitution; SRT; the agent-mode decision round trip with rejection feedback;
  and budget enforcement.
- The offline demo renders all four masters (16:9, 9:16 and 4:5 hero, plus 9:16 social) through the real
  Remotion → master → verify chain. All spec checks pass at −14 LUFS, ≤ −1 dBTP, yuv420p/bt709 and AAC 48k.
- The S9 loop was exercised for two iterations with canned decisions: evidence pack, merge, claim stills,
  patch, debug stills, re-render, and the automatic revert when the score dropped.

## Not yet exercised against live services

- **S4 capture** against a real app. `capture.mjs` and the Vi3W `capture.yaml` macros are written to the
  spec, but selectors must be confirmed with `ui_dump` on your app.
- **fal and ElevenLabs** calls. The request shapes follow the spec. Cost estimates for budget enforcement
  are rough and set by `REELFORGE_EST_*`.
- **API-mode decisions.** These need `ANTHROPIC_API_KEY`. Agent mode was tested.
- **Bloom post-processing and `CameraMotionBlur`** aren't wired in yet. The 3D stage uses emissive
  thrusters, fog and grain.
