"""Text -> skeletal motion (SOMA-77, see soma.py) behind one interface.

Backends
--------
* ``KimodoBackend``  - the real thing: NVIDIA Kimodo (`kimodo_gen`), arbitrary text.
  Needs the Kimodo install + weights (see README). Multi-prompt is native in Kimodo, so a
  sentence like "walk forward, jump and do a backflip" becomes three prompts with
  durations and Kimodo blends them.
* ``ClipLibraryBackend`` - offline stand-in used by the proof of concept: picks the
  closest pre-generated Kimodo clip per prompt segment and stitches them (heading +
  position aligned, crossfaded). Same output format, so the rest of the pipeline is
  exercised for real. "flip" segments are synthesised from a jump (clearly a stand-in).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .soma import IDX, axis_angle, load_motion, slerp_mats

# ---------------------------------------------------------------- prompt planning

_IRREGULAR = {"do": "does", "go": "goes", "be": "is", "have": "has"}
_LEAD = re.compile(r"^(please\s+)?(make|have|let|get)\s+(this|the|my)?\s*(character|guy|girl|person|model|him|her|it)\s+(to\s+)?", re.I)


def _third_person(verb: str) -> str:
    v = verb.lower()
    if v in _IRREGULAR:
        return _IRREGULAR[v]
    if v.endswith(("s", "sh", "ch", "x", "z", "o")):
        return v + "es"
    if v.endswith("y") and len(v) > 2 and v[-2] not in "aeiou":
        return v[:-1] + "ies"
    return v + "s"


@dataclass
class Segment:
    prompt: str      # Kimodo-style: "A person walks forward."
    seconds: float


_DURATION = [("backflip", 2.2), ("flip", 2.2), ("cartwheel", 2.5), ("jump", 2.0), ("hop", 1.5),
             ("walk", 3.0), ("run", 2.5), ("jog", 3.0), ("dance", 4.0), ("wave", 2.5),
             ("punch", 1.8), ("kick", 1.8), ("sit", 3.0), ("idle", 3.0), ("turn", 2.0)]


def plan(text: str, default_seconds: float = 2.5) -> list[Segment]:
    """Split a free-form instruction into ordered Kimodo prompts with durations.

    Kimodo's docs: start prompts with "A person ...", one or two behaviours each, and
    generate long sequences as several prompts in sequence.
    """
    t = _LEAD.sub("", text.strip())
    parts = re.split(r"\s*(?:,|;|\.|\bthen\b|\band then\b|\bafter that\b|\band\b)\s*", t, flags=re.I)
    segs = []
    for p in parts:
        p = re.sub(r"^(to|and|then|finally)\s+", "", p.strip(), flags=re.I).strip()
        if not p:
            continue
        if re.match(r"^(a|the)\s+(person|man|woman|character)\b", p, re.I):
            sentence = p[0].upper() + p[1:]
        else:
            words = p.split()
            sentence = "A person " + " ".join([_third_person(words[0])] + words[1:])
        sentence = sentence.rstrip(".") + "."
        secs = next((s for k, s in _DURATION if k in sentence.lower()), default_seconds)
        segs.append(Segment(sentence, secs))
    if not segs:
        raise ValueError(f"no motion found in prompt: {text!r}")
    return segs


# ---------------------------------------------------------------- backends

class KimodoBackend:
    """Runs `kimodo_gen` (NVIDIA Kimodo, Apache-2.0 code; SOMA weights under NVIDIA Open
    Model License). On Apple Silicon set device="mps" only after applying the one-line
    device patch described in the README; otherwise it runs on CPU."""

    def __init__(self, model: str = "Kimodo-SOMA-RP-v1.2", exe: str | None = None,
                 seed: int = 1, text_encoder_device: str | None = None, diffusion_steps: int = 100):
        self.model, self.seed, self.steps = model, seed, diffusion_steps
        self.exe = exe or shutil.which("kimodo_gen")
        self.text_encoder_device = text_encoder_device
        if not self.exe:
            raise RuntimeError("kimodo_gen not found - install Kimodo (README step 3) or use --motion clips")

    def generate(self, segs: list[Segment], out_stem: Path) -> dict:
        env = dict(os.environ)
        if self.text_encoder_device:
            env["TEXT_ENCODER_DEVICE"] = self.text_encoder_device
        cmd = [self.exe, " ".join(s.prompt for s in segs),
               "--model", self.model,
               "--duration", " ".join(f"{s.seconds:g}" for s in segs),
               "--diffusion_steps", str(self.steps),
               "--seed", str(self.seed), "--output", str(out_stem)]
        print("[kimodo]", " ".join(repr(c) if " " in c else c for c in cmd))
        subprocess.run(cmd, check=True, env=env)
        return load_motion(f"{out_stem}.npz")


class ClipLibraryBackend:
    """Offline stand-in: nearest pre-generated Kimodo clip per segment, then stitch."""

    def __init__(self, clip_dir: Path):
        self.dir = Path(clip_dir)
        meta = json.loads((self.dir / "presets.json").read_text())
        self.clips = {p["id"]: p["prompt"] for p in meta["presets"]
                      if (self.dir / f"{p['id']}.npz").exists()}
        if not self.clips:
            raise RuntimeError(f"no clips in {self.dir}")

    @staticmethod
    def _words(s: str) -> set[str]:
        return {w.rstrip("s") for w in re.findall(r"[a-z]+", s.lower())} - {"a", "person", "the", "and"}

    def pick(self, prompt: str) -> tuple[str, bool]:
        """(clip id, is_flip). Flips are built from the jump clip."""
        flip = bool(re.search(r"\b(back)?flip|somersault", prompt, re.I))
        if flip and "jump" in self.clips:
            return "jump", True
        w = self._words(prompt)
        best = max(self.clips, key=lambda c: (len(w & self._words(self.clips[c] + " " + c)), -len(c)))
        if not w & self._words(self.clips[best] + " " + best):
            print(f"[clips] WARNING no clip matches {prompt!r}; using {best!r}")
        return best, False

    def generate(self, segs: list[Segment], out_stem: Path | None = None) -> dict:
        parts = []
        for s in segs:
            cid, flip = self.pick(s.prompt)
            m = load_motion(self.dir / f"{cid}.npz")
            m = trim(m, s.seconds)
            if flip:
                m = add_backflip(m)
            print(f"[clips] {s.prompt!r} -> {cid}.npz{' + synthetic backflip' if flip else ''} "
                  f"({len(m['hips'])} frames)")
            parts.append(m)
        return stitch(parts)


# ---------------------------------------------------------------- clip maths

def trim(m: dict, seconds: float) -> dict:
    n = min(len(m["hips"]), max(2, int(round(seconds * m["fps"]))))
    return {**m, "global_rot_mats": m["global_rot_mats"][:n], "hips": m["hips"][:n]}


def heading(g_hips: np.ndarray) -> float:
    """Yaw (about +Y) of the hips' forward (+Z) axis."""
    f = g_hips @ np.array([0.0, 0, 1])
    return float(np.arctan2(f[0], f[2]))


