"""The pipeline: S0-S10. Python does the operations; Decider is called only at D1-D11."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Callable, Optional

from . import plan as planmod
from . import review as rv
from .grid import Grid, timecode
from .llm import Decider, DecisionPending
from .ops import audio, glb, media, providers, strokes
from .ops import capture as cap
from .ops import env as envops
from .ops import remotion as rem
from .ops.images import find_image
from .ops.takes import AssetServer, make_takes
from .project import STAGES, BudgetExceeded, Project, hash_files, sha
from .schemas import (
    SCENE_KINDS, AssetSelection, AudioPlan, BeatsDoc, CapturePlan, DirectorNote, FixPlan, Review,
    StrokePlacement, Timeline, Treatment, VariantJudgement,
)
from .validate import enforce_asset_rules, trademark_hits, validate_beats, validate_timeline

TASTE_CACHE = Path(os.environ.get("REELFORGE_CACHE", Path.home() / ".reelforge" / "taste"))


class StageFailed(RuntimeError):
    pass


def _brief_ctx(p: Project) -> dict:
    b = p.brief
    return {"brief": b.model_dump(mode="json"), "brand": p.brand.model_dump(mode="json"),
            "grid": Grid(bpm=b.music.bpm, fps=b.fps).describe()}


# ============================================================================ S0 init + env check


def s0_init(p: Project, d: Decider, **_) -> dict:
    envops.load_env(p.root)
    res = envops.env_check(p.brief.product.url, need_capture=p.path("capture.yaml").exists())
    p.write_json("logs/env_check.json", res)
    rem.write_brand_ts(p.brand)
    if not res["ok"]:
        bad = {k: v for k, v in res["checks"].items() if v["required"] and not v["ok"]}
        raise StageFailed(f"environment check failed: {json.dumps(bad)}")
    return {"env": "ok", "warnings": [k for k, v in res["checks"].items() if not v["ok"]]}


# ============================================================================ S1 treatment (D1)


def s1_treatment(p: Project, d: Decider, **_) -> dict:
    b = p.brief
    TASTE_CACHE.mkdir(parents=True, exist_ok=True)
    taste_f = TASTE_CACHE / f"{re.sub(r'[^a-z0-9-]', '-', b.genre.lower())}.json"
    taste = json.loads(taste_f.read_text()) if taste_f.exists() else None
    task = ("D1 TREATMENT. Write the taste board and a one-page treatment for this launch film: logline, tone, colour "
            "script per act, music plan, camera language, the transition motif, pacing targets, a hook rule, and three "
            "'screenshot frames' (moments that must work as stills). Study best-in-class launch films (Apple, Linear, "
            "Vercel, Figma, Arc, the product's category) and Pixar story principles; say what to steal.")
    ctx = {**_brief_ctx(p), "cached_taste_board": taste}
    t = d.decide("D1_treatment", Treatment, task, ctx, web_research=taste is None)
    if taste is None:
        taste_f.write_text(json.dumps({"genre": b.genre, "steal_list": t.steal_list}, indent=2))
    p.write_json("research/treatment.json", t)
    p.path("research/treatment.md").write_text(t.treatment_markdown)
    return {"logline": t.logline, "motif": t.motif}


# ============================================================================ S2 beats -> timeline (D2)


SCENE_CATALOGUE = {
    "cold_open": "props: clock, channel, messages[{from,text,at(frame),me?}], chatAt, stare{at}, slam{text,at}, photo?",
    "chat": "props: channel, messages[{from,text,at,me?}]",
    "url_to_logo": "props: url, logo? (asset), wordmark?, sub, reflowAt",
    "product_shot": "props: take, timeKeys[[localFrame, srcSec]], focusKeys[[f,x,y,w,h]] (page px), headlines[{text,at,out?}], tag{text,at} (honest real time), side, strokesFrom",
    "before_after": "props: before, after (asset or 'take:<take>/out.jpg'), wipeKeys[[f,0..1]], labels[2], headline",
    "triptych": "props: images[3], labels[3]",
    "image_to_3d": "props: take, timeKeys, focusKeys, glb ('take:<take>/model.glb'), scanAt, scanDur, headline, tag",
    "plot_twist": "props: channel, messages, big{text,at}",
    "finale_3d": "props: glb, hdri?, camKeys[[f,x,y,z,lx,ly,lz,fov]], carKeys[[f,y,rotY,tilt]], thrustKeys[[f,power]], anchors (auto), tunnel, headlines",
    "end_room": "props: clock, sleepAt, tagline, monitor?, photo?",
    "end_card": "props: logo?, wordmark?, tagline, url, cta",
    "video_clip": "props: src (fal clip, NON-product only), trimSec, caption, generated=true",
    "photo_insert": "props: src (asset), kenBurns[[f,scale,x,y]], caption",
    "hook": "props: lines[{text,at,accent?,size?}] (honest claims), src (asset) + video? + trimSec | glb + camKeys, zoomKeys[[f,scale]], place top|bottom, flash, generated",
}


def s2_beats(p: Project, d: Decider, **_) -> dict:
    b = p.brief
    tr = p.read_json("research/treatment.json", {})
    task = ("D2 BEATS. Turn the brief and treatment into a beat sheet for every cut. Rules: each beat is one scene "
            "kind from the catalogue; starts and durations are in SECONDS and must land on the BPM grid; beats are "
            "contiguous and sum exactly to the cut length; major events (title sting, reveal drop, twist silence, "
            "finale drop) sit on bar lines; headlines <= 4 words; the social cut's hook lands within hook_seconds "
            "(set props.hook_at if the first beat is long); never use trademark terms. Put scene props you already "
            "know in props (e.g. chat messages with frame offsets, clock text).")
    ctx = {**_brief_ctx(p), "treatment": tr, "scene_catalogue": SCENE_CATALOGUE}
    doc = d.decide("D2_beats", BeatsDoc, task, ctx, validator=lambda x: validate_beats(x, b))
    p.write_json("plan/beats.json", doc)
    prev = Timeline.model_validate(p.read_json("plan/timeline.json")) if p.path("plan/timeline.json").exists() else None
    tl = planmod.beats_to_timeline(doc, b, p.brand.model_dump(mode="json"), previous=prev)
    errs = validate_timeline(tl, b)
    if errs:
        raise StageFailed("timeline invalid: " + "; ".join(errs))
    p.write_json("plan/timeline.json", tl)
    _shotlist(p, doc)
    return {c.cut: len(c.beats) for c in doc.cuts}


def _shotlist(p: Project, doc: BeatsDoc) -> None:
    lines = ["# Shot list", ""]
    for c in doc.cuts:
        lines += [f"## {c.cut}", "", "| id | start | dur | kind | headline | caption |", "|---|---|---|---|---|---|"]
        lines += [f"| {x.id} | {x.start:.2f} | {x.dur:.2f} | {x.kind} | {x.headline} | {x.caption} |" for x in c.beats]
        lines.append("")
    p.path("plan/shotlist.md").write_text("\n".join(lines))


# ============================================================================ S3 storyboard (stills)


def s3_storyboard(p: Project, d: Decider, scale: float = 0.4, **_) -> dict:
    tl = p.timeline
    rem.write_brand_ts(p.brand)
    out = p.path("plan/storyboard")
    if out.exists():
        shutil.rmtree(out)
    with AssetServer(p.root) as srv:
        props = rem.write_props(p, srv.url)
        jobs = [{"comp": f"{ct.name}-{fmt}", "frames": [s.from_ + min(s.duration - 1, max(12, s.duration // 2)) for s in ct.scenes]}
                for ct in tl.cuts for fmt in ct.formats]
        stills = rem.render_stills(p, props, jobs, out / "stills", scale=scale)
    sheets = []
    for ct in tl.cuts:
        for fmt in ct.formats:
            comp = f"{ct.name}-{fmt}"
            mine = [s for s in stills if s.name.startswith(comp + "_")]
            labels = [(f"{sc.id} {timecode(sc.from_)}", f) for sc, f in zip(ct.scenes, sorted(mine))]
            sheets.append(media.tile(labels, out / f"{comp}.sheet.jpg", cols=6, cell_w=260 if fmt == "16x9" else 160,
                                     title=f"storyboard {comp}"))
    return {"stills": len(stills), "sheets": [str(s.relative_to(p.root)) for s in sheets]}


# ============================================================================ S4 capture (D3, D4, D5)


def s4_capture(p: Project, d: Decider, only: Optional[list[str]] = None, headless: Optional[bool] = None, **_) -> dict:
    b = p.brief
    cfg = cap.capture_config(p)
    ui = p.read_json("capture/_ui/ui.json")
    task = ("D3 CAPTURE PLAN. Decide the real product runs needed for every product beat: which macro (command) to run, "
            "the take id, the prompt to type on screen (trademark rules apply; prompts are visible), which features to "
            "sketch, the model choice, and how many variants. Use a new studio per chain (stale state is a known bug).")
    ctx = {**_brief_ctx(p), "beats": p.read_json("plan/beats.json"), "macros": list(cfg.get("macros", {})),
           "credits_per_command": cfg.get("credits", {}), "ui_dump": (ui or [])[:200]}
    plan = d.decide("D3_capture_plan", CapturePlan, task, ctx,
                    validator=lambda x: [h for s in x.steps for h in trademark_hits([s.prompt], b.rules.trademark_avoid)])
    p.write_json("plan/capture_plan.json", plan)
    results = {}
    for step in plan.steps:
        if only and step.take not in only:
            continue
        if p.path("capture", step.take, "take.json").exists() and not only:
            results[step.take] = "cached"
            continue
        results[step.take] = _capture_with_judging(p, d, step, cfg, headless)
    return results


def _strokes_for(p: Project, d: Decider, step, take_dir: Path) -> Optional[Path]:
    """Sketch strokes: templates for fresh sketches; D4 placement on the real out.jpg for overlay edits."""
    if step.command == "sketch":
        name = step.features[0] if step.features and step.features[0] in strokes.TEMPLATES else None
        prims = strokes.TEMPLATES[name] if name else strokes.TEMPLATES["sedan_side"]
        s = strokes.build(prims, seed=int(sha(step.take)[:6], 16))
        strokes.preview(s, take_dir / "strokes.preview.png")
        return strokes.save(s, take_dir / "strokes.json")
    if step.command == "edit":
        src_take = step.source_take
        src = p.path("capture", src_take, "out.jpg")
        if not src.exists():
            raise StageFailed(f"edit step {step.take} needs capture/{src_take}/out.jpg")
        from PIL import Image

        W, H = Image.open(src).size
        task = ("D4 STROKE PLACEMENT. On this real generated image, return pixel coordinates for the parts the "
                f"sketch must touch: {step.features}. Circles for wheels (centre + radius), polylines for deck lines, "
                "hood centreline, etc. Coordinates in the image's own pixel space.")
        sp = d.decide(f"D4_strokes_{step.take}", StrokePlacement, task, {"features": step.features, "image_size": [W, H]},
                      images=[src])
        prims = strokes.from_parts([x.model_dump() for x in sp.parts], (W, H))
        s = strokes.build(prims, seed=int(sha(step.take)[:6], 16))
        strokes.preview(s, take_dir / "strokes.preview.png", base=src)
        return strokes.save(s, take_dir / "strokes.json")
    return None


def _capture_with_judging(p: Project, d: Decider, step, cfg: dict, headless) -> dict:
    credits = cfg.get("credits", {}).get(step.command, 0)
    prompt = step.prompt
    attempts = []
    max_tries = cfg.get("max_retries", 2) + 1
    for attempt in range(max_tries):
        variants = []
        for v in range(max(1, step.variants)):
            take = step.take if step.variants <= 1 and attempt == 0 else f"{step.take}__a{attempt}v{v}"
            tdir = p.path("capture", take)
            tdir.mkdir(parents=True, exist_ok=True)
            p.check_budget("app", credits=credits)
            sfile = _strokes_for(p, d, step, tdir)
            args = {"prompt": prompt, "model_regex": step.model, "take": take, "source_take": step.source_take}
            if sfile:
                args["strokes"] = str(sfile)
            res = cap.capture_step(p, step.command, take, args, headless=headless)
            p.add_cost("app", 0.0, credits=credits, take=take, command=step.command)
            variants.append(res)
        outs = [(v["take"], p.path("capture", v["take"], "out.jpg")) for v in variants if v["ok"]]
        outs = [(t, f) for t, f in outs if f.exists()]
        if not outs:
            attempts.append({"attempt": attempt, "error": [v.get("error") for v in variants]})
            continue
        checks = cfg.get("judge_checks", [
            "no legible brand badge or logo on the product",
            "the change is dramatic at a 320 px thumbnail",
            f"the requested features are present: {step.features}",
            "composition matches the sketch",
        ])
        task = (f"D5 VARIANT JUDGE for take '{step.take}' ({step.command}). Images are candidate outputs in order "
                f"{[t for t, _ in outs]}. Apply every hard check; reject any candidate that fails one. If all fail, "
                "write a strengthened prompt (never retouch outputs - re-run instead).")
        j = d.decide(f"D5_judge_{step.take}_a{attempt}", VariantJudgement, task,
                     {"checks": checks, "prompt": prompt, "candidates": [t for t, _ in outs],
                      "trademark_avoid": p.brief.rules.trademark_avoid}, images=[f for _, f in outs])
        attempts.append({"attempt": attempt, "best": j.best, "rejects": j.rejects, "reasons": j.reasons})
        if j.best:
            if j.best != step.take:
                dst = p.path("capture", step.take)
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(p.path("capture", j.best), dst)
            p.log("capture", {"take": step.take, "picked": j.best, "attempts": len(attempts)})
            return {"ok": True, "picked": j.best, "attempts": attempts}
        prompt = j.stronger_prompt or prompt
    raise StageFailed(f"capture {step.take}: no variant passed the judge after {max_tries} attempts: {attempts}")


# ============================================================================ S5 audio + generative assets (D6)


def s5_audio(p: Project, d: Decider, skip_paid: bool = False, **_) -> dict:
    b = p.brief
    tl = p.timeline
    task = ("D6 AUDIO PLAN. Write an ElevenLabs Music composition plan whose section durations match the hero edit "
            "(intro, drop at the title sting, build, groove, break at the twist, rebuild, drop 2, outro), a separate "
            "~9 s outro cue so the tagline isn't silent, the SFX list (short prompts, seconds), and fal video prompts "
            "for NON-product b-roll only (a human at a desk at night, hands, establishing room shots).")
    hero = tl.cuts[0]
    ctx = {**_brief_ctx(p), "timeline_scenes": [{"id": s.id, "kind": s.kind, "from_s": s.from_ / hero.fps,
                                                "dur_s": s.duration / hero.fps} for s in hero.scenes],
           "sfx_hints": sorted({x[1] for ct in tl.cuts for x in ct.sfx})}
    ap = d.decide("D6_audio_plan", AudioPlan, task, ctx)
    p.write_json("plan/audio_plan.json", ap)
    out: dict = {"music": None, "sfx": 0, "video": []}
    envops.load_env(p.root)
    music = p.path("audio/music/hero.mp3")
    if not skip_paid and not music.exists():
        try:
            plan = {"positive_global_styles": ap.positive_global_styles, "negative_global_styles": ap.negative_global_styles,
                    "sections": [s.model_dump() for s in ap.sections]}
            providers.gen_music(p, "hero", plan)
            providers.gen_music(p, "outro", {**plan, "sections": [s.model_dump() for s in ap.outro_sections]})
        except (providers.ProviderError, BudgetExceeded) as e:
            out["music_error"] = str(e)
    if not skip_paid:
        try:
            out["sfx"] = len(providers.gen_sfx(p, [c.model_dump() for c in ap.sfx]))
        except (providers.ProviderError, BudgetExceeded) as e:
            out["sfx_error"] = str(e)
        for vp in ap.video:
            try:
                out["video"].append(_gen_broll(p, d, vp))
            except (providers.ProviderError, BudgetExceeded) as e:
                out.setdefault("video_errors", []).append(str(e))
    if music.exists():
        out["music"] = align_music(p)
    return out


def _gen_broll(p: Project, d: Decider, vp) -> str:
    cands = []
    for i in range(max(1, vp.candidates)):
        raw = providers.gen_video(p, f"{vp.clip}_c{i}", vp.prompt, vp.seconds, vp.aspect)
        cands.append(raw)
    stills = [media.still_at(c, vp.seconds / 2, c.with_suffix(".mid.jpg")) for c in cands]
    j = d.decide(f"D5_judge_broll_{vp.clip}", VariantJudgement,
                 "D5 VARIANT JUDGE for generated b-roll. Reject anything that depicts product UI or outputs, any legible "
                 "brand, uncanny hands/faces, or off-brand colour.",
                 {"prompt": vp.prompt, "candidates": [c.stem for c in cands]}, images=stills)
    best = next((c for c in cands if c.stem == j.best), None)
    if not best:
        raise providers.ProviderError(f"all b-roll candidates rejected for {vp.clip}")
    for ct in p.timeline.cuts:
        for fmt in ct.formats:
            w, h = {"16x9": (1920, 1080), "9x16": (1080, 1920), "4x5": (1080, 1350), "5x4": (1350, 1080)}[fmt]
            media.conform(best, p.path("video_gen", f"{vp.clip}.{fmt}.mp4"), w, h, seconds=vp.seconds,
                          grade_toward=p.brand.colors.get("ink"))
    return vp.clip


def align_music(p: Project) -> dict:
    """Solve music offsets so drops land on the edit's bar lines; write segments into timeline.json."""
    b = p.brief
    an = audio.analyse(p.path("audio/music/hero.mp3"), bpm_prior=b.music.bpm)
    outro = p.path("audio/music/outro.mp3")
    p.write_json("audio/analysis.json", an)
    doc = p.read_json("plan/timeline.json")
    for ct in doc["cuts"]:
        fps, total = ct["fps"], ct["durationInFrames"] / ct["fps"]
        grid = Grid(bpm=ct["bpm"], fps=fps)
        marks = [s["from"] / fps for s in ct["scenes"] if s["props"].get("music_drop")] or \
                [s["from"] / fps for s in ct["scenes"] if s["kind"] in ("url_to_logo", "finale_3d")]
        marks = [grid.frame_to_sec(grid.nearest_bar(m * fps)) for m in marks]
        drops = [x["t_beat"] for x in an["drops"]] or [an["phase"]]
        end_card = next((s for s in ct["scenes"] if s["kind"] in ("end_card", "end_room")), None)
        music_end = (end_card["from"] / fps) if (end_card and outro.exists()) else total
        aligns = []
        if marks:
            # First drop -> first mark (delay entry if needed); second drop -> second mark via re-entry.
            aligns.append({"src": "audio/music/hero.mp3", "edit_from": 0.0, "edit_to": marks[1] if len(marks) > 1 and len(drops) > 1 else music_end,
                           "edit_align": marks[0], "music_align": drops[0]})
            if len(marks) > 1 and len(drops) > 1:
                aligns.append({"src": "audio/music/hero.mp3", "edit_from": marks[1] - 0.15 if marks[1] > 0.15 else marks[1],
                               "edit_to": music_end, "edit_align": marks[1], "music_align": drops[1]})
        else:
            aligns.append({"src": "audio/music/hero.mp3", "edit_from": 0.0, "edit_to": music_end, "edit_align": 0.0, "music_align": 0.0})
        segs = audio.solve_segments(aligns, fps=fps)
        for s in segs:
            end = s["from"] + s["dur"]
            s["volumeKeys"] = [[s["from"], 0.0], [s["from"] + 6, 0.9], [max(s["from"] + 7, end - 12), 0.9], [end, 0.0]]
        if outro.exists() and end_card:
            segs.append({"src": "audio/music/outro.mp3", "from": end_card["from"], "trimSec": 0.0,
                         "dur": ct["durationInFrames"] - end_card["from"],
                         "volumeKeys": [[end_card["from"], 0.9], [ct["durationInFrames"] - 6, 0.9], [ct["durationInFrames"], 0.0]]})
        ct["music"] = segs
    p.write_json("plan/timeline.json", doc)
    return {"bpm": an["bpm"], "drops": an["drops"], "segments": {c["name"]: c["music"] for c in doc["cuts"]}}


