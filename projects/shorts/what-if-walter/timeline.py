"""python timeline.py: vo.json + pacing -> out/props.json (picture) and public/mix.wav (all audio, mastered later).

One source of truth: the anchors below (seconds, film time) drive both the Remotion cuts and the SFX / music cues.

Music plan (Hitman, Kevin MacLeod, CC BY 4.0):
  Act 1  track 0 -> its first surge (~14 s) lands under "Heisenberg"; hard stop + tape rewind on "But what if".
  Act 2  the quiet timeline: no score, a wall clock ticking and a low drone. Ordinary life.
  Act 3  track 44 s -> its kick (52.5 s) lands on the second "Heisenberg"; carries the Gray Matter beat; out by "Safe".
  Act 4  the confession and the ending sit on the drone alone, then a last low hit under the end card.
"""
import json, subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

d = Path(__file__).resolve().parent
ROOT = d.parents[2]
FPS, SR = 30, 48000
LEAD = 0.8
GAPS = [0.9, 0.5, 0.7, 1.0, 1.7, 0.5, 0.5, 0.6, 0.6, 0.5, 1.0, 0.5, 0.6, 0.7, 0.8, 1.1, 0.5, 1.1, 0.6]
TAIL = 4.2
MUSIC = ROOT / "projects/shorts/vi3w-memes/music/hitman.mp3"
SFX = ROOT / "assets/shorts-sfx"
rng = np.random.default_rng(7)

vo = json.loads((d / "vo.json").read_text())
t, lines = LEAD, []
for i, l in enumerate(vo):
    lines.append({"src": l["src"], "start": round(t, 3), "dur": l["dur"], "text": l["text"],
                  "words": [[round(t + a, 3), round(t + b, 3), w] for a, b, w in l["words"]]})
    t += l["dur"] + (GAPS[i] if i < len(GAPS) else 0)
END = round(t + TAIL, 2)


def W(i, j):
    return lines[i]["words"][j][0]


def L(i):
    return lines[i]["start"]


def E(i):
    return round(lines[i]["start"] + lines[i]["dur"], 3)


A = {
    "cough": W(0, 4), "l2": L(1), "fifty": W(1, 2), "chem": W(1, 6), "car": W(1, 14),
    "l3": L(2), "lung": W(2, 5), "inop": W(2, 7), "l4": L(3), "pride": W(3, 7), "heis": W(3, 12), "l4end": E(3),
    "l5": L(4), "whatif": W(4, 1), "just": W(4, 6), "l5end": E(4),
    "l6": L(5), "ride": W(5, 4), "l7": L(6), "jesse": W(6, 6), "window": W(6, 12),
    "l8": L(7), "caught": W(7, 6), "lives": W(7, 8), "l9": L(8), "jane": W(8, 0), "plane": W(8, 4), "abq": W(8, 11),
    "l10": L(9), "retires": W(9, 5), "bbq": W(9, -1), "l11": L(10), "grading": W(10, 4), "swallow": W(10, 7),
    "l12": L(11), "cancer12": W(11, 2), "heis2": W(11, 5), "l13": L(12), "five": W(12, 8), "billions": W(12, 14),
    "l14": L(13), "pride2": W(13, 1), "cancer14": W(13, 6), "permission": W(13, 10),
    "l15": L(14), "lives15": W(14, 6), "eighty": W(14, 9),
    "l16": L(15), "safe": W(15, 0), "respected": W(15, 1), "forgotten": W(15, 2), "l16end": E(15),
    "l17": L(16), "l18": L(17), "alive": W(17, -1), "l18end": E(17),
    "l19": L(18), "thirty": W(18, 5), "l20": L(19), "never": W(19, 2), "alive2": W(19, 3), "l20end": E(19),
    "end": END,
}
A = {k: round(v, 3) for k, v in A.items()}

# ------------------------------------------------------------------ audio
N = int(END * SR) + SR


def load(p, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def place(bus, x, at, gain=1.0):
    i = int(at * SR)
    x = x[: max(0, len(bus) - i)]
    bus[i: i + len(x)] += gain * x


def env(n, a=0.002, r=0.1):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def tick():
    n = int(0.05 * SR)
    x = rng.standard_normal(n) * np.exp(-np.linspace(0, 40, n))
    hp = np.diff(x, prepend=0)                               # bright wooden click
    return 0.35 * hp / np.abs(hp).max()


def stamp():
    n = int(0.35 * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * (95 - 50 * tt) * tt) * np.exp(-tt * 14)
    slap = lowpass(rng.standard_normal(n), 2500) * np.exp(-tt * 45)
    x = body + 1.4 * slap
    return 0.9 * x / np.abs(x).max()


def rewind(dur=0.9):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = 900 * np.exp(-tt * 3) + 120
    x = 0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.25 * lowpass(rng.standard_normal(n), 3000)
    return 0.6 * x * env(n, 0.01, 0.25)


def drone(n, f0=55.0):
    tt = np.arange(n) / SR
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt)
    x = (np.sin(2 * np.pi * f0 * tt) + 0.55 * np.sin(2 * np.pi * f0 * 1.5 * tt + 1.3)
         + 0.3 * np.sin(2 * np.pi * f0 * 2.01 * tt)) * lfo
    air = lowpass(rng.standard_normal(n), 400) * 0.6
    return (x + air) / 3.0