def stitch(parts: list[dict], blend: int = 8) -> dict:
    """Concatenate clips: each next clip is turned (yaw) and moved so it starts where and
    facing the way the previous one ended, then the seam is crossfaded."""
    out = {k: v for k, v in parts[0].items()}
    for nxt in parts[1:]:
        g_prev, h_prev = out["global_rot_mats"], out["hips"]
        g, h = nxt["global_rot_mats"], nxt["hips"]
        yaw = heading(g_prev[-1, 0]) - heading(g[0, 0])
        r = axis_angle([0, 1, 0], yaw)
        g = np.einsum("ij,tkjl->tkil", r, g)
        h = (h - h[0]) @ r.T
        h[:, 1] += nxt["hips"][0, 1]          # keep the clip's own absolute height (same floor)
        h[:, [0, 2]] += h_prev[-1, [0, 2]]    # start where the previous clip ended
        n = min(blend, len(g_prev), len(g))
        for i in range(n):  # crossfade the last n frames of prev into the first n of next
            t = (i + 1) / (n + 1)
            g_prev[-n + i] = slerp_mats(g_prev[-n + i], g[i], t)
            h_prev[-n + i] = (1 - t) * h_prev[-n + i] + t * h[i]
        out["global_rot_mats"] = np.concatenate([g_prev, g[n:]])
        out["hips"] = np.concatenate([h_prev, h[n:]])
    return out


def add_backflip(m: dict, height_gain: float = 0.9) -> dict:
    """Stand-in backflip from a jump clip: during the airborne phase rotate the whole body
    -360 deg about the character's left axis (backwards) and lift the arc. Not a model
    output - with Kimodo installed the real model is asked for the flip instead."""
    g, h = m["global_rot_mats"].copy(), m["hips"].copy()
    y = h[:, 1]
    ground = np.percentile(y, 20)
    air = np.where(y > ground + 0.6 * (y.max() - ground))[0]
    if len(air) < 3:
        return m
    a, b = air[0], air[-1]
    pad = max(3, (b - a) // 2)
    a, b = max(0, a - pad), min(len(y) - 1, b + pad)
    left = g[a, 0] @ np.array([1.0, 0, 0])  # hips' left axis at take-off
    for t in range(a, b + 1):
        u = (t - a) / (b - a)
        s = u * u * (3 - 2 * u)  # smoothstep
        r = axis_angle(left, -2 * np.pi * s)
        g[t] = np.einsum("ij,kjl->kil", r, g[t])
        h[t, 1] += height_gain * np.sin(np.pi * u)
    return {**m, "global_rot_mats": g, "hips": h}
