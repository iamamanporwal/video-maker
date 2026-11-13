"""Where did GTA 6's billion dollars go? — money-trail mini-doc → Remotion Gta13 (+ money kit overlays) + shared Vi3W outro.

usage: .venv/bin/python projects/shorts/gta6-billion/build.py [--preview]
  1. recut the Kokoro take (out/words_<VOICE>.json from vo.py): cap pauses → out/vo_recut.wav, word times remapped
  2. shot list + overlays keyed to recut word times: A("p2", 9) = start of word 9 of line p2 (seconds)
  3. trailer shots pre-cut to small h264 clips; missing 3D shots fall back to a placeholder (dry runs before agents finish)
  4. Remotion → picture + SFX; ffmpeg adds outro clip, VO (story + outro take), music ducked under the voice; -14 LUFS
Facts: RESEARCH.md (hedges stay on screen). Logos: Rockstar / Take-Two (Wikimedia SVG), GTA VI (official trailer end card),
Netflix (Wikimedia) — permissions are the owner's responsibility (2026-11-08). Footage: official Rockstar uploads, muted.
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

NAME = "gta6-billion"
VOICE = os.environ.get("VO", "cb")                # cb = Chatterbox (vo_cb.py); am_fenrir = Kokoro (vo.py)
FPS, SR = 30, 48000
OUT, PUB = D / "out", D / "public"
TEMPO = float(os.environ.get("TEMPO", "1.0"))
VO_AT = 0.2
GAP_IN, GAP_LINE = 0.3, 0.38
BEAT = {"h1": 0.2, "h3": 0.25, "h4": 0.15, "p2": 0.3, "a1": 0.3, "r2": 0.3, "b1": 0.25}
MUSIC = ROOT / "projects/shorts/gta6-facts/public/music/hitman.mp3"       # Kevin MacLeod "Hitman", CC BY 4.0
F = lambda s: round(s * FPS)  # noqa: E731
H264 = ROOT / "projects/shorts/gta6-13-years/ref/h264"
SRC = {"t1": ROOT / "projects/shorts/gta6-facts/public/clips/t1.mp4", "t2": ROOT / "projects/shorts/gta6-facts/public/clips/t2.mp4",
       "rz": ROOT / "projects/shorts/gta6-facts/public/clips/rz.mp4", "ng": H264 / "foUaOCzfIRU.mp4", "gp": H264 / "N-xHcvug3WI.mp4"}
# caption display: (line, first word, n words) → one caption token spanning those words
SHOW = [("h1", 0, 4, "GTA 6"), ("h1", 12, 1, "13"), ("h2", 3, 3, "$1 BILLION"), ("p1", 5, 6, "4,711"), ("p2", 4, 3, "$100K"),
        ("f1", 11, 2, "2015"), ("l1", 3, 1, "90"), ("l1", 10, 3, "$5 MILLION"), ("a1", 12, 5, "$975,000"), ("r1", 3, 4, "GTA 6"),
        ("r1", 9, 3, "$3 BILLION"), ("b2", 4, 1, "Vi3W"), ("b2", 9, 2, "3D")]
SFX = {"kaching": "landlord-dog/sfx", "slam": "mcqueen-brain/sfx", "riser": "mcqueen-brain/sfx", "vineboom": "mcqueen-brain/sfx",
       "splash": "mcqueen-brain/sfx", "shock": "mcqueen-brain/sfx", "pop": "gta6-facts/public/sfx", "whoosh": "gta6-facts/public/sfx",
       "boom": "gta6-facts/public/sfx", "ding": "gta6-facts/public/sfx", "freeze": "gta6-facts/public/sfx", "click": "landlord-dog/sfx",
       "pipe": "vi3w-memes/sfx", "ting": "roblox-hooks/sfx", "yt-explode": "roblox-hooks/sfx", "drop": "roblox-hooks/sfx"}
SFX_X = {"jet": "projects/artist-who-couldnt-create/audio/sfx/jet.mp3", "printer": "projects/launch/one-sketch-away/audio/sfx/printer.mp3",
         "rewind": "projects/launch/one-sketch-away/audio/sfx/rewind.mp3", "page": "projects/artist-who-couldnt-create/audio/sfx/page.mp3",
         "glitch": "projects/artist-who-couldnt-create/audio/sfx/glitch.mp3"}


def run(cmd, timeout=900, cwd=None):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if r.returncode:
        raise SystemExit(f"{' '.join(map(str, cmd[:5]))} failed:\n{(r.stderr or r.stdout)[-3000:]}")
    return r


# --------------------------------------------------------------------------- 1. VO recut

def recut():
    vo = json.loads((OUT / f"words_{VOICE}.json").read_text())
    words, spans = vo["words"], vo["lines"]
    key = {i: (k, i - a) for k, (a, b) in spans.items() for i in range(a, b)}
    sr0 = int(vo.get("sr", 24000))
    pcm = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", vo["mp3"], "-f", "f32le", "-ac", "1", "-ar", str(sr0), "-"],
                                       capture_output=True, timeout=60, check=True).stdout, dtype=np.float32)
    segs, s0 = [], max(0.0, words[0][0] - 0.05)
    for i in range(len(words) - 1):
        k, wi = key[i]
        cap = BEAT.get(k, GAP_LINE) if wi == spans[k][1] - spans[k][0] - 1 else GAP_IN
        g = words[i + 1][0] - words[i][1]
        if g > cap:
            segs.append((s0, words[i][1] + cap / 2))
            s0 = words[i + 1][0] - cap / 2
    segs.append((s0, words[-1][1] + 0.3))
    out, tmap, t = [], [], 0.0
    for a, b in segs:
        out.append(pcm[int(a * sr0):int(b * sr0)])
        tmap.append((a, b, t))
        t += b - a
    raw = OUT / "vo_cut.f32"
    np.concatenate(out).astype(np.float32).tofile(raw)
    wav = OUT / "vo_recut.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", sr0, "-ac", 1, "-i", raw, "-af",
         f"atempo={TEMPO},highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=9",
         "-ar", SR, wav])
    raw.unlink()

    def remap(x):
        for a, b, o in tmap:
            if a - 1e-6 <= x <= b + 1e-6:
                return VO_AT + (o + x - a) / TEMPO
        best = min(tmap, key=lambda s: min(abs(x - s[0]), abs(x - s[1])))
        return VO_AT + (best[2] + min(max(x, best[0]), best[1]) - best[0]) / TEMPO

    cw = {key[i]: (remap(w[0]), remap(w[1]), w[2]) for i, w in enumerate(words)}
    dur = float(media.probe(wav)["format"]["duration"])
    return wav, cw, VO_AT + dur


# --------------------------------------------------------------------------- 2. edit

def edit(A, E, story_end):
    """Shots: (start_s, src, at_s, cx, grade, flags). src = '3d:<name>' (public/3d) or a SRC key (trailer, muted)."""
    S = []

    def sh(t, src, at=0.0, cx=0.5, grade="none", fl=""):
        S.append((t, src, at, cx, grade, fl))

    sh(0, "3d:rocket")                                                        # HOOK: cash rocket → 13 rockets
    sh(A("h2", 0), "3d:cashrain", 0, 0.5, "money", "g")
    sh(A("h3", 0), "3d:vault")
    sh(A("p1", 0), "3d:bh_office", 0, 0.5, "none", "g")
    sh(A("p2", 0), "3d:printer")
    sh(A("f1", 0), "3d:bh_florida", 0, 0.5, "vice")
    sh(A("f1", 5), "t1", 3.0, 0.5, "vice", "c")                               # the real Vice City (causeway at sunset)
    sh(A("f2", 0), "3d:bh_citypull")
    sh(A("f2", 2), "3d:bh_props")
    sh(A("f2", 5), "3d:bh_trashcan", 2.9)                                     # trash can callback (texture wipe)
    sh(A("c1", 0), "3d:bh_animate", 0, 0.5, "none", "g")
    sh(A("c1", 7), "3d:bh_rig", 0.5)
    sh(A("c2", 0), "3d:beer", 0, 0.5, "none", "g")
    sh(A("l1", 0), "3d:leak", 0, 0.5, "none", "g")
    sh(A("a1", 0), "ng", 30.0, 0.5, "vice", "c")                              # superyacht: "and marketing?"
    sh(A("a1", 2), "3d:sign")
    sh(A("r1", 0), "3d:cashrain_rev", 0, 0.5, "money", "g")                   # money flies BACK
    sh(A("r2", 0), "ng", 27.5, 0.55, "money", "c")                            # hand grabbing stacks of cash (official)
    sh(A("b1", 0), "3d:bh_lonely", 0, 0.5, "cold", "g")
    sh(A("b2", 0), "3d:bh_lonely", 0.8, 0.5, "cold")
    S.sort(key=lambda s: s[0])

    gold, pink, red, yel = "#F5C542", "#FF3E9A", "#E8303A", "#FFE14D"
    rcpt = dict(title="ROCKSTAR GAMES · GTA VI", foot="*napkin math · rest = estimates")
    items = [dict(label="4,711 STAFF × $100K*", price="$471M/YR", at=A("p2", 13)),
             dict(label="FAKE FLORIDA (2015-)", price="$ ???", at=A("f2", 8)),
             dict(label="MOCAP + 1 BEER DEBATE", price="$ ???", at=A("c2", 21)),
             dict(label="LEAK CLEANUP 2022", price="$5,000,000", at=A("l1", 11), hot=True),
             dict(label="1 ROOF SIGN", price="$975,000", at=A("a1", 14), hot=True)]
    ov = [
        dict(kind="bills", t=0, u=A("h2", 0), n=34, src="img/bill.png", ox=540, oy=1250, spread=1.4, up=True, seed=1),
        dict(kind="logo", t=0.05, u=A("h1", 9), src="logos/gta6_logo.png", x=540, y=170, w=470, glow=pink, slam=True),
        dict(kind="stamp", t=A("h1", 12), u=A("h2", 0), text="×13", sub="CHANDRAYAAN-3 ≈ $75M", color=yel, rot=-6),
        dict(kind="flash", t=A("h2", 0), u=A("h2", 0) + 0.25),
        dict(kind="logo", t=A("h2", 1), u=A("h3", 0), src="logos/Rockstar_Games_Logo.svg", x=300, y=330, w=330, rot=-6, slam=True),
        dict(kind="logo", t=A("h2", 2), u=A("h3", 0), src="logos/Take-Two_Interactive_Logo.svg", x=780, y=360, w=360, rot=5, slam=True, bg="#fff"),
        dict(kind="stamp", t=A("h3", 3), u=A("h3", 5), text="WRONG", sub="ROCKSTAR, ON THE $1.5B RUMOR", color=red, rot=-7),
        dict(kind="stamp", t=A("h3", 5), u=A("h4", 0), text="NO COMMENT", sub="THE REAL NUMBER", color=red, rot=5),
        dict(kind="receipt", t=A("h4", 3), u=A("p1", 4), **rcpt, items=[]),
        dict(kind="counter", t=A("p1", 4), u=A("p2", 0), value=4711, label="ROCKSTAR EMPLOYEES · 2026", note="UP FROM 2,441"),
        dict(kind="tip", t=A("p2", 0), u=A("p2", 13), text="NAPKIN MATH, NOT AN OFFICIAL NUMBER."),
        dict(kind="receipt", t=A("p2", 12), u=A("f1", 0), **rcpt, items=items[:1]),
        dict(kind="bills", t=A("p2", 15), u=A("f1", 0), n=26, src="img/bill.png", ox=540, oy=-200, spread=0.9, seed=3),
        dict(kind="stamp", t=A("f1", 3), u=A("f1", 5), text="FAKE FLORIDA", sub="LEONIDA · GTA VI", color=pink, rot=-5),
        dict(kind="stamp", t=A("f1", 11), u=A("f2", 0), text="SINCE 2015", sub="FIRST MIAMI RESEARCH TRIP (BLOOMBERG)", color=yel, rot=4),
        dict(kind="receipt", t=A("f2", 7), u=A("c1", 0), **rcpt, items=items[:2]),
        dict(kind="viewport", t=A("c1", 0), u=A("c2", 0), mode="Pose Mode · Mocap cleanup", rec=True),
        dict(kind="tip", t=A("c2", 0), u=A("c2", 11), text="BLOOMBERG: THE TEAM DEBATED HOW BUYING A BEER SHOULD WORK."),
        dict(kind="pipeline", t=A("c2", 11), u=A("l1", 0), steps=[dict(label="GRAB FROM FRIDGE", at=A("c2", 11)),
             dict(label="WALK TO COUNTER", at=A("c2", 16)), dict(label="PAY", at=A("c2", 21))]),
        dict(kind="receipt", t=A("c2", 20), u=A("l1", 1), **rcpt, items=items[:3]),
        dict(kind="stars", t=A("l1", 2), u=A("a1", 0), n=5),
        dict(kind="counter", t=A("l1", 5), u=A("a1", 0), prefix="$", value=5_000_000, label="LEAK CLEANUP · PER ROCKSTAR (2022)",
             note="+ THOUSANDS OF STAFF HOURS"),
        dict(kind="logo", t=A("a1", 0), u=A("a1", 3), src="logos/Netflix_2015_logo.svg", x=540, y=420, w=560, slam=True),
        dict(kind="stamp", t=A("a1", 12), u=A("a1", 17), text="$975,000", sub="REPORTEDLY", color=gold, rot=-6),
        dict(kind="bills", t=A("a1", 17), u=A("r1", 0), n=24, src="img/bill.png", ox=540, oy=-200, spread=0.9, seed=5),
        dict(kind="receipt", t=A("a1", 16), u=A("r1", 0), **rcpt, items=items, total=dict(label="TOTAL", value="NO COMMENT", at=A("a1", 18))),
        dict(kind="logo", t=A("r1", 1), u=A("r1", 9), src="logos/Take-Two_Interactive_Logo.svg", x=540, y=330, w=420, slam=True, bg="#fff"),
        dict(kind="counter", t=A("r1", 8), u=A("r2", 0), prefix="$", value=3_000_000_000, label="FIRST 4 MONTHS · ANALYST ESTIMATE",
             note="≈ 40 MILLION COPIES"),
        dict(kind="bills", t=A("r1", 0), u=A("b1", 0), n=40, src="img/bill.png", ox=540, oy=2100, spread=1.0, up=True, seed=7),
        dict(kind="passed", t=A("r2", 3), u=A("b1", 0), sub="BUDGET RECOVERED"),
        dict(kind="logo", t=A("r2", 0), u=A("b1", 0), src="logos/gta6_logo.png", x=540, y=200, w=420, glow=pink),
        dict(kind="wasted", t=A("b1", 0), u=A("b2", 0), text="BROKE", sub="(probably you)"),
        dict(kind="bridge", t=A("b2", 0) - 0.05, u=story_end, sketch="img/sketch.png", model="clips/car3d.mp4", pop=A("b2", 5)),
    ]
    return S, ov


# --------------------------------------------------------------------------- 3. clips

def bars(src: Path, at: float, dur: float) -> str:
    r = subprocess.run(["ffmpeg", "-ss", f"{at:.2f}", "-i", str(src), "-t", f"{min(dur, 2.0):.2f}", "-vf", "cropdetect=limit=24:round=2:reset=0",
                        "-an", "-f", "null", "-"], capture_output=True, text=True, timeout=60).stderr
    c = [ln.rsplit("crop=", 1)[1].strip() for ln in r.splitlines() if "crop=" in ln]
    if not c:
        return ""
    w, h, x, y = map(int, c[-1].split(":"))
    return f"crop={w}:{h}:{x}:{y}," if 400 < h < 1060 * (w / 1920) else ""


def cut(src: Path, at: float, dur: float) -> str:
    h = hashlib.sha1(f"{src.name}|{at:.2f}|{dur:.2f}".encode()).hexdigest()[:10]
    dst = PUB / "clips/cut" / f"{h}.mp4"
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", src, "-t", f"{dur + 0.4:.3f}", "-an",
             "-vf", f"{bars(src, at, dur)}scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", dst], timeout=120)
    return dst.relative_to(PUB).as_posix()


def assets():
    """Bill sprite (rounded, alpha), reversed cash rain, SFX copies."""
    from PIL import Image, ImageDraw
    bill = PUB / "img/bill.png"
    if not bill.exists():
        im = Image.open(PUB / "img/bill_front.jpg").convert("RGBA").resize((600, 252))
        m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], 10, fill=255)
        im.putalpha(m)
        im.save(bill)
    cr, rev = PUB / "3d/cashrain.mp4", PUB / "3d/cashrain_rev.mp4"
    if cr.exists() and (not rev.exists() or rev.stat().st_mtime < cr.stat().st_mtime):
        run(["ffmpeg", "-y", "-v", "error", "-i", cr, "-vf", "reverse", "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", rev])
    (PUB / "sfx").mkdir(exist_ok=True)
    for n, d in SFX.items():
        if not (PUB / "sfx" / f"{n}.mp3").exists():
            shutil.copy(ROOT / "projects/shorts" / d / f"{n}.mp3", PUB / "sfx" / f"{n}.mp3")
    for n, p in SFX_X.items():
        if not (PUB / "sfx" / f"{n}.mp3").exists():
            shutil.copy(ROOT / p, PUB / "sfx" / f"{n}.mp3")


# --------------------------------------------------------------------------- 4. render + mix

def main(preview=False):
    t_all = time.time()
    assets()
    wav, cw, vo_end = recut()
    A = lambda k, i: cw[(k, i)][0]  # noqa: E731
    E = lambda k, i: cw[(k, i)][1]  # noqa: E731
    story_end = vo_end + 0.45
    S, ov = edit(A, E, story_end)

    shots, missing = [], []
    for i, (t, src, at, cx, grade, fl) in enumerate(S):
        t1 = S[i + 1][0] if i + 1 < len(S) else story_end
        dur = t1 - t
        speed, start = 1.0, 0
        if src.startswith("3d:"):
            p = PUB / "3d" / f"{src[3:]}.mp4"
            if not p.exists():                                                  # placeholder until the 3D agent delivers
                missing.append(src[3:])
                path = cut(SRC["ng"], 27.5 + (i % 5) * 2.5, dur)
            else:
                path = p.relative_to(PUB).as_posix()
                clip = float(media.probe(p)["format"]["duration"]) - at - 0.1
                speed = round(min(1.0, max(0.5, clip / dur)), 3)
                start = F(at)
        else:
            path = cut(SRC[src], at, dur)
        shots.append({"src": path, "from": F(t), "dur": max(1, F(t1) - F(t)), "at": start, "x": cx, "mode": "full",
                      "grade": grade, "glitch": "g" in fl, "speed": speed, "credit": "c" in fl})

    overlays = []
    for o in ov:
        o = dict(o)
        a, b = o.pop("t"), o.pop("u")
        if o["kind"] == "bridge":
            o["pop"] = F(o["pop"]) - F(a)
        for lst in ("items", "steps", "lines"):
            if lst in o:
                o[lst] = [{**it, "at": F(it["at"]) - F(a)} for it in o[lst]]
        if "total" in o:
            o["total"] = {**o["total"], "at": F(o["total"]["at"]) - F(a)}
        overlays.append({**o, "from": F(a), "dur": max(6, F(b) - F(a))})

    cue = lambda n, t, v=0.4, d=None: {"src": f"sfx/{n}.mp3", "from": max(0, F(t)), "volume": v, **({"dur": F(d)} if d else {})}  # noqa: E731
    sfx = [cue("jet", 0, 0.5), cue("boom", 0.05, 0.35), cue("yt-explode", A("h1", 12), 0.35), cue("riser", A("h2", 0) - 1.2, 0.3),
           cue("kaching", A("h2", 4), 0.45), cue("slam", A("h3", 0) + 0.85, 0.6), cue("vineboom", A("h3", 5), 0.35),
           cue("printer", A("p2", 0), 0.35), cue("printer", A("p2", 0) + 3.0, 0.35),
           *[cue("page", A("p2", k), 0.4) for k in (15, 16, 17)], cue("kaching", A("p2", 13), 0.45),
           cue("whoosh", A("f1", 5) - 0.1, 0.35), cue("ting", A("c2", 10), 0.35), cue("kaching", A("c2", 21), 0.5),
           cue("pipe", A("l1", 2), 0.4), cue("splash", A("l1", 2) + 0.1, 0.35), cue("glitch", A("l1", 0), 0.25),
           cue("vineboom", A("a1", 12), 0.4), cue("rewind", A("r1", 0) - 0.05, 0.45), cue("kaching", A("r1", 10), 0.5)]
    for o in overlays:
        k = o["kind"]
        if k in ("stamp", "logo") and not any(abs(o["from"] - c["from"]) < 4 for c in sfx):
            sfx.append({"src": "sfx/pop.mp3", "from": o["from"], "volume": 0.35})
        elif k == "wasted":
            sfx.append({"src": "sfx/boom.mp3", "from": o["from"], "volume": 0.45})
        elif k == "passed":
            sfx.append({"src": "sfx/ding.mp3", "from": o["from"], "volume": 0.5})
        elif k == "receipt":
            sfx.append({"src": "sfx/printer.mp3", "from": o["from"], "volume": 0.18, "dur": 24})
        elif k == "bridge":
            sfx += [{"src": "sfx/whoosh.mp3", "from": o["from"] - 3, "volume": 0.4}, {"src": "sfx/pop.mp3", "from": o["from"] + o["pop"], "volume": 0.55}]
        elif k == "counter":
            sfx.append({"src": "sfx/kaching.mp3", "from": o["from"] + 36, "volume": 0.3})
        elif k == "pipeline":
            sfx += [{"src": "sfx/click.mp3", "from": o["from"] + st["at"], "volume": 0.4} for st in o["steps"]]
    for s in shots:
        if s["glitch"] and s["from"] > F(4):
            sfx.append({"src": "sfx/freeze.mp3", "from": s["from"], "volume": 0.15})

    # captions: merge spoken numbers into one display token
    merged, skip = {}, set()
    for k, i0, n, txt in SHOW:
        merged[(k, i0)] = (cw[(k, i0)][0], cw[(k, i0 + n - 1)][1], txt)
        skip |= {(k, i0 + j) for j in range(1, n)}
    last = {}
    for (k, i) in cw:
        last[k] = max(last.get(k, -1), i)
    for kk in list(merged):
        k, i0 = kk
        n = next(n for kx, ix, n, _ in SHOW if (kx, ix) == kk)
        if i0 + n - 1 == last[k]:
            a, b, txt = merged[kk]
            merged[kk] = (a, b, txt + ".")
    cap = [merged.get(kk, (v[0], v[1], v[2] + "." if kk[1] == last[kk[0]] else v[2]))
           for kk, v in sorted(cw.items(), key=lambda x: x[1][0]) if kk not in skip]
    words = [[F(a), F(b), w] for a, b, w in cap]
    props = {
        "fps": FPS, "durationInFrames": F(story_end), "shots": shots, "overlays": overlays,
        "hud": {"from": F(A("h2", 0)), "to": F(A("h4", 2)), "years": [], "cash": [[F(A("h2", 0)), 0], [F(E("h2", 5)), 1_000_000_000]]},
        "credit": {"text": "Footage: Rockstar Games", "to": F(story_end), "perShot": True},
        "words": words, "captionsFrom": F(A("h1", 4)),
        "emphasis": ["13", "moon", "$1billion", "$5million", "$3billion", "gta6", "billion", "wrong", "money", "4711", "$100k", "half", "year", "florida", "2015", "hand",
                     "beer", "pay", "90", "$5", "million", "$975000", "one", "sign", "$3", "fast", "vi3w", "3d", "seconds", "broke"],
        "cues": sfx,
    }
    pj = OUT / "props.json"
    pj.write_text(json.dumps(props, indent=1))
    if missing:
        print("PLACEHOLDER shots (3D not delivered yet):", sorted(set(missing)))

    rem = ROOT / "node" / "remotion"
    raw = OUT / f"story{'-preview' if preview else ''}.mp4"
    t = time.time()
    run(["npx", "remotion", "render", "src/shorts/index.ts", "Gta13", raw, "--codec", "h264", "--crf", "17", "--pixel-format", "yuv420p",
         "--image-format", "jpeg", "--jpeg-quality", "92", "--timeout", "240000", "--concurrency", "6", "--props", pj,
         "--public-dir", PUB] + (["--scale", "0.5"] if preview else []), cwd=rem, timeout=3600)
    t_render = time.time() - t

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
             f"[3:a]aresample={SR},volume=0.42,afade=t=in:d=0.3,afade=t=out:st={end - 2.0:.2f}:d=2.0[mus]",
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
                      "total_s": round(time.time() - t_all), "loudness": media.loudness(mp4), "placeholders": sorted(set(missing))}))
    if not preview and not missing:
        dst = ROOT / "FinalUploads" / "Drafts"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy(mp4, dst / f"{NAME}.mp4")
        if (D / "caption.txt").exists():
            (dst / f"{NAME}.txt").write_text((D / "caption.txt").read_text())


if __name__ == "__main__":
    main(preview="--preview" in sys.argv)
