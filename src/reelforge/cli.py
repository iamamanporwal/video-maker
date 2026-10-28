"""reelforge CLI: scripting and CI face of the pipeline."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import stages
from .llm import Decider, DecisionPending, pending_decisions, submit_decision
from .ops import env as envops
from .project import Project

EXIT_PENDING = 3


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _pending(e: DecisionPending, p: Project) -> int:
    req = json.loads(e.request_path.read_text())
    print(f"\n⏸  Decision {e.decision_id} needs an answer (agent mode).", file=sys.stderr)
    print(f"   request : {e.request_path}", file=sys.stderr)
    print(f"   answer  : write JSON matching output_schema to {e.request_path.with_name(e.decision_id + '.response.json')}",
          file=sys.stderr)
    print("             or `reelforge answer <project> <id> <file.json>`, or MCP tool decision_submit; then re-run.",
          file=sys.stderr)
    print(f"   task    : {req['task'][:300]}", file=sys.stderr)
    return EXIT_PENDING


def cmd_setup(a) -> int:
    from .ops.remotion import npm_install

    for name in ("remotion", "capture"):
        print(f"npm install node/{name} ...")
        npm_install(name)
    print("done")
    return 0


def cmd_init(a) -> int:
    src = Path(a.template) if a.template else None
    p = Project.create(a.project, brief=src / "brief.yaml" if src else None, brand=src / "brand.json" if src else None,
                       manifest=src / "assets/manifest.yaml" if src else None)
    if src:
        for extra in ("capture.yaml",):
            if (src / extra).exists() and not p.path(extra).exists():
                shutil.copy(src / extra, p.path(extra))
        if (src / "assets").is_dir():
            for f in (src / "assets").rglob("*"):
                if f.is_file() and f.name != "manifest.yaml":
                    dst = p.path("assets", f.relative_to(src / "assets"))
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        shutil.copy(f, dst)
    if not p.path("brief.yaml").exists():
        print("Created project folder. Write brief.yaml (see examples/vi3w/brief.yaml) or use /reel-new.")
    p.commit("S0 project created")
    print(f"project ready: {p.root}")
    return 0


def cmd_env(a) -> int:
    envops.load_env(Path(a.project) if a.project else None)
    url = Project.open(a.project).brief.product.url if a.project else None
    res = envops.env_check(url)
    for k, v in res["checks"].items():
        mark = "✓" if v["ok"] else ("✗" if v["required"] else "·")
        print(f" {mark} {k:20s} {v['detail']}")
    print("OK" if res["ok"] else "NOT READY")
    return 0 if res["ok"] else 1


def cmd_run(a) -> int:
    p = Project.open(a.project)
    envops.load_env(p.root)
    skip = tuple(stages.resolve(s) for s in (a.skip.split(",") if a.skip else []))
    try:
        res = stages.run_pipeline(p, start=a.start, end=a.end, skip=skip)
    except DecisionPending as e:
        return _pending(e, p)
    _print(res)
    return 0


def cmd_stage(a) -> int:
    p = Project.open(a.project)
    envops.load_env(p.root)
    opts = json.loads(a.opts) if a.opts else {}
    try:
        _print(stages.run_stage(p, a.stage, force=a.force, **opts))
    except DecisionPending as e:
        return _pending(e, p)
    return 0


def cmd_review(a) -> int:
    p = Project.open(a.project)
    envops.load_env(p.root)
    try:
        _print(stages.run_stage(p, "S9", force=True, iterations=p.state().get("iteration", 0) + a.iterations))
    except DecisionPending as e:
        return _pending(e, p)
    return 0


def cmd_render(a) -> int:
    p = Project.open(a.project)
    _print(stages.s8_render(p, Decider(p), cuts=a.cut or None, formats=a.format or None, concurrency=a.concurrency))
    return 0


def cmd_stills(a) -> int:
    from .ops import remotion as rem
    from .ops.takes import AssetServer

    p = Project.open(a.project)
    rem.write_brand_ts(p.brand)
    with AssetServer(p.root) as srv:
        props = rem.write_props(p, srv.url, debug=a.debug)
        out = rem.render_stills(p, props, [{"comp": a.comp, "frames": [int(x) for x in a.frames.split(",")]}],
                                p.path("render", "stills"), scale=a.scale)
    _print([str(x) for x in out])
    return 0


def cmd_decisions(a) -> int:
    p = Project.open(a.project)
    for r in pending_decisions(p):
        print(f"{r['decision']}: {r['task'][:120]}")
    return 0


def cmd_answer(a) -> int:
    p = Project.open(a.project)
    f = submit_decision(p, a.decision, Path(a.file).read_text())
    print(f"saved {f}; re-run the stage to validate it")
    return 0


def cmd_status(a) -> int:
    p = Project.open(a.project)
    st = p.state()
    for s in stages.STAGE_FUNCS:
        x = st["stages"].get(s, {})
        print(f" {s:4s} {stages.STAGE_NAMES[s]:11s} {x.get('status', '-'):18s} {x.get('decision', '') or x.get('error', '')[:80]}")
    print("costs:", p.costs())
    return 0


def cmd_brand(a) -> int:
    from .ops.remotion import write_brand_ts

    print(write_brand_ts(Project.open(a.project).brand))
    return 0


def cmd_demo(a) -> int:
    from .demo import build_demo

    p = build_demo(Path(a.project))
    print(f"demo project ready at {p.root}\nnext: reelforge render {p.root}  (no API keys or app needed)")
    return 0


def cmd_ui(a) -> int:
    import uvicorn

    from .ui.app import create_app

    uvicorn.run(create_app(Path(a.projects)), host="127.0.0.1", port=a.port)
    return 0


def cmd_mcp(a) -> int:
    from .mcp_server import main as mcp_main

    mcp_main()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="reelforge", description="AI-directed product-film pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="npm install the Remotion and capture drivers").set_defaults(fn=cmd_setup)
    x = sub.add_parser("init", help="create a project folder")
    x.add_argument("project")
    x.add_argument("--template", help="folder with brief.yaml / brand.json / assets/manifest.yaml / capture.yaml")
    x.set_defaults(fn=cmd_init)
    x = sub.add_parser("env", help="check tools, ports, keys and the app URL")
    x.add_argument("project", nargs="?")
    x.set_defaults(fn=cmd_env)
    x = sub.add_parser("run", help="run the pipeline (resumable, cached)")
    x.add_argument("project")
    x.add_argument("--from", dest="start", default="S0")
    x.add_argument("--to", dest="end", default="S10")
    x.add_argument("--skip", help="comma list, e.g. S1,S5")
    x.set_defaults(fn=cmd_run)
    x = sub.add_parser("stage", help="run one stage")
    x.add_argument("project")
    x.add_argument("stage", help="S0..S10 or a name (beats, capture, render...)")
    x.add_argument("--force", action="store_true")
    x.add_argument("--opts", help="JSON stage options")
    x.set_defaults(fn=cmd_stage)
    x = sub.add_parser("review", help="run N review/fix iterations")
    x.add_argument("project")
    x.add_argument("--iterations", type=int, default=1)
    x.set_defaults(fn=cmd_review)
    x = sub.add_parser("render", help="render, master, posters, SRT and verify")
    x.add_argument("project")
    x.add_argument("--cut", action="append")
    x.add_argument("--format", action="append")
    x.add_argument("--concurrency", type=int, default=4)
    x.set_defaults(fn=cmd_render)
    x = sub.add_parser("stills", help="render stills of one composition")
    x.add_argument("project")
    x.add_argument("comp")
    x.add_argument("frames", help="comma list")
    x.add_argument("--scale", type=float, default=0.5)
    x.add_argument("--debug", action="store_true")
    x.set_defaults(fn=cmd_stills)
    x = sub.add_parser("decisions", help="list pending agent-mode decisions")
    x.add_argument("project")
    x.set_defaults(fn=cmd_decisions)
    x = sub.add_parser("answer", help="answer a pending decision with a JSON file")
    x.add_argument("project")
    x.add_argument("decision")
    x.add_argument("file")
    x.set_defaults(fn=cmd_answer)
    x = sub.add_parser("status", help="stage status and costs")
    x.add_argument("project")
    x.set_defaults(fn=cmd_status)
    x = sub.add_parser("brand", help="regenerate brand.ts from brand.json")
    x.add_argument("project")
    x.set_defaults(fn=cmd_brand)
    x = sub.add_parser("demo", help="build an offline demo project (synthetic capture, music and GLB)")
    x.add_argument("project")
    x.set_defaults(fn=cmd_demo)
    x = sub.add_parser("ui", help="local web UI")
    x.add_argument("--projects", default="projects")
    x.add_argument("--port", type=int, default=8765)
    x.set_defaults(fn=cmd_ui)
    sub.add_parser("mcp", help="run the MCP server (stdio)").set_defaults(fn=cmd_mcp)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