# ============================================================================ S6 data prep


def s6_prep(p: Project, d: Decider, **_) -> dict:
    takes = make_takes(p) if p.path("capture").exists() else {}
    models = {}
    for g in sorted(p.path("capture").glob("*/model.glb")):
        take = g.parent.name
        info = glb.inspect_glb(g)
        tex = glb.texture_check(g, g.parent / "out.jpg", out_png=g.parent / "basecolor.png")
        anc = glb.anchors(g)
        models[take] = {"inspect": info, "texture": tex, "anchors": anc}
        if "recommend" in tex:
            p.log("decisions", {"decision": "texture_check", "take": take, "applied": tex["recommend"]})
    p.write_json("plan/models.json", models)
    # Fill model-derived props the AI shouldn't guess (anchors, base-colour factor) where unset.
    doc = p.read_json("plan/timeline.json")
    for ct in doc["cuts"]:
        for s in ct["scenes"]:
            g = s["props"].get("glb", "")
            m = re.match(r"take:([^/]+)/", g)
            if m and m.group(1) in models:
                mi = models[m.group(1)]
                if s["kind"] == "finale_3d" and "anchors" not in s["props"]:
                    A = mi["anchors"]
                    up = "xyz".index(A["up"])
                    s["props"]["anchors"] = [_to_three(v, up) for v in A["anchors"].values()]
                if "recommend" in mi["texture"] and "baseColorFactor" not in s["props"]:
                    s["props"]["baseColorFactor"] = mi["texture"]["recommend"]["baseColorFactor"][0]
    p.write_json("plan/timeline.json", doc)
    return {"takes": takes, "models": list(models)}


