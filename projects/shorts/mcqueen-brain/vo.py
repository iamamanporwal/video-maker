"""env -u VIRTUAL_ENV ~/models/kokoro-venv/bin/python vo.py: Kokoro-82M (af_heart, local, free) → out/vo/story.wav + out/words.json.
ElevenLabs credits are 0 until 2026-11-21 and fal is off-limits, so this short uses the local voice.
Comedy/parody: no facts to check. Inspired by the "Cars anatomy" fan-art cutaways.
"""
import json
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro import KPipeline

D = Path(__file__).resolve().parent
SCRIPT = (
    "What if I told you, cars aren't actually machines? "
    "Look inside Lightning McQueen. "
    "Bro has a full human brain. "
    "Right behind the windshield. Which means the windshield is just his eyelids. "
    "The engine? That's his heart. It pumps gasoline. "
    "Down here? Intestines. Like, meters of them. "
    "And the bumper is a mouth. With teeth. "
    "So a pit stop? Four strangers rip his feet off, while he's awake. "
    "And he says thank you. "
    "A car crash isn't a car crash. It's a crime scene. "
    "Which means Mater isn't a tow truck. "
    "He's a hearse. "
    "Anyway. Ka-chow."
)

if __name__ == "__main__":
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    audio, words, off = [], [], 0.0
    for r in pipe(SCRIPT, voice="af_heart", speed=1.18, split_pattern=r"(?<=[.!?])\s+"):
        a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
        for t in r.tokens or []:
            if t.start_ts is None or not t.text.strip() or all(c in ".,!?;:—…" for c in t.text):
                continue
            words.append([round(off + t.start_ts, 3), round(off + (t.end_ts or t.start_ts + 0.2), 3), t.text])
        audio.append(a)
        gap = np.zeros(int(24000 * 0.06), dtype=a.dtype)
        audio.append(gap)
        off += (len(a) + len(gap)) / 24000
    out = D / "out" / "vo"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "story.wav", np.concatenate(audio), 24000)
    (D / "out" / "words.json").write_text(json.dumps({"mp3": str(out / "story.wav"), "dur": off, "words": words}))
    print(f"{off:.1f}s {len(words)} words")
    for w in words:
        print(f"{w[0]:6.2f} {w[1]:6.2f} {w[2]}")
