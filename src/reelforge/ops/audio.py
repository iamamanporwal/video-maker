"""Audio analysis with numpy only: kicks, tempo, beat phase, drops, and solving music offsets onto bar lines."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import numpy as np

SR = 22050
HOP = 256
N_FFT = 1024
# Frame i is centred at (i*HOP + N_FFT/2) / SR.
CENTRE = N_FFT / 2 / SR


def load_mono(path: Path, sr: int = SR) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def _stft_mag(y: np.ndarray, n_fft: int = N_FFT, hop: int = HOP) -> np.ndarray:
    if len(y) < n_fft:
        y = np.pad(y, (0, n_fft - len(y)))
    n = 1 + (len(y) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n)[:, None]
    frames = y[idx] * np.hanning(n_fft)[None, :]
    return np.abs(np.fft.rfft(frames, axis=1))


def onset_envelope(y: np.ndarray, sr: int = SR, max_hz: float = 150.0) -> np.ndarray:
    """Low-band spectral flux: kicks."""
    mag = _stft_mag(y)
    freqs = np.fft.rfftfreq(N_FFT, 1 / sr)
    low = np.log1p(mag[:, freqs <= max_hz] * 10).sum(axis=1)
    flux = np.maximum(0, np.diff(low, prepend=low[:1]))
    k = np.hanning(5)
    flux = np.convolve(flux, k / k.sum(), mode="same")
    return flux / (flux.max() + 1e-9)


def tempo(env: np.ndarray, sr: int = SR, lo: float = 70, hi: float = 180, prior: Optional[float] = None) -> float:
    fps = sr / HOP
    e = env - env.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    lags = np.arange(len(ac))
    bpms = 60 * fps / np.maximum(lags, 1)
    mask = (bpms >= lo) & (bpms <= hi)
    score = ac.copy()
    if prior:
        score = score * np.exp(-0.5 * (np.log2(bpms / prior) / 0.15) ** 2)
    best = lags[mask][np.argmax(score[mask])]
    # Parabolic refinement.
    if 1 <= best < len(ac) - 1:
        a, b, c = ac[best - 1], ac[best], ac[best + 1]
        best = best + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    return float(60 * fps / best)


def beat_phase(env: np.ndarray, bpm: float, sr: int = SR) -> float:
    """Seconds of the first beat (0 <= phase < period) maximising envelope energy on the grid."""
    fps = sr / HOP
    period = 60 * fps / bpm
    best, best_s = 0.0, -1.0
    for off in np.linspace(0, period, 64, endpoint=False):
        idx = np.round(np.arange(off, len(env), period)).astype(int)
        idx = idx[idx < len(env)]
        s = env[idx].sum()
        if s > best_s:
            best, best_s = off, s
    return float((best / fps + CENTRE) % (60 / bpm))


def energy(y: np.ndarray, sr: int = SR, win: float = 0.25) -> tuple[np.ndarray, float]:
    n = int(sr * win)
    m = len(y) // n
    rms = np.sqrt((y[: m * n].reshape(m, n) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9), win


def drops(y: np.ndarray, sr: int = SR, k: int = 4, min_gap: float = 6.0, ctx: float = 2.0) -> list[dict]:
    """The biggest sustained energy rises: mean(next ctx s) - mean(prev ctx s)."""
    db, win = energy(y, sr)
    c = int(ctx / win)
    rises = np.full(len(db), -np.inf)
    for i in range(c, len(db) - c):
        rises[i] = db[i:i + c].mean() - db[i - c:i].mean()
    picks: list[dict] = []
    for i in np.argsort(rises)[::-1]:
        if not np.isfinite(rises[i]) or rises[i] < 3.0:
            break
        t = i * win
        if all(abs(t - p["t"]) >= min_gap for p in picks):
            picks.append({"t": round(float(t), 3), "rise_db": round(float(rises[i]), 2)})
        if len(picks) >= k:
            break
    return sorted(picks, key=lambda p: p["t"])


def snap_to_beat(t: float, bpm: float, phase: float) -> float:
    period = 60 / bpm
    return phase + round((t - phase) / period) * period


def analyse(path: Path, bpm_prior: Optional[float] = None) -> dict:
    y = load_mono(path)
    env = onset_envelope(y)
    bpm = tempo(env, prior=bpm_prior)
    if bpm_prior and abs(bpm - bpm_prior) / bpm_prior < 0.04:
        bpm = float(bpm_prior)
    phase = beat_phase(env, bpm)
    ds = drops(y)
    for d in ds:
        d["t_beat"] = round(snap_to_beat(d["t"], bpm, phase), 3)
    fps = SR / HOP
    kicks = [round(float(i / fps + CENTRE), 3) for i in np.where((env[1:-1] > env[:-2]) & (env[1:-1] >= env[2:])
                                                  & (env[1:-1] > 0.35))[0] + 1]
    return {"file": str(path), "duration": round(len(y) / SR, 3), "bpm": round(bpm, 3),
            "phase": round(phase, 4), "drops": ds, "kicks": kicks[:400]}


def solve_segments(alignments: list[dict], fps: int = 30) -> list[dict]:
    """Each alignment: {src, edit_from, edit_to, edit_align, music_align, volumeKeys?} in seconds.

    Returns MusicSegment dicts so `music_align` (a drop in the file) lands exactly on `edit_align`
    (a bar line in the edit). If the drop is earlier in the file than the segment allows, the segment
    entry is delayed instead (e.g. delay the music 1.15 s so its entry sits on the 8.0 s sting).
    """
    segs = []
    for a in alignments:
        trim = a["music_align"] - (a["edit_align"] - a["edit_from"])
        start = a["edit_from"]
        if trim < 0:
            start, trim = start - trim, 0.0
        f0, f1 = int(round(start * fps)), int(round(a["edit_to"] * fps))
        segs.append({"src": a["src"], "from": f0, "trimSec": round(trim, 4), "dur": f1 - f0,
                     "volumeKeys": a.get("volumeKeys", [])})
    return segs
