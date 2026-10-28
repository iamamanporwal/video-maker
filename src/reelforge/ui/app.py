"""Local web UI: brief, brand kit, asset library, run monitor, review gallery, deliverables.

It is a thin layer over the same Project/stages code the CLI and MCP server use.
"""

from __future__ import annotations

import json
import shutil
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import ValidationError

from .. import review as rv
from .. import stages
from ..llm import DecisionPending, pending_decisions, submit_decision
from ..ops import env as envops
from ..ops import media
from ..ops.images import contrast_ratio, dominant_colours
from ..project import Project
from ..schemas import Asset, Brand, Brief

STATIC = Path(__file__).parent / "static"
KIND_BY_EXT = {".png": "image", ".jpg": "photo", ".jpeg": "photo", ".webp": "image", ".mp3": "music", ".wav": "sfx",
               ".mp4": "video", ".mov": "video", ".hdr": "hdri", ".glb": "glb", ".ttf": "font", ".otf": "font"}


class Jobs:
    def __init__(self):
        self.lock = threading.Lock()
        self.jobs: dict[str, dict] = {}

    def start(self, key: str, fn, *args, **kw) -> dict:
        with self.lock:
            j = self.jobs.get(key)
            if j and j["status"] == "running":
                raise HTTPException(409, f"a job is already running for {key}: {j['what']}")
            job = {"what": kw.pop("_what", fn.__name__), "status": "running", "started": time.time()}
            self.jobs[key] = job

        def run():
            try:
                job["result"] = fn(*args, **kw)
                job["status"] = "done"
            except DecisionPending as e:
                job["status"] = "awaiting_decision"
                job["decision"] = e.decision_id
            except Exception as e:  # noqa: BLE001
                job["status"] = "failed"
                job["error"] = f"{e}\n{traceback.format_exc()[-1500:]}"
            job["ended"] = time.time()

        threading.Thread(target=run, daemon=True).start()
        return job


