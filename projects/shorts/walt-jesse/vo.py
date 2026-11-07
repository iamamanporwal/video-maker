"""python vo.py: narration for "What if Walter White never had cancer? (Jesse-style narration)" → out/words.json.

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

VOICE = {"id": "bIHbv24MWmeRgasZH58o", "model": "eleven_v3", "stability": 0.0}      # Will (premade), Jesse-style

LINES = [
    "[excited] Yo. What if Mister White... never got cancer? Like, ever?",          # 0  hook: Heisenberg in the desert
    "Albuquerque, 2008. Dude gets his lungs checked, and the scan comes back...",  # 1  x-ray lightbox
    "[whispers] clean. Clean, yo!",                                                # 2  lungs clear
    "No tumor. No clock ticking. So Walt just goes home, like a total square.",    # 3  hospital bed
    "He never rides along with Hank. He never finds me. Me, bitch!",               # 4  empty desert
    "So no RV. No desert. No blue. Nothing, yo.",                                  # 5  RV + crystals vanish
    "And no pizza on the freakin' roof.",                                          # 6  house roof
    "Instead, he teaches chemistry. For twenty-five more years, man!",             # 7  classroom, years tick
    "He retires, all quiet and boring as shit. Nobody ever knew his name.",        # 8  cake, alone
    "Then Skyler's digging around the garage, and she finds this box.",            # 9  garage box
    "Inside? His formula, yo. Ninety-nine point one percent pure. Never cooked a single batch.",  # 10
    "[serious] Because cancer didn't make Heisenberg, man...",                     # 11 hat on the table
    "It just gave him permission. [laughs] Science, bitch.",                       # 12 Walt + hat, desert dusk
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
