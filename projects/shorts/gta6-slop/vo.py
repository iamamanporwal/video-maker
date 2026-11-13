"""env -u VIRTUAL_ENV ~/models/kokoro-venv/bin/python vo.py: deadpan narrator (Kokoro am_michael, local, free)
→ out/vo/story.wav + out/words.json (+ line start times). ElevenLabs credits are 0 until 2026-11-21.

Lines are generated one by one so the comedic pauses are exact (GAP after each line).
"""
import json
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro import KPipeline

D = Path(__file__).resolve().parent
VOICE, SPEED, SR = "am_michael", 1.22, 24000
LINES = [  # (id, text, pause after)
    ("hook", "GTA six is the biggest AI slop ever made.", 0.35),
    ("five", "It looks like a five-year-old made it, with Claude Opus five point five.", 0.45),
    ("cooked", "And honestly?", 0.25),
    ("cooked2", "That five-year-old cooked.", 0.6),
    ("pivot", "Oh, and to the guy typing, your AI slop bores me.", 0.55),
    ("j1", "Your mom's so big, Rockstar delayed GTA six just to fit her on the map.", 0.45),
    ("j2", "Your mom's so old, her first prompt was carved in stone.", 0.45),
    ("j3", "Your mom's so bad at games, she got a five star wanted level in Animal Crossing.", 0.45),
    ("j4", "Your mom thinks Opus five point five is a perfume.", 0.45),
    ("j5", "Your mom is so slop, even Claude refused to generate her.", 0.6),
    ("j6", "AI slop bores you? Bro.", 0.3),
    ("j6b", "Your mom typed, make me a son.", 0.35),
    ("j6c", "Got you.", 0.45),
    ("j6d", "And didn't even hit regenerate.", 0.8),
    ("end", "Anyway.", 0.3),
    ("end2", "I was the five-year-old.", 0.3),
]

if __name__ == "__main__":
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    audio, words, starts, off = [], [], {}, 0.15
    audio.append(np.zeros(int(SR * off), dtype=np.float32))
    for lid, text, gap in LINES:
        starts[lid] = round(off, 3)
        for r in pipe(text, voice=VOICE, speed=SPEED):
            a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
            toks = [t for t in r.tokens or [] if t.start_ts is not None and t.text.strip()
                    and not all(c in ".,!?;:—…" for c in t.text)]
            # trim Kokoro's built-in lead/tail silence so pauses are only the GAPs we choose
            lead = max(0.0, toks[0].start_ts - 0.04)
            tail = (toks[-1].end_ts or toks[-1].start_ts + 0.3) + 0.12
            a = a[int(lead * SR): int(tail * SR)]
            for t in toks:
                words.append([round(off + t.start_ts - lead, 3), round(off + (t.end_ts or t.start_ts + 0.2) - lead, 3),
                              t.text, lid])
            audio.append(a.astype(np.float32))
            off += len(a) / SR
        audio.append(np.zeros(int(SR * gap), dtype=np.float32))
        off += gap
    out = D / "out" / "vo"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "story.wav", np.concatenate(audio), SR)
    (D / "out" / "words.json").write_text(json.dumps({"mp3": str(out / "story.wav"), "dur": off, "words": words,
                                                       "starts": starts}))
    print(f"{off:.2f}s {len(words)} words")
    for lid, s in starts.items():
        print(f"{s:6.2f} {lid}")