def create_app(projects_dir: Path) -> FastAPI:
    projects_dir = projects_dir.resolve()
    projects_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="ReelForge")
    jobs = Jobs()

    def proj(name: str) -> Project:
        root = (projects_dir / name).resolve()
        if projects_dir not in root.parents or not (root / "brief.yaml").exists():
            raise HTTPException(404, f"no project {name}")
        envops.load_env(root)
        return Project(root)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (STATIC / "index.html").read_text()

    # ------------------------------------------------------------------ projects

    @app.get("/api/projects")
    def list_projects():
        out = []
        for d in sorted(projects_dir.iterdir()):
            if (d / "brief.yaml").exists():
                st = json.loads((d / "state.json").read_text()) if (d / "state.json").exists() else {}
                done = [s for s, v in st.get("stages", {}).items() if v.get("status") == "done"]
                out.append({"name": d.name, "stages_done": len(done), "iteration": st.get("iteration", 0)})
        return out

    @app.post("/api/projects")
    def create_project(body: dict = Body(...)):
        name = body.get("name", "").strip()
        if not name or "/" in name or name.startswith("."):
            raise HTTPException(400, "bad name")
        root = projects_dir / name
        tpl = body.get("template")
        if body.get("demo"):
            from ..demo import build_demo

            build_demo(root)
            return {"name": name}
        src = Path(tpl) if tpl else Path(__file__).resolve().parents[3] / "examples" / "vi3w"
        p = Project.create(root, brief=src / "brief.yaml", brand=src / "brand.json", manifest=src / "assets/manifest.yaml")
        if (src / "capture.yaml").exists() and not p.path("capture.yaml").exists():
            shutil.copy(src / "capture.yaml", p.path("capture.yaml"))
        data = yaml.safe_load(p.path("brief.yaml").read_text())
        data["project"] = name
        p.path("brief.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        return {"name": name}

    @app.get("/api/p/{name}")
    def project_info(name: str):
        p = proj(name)
        tl = p.read_json("plan/timeline.json")
        return {
            "name": name,
            "brief_yaml": p.path("brief.yaml").read_text(),
            "brand": p.brand.model_dump(),
            "state": p.state(),
            "costs": p.costs(),
            "budgets": p.brief.budgets.model_dump(),
            "pending": pending_decisions(p),
            "jobs": jobs.jobs.get(name),
            "beats": p.read_json("plan/beats.json"),
            "timeline": {"cuts": [{"name": c["name"], "frames": c["durationInFrames"], "formats": c["formats"],
                                   "scenes": [{"id": s["id"], "kind": s["kind"], "from": s["from"], "duration": s["duration"]}
                                              for s in c["scenes"]]} for c in tl["cuts"]]} if tl else None,
            "stages": [{"id": s, "name": stages.STAGE_NAMES[s]} for s in stages.STAGE_FUNCS],
        }

    # ------------------------------------------------------------------ brief + brand

    @app.put("/api/p/{name}/brief")
    def save_brief(name: str, body: dict = Body(...)):
        p = proj(name)
        try:
            data = yaml.safe_load(body["yaml"])
            Brief.model_validate(data)
        except (yaml.YAMLError, ValidationError) as e:
            raise HTTPException(400, str(e))
        p.path("brief.yaml").write_text(body["yaml"])
        return {"ok": True}

    @app.put("/api/p/{name}/brand")
    def save_brand(name: str, body: dict = Body(...)):
        p = proj(name)
        try:
            b = Brand.model_validate(body)
        except ValidationError as e:
            raise HTTPException(400, str(e))
        p.path("brand.json").write_text(b.model_dump_json(indent=2))
        return {"ok": True, "contrast": brand_contrast(b)}

    def brand_contrast(b: Brand) -> list[dict]:
        ink = b.colors.get("ink", "#000000")
        out = []
        for k, v in b.colors.items():
            for c in (v if isinstance(v, list) else [v]):
                if isinstance(c, str) and c.startswith("#") and k != "ink":
                    r = contrast_ratio(c, ink)
                    out.append({"token": k, "color": c, "ratio": r, "warn": r < 4.5})
        return out

    @app.get("/api/p/{name}/brand/contrast")
    def get_contrast(name: str):
        return brand_contrast(proj(name).brand)

    # ------------------------------------------------------------------ assets

    @app.get("/api/p/{name}/assets")
    def get_assets(name: str):
        p = proj(name)
        out = []
        for a in p.assets:
            f = p.path(a.file)
            info: dict[str, Any] = {"exists": f.exists()}
            if f.exists():
                info["size_kb"] = round(f.stat().st_size / 1024)
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    from PIL import Image

                    with Image.open(f) as im:
                        info["dims"] = f"{im.width}x{im.height}"
                    info["colours"] = dominant_colours(f)
                elif f.suffix.lower() in (".mp3", ".wav", ".mp4", ".mov"):
                    try:
                        info["duration"] = round(media.summary(f)["duration"], 2)
                    except Exception:  # noqa: BLE001
                        pass
            out.append({**a.model_dump(), **info})
        return out

    @app.put("/api/p/{name}/assets")
    def put_assets(name: str, body: list[dict] = Body(...)):
        p = proj(name)
        try:
            assets = [Asset.model_validate(a) for a in body]
        except ValidationError as e:
            raise HTTPException(400, str(e))
        p.save_assets(assets)
        return {"ok": True}

    @app.post("/api/p/{name}/assets/upload")
    async def upload(name: str, files: list[UploadFile] = File(...)):
        p = proj(name)
        assets = p.assets
        known = {a.file for a in assets}
        added = []
        for uf in files:
            fn = Path(uf.filename or "upload.bin").name
            kind = KIND_BY_EXT.get(Path(fn).suffix.lower(), "other")
            rel = f"assets/{kind}s/{fn}"
            dst = p.path(rel)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(await uf.read())
            if rel not in known:
                assets.append(Asset(file=rel, kind=kind))
                added.append(rel)
        p.save_assets(assets)
        return {"added": added}

    # ------------------------------------------------------------------ runs + decisions

    @app.post("/api/p/{name}/run")
    def run(name: str, body: dict = Body(...)):
        p = proj(name)
        stage = body.get("stage")
        if body.get("pipeline"):
            return jobs.start(name, stages.run_pipeline, p, start=body.get("from", "S0"), end=body.get("to", "S10"),
                              _what="pipeline")
        if stage == "demo-render":
            return jobs.start(name, stages.s8_render, p, None, _what="render")
        opts = body.get("options") or {}
        return jobs.start(name, stages.run_stage, p, stage, force=bool(body.get("force")), _what=f"stage {stage}", **opts)

    @app.get("/api/p/{name}/logs")
    def logs(name: str, since: float = 0):
        p = proj(name)
        recs = [r for s in ("run", "decisions", "capture", "costs") for r in
                ({**x, "stream": s} for x in p.read_log(s)) if r["t"] > since]
        return sorted(recs, key=lambda r: r["t"])[-300:]

    @app.post("/api/p/{name}/decisions/{decision}")
    def answer(name: str, decision: str, body: dict = Body(...)):
        p = proj(name)
        ans = body.get("answer")
        if isinstance(ans, str):
            try:
                ans = json.loads(ans)
            except json.JSONDecodeError as e:
                raise HTTPException(400, f"answer is not JSON: {e}")
        submit_decision(p, decision, ans)
        return {"ok": True}

    # ------------------------------------------------------------------ review + deliverables

    @app.get("/api/p/{name}/reviews")
    def reviews(name: str):
        p = proj(name)
        out = []
        for d in sorted(p.path("review").glob("it*")):
            if not d.is_dir():
                continue
            ev = json.loads((d / "evidence.json").read_text()) if (d / "evidence.json").exists() else {}
            item = {"iteration": d.name, "scores": _load(d / "scores.json"), "review": _load(d / "review.json"),
                    "fixplan": _load(d / "fixplan.json"),
                    "sheets": [m["sheet"] for m in ev.get("masters", {}).values()],
                    "waves": [m["waveform"] for m in ev.get("masters", {}).values()],
                    "stills": [s["file"] for m in ev.get("masters", {}).values() for s in m.get("stills", [])][:24]}
            out.append(item)
        return {"iterations": out, "scoreboard": p.path("review/SCOREBOARD.md").read_text()
                if p.path("review/SCOREBOARD.md").exists() else ""}

    @app.post("/api/p/{name}/evidence")
    def make_evidence(name: str, body: dict = Body(default={})):
        p = proj(name)
        it = int(body.get("iteration") or p.state().get("iteration", 0) + 1)
        return jobs.start(name, rv.evidence_pack, p, it, _what=f"evidence it{it:02d}")

    @app.get("/api/p/{name}/deliverables")
    def deliverables(name: str):
        p = proj(name)
        out = p.path("render/out")
        files = sorted(f.name for f in out.iterdir()) if out.exists() else []
        spec = out / "spec-table.md"
        return {"files": files, "spec_table": spec.read_text() if spec.exists() else "",
                "storyboard": sorted(str(f.relative_to(p.root)) for f in p.path("plan/storyboard").glob("*.sheet.jpg"))}

    @app.get("/files/{name}/{path:path}")
    def files(name: str, path: str):
        p = proj(name)
        f = (p.root / path).resolve()
        if p.root not in f.parents or not f.is_file():
            raise HTTPException(404)
        return FileResponse(f)

    return app


def _load(f: Path) -> Optional[dict]:
    return json.loads(f.read_text()) if f.exists() else None
