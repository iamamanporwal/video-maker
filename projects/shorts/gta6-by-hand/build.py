"""GTA 6 took 13 years because everything was made BY HAND — game-dev 3D short → Remotion Gta13 + shared Vi3W outro.

usage: .venv/bin/python projects/shorts/gta6-by-hand/build.py [--preview]
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

NAME = "gta6-by-hand"
FPS, SR = 30, 48000
OUT, PUB = D / "out", D / "public"
TEMPO = 1.12
VO_AT = 0.25
DROP: set = set()
BLEEP = ("a1", 6)                               # "freaking" → bleep (caption #@$%ing)
GAP_IN, GAP_LINE = 0.2, 0.28                    # max pause inside a line / between lines (source seconds)
BEAT = {"h1": 0.15, "h2": 0.35, "h4": 0.3, "p2": 0.3, "a1": 0.3, "a2": 0.3, "q1": 0.35, "q2": 0.3, "s2": 0.45, "b1": 0.35}  # held beats after lines
MUSIC = ROOT / "projects/shorts/gta6-facts/public/music/hitman.mp3"       # Kevin MacLeod "Hitman", CC BY 4.0
F = lambda s: round(s * FPS)  # noqa: E731

SRC = {  # official Rockstar uploads (h264 copies) + GTA VI trailers from the gta6-facts project
    "rev": D / "ref/h264/QkkoHAzjnUs.mp4", "mft": D / "ref/h264/Bf38HiYPMiI.mp4", "gp": D / "ref/h264/N-xHcvug3WI.mp4",
    "onl": D / "ref/h264/olEGtoYs_8A.mp4", "casino": D / "ref/h264/lX_IN4v-RnA.mp4", "heist": D / "ref/h264/UUmKwJD76GY.mp4",
    "ng": D / "ref/h264/foUaOCzfIRU.mp4", "ps5": D / "ref/h264/VNbONMSObfs.mp4", "rdr": D / "ref/h264/eaW0tYpxyp0.mp4",
    "t1": ROOT / "projects/shorts/gta6-facts/public/clips/t1.mp4", "t2": ROOT / "projects/shorts/gta6-facts/public/clips/t2.mp4",
    "rz": ROOT / "projects/shorts/gta6-facts/public/clips/rz.mp4",
}
SRC = {k: (ROOT / "projects/shorts/gta6-13-years" / v.relative_to(D) if str(v).startswith(str(D)) else v) for k, v in SRC.items()}


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
    if BLEEP:
        bi = spans[BLEEP[0]][0] + BLEEP[1]
        pcm = pcm.copy()
        pcm[int((words[bi][0] - 0.02) * SR):int((words[bi][1] + 0.02) * SR)] = 0
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
        w = "#@$%ing" if (k, wi) == BLEEP else words[i][2]
        cw[(k, wi)] = (remap(words[i][0]), remap(min(words[i][1], segs[-1][1])), w)
    dur = float(media.probe(wav)["format"]["duration"])
    return wav, cw, VO_AT + dur


# --------------------------------------------------------------------------- 2. edit

def edit(A, E, story_end):
    """Shots: (start_s, src, src_s, cx, grade, flags) — each runs to the next start. 3D first; Rockstar clips are punctuation."""
    has3d = lambda n: (PUB / "3d" / f"{n}.mp4").exists()  # noqa: E731
    td = lambda n, fb: ("3d", f"3d/{n}.mp4", 0.5) if has3d(n) else fb  # noqa: E731  (src, at, cx)
    S = []

    def sh(t, src, at, cx=0.5, grade="none", fl=""):
        S.append((t, src, at, cx, grade, fl))

    sh(0, *td("trashcan", ("rev", 32.5, 0.6)))                                 # HOOK: cube → trash can, "By hand."
    sh(A("h3", 0), *td("props", ("rev", 7.5, 0.6)))                            # bench, palm tree
    sh(A("h4", 0), *td("citypull", ("gp", 26.0, 0.5)))                         # "...an entire state"
    sh(A("p1", 0), *td("pipeline", ("mft", 15.0, 0.5)))                        # cube → model → UV → texture
    sh(A("p2", 0), *td("florida", ("gp", 26.0, 0.5)))                          # every alley in...
    sh(A("p2", 7), "t1", 3.0, 0.5, "vice", "c")                                # ..."fake Florida" — the real thing
    sh(A("n1", 0), *td("npcs", ("onl", 47.5, 0.5)))
    sh(A("n2", 0), *td("rig", ("mft", 42.5, 0.45)))
    sh(A("a1", 0), *td("animate", ("mft", 207.5, 0.6)))
    sh(A("a2", 0), "rdr", 101.5, 0.45, "warm", "c")                            # RDR2: 300,000 animations
    sh(A("a3", 0), *td("cycles", ("mft", 70.0, 0.35)))
    sh(A("q1", 0), *td("fallthrough", ("gp", 265.0, 0.4)))
    sh(A("q2", 0), *td("bugs", ("mft", 205.0, 0.45)), "none", "g")
    sh(A("s1", 0), "rdr", 55.0, 0.55, "warm", "c")                             # "they shipped Red Dead 2"
    sh(A("s1", 7), *td("consoles", ("gp", 280.5, 0.5)))                        # re-released GTA 5... twice (our 3D consoles)
    sh(A("s2", 0), *td("office", ("onl", 47.5, 0.5)))                          # 4,700 people
    sh(A("b1", 0), *td("lonely", ("rev", 40.0, 0.65)), "cold")                 # "You don't have 4,700 people."
    sh(A("b2", 0), *td("lonely", ("rz", 25.5, 0.55)), "cold")                  # plate under the sketch → 3D panels
    S.sort(key=lambda s: s[0])

    ov = [
        dict(kind="viewport", t=A("h3", 0), u=A("p1", 0), mode="Object Mode", objects=[3, 48210]),
        dict(kind="viewport", t=A("p1", 0), u=A("p2", 0), mode="Edit Mode", tris=[12, 18640]),
        dict(kind="pipeline", t=A("p1", 4), u=A("p2", 7), steps=[dict(label="BLOCKOUT", at=A("p1", 5)), dict(label="MODEL", at=A("p1", 7)),
             dict(label="UV UNWRAP", at=A("p1", 9)), dict(label="TEXTURE", at=A("p1", 11))]),
        dict(kind="stamp", t=A("p2", 7), u=A("n1", 0), text="FAKE FLORIDA", sub="LEONIDA · GTA 6", color="#FF3E9A", rot=-5),
        dict(kind="viewport", t=A("n1", 0), u=A("n2", 0), mode="Object Mode", objects=[1, 640]),
        dict(kind="stamp", t=A("n1", 7), u=A("n2", 0), text="NPC OFFICE", sub="A WHOLE STUDIO FOR NPCs (BLOOMBERG)", color="#4FA3FF", rot=-4),
        dict(kind="viewport", t=A("n2", 0), u=A("a1", 0), mode="Pose Mode"),
        dict(kind="console", t=A("n2", 8), u=A("a1", 0), lines=[dict(text="Bad vertex weights: forearm_L", at=A("n2", 8), warn=True),
             dict(text="Elbow folding like a lawn chair", at=A("n2", 11), warn=True)]),
        dict(kind="viewport", t=A("a1", 0), u=A("a2", 0), mode="Pose Mode · Keyframing", rec=True),
        dict(kind="keys", t=A("a1", 0), u=A("a2", 0), keys=[]),
        dict(kind="counter", t=A("a2", 0), u=A("a3", 0), value=300_000, label="ANIMATIONS IN RED DEAD 2", note="DAN HOUSER · 2018"),
        dict(kind="pipeline", t=A("a3", 0), u=A("q1", 0), steps=[dict(label="WALK", at=A("a3", 0)), dict(label="RUN", at=A("a3", 1)),
             dict(label="TRIP", at=A("a3", 2)), dict(label="HIT BY CAR", at=A("a3", 4)), dict(label="CLEANUP ×300,000", at=A("a3", 10))]),
        dict(kind="viewport", t=A("q1", 0), u=A("q2", 0), mode="▶ Play"),
        dict(kind="console", t=A("q1", 8), u=A("q2", 0), lines=[dict(text="Vehicle_Sedan fell out of world (z=-9999)", at=A("q1", 8))]),
        dict(kind="console", t=A("q2", 0), u=A("s1", 0), lines=[dict(text="FIXED: vehicle collision", at=A("q2", 0), warn=True),
             dict(text="NPC_0412 stuck in T-pose (in the sky)", at=A("q2", 3)), dict(text="palm_tree_07: mesh exploded", at=A("q2", 3) + 0.15),
             dict(text="Car inside wall. Again.", at=A("q2", 3) + 0.3)]),
        dict(kind="stamp", t=A("s1", 0), u=A("s1", 7), text="RDR2", sub="SHIPPED 2018", color="#FF9A3C", rot=-6),
        dict(kind="stack", t=A("s1", 7), u=A("s2", 0), title="GTA V · RELEASED 3 TIMES",
             items=[dict(a="PS3", b="2013", at=A("s1", 7)), dict(a="PS4", b="2014", at=A("s1", 10)), dict(a="PS5", b="2022", at=A("s1", 10) + 0.2)]),
        dict(kind="counter", t=A("s2", 0), u=A("b1", 0), value=4711, label="ROCKSTAR STAFF · AUG 2026", note="~8 YEARS OF DEVELOPMENT"),
        dict(kind="bridge", t=A("b2", 0) - 0.05, u=story_end, sketch="img/sketch.png", model="clips/car3d.mp4", pop=A("b2", 4)),
    ]
    k0, k1 = A("a1", 0), A("a2", 0)
    for o in ov:
        if o["kind"] == "keys":
            o["keys"] = [k0 + 0.15 + i * (k1 - k0 - 0.4) / 7 for i in range(8)]
    return S, ov, [], []


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
                      "mode": "band" if "b" in fl else "full", "grade": grade, "glitch": "g" in fl, "speed": speed, "credit": "c" in fl})

    overlays = []
    for o in ov:
        o = dict(o)
        a, b = o.pop("t"), o.pop("u")
        if o["kind"] == "bridge":
            o["pop"] = F(o["pop"]) - F(a)
        for lst in ("items", "msgs", "steps", "lines"):
            if lst in o:
                o[lst] = [{**it, "at": F(it["at"]) - F(a)} for it in o[lst]]
        if "keys" in o:
            o["keys"] = [F(x) - F(a) for x in o["keys"]]
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
        if k == "pipeline":
            sfx += [{"src": "sfx/click.mp3", "from": o["from"] + st["at"], "volume": 0.4} for st in o["steps"]]
        elif k == "console":
            sfx += [{"src": "sfx/error.mp3", "from": o["from"] + ln["at"], "volume": 0.3} for ln in o["lines"]]
    bw = cw[BLEEP]
    sfx.append({"src": "sfx/bleep.mp3", "from": F(bw[0]) - 1, "volume": 0.35, "dur": F(bw[1] - bw[0]) + 3})
    for s in shots:
        if s["glitch"] and s["from"] > F(4):
            sfx.append({"src": "sfx/freeze.mp3", "from": s["from"], "volume": 0.18})
    for n, src in [("whoosh", "gta6-facts/public/sfx"), ("boom", "gta6-facts/public/sfx"), ("ding", "gta6-facts/public/sfx"),
                   ("pop", "gta6-facts/public/sfx"), ("freeze", "gta6-facts/public/sfx"), ("kaching", "landlord-dog/sfx"),
                   ("click", "landlord-dog/sfx")]:
        dst = PUB / "sfx" / f"{n}.mp3"
        if not dst.exists():
            shutil.copy(ROOT / "projects/shorts" / src / f"{n}.mp3", dst)
    for n, af in [("bleep", "sine=f=1000:d=0.8"), ("error", "sine=f=330:d=0.09,apad=pad_dur=0.04,aloop=loop=1:size=6240")]:
        if not (PUB / "sfx" / f"{n}.mp3").exists():
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", af, "-af", "volume=0.5", PUB / "sfx" / f"{n}.mp3"])

    words = [[F(a), F(b), w] for (k, i), (a, b, w) in sorted(cw.items(), key=lambda x: x[1][0])]
    props = {
        "fps": FPS, "durationInFrames": F(story_end), "shots": shots, "overlays": overlays,
        "hud": {"from": 0, "to": 0, "years": [], "cash": []},
        "credit": {"text": "Footage: Rockstar Games", "to": F(story_end), "perShot": True},
        "words": words, "captionsFrom": F(4.5),
        "emphasis": ["hand", "bench", "palm", "state", "cube", "model", "unwrap", "texture", "florida", "npcs", "skeleton", "lawn",
                     "chairs", "ing", "three", "hundred", "thousand", "walk", "run", "trip", "car", "map", "bug", "twice", "4700", "eight",
                     "one", "sketch", "rigged", "animate", "thirteen", "trash", "can"],
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
