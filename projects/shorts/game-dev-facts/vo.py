"""Generate the VO lines for one game-dev-fact short (fal ElevenLabs v3, Laura) and print word timings.

usage: .venv/bin/python projects/shorts/game-dev-facts/vo.py <01|02>   (→ vo-<id>.json)
"""
import json, sys
from pathlib import Path
from dotenv import load_dotenv
D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src")); load_dotenv(ROOT / ".env")
from reelforge import shorts

VOICE = {"id": "FGY2WhTYpPnrIDTdsKH5", "provider": "fal", "model": "eleven_v3", "stability": 0.0}  # Laura
SAY = {"GTA 5": "G T A five", "3D": "three D", "Vi3W.in": "view dot in", "Vi3W": "View"}
SCRIPTS = {
    "01": {  # gta-minecraft: ArchiveOP 17.2M views; Minecraft 350M+ / GTA V 225M copies (Take-Two, Feb 2026)
        "rec": "[excited] A video of Minecraft... inside GTA 5 got 17 MILLION views.",
        "num": "Two of the best-selling games EVER... smashed into one.",
        "steal": "But Steve isn't in GTA. Modders rebuild him as a 3D model... and drop him into the game files.",
        "model": "Every Steve, every creeper, every block in these videos? That's a 3D model. And that's the slow part.",
        "sketch": "So we sketched a car...",
        "meet": "[excited] and Vi3W made it 3D in minutes!",
        "cta": "Comment what we should mod into GTA next! Vi3W.in",
    },
    "02": {  # frog-mod: Avun Hub 5AM8j4jIJ_I 23.4M views (permission on file, gta-frog/assets/permission.md)
        "rec": "[excited] This GTA 5 frog Short got 23 MILLION views.",
        "num": "Twenty-three million... for a frog saving Franklin.",
        "steal": "And that frog? It's not from Rockstar. It's a mod.",
        "model": "A custom 3D model, dropped into the game. And the model is the hard part.",
        "sketch": "So we took one screenshot of the frog...",
        "meet": "[excited] and Vi3W made it 3D!",
        "cta": "Comment what we should turn 3D next! Vi3W.in",
    },
}


def main():
    sid = sys.argv[1]
    dst = D / f"vo-{sid}.json"
    out = json.loads(dst.read_text()) if dst.exists() else {}
    for k, t in SCRIPTS[sid].items():
        p, words, dur = shorts.tts(D, D / "public", VOICE, t, SAY)
        out[k] = {"src": p, "dur": round(dur, 3), "words": words}
        print(k, round(dur, 2), " ".join(f"{w[2]}@{w[0]:.2f}" for w in words))
        dst.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
