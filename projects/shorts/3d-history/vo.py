"""~/models/kokoro-venv/bin/python vo.py: local Kokoro-82M narration (am_michael, documentary read) → out/vo/story.wav
+ out/words.json with word times. ElevenLabs credits are exhausted until 2026-11-21; fal is off-limits.

Facts (checked 2026-11-08): Sketchpad, Ivan Sutherland, MIT 1963, light pen on the room-sized TX-2; Ed Catmull &
Fred Parke "A Computer Animated Hand" 1972 (Utah; polygons drawn on a plaster cast of his hand; National Film
Registry 2011); Martin Newell's Utah teapot 1975; Toy Story 1995 first fully computer-animated feature; 3D Studio MAX
1996, Maya 1998, Blender public 1998 / open source 2002. "Days" for a game character = hedged industry norm.
Vi3W features (sketch/image → 3D, auto-rig, animation, Roblox/Unity export) confirmed live by the owner 2026-11-02.
"""
import json
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro import KPipeline

D = Path(__file__).resolve().parent
VOICE, SPEED, GAP = "am_michael", 1.18, 0.22
SCRIPT = (
    "Three-D modeling is sixty years old. And the hardest part... never changed. "
    "In nineteen sixty-three, Ivan Sutherland drew on a screen with a light pen. The computer filled a whole room. "
    "In nineteen seventy-two, Ed Catmull turned his own hand into polygons, one by one. "
    "In nineteen seventy-five, a teapot became the most famous model in graphics history. "
    "And in nineteen ninety-five, Toy Story became the first fully computer-animated movie. "
    "Then came Maya, three D S Max, and Blender. The pictures got unbelievably good. "
    "But look at the artist. Nineteen ninety-eight. Two thousand eight. Twenty eighteen. Today. "
    "Click a vertex. Drag it. Repeat. Thousands of times. "
    "One game character can still take days. "
    "The graphics evolved. The work didn't. "
    "Now? Draw a sketch. View turns it into a three-D model in seconds. "
    "Auto-rigged, animated, and ready for Roblox or Unity. "
    "Sixty years of clicking... to one sketch."
)
SHOW = {"nineteen": "1963", "sixty-three,": None, "seventeen-year-old": "17-year-old", "sixty-five,": "65,",
        "two": "264", "hundred": None, "and": None, "sixty-four": None, "fourteen": "14", "eleven": "11"}

if __name__ == "__main__":
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    audio, words, off = [], [], 0.0
    for r in pipe(SCRIPT, voice=VOICE, speed=SPEED, split_pattern=r"(?<=[.!?])\s+"):
        a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
        toks = [t for t in (r.tokens or []) if t.start_ts is not None and t.text.strip()
                and not all(c in ".,!?;:—…" for c in t.text)]
        if not toks:
            continue
        s0 = max(0.0, toks[0].start_ts - 0.04)                       # trim Kokoro's lead/tail silence per sentence
        s1 = min(len(a) / 24000, (toks[-1].end_ts or toks[-1].start_ts + 0.3) + 0.12)
        a = a[int(s0 * 24000):int(s1 * 24000)]
        for t in toks:
            words.append([round(off + t.start_ts - s0, 3), round(off + (t.end_ts or t.start_ts + 0.2) - s0, 3), t.text])
        audio.append(a)
        gap = np.zeros(int(24000 * GAP), dtype=a.dtype)
        audio.append(gap)
        off += (len(a) + len(gap)) / 24000
    out = D / "out" / "vo"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "story.wav", np.concatenate(audio), 24000)
    (D / "out" / "words.json").write_text(json.dumps({"mp3": str(out / "story.wav"), "dur": off, "words": words}))
    print(f"{off:.1f}s {len(words)} words")
    for w in words:
        print(f"{w[0]:6.2f} {w[1]:6.2f} {w[2]}")
