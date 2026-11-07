"""Why did GTA 6 take 13 years? Satirical mini-doc → Remotion Gta13 + shared Vi3W outro.

usage: .venv/bin/python projects/shorts/gta6-13-years/build.py [--preview]
  1. recut the single Brian take (out/words.json from vo.py): cap pauses, drop cut words, atempo TEMPO → out/vo_recut.wav
  2. shot list + overlays keyed to recut word times: A("m2", 6) = start of word 6 of line m2 (seconds)
  3. pre-cut every footage shot to a small h264 clip (public/clips/cut) so the Remotion bundle stays small
  4. Remotion renders picture + SFX → ffmpeg: + outro clip, VO (story + fresh outro take), music ducked under the voice
  5. -14 LUFS master → out/gta6-13-years.mp4, contact sheet, caption.txt, FinalUploads/Drafts copy
Footage: official Rockstar trailers only (ref/SOURCES.md), muted. Facts: RESEARCH.md (safe wording only).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
import os  # noqa: E402
for _l in (ROOT / ".env").read_text().splitlines():
    if "=" in _l and not _l.lstrip().startswith("#"):
        _k, _v = _l.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
from reelforge import outro  # noqa: E402
from reelforge.ops import media  # noqa: E402

NAME = "gta6-13-years"
FPS, SR = 30, 48000
OUT, PUB = D / "out", D / "public"
TEMPO = 1.16
VO_AT = 0.25
DROP = {("end", i) for i in range(8)}          # "Thirteen years and 4,700 people for one world."
GAP_IN, GAP_LINE = 0.2, 0.28                    # max pause inside a line / between lines (source seconds)
BEAT = {"hook2": 0.3, "hook3": 0.5, "m3": 0.35, "m5": 0.55, "c3": 0.5, "w3": 0.45, "w5": 0.4, "d2": 0.45}  # held beats after lines
MUSIC = ROOT / "projects/shorts/gta6-facts/public/music/hitman.mp3"       # Kevin MacLeod "Hitman", CC BY 4.0
F = lambda s: round(s * FPS)  # noqa: E731

SRC = {  # official Rockstar uploads (h264 copies) + GTA VI trailers from the gta6-facts project
    "rev": D / "ref/h264/QkkoHAzjnUs.mp4", "mft": D / "ref/h264/Bf38HiYPMiI.mp4", "gp": D / "ref/h264/N-xHcvug3WI.mp4",
    "onl": D / "ref/h264/olEGtoYs_8A.mp4", "casino": D / "ref/h264/lX_IN4v-RnA.mp4", "heist": D / "ref/h264/UUmKwJD76GY.mp4",
    "ng": D / "ref/h264/foUaOCzfIRU.mp4", "ps5": D / "ref/h264/VNbONMSObfs.mp4", "rdr": D / "ref/h264/eaW0tYpxyp0.mp4",
    "t1": ROOT / "projects/shorts/gta6-facts/public/clips/t1.mp4", "t2": ROOT / "projects/shorts/gta6-facts/public/clips/t2.mp4",
    "rz": ROOT / "projects/shorts/gta6-facts/public/clips/rz.mp4",
}


def run(cmd, timeout=900, cwd=None):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if r.returncode:
        raise SystemExit(f"{' '.join(map(str, cmd[:5]))} failed:\n{(r.stderr or r.stdout)[-3000:]}")
    return r


# --------------------------------------------------------------------------- 1. VO recut

def recut():
    vo = json.loads((OUT / "words.json").read_text())
    words, spans = vo["words"], vo["lines"]
    key = {}
    for k, (a, b) in spans.items():
        for i in range(a, b):
            key[i] = (k, i - a)
    keep = [i for i in range(len(words)) if key[i] not in DROP]
    pcm = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", vo["mp3"], "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                                       capture_output=True, timeout=60, check=True).stdout, dtype=np.float32)
    segs, s0 = [], max(0.0, words[keep[0]][0] - 0.06)
    for j in range(len(keep) - 1):
        i, n = keep[j], keep[j + 1]
        k, wi = key[i]
        end_of_line = wi == spans[k][1] - spans[k][0] - 1
        cap = BEAT.get(k, GAP_LINE) if end_of_line else GAP_IN
        if n != i + 1:
            cap = GAP_LINE
        g = words[n][0] - words[i][1]
        if g > cap:
            segs.append((s0, words[i][1] + cap / 2))
            s0 = words[n][0] - cap / 2
    segs.append((s0, words[keep[-1]][1] + 0.35))
    out, tmap, t = [], [], 0.0
    for a, b in segs:
        out.append(pcm[int(a * SR):int(b * SR)])
        tmap.append((a, b, t))
        t += b - a
    raw = OUT / "vo_cut.f32"
    np.concatenate(out).astype(np.float32).tofile(raw)
    wav = OUT / "vo_recut.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", SR, "-ac", 1, "-i", raw, "-af",
         f"atempo={TEMPO},loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", SR, wav])
    raw.unlink()

    def remap(x):
        for a, b, o in tmap:
            if a - 1e-6 <= x <= b + 1e-6:
                return VO_AT + (o + x - a) / TEMPO
        raise ValueError(x)

    cw = {}
    for i in keep:
        k, wi = key[i]
        cw[(k, wi)] = (remap(words[i][0]), remap(min(words[i][1], segs[-1][1])), words[i][2])
    dur = float(media.probe(wav)["format"]["duration"])
    return wav, cw, VO_AT + dur


# --------------------------------------------------------------------------- 2. edit

def edit(A, E, story_end):
    """Shots: (start_s, src, src_s, cx, grade, flags) — each runs to the next start. Overlays in seconds."""
    has3d = lambda n: (PUB / "3d" / f"{n}.mp4").exists()  # noqa: E731
    td = lambda n, fb: ("3d", f"3d/{n}.mp4", 0.5) if has3d(n) else fb  # noqa: E731  (src, at, cx)
    S = []

    def sh(t, src, at, cx=0.5, grade="none", fl=""):
        S.append((t, src, at, cx, grade, fl))

    # COLD OPEN — no text before 4.5 s; GTA VI now → GTA V then
    sh(0, "rz", 26.0, 0.45, "vice")                                       # Lucia & Jason, convertible
    sh(A("hook1", 2), "rev", 7.5, 0.6, "warm")                               # "out four thousand..."
    sh(A("hook1", 7), *td("calendar", ("gp", 6.5, 0.5)), "warm")            # "...eleven days ago"
    sh(A("hook2", 0), "mft", 42.5, 0.45, "warm")                              # Michael: "If you were five"
    sh(A("hook2", 7), "rz", 39.0, 0.4, "vice", "g")                           # Jason & Lucia: "legally buy GTA 6"
    sh(A("hook3", 0), *td("hourglass", ("rev", 70.0, 0.45)), "none")   # "why 13 years?"
    # REASON 1 — the money printer
    sh(A("r1", 0) - 0.1, "gp", 257.5, 0.4, "money", "g")
    sh(A("r1", 2), "ng", 27.0, 0.55, "money")                                 # "GTA 5 refused to die"
    sh(A("m1", 0), "casino", 5.0, 0.5, "money")
    sh(A("m1", 6), "casino", 30.0, 0.4, "money")                              # "World record" — hugging the supercar
    sh(A("m2", 0), *td("consoles", ("gp", 280.0, 0.5)), "none")
    sh(A("m3", 5) - 0.05, "mft", 207.5, 0.6, "warm", "g")                      # "Same Trevor."
    sh(A("m4", 0), "onl", 47.5, 0.5, "money")                                 # parachuting crowd
    sh(A("m4", 5), "heist", 17.5, 0.45, "money")                              # blackjack: "1.3 million"
    sh(A("m5", 0), *td("printer", ("ng", 27.5, 0.55)), "money")
    # REASON 2 — cowboys
    sh(A("r2", 0) - 0.1, "rdr", 27.5, 0.4, "warm", "g")
    sh(A("c1", 0), "rdr", 55.0, 0.55, "warm")
    sh(A("c1", 6), "rdr", 67.5, 0.5, "warm")                                  # "pulled senior staff off GTA 6"
    sh(A("c2", 0), "rdr", 102.5, 0.45, "warm")
    sh(A("c2", 7), "onl", 15.0, 0.45, "red", "g")                             # "and the internet lost it"
    sh(A("c3", 0), "gp", 57.5, 0.5, "cold")                                   # trio on the roof + phone
    # REASON 3 — everything went wrong
    sh(A("r3", 0) - 0.1, "mft", 205.0, 0.45, "red", "g")
    sh(A("w1", 0), "rev", 40.0, 0.65, "cold")                                 # "the lead writer left"
    sh(A("w1", 4), "onl", 170.0, 0.5, "bw")                                   # "pandemic sent everyone home"
    sh(A("w2", 0), "heist", 25.0, 0.5, "red", "g")                            # "a hacker leaked..."
    sh(A("w2", 5), "heist", 42.5, 0.4, "red")                                 # "Rockstar says that cost..."
    sh(A("w3", 0), "gp", 26.0, 0.5, "none")                                   # map aerial
    sh(A("w3", 9), "t2", 6.6, 0.5, "vice")                                    # "cut it down to Florida"
    sh(A("w4", 0), "t2", 39.0, 0.45, "vice")                                  # "Of course it's Florida."
    sh(A("w5", 0), "t2", 99.0, 0.5, "vice")                                   # team doubled
    sh(A("w5", 7), "rz", 52.8, 0.3, "vice")                                  # "office just for NPCs"
    # REASON 4 — polish
    sh(A("r4", 0) - 0.1, "rz", 46.5, 0.35, "vice", "g")
    sh(A("d1", 0), "t1", 84.0, 0.5, "vhs", "b")                               # COMING 2025
    sh(A("d1", 4), "t2", 162.0, 0.5, "vhs", "bg")                             # MAY 26 2026
    sh(A("d1", 7), "rz", 81.5, 0.5, "none", "bg")                             # NOV 19 2026
    sh(A("d2", 0), *td("vault", ("t2", 117.0, 0.6)), "none")           # "Both delays? For polish."
    sh(A("d2", 5), "t1", 3.0, 0.5, "vice")                                    # "The price? Eighty bucks."
    # BRIDGE — our sketch → 3D (real Vi3W output)
    sh(A("end", 8), "rz", 25.5, 0.55, "bw")                                  # bridge plate under the comic panels
    S.sort(key=lambda s: s[0])

    ov = [
        dict(kind="title", t=A("hook3", 0), u=A("r1", 0) - 0.15, lines=["why did it take", "13 YEARS?"]),
        dict(kind="stamp", t=A("hook2", 8), u=A("hook3", 0), text="18+ ✓", sub="NOW LEGAL TO BUY", color="#6FDB6A"),
        dict(kind="chapter", t=A("r1", 0) - 0.15, u=A("m1", 0), n="REASON 1", title="the money printer", color="#6FDB6A"),
        dict(kind="counter", t=A("m1", 0), u=A("m2", 0), prefix="$", value=1_000_000_000, label="GTA V · FIRST 3 DAYS",
             note="GUINNESS WORLD RECORD"),
        dict(kind="stack", t=A("m2", 0), u=A("m3", 5) - 0.05, title="SAME GAME · 3 CONSOLE GENERATIONS",
             items=[dict(a="PS3", b="2013", at=A("m2", 0)), dict(a="PS4", b="2014", at=A("m2", 6)), dict(a="PS5", b="2022", at=A("m2", 10))]),
        dict(kind="counter", t=A("m4", 1), u=A("m5", 0), prefix="$", value=1_300_000, label="GTA ONLINE · PER DAY (REPORTED)",
             note="LEAKED FIGURES VIA KOTAKU"),
        dict(kind="cash", t=A("m4", 8), u=A("m5", 0) + 0.6, text="+$"),
        dict(kind="tip", t=A("m5", 0), u=A("r2", 0) - 0.2, text="Shark Cards are not a retirement plan."),
        dict(kind="chapter", t=A("r2", 0) - 0.15, u=A("c1", 0), n="REASON 2", title="cowboys", color="#FF9A3C"),
        dict(kind="stamp", t=A("c1", 0), u=A("c1", 6), text="RDR2", sub="OCT 2018 · PRIORITY #1", color="#FF9A3C", rot=-6),
        dict(kind="stamp", t=A("c2", 3), u=A("c2", 7), text="100 HRS", sub="PER WEEK (2018 INTERVIEW)", color="#E8303A"),
        dict(kind="stars", t=A("c2", 7), u=A("c3", 0), n=5),
        dict(kind="phone", t=A("c3", 0) - 0.1, u=A("r3", 0) - 0.15, who="Rockstar",
             msgs=[dict(text="new rule: less crunch 🙏", at=A("c3", 2)), dict(text="so... GTA 6 when?", at=A("c3", 5), me=True),
                   dict(text="slower.", at=A("c3", 6))]),
        dict(kind="chapter", t=A("r3", 0) - 0.15, u=A("w1", 0), n="REASON 3", title="everything went wrong", color="#E8303A"),
        dict(kind="stamp", t=A("w1", 0) + 0.1, u=A("w1", 4), text="2020", sub="HEAD WRITER EXITS", color="#FFE14D", rot=-5),
        dict(kind="stamp", t=A("w1", 4), u=A("w2", 0), text="WFH", sub="PANDEMIC · 2020", color="#4FA3FF"),
        dict(kind="wasted", t=A("w2", 5), u=A("w3", 0), text="leaked", sub="$5,000,000 · ROCKSTAR SAYS"),
        dict(kind="stamp", t=A("w3", 2), u=A("w3", 9), text="2 CONTINENTS", sub="ORIGINAL PLAN (REPORTEDLY)", color="#FFE14D", rot=-4),
        dict(kind="tip", t=A("w4", 0), u=A("w5", 0), text="In Florida, this counts as a normal Tuesday."),
        dict(kind="counter", t=A("w5", 0), u=A("w5", 7), value=4711, label="ROCKSTAR STAFF · AUG 2026", note="2,441 IN 2018"),
        dict(kind="stamp", t=A("w5", 9), u=A("r4", 0) - 0.15, text="NPC HQ", sub="A WHOLE OFFICE (LA)", color="#FF3E9A"),
        dict(kind="chapter", t=A("r4", 0) - 0.15, u=A("d1", 0), n="REASON 4", title="polish", color="#4FA3FF"),
        dict(kind="stamp", t=A("d1", 4), u=A("d1", 7), text="DELAYED", color="#E8303A"),
        dict(kind="stamp", t=A("d1", 7), u=A("d2", 0), text="DELAYED", sub="AGAIN", color="#E8303A", rot=6),
        dict(kind="passed", t=A("d2", 5), u=A("end", 8), title="mission passed?", sub="$79.99 · NOV 19, 2026"),
        dict(kind="bridge", t=A("end", 8) - 0.05, u=story_end, sketch="img/sketch.png", model="clips/car3d.mp4", pop=A("end", 12)),
    ]
    years = [(4.5, 2013), (A("hook2", 7), 2026), (A("r1", 0), 2013), (A("m2", 6), 2014), (A("m2", 10), 2022), (A("m4", 0), 2026),
             (A("r2", 0), 2018), (A("r3", 0), 2020), (A("w2", 0), 2022), (A("w5", 0), 2026), (A("d1", 0), 2025), (A("d1", 4), 2026)]
    cash = [(A("m1", 0), 0), (A("m1", 6), 1_000_000_000), (A("m4", 5), 1_000_000_000), (A("m5", 6), 1_500_000_000),
            (A("r2", 0) - 0.05, 1_500_000_000), (A("r2", 0), 0)]
    return S, ov, years, cash


# --------------------------------------------------------------------------- 3. clips

def bars(src: Path, at: float, dur: float) -> str:
    """Letterbox crop (cropdetect over the shot) so full-bleed 9:16 crops have no baked-in black bars."""
    r = subprocess.run(["ffmpeg", "-ss", f"{at:.2f}", "-i", str(src), "-t", f"{min(dur, 2.0):.2f}", "-vf", "cropdetect=limit=24:round=2:reset=0",
                        "-an", "-f", "null", "-"], capture_output=True, text=True, timeout=60).stderr
    c = [ln.rsplit("crop=", 1)[1].strip() for ln in r.splitlines() if "crop=" in ln]
    if not c:
        return ""
    w, h, x, y = map(int, c[-1].split(":"))
    return f"crop={w}:{h}:{x}:{y}," if h < 1060 * (w / 1920) and h > 400 else ""


def cut(src: Path, at: float, dur: float, band: bool) -> str:
    h = hashlib.sha1(f"{src.name}|{at:.2f}|{dur:.2f}|lb{band}".encode()).hexdigest()[:10]
    dst = PUB / "clips/cut" / f"{h}.mp4"
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        crop = "" if band else bars(src, at, dur)
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", src, "-t", f"{dur + 0.4:.3f}", "-an",
             "-vf", f"{crop}scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", dst], timeout=120)
    return dst.relative_to(PUB).as_posix()


# --------------------------------------------------------------------------- 4. render + mix

def main(preview=False):
    t_all = time.time()
    wav, cw, vo_end = recut()
    A = lambda k, i: cw[(k, i)][0]  # noqa: E731
    E = lambda k, i: cw[(k, i)][1]  # noqa: E731
    story_end = vo_end + 0.5
    S, ov, years, cash = edit(A, E, story_end)
    for p, d in [("img/sketch.png", ROOT / "projects/shorts/gta6-facts/public/img/sketch.png"),
                 ("clips/car3d.mp4", ROOT / "projects/shorts/gta6-facts/public/clips/car3d_b.mp4")]:
        (PUB / p).parent.mkdir(parents=True, exist_ok=True)
        if not (PUB / p).exists():
            shutil.copy(d, PUB / p)

    shots = []
    for i, (t, src, at, cx, grade, fl) in enumerate(S):
        t1 = S[i + 1][0] if i + 1 < len(S) else story_end
        dur = t1 - t
        if src in SRC:
            path, start = cut(SRC[src], at, dur, "b" in fl), 0
        elif src == "img":
            path, start = "img/sketch.png", 0
        elif src == "car":
            path, start = "clips/car3d.mp4", F(at)
        else:                                                                 # "3d": at is the public path
            path, start = at, 0
        speed = 1.0
        if src == "3d":
            clip = float(media.probe(PUB / path)["format"]["duration"]) - 0.1
            speed = round(min(1.0, clip / dur), 3)
        shots.append({"src": path, "from": F(t), "dur": max(1, F(t1) - F(t)), "at": start, "x": cx,
                      "mode": "band" if "b" in fl else "full", "grade": grade, "glitch": "g" in fl, "speed": speed})

    overlays = []
    for o in ov:
        o = dict(o)
        a, b = o.pop("t"), o.pop("u")
        if o["kind"] == "bridge":
            o["pop"] = F(o["pop"]) - F(a)
        for lst in ("items", "msgs"):
            if lst in o:
                o[lst] = [{**it, "at": F(it["at"]) - F(a)} for it in o[lst]]
        overlays.append({**o, "from": F(a), "dur": max(6, F(b) - F(a))})

    sfx = []
    for o in overlays:
        k = o["kind"]
        if k in ("chapter", "title"):
            sfx.append({"src": "sfx/whoosh.mp3", "from": o["from"] - 3, "volume": 0.45})
        elif k == "wasted":
            sfx.append({"src": "sfx/boom.mp3", "from": o["from"], "volume": 0.5})
        elif k == "passed":
            sfx.append({"src": "sfx/ding.mp3", "from": o["from"], "volume": 0.5})
        elif k == "stamp":
            sfx.append({"src": "sfx/pop.mp3", "from": o["from"], "volume": 0.35})
        elif k == "bridge":
            sfx += [{"src": "sfx/whoosh.mp3", "from": o["from"] - 3, "volume": 0.4}, {"src": "sfx/pop.mp3", "from": o["from"] + o["pop"], "volume": 0.55}]
        elif k == "cash":
            sfx.append({"src": "sfx/kaching.mp3", "from": o["from"], "volume": 0.45})
        elif k == "counter":
            sfx.append({"src": "sfx/kaching.mp3", "from": o["from"] + 36, "volume": 0.3})
        for it in o.get("items", []) + o.get("msgs", []):
            sfx.append({"src": "sfx/pop.mp3" if "a" in it else "sfx/click.mp3", "from": o["from"] + it["at"], "volume": 0.35})
    for s in shots:
        if s["glitch"] and s["from"] > F(4):
            sfx.append({"src": "sfx/freeze.mp3", "from": s["from"], "volume": 0.18})
    for n, src in [("whoosh", "gta6-facts/public/sfx"), ("boom", "gta6-facts/public/sfx"), ("ding", "gta6-facts/public/sfx"),
                   ("pop", "gta6-facts/public/sfx"), ("freeze", "gta6-facts/public/sfx"), ("kaching", "landlord-dog/sfx"),
                   ("click", "landlord-dog/sfx")]:
        dst = PUB / "sfx" / f"{n}.mp3"
        if not dst.exists():
            shutil.copy(ROOT / "projects/shorts" / src / f"{n}.mp3", dst)

    words = [[F(a), F(b), w] for (k, i), (a, b, w) in sorted(cw.items(), key=lambda x: x[1][0])]
    props = {
        "fps": FPS, "durationInFrames": F(story_end), "shots": shots, "overlays": overlays,
        "hud": {"from": F(4.5), "to": F(A("end", 8)), "years": [[F(t), y] for t, y in years], "cash": [[F(t), c] for t, c in cash]},
        "credit": {"text": "Footage: Rockstar Games · official trailers", "to": F(A("end", 8))},
        "words": words, "captionsFrom": F(4.5),
        "emphasis": ["billion", "ps4", "ps5", "trevor", "13", "million", "day", "cowboys", "100hour", "slower", "wrong", "ninety",
                     "five", "florida", "4700", "npcs", "polish", "2025", "2026", "19th", "eighty", "sketch", "legally", "thirteen"],
        "cues": sfx,
    }
    pj = OUT / "props.json"
    pj.write_text(json.dumps(props, indent=1))

    rem = ROOT / "node" / "remotion"
    raw = OUT / f"story{'-preview' if preview else ''}.mp4"
    t = time.time()
    run(["npx", "remotion", "render", "src/shorts/index.ts", "Gta13", raw, "--codec", "h264", "--crf", "17", "--pixel-format", "yuv420p",
         "--image-format", "jpeg", "--jpeg-quality", "92", "--timeout", "240000", "--concurrency", "6", "--props", pj,
         "--public-dir", PUB] + (["--scale", "0.5"] if preview else []), cwd=rem, timeout=3600)
    t_render = time.time() - t

    # audio: story VO + fresh outro take → one wav; music ducked under it; Remotion's SFX on top
    end = story_end + outro.META["dur"]
    o_mp3, _, o_at = outro.voice(D)
    vo_track = OUT / "vo_track.wav"
    oms = int((story_end + o_at) * 1000)
    run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-i", o_mp3, "-filter_complex",
         f"[0:a]aresample={SR},adelay={int(VO_AT * 1000)}|{int(VO_AT * 1000)}[a0];[1:a]aresample={SR},loudnorm=I=-16:TP=-1.5,"
         f"adelay={oms}|{oms}[a1];[a0][a1]amix=inputs=2:normalize=0:duration=longest,apad=whole_dur={end:.3f}[a]",
         "-map", "[a]", "-t", f"{end:.3f}", vo_track])
    W = 540 if preview else 1080
    mp4 = OUT / f"{NAME}{'-preview' if preview else ''}.mp4"
    chain = [f"[0:v]fps={FPS},scale={W}:-2,setsar=1,format=yuv420p[st]", f"[1:v]fps={FPS},scale={W}:-2,setsar=1,format=yuv420p[ou]",
             "[st][ou]concat=n=2:v=1:a=0,fade=t=out:st={:.2f}:d=0.6[vout]".format(end - 0.6),
             f"[0:a]aresample={SR},apad=whole_dur={end:.3f}[sfx]",
             f"[2:a]aresample={SR},asplit=2[vo][key]",
             f"[3:a]aresample={SR},volume=0.38,afade=t=in:d=0.4,afade=t=out:st={end - 2.0:.2f}:d=2.0[mus]",
             "[mus][key]sidechaincompress=threshold=0.025:ratio=10:attack=15:release=300[duck]",
             f"[vo][duck][sfx]amix=inputs=3:normalize=0:duration=first,atrim=0:{end:.3f}[aout]"]
    run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-i", outro.CLIP, "-i", vo_track, "-stream_loop", "-1", "-i", MUSIC,
         "-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", f"{end:.3f}", "-c:v", "libx264", "-preset", "fast",
         "-crf", "18", "-pix_fmt", "yuv420p", "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", "-ar", SR, "-movflags", "+faststart", mp4], timeout=900)
    final = OUT / f"{NAME}-m.mp4"
    media.master(mp4, final)
    final.replace(mp4)
    media.contact_sheet(mp4, OUT / ("contact-preview.jpg" if preview else "contact.jpg"), fps=1.0, cols=8, cell_w=180, title=NAME)
    print(json.dumps({"file": str(mp4), "story_end": round(story_end, 2), "seconds": round(end, 2), "render_s": round(t_render),
                      "total_s": round(time.time() - t_all), "loudness": media.loudness(mp4)}))
    if not preview:
        dst = ROOT / "FinalUploads" / "Drafts"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy(mp4, dst / f"{NAME}.mp4")
        (dst / f"{NAME}.txt").write_text((D / "caption.txt").read_text())


if __name__ == "__main__":
    main(preview="--preview" in sys.argv)
