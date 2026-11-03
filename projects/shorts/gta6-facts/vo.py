"""Generate the GTA 6 facts VO lines (fal ElevenLabs v3, Laura) for every episode + the shared plug.

usage: .venv/bin/python projects/shorts/gta6-facts/vo.py [ep ...]   (default: all; finished lines stay cached)
Writes vo.json: {ep: {line: {src, dur, words}}}. Wording must stay inside PLAN.md's safe-wording column.
"""
import json, sys
from pathlib import Path
from dotenv import load_dotenv
D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src")); load_dotenv(ROOT / ".env")
from reelforge import shorts

VOICE = {"id": "FGY2WhTYpPnrIDTdsKH5", "provider": "fal", "model": "eleven_v3", "stability": 0.0}  # Laura
SAY = {"GTA": "G T A", "6": "six", "3D": "three D", "Vi3W": "View", "Vi3W.in": "view dot in", "PS5": "P S five",
       "MrBeast's": "Mister Beast's", "9th": "ninth", "19th": "nineteenth", "12": "twelve", "90": "ninety",
       "24": "twenty-four", "17-year-old": "seventeen-year-old"}
EPS = {
    "01-leak-firestick": {
        "a": "[excited] The guy who leaked GTA 6... did it from a hotel room. With an Amazon Fire Stick.",
        "b": "Police had taken his laptop... so a court heard he used the hotel TV and his phone.",
        "c": "He got 90 secret videos of the game. Rockstar said it cost them five million dollars.",
        "d": "And he's due back in court November 9th... ten days before GTA 6 comes out.",
    },
    "02-trailer-record": {
        "a": "[excited] This GTA 6 trailer leaked the night before... so Rockstar dropped it 12 hours early.",
        "b": "Then it got 90 MILLION views in 24 hours.",
        "c": "That beat MrBeast's record. Guinness made it official.",
        "d": "90 million views... for a game that wasn't even out yet.",
    },
    "03-ps5-billion": {
        "a": "[excited] Rockstar says this whole GTA 6 trailer ran on a PS5.",
        "b": "Not a gaming PC. Not a render farm. Captured in-game, on a PlayStation.",
        "c": "Half of it is actual gameplay. And analysts think the game cost over a BILLION dollars to make.",
        "d": "It comes out November 19th.",
    },
    "plug": {
        "p1": "Rockstar has thousands of devs making cars like these. We just drew one...",
        "p2": "[excited] and Vi3W made it 3D!",
        "p3": "Comment the GTA car we should build next! Vi3W.in",
    },
}


def main():
    want = sys.argv[1:] or list(EPS)
    path = D / "vo.json"
    out = json.loads(path.read_text()) if path.exists() else {}
    for ep in want:
        out[ep] = {}
        for k, t in EPS[ep].items():
            p, words, dur = shorts.tts(D, D / "public", VOICE, t, SAY)
            out[ep][k] = {"src": p, "dur": round(dur, 3), "words": words}
            print(ep, k, round(dur, 2), " ".join(f"{w[2]}@{w[0]:.2f}" for w in words))
        path.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
