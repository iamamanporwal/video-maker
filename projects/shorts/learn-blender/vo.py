"""python vo.py: dramatic narration via ElevenLabs direct API (premade Brian) → out/words.json.
Comedy exaggeration (19 h/day, 14 burgers, +20 kg) is deliberate; the Vi3W claims are the real product."""
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
         "stability": 0.38, "similarity_boost": 0.8, "style": 0.35}
SAY = {"3D": "three D", "Vi3W": "View", "300": "three hundred", "19": "nineteen", "9": "nine", "14": "fourteen",
       "20": "twenty", "99%": "ninety-nine percent", "30": "thirty"}

SCRIPT = (
    "What if you tried to learn Blender today? "
    "Day one. You open it. A grey cube stares back at you. 300 buttons. Zero idea. "
    "So you watch the famous donut tutorial. Four hours later, your donut looks like a tire. "
    "Day thirty. You sit there 19 hours a day. No sunlight. No friends. Just you and the shortcuts. "
    "Finally, you hit render. Estimated time: 9 hours. So you wait. And you eat a burger. Then another one. "
    "Then 14 more. You gain 20 kilos. "
    "And at 99%... Blender crashes. You didn't save. "
    "Six months. One chair. Zero models. "
    "Or... you just sketch it. On Vi3W, you draw anything, and it turns into a 3D model in under 30 seconds. "
    "No cube. No crashes. No burgers."
)

if __name__ == "__main__":
    pub = D / "out"
    mp3, words, dur = tts(D, pub, VOICE, SCRIPT, SAY)
    (pub / "words.json").write_text(json.dumps({"mp3": str(pub / mp3), "dur": dur, "words": words}))
    print(f"{dur:.1f}s, {len(words)} words → {mp3}")