def _to_three(v: list[float], up: int) -> list[float]:
    """Anchors are reported in the GLB's world axes; the renderer is Y-up."""
    x, y, z = v
    return [x, z, -y] if up == 2 else [x, y, z]


# ============================================================================ S7 compose (D7)


ASSET_PROP = {"photo": {"cold_open": "photo", "end_room": "photo", "photo_insert": "src"},
              "logo": {"url_to_logo": "logo", "end_card": "logo"},
              "video": {"video_clip": "src"}, "hdri": {"finale_3d": "hdri", "image_to_3d": "hdri"}}


def s7_compose(p: Project, d: Decider, **_) -> dict:
    assets = p.assets
    doc = p.read_json("plan/timeline.json")
    applied = []
    if assets:
        scenes = [{"cut": ct["name"], "id": s["id"], "kind": s["kind"]} for ct in doc["cuts"] for s in ct["scenes"]]
        task = ("D7 ASSET SELECTION. For each beat, pick the best labelled asset (or null). Respect each asset's "
                "`use` and `never` labels and notes (e.g. a real photo is preferred over the vector room).")
        sel = d.decide("D7_assets", AssetSelection, task,
                       {"scenes": scenes, "assets": [a.model_dump() for a in assets]})
        by_file = {a.file: a for a in assets}
        for pick in sel.picks:
            if not pick.asset or pick.asset not in by_file:
                continue
            a = by_file[pick.asset]
            for ct in doc["cuts"]:
                for s in ct["scenes"]:
                    if s["id"] != pick.beat_id:
                        continue
                    if enforce_asset_rules(a, s["kind"]):  # Python enforces `never`
                        p.log("decisions", {"decision": "D7_enforced", "dropped": a.file, "scene": s["id"]})
                        continue
                    key = ASSET_PROP.get(a.kind, {}).get(s["kind"])
                    if key and key not in s["props"]:
                        s["props"][key] = a.file
                        applied.append((s["id"], key, a.file))
    p.write_json("plan/timeline.json", doc)
    errs = validate_timeline(p.timeline, p.brief)
    if errs:
        raise StageFailed("timeline invalid: " + "; ".join(errs))
    rem.write_brand_ts(p.brand)
    return {"assets_applied": applied}


