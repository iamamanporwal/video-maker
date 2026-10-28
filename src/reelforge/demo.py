"""Offline demo project: synthetic capture take, music, SFX and GLB so the ops chain
(takes -> compose -> render -> master -> verify -> evidence) can be exercised without API keys or a live app.

Everything here is a clearly-labelled TEST FIXTURE, not product footage.
"""

from __future__ import annotations

import json
import math
import struct
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .ops import strokes
from .plan import beats_to_timeline
from .project import Project
from .schemas import BeatsDoc
from .validate import validate_beats, validate_timeline

BRIEF = """\
project: demo
genre: product-launch
product:
  name: Demo3D
  url: http://localhost:8080
  auth: { method: none }
idea: "An artist sketches a car; the app turns it into an image, then a 3D model."
story:
  - "2:47 AM, impossible request"
  - "Sketch becomes an image"
  - "Image becomes 3D"
tagline: "Catch more sleep."
setting: "dark late-night room, cold monitor glow"
cuts:
  - { name: hero, seconds: 12, formats: [16x9, 9x16, 4x5] }
  - { name: social, seconds: 6, formats: [9x16], hook_seconds: 1.5 }
music: { bpm: 120, mood: "minimal electronic" }
budgets: { app_credits: 100, fal_usd: 0, max_iterations: 2, target_score: 9.0 }
rules:
  trademark_avoid: ["BMW"]
"""

SR = 48000


def _font(size: int):
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Menlo.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# --------------------------------------------------------------------------- synthetic take


def _car_image(size=(768, 768), seed=1) -> Image.Image:
    rng = np.random.default_rng(seed)
    W, H = size
    y = np.linspace(0, 1, H)[:, None, None]
    bg = (np.array([24, 28, 34]) * (1 - y) + np.array([60, 66, 74]) * y).astype(np.uint8)
    im = Image.fromarray(np.repeat(bg, W, axis=1))
    d = ImageDraw.Draw(im)
    body = [(0.10, 0.62), (0.12, 0.52), (0.30, 0.48), (0.40, 0.36), (0.62, 0.35), (0.74, 0.47), (0.88, 0.50), (0.90, 0.62)]
    d.polygon([(x * W, yv * H) for x, yv in body], fill=(176, 40, 46))
    d.polygon([(0.42 * W, 0.38 * H), (0.50 * W, 0.38 * H), (0.50 * W, 0.47 * H), (0.33 * W, 0.47 * H)], fill=(40, 52, 64))
    d.polygon([(0.53 * W, 0.38 * H), (0.61 * W, 0.38 * H), (0.69 * W, 0.47 * H), (0.53 * W, 0.47 * H)], fill=(40, 52, 64))
    for cx in (0.28, 0.73):
        d.ellipse([(cx - 0.065) * W, 0.54 * H, (cx + 0.065) * W, 0.72 * H], fill=(18, 18, 20), outline=(120, 120, 128), width=4)
    noise = rng.normal(0, 4, (H, W, 3))
    return Image.fromarray(np.clip(np.asarray(im, dtype=float) + noise, 0, 255).astype(np.uint8))


def _app_frame(t: float, sketch: list[list[tuple[float, float]]], progress: float, result: Image.Image | None) -> Image.Image:
    """A synthetic 'app' screen, labelled as a fixture."""
    W, H = 1920, 1080
    im = Image.new("RGB", (W, H), (22, 24, 23))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 64], fill=(30, 33, 31))
    d.text((24, 18), "DEMO FIXTURE - synthetic app", fill=(200, 205, 195), font=_font(26))
    d.rectangle([0, 64, 300, H], fill=(27, 29, 28))
    for i, lbl in enumerate(["Draw", "Erase", "Generate", "To 3D"]):
        d.rounded_rectangle([24, 100 + i * 70, 276, 150 + i * 70], 10, fill=(40, 44, 41))
        d.text((44, 112 + i * 70), lbl, fill=(220, 225, 215), font=_font(24))
    cx0, cy0, cs = 420, 120, 860
    d.rectangle([cx0, cy0, cx0 + cs, cy0 + cs], fill=(245, 245, 240))
    total = sum(len(s) for s in sketch)
    n = int(total * progress)
    for s in sketch:
        pts = s[: max(0, n)]
        n -= len(s)
        if len(pts) > 1:
            d.line([(cx0 + x * cs, cy0 + y * cs) for x, y in pts], fill=(20, 20, 20), width=5, joint="curve")
    d.rounded_rectangle([1320, 120, 1880, 1000], 12, fill=(30, 33, 31))
    if result is not None:
        im.paste(result.resize((520, 520)), (1340, 300))
    else:
        d.text((1360, 520), "waiting..." if progress >= 1 else "", fill=(140, 146, 136), font=_font(28))
    d.text((1340, 140), f"t={t:5.2f}s", fill=(140, 146, 136), font=_font(22))
    return im


