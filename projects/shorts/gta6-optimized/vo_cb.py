"""~/models/chatterbox-venv/bin/python vo_cb.py: expressive narration with Chatterbox (Resemble AI, MIT, local) →
out/vo/story_cb.wav + out/words_cb.json in the same shape as vo.py (so build.py indices A("p2", 13) still match).

Per line: N takes → mlx-whisper transcribes each → keep the take with the lowest word error rate vs the spoken text
(ties → livelier pitch). Word times: whisper words aligned to vo.py's Kokoro token list (difflib anchors + letter-count
interpolation), so captions and every overlay keyed by word index stay in sync. Kokoro was rejected by the user as robotic
(2026-11-08); ElevenLabs free tier has 21 chars left until the reset."""
import difflib, json, re, sys
from pathlib import Path
import numpy as np, torch, torchaudio as ta
import mlx_whisper
from chatterbox.tts import ChatterboxTTS

D = Path(__file__).resolve().parent
OUT = D / "out"

WEIGHTS = Path.home() / "models/chatterbox-weights"
TAKES = int(sys.argv[1]) if len(sys.argv) > 1 else 3
EXAG, CFG, TEMP = 0.62, 0.38, 0.75
SAY = {"GTA 6": "G.T.A. six", "LOD": "L.O.D.", "optimization": "optimisation", "Vi3W": "View", "3D": "three-D", "212": "two hundred and twelve", "25 million": "twenty-five million",
       "5 billion": "five billion", "PS5": "P.S. five", "200": "two hundred"}
WHISPER = str(Path.home() / "models/whisper-turbo")      # mlx-community/whisper-large-v3-turbo, fetched with curl
GAP = {"h1": 0.3, "h3": 0.35, "p1": 0.35, "p2": 0.4}
NUM = {"212": "two hundred and twelve", "25": "twenty five", "200": "two hundred", "ps5": "p s five", "6": "six", "13": "thirteen", "90": "ninety", "2015": "twenty fifteen", "4711": "four thousand seven hundred and eleven",
       "100": "hundred", "975000": "nine hundred seventy-five thousand", "3": "three", "5": "five", "1": "one", "3d": "three d",
       "4": "four", "lod": "lod", "gta": "g t a", "view": "view", "vi3w": "view"}


def norm(w):
    w = re.sub(r"[^a-z0-9' -]", "", w.lower().replace(",", "")).strip("'")
    return NUM.get(w.replace(" ", ""), w)


def split_words(ws):
    out = []
    for w in ws:
        parts = norm(w["word"]).replace("-", " ").split()
        n = max(1, len(parts))
        for j, p in enumerate(parts or [""]):
            a = w["start"] + (w["end"] - w["start"]) * j / n
            out.append((p, a, a + (w["end"] - w["start"]) / n))
    return out


def transcribe(path):
    r = mlx_whisper.transcribe(str(path), path_or_hf_repo=WHISPER, word_timestamps=True, language="en")
    return [w for s in r["segments"] for w in s.get("words", [])]


def wer(ref, hyp):
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    match = sum(b.size for b in sm.get_matching_blocks())
    return 1 - match / max(1, len(ref)) + 0.5 * max(0, len(hyp) - len(ref)) / max(1, len(ref))


def align(tokens, hw, dur):
    """tokens: script token strings; hw: [(word, s, e)] from whisper → [(s, e)] per token."""
    ref = [p for t in tokens for p in norm(t).replace("-", " ").split()] or [""]
    owner = [i for i, t in enumerate(tokens) for _ in (norm(t).replace("-", " ").split() or [""])]
    sm = difflib.SequenceMatcher(a=ref, b=[h[0] for h in hw], autojunk=False)
    t_s, t_e = [None] * len(ref), [None] * len(ref)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            t_s[blk.a + k], t_e[blk.a + k] = hw[blk.b + k][1], hw[blk.b + k][2]
    # fill gaps by letter-count interpolation between anchors
    i = 0
    while i < len(ref):
        if t_s[i] is not None:
            i += 1
            continue
        j = i
        while j < len(ref) and t_s[j] is None:
            j += 1
        a = t_e[i - 1] if i > 0 else (hw[0][1] if hw else 0.0)
        b = t_s[j] if j < len(ref) else (hw[-1][2] if hw else dur)
        L = [max(1, len(ref[k])) for k in range(i, j)]
        tot, acc = sum(L), 0
        for k, l in zip(range(i, j), L):
            t_s[k] = a + (b - a) * acc / tot
            acc += l
            t_e[k] = a + (b - a) * acc / tot
        i = j
    res = []
    for ti in range(len(tokens)):
        ks = [k for k, o in enumerate(owner) if o == ti]
        res.append((t_s[ks[0]], t_e[ks[-1]]))
    return res


def pitch_var(w, sr):
    x = w.squeeze().numpy()
    hop = int(sr * 0.02)
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    return float(np.std(e[e > 0.01])) if (e > 0.01).any() else 0.0


if __name__ == "__main__":
    lines = json.loads((D / "script.json").read_text())["lines"]
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    m = ChatterboxTTS.from_local(WEIGHTS, device=dev)
    sr = m.sr
    tdir = OUT / "vo" / "cb_takes"
    tdir.mkdir(parents=True, exist_ok=True)
    audio, words, spans, off, report = [], [], {}, 0.0, []
    for key, text in lines:
        said = text
        for a, b in SAY.items():
            said = said.replace(a, b)
        tokens = re.findall(r"[\w'$-]+", text)
        want = [p for t in tokens for p in norm(t).replace("-", " ").split()]
        best = None
        for k in range(TAKES):
            torch.manual_seed(1000 * k + len(key) * 7 + sum(map(ord, key)))
            w = m.generate(said, exaggeration=EXAG, cfg_weight=CFG, temperature=TEMP)
            p = tdir / f"{key}_{k}.wav"
            ta.save(str(p), w, sr)
            hw = split_words(transcribe(p))
            score = wer(want, [h[0] for h in hw])
            cand = (score, -pitch_var(w, sr), k, w, hw)
            print(f"{key} take {k}: wer={score:.2f} {' '.join(h[0] for h in hw)}", flush=True)
            if best is None or cand[:2] < best[:2]:
                best = cand
            if score == 0 and k >= 1:
                break
        score, _, k, w, hw = best
        x = w.squeeze().numpy()
        s0 = max(0.0, (hw[0][1] if hw else 0) - 0.06)
        s1 = min(len(x) / sr, (hw[-1][2] if hw else len(x) / sr) + 0.15)
        x = x[int(s0 * sr):int(s1 * sr)]
        hw = [(h[0], h[1] - s0, h[2] - s0) for h in hw]
        i0 = len(words)
        for tok, (a, b) in zip(tokens, align(tokens, hw, len(x) / sr)):
            words.append([round(off + a, 3), round(off + b, 3), tok])
        spans[key] = [i0, len(words)]
        g = GAP.get(key, 0.2)
        audio += [x, np.zeros(int(sr * g), dtype=x.dtype)]
        off += len(x) / sr + g
        report.append((key, k, round(score, 2)))
    (OUT / "vo").mkdir(parents=True, exist_ok=True)
    wav = OUT / "vo" / "story_cb.wav"
    ta.save(str(wav), torch.from_numpy(np.concatenate(audio)).unsqueeze(0), sr)
    (OUT / "words_cb.json").write_text(json.dumps({"mp3": str(wav), "dur": off, "sr": sr, "words": words, "lines": spans}))
    print("picked:", report)
    print(f"cb: {off:.1f}s {len(words)} words")
