"""Broadcast-style audio mix for a GameReel, built from the same props.json Remotion renders.

Remotion plays every sound at a fixed volume, so a sound effect under a voice line fights it. This rebuilds the
soundtrack in ffmpeg with three buses and replaces the render's audio:

    VO   each line loudness-matched to VO_LUFS, high-passed, gently compressed, a little presence lift
    FX   clip audio + one-shot SFX (cues, whoosh/pop), dipped DUCK_DB under every spoken line by a smooth volume
         envelope (ramps PRE before the first word and POST after the last), so nothing pumps between words
    MIX  VO + ducked FX through a limiter; shorts.build then masters to -14 LUFS as before

`audit` measures the result from the stems: speech-to-background ratio over every voiced 50 ms frame, SFX onsets
that land on top of a spoken word, and SFX bursts in the gaps that jump far above the voice level.

    python -m reelforge.mix projects/shorts/roblox-hooks/06-deer-67     # remix + audit an already-built reel
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 48000
VO_LUFS = -16.0          # every VO line lands here before the bus chain
DUCK_DB, PRE, POST = -15.0, 0.12, 0.25   # FX-bus dip under speech, ramp in before / out after each line (s)
WIN = 0.05               # audit window (s)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{cmd[0]} failed:\n{r.stderr[-2000:]}")
    return r


def lufs(path: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else -70.0


def build_mix(props: dict, pub: Path, out_dir: Path) -> dict:
    """Write out_dir/mix.wav plus stems (vo.wav, fx.wav). Returns the event list the audit needs."""
    fps = props["fps"]
    total = props["durationInFrames"] / fps
    ins: list[list[str]] = []
    fx, vo = [], []

    def add(path: Path, ss: float = 0.0, t: float | None = None) -> int:
        a = (["-ss", f"{ss:.3f}"] if ss else []) + (["-t", f"{t:.3f}"] if t else [])
        ins.append(a + ["-i", str(path)])
        return len(ins) - 1

    events = []   # (kind, start_s, label) for the audit
    for i, s in enumerate(props["segments"]):
        if s["type"] in ("clip", "source") and s.get("gain"):
            sp = float(s.get("speed", 1))
            k = add(pub / s["src"], s["startFrom"] / fps, s["dur"] / fps * sp)
            tempo = f"atempo={sp}," if sp != 1 else ""
            d = round(s["from"] / fps * 1000)
            fx.append(f"[{k}:a]{tempo}aresample={SR},volume={s['gain']},adelay={d}|{d}[b{i}]")
    sfx = props.get("sfx") or {}
    shots = [(c["src"], c["from"], c["volume"]) for c in props.get("cues") or []]
    if sfx.get("whoosh"):
        shots += [(sfx["whoosh"], max(0, s["from"] - 6), 0.55) for s in props["segments"][1:]]
    for j, (src, f0, vol) in enumerate(shots):
        k = add(pub / src)
        d = round(f0 / fps * 1000)
        fx.append(f"[{k}:a]aresample={SR},volume={vol},adelay={d}|{d}[c{j}]")
        events.append(("sfx", f0 / fps, Path(src).stem))
    for j, v in enumerate(props.get("vo") or []):
        p = pub / v["src"]
        k = add(p)
        g = VO_LUFS - lufs(p)
        d = round(v["from"] / fps * 1000)
        vo.append(f"[{k}:a]aresample={SR},volume={g:.2f}dB,adelay={d}|{d}[v{j}]")
        events += [("word", w[0] / fps, w[2]) for w in v["words"]]
        events += [("wordend", w[1] / fps, w[2]) for w in v["words"]]

    spans = [(v["words"][0][0] / fps, v["words"][-1][1] / fps) for v in props.get("vo") or [] if v["words"]]
    depth = 1 - 10 ** (DUCK_DB / 20)
    env = "0"
    for a, b in spans:
        env = f"max({env},clip(min((t-{a - 2 * PRE:.3f})/{PRE},({b + 2 * POST:.3f}-t)/{POST}),0,1))"
    duck = f"volume='1-{depth:.3f}*{env}':eval=frame"

    T = f"{total:.3f}"
    pad = f"apad=whole_dur={T},atrim=0:{T}"
    g = fx + vo
    fl = "".join(f"[b{i}]" for i, s in enumerate(props["segments"]) if s["type"] in ("clip", "source") and s.get("gain"))
    fl += "".join(f"[c{j}]" for j in range(len(shots)))
    nfx = fl.count("[")
    if nfx:
        g.append(f"{fl}amix=inputs={nfx}:normalize=0:duration=longest,{pad},aformat=channel_layouts=stereo[fxraw]")
    else:
        g.append(f"anullsrc=r={SR}:cl=stereo,atrim=0:{T}[fxraw]")
    if vo:
        g.append("".join(f"[v{j}]" for j in range(len(vo))) +
                 f"amix=inputs={len(vo)}:normalize=0:duration=longest,{pad},aformat=channel_layouts=stereo,"
                 "highpass=f=85,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80:makeup=1.5,"
                 "equalizer=f=3200:t=q:w=1.0:g=2.5,asplit=2[vo1][vostem]")
        g.append(f"[fxraw]{duck},asplit=2[fx1][fxstem]")
        g.append("[fx1][vo1]amix=inputs=2:normalize=0,alimiter=limit=0.89:attack=3:release=60[mix]")
    else:
        g.append("[fxraw]asplit=2[fx1][fxstem]")
        g.append("[fx1]alimiter=limit=0.89[mix]")
        g.append(f"anullsrc=r={SR}:cl=stereo,atrim=0:{T}[vostem]")
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + [x for a in ins for x in a]
    cmd += ["-filter_complex", ";".join(g)]
    for lab, name in (("mix", "mix"), ("vostem", "vo"), ("fxstem", "fx")):
        cmd += ["-map", f"[{lab}]", "-ar", str(SR), "-c:a", "pcm_s16le", str(out_dir / f"{name}.wav")]
    _run(cmd)
    return {"events": events, "seconds": total}


def _env(path: Path) -> np.ndarray:
    """Mono RMS envelope in dBFS, one value per WIN seconds."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = int(SR * WIN)
    x = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((x.astype(np.float64) ** 2).mean(axis=1)) + 1e-9)


