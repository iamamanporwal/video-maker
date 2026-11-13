"""env -u VIRTUAL_ENV ~/models/kokoro-venv/bin/python vo.py: local Kokoro-82M narration, one call per script line
→ out/vo/story.wav + out/words.json {words:[[s,e,text]], lines:{key:[i0,i1]}} (same shape build.py's recut() expects).
ElevenLabs credits are exhausted until 2026-11-21; fal is off-limits. Facts: RESEARCH.md."""
import json, re, sys
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro import KPipeline

D = Path(__file__).resolve().parent
VOICE = sys.argv[1] if len(sys.argv) > 1 else "am_michael"
SPEED, SR, GAP = 1.15, 24000, 0.12
SAY = {"GTA 6": "G T A six", "Vi3W": "View", "3D": "three D", "Mocap": "Mo-cap"}

if __name__ == "__main__":
    lines = json.loads((D / "script.json").read_text())["lines"]
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    audio, words, spans, off = [], [], {}, 0.0
    for key, text in lines:
        said = text
        for a, b in SAY.items():
            said = said.replace(a, b)
        i0 = len(words)
        for r in pipe(said, voice=VOICE, speed=SPEED, split_pattern=r"\n+"):
            a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
            toks = [t for t in (r.tokens or []) if t.start_ts is not None and re.search(r"\w", t.text)]
            s0 = max(0.0, toks[0].start_ts - 0.04)
            s1 = min(len(a) / SR, (toks[-1].end_ts or toks[-1].start_ts + 0.3) + 0.1)
            a = a[int(s0 * SR):int(s1 * SR)]
            for t in toks:
                words.append([round(off + t.start_ts - s0, 3), round(off + (t.end_ts or t.start_ts + 0.2) - s0, 3), t.text])
            audio += [a, np.zeros(int(SR * GAP), dtype=a.dtype)]
            off += len(a) / SR + GAP
        spans[key] = [i0, len(words)]
        print(f"{key}: {off:6.2f}s  " + " ".join(w[2] for w in words[i0:]))
    out = D / "out" / "vo"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / f"story_{VOICE}.wav", np.concatenate(audio), SR)
    (D / "out" / f"words_{VOICE}.json").write_text(json.dumps({"mp3": str(out / f"story_{VOICE}.wav"), "dur": off, "words": words, "lines": spans}))
    print(f"{VOICE}: {off:.1f}s {len(words)} words")
