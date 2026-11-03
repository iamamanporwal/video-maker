"""Generate the VO lines for one dev-fact short (fal ElevenLabs v3, Laura) and print word timings.

usage: .venv/bin/python projects/shorts/roblox-dev-facts/vo.py [01|02|03|04]   (default 01 → vo.json, others → vo-<id>.json)
"""
import json, sys
from pathlib import Path
from dotenv import load_dotenv
D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src")); load_dotenv(ROOT / ".env")
from reelforge import shorts

VOICE = {"id": "FGY2WhTYpPnrIDTdsKH5", "provider": "fal", "model": "eleven_v3", "stability": 0.0}  # Laura
SAY = {"25.8": "twenty-five point eight", "33.9": "thirty-three point nine", "21.6": "twenty-one point six",
       "37": "thirty-seven", "1,440": "fourteen hundred and forty", "3D": "three D", "Vi3W": "View"}
SCRIPTS = {
    "01": {
        "rec": "[excited] This Roblox game broke Fortnite's all-time player record.",
        "num": "25.8 MILLION people... playing at the same time.",
        "steal": "And the whole game is literally... stealing memes.",
        "model": "But every brainrot in it? That's a 3D model. And modeling them takes forever.",
        "sketch": "So we sketched a brand new one...",
        "meet": "[excited] Meet Tostino Squalino!",
    },
    "02": {  # median-dev: Roblox newsroom (DevEx >$1B, median $1,440) + Economic Impact Report (top 10 avg $33.9M)
        "rec": "[excited] Roblox paid its devs over one billion dollars in a single year.",
        "num": "The top ten devs? They averaged 33.9 MILLION dollars. Each.",
        "steal": "And the median dev?... 1,440 dollars.",
        "model": "The difference? Top games keep shipping new stuff. And every new item is a 3D model.",
        "sketch": "So our founder sketched a fighter jet...",
        "meet": "[excited] and Vi3W turned it 3D in minutes!",
    },
    "03": {  # brookhaven: Guinness 37.2B visits (29 Sep 2023); world population ~8B
        "rec": "[excited] The most visited Roblox game of all time? Brookhaven.",
        "num": "Guinness counted 37 BILLION visits... and that was back in 2023.",
        "steal": "That's over four visits for every human on Earth.",
        "model": "And every house and every car in it? That's a 3D model. And modeling them takes forever.",
        "sketch": "So we sketched a car...",
        "meet": "[excited] and Vi3W made it 3D!",
    },
    "04": {  # garden: AP / Fortune 2025-07-30 (16-year-old, few days, 21.6M); Ctech ($12M in May 2025)
        "rec": "[excited] A 16-year-old built a Roblox game called Grow a Garden... in about three days.",
        "num": "Months later, 21.6 MILLION people played it at once. More than Fortnite's record.",
        "steal": "And players spent 12 million dollars on it... in one month.",
        "model": "Every seed, every pet, every crate in it? That's a 3D model.",
        "sketch": "So we sketched a treasure chest...",
        "meet": "[excited] and Vi3W made it 3D in about a minute!",
    },
}


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else "01"
    dst = D / ("vo.json" if sid == "01" else f"vo-{sid}.json")
    out = json.loads(dst.read_text()) if dst.exists() else {}
    for k, t in SCRIPTS[sid].items():
        p, words, dur = shorts.tts(D, D / "public", VOICE, t, SAY)
        out[k] = {"src": p, "dur": round(dur, 3), "words": words}
        print(k, round(dur, 2), " ".join(f"{w[2]}@{w[0]:.2f}" for w in words))
        dst.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
