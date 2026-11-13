"""~/models/kokoro-venv/bin/python vo.py: local Kokoro-82M TTS (Apache-2.0, af_heart) → out/vo/story.wav + out/words.json.

ElevenLabs was out of credits on 2026-11-08 (21 left, resets 2026-11-21) and fal is off-limits, so this short uses
the free local model. Word timings come from Kokoro's own token timestamps (no whisper pass needed).

Facts (checked 2026-11-08): Randy Gardner, 17, San Diego science fair, Dec 1963 → 8 Jan 1964, 264.4 h (11 days);
stayed up with Coca-Cola, loud music, cold showers (Guinness); moody/uncoordinated by day 3; day 4: street sign was
a person, then believed he was football player Paul Lowe; serial sevens from 100 stopped at 65; slept ~14 h after;
insomnia later in life; Guinness stopped monitoring sleep-deprivation records in 1997 (danger).
"""
import json
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro import KPipeline

D = Path(__file__).resolve().parent
SCRIPT = (
    "If you stayed awake for eleven days, you'd think you'd just be really, really tired. "
    "In nineteen sixty-three, a seventeen-year-old named Randy Gardner actually tried it. For a science fair! "
    "He survived on cola, loud music, and cold showers. "
    "But by day three, his brain started glitching. He got moody, and clumsy. "
    "On day four, he thought a street sign was a person. "
    "Then he decided he was a famous football player. "
    "Near the end, doctors asked him to count down from a hundred, by sevens. "
    "He got to sixty-five, and forgot what he was doing. "
    "After two hundred and sixty-four hours, he finally slept. For fourteen hours straight. "
    "Guinness stopped tracking this record. Too dangerous. "
    "And Randy? Years later... he got insomnia."
)
# caption display forms for spoken words
SHOW = {"nineteen": "1963", "sixty-three,": None, "seventeen-year-old": "17-year-old", "sixty-five,": "65,",
        "two": "264", "hundred": None, "and": None, "sixty-four": None, "fourteen": "14", "eleven": "11"}

if __name__ == "__main__":
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    audio, words, off = [], [], 0.0
    for r in pipe(SCRIPT, voice="af_heart", speed=1.22, split_pattern=r"(?<=[.!?])\s+"):
        a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
        for t in r.tokens or []:
            if t.start_ts is None or not t.text.strip() or all(c in ".,!?;:—…" for c in t.text):
                continue
            w = t.text + (t.whitespace and "" or "")
            words.append([round(off + t.start_ts, 3), round(off + (t.end_ts or t.start_ts + 0.2), 3), w])
        audio.append(a)
        gap = np.zeros(int(24000 * 0.03), dtype=a.dtype)
        audio.append(gap)
        off += (len(a) + len(gap)) / 24000
    out = D / "out" / "vo"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "story.wav", np.concatenate(audio), 24000)
    (D / "out" / "words.json").write_text(json.dumps({"mp3": str(out / "story.wav"), "dur": off, "words": words}))
    print(f"{off:.1f}s {len(words)} words")
    for w in words:
        print(f"{w[0]:6.2f} {w[1]:6.2f} {w[2]}")
