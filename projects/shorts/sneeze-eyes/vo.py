"""python vo.py: Brian (premade, direct ElevenLabs) narration → out/vo/<hash>.mp3 + out/words.json.

Facts (checked 2026-11-08, see SCRIPT.md): six extraocular muscles; eye-close reflex cause unknown (germ theory);
Tang et al. high-speed imaging → ~4.5 m/s (~10 mph); BMJ Case Reports Dec 2023, Dundee, tracheal tear stifling a sneeze.
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
         "stability": 0.45, "similarity_boost": 0.8, "style": 0.3}
SAY = {}

SCRIPT = (
    "If you sneeze with your eyes open, your eyeballs pop out of your head. "
    "That's what every kid on the playground said. "
    "But eyes aren't corks. "
    "Six muscles hold each one in its socket, like ropes on a tent. "
    "And a sneeze isn't a hundred miles an hour. Scientists filmed it. About ten. "
    "Your eyes shut anyway, probably to keep germs out. "
    "You can sneeze with them open. It just looks cursed. "
    "The real danger is holding it in. "
    "A man in Scotland pinched his nose, shut his mouth, and tore his windpipe. "
    "His eyes were fine."
)   # 512 chars: trimmed 2026-11-08 to fit the 533 ElevenLabs credits left (quota resets 2026-11-21)

if __name__ == "__main__":
    pub = D / "out"
    mp3, words, dur = tts(D, pub, VOICE, SCRIPT, SAY)
    (pub / "words.json").write_text(json.dumps({"mp3": str(pub / mp3), "dur": dur, "words": words}))
    print(f"{dur:.1f}s, {len(words)} words → {mp3}")
    for w in words:
        print(f"{w[0]:6.2f} {w[1]:6.2f} {w[2]}")
