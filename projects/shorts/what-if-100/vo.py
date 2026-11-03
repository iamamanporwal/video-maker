"""python vo.py: narration via ElevenLabs direct API (premade Brian) → vo/<hash>.mp3 + out/words.json.

Facts (checked 2026-11-03):
  refractory period: cause still debated (prolactin theory challenged, Valente et al. 2021, Commun Biol)
  ~100 kcal per session for men (Frappier et al. 2013, PLoS ONE: 101 kcal mean)
  heart rate rarely above ~130 bpm (AHA scientific statement, Levine et al. 2012, Circulation)
  ~1 in 5 people in the US had an STI on any given day (CDC, 2018 data, published Jan 2021)
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
from reelforge.shorts import tts  # noqa: E402

VOICE = {"id": "nPczCjzI2devNBz1zQrb", "model": "eleven_multilingual_v2",   # Brian (premade)
         "stability": 0.42, "similarity_boost": 0.8, "style": 0.25}
SAY = {"100": "one hundred", "1,440": "fourteen hundred and forty", "14": "fourteen", "130": "a hundred and thirty", "1": "one", "5": "five", "20": "twenty",
       "90-something": "ninety-something"}

SCRIPT = (
    "What if you tried to sleep with 100 women in a single day? "
    "First, the math. A day has 1,440 minutes. Divide that by 100, and you get just 14 minutes per woman. "
    "No sleep. No food. No breaks. "
    "Woman number 1? Easy. "
    "But the moment you finish, your body slams on the brakes. It's called the refractory period, and it can last "
    "anywhere from a few minutes to a whole day. Scientists still argue about what causes it. "
    "So by woman number 5, you're already way behind schedule. "
    "Then, the tank starts running dry. Every round drains your sperm reserves, and refilling them takes days. "
    "Meanwhile, each round burns about 100 calories and can push your heart to around 130 beats per minute. "
    "Every 14 minutes. All day long. "
    "But the real danger isn't exhaustion. On any given day, about 1 in 5 Americans has a sexually transmitted "
    "infection. Line up 100 people, and that's roughly 20 of them. "
    "So how far would you actually get? For most men, a handful. Maybe less. "
    "The other 90-something women go home. And you? You sleep for a very, very long time."
)

if __name__ == "__main__":
    pub = D / "out"
    mp3, words, dur = tts(D, pub, VOICE, SCRIPT, SAY)
    (pub / "words.json").write_text(json.dumps({"mp3": str(pub / mp3), "dur": dur, "words": words}))
    print(f"{dur:.1f}s, {len(words)} words → {mp3}")
