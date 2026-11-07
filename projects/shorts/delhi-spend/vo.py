"""python vo.py: narration for "How much money can you spend in one day in Delhi?" → out/words.json.

ElevenLabs direct API, premade Brian (eleven_v3). One take for the whole story; `beats` stores the start of each
LINES entry so scene.py / build.py can key every shot on real word times (B[k] = start of line k).
"""
import json, os, sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))
from reelforge.shorts import DEFAULTS, tts  # noqa: E402

VOICE = {"id": "nPczCjzI2devNBz1zQrb", "model": "eleven_v3", "stability": 0.5}      # Brian (premade)

LINES = [
    "What if you had one day in Delhi,",                                   # 0  hook: India Gate, cash rain
    "and you had to spend as much money as humanly possible?",            # 1
    "7 AM. You're hungry.",                                               # 2  breakfast
    "So you buy every plate of chole bhature in Chandni Chowk.",          # 3
    "9 AM. Traffic is bad.",                                              # 4  rickshaws
    "So you buy every auto rickshaw in Delhi... and paint them gold.",    # 5
    "11 AM. The Metro is crowded.",                                       # 6  metro
    "So you buy the whole Metro. Now it only stops at your house.",       # 7
    "1 PM. Lunch.",                                                       # 8  butter chicken pool
    "A swimming pool full of butter chicken. [laughs] And you jump in.",  # 9
    "4 PM. Karol Bagh.",                                                  # 10 gold
    "You walk out wearing 80 kilos of gold. You can't move.",             # 11
    "7 PM. You throw a baraat. For no reason.",                           # 12 baraat
    "Ten thousand dhol players. Fireworks.",                              # 13
    "10 PM. The air is bad.",                                             # 14 fan vs smog
    "So you buy a fan as tall as Qutub Minar. All of Delhi can breathe.", # 15
    "Midnight. Total spent: 5 lakh crore rupees.",                        # 16 bank
    "Your bank calls. So you buy the bank.",                              # 17
    "[excited] But the best deal of the day?",                            # 18 Vi3W
    "Draw any sketch, and Vi3W turns it into a 3D model in 30 seconds.",  # 19
]

if __name__ == "__main__":
    pub = D / "out"
    mp3, words, dur = tts(D, pub, VOICE, " ".join(LINES), DEFAULTS["say"])
    beats, i = [], 0
    for ln in LINES:
        beats.append(words[i][0])
        i += len([t for t in ln.split() if not t.startswith("[") and not t.endswith("]")])
    assert i == len(words), (i, len(words))
    (pub / "words.json").write_text(json.dumps({"mp3": str(pub / mp3), "dur": dur, "words": words, "beats": beats}))
    print(f"{dur:.1f}s, {len(words)} words → {mp3}")
    for k, (b, ln) in enumerate(zip(beats, LINES)):
        print(f"{k:2d} {b:6.2f}  {ln}")
