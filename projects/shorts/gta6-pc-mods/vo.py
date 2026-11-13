"""env -u VIRTUAL_ENV ~/models/kokoro-venv/bin/python vo.py: narrator (Kokoro af_heart, local, free)
→ out/vo/story.wav + out/words.json (+ line start times). ElevenLabs credits are 0 until 2026-11-21.

Lines are generated one by one so the comedic pauses are exact (GAP after each line).
"""
import json
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro import KPipeline

D = Path(__file__).resolve().parent
VOICE, SPEED, SR = "af_heart", 1.2, 24000
LINES = [  # (id, text, pause after)
    ("hook", "This is why GTA six isn't coming to PC.", 0.4),
    ("date", "It launches November nineteenth. PlayStation and Xbox only.", 0.35),
    ("wait", "Last time, PC players waited nineteen months for GTA five.", 0.35),
    ("why", "Rockstar won't say why.", 0.2),
    ("why2", "But I know why.", 0.35),
    ("sec", "Because the second it hits PC...", 0.15),
    ("sec2", "this happens.", 0.3),
    ("m1", "Toilets with engines.", 0.6),
    ("m2", "A man riding a cow.", 0.7),
    ("m3", "A speedboat, on the highway.", 0.6),
    ("m4", "Wheelchairs with jet engines.", 0.5),
    ("day", "Now imagine GTA six. Day one on PC.", 0.35),
    ("h1", "Hour one. Everyone's a giant.", 0.55),
    ("h3", "Hour three. It's raining cows.", 0.55),
    ("h6", "Hour six. The cops forgot how to move.", 0.55),
    ("h9", "Hour nine. Rockstar unplugs the internet.", 0.6),
    ("end", "Yeah.", 0.2),
    ("end2", "That's why.", 0.3),
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