# ============================================================================ S8 render + master + verify


def allowed_dark(p: Project, cut: str) -> list[tuple[int, int]]:
    ct = p.timeline.cut(cut)
    return [(s.from_, s.from_ + s.duration) for s in ct.scenes if s.props.get("allowDark")]


def s8_render(p: Project, d: Decider, cuts: Optional[list[str]] = None, formats: Optional[list[str]] = None,
              concurrency: int = 4, **_) -> dict:
    rem.write_brand_ts(p.brand)
    out = p.path("render/out")
    raw = p.path("render/raw")
    comps = rem.compositions(p, cuts, formats)
    heavy = any(g.stat().st_size > 30e6 for g in p.path("capture").glob("*/model.glb"))
    results = []
    with AssetServer(p.root) as srv:
        props = rem.write_props(p, srv.url)
        for comp, cut, fmt in comps:
            t0 = time.time()
            rem.render_video(p, comp, props, raw / f"{comp}.mp4", concurrency=2 if heavy else concurrency,
                             timeout_ms=480000 if heavy else 240000)
            media.master(raw / f"{comp}.mp4", out / f"{comp}.mp4")
            p.log("run", {"rendered": comp, "seconds": round(time.time() - t0, 1)})
        posters = rem.render_stills(p, props, [{"comp": f"Poster-{c}", "frames": [0]} for c, _, _ in comps],
                                    p.path("render/posters_tmp"), scale=1.0, fmt="png")
        for f in posters:
            shutil.move(str(f), out / (f.name.split("_f")[0] + ".png"))
    for cut in {c for _, c, f in comps if f == "16x9"}:
        ct = p.timeline.cut(cut)
        out.joinpath(f"{cut}-16x9.srt").write_text(media.srt(ct.captions, ct.fps))
    for comp, cut, fmt in comps:
        ct = p.timeline.cut(cut)
        w, h = {"16x9": (1920, 1080), "9x16": (1080, 1920), "4x5": (1080, 1350), "5x4": (1350, 1080)}[fmt]
        results.append(media.verify_specs(out / f"{comp}.mp4", {"duration": ct.durationInFrames / ct.fps, "width": w,
                                                                  "height": h, "fps": ct.fps},
                                          allowed_dark=allowed_dark(p, cut)))
    table = media.spec_table(results)
    out.joinpath("spec-table.md").write_text("# Spec table\n\n" + table)
    p.write_json("render/out/spec.json", results)
    failed = [r["file"] for r in results if not r["pass"]]
    if failed:
        raise StageFailed(f"spec verification failed for {failed}; see render/out/spec-table.md")
    return {"masters": [c for c, _, _ in comps], "spec": "pass"}


