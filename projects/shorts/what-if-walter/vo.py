"""python vo.py: narration via Kokoro (local, open-weights TTS) -> public/vo/LNN.wav + vo.json.

No ElevenLabs key is needed. Model files (kokoro-v1.0.onnx, voices-v1.0.bin) come from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0; point KOKORO_DIR at them.

Kokoro gives no word timestamps, so word times are estimated per line: leading/trailing silence is trimmed, internal
pauses (>= 110 ms) are matched to punctuation breaks, and words inside each phrase share its span by syllable weight.
Cuts in the film key to line starts (exact) and to these estimates (good to a few frames).
"""
import json, os, re
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

D = Path(__file__).resolve().parent
KDIR = Path(os.environ.get("KOKORO_DIR", D / "kokoro"))
VOICE, SPEED = os.environ.get("KOKORO_VOICE", "am_michael"), 0.94
SLOW = {15: 0.8, 17: 0.8, 19: 0.85}                 # the confession is read slower
SR = 24000


def trim(a, th=0.012):
    idx = np.where(np.abs(a) > th)[0]
    return a[max(0, idx[0] - int(0.03 * SR)): idx[-1] + int(0.06 * SR)] if len(idx) else a


def pauses(a, th=0.012, min_len=0.11):
    """Internal silent runs (start, end) in seconds."""
    win = int(0.01 * SR)
    env = np.array([np.abs(a[i:i + win]).max() for i in range(0, len(a) - win, win)])
    quiet = env < th
    out, s = [], None
    for i, q in enumerate(quiet):
        if q and s is None:
            s = i
        elif not q and s is not None:
            if (i - s) * 0.01 >= min_len and s > 0:
                out.append((s * 0.01, i * 0.01))
            s = None
    return out


def syl(w):
    w = re.sub(r"[^a-z]", "", w.lower()) or "x"
    return max(1, len(re.findall(r"[aeiouy]+", w)) - (1 if w.endswith("e") and len(w) > 3 else 0))


def word_times(text, a):
    dur = len(a) / SR
    words = text.split()
    # phrase breaks after punctuated words
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.,?!]$|\.\.\.$", w):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    ps = sorted(pauses(a), key=lambda p: p[1] - p[0], reverse=True)[: len(groups) - 1]
    ps = sorted(ps)
    spans, t = [], 0.0
    if len(ps) == len(groups) - 1:
        for p in ps:
            spans.append((t, p[0]))
            t = p[1]
        spans.append((t, dur))
    else:                                            # fall back to syllable share over the whole line
        tot = sum(syl(w) for w in words)
        for g in groups:
            d = dur * sum(syl(w) for w in g) / tot
            spans.append((t, t + d))
            t += d
    out = []
    for g, (s0, s1) in zip(groups, spans):
        tot, t = sum(syl(w) for w in g), s0
        for w in g:
            d = (s1 - s0) * syl(w) / tot
            out.append([round(t, 3), round(t + d, 3), w])
            t += d
    return out


if __name__ == "__main__":
    k = Kokoro(str(KDIR / "kokoro-v1.0.onnx"), str(KDIR / "voices-v1.0.bin"))
    lines = json.loads((D / "script.json").read_text())
    res = []
    for i, text in enumerate(lines):
        a, sr = k.create(text, voice=VOICE, speed=SLOW.get(i, SPEED), lang="en-us")
        assert sr == SR
        a = trim(a)
        src = f"vo/L{i + 1:02d}.wav"
        sf.write(D / "public" / src, a, SR)
        res.append({"src": src, "text": text, "dur": round(len(a) / SR, 3), "words": word_times(text, a)})
        print(f"L{i + 1:<2} {len(a) / SR:5.2f}s  {text}")
    (D / "vo.json").write_text(json.dumps(res, indent=1))
    print(f"total speech {sum(r['dur'] for r in res):.1f}s, voice {VOICE}")