def make_take(p: Project, take: str = "demo_sketch", seconds: float = 8.0, fps: int = 15) -> None:
    out = p.path("capture", take)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    sk = strokes.build(strokes.TEMPLATES["sedan_side"], seed=3)
    result = _car_image()
    result.save(out / "out.jpg", quality=92)
    frames, mouse, events = [], [], [{"t": 0, "name": "recordStart"}]
    draw_end, gen_at, ready_at = 4.0, 4.6, 6.2
    total = sum(len(s) for s in sk)
    flat = [(x, y, i == 0) for s in sk for i, (x, y) in enumerate(s)]
    cx0, cy0, cs = 420, 120, 860
    for i in range(int(seconds * fps)):
        t = i / fps
        prog = min(1.0, t / draw_end)
        res = result if t >= ready_at else None
        _app_frame(t, sk, prog, res).resize((1920, 1080)).save(out / "frames" / f"f_{i:06d}.jpg", quality=80)
        frames.append({"t": int(t * 1000), "file": f"f_{i:06d}.jpg"})
    for k, (x, y, first) in enumerate(flat):
        t = k / total * draw_end
        mouse.append({"t": int(t * 1000), "x": cx0 + x * cs, "y": cy0 + y * cs, "down": not first})
    mouse.append({"t": int(gen_at * 1000) - 300, "x": 150, "y": 255, "down": False})
    mouse.append({"t": int(gen_at * 1000), "x": 150, "y": 265, "down": False})
    events += [{"t": int(draw_end * 1000), "name": "strokeEnd"},
               {"t": int(gen_at * 1000), "name": "click", "x": 150, "y": 265, "label": "Generate"},
               {"t": int(gen_at * 1000), "name": "generateClicked"},
               {"t": int(ready_at * 1000), "name": "imageReady", "waitMs": int((ready_at - gen_at) * 1000)},
               {"t": int(seconds * 1000), "name": "recordEnd"}]
    (out / "frames.json").write_text(json.dumps(frames))
    (out / "mouse.json").write_text(json.dumps(mouse))
    (out / "events.json").write_text(json.dumps(events))
    (out / "take.json").write_text(json.dumps({"take": take, "ok": True, "viewport": {"width": 1920, "height": 1080},
                                               "dpr": 1, "frames": len(frames), "fixture": True}))
    # The "before" for before/after is the sketch itself.
    strokes.preview(sk, out / "sketch.png", size=(768, 768), colour="#141414", width=6)


# --------------------------------------------------------------------------- GLB


def _box(cx, cy, cz, sx, sy, sz):
    v = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=np.float32) * [sx / 2, sy / 2, sz / 2] + [cx, cy, cz]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    P, N, I = [], [], []
    for f in faces:
        a, b, c = v[f[0]], v[f[1]], v[f[2]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n)
        base = len(P)
        for idx in f:
            P.append(v[idx])
            N.append(n)
        I += [base, base + 1, base + 2, base, base + 2, base + 3]
    return np.array(P), np.array(N), np.array(I)


def _cyl(cx, cy, cz, r, w, seg=24):
    P, N, I = [], [], []
    for side in (-1, 1):
        c = len(P)
        P.append([cx, cy, cz + side * w / 2]); N.append([0, 0, side])
        for k in range(seg + 1):
            a = 2 * math.pi * k / seg
            P.append([cx + r * math.cos(a), cy + r * math.sin(a), cz + side * w / 2]); N.append([0, 0, side])
        for k in range(seg):
            I += [c, c + 1 + k, c + 2 + k] if side > 0 else [c, c + 2 + k, c + 1 + k]
    for k in range(seg + 1):
        a = 2 * math.pi * k / seg
        n = [math.cos(a), math.sin(a), 0]
        for side in (-1, 1):
            P.append([cx + r * n[0], cy + r * n[1], cz + side * w / 2]); N.append(n)
    base = len(P) - 2 * (seg + 1)
    for k in range(seg):
        a0, b0 = base + 2 * k, base + 2 * k + 1
        a1, b1 = base + 2 * k + 2, base + 2 * k + 3
        I += [a0, a1, b0, b0, a1, b1]
    return np.array(P, dtype=np.float32), np.array(N, dtype=np.float32), np.array(I)


