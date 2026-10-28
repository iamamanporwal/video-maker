---
description: Run one ReelForge review/fix iteration (evidence → self + fresh score → verified fix plan → re-render)
argument-hint: "<project-folder>"
---

Use the reelforge skill. Project: `$ARGUMENTS`.

Run `run_stage(project, "S9", force=true, options={"iterations": <current iteration + 1>})` and answer its
decisions:

- **D8 self-score:** Read every evidence image. Cite a timecode and format for each score.
- **D9 fresh review:** spawn a fresh general-purpose subagent. Give it only the request's image paths, the
  rubric and the hard rules, and ask it for JSON matching the schema. Submit its answer unchanged.
- **D10 fix plan:** first check each claim against the full-res claim stills, and skip any you can't
  verify. If a dimension has been stuck for 2 iterations, change the approach. If the ceiling is a missing
  asset, return `needs_asset` and tell the user exactly what to supply.

Report: score before and after, what changed, what was skipped and why, and the scoreboard row.
