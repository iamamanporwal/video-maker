"""Pixel matching (history order is unstable: select by content, never by position) and simple image stats."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def _sig(img: Image.Image, size: int = 32) -> np.ndarray:
    a = np.asarray(img.convert("L").resize((size, size), Image.BILINEAR), dtype=np.float32)
    a = a - a.mean()
    return a / (np.linalg.norm(a) + 1e-6)


def similarity(a: Path | Image.Image, b: Path | Image.Image) -> float:
    ia = a if isinstance(a, Image.Image) else Image.open(a)
    ib = b if isinstance(b, Image.Image) else Image.open(b)
    return float((_sig(ia) * _sig(ib)).sum())


def find_image(ref: Path, candidates: list[Path], min_score: float = 0.9) -> dict:
    """Return the candidate that pixel-matches ref (normalised cross-correlation on a 32x32 signature)."""
    scores = sorted(((similarity(ref, c), str(c)) for c in candidates), reverse=True)
    best = scores[0] if scores else (0.0, None)
    return {"best": best[1] if best[0] >= min_score else None, "score": round(best[0], 4),
            "ranking": [{"file": f, "score": round(s, 4)} for s, f in scores[:5]]}


def find_in_screenshot(ref: Path, screenshot: Path, boxes: list[tuple[int, int, int, int]]) -> dict:
    """Given candidate boxes (x, y, w, h) on a screenshot (e.g. history thumbnails), return the index matching ref."""
    shot = Image.open(screenshot)
    crops = [shot.crop((x, y, x + w, y + h)) for x, y, w, h in boxes]
    scores = [similarity(ref, c) for c in crops]
    i = int(np.argmax(scores)) if scores else -1
    return {"index": i, "score": round(scores[i], 4) if i >= 0 else 0.0, "scores": [round(s, 4) for s in scores]}


def dominant_colours(path: Path, k: int = 5) -> list[str]:
    im = Image.open(path).convert("RGB").resize((96, 96))
    q = im.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: k * 3]
    counts = sorted(q.getcolors(), reverse=True)
    return ["#%02X%02X%02X" % tuple(pal[i * 3: i * 3 + 3]) for _, i in counts[:k]]


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    def lum(h: str) -> float:
        rgb = [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    la, lb = sorted((lum(hex_a), lum(hex_b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)
