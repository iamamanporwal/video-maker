"""Paid generation providers: fal (queue API: music, video b-roll) and ElevenLabs (SFX).

Budgets are checked before every paid call; every call is logged to costs.jsonl.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

import httpx

from ..project import Project

FAL_QUEUE = "https://queue.fal.run"
ELEVEN = "https://api.elevenlabs.io/v1"
SFX_CONCURRENCY = 4  # ElevenLabs returns 429 above this

# Rough per-call estimates for budget enforcement (override with REELFORGE_EST_<KEY>).
EST_USD = {"music_per_min": 0.8, "video_per_sec": 0.10}


def _est(key: str) -> float:
    return float(os.environ.get(f"REELFORGE_EST_{key.upper()}", EST_USD[key]))


class ProviderError(RuntimeError):
    pass


# --------------------------------------------------------------------------- fal


class Fal:
    def __init__(self, key: Optional[str] = None, poll: float = 3.0, timeout: float = 900):
        self.key = key or os.environ.get("FAL_KEY")
        if not self.key:
            raise ProviderError("FAL_KEY is not set (.env)")
        self.poll, self.timeout = poll, timeout
        self.http = httpx.Client(timeout=120, headers={"Authorization": f"Key {self.key}"})

    def run(self, model: str, payload: dict) -> dict:
        r = self.http.post(f"{FAL_QUEUE}/{model}", json=payload)
        if r.status_code >= 400:
            raise ProviderError(f"fal submit {model}: {r.status_code} {r.text[:400]}")
        sub = r.json()
        t0 = time.time()
        while True:
            st = self.http.get(sub["status_url"]).json()
            if st.get("status") == "COMPLETED":
                break
            if st.get("status") in ("FAILED", "ERROR"):
                raise ProviderError(f"fal {model} failed: {st}")
            if time.time() - t0 > self.timeout:
                raise ProviderError(f"fal {model} timed out after {self.timeout}s")
            time.sleep(self.poll)
        res = self.http.get(sub["response_url"])
        if res.status_code >= 400:
            raise ProviderError(f"fal result {model}: {res.status_code} {res.text[:400]}")
        return res.json()

    def download(self, url: str, dst: Path) -> Path:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r:
            r.raise_for_status()
            with dst.open("wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
        return dst


def _find_url(obj: Any, keys=("audio", "video", "file")) -> Optional[str]:
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, dict) and "url" in v:
                return v["url"]
            if isinstance(v, str) and v.startswith("http"):
                return v
        for v in obj.values():
            u = _find_url(v, keys)
            if u:
                return u
    elif isinstance(obj, list):
        for v in obj:
            u = _find_url(v, keys)
            if u:
                return u
    return None


def gen_music(p: Project, name: str, plan: dict, model: str = "fal-ai/elevenlabs/music") -> Path:
    """plan = {positive_global_styles, negative_global_styles, sections:[{section_name, positive_local_styles,
    negative_local_styles, duration_ms, lines}]}. Uses respect_sections_durations so sections match the edit."""
    secs = sum(s["duration_ms"] for s in plan["sections"]) / 1000
    est = _est("music_per_min") * secs / 60
    p.check_budget("fal", est)
    payload = {"composition_plan": plan, "respect_sections_durations": True}
    res = Fal().run(model, payload)
    url = _find_url(res)
    if not url:
        raise ProviderError(f"no audio url in fal response: {json.dumps(res)[:300]}")
    out = Fal().download(url, p.path("audio/music", f"{name}.mp3"))
    p.path("audio/music", f"{name}.plan.json").write_text(json.dumps(payload, indent=2))
    p.add_cost("fal", est, what="music", name=name, model=model, seconds=secs)
    p.append_credit(f"audio/music/{name}.mp3 - generated music, ElevenLabs Music via fal ({model})")
    return out


def gen_video(p: Project, clip: str, prompt: str, seconds: float, aspect: str,
              model: Optional[str] = None, image_url: Optional[str] = None) -> Path:
    """Non-product b-roll only. Saves prompt.json next to the clip and labels it generated in CREDITS.md."""
    model = model or os.environ.get("REELFORGE_FAL_VIDEO_MODEL") or p.brief.providers.get("video", "").removeprefix("fal:")
    if not model or "<" in model:
        raise ProviderError("set providers.video in brief.yaml (e.g. fal:fal-ai/kling-video/...) or REELFORGE_FAL_VIDEO_MODEL")
    est = _est("video_per_sec") * seconds
    p.check_budget("fal", est)
    payload: dict[str, Any] = {"prompt": prompt, "duration": str(int(round(seconds))), "aspect_ratio": aspect}
    if image_url:
        payload["image_url"] = image_url
    res = Fal().run(model, payload)
    url = _find_url(res, ("video", "file"))
    if not url:
        raise ProviderError(f"no video url in fal response: {json.dumps(res)[:300]}")
    out = Fal().download(url, p.path("video_gen", f"{clip}.mp4"))
    p.path("video_gen", f"{clip}.prompt.json").write_text(json.dumps({"model": model, **payload}, indent=2))
    p.add_cost("fal", est, what="video", clip=clip, model=model, seconds=seconds)
    p.append_credit(f"video_gen/{clip}.mp4 - GENERATED b-roll ({model}); non-product shot")
    return out


# --------------------------------------------------------------------------- ElevenLabs SFX


def gen_sfx(p: Project, cues: list[dict], overwrite: bool = False) -> list[Path]:
    """cues: [{name, prompt, seconds}]. At most 4 concurrent requests."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise ProviderError("ELEVENLABS_API_KEY is not set (.env)")
    out_dir = p.path("audio/sfx")
    out_dir.mkdir(parents=True, exist_ok=True)

    def one(c: dict) -> Path:
        dst = out_dir / f"{c['name']}.mp3"
        if dst.exists() and not overwrite:
            return dst
        for attempt in range(5):
            r = httpx.post(f"{ELEVEN}/sound-generation", headers={"xi-api-key": key}, timeout=120,
                           json={"text": c["prompt"], "duration_seconds": max(0.5, min(22, c["seconds"])),
                                 "prompt_influence": 0.5})
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                raise ProviderError(f"sfx {c['name']}: {r.status_code} {r.text[:200]}")
            dst.write_bytes(r.content)
            p.add_cost("elevenlabs", 0.0, what="sfx", name=c["name"], seconds=c["seconds"])
            return dst
        raise ProviderError(f"sfx {c['name']}: still rate-limited")

    with ThreadPoolExecutor(max_workers=SFX_CONCURRENCY) as ex:
        paths = list(ex.map(one, cues))
    p.append_credit("audio/sfx/*.mp3 - generated sound effects, ElevenLabs sound-generation")
    return paths
