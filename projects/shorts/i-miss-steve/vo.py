"""Voice every line of script.json -> public/vo/*.mp3 + vo.json (word times). Cached, so re-runs are free.
usage: python vo.py [voice_id] [stability]"""
import json, sys
from pathlib import Path
from reelforge.shorts import DEFAULTS, tts

d = Path(__file__).parent
voice = {"id": sys.argv[1] if len(sys.argv) > 1 else "nPczCjzI2devNIAzQkzx",  # Brian: deep, resonant narrator
         "model": "eleven_v3", "provider": "fal", "stability": float(sys.argv[2]) if len(sys.argv) > 2 else 0.5}
lines = json.loads((d / "script.json").read_text())
out = []
for text in lines:
    src, words, dur = tts(d, d / "public", voice, text, DEFAULTS["say"])
    out.append({"text": text, "src": src, "dur": round(dur, 2), "words": words})
    print(f"{dur:5.2f}s  {text}")
(d / "vo.json").write_text(json.dumps(out, indent=1))
print("total", round(sum(o["dur"] for o in out), 2))