# ============================================================================ S9 review loop (D8, D9, D10)


def _review_task(kind: str) -> str:
    return (f"{kind}. Score this launch film on the rubric (0-10 per dimension). Every score must cite evidence as a "
            "timecode + format. Then list ranked problems (gain / effort) with concrete fixes, each tagged craft, "
            "real-output-bound (limited by what the product actually produced) or missing-asset (needs a new asset). "
            "Contact sheets are tiled: verify on full-res stills before claiming clipping or black frames.")


def review_once(p: Project, d: Decider, it: int) -> dict:
    idx = rv.evidence_pack(p, it)
    imgs = rv.evidence_images(p, idx)
    spec = p.read_json("render/out/spec.json", [])
    evidence_ctx = {"rubric": rv.RUBRIC, "hard_rules": rv.HARD_RULES_REVIEW,
                    "evidence": {k: {kk: vv for kk, vv in v.items() if kk in ("loudness", "dark_frames", "dips")}
                                 for k, v in idx["masters"].items()},
                    "spec": [{"file": r["file"], "pass": r["pass"], "checks": r["checks"]} for r in spec],
                    "images": [str(i.relative_to(p.root)) for i in imgs]}
    self_ctx = {**evidence_ctx, "treatment": p.read_json("research/treatment.json"), "shotlist": p.path("plan/shotlist.md").read_text()
                if p.path("plan/shotlist.md").exists() else ""}
    mine = d.decide(f"D8_self_it{it:02d}", Review, _review_task("D8 SELF-SCORE"), self_ctx, images=imgs)
    # D9: a fresh reviewer sees ONLY the evidence, rubric and hard rules - never the reasoning or treatment.
    fresh_d = Decider(p, mode=d.mode, model=d.model)
    fresh = fresh_d.decide(f"D9_fresh_it{it:02d}", Review,
                           _review_task("D9 FRESH REVIEW (you are an independent reviewer; spawn-fresh context)"),
                           evidence_ctx, images=imgs)
    merged = rv.merge(mine, fresh)
    return {"evidence": idx, "self": mine.model_dump(), "fresh": fresh.model_dump(), "merged": merged}


