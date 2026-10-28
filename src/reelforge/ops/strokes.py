"""Stroke designer: sketches are code. Primitives in normalised 0..1 canvas space, humanised with seeded wobble,
sampled with slow-in/slow-out spacing. capture.mjs replays them as real pointer input.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
from PIL import Image, ImageDraw

Pt = tuple[float, float]


def _ease(n: int) -> np.ndarray:
    """Slow-in/slow-out parameter spacing."""
    t = np.linspace(0, 1, n)
    return 0.5 - 0.5 * np.cos(np.pi * t)


def bezier(p0: Pt, p1: Pt, p2: Pt, p3: Pt, n: int = 40) -> np.ndarray:
    t = _ease(n)[:, None]
    P = [np.array(p) for p in (p0, p1, p2, p3)]
    return ((1 - t) ** 3) * P[0] + 3 * ((1 - t) ** 2) * t * P[1] + 3 * (1 - t) * t * t * P[2] + t ** 3 * P[3]


def ellipse(c: Pt, rx: float, ry: float, start: float = 0.0, sweep: float = 2 * math.pi + 0.25, n: int = 60) -> np.ndarray:
    a = start + _ease(n) * sweep
    return np.stack([c[0] + rx * np.cos(a), c[1] + ry * np.sin(a)], axis=1)


def polyline(pts: Iterable[Pt], per_seg: int = 14) -> np.ndarray:
    pts = [np.array(p, dtype=float) for p in pts]
    out = [pts[0][None]]
    for a, b in zip(pts, pts[1:]):
        t = _ease(per_seg)[1:, None]
        out.append(a + (b - a) * t)
    return np.concatenate(out)


def humanise(path: np.ndarray, seed: int, amp: float = 0.0025, freq: float = 3.0) -> np.ndarray:
    """Seeded low-frequency wobble perpendicular to the path. Same seed -> same stroke."""
    rng = np.random.default_rng(seed)
    if len(path) < 3:
        return path
    d = np.gradient(path, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
    s = np.linspace(0, 1, len(path))
    ph = rng.uniform(0, 2 * np.pi, 3)
    w = sum(np.sin(2 * np.pi * freq * (k + 1) * s + ph[k]) / (k + 1) for k in range(3))
    return path + nrm * (amp * w)[:, None]


def build(primitives: list[dict], seed: int = 7) -> list[list[Pt]]:
    """primitives: [{type: bezier|ellipse|line|polyline, ...}] -> list of strokes (each a point list)."""
    strokes = []
    for i, pr in enumerate(primitives):
        t = pr["type"]
        if t == "bezier":
            p = bezier(*pr["pts"], n=pr.get("n", 40))
        elif t == "ellipse":
            p = ellipse(tuple(pr["c"]), pr["rx"], pr.get("ry", pr["rx"]), pr.get("start", -math.pi / 2),
                        pr.get("sweep", 2 * math.pi + 0.25), n=pr.get("n", 60))
        elif t in ("line", "polyline"):
            p = polyline(pr["pts"], per_seg=pr.get("per_seg", 14))
        else:
            raise ValueError(f"unknown primitive {t}")
        if pr.get("wobble", True):
            p = humanise(p, seed + i, amp=pr.get("amp", 0.0025))
        strokes.append([(round(float(x), 5), round(float(y), 5)) for x, y in np.clip(p, 0, 1)])
    return strokes


TEMPLATES: dict[str, list[dict]] = {
    # A generic, unbranded sedan side profile.
    "sedan_side": [
        {"type": "polyline", "pts": [(0.10, 0.62), (0.12, 0.52), (0.30, 0.48), (0.40, 0.36), (0.62, 0.35),
                                     (0.74, 0.47), (0.88, 0.50), (0.90, 0.62)]},
        {"type": "line", "pts": [(0.10, 0.62), (0.21, 0.62)]},
        {"type": "line", "pts": [(0.35, 0.62), (0.66, 0.62)]},
        {"type": "line", "pts": [(0.80, 0.62), (0.90, 0.62)]},
        {"type": "ellipse", "c": (0.28, 0.63), "rx": 0.065, "ry": 0.09},
        {"type": "ellipse", "c": (0.73, 0.63), "rx": 0.065, "ry": 0.09},
        {"type": "polyline", "pts": [(0.42, 0.38), (0.50, 0.38), (0.50, 0.47), (0.33, 0.47)], "per_seg": 10},
        {"type": "polyline", "pts": [(0.53, 0.38), (0.61, 0.38), (0.69, 0.47), (0.53, 0.47)], "per_seg": 10},
    ],
}


def from_parts(parts: list[dict], image_size: tuple[int, int], style: str = "trace") -> list[dict]:
    """D4 output (pixel coords on out.jpg) -> primitives in normalised space."""
    W, H = image_size
    prims = []
    for part in parts:
        pts = [(x / W, y / H) for x, y in part["points"]]
        if part["kind"] == "circle":
            prims.append({"type": "ellipse", "c": pts[0], "rx": part["radius"] / W, "ry": part["radius"] / H})
        elif part["kind"] in ("line", "polyline"):
            prims.append({"type": "polyline", "pts": pts})
        elif part["kind"] == "point":
            x, y = pts[0]
            prims.append({"type": "ellipse", "c": (x, y), "rx": 0.01, "ry": 0.01 * W / H})
    return prims


def thrusters(anchor_px: list[tuple[float, float]], image_size: tuple[int, int], length: float = 0.08) -> list[dict]:
    """Downward flame-cone sketches under each wheel anchor."""
    W, H = image_size
    prims = []
    for x, y in anchor_px:
        cx, cy = x / W, y / H
        prims.append({"type": "polyline", "pts": [(cx - 0.03, cy), (cx, cy + length), (cx + 0.03, cy)]})
        prims.append({"type": "ellipse", "c": (cx, cy), "rx": 0.035, "ry": 0.012})
    return prims


def preview(strokes: list[list[Pt]], out: Path, base: Optional[Path] = None, size: tuple[int, int] = (1024, 1024),
            colour: str = "#D4F77C", width: int = 5) -> Path:
    """Draw strokes over the real image for a vision check before spending credits."""
    im = Image.open(base).convert("RGB") if base else Image.new("RGB", size, (245, 245, 240))
    W, H = im.size
    d = ImageDraw.Draw(im)
    for s in strokes:
        d.line([(x * W, y * H) for x, y in s], fill=colour, width=width, joint="curve")
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


def save(strokes: list[list[Pt]], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"space": "normalised", "strokes": strokes}))
    return out