def write_glb(path: Path) -> None:
    parts = [  # (geometry, material index)
        (_box(0, 0.35, 0, 4.4, 0.7, 1.8), 0),
        (_box(-0.2, 0.95, 0, 2.2, 0.55, 1.6), 1),
        *[(_cyl(x, 0.33, z, 0.36, 0.3), 2) for x in (-1.4, 1.4) for z in (-0.85, 0.85)],
    ]
    blob, views, accs, prims = b"", [], [], []
    for (P, N, I), mat in parts:
        P, N, I = P.astype(np.float32), N.astype(np.float32), I.astype(np.uint32)
        ids = []
        for arr, target, typ in ((P, 34962, "VEC3"), (N, 34962, "VEC3"), (I, 34963, "SCALAR")):
            pad = (-len(blob)) % 4
            blob += b"\0" * pad
            views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": arr.nbytes, "target": target})
            blob += arr.tobytes()
            acc = {"bufferView": len(views) - 1, "componentType": 5126 if arr.dtype == np.float32 else 5125,
                   "count": int(arr.shape[0]), "type": typ}
            if typ == "VEC3" and len(ids) == 0:
                acc["min"], acc["max"] = P.min(axis=0).tolist(), P.max(axis=0).tolist()
            accs.append(acc)
            ids.append(len(accs) - 1)
        prims.append({"attributes": {"POSITION": ids[0], "NORMAL": ids[1]}, "indices": ids[2], "material": mat})
    gltf = {
        "asset": {"version": "2.0", "generator": "reelforge demo fixture"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "car"}],
        "meshes": [{"primitives": prims}],
        "materials": [
            {"name": "paint", "pbrMetallicRoughness": {"baseColorFactor": [0.69, 0.16, 0.18, 1], "metallicFactor": 0.5, "roughnessFactor": 0.35}},
            {"name": "glass", "pbrMetallicRoughness": {"baseColorFactor": [0.12, 0.16, 0.2, 1], "metallicFactor": 0.1, "roughnessFactor": 0.1}},
            {"name": "tyre", "pbrMetallicRoughness": {"baseColorFactor": [0.05, 0.05, 0.05, 1], "metallicFactor": 0.0, "roughnessFactor": 0.9}},
        ],
        "buffers": [{"byteLength": len(blob)}], "bufferViews": views, "accessors": accs,
    }
    js = json.dumps(gltf).encode()
    js += b" " * ((-len(js)) % 4)
    blob += b"\0" * ((-len(blob)) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(js), b"JSON") + js
                     + struct.pack("<I4s", len(blob), b"BIN\0") + blob)


# --------------------------------------------------------------------------- audio


def _write_mp3(y: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    stereo = np.stack([pcm, pcm], axis=1).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "libmp3lame", "-b:a", "192k", str(path)], input=stereo, check=True)


def synth_music(seconds: float, bpm: int = 120, drop_at: float = 3.0, drop2_at: float | None = None) -> np.ndarray:
    n = int(seconds * SR)
    t = np.arange(n) / SR
    y = 0.05 * np.sin(2 * np.pi * 110 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t))  # pad
    beat = 60 / bpm
    kick = np.exp(-np.arange(int(0.25 * SR)) / (0.04 * SR)) * np.sin(2 * np.pi * 55 * np.arange(int(0.25 * SR)) / SR * (1 + 2 * np.exp(-np.arange(int(0.25 * SR)) / (0.01 * SR))))
    rng = np.random.default_rng(0)
    hat = rng.normal(0, 1, int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / (0.008 * SR))
    for k in range(int(seconds / beat) + 1):
        s = int(k * beat * SR)
        tk = k * beat
        loud = tk >= drop_at and not (drop2_at and drop_at + 4 <= tk < drop2_at - 0.01)
        if loud and s + len(kick) < n:
            y[s:s + len(kick)] += 0.8 * kick
        h = int((k + 0.5) * beat * SR)
        if loud and h + len(hat) < n:
            y[h:h + len(hat)] += 0.18 * hat
    y[t >= drop_at] += 0.08 * np.sign(np.sin(2 * np.pi * 220 * t[t >= drop_at])) * 0.5
    return y * 0.6


def synth_sfx(kind: str) -> np.ndarray:
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(len(kind))
    if kind == "click":
        return 0.6 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.01)
    if kind == "whoosh":
        nz = rng.normal(0, 1, n)
        return 0.4 * nz * np.sin(np.pi * t / t[-1]) ** 2
    if kind == "impact":
        return 0.9 * np.sin(2 * np.pi * 50 * t) * np.exp(-t / 0.15) + 0.2 * rng.normal(0, 1, n) * np.exp(-t / 0.03)
    return 0.5 * np.sin(2 * np.pi * 880 * t) * np.exp(-t / 0.2)  # ping / chime


# --------------------------------------------------------------------------- beats


