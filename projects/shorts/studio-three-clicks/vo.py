"""Generate word-timed narration for the studio-three-clicks Blender short."""
import json
import os
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))
from reelforge.shorts import DEFAULTS, tts  # noqa: E402

VOICE = {"id": "nPczCjzI2devNBz1zQrb", "model": "eleven_v3", "stability": 0.5}
LINES = [
    "[serious] What if every 3D studio woke up tomorrow and fired its slowest workflow?",
    "Not the artists.",
    "The waiting. The menus. The revisions that kill the idea before it exists.",
    "Because right now, one little sketch can take a whole team through days of software.",
    "But imagine this. Click one: an image. Click two: change anything.",
    "Click three: a real 3D model you can spin, build, and put in a world.",
    "One idea. Game ready. Product ready. Film ready.",
    "That is not fewer artists. It is fewer bottlenecks.",
    "What would your studio make with its time back?",
    "Vi3W. 3D in three clicks.",
]

if __name__ == "__main__":
    out = D / "out"
    mp3, words, duration = tts(D, out, VOICE, " ".join(LINES), DEFAULTS["say"])
    beats, index = [], 0
    for line in LINES:
        beats.append(words[index][0])
        index += len([token for token in line.split() if not token.startswith("[") and not token.endswith("]")])
    if index != len(words):
        raise RuntimeError(f"alignment mismatch: {index} planned words, {len(words)} aligned")
    (out / "words.json").write_text(json.dumps({"mp3": str(out / mp3), "dur": duration, "words": words, "beats": beats}))
    print(f"{duration:.1f}s, {len(words)} words → {mp3}")
