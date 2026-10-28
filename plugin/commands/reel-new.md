---
description: Start a new ReelForge film - interview for the brief, then create the project folder
argument-hint: "[project-folder]"
---

Use the reelforge skill. Create a new film project at `$ARGUMENTS` (default: `projects/<slug>`).

1. Ask the user, in one round of questions, only for what's missing: product name and URL, how the app
   authenticates for capture (test-token script, storage state, or none), the ad idea, the story (free text or
   beats), the tagline, the setting and tone, the cuts (name, seconds, formats, hook seconds for social), music
   mood, BPM, providers, budgets, and trademark terms to avoid.
2. Call `project_init` (use `examples/vi3w` as the template if the user wants a starting point), then write
   `brief.yaml` with their answers. Keep `brand.json` and `assets/manifest.yaml` from the template, or ask for
   brand colours and fonts.
3. If the product has a UI to capture, run `ui_dump` on its main view and draft `capture.yaml` macros
   (sketch, edit, to3d, ...) from the visible roles and labels. Show them to the user.
4. Run `env_check` and report anything that's blocking.
5. Finish with the next step: `/reel-run <project>`.
