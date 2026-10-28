---
description: Run the full ReelForge pipeline (S0-S10) on a project, answering decisions as director
argument-hint: "<project-folder> [from-stage] [to-stage]"
---

Use the reelforge skill. Project and optional stage range: `$ARGUMENTS`.

Drive the pipeline stage by stage with `run_stage`. Whenever a stage returns `awaiting_decision`, read the
request with `decision_pending` (and Read every image it lists), decide, `decision_submit`, and re-run the
stage. For D9 (fresh review) spawn a fresh subagent that sees only the evidence, rubric and hard rules.

Pause and ask the user before:
- the first paid generation (music, SFX, fal video), and state the estimated spend against the budget;
- S4 capture, if the app URL isn't reachable or the auth script fails;
- continuing the review loop when the fix plan says `needs_asset`.

After each stage, give a one-line update. At the end, report the masters, the spec table, the final score and
the remaining weaknesses, all taken from `render/out/spec-table.md` and `review/SCOREBOARD.md`.
