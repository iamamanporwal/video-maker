"""~/models/chatterbox-venv/bin/python vo.py [takes]: Chatterbox best-of-N narration → out/vo/story.wav, out/vo/outro.wav,
out/words.json = {"lines": [{id, text, start, end, words: [[word, s, e], ...]}], "dur": story_seconds, "outro": {...}}.
Per line: N takes, mlx-whisper transcribes each, keep the lowest word-error take; word times come from whisper."""
import difflib, json, re, sys
from pathlib import Path
import numpy as np, torch, torchaudio as ta
import mlx_whisper
from chatterbox.tts import ChatterboxTTS

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
from script import LINES, OUTRO, SAY, GAP, GAP_AFTER  # noqa: E402

OUT = D / "out" / "vo"
OUT.mkdir(parents=True, exist_ok=True)
TAKES = int(sys.argv[1]) if len(sys.argv) > 1 else 3
EXAG, CFG, TEMP = 0.65, 0.4, 0.78
WHISPER = str(Path.home() / "models/whisper-turbo")
NUM = {"3d": "three d", "30": "thirty", "6": "six", "view": "view", "vi3w": "view"}


def spoken(t):
    for k, v in SAY.items():
        t = t.replace(k, v)
    return t


def norm_words(t):
    ws = re.sub(r"[^a-z0-9' ]", " ", t.lower().replace("-", " ")).split()
    return [NUM.get(w, w) for w in ws]


def transcribe(path):
    r = mlx_whisper.transcribe(str(path), path_or_hf_repo=WHISPER, word_timestamps=True, language="en")
    return [(w["word"].strip(), w["start"], w["end"]) for s in r["segments"] for w in s.get("words", [])]


def wer(ref, hyp):
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    m = sum(b.size for b in sm.get_matching_blocks())
    return 1 - m / max(1, len(ref)) + 0.5 * max(0, len(hyp) - len(ref)) / max(1, len(ref))


def trim(wav, sr, words):
    """Cut leading/trailing silence using whisper's word bounds (+ small pads)."""
    if not words:
        return wav, words
    a = max(0.0, words[0][1] - 0.06)
    b = min(wav.shape[-1] / sr, words[-1][2] + 0.18)
    return wav[..., int(a * sr):int(b * sr)], [(w, s - a, e - a) for w, s, e in words]


def best(model, lid, text):
    ref = norm_words(spoken(text))
    cands = []
    for k in range(TAKES):
        p = OUT / f"{lid}_{k}.wav"
        if p.exists():                                   # resume: reuse a take already on disk
            wav, _ = ta.load(str(p))
        else:
            torch.manual_seed(1000 * k + sum(map(ord, lid)))
            wav = model.generate(spoken(text), exaggeration=EXAG, cfg_weight=CFG, temperature=TEMP)
            ta.save(str(p), wav, model.sr)
        hw = transcribe(p)
        score = wer(ref, norm_words(" ".join(w for w, _, _ in hw)))
        cands.append((score, k, wav, hw))
        print(f"  {lid} take {k}: wer={score:.2f}  {' '.join(w for w, _, _ in hw)}", flush=True)
        if score == 0 and k >= 1:
            break
    score, k, wav, hw = min(cands, key=lambda c: (c[0], c[1]))
    wav, hw = trim(wav, model.sr, hw)
    return wav, hw, score


def main():
    model = ChatterboxTTS.from_local(str(Path.home() / "models/chatterbox-weights"), device="mps" if torch.backends.mps.is_available() else "cpu")
    sr = model.sr
    lines, chunks, t = [], [], 0.0
    for lid, text in LINES:
        wav, hw, score = best(model, lid, text)
        d = wav.shape[-1] / sr
        lines.append({"id": lid, "text": text, "start": round(t, 3), "end": round(t + d, 3), "wer": round(score, 2),
                      "words": [[w, round(t + s, 3), round(t + e, 3)] for w, s, e in hw]})
        g = GAP_AFTER.get(lid, GAP)
        chunks += [wav, torch.zeros(1, int(g * sr))]
        t += d + g
    story = torch.cat(chunks, dim=-1)
    ta.save(str(OUT / "story.wav"), story, sr)
    owav, ohw, oscore = best(model, OUTRO[0], OUTRO[1])
    ta.save(str(OUT / "outro.wav"), owav, sr)
    meta = {"lines": lines, "dur": round(t, 3),
            "outro": {"text": OUTRO[1], "dur": round(owav.shape[-1] / sr, 3), "wer": round(oscore, 2),
                      "words": [[w, round(s, 3), round(e, 3)] for w, s, e in ohw]}}
    (D / "out" / "words.json").write_text(json.dumps(meta, indent=1))
    print("story", round(t, 2), "s; worst wer", max(l["wer"] for l in lines))


if __name__ == "__main__":
    main()