def demo_beats() -> dict:
    T = "take:demo_sketch"
    shot = {"take": "demo_sketch", "timeKeys": [[0, 0.3], [60, 4.2], [90, 6.6]],
            "focusKeys": [[0, 380, 90, 940, 940], [60, 380, 90, 940, 940], [72, 1300, 100, 600, 920], [90, 1300, 100, 600, 920]],
            "tag": {"text": "1.6 s - real time", "at": 66}}
    finale = {"glb": f"{T}/model.glb", "tunnel": True,
              "camKeys": [[0, 1.2, 0.3, 1.2, 0, 0.05, 0, 30], [60, -0.9, 0.5, 1.3, 0, 0.1, 0, 32]],
              "carKeys": [[0, 0, 0, 0], [20, 0, 0.2, 0], [60, 0.25, 0.6, -0.05]],
              "thrustKeys": [[0, 0], [10, 1], [60, 1]]}
    return {"bpm": 120, "cuts": [
        {"cut": "hero", "beats": [
            {"id": "s01", "start": 0, "dur": 2, "kind": "cold_open", "headline": "One hour?",
             "props": {"clock": "2:47 AM", "chatAt": 8, "channel": "#3d-team",
                       "messages": [{"from": "dev", "text": "need a car model in 1 hour", "at": 12}]},
             "sfx_hints": ["ping"]},
            {"id": "s02", "start": 2, "dur": 1, "kind": "url_to_logo", "props": {"url": "demo3d.app", "wordmark": "Demo3D", "reflowAt": 10},
             "sfx_hints": ["whoosh"]},
            {"id": "s03", "start": 3, "dur": 3, "kind": "product_shot", "headline": "Sketch it.", "caption": "Draw what you mean",
             "props": shot, "sfx_hints": ["click"]},
            {"id": "s04", "start": 6, "dur": 2, "kind": "before_after", "headline": "Get the *image*",
             "props": {"before": "take:demo_sketch/sketch.png", "after": "take:demo_sketch/out.jpg", "labels": ["sketch", "image"],
                       "wipeKeys": [[0, 0], [8, 0], [40, 1]]}},
            {"id": "s05", "start": 8, "dur": 2, "kind": "finale_3d", "headline": "Then 3D.",
             "props": {**finale, "music_drop": True}, "sfx_hints": ["impact"]},
            {"id": "s06", "start": 10, "dur": 2, "kind": "end_card", "headline": "Catch more sleep.",
             "props": {"wordmark": "Demo3D", "url": "demo3d.app"}},
        ]},
        {"cut": "social", "beats": [
            {"id": "s01", "start": 0, "dur": 1.5, "kind": "product_shot", "headline": "Sketch to 3D",
             "props": {**shot, "timeKeys": [[0, 1.0], [45, 6.6]], "hook_at": 0.5}},
            {"id": "s02", "start": 1.5, "dur": 1.5, "kind": "before_after",
             "props": {"before": "take:demo_sketch/sketch.png", "after": "take:demo_sketch/out.jpg", "labels": ["sketch", "image"],
                       "wipeKeys": [[0, 0], [4, 0], [30, 1]]}},
            {"id": "s03", "start": 3, "dur": 1.5, "kind": "finale_3d", "props": {**finale, "music_drop": True}},
            {"id": "s04", "start": 4.5, "dur": 1.5, "kind": "end_card", "headline": "Catch more sleep.",
             "props": {"wordmark": "Demo3D", "url": "demo3d.app"}},
        ]},
    ]}


def build_demo(root: Path) -> Project:
    here = Path(__file__).resolve().parents[2] / "examples" / "vi3w"
    p = Project.create(root)
    p.path("brief.yaml").write_text(BRIEF)
    if (here / "brand.json").exists():
        p.path("brand.json").write_text((here / "brand.json").read_text())
    make_take(p)
    write_glb(p.path("capture", "demo_sketch", "model.glb"))
    _write_mp3(synth_music(16, drop_at=3.0, drop2_at=11.0), p.path("audio/music/hero.mp3"))
    for k in ("ping", "click", "whoosh", "impact"):
        _write_mp3(synth_sfx(k), p.path("audio/sfx", f"{k}.mp3"))
    p.append_credit("everything in this project is a synthetic test fixture generated by reelforge.demo")
    doc = BeatsDoc.model_validate(demo_beats())
    errs = validate_beats(doc, p.brief)
    if errs:
        raise RuntimeError(errs)
    p.write_json("plan/beats.json", doc)
    tl = beats_to_timeline(doc, p.brief, p.brand.model_dump(mode="json"))
    errs = validate_timeline(tl, p.brief)
    if errs:
        raise RuntimeError(errs)
    p.write_json("plan/timeline.json", tl)
    from .stages import align_music, s6_prep

    s6_prep(p, None)
    align_music(p)
    p.commit("demo fixture")
    return p
