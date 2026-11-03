"""Per-shot flicker score for a rendered frame folder.

    python -m reelforge.flicker <frames_dir> <shots.json | cut seconds "0,3.4,7.35,...">

Score per frame = mean |2·f_t − f_t−1 − f_t+1| on downscaled luma: smooth motion ≈ 0, flicker spikes.
Guide (what-if-100, Nov 2026): clean shots < 2, look closely > 5, broken > 20 (dark sets with an overflowing shadow
pool scored 30-125).
"""
import glob, json, sys

import numpy as np
from PIL import Image


def scores(frames_dir):
    fs = sorted(glob.glob(frames_dir + "/f_*.jpg"))
    L = [np.asarray(Image.open(f).convert("L").resize((270, 480)), dtype=np.float32) for f in fs]
    return np.array([0] + [np.abs(2 * L[i] - L[i - 1] - L[i + 1]).mean() for i in range(1, len(L) - 1)] + [0])


def main():
    d, spec = sys.argv[1], sys.argv[2]
    sc = scores(d)
    if spec.endswith(".json"):
        ranges = [(a - 1, b - 1, n) for n, a, b in json.load(open(spec))]
    else:
        cf = [round(float(c) * 30) for c in spec.split(",")] + [len(sc)]
        ranges = [(a, b, "") for a, b in zip(cf, cf[1:])]
    worst = 0
    for a, b, name in ranges:
        seg = sc[a + 2:b - 1]
        if len(seg):
            worst = max(worst, float(np.median(seg)))
            flag = "  <-- check" if np.median(seg) > 5 else ""
            print(f"{a / 30:5.1f}-{(b + 1) / 30:5.1f}s {name:7s} median {np.median(seg):5.2f}  p95 "
                  f"{np.percentile(seg, 95):5.2f}  max {seg.max():6.2f}{flag}")
    print(f"worst shot median: {worst:.2f}")


if __name__ == "__main__":
    main()