def _claim_stills(p: Project, it: int, issues: list[dict]) -> list[Path]:
    """Full-res stills at every claimed timecode, so the fix planner can verify claims before acting."""
    out = []
    for iss in issues[:10]:
        m = re.search(r"(\d+):(\d+(?:\.\d+)?)", iss.get("timecode", ""))
        fm = re.search(r"(16x9|9x16|4x5|5x4)", iss.get("timecode", ""))
        cm = re.search(r"\b(" + "|".join(c.name for c in p.brief.cuts) + r")\b", iss.get("timecode", ""))
        if not m:
            continue
        sec = int(m.group(1)) * 60 + float(m.group(2))
        cut = cm.group(1) if cm else p.brief.cuts[0].name
        fmt = fm.group(1) if fm else "16x9"
        src = p.path("render/out", f"{cut}-{fmt}.mp4")
        if src.exists():
            out.append(media.still_at(src, sec, rv.iteration_dir(p, it) / "claims" / f"{iss['id']}.jpg"))
    return out


def s9_review(p: Project, d: Decider, iterations: Optional[int] = None, render: Callable = None, **_) -> dict:
    b = p.brief
    state = p.state()
    it = state.get("iteration", 0) + 1
    max_it = iterations or b.budgets.max_iterations
    best = max((r["total"] for r in rv.scoreboard_rows(p)), default=None)
    history = []
    while it <= max_it:
        r = review_once(p, d, it)
        merged = r["merged"]
        itdir = rv.iteration_dir(p, it)
        shutil.copyfile(p.path("plan/timeline.json"), itdir / "timeline.json")
        decision = "keep"
        if best is not None and merged["total"] < best:
            # Score dropped: revert to the best timeline and log why.
            best_it = max(rv.scoreboard_rows(p), key=lambda x: x["total"])["iteration"]
            shutil.copyfile(p.path("review", f"it{best_it:02d}", "timeline.json"), p.path("plan/timeline.json"))
            decision = f"revert to it{best_it:02d} ({merged['total']} < {best})"
        record = {"iteration": it, "total": merged["total"], "dimensions": merged["dimensions"],
                  "blocking": merged["blocking"], "decision": decision}
        (itdir / "scores.json").write_text(json.dumps(record, indent=2))
        (itdir / "review.json").write_text(json.dumps({"self": r["self"], "fresh": r["fresh"], "merged": merged}, indent=2))
        rv.write_scoreboard(p)
        prev_best = best
        best = merged["total"] if best is None else max(best, merged["total"])
        st = p.state()
        st["iteration"] = it
        p.save_state(st)
        history.append(record)
        if merged["total"] >= b.budgets.target_score:
            p.commit(f"iteration {it:02d} (score {prev_best} -> {merged['total']}): target reached")
            break
        if it >= max_it:
            # Last iteration: don't plan a fix nobody will score. If we reverted, the masters must match again.
            if decision.startswith("revert"):
                (render or s8_render)(p, d)
            p.commit(f"iteration {it:02d} (score {prev_best} -> {merged['total']}): iteration budget used")
            break
        stuck = rv.stuck_dimensions(p)
        claims = _claim_stills(p, it, merged["issues"])
        task = ("D10 FIX PLAN. Decide which ranked fixes to apply this iteration. VERIFY every reviewer claim against "
                "the full-res claim stills (images) first - tiled contact sheets cause false claims; skip unverified "
                "ones. Express fixes as JSON-pointer ops on timeline.json (scene ids may be used in paths, e.g. "
                "/cuts/hero/scenes/s07/props/headlines) or as re-capture requests. If a dimension is stuck for 2 "
                "iterations, change the APPROACH (new shot type, layout or asset), not parameters. If the ceiling is "
                "real-output-bound or a missing asset, say what you need in needs_asset instead of looping.")
        fp = d.decide(f"D10_fix_it{it:02d}", FixPlan, task,
                      {"merged_review": merged, "stuck_dimensions": stuck, "timeline": p.read_json("plan/timeline.json"),
                       "scene_catalogue": SCENE_CATALOGUE, "claim_stills": [c.name for c in claims]}, images=claims,
                      validator=lambda x: _patch_errors(p, x))
        (itdir / "fixplan.json").write_text(fp.model_dump_json(indent=2))
        _write_iteration_md(p, it, record, fp)
        if fp.needs_asset and not fp.patch and not fp.recapture:
            p.commit(f"iteration {it:02d} (score {prev_best} -> {merged['total']}): blocked on assets")
            return {"history": history, "stopped": "needs_asset", "needs_asset": fp.needs_asset}
        new = _apply_fix(p, fp)
        p.write_json("plan/timeline.json", new)
        if fp.recapture:
            p.write_json(f"review/it{it:02d}/recapture.json", [x.model_dump() for x in fp.recapture])
            s4_capture(p, d, only=[x.take for x in fp.recapture])
            s6_prep(p, d)
        _debug_stills(p, it, fp)
        p.commit(f"iteration {it:02d} (score {prev_best} -> {merged['total']})")
        (render or s8_render)(p, d)
        it += 1
    return {"history": history, "best": best}


