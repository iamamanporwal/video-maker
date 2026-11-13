"""How do open worlds like GTA 6 stay fast? LOD, culling, streaming, instancing — own-3D dev-facts short → Remotion Gta13 + shared Vi3W outro.

usage: .venv/bin/python projects/shorts/gta6-download/build.py [--plan] [--preview]
  --plan   only write scenes/dur.json (3D shot lengths + event fractions from the VO word times), then render 3D with
           scenes/build.py <shots> --full
Facts + sources: RESEARCH.md. VO: vo_cb.py (Chatterbox). Earth textures: Solar System Scope (CC BY 4.0).
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

NAME = "gta6-optimized"
VOICE = "cb"
FPS, SR = 30, 48000
OUT, PUB = D / "out", D / "public"
TEMPO = float(os.environ.get("TEMPO", "1.0"))
VO_AT = 0.15
GAP_IN, GAP_LINE = 0.28, 0.34
BEAT = {"h1": 0.3, "h3": 0.4, "p1": 0.6, "p2": 0.45}
MUSIC = ROOT / "projects/shorts/gta6-facts/public/music/hitman.mp3"       # Kevin MacLeod "Hitman", CC BY 4.0
F = lambda s: round(s * FPS)  # noqa: E731
SRC = {"t1": ROOT / "projects/shorts/gta6-facts/public/clips/t1.mp4", "t2": ROOT / "projects/shorts/gta6-facts/public/clips/t2.mp4",
       "rz": ROOT / "projects/shorts/gta6-facts/public/clips/rz.mp4"}
SHOW = [("h1", 0, 2, "GTA 6"), ("h3", 1, 4, "30 FPS"), ("h3", 8, 2, "33 MS"), ("t1", 8, 2, "35,000"), ("p1", 9, 2, "33 MS"), ("b1", 9, 1, "Vi3W")]
SFX = {"kaching": "landlord-dog/sfx", "slam": "mcqueen-brain/sfx", "riser": "mcqueen-brain/sfx", "vineboom": "mcqueen-brain/sfx", "shock": "mcqueen-brain/sfx",
       "pop": "gta6-facts/public/sfx", "whoosh": "gta6-facts/public/sfx", "boom": "gta6-facts/public/sfx", "ding": "gta6-facts/public/sfx",
       "freeze": "gta6-facts/public/sfx", "click": "landlord-dog/sfx", "ting": "roblox-hooks/sfx", "drop": "roblox-hooks/sfx"}
SFX_X = {"glitch": "projects/artist-who-couldnt-create/audio/sfx/glitch.mp3"}
PAD = 0.2                                                                 # extra seconds rendered per 3D shot


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
    """Shots: (start_s, src, at_s, cx, grade, flags). src = '3d:<name>' (public/3d)."""
    S = []

    def sh(t, src, at=0.0, cx=0.5, grade="none", fl=""):
        S.append((t, src, at, cx, grade, fl))

    sh(0, "3d:street")                                                        # HOOK: dusk boulevard → wire dissolve "not drawn"
    sh(A("h3", 0), "3d:drive")
    sh(A("t1", 0), "3d:lodline")
    sh(A("t1", 11), "3d:lod")
    sh(A("t2", 0), "3d:cull")
    sh(A("t3", 0), "3d:stream")
    sh(A("t4", 0), "3d:crowd")
    sh(A("p1", 0), "3d:reveal")
    sh(A("p2", 0), "3d:street", 0.3)
    sh(A("b1", 0), "3d:lodline", 0.8)
    S.sort(key=lambda s: s[0])
    ends = [s[0] for s in S[1:]] + [story_end]
    dur = {}
    for (t, src, at, *_), t1 in zip(S, ends):
        if src.startswith("3d:"):
            dur[src[3:]] = round(max(dur.get(src[3:], 0), at + (t1 - t) + PAD), 2)
    start = lambda name: next(s[0] for s in S if s[1] == "3d:" + name)  # noqa: E731
    frac = lambda name, t: round((t - start(name)) / dur[name], 3)  # noqa: E731
    dur["street@ev"] = frac("street", A("h2", 6))
    dur["cull@ev"] = frac("cull", A("t2", 7))
    dur["crowd@ev"] = frac("crowd", A("t4", 7))
    (D / "scenes" / "dur.json").write_text(json.dumps(dur, indent=1))

    cnt = json.loads((D / "out3d" / "lod_counts.json").read_text()) if (D / "out3d" / "lod_counts.json").exists() else {"0": 35162, "1": 8790, "2": 2109, "3": 526}
    pink, red, yel, grn, cy = "#FF3E9A", "#E8303A", "#FFE14D", "#6FDB6A", "#5CE1FF"
    ts, tl = start("lod"), dur["lod"]
    sw = [ts + f * tl for f in (0.0, 0.30, 0.55, 0.78)] + [A("t2", 0)]
    lodtips = [dict(kind="tip", t=sw[i], u=sw[i + 1], text=f"LOD {i} · {cnt[str(i)]:,} TRIANGLES") for i in range(4)]
    ov = [
        dict(kind="logo", t=0.05, u=A("h1", 6), src="logos/gta6_logo.png", x=540, y=190, w=430, glow=pink, slam=True),
        dict(kind="stamp", t=A("h2", 6), u=A("h3", 0), text="NOT DRAWN", sub="MOST OF THE CITY", color=red, rot=-5),
        dict(kind="counter", t=A("h3", 1), u=A("h3", 12), value=33, label="MS PER FRAME", note="30 FPS = 33 MILLISECONDS"),
        dict(kind="tip", t=A("h3", 12), u=A("t1", 0), text="THE STANDARD OPEN-WORLD TRICKS. NOT ROCKSTAR'S CODE."),
        dict(kind="chapter", t=A("t1", 0), u=A("t1", 4), n="1", title="LOD", color=yel),
        *lodtips,
        dict(kind="chapter", t=A("t2", 0), u=A("t2", 3), n="2", title="CULLING", color=cy),
        dict(kind="tip", t=A("t2", 3), u=A("t2", 7), text="YELLOW CONE = WHAT THE CAMERA SEES."),
        dict(kind="stamp", t=A("t2", 7) + 0.1, u=A("t3", 0), text="OCCLUDED", sub="HIDDEN BEHIND A BUILDING", color=red, rot=-5),
        dict(kind="chapter", t=A("t3", 0), u=A("t3", 3), n="3", title="STREAMING", color=grn),
        dict(kind="tip", t=A("t3", 3), u=A("t4", 0), text="ONLY NEARBY TILES STAY LOADED."),
        dict(kind="chapter", t=A("t4", 0), u=A("t4", 3), n="4", title="INSTANCING", color=pink),
        dict(kind="counter", t=A("t4", 4), u=A("p1", 0), value=100, label="PEDESTRIANS · ONE MODEL", note="SAME MESH, DRAWN 100 TIMES"),
        dict(kind="stamp", t=A("p1", 9) , u=A("p2", 0), text="33 MS", sub="THE WHOLE CITY", color=grn, rot=-5),
        dict(kind="passed", t=A("p1", 11) + 0.2, u=A("p2", 0), sub="CITY RENDERED"),
        dict(kind="bridge", t=A("b1", 12) - 0.05, u=story_end, sketch="img/sketch.png", model="clips/car3d.mp4", pop=A("b1", 18)),
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
    if "--plan" in sys.argv:
        print((D / "scenes" / "dur.json").read_text(), "story_end", round(story_end, 2))
        return

    shots, missing = [], []
    for i, (t, src, at, cx, grade, fl) in enumerate(S):
        t1 = S[i + 1][0] if i + 1 < len(S) else story_end
        dur = t1 - t
        speed, start = 1.0, 0
        if src.startswith("3d:"):
            p = PUB / "3d" / f"{src[3:]}.mp4"
            if not p.exists():                                                  # placeholder until the 3D agent delivers
                missing.append(src[3:])
                path = cut(SRC["t2"], 30 + (i % 5) * 2.5, dur)
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
    sfx = [cue("whoosh", 0, 0.4), cue("glitch", A("h2", 6) - 0.05, 0.4), cue("boom", A("h2", 6), 0.5), cue("riser", A("h2", 6) - 1.2, 0.3),
           cue("click", A("t2", 7), 0.5), cue("ting", A("p1", 11) , 0.3), cue("drop", A("t4", 7), 0.4)]
    for sh_ in shots[1:]:
        sfx.append({"src": "sfx/whoosh.mp3", "from": max(0, sh_["from"] - 3), "volume": 0.3})
    for o in overlays:
        k = o["kind"]
        if k in ("stamp", "logo") and not any(abs(o["from"] - c["from"]) < 4 for c in sfx):
            sfx.append({"src": "sfx/pop.mp3", "from": o["from"], "volume": 0.35})
        elif k == "chapter":
            sfx.append({"src": "sfx/slam.mp3", "from": o["from"], "volume": 0.45})
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
        "hud": {"from": 0, "to": 0, "years": [], "cash": []},
        "credit": {"text": "", "to": 0, "perShot": True},
        "words": words, "captionsFrom": 0,
        "emphasis": ["gta6", "lying", "drawn", "30fps", "33ms", "cheats", "lod", "35000", "triangles", "culling", "streaming", "instancing", "hundred", "one", "model", "city", "looking", "vi3w", "sketch", "seconds", "never", "see", "frame", "behind", "unload"],
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
         "--image-format", "jpeg", "--jpeg-quality", "92", "--timeout", "600000", "--concurrency", os.environ.get("CONC", "3"), "--props", pj,
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
