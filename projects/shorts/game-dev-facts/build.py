"""Build game-dev-fact shorts (GTA / Minecraft mods; Remotion DevFact) from vo-<id>.json word timings.

usage: .venv/bin/python projects/shorts/game-dev-facts/build.py <01|02> [--stills]
  Same beat sheet as roblox-dev-facts/build2.py: fact hook over footage → stat card → blueprint freeze → Vi3W
  reveal (screen recording, or screenshot → model turntable) → shared outro. Every visual hangs off word times.
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
TEMPO = {"01": 1.15}  # VO speed-up per short (01 runs long at 1.0)

# Vi3W screen recordings: sketch segment (crop, start) → model segment (crop, start, slow-mo so it stays on the
# close-up, optional box over the promo's own lower-third text). Both crops share an aspect ratio.
DEMOS = {
    "jet": {"src": ROOT / "Input/demo1.mp4", "sk": ("2618:1964:0:0", 0.4), "m": ("2618:1964:0:0", 35.9), "speed": 0.35},
    "car": {"src": ROOT / "Input/demo3.mp4", "sk": ("2160:1820:80:0", 1.4), "m": ("2160:1820:80:0", 19.25), "speed": 0.2},
    "chest": {"src": ROOT / "Input/Demo 1.mp4", "sk": ("1080:1080:830:0", 0.8), "m": ("1080:1080:440:0", 20.2), "speed": 0.25,
              "box": "drawbox=x=0:y=905:w=330:h=100:color=0x101114:t=fill"},
    # Hook screenshot → the Vi3W frog model (gta-frog series turntable), both as 1000x1000 squares.
    "frog": {"img": D / "public/img/frog_ss.png", "src": D.parent / "gta-frog/assets/turntable.mp4", "m": ("840:840:285:0", 0.0), "speed": 1.0},
}
CLIPS = {"ao": "clips/ao.mp4", "fr": "clips/fr.mp4"}
SRC = {"clips/ao.mp4": D / "ref/DvZXYF0ErWs.mp4", "clips/fr.mp4": D / "ref/5AM8j4jIJ_I.mp4"}
# Source fit: ArchiveOP is 1280x720 → 1920x1080; Avun Hub is 1080x1906 → padded to 1080x1920.
FIT = {"clips/ao.mp4": "scale=1920:1080:flags=lanczos", "clips/fr.mp4": "pad=1080:1920:0:7"}


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
    if sid == "01":
        return {
            "slug": "devfact-gta-minecraft", "tag": "GAME DEV FACT 🧱", "credit": "🎥 ArchiveOP (@abhasop)", "demo": "car",
            "shots": [("ao", w("rec", 4), 5.0, "wide", 349), ("ao", at["num"], 606.0, "wide", 349),
                      ("ao", w("num", 6), 609.0, "wide", 349), ("ao", at["steal"], 613.0, "wide", 349),
                      ("ao", w("steal", 5), 619.5, "wide", 349), ("ao", w("steal", 13), 617.0, "wide", 349),
                      ("ao", at["model"] - 0.25, 611.0, "wide", 349)],
            "stat": {"from": at["num"] - 0.1, "to": at["steal"] - 0.05, "header": "COPIES SOLD · ALL TIME", "label": "MINECRAFT ⛏️",
                     "value": 350_000_000, "rival": "GTA V: 225M", "rivalValue": 225_000_000, "note": "MOJANG · TAKE-TWO (FEB 2026)"},
            "freeze": [("ao", 5.5, "wide", 349), ("ao", 609.5, "wide", 349)], "chip": "🧱 EVERY BLOCK = A 3D MODEL",
            "name": "Sketch Car 🏎️", "bait": "what should we mod into GTA next? 👇",
            "emphasis": ["minecraft", "gta", "17", "million", "ever", "3d", "car", "minutes"],
            "caption": ("how youtubers put minecraft inside gta 5 🧱🚗\n\n"
                        "\"Playing MINECRAFT in GTA 5!\" by ArchiveOP has 17M+ views. Minecraft (350M+ copies) and GTA V "
                        "(225M, Take-Two Feb 2026) are two of the best-selling games ever. Steve isn't in GTA: modders rebuild "
                        "him as a 3D model (an \"add-on ped\") and install it into the game files with tools like OpenIV. "
                        "Every block, creeper and Steve is a 3D model, so we sketched a car and Vi3W made it 3D.\n\n"
                        "what should we mod into GTA next? 👇\n\n🎥 gameplay: ArchiveOP (youtube.com/@ArchiveOP), used with permission\n"
                        "Sketch → 3D: Vi3W.in\n\n#gta5 #minecraft #gamedev"),
        }
    if sid == "02":
        return {
            "slug": "devfact-frog-mod", "tag": "GAME DEV FACT 🐸", "credit": "🎥 @AvunHub", "demo": "frog",
            "shots": [("fr", w("rec", 4), 0.0, "tall", 365), ("fr", at["num"], 23.2, "tall", 365),
                      ("fr", at["num"] + 1.0, 25.0, "tall", 365), ("fr", at["steal"], 9.0, "tall", 365),
                      ("fr", w("steal", 4), 3.0, "tall", 365), ("fr", at["model"] - 0.25, 15.0, "tall", 365)],
            "stat": {"from": at["num"] - 0.1, "to": at["steal"] - 0.05, "header": "VIEWS · ONE GTA 5 SHORT", "label": "FROG SAVES FRANKLIN 🐸",
                     "value": 23_393_513, "rival": "its next biggest: 13M", "rivalValue": 13_000_000, "note": "YOUTUBE · NOV 2026"},
            "freeze": [("fr", 3.2, "tall", 365), ("fr", 18.5, "tall", 365)], "chip": "🐸 THE FROG = A 3D MODEL",
            "name": "GTA Frog 🐸", "bait": "what should we turn 3D next? 👇",
            "emphasis": ["frog", "23", "million", "mod", "3d", "screenshot"],
            "caption": ("the gta 5 frog isn't from rockstar 🐸\n\n"
                        "Avun Hub's \"Frog Stopped Franklin Just In Time\" has 23M+ views. The frog is a mod: a custom 3D model "
                        "dropped into GTA 5. We took one screenshot of the frog and Vi3W made it 3D.\n\n"
                        "what should we turn 3D next? 👇\n\n🎥 gameplay: @AvunHub, used with permission\n"
                        "Screenshot → 3D: Vi3W.in\n\n#gta5 #gtamods #gamedev"),
        }
    raise SystemExit(f"unknown short {sid}")


# ------------------------------------------------------------------ asset prep

def ensure_clip(key: str) -> str:
    rel = CLIPS[key]
    dst = PUB / rel
    if not dst.exists():  # 30 fps, fitted to what DevFact expects; source audio muted in the shots (music in both sources)
        run(["ffmpeg", "-v", "error", "-y", "-i", SRC[rel], "-vf", f"{FIT[rel]},fps=30", "-c:v", "libx264", "-crf", "16",
             "-preset", "fast", "-an", dst])
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
        inp, vf = ["-ss", str(t), "-i", PUB / ensure_clip(src)], f"crop=1080:1190:0:{off}"
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
    if "img" in d:  # still screenshot (blurred square fill) → turntable
        sq = "scale=1000:1000:force_original_aspect_ratio=decrease"
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{pop:.3f}", "-i", d["img"], "-stream_loop", "-1", "-t", f"{rest:.3f}", "-i", d["src"],
             "-filter_complex", f"[0:v]split[s0][s1];[s0]scale=1000:1000:force_original_aspect_ratio=increase,crop=1000:1000,gblur=sigma=30[bg];"
             f"[s1]{sq}[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,{tail}[a];[1:v]crop={d['m'][0]},{tail}[b];[a][b]concat=n=2:v=1:a=0[v]",
             "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", PUB / rel])
        return {"src": rel, "w": W, "h": H, "label": "HOOK SCREENSHOT → Vi3W", "first": "SCREENSHOT 📸"}
    mvf = f"crop={d['m'][0]}," + (d["box"] + "," if "box" in d else "") + f"setpts=PTS/{d['speed']}," + tail
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(d["sk"][1]), "-t", f"{pop:.3f}", "-i", d["src"],
         "-ss", str(d["m"][1]), "-t", f"{rest * d['speed']:.3f}", "-i", d["src"],
         "-filter_complex", f"[0:v]crop={d['sk'][0]},{tail}[a];[1:v]{mvf}[b];[a][b]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-an",
         "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", PUB / rel])
    return {"src": rel, "w": W, "h": H}


def main() -> None:
    sid = sys.argv[1]
    vo = json.loads((D / f"vo-{sid}.json").read_text())
    tempo = TEMPO.get(sid, 1.0)
    for k in vo:                                                    # word times + durations at the played speed
        vo[k] = vo[k] | {"dur": vo[k]["dur"] / tempo, "words": [[a / tempo, b / tempo, wd] for a, b, wd in vo[k]["words"]]}
    at, t = {}, 0.1
    for k in ORDER:
        t += GAP.get(k, 0)
        at[k] = round(t, 3)
        t += vo[k]["dur"]
    c = cfg(sid, at, vo)
    freeze_from, reveal_from = at["model"] - 0.25, at["sketch"] - 0.1
    pop = at["sketch"] + vo["sketch"]["dur"] + 0.3
    at["meet"] = pop + 0.45
    at["cta"] = at["meet"] + vo["meet"]["dur"] + 0.5               # no shared outro (it's Roblox-specific): CTA line over the reveal
    end = at["cta"] + vo["cta"]["dur"] + 1.2
    outro_from = end

    for k in at:                                                    # VO to -14 LUFS (same as 01)
        src = PUB / vo[k]["src"]
        n = src.with_name(src.stem + (f"-n{tempo}.mp3" if tempo != 1 else "-n.mp3"))
        if not n.exists():
            af = (f"atempo={tempo}," if tempo != 1 else "") + "loudnorm=I=-14:TP=-1.5:LRA=11"
            run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", "48000", n])
        vo[k]["src"] = n.relative_to(PUB).as_posix()
    words = [[F(at[k] + a), F(at[k] + b), wd] for k in at for a, b, wd in vo[k]["words"]]
    w3d = next(a for a, _, wd in vo["model"]["words"] if wd.lower().startswith("3d"))

    shots, t0 = [], 0.0
    for src, until, st, kind, off in c["shots"]:
        rel = src if kind == "img" else ensure_clip(src)
        shots.append({"src": rel, "from": F(t0), "dur": F(until) - F(t0), "at": F(st), "y0": off if kind == "tall" else 0,
                      "kind": kind, "x0": off, "volume": 0})
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
        "outro": {"from": F(end) + 30, "src": ""},
        "words": words, "emphasis": c["emphasis"],
        "vo": [{"src": vo[k]["src"], "from": F(at[k])} for k in at],
        "cues": [
            {"src": "music/pixelland.mp3", "from": 0, "volume": 0.1},  # hook audio is muted (both sources carry music)
            {"src": "sfx/whoosh.mp3", "from": F(s["from"]) - 4, "volume": 0.35},
            {"src": "sfx/boom.mp3", "from": F(s["twist"]["at"] if "twist" in s else at["num"] + vo["num"]["words"][-1][0]), "volume": 0.5},
            {"src": "sfx/freeze.mp3", "from": F(freeze_from), "volume": 0.4},
            {"src": "sfx/whoosh.mp3", "from": F(reveal_from) - 6, "volume": 0.4},
            {"src": "sfx/pop.mp3", "from": F(pop), "volume": 0.55},
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
        for old in out.glob("s_*.png"):
            old.unlink()
        ts = [0.4, at["rec"] + 2.2, at["num"] + 1.0, at["num"] + vo["num"]["dur"] - 0.3, at["steal"] + vo["steal"]["dur"] - 0.3,
              freeze_from + 0.9, at["model"] + w3d + 0.9, reveal_from + 1.0, pop + 0.6, at["meet"] + vo["meet"]["dur"] + 0.6, end - 0.4]
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