def _apply_fix(p: Project, fp: FixPlan) -> dict:
    doc = planmod.apply_patch(p.read_json("plan/timeline.json"), fp.patch)
    for ct in doc["cuts"]:
        planmod.retime(doc, ct["name"])
    return doc


def _patch_errors(p: Project, fp: FixPlan) -> list[str]:
    try:
        doc = _apply_fix(p, fp)
        tl = Timeline.model_validate(doc)
    except Exception as e:  # noqa: BLE001 - surfaced to the LLM for a retry
        return [f"patch does not apply: {e}"]
    return validate_timeline(tl, p.brief)


def _debug_stills(p: Project, it: int, fp: FixPlan) -> None:
    """Render debug stills of the changed scenes before the full re-render."""
    ids = set()
    for op in fp.patch:
        m = re.search(r"/scenes/([^/]+)", op.path)
        if m:
            ids.add(m.group(1))
    if not ids:
        return
    tl = p.timeline
    jobs = []
    for ct in tl.cuts:
        frames = [s.from_ + s.duration // 2 for i, s in enumerate(ct.scenes) if s.id in ids or str(i) in ids]
        if frames:
            jobs += [{"comp": f"{ct.name}-{fmt}", "frames": frames} for fmt in ct.formats]
    if jobs:
        with AssetServer(p.root) as srv:
            props = rem.write_props(p, srv.url, debug=True)
            rem.render_stills(p, props, jobs, rv.iteration_dir(p, it) / "debug", scale=0.5)


def _write_iteration_md(p: Project, it: int, record: dict, fp: FixPlan) -> None:
    lines = [f"# Iteration {it:02d}", "", f"Total: **{record['total']}** ({record['decision']})", "",
             "## Scores", *[f"- {k}: {v}" for k, v in record["dimensions"].items()], "",
             "## Fix plan", f"Applied: {fp.apply}", f"Skipped: {fp.skip}", f"Approach change: {fp.approach_change or '-'}",
             f"Needs asset: {fp.needs_asset or '-'}", "", fp.rationale]
    p.path("review", f"iteration-{it:02d}.md").write_text("\n".join(lines) + "\n")


# ============================================================================ S10 handover (D11)


def s10_handover(p: Project, d: Decider, **_) -> dict:
    out = p.path("render/out")
    files = sorted(f.name for f in out.iterdir() if f.suffix in (".mp4", ".png", ".srt", ".md"))
    rows = rv.scoreboard_rows(p)
    note = d.decide("D11_director_note", DirectorNote,
                    "D11 DIRECTOR'S NOTE. Markdown: the creative choices, honest remaining weaknesses, which file goes on "
                    "which platform, and a first-line caption per platform.",
                    {"files": files, "scores": rows[-3:], "costs": p.costs(), "treatment": p.read_json("research/treatment.json")})
    p.path("DIRECTORS_NOTE.md").write_text(note.markdown)
    p.path("HANDOVER.md").write_text("\n".join([
        f"# {p.brief.project} - handover", "", "## Deliverables", *[f"- render/out/{f}" for f in files], "",
        "## Evidence", "- render/out/spec-table.md", "- review/SCOREBOARD.md", "- logs/capture-log.md", "- CREDITS.md",
        "- DIRECTORS_NOTE.md", "", "## Costs", *[f"- {k}: {v}" for k, v in p.costs().items()], ""]))
    return {"files": files}


# ============================================================================ orchestration


STAGE_FUNCS: dict[str, Callable] = {
    "S0": s0_init, "S1": s1_treatment, "S2": s2_beats, "S3": s3_storyboard, "S4": s4_capture, "S5": s5_audio,
    "S6": s6_prep, "S7": s7_compose, "S8": s8_render, "S9": s9_review, "S10": s10_handover,
}
STAGE_NAMES = {"S0": "init", "S1": "treatment", "S2": "beats", "S3": "storyboard", "S4": "capture", "S5": "audio",
               "S6": "prep", "S7": "compose", "S8": "render", "S9": "review", "S10": "handover"}
STAGE_INPUTS = {
    "S1": ["brief.yaml", "brand.json"], "S2": ["brief.yaml", "research/treatment.json"],
    "S3": ["plan/timeline.json", "brand.json"], "S4": ["plan/beats.json", "capture.yaml"],
    "S5": ["plan/beats.json", "brief.yaml"], "S6": ["capture"], "S7": ["plan/timeline.json", "assets/manifest.yaml"],
}


def resolve(stage: str) -> str:
    s = stage.upper() if stage.upper() in STAGE_FUNCS else next((k for k, v in STAGE_NAMES.items() if v == stage.lower()), None)
    if not s:
        raise KeyError(f"unknown stage {stage}; use S0..S10 or {list(STAGE_NAMES.values())}")
    return s


def run_stage(p: Project, stage: str, d: Optional[Decider] = None, force: bool = False, **opts) -> dict:
    s = resolve(stage)
    d = d or Decider(p)
    inputs = [p.path(x) for x in STAGE_INPUTS.get(s, [])]
    h = hash_files(inputs) + sha(opts) if inputs else ""
    if h and not force and p.stage_fresh(s, h):
        return {"stage": s, "status": "cached"}
    p.mark(s, "running", h)
    try:
        res = STAGE_FUNCS[s](p, d, **opts)
    except DecisionPending as e:
        p.mark(s, "awaiting_decision", h, decision=e.decision_id, request=str(e.request_path.relative_to(p.root)))
        raise
    except Exception as e:
        p.mark(s, "failed", h, error=str(e)[:2000])
        raise
    p.mark(s, "done", h, result=res)
    p.commit(f"{s} {STAGE_NAMES[s]}")
    return {"stage": s, "status": "done", "result": res}


def run_pipeline(p: Project, start: str = "S0", end: str = "S10", skip: tuple[str, ...] = (), **opts) -> list[dict]:
    order = list(STAGES)
    a, b = order.index(resolve(start)), order.index(resolve(end))
    out = []
    d = Decider(p)
    for s in order[a: b + 1]:
        if s in skip:
            out.append({"stage": s, "status": "skipped"})
            continue
        out.append(run_stage(p, s, d, **opts.get(s, {})))
    return out
