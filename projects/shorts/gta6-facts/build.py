"""Build a GTA 6 dev-fact short (Remotion GtaFact) from vo.json word timings.

usage: .venv/bin/python projects/shorts/gta6-facts/build.py <ep> [--stills]
  ep = 01-leak-firestick | 02-trailer-record | 03-ps5-billion
  Hook lines a-d play back to back (ep TEMPO speeds them up so the plug lands ~20 s), then the shared plug p1-p3.
  Shots, cards and the plug hang off word times: A("b", 5) = start of word 5 of line b.
  props → Remotion → master (-14 LUFS) → out/<ep>/ + contact sheet + caption.txt.
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
GAP = 0.18
F = lambda s: round(s * FPS)  # noqa: E731
CREDIT = "🎥 Rockstar Games · official trailers"
MUSIC_CREDIT = 'Music: "{}" Kevin MacLeod (incompetech.com), CC BY 4.0'
TEMPO = {"01-leak-firestick": 1.15}
PLUG_SHOTS = [("clips/rz.mp4", 46.6, 0, 0.5), ("clips/t1.mp4", 70.3, 4, 0.55), ("clips/t2.mp4", 27.0, 6, 0.5)]  # (src, at, p1 word, x)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{' '.join(map(str, cmd[:4]))} failed:\n{(r.stderr or r.stdout)[-3000:]}")


def episode(ep: str, A) -> dict:
    """Per-episode hook: shots [(src, source_s, start_s, x, flags)], cards, emphasis, music, tag, caption."""
    rz, t1, t2 = "clips/rz.mp4", "clips/t1.mp4", "clips/t2.mp4"
    if ep == "01-leak-firestick":
        shots = [(t1, 48.2, 0, 0.5, "g"), (t1, 13.5, A("a", 4), 0.5, ""), (rz, 36.0, A("a", 6), 0.55, ""), (rz, 29.0, A("a", 12), 0.45, ""),
                 (t2, 50.3, A("b", 0), 0.5, ""), (t1, 8.2, A("b", 5), 0.4, ""), (t2, 129.0, A("b", 11), 0.5, ""),
                 (rz, 52.4, A("c", 0), 0.5, "g"), (t1, 64.0, A("c", 0) + 0.4, 0.5, "g"), (rz, 72.0, A("c", 0) + 0.8, 0.45, "g"),
                 (rz, 60.0, A("c", 0) + 1.2, 0.5, "g"), (t1, 77.0, A("c", 0) + 1.6, 0.5, "g"),
                 (t2, 76.0, A("c", 8), 0.5, ""), (t1, 5.5, A("d", 0), 0.5, ""), (rz, 81.5, A("d", 8), 0.5, "")]
        cards = [
            {"kind": "list", "from": A("a", 14), "to": A("c", 0), "title": "THE HACK SETUP 🤯",
             "items": [{"icon": "🔥", "text": "FIRE STICK", "at": A("a", 15)}, {"icon": "📺", "text": "HOTEL TV", "at": A("b", 12)},
                       {"icon": "📱", "text": "PHONE", "at": A("b", 15)}]},
            {"kind": "stamp", "from": A("c", 2), "to": A("c", 8), "text": "LEAKED", "sub": "90 SECRET VIDEOS"},
            {"kind": "counter", "from": A("c", 8), "to": A("d", 0), "prefix": "$", "value": 5_000_000, "label": "WHAT THE LEAK COST ROCKSTAR",
             "note": "+ THOUSANDS OF STAFF HOURS"},
            {"kind": "stamp", "from": A("d", 6), "to": A("d", 8) + 0.2, "text": "NOV 9", "sub": "BACK IN COURT ⚖️", "color": "#FFE14D"},
        ]
        em = ["amazon", "fire", "stick", "hotel", "tv", "phone", "90", "secret", "five", "million", "november", "9th"]
        return {"tag": "GTA 6 DEV FACT #1 🕵️", "shots": shots, "cards": cards, "emphasis": em, "music": "investigations",
                "caption": ("the GTA 6 leak was done with a FIRE STICK 💀 and he's back in court 10 days before launch\n\n"
                            "comment the GTA car we should 3D next 👇 we'll make it in Vi3W\n\n"
                            "#gta6 #gtavi #rockstargames #gamedev #gta6leak #gaming #3dmodeling")}
    if ep == "02-trailer-record":
        shots = [(t1, 3.2, 0, 0.5, ""), (t1, 48.2, A("a", 4), 0.5, "g"), (t1, 13.0, A("a", 8), 0.5, ""), (t1, 22.0, A("a", 12), 0.5, ""),
                 (t1, 25.5, A("b", 0), 0.5, ""), (t1, 34.0, A("b", 3), 0.5, ""), (t1, 36.0, A("c", 0), 0.5, ""), (t1, 40.0, A("c", 4), 0.5, ""),
                 (t1, 66.0, A("d", 0), 0.5, ""), (t1, 31.0, A("d", 5), 0.5, ""), (t1, 77.0, A("d", 8), 0.5, "")]
        cards = [
            {"kind": "stamp", "from": A("a", 4), "to": A("a", 8), "text": "LEAKED", "sub": "THE NIGHT BEFORE 😳"},
            {"kind": "stamp", "from": A("a", 12), "to": A("b", 0), "text": "12 HRS", "sub": "EARLY DROP 🚨", "color": "#FFE14D"},
            {"kind": "counter", "from": A("b", 2), "to": A("d", 0), "value": 90_421_491, "label": "VIEWS IN 24 HOURS",
             "rival": {"label": "MrBeast's record: 59.4M", "value": 59_400_000}, "note": "GUINNESS WORLD RECORD"},
        ]
        em = ["12", "90", "million", "mrbeast's", "guinness", "official"]
        return {"tag": "GTA 6 DEV FACT #2 📈", "shots": shots, "cards": cards, "emphasis": em, "music": "hitman",
                "caption": ("GTA 6 trailer leaked… then broke MrBeast's record 😳 90M views in 24h\n\n"
                            "comment the GTA car we should 3D next 👇 we'll make it in Vi3W\n\n"
                            "#gta6 #gtavi #rockstargames #gamedev #mrbeast #gaming #3dmodeling")}
    if ep == "03-ps5-billion":
        shots = [(t2, 8.0, 0, 0.5, ""), (t2, 9.0, A("a", 4), 0.5, ""), (t2, 38.5, A("a", 7), 0.45, ""),
                 (t2, 25.5, A("b", 0), 0.5, ""), (t2, 36.0, A("b", 4), 0.5, ""), (t2, 140.5, A("b", 8), 0.5, ""),
                 (t2, 142.5, A("c", 0), 0.5, ""), (t2, 11.5, A("c", 4), 0.5, ""), (rz, 49.0, A("c", 6), 0.5, ""),
                 (rz, 60.0, A("c", 10), 0.5, ""), (rz, 72.0, A("c", 14), 0.45, ""), (rz, 81.5, A("d", 0), 0.5, "")]
        cards = [
            {"kind": "stamp", "from": A("a", 10), "to": A("b", 0) + 0.3, "text": "PS5 ✓", "sub": "CAPTURED IN-GAME", "color": "#4FA3FF"},
            {"kind": "counter", "from": A("c", 10), "to": A("d", 0), "prefix": "$", "value": 1_000_000_000, "suffix": "+",
             "label": "ANALYST BUDGET ESTIMATE", "note": "MOST EXPENSIVE GAME EVER?"},
            {"kind": "stamp", "from": A("d", 3), "to": A("d", 4) + 1.0, "text": "NOV 19", "sub": "2026 🔥", "color": "#FFE14D"},
        ]
        em = ["ps5", "playstation", "gameplay", "billion", "november", "19th"]
        return {"tag": "GTA 6 DEV FACT #3 🎮", "shots": shots, "cards": cards, "emphasis": em, "music": "hitman",
                "caption": ("this whole GTA 6 trailer ran on a PS5 🤯 and it might be the most expensive game ever\n\n"
                            "comment the GTA car we should 3D next 👇 we'll make it in Vi3W\n\n"
                            "#gta6 #gtavi #rockstargames #gamedev #ps5 #gaming #3dmodeling")}
    raise SystemExit(f"unknown episode {ep}")


def norm(src: str, tempo: float) -> str:
    """VO → -14 LUFS (and sped up by `tempo`), cached next to the original."""
    p = PUB / src
    n = p.with_name(f"{p.stem}-n{'' if tempo == 1 else tempo}.mp3")
    if not n.exists():
        af = (f"atempo={tempo}," if tempo != 1 else "") + "loudnorm=I=-14:TP=-1.5:LRA=11"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-af", af, "-ar", "48000", str(n)])
    return n.relative_to(PUB).as_posix()


def main() -> None:
    ep = sys.argv[1]
    allvo = json.loads((D / "vo.json").read_text())
    tempo = TEMPO.get(ep, 1.0)
    lines: dict[str, dict] = {}
    t = 0.1
    for k, v in allvo[ep].items():                                   # hook a-d back to back
        lines[k] = {"at": t, "tempo": tempo, **v}
        t += v["dur"] / tempo + GAP
    plug_cut = t + 0.25
    t = plug_cut + 0.15
    for k, v in allvo["plug"].items():                               # plug p1-p3
        lines[k] = {"at": t, "tempo": 1.0, **v}
        t += v["dur"] + (0.55 if k == "p1" else 0.35)
    A = lambda k, i: lines[k]["at"] + lines[k]["words"][i][0] / lines[k]["tempo"]  # noqa: E731

    e = episode(ep, A)
    sketch_at = A("p1", 9) - 0.1                                      # "We just drew one..."
    pop = A("p2", 2) - 0.05                                           # "...made it 3D!"
    end_at = lines["p3"]["at"]
    end = lines["p3"]["at"] + lines["p3"]["dur"] + 1.6

    shots = e["shots"] + [(s, at, A("p1", w), x, "") for s, at, w, x in PLUG_SHOTS]
    shots.sort(key=lambda s: s[2])
    starts = [s[2] for s in shots] + [sketch_at]
    words = [[F(L["at"] + a / L["tempo"]), F(L["at"] + b / L["tempo"]), w] for L in lines.values() for a, b, w in L["words"]]
    p1_card = {"kind": "list", "from": A("p1", 0), "to": sketch_at, "title": "HOW ROCKSTAR BUILDS IT",
               "items": [{"icon": "🧑‍💻", "text": "1000s OF DEVS", "at": A("p1", 2)}, {"icon": "⏳", "text": "YEARS OF WORK", "at": A("p1", 6)}]}
    cards = []
    for c in e["cards"] + [p1_card]:
        c = dict(c)
        a, b = c.pop("from"), c.pop("to")
        if "items" in c:
            c["items"] = [{**it, "at": F(it["at"]) - F(a)} for it in c["items"]]
        cards.append({**c, "from": F(a), "dur": F(b) - F(a)})

    sfx = [{"src": "sfx/whoosh.mp3", "from": F(c["from"] / FPS) - 4, "volume": 0.3} for c in cards if c["kind"] != "stamp"]
    sfx += [{"src": "sfx/boom.mp3", "from": c["from"], "volume": 0.45} for c in cards if c["kind"] == "stamp"]
    sfx += [{"src": "sfx/pop.mp3", "from": c["from"] + it["at"], "volume": 0.35} for c in cards if c["kind"] == "list" for it in c["items"]]
    props = {
        "fps": FPS, "durationInFrames": F(end), "tag": e["tag"], "credit": CREDIT,
        "shots": [{"src": s, "from": F(a), "dur": F(starts[i + 1]) - F(a), "at": F(at), "x": x, "glitch": "g" in fl}
                  for i, (s, at, a, x, fl) in enumerate(shots)],
        "cards": cards,
        "plug": {"from": F(sketch_at), "pop": F(pop) - F(sketch_at), "end": F(end_at) - F(sketch_at),
                 "sketch": "img/sketch.png", "render": "img/render.png", "model": "clips/car3d_b.mp4", "logo": "img/logo.png",
                 "url": "Vi3W.in", "bait": "comment the GTA car we should 3D next 👇"},
        "words": words,
        "emphasis": e["emphasis"] + ["3d!", "vi3w.in"],
        "vo": [{"src": norm(L["src"], L["tempo"]), "from": F(L["at"])} for L in lines.values()],
        "cues": [{"src": f"music/{e['music']}.mp3", "from": 0, "volume": 0.11, "dur": F(end)},
                 {"src": "sfx/whoosh.mp3", "from": F(sketch_at) - 6, "volume": 0.4},
                 {"src": "sfx/pop.mp3", "from": F(pop), "volume": 0.55},
                 {"src": "sfx/ding.mp3", "from": F(end_at), "volume": 0.4}] + sfx,
    }
    out = D / "out" / ep
    out.mkdir(parents=True, exist_ok=True)
    pj = out / "props.json"
    pj.write_text(json.dumps(props, indent=1))
    rem = ROOT / "node" / "remotion"
    common = ["--props", str(pj), "--public-dir", str(PUB)]
    if "--stills" in sys.argv:
        ts = sorted({0.6} | {round(s[2] + 0.5, 1) for s in shots} | {round(sketch_at + 0.6, 1), round(pop + 0.8, 1), round(end_at + 0.8, 1)})
        for x in ts:
            run(["npx", "remotion", "still", "src/shorts/index.ts", "GtaFact", str(out / f"s_{x:05.1f}.png"), "--frame", str(F(x))] + common, cwd=rem)
        print(json.dumps({"stills": str(out), "seconds": round(end, 2), "plug_at": round(plug_cut, 2)}))
        return
    raw = out / f"{ep}.raw.mp4"
    run(["npx", "remotion", "render", "src/shorts/index.ts", "GtaFact", str(raw), "--codec", "h264", "--crf", "16",
         "--pixel-format", "yuv420p", "--image-format", "jpeg", "--jpeg-quality", "95", "--timeout", "240000",
         "--concurrency", "6"] + common, cwd=rem)
    final = out / f"gta6-{ep}.mp4"
    media.master(raw, final)
    raw.unlink(missing_ok=True)
    media.contact_sheet(final, out / "contact.jpg", fps=1.0, cols=8, cell_w=180, title=ep)
    music = {"investigations": "Investigations", "hitman": "Hitman"}[e["music"]]
    (out / "caption.txt").write_text(e["caption"] + "\n\n" + MUSIC_CREDIT.format(music) + "\nFootage: official GTA VI trailers © Rockstar Games (commentary)\n")
    print(json.dumps({"file": str(final), "seconds": round(end, 2), "plug_at": round(plug_cut, 2), "loudness": media.loudness(final)}))


if __name__ == "__main__":
    main()
