"""python vo.py: Laura (eleven_v3, direct ElevenLabs) narration → out/vo/<hash>.mp3 + out/words.json.

The first ~5 s are silent on purpose (channel rule): picture + SFX carry the hook. VO starts at VO_AT in build.py.
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

SCRIPT = (
    "[whispers] Okay... you just stepped on the landlord's dog. "
    "[excited] Don't panic! Just offer it a snack. "
    "[gasps] It ate the snack... and now it wants dessert. "
    "[shouting] RUN! "
    "[laughs] Plot twist... the landlord saw everything. "
    "Rent just went up. "
    "[excited] The bread, the panda, the robot? All made in Vi3W. Draw anything, and get it in 3D. Vi3W.in"
)

if __name__ == "__main__":
    pub = D / "out"
    mp3, words, dur = tts(D, pub, DEFAULTS["voice"], SCRIPT, DEFAULTS["say"])
    (pub / "words.json").write_text(json.dumps({"mp3": str(pub / mp3), "dur": dur, "words": words}))
    print(f"{dur:.1f}s, {len(words)} words → {mp3}")
    for w in words:
        print(f"{w[0]:6.2f} {w[1]:6.2f} {w[2]}")

# v2 ending (2026-11-03, user = Vi3W's owner; the workflow is theirs): separate take for the CTA
CTA = ("[excited] The bread, the panda, the robot? All made in Vi3W. "
       "And this whole video? Made with the Vi3W workflow. Vi3W.in")


def cta():
    pub = D / "out"
    mp3, words, dur = tts(D, pub, DEFAULTS["voice"], CTA, DEFAULTS["say"])
    (pub / "words_cta.json").write_text(json.dumps({"mp3": str(pub / mp3), "dur": dur, "words": words}))
    print(f"CTA {dur:.1f}s")
    for w in words:
        print(f"{w[0]:6.2f} {w[1]:6.2f} {w[2]}")
