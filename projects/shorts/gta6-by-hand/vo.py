"""python vo.py: whole script in ONE Brian take (direct ElevenLabs, premade) → out/words.json with per-line word spans."""
import json, os, sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))
from reelforge.shorts import tts  # noqa: E402

VOICE = {"id": "nPczCjzI2devNBz1zQrb", "model": "eleven_multilingual_v2",   # Brian (premade)
         "stability": 0.36, "similarity_boost": 0.8, "style": 0.4}
SAY = {"GTA": "G T A", "PS4": "P S four", "PS5": "P S five", "1.3": "one point three", "100-hour": "hundred-hour",
       "4,700": "forty-seven hundred", "2025": "twenty twenty-five", "2026": "twenty twenty-six", "19th": "nineteenth",
       "NPCs": "N P Cs", "3D": "three D", "Vi3W": "View"}

if __name__ == "__main__":
    lines = json.loads((D / "script.json").read_text())["lines"]
    text = " ".join(t for _, t in lines)
    out = D / "out"
    mp3, words, dur = tts(D, out, VOICE, text, SAY)
    spans, i = {}, 0
    for k, t in lines:
        n = len(t.split())
        spans[k] = [i, i + n]
        i += n
    assert i == len(words), (i, len(words))
    (out / "words.json").write_text(json.dumps({"mp3": str(out / mp3), "dur": dur, "words": words, "lines": spans}))
    print(f"{dur:.1f}s, {len(words)} words → {mp3}")
