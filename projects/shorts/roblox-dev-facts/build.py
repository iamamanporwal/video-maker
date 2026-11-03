"""Build 01-brainrot-record (Remotion DevFact) from vo.json word timings.

usage: .venv/bin/python projects/shorts/roblox-dev-facts/build.py [--stills]
  VO lines are placed back to back; shots, stat card, freeze and reveal hang off the real word times.
  props → Remotion DevFact → master (-14 LUFS) → out/01-brainrot-record/ + contact sheet + caption.txt.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from reelforge.ops import media  # noqa: E402

FPS = 30
SID = "01-brainrot-record"
PUB = D / "public"
F = lambda s: round(s * FPS)  # noqa: E731


def run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{' '.join(map(str, cmd[:4]))} failed:\n{(r.stderr or r.stdout)[-3000:]}")


def main() -> None:
    vo = json.loads((D / "vo.json").read_text())
    at = {"rec": 0.1, "num": 3.8, "steal": 7.6, "model": 11.6, "sketch": 17.9}
    stat_from, freeze_from, reveal_from = 3.7, 11.35, 17.8
    pop = at["sketch"] + vo["sketch"]["dur"] + 0.3                  # 3D pops in the gap after "brand new one..."
    at["meet"] = pop + 0.45
    outro_from = at["meet"] + vo["meet"]["dur"] + 1.3
    end = outro_from + 8.8

    for k in at:                                                    # VO to -14 LUFS so it sits ~10 dB over the clip
        src = PUB / vo[k]["src"]
        n = src.with_name(src.stem + "-n.mp3")
        if not n.exists():
            run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", str(n)])
        vo[k]["src"] = n.relative_to(PUB).as_posix()
    words = [[F(at[k] + a), F(at[k] + b), w] for k in at for a, b, w in vo[k]["words"]]
    model_word = next(a for a, _, w in vo["model"]["words"] if w.lower().startswith("modeling"))

    shots = [  # (src, from_s, to_s, source_start_s, crop top)
        ("clips/yy.mp4", 0.0, 1.3, 13.5, 800),       # Strawberry Elephant OG, front on
        ("clips/yy.mp4", 1.3, 1.9, 7.9, 760),        # pizza monster grin
        ("clips/yy.mp4", 1.9, 2.75, 14.2, 800),      # elephant running, $420K/s
        ("clips/b3.mp4", 2.75, 3.7, 15.6, 760),      # giant glowing brainrots
        ("clips/b3.mp4", 3.7, 7.6, 13.4, 760),       # base packed with brainrots (under the counter)
        ("clips/yy.mp4", 7.6, 9.2, 3.4, 780),        # RUN!! carrying a brainrot
        ("clips/b3.mp4", 9.2, freeze_from, 0.3, 760),  # Eazy walking his brainrot base
    ]
    props = {
        "fps": FPS, "durationInFrames": F(end),
        "tag": "ROBLOX DEV FACT #1 🧠", "credit": "🎥 @EazyEthan",
        "shots": [{"src": s, "from": F(a), "dur": F(b) - F(a), "at": F(t), "y0": y, "volume": 0.2} for s, a, b, t, y in shots],
        "stat": {"from": F(stat_from), "dur": F(at["steal"]) - F(stat_from), "label": "STEAL A BRAINROT", "value": 25868678,
                 "rival": "Fortnite's record: 15.3M", "rivalValue": 15300000, "note": "GUINNESS WORLD RECORD"},
        "freeze": {"from": F(freeze_from), "dur": F(reveal_from) - F(freeze_from), "chip": "⏳ HOURS PER MODEL 💀",
                   "items": [{"img": "img/game_13.8.png", "wire": "img/wire_13.8.png", "tag": "3D MODEL ✓", "at": 0},
                             {"img": "img/game_8.3.png", "wire": "img/wire_8.3.png", "tag": "3D MODEL ✓",
                              "at": F(at["model"] + model_word) - F(freeze_from) - 4}]},
        "reveal": {"from": F(reveal_from), "dur": F(outro_from) - F(reveal_from), "pop": F(pop) - F(reveal_from),
                   "baitAt": F(at["meet"] + vo["meet"]["dur"]) - F(reveal_from),
                   "sketch": "img/sketch.png", "model": "models/bread-tt-b.webm", "name": "Tostino Squalino", "rate": "💵 $999K/s",
                   "line": "so we drew a *new* one ✏️".replace("*", ""), "bait": "name a better one 👇"},
        "outro": {"from": F(outro_from), "src": "clips/outro.mp4"},
        "words": words,
        "emphasis": ["fortnite's", "25.8", "million", "stealing", "3d", "forever", "tostino", "squalino"],
        "vo": [{"src": vo[k]["src"], "from": F(at[k])} for k in at],
        "cues": [
            {"src": "music/pixelland.mp3", "from": 0, "volume": 0.05},
            {"src": "sfx/whoosh.mp3", "from": F(stat_from) - 4, "volume": 0.35},
            {"src": "sfx/boom.mp3", "from": F(at["steal"] + vo["steal"]["dur"]) + 1, "volume": 0.5},
            {"src": "sfx/freeze.mp3", "from": F(freeze_from), "volume": 0.4},
            {"src": "sfx/whoosh.mp3", "from": F(reveal_from) - 6, "volume": 0.4},
            {"src": "sfx/pop.mp3", "from": F(pop), "volume": 0.55},
            {"src": "sfx/whoosh.mp3", "from": F(outro_from) - 6, "volume": 0.4},
        ],
    }
    out = D / "out" / SID
    out.mkdir(parents=True, exist_ok=True)
    pj = out / "props.json"
    pj.write_text(json.dumps(props, indent=1))
    rem = ROOT / "node" / "remotion"
    common = ["--props", str(pj), "--public-dir", str(PUB)]
    if "--stills" in sys.argv:
        for t in (0.5, 2.5, 5.5, 8.3, 10.3, 12.5, 15.8, 18.6, pop + 1.2, outro_from + 2):
            run(["npx", "remotion", "still", "src/shorts/index.ts", "DevFact", str(out / f"s_{t:05.1f}.png"),
                 "--frame", str(F(t))] + common, cwd=rem)
        print(json.dumps({"stills": str(out), "seconds": round(end, 2)}))
        return
    raw = out / f"{SID}.raw.mp4"
    run(["npx", "remotion", "render", "src/shorts/index.ts", "DevFact", str(raw), "--codec", "h264", "--crf", "16",
         "--pixel-format", "yuv420p", "--image-format", "jpeg", "--jpeg-quality", "95", "--timeout", "240000",
         "--concurrency", "6"] + common, cwd=rem)
    final = out / f"{SID}.mp4"
    media.master(raw, final)
    raw.unlink(missing_ok=True)
    media.contact_sheet(final, out / "contact.jpg", fps=1.0, cols=8, cell_w=180, title=SID)
    print(json.dumps({"file": str(final), "seconds": round(end, 2), "loudness": media.loudness(final)}))


if __name__ == "__main__":
    main()
