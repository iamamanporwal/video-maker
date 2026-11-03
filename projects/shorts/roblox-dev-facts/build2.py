"""Build dev-fact shorts 02-04 (Remotion DevFact) from vo-<id>.json word timings.

usage: .venv/bin/python projects/shorts/roblox-dev-facts/build2.py <02|03|04> [--stills]
  Same beat sheet as 01 (build.py): fact hook over cleared footage → stat card → blueprint freeze → real Vi3W
  screen recording (sketch, cut to 3D) → shared outro. VO lines run back to back; every visual hangs off word times.
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
PUB = D / "public"
F = lambda s: round(s * FPS)  # noqa: E731
ORDER = ["rec", "num", "steal", "model", "sketch", "meet"]
GAP = {"num": 0.12, "steal": 0.1, "model": 0.25, "sketch": 0.3, "meet": 0.45}

# Vi3W screen recordings: sketch segment (crop, start) → model segment (crop, start, slow-mo so it stays on the
# close-up, optional box over the promo's own lower-third text). Both crops share an aspect ratio.
DEMOS = {
    "jet": {"src": ROOT / "Input/demo1.mp4", "sk": ("2618:1964:0:0", 0.4), "m": ("2618:1964:0:0", 35.9), "speed": 0.35},
    "car": {"src": ROOT / "Input/demo3.mp4", "sk": ("2160:1820:80:0", 1.4), "m": ("2160:1820:80:0", 19.25), "speed": 0.3},
    "chest": {"src": ROOT / "Input/Demo 1.mp4", "sk": ("1080:1080:830:0", 0.8), "m": ("1080:1080:440:0", 20.2), "speed": 0.25,
              "box": "drawbox=x=0:y=905:w=330:h=100:color=0x101114:t=fill"},
}
CLIPS = {"fb": "clips/fb.mp4", "b3": "clips/b3.mp4", "bhc": "clips/bh_c5.mp4", "bhu": "clips/bh_un.mp4"}
SRC = {"clips/bh_c5.mp4": D / "ref/bh/C5hwO43G_aw.mp4", "clips/bh_un.mp4": D / "ref/bh/unZxKg5Pe4M.mp4"}


def run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{' '.join(map(str, cmd[:4]))} failed:\n{(r.stderr or r.stdout)[-3000:]}")


# ------------------------------------------------------------------ per-short config
# shots: (clip key or img path, until-anchor seconds, source second, kind, offset); from = previous shot's end.
# kind "tall" offset = y0 (1080x1920 source); "wide" offset = x0 (16:9, 1778 px wide in the band; 698 = right edge,
# clear of the face cam); "img" offset = start pan x.
# freeze: (source, second, kind, x/y) → game/wire stills; tags shown at the start and on the model line's "3D" word.

def cfg(sid: str, at: dict, vo: dict) -> dict:
    end = lambda k: at[k] + vo[k]["dur"]  # noqa: E731
    w = lambda k, i: at[k] + vo[k]["words"][i][0]  # noqa: E731
    if sid == "02":
        return {
            "slug": "devfact-median-dev", "tag": "ROBLOX DEV FACT #2 💸", "credit": "🎥 @EazyEthan", "demo": "jet",
            "shots": [("b3", w("rec", 3), 14.0, "tall", 470), ("fb", end("rec") - 1.4, 0.3, "tall", 460),
                      ("b3", at["num"], 2.2, "tall", 460), ("b3", w("num", 6), 15.0, "tall", 780),
                      ("fb", at["steal"], 8.0, "tall", 780), ("fb", at["model"] - 0.25, 17.0, "tall", 780)],
            "stat": {"from": at["num"] - 0.1, "to": at["model"] - 0.25, "header": "WHAT ROBLOX DEVS MADE (2024)", "prefix": "$",
                     "label": "", "value": 33_900_000, "rival": "TOP 10 DEVS (AVERAGE)", "rivalValue": 33_900_000,
                     "twist": {"at": w("steal", 4) - 0.1, "label": "THE MEDIAN DEV", "value": 1440},
                     "note": "ROBLOX ECONOMIC IMPACT REPORT · DEVEX"},
            "freeze": [("b3", 2.4, "tall", 365), ("b3", 3.4, "tall", 365)], "chip": "📦 EVERY ITEM = A 3D MODEL",
            "name": "Fighter Jet ✈️", "bait": "what should we sketch next? 👇",
            "emphasis": ["billion", "33.9", "million", "1,440", "3d", "jet", "minutes"],
            "caption": ("roblox paid devs over $1B. the median dev made $1,440 💀\n\n"
                        "Top 10 Roblox devs averaged $33.9M (Roblox Economic Impact Report, 2024 earnings). "
                        "The median DevEx creator got $1,440 in the 12 months to June 2025 (Roblox). "
                        "The gap is content, and every new item is a 3D model. Our founder sketched a jet and Vi3W turned it 3D.\n\n"
                        "what should we sketch next? 👇\n\n🎥 gameplay: @EazyEthan\nSketch → Roblox-ready 3D: Vi3W.in\n\n"
                        "#roblox #robloxdev #robloxstudio"),
        }
    if sid == "03":
        return {
            "slug": "devfact-brookhaven", "tag": "ROBLOX DEV FACT #3 🏡", "credit": "🎥 @EazyEthan", "demo": "car",
            "shots": [("bhc", w("rec", 6) - 0.1, 5.2, "wide", 349), ("bhc", at["num"], 28.0, "wide", 349),
                      ("bhc", w("num", 4), 8.0, "wide", 698), ("bhc", at["steal"], 16.0, "wide", 698),
                      ("bhu", at["steal"] + 1.6, 58.0, "wide", 349), ("bhu", at["model"] - 0.25, 106.5, "wide", 698)],
            "stat": {"from": at["num"] - 0.1, "to": at["steal"] - 0.05, "header": "ALL-TIME VISITS (29 SEP 2023)", "label": "BROOKHAVEN 🏡RP",
                     "value": 37_200_000_000, "rival": "people on Earth: ~8B", "rivalValue": 8_000_000_000, "note": "GUINNESS WORLD RECORD"},
            "freeze": [("bhu", 58.0, "wide", 349), ("bhc", 28.0, "wide", 349)], "chip": "🏠 EVERY HOUSE = A 3D MODEL",
            "name": "Sketch Car 🏎️", "bait": "what should we sketch next? 👇",
            "emphasis": ["brookhaven", "37", "billion", "four", "3d", "car"],
            "caption": ("the most visited roblox game ever is literally just a town 🏡\n\n"
                        "Brookhaven RP: 37.2 billion visits by 29 Sep 2023 (Guinness World Records), over 4 for every person on Earth. "
                        "Every house and car in it is a 3D model, so we sketched a car and Vi3W made it 3D.\n\n"
                        "what should we sketch next? 👇\n\n🎥 gameplay: @EazyEthan\nSketch → Roblox-ready 3D: Vi3W.in\n\n"
                        "#roblox #brookhaven #robloxdev"),
        }
    if sid == "04":
        g = lambda n: f"img/g_{n}.png"  # noqa: E731
        return {
            "slug": "devfact-garden-16yo", "tag": "ROBLOX DEV FACT #4 🌱", "credit": "🎨 illustration", "demo": "chest",
            "shots": [(g("teen"), w("rec", 7), 0, "img", 60), (g("garden1"), at["num"], 0, "img", 30),
                      (g("crowd"), at["steal"], 0, "img", 60), (g("money"), at["model"] - 0.25, 0, "img", 40)],
            "stat": {"from": at["num"] - 0.1, "to": at["steal"] - 0.05, "header": "PLAYERS AT THE SAME TIME", "label": "GROW A GARDEN 🌱",
                     "value": 21_600_000, "rival": "Fortnite's record: 15.3M", "rivalValue": 15_300_000, "note": "AP · JUNE 2025"},
            "freeze": [(g("garden1"), 0, "img", 0), (g("money"), 0, "img", 0)], "chip": "🌱 EVERY SEED = A 3D MODEL",
            "name": "Treasure Chest 🪙", "bait": "what should we sketch next? 👇",
            "emphasis": ["16-year-old", "three", "21.6", "million", "12", "3d", "minute"],
            "caption": ("a 16 year old made this roblox game in 3 days. then it beat fortnite 🌱\n\n"
                        "Grow a Garden was built in a few days by a 16-year-old (AP, July 2025), hit 21.6M players at once "
                        "(Fortnite's record: 15.3M) and players spent $12M on it in May 2025 (Calcalist). "
                        "Every seed, pet and crate is a 3D model, so we sketched a chest and Vi3W made it 3D.\n\n"
                        "what should we sketch next? 👇\n\nIllustrations: AI-generated, not game footage.\n"
                        "Sketch → Roblox-ready 3D: Vi3W.in\n\n#roblox #growagarden #robloxdev"),
        }
    raise SystemExit(f"unknown short {sid}")


# ------------------------------------------------------------------ asset prep

def ensure_clip(key: str) -> str:
    rel = CLIPS[key]
    dst = PUB / rel
    if not dst.exists():  # Brookhaven long-form: 1080p, 30 fps, keep audio
        run(["ffmpeg", "-v", "error", "-y", "-i", SRC[rel], "-vf", "fps=30", "-c:v", "libx264", "-crf", "16", "-preset", "fast",
             "-c:a", "aac", "-b:a", "192k", dst])
    return rel


def freeze_still(sid: str, i: int, src: str, t: float, kind: str, off: int) -> tuple[str, str]:
    """Game still (1080x1190, what FreezeView shows) + its cyan edge 'wireframe'."""
    game, wire = f"img/f{sid}_{i}.png", f"img/f{sid}_{i}_wire.png"
    if kind == "img":
        inp, vf = ["-i", PUB / src], "crop=930:1024:(iw-930)/2:0,scale=1080:1190"
    elif kind == "wide":
        x = round(off * 1080 / 1000)                       # band px → source px (band is 1000 tall = 1080 src)
        inp, vf = ["-ss", str(t), "-i", PUB / ensure_clip(src)], f"crop=980:1080:{min(x, 1920 - 980)}:0,scale=1080:1190"
    else:
        inp, vf = ["-ss", str(t), "-i", PUB / CLIPS[src]], f"crop=1080:1190:0:{off}"
    run(["ffmpeg", "-v", "error", "-y", *inp, "-frames:v", "1", "-vf", vf, PUB / game])
    run(["ffmpeg", "-v", "error", "-y", "-i", PUB / game, "-vf",
         "edgedetect=low=0.06:high=0.18,format=rgb24,colorchannelmixer=rr=0.08:gg=0.2:bb=0.24", PUB / wire])
    return game, wire


def demo_clip(sid: str, name: str, pop: float, total: float) -> dict:
    d = DEMOS[name]
    w, h, *_ = map(int, d["m"][0].split(":"))
    W, H = 1000, round(1000 * h / w / 2) * 2
    rel = f"clips/demo_{sid}.mp4"
    tail = f"scale={W}:{H},fps=30,setsar=1"
    rest = total - pop + 0.5
    mvf = f"crop={d['m'][0]}," + (d["box"] + "," if "box" in d else "") + f"setpts=PTS/{d['speed']}," + tail
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(d["sk"][1]), "-t", f"{pop:.3f}", "-i", d["src"],
         "-ss", str(d["m"][1]), "-t", f"{rest * d['speed']:.3f}", "-i", d["src"],
         "-filter_complex", f"[0:v]crop={d['sk'][0]},{tail}[a];[1:v]{mvf}[b];[a][b]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-an",
         "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", PUB / rel])
    return {"src": rel, "w": W, "h": H}


def main() -> None:
    sid = sys.argv[1]
    vo = json.loads((D / f"vo-{sid}.json").read_text())
    at, t = {}, 0.1
    for k in ORDER:
        t += GAP.get(k, 0)
        at[k] = round(t, 3)
        t += vo[k]["dur"]
    c = cfg(sid, at, vo)
    freeze_from, reveal_from = at["model"] - 0.25, at["sketch"] - 0.1
    pop = at["sketch"] + vo["sketch"]["dur"] + 0.3
    at["meet"] = pop + 0.45
    outro_from = at["meet"] + vo["meet"]["dur"] + 1.3
    end = outro_from + 8.8

    for k in at:                                                    # VO to -14 LUFS (same as 01)
        src = PUB / vo[k]["src"]
        n = src.with_name(src.stem + "-n.mp3")
        if not n.exists():
            run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", n])
        vo[k]["src"] = n.relative_to(PUB).as_posix()
    words = [[F(at[k] + a), F(at[k] + b), wd] for k in at for a, b, wd in vo[k]["words"]]
    w3d = next(a for a, _, wd in vo["model"]["words"] if wd.lower().startswith("3d"))

    shots, t0 = [], 0.0
    for src, until, st, kind, off in c["shots"]:
        rel = src if kind == "img" else ensure_clip(src)
        shots.append({"src": rel, "from": F(t0), "dur": F(until) - F(t0), "at": F(st), "y0": off if kind == "tall" else 0,
                      "kind": kind, "x0": off, "volume": 0.2 if kind == "tall" else 0.12})
        t0 = until
    assert abs(t0 - freeze_from) < 0.01, (t0, freeze_from)
    items = []
    for i, (src, st, kind, off) in enumerate(c["freeze"]):
        game, wire = freeze_still(sid, i, src, st, kind, off)
        items.append({"img": game, "wire": wire, "tag": "3D MODEL ✓", "at": 0 if i == 0 else F(at["model"] + w3d) - F(freeze_from) - 4})
    demo = demo_clip(sid, c["demo"], pop - reveal_from, outro_from - reveal_from)
    s = c["stat"]
    stat = {k: v for k, v in s.items() if k not in ("from", "to", "twist")}
    stat |= {"from": F(s["from"]), "dur": F(s["to"]) - F(s["from"])}
    if "twist" in s:
        stat["twist"] = s["twist"] | {"at": F(s["twist"]["at"]) - F(s["from"])}

    props = {
        "fps": FPS, "durationInFrames": F(end), "tag": c["tag"], "credit": c["credit"], "shots": shots, "stat": stat,
        "freeze": {"from": F(freeze_from), "dur": F(reveal_from) - F(freeze_from), "chip": c["chip"], "items": items},
        "reveal": {"from": F(reveal_from), "dur": F(outro_from) - F(reveal_from), "pop": F(pop) - F(reveal_from),
                   "baitAt": F(at["meet"] + vo["meet"]["dur"]) - F(reveal_from), "sketch": "", "model": "", "name": c["name"],
                   "rate": "", "line": "", "bait": c["bait"], "demo": demo},
        "outro": {"from": F(outro_from), "src": "clips/outro.mp4"},
        "words": words, "emphasis": c["emphasis"],
        "vo": [{"src": vo[k]["src"], "from": F(at[k])} for k in at],
        "cues": [
            {"src": "music/pixelland.mp3", "from": 0, "volume": 0.05 if any(x["kind"] == "tall" for x in shots) else 0.1},  # louder bed when the hook has no game audio
            {"src": "sfx/whoosh.mp3", "from": F(s["from"]) - 4, "volume": 0.35},
            {"src": "sfx/boom.mp3", "from": F(s["twist"]["at"] if "twist" in s else at["num"] + vo["num"]["words"][-1][0]), "volume": 0.5},
            {"src": "sfx/freeze.mp3", "from": F(freeze_from), "volume": 0.4},
            {"src": "sfx/whoosh.mp3", "from": F(reveal_from) - 6, "volume": 0.4},
            {"src": "sfx/pop.mp3", "from": F(pop), "volume": 0.55},
            {"src": "sfx/whoosh.mp3", "from": F(outro_from) - 6, "volume": 0.4},
        ],
    }
    sname = f"{sid}-{c['slug'].removeprefix('devfact-')}"
    out = D / "out" / sname
    out.mkdir(parents=True, exist_ok=True)
    pj = out / "props.json"
    pj.write_text(json.dumps(props, indent=1))
    (out / "caption.txt").write_text(c["caption"] + "\n")
    rem = ROOT / "node" / "remotion"
    common = ["--props", str(pj), "--public-dir", str(PUB)]
    if "--stills" in sys.argv:
        ts = [0.4, at["rec"] + 2.2, at["num"] + 1.0, at["num"] + vo["num"]["dur"] - 0.3, at["steal"] + vo["steal"]["dur"] - 0.3,
              freeze_from + 0.9, at["model"] + w3d + 0.9, reveal_from + 1.0, pop + 0.6, at["meet"] + vo["meet"]["dur"] + 0.6, outro_from + 2]
        for x in ts:
            run(["npx", "remotion", "still", "src/shorts/index.ts", "DevFact", out / f"s_{x:05.1f}.png", "--frame", str(F(x))] + common, cwd=rem)
        run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", str(out / "s_*.png"), "-vf", "scale=270:-1,tile=11x1", out / "stills.jpg"])
        print(json.dumps({"stills": str(out / "stills.jpg"), "seconds": round(end, 2), "at": at, "pop": pop}))
        return
    raw = out / f"{sname}.raw.mp4"
    run(["npx", "remotion", "render", "src/shorts/index.ts", "DevFact", raw, "--codec", "h264", "--crf", "16",
         "--pixel-format", "yuv420p", "--image-format", "jpeg", "--jpeg-quality", "95", "--timeout", "240000",
         "--concurrency", "6"] + common, cwd=rem)
    final = out / f"{sname}.mp4"
    media.master(raw, final)
    raw.unlink(missing_ok=True)
    media.contact_sheet(final, out / "contact.jpg", fps=1.0, cols=8, cell_w=180, title=sname)
    print(json.dumps({"file": str(final), "seconds": round(end, 2), "loudness": media.loudness(final)}))


if __name__ == "__main__":
    main()
