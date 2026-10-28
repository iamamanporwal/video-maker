---
description: Render, master, poster, SRT and spec-verify a ReelForge project's masters
argument-hint: "<project-folder> [cut] [format]"
---

Use the reelforge skill. Arguments: `$ARGUMENTS`.

Call `render(project, cuts, formats)`. If it fails, read the spec table it returns, find the cause (usually
in timeline data, e.g. an unintended dark frame or a duration mismatch), fix it with `write_timeline`, and
render again. Don't loosen a check. When it passes, show the spec table and list the files in `render/out/`.