def audit(out_dir: Path, events: list) -> dict:
    v, f = _env(out_dir / "vo.wav"), _env(out_dir / "fx.wav")
    n = min(len(v), len(f))
    v, f = v[:n], np.maximum(f[:n], -60.0)
    voiced = v > -42
    snr = (v - f)[voiced]
    vo_level = float(np.median(v[voiced])) if voiced.any() else -70.0
    words = [(t, e) for (k, t, _), (k2, e, _) in zip([x for x in events if x[0] == "word"],
                                                     [x for x in events if x[0] == "wordend"])]
    hits = [(round(t, 2), lab) for k, t, lab in events if k == "sfx" and any(a - 0.15 <= t <= b + 0.1 for a, b in words)]
    # Gap bursts: FX louder than the voice's typical level by > 6 dB while nobody is talking.
    gap = (~voiced) & (f > vo_level + 6)
    loud = sorted({round(i * WIN, 1) for i in np.where(gap)[0]})
    return {
        "vo_median_db": round(vo_level, 1),
        "snr_median_db": round(float(np.median(snr)), 1) if snr.size else None,
        "snr_p10_db": round(float(np.percentile(snr, 10)), 1) if snr.size else None,
        "voiced_below_8db_pct": round(float((snr < 8).mean() * 100), 1) if snr.size else None,
        "sfx_on_words": hits,
        "gap_bursts_s": loud[:12],
    }


def apply(props_path: Path, pub: Path, raw: Path) -> dict:
    """Mix from props, swap it into the Remotion render `raw` in place, return the audit."""
    props = json.loads(props_path.read_text())
    out_dir = props_path.parent / "mix"
    info = build_mix(props, pub, out_dir)
    tmp = raw.with_name(raw.stem + ".mixed.mp4")
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw), "-i", str(out_dir / "mix.wav"),
          "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest", str(tmp)])
    tmp.replace(raw)
    rep = audit(out_dir, info["events"])
    (out_dir / "audit.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    d = Path(sys.argv[1]).resolve()
    props = json.loads((d / "out" / "props.json").read_text())
    info = build_mix(props, d / "public", d / "out" / "mix")
    print(json.dumps(audit(d / "out" / "mix", info["events"]), indent=1))