def boom():
    n = int(2.5 * SR)
    tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * (60 - 25 * tt / 2.5) * tt) * np.exp(-tt * 2.2)
    return 0.9 * x


def fade(x, a, b):
    x = x.copy()
    na, nb = int(a * SR), int(b * SR)
    if na:
        x[:na] *= np.linspace(0, 1, na)
    if nb:
        x[-nb:] *= np.linspace(1, 0, nb)
    return x


if __name__ == "__main__":
    voice = np.zeros(N)
    for l in lines:
        x = load(d / "public" / l["src"])
        place(voice, x, l["start"], 1.0)

    music = np.zeros(N)
    hit = load(MUSIC)
    # Act 1: track starts at film 1.6 s so its first surge (track ~14.3 s) arrives under "became Heisenberg"
    a1 = A["heis"] - 14.3
    seg = hit[int(max(0, -a1) * SR): int((A["l5"] + 0.15 - a1) * SR)]
    place(music, fade(seg, 1.5, 0.12), max(0, a1), 0.9)
    # Act 3: kick at track 52.5 s lands on the second "Heisenberg"
    a3 = A["heis2"] - 52.5
    s0 = A["l12"] - 1.2
    seg = hit[int((s0 - a3) * SR): int((A["l16"] + 0.3 - a3) * SR)]
    place(music, fade(seg, 1.0, 1.6), s0, 0.9)

    bed = np.zeros(N)
    # Act 2 bed: drone + wall clock from the rewind to the twist
    b0, b1 = A["l5end"] + 0.3, A["l12"] - 0.3
    place(bed, fade(drone(int((b1 - b0) * SR)), 1.2, 1.0), b0, 0.16)
    tk = tick()
    for k in np.arange(b0 + 0.5, b1 - 0.4, 1.0):
        place(bed, tk, k, 0.5)
    # Act 4 bed: lower drone from "Safe" to the end, then the last hit
    c0 = A["l16"] - 0.4
    place(bed, fade(drone(int((END - c0) * SR), 41.2), 1.5, 2.0), c0, 0.2)
    for k in np.arange(A["safe"], A["l17"] - 0.3, 1.0):          # the clock comes back for "Safe. Respected. Forgotten."
        place(bed, tk, k, 0.45)
    place(bed, boom(), A["l20end"] + 0.35, 0.55)

    fx = np.zeros(N)
    whoosh, pop = load(SFX / "whoosh.mp3"), load(SFX / "pop.mp3")
    st = stamp()
    for k, off in [("inop", 0.05), ("ride", 0.25), ("lives", 0.05), ("jane", 0.45), ("plane", 0.25), ("retires", 0.05),
                   ("permission", 0.05)]:
        place(fx, st, A[k] + off, 0.55)
    place(fx, rewind(), A["l5"] - 0.75, 0.7)
    for k in ["l2", "l6", "l12", "l17"]:
        place(fx, whoosh, A[k] - 0.45, 0.28)
    for k in ["fifty", "five", "eighty"]:
        place(fx, pop, A[k], 0.22)

    # duck music + bed under the voice (envelope follower, ~12 dB)
    e = np.abs(voice)
    win = int(0.25 * SR)
    e = np.convolve(e, np.ones(win) / win, mode="same")
    duck = 1 - 0.75 * np.clip(e / 0.02, 0, 1)
    duck = np.convolve(duck, np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    mix = voice + (0.42 * music + bed) * duck + fx
    mix = mix[: int(END * SR)]
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    sf.write(d / "public/mix.wav", mix.astype(np.float32), SR)

    props = {"fps": FPS, "durationInFrames": round(END * FPS), "lines": lines, "A": A}
    (d / "out").mkdir(exist_ok=True)
    (d / "out/props.json").write_text(json.dumps(props, indent=1))
    for i, l in enumerate(lines):
        print(f"L{i + 1:<2} {l['start']:6.2f}-{l['start'] + l['dur']:6.2f}  {l['text'][:64]}")
    print(f"END {END}s ({round(END * FPS)} frames). Act-1 music at {a1:.2f}s, act-3 kick on {A['heis2']:.2f}s")
