"""python build.py [--no-render] [--stills 4,8.5,...]: tex.py → scene.py → parallel EEVEE (PS2 360x640) →
RADAL mod clips (hook 0-3.3 s + montage 17.9-26.1 s, muted, 9:16 centre crop) + 3D story + PS2 captions + HUD +
SFX in VO gaps + ducked music + shared Vi3W outro. VO: Kokoro af_heart (vo.py); outro: cached Laura take.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
import os  # noqa: E402
for _l in (ROOT / ".env").read_text().splitlines():
    if "=" in _l and not _l.lstrip().startswith("#"):
        _k, _v = _l.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
from reelforge.blender.render import BLENDER, render_shots  # noqa: E402
from reelforge import outro  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT, FPS = D / "out", 30
STORY_END = 42.3
END = STORY_END + outro.META["dur"]
NAME = "gta6-no-pc-mods"
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MUSIC = D / "music/hitman.mp3"                  # Kevin MacLeod, "Hitman", CC BY 4.0
SRC = D / "src"
KX, CE, HC = "keXlwOZUcaY", "CEUkE7WRPUI", "Hc0GSvJ5ZAw"   # RADAL: babushka GTA 5 mods / Worst GTA 5 Mods / GTA 5 mods are funny
# timeline: (kind, t0, t1, payload) — clip payload = [(video, src_in, src_out)] stretched to fill t1-t0
TIMELINE = [("clip", 0.0, 3.3, [(KX, 216.5, 217.8), (KX, 218.0, 218.6), (KX, 220.9, 222.3)]),
            ("3d", 3.3, 17.9, None),
            ("clip", 17.9, 19.85, [(CE, 616.9, 618.85)]),
            ("clip", 19.85, 21.9, [(CE, 401.4, 403.45)]),
            ("clip", 21.9, 23.95, [(HC, 83.0, 85.05)]),
            ("clip", 23.95, 26.1, [(KX, 226.3, 228.0)]),
            ("3d", 26.1, STORY_END, None)]
HUD = [("hud_day1", 26.1, 29.5), ("hud_h1", 29.5, 31.9), ("hud_h3", 31.9, 34.2), ("hud_h6", 34.2, 37.1), ("hud_h9", 37.1, 40.1)] + \
      [(f"hud_m{n:02d}", 8.9 + (n - 1) * 0.12, 8.9 + n * 0.12 if n < 19 else 11.5) for n in range(1, 20)] + \
      [("credit", 0.0, 3.3), ("credit", 17.9, 26.1)]
CUES = [(3.22, "whoosh", 0.4), (6.95, "dun", 0.45), (14.1, "vineboom", 0.8), (17.5, "boom", 0.9), (19.13, "flush", 0.7),
        (21.07, "moo", 0.9), (23.27, "splash", 0.5), (25.55, "boom", 0.8), (31.24, "boom", 0.9), (33.58, "moo", 0.8),
        (36.44, "error", 0.45), (38.4, "spark", 0.25), (39.4, "boom", 0.7), (41.76, "vineboom", 0.8),
        (STORY_END + 4.0, "click", 0.6)]
MERGE = [(("GTA", "six"), "GTA 6"), (("GTA", "five"), "GTA 5"), (("nineteenth",), "19th"), (("nineteen",), "19")]


def run(cmd, timeout=900):
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)


def merge(words):
    out, i = [], 0
    while i < len(words):
        for pat, rep in MERGE:
            seg = words[i:i + len(pat)]
            if len(seg) == len(pat) and all(w[2].strip(".,?!").lower() == p.lower() for w, p in zip(seg, pat)):
                tail = seg[-1][2][len(seg[-1][2].rstrip(".,?!")):]
                out.append([seg[0][0], seg[-1][1], rep + tail, seg[0][3]])
                i += len(pat)
                break
        else:
            out.append(words[i])
            i += 1
    return out


def phrases(words, max_words=4):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if len(cur) >= max_words or w[2][-1] in ".,?!" or (nxt and (nxt[0] - w[1] > 0.06 or nxt[3] != w[3])):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def card(text, path, size=68, y=0.69, fill="#f8e800"):
    font = ImageFont.truetype(FONT, size)
    im = Image.new("RGBA", (1080, 1920))
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=font)
    d.text(((1080 - tw) / 2, int(1920 * y)), text, font=font, fill=fill, stroke_width=6, stroke_fill="black")
    im.save(path)


def caption_cards(words, out_dir):
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)
    cards, chunks = [], phrases(merge(words))
    for k, ch in enumerate(chunks):
        text = " ".join(w[2] for w in ch).rstrip(",")
        p = out_dir / f"cap_{k:03d}.png"
        card(text, p)
        t1 = chunks[k + 1][0][0] if k + 1 < len(chunks) else ch[-1][1] + 0.5
        cards.append((p, ch[0][0], min(t1 - 0.02, ch[-1][1] + 0.45)))
    return cards


def lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])


def level(mp4, target=-14.0):
    gain = target - lufs(mp4)
    tmp = mp4.with_suffix(".lvl.mp4")
    run(["ffmpeg", "-y", "-i", mp4, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp])
    tmp.replace(mp4)


def clip_seg(k, t0, t1, parts):
    """RADAL footage → silent 1080x1920 segment of exactly t1-t0 s (speed-stretched to fit)."""
    seg = OUT / f"seg_{k:02d}.mp4"
    src = sum(b - a for _, a, b in parts)
    f = (t1 - t0) / src
    cmd, fc = ["ffmpeg", "-y"], []
    for i, (v, a, b) in enumerate(parts):
        cmd += ["-ss", str(a), "-t", str(b - a), "-i", SRC / f"{v}.mp4"]
        fc.append(f"[{i}:v]setpts=(PTS-STARTPTS)*{f:.4f},fps={FPS},scale=-2:1920,crop=1080:1920,setsar=1,format=yuv420p[p{i}]")
    fc.append("".join(f"[p{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0[v]")
    run(cmd + ["-filter_complex", ";".join(fc), "-map", "[v]", "-t", f"{t1 - t0:.3f}", "-an", "-c:v", "libx264", "-crf", "16", seg])
    return seg


def frames_seg(k, t0, t1, frames):
    seg = OUT / f"seg_{k:02d}.mp4"
    f0, n = round(t0 * FPS) + 1, round((t1 - t0) * FPS)
    seq = [frames / f"f_{f:04d}.png" for f in range(f0, f0 + n)]
    lst = OUT / f"frames_{k:02d}.txt"
    lst.write_text("".join(f"file '{p}'\nduration {1 / FPS:.6f}\n" for p in seq))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"fps={FPS},scale=1080:1920:flags=neighbor,setsar=1,format=yuv420p",
         "-t", f"{t1 - t0:.3f}", "-c:v", "libx264", "-crf", "14", seg])
    return seg


def main(do_render=True):
    t_all, stamps = time.time(), {}
    vo = json.loads((OUT / "words.json").read_text())
    frames = OUT / "frames"
    run([sys.executable, D / "tex.py"])
    if do_render:
        t = time.time()
        run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
        stamps["scene"] = time.time() - t
        shutil.rmtree(frames, ignore_errors=True)
        shots = json.loads((OUT / "shots.json").read_text())
        stamps["render"] = render_shots(str(OUT / "scene.blend"), str(frames), shots, workers=3)
    t = time.time()
    segs = [clip_seg(k, a, b, p) if kind == "clip" else frames_seg(k, a, b, frames) for k, (kind, a, b, p) in enumerate(TIMELINE)]
    story = OUT / "story.mp4"
    cc = ["ffmpeg", "-y"]
    for sg in segs:
        cc += ["-i", sg]
    fc = "".join(f"[{i}:v]settb=1/{FPS},setpts=N/{FPS}/TB,fps={FPS}[c{i}];" for i in range(len(segs)))
    fc += "".join(f"[c{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[v]"
    run(cc + ["-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-crf", "14", "-preset", "fast", story])
    cards = caption_cards(vo["words"], OUT / "captions")
    o_mp3, _, o_at = outro.voice(D)
    cmd = ["ffmpeg", "-y", "-i", story, "-i", vo["mp3"], "-i", o_mp3, "-stream_loop", "-1", "-i", MUSIC, "-i", outro.CLIP]
    n_sfx = 5
    for _, name, _v in CUES:
        cmd += ["-i", SFX(name)]
    n_ov = n_sfx + len(CUES)
    overlays = [(OUT / "ov" / f"{n}.png", a, b) for n, a, b in HUD] + cards
    for p, *_ in overlays:
        cmd += ["-i", p]
    chain = [f"[0:v]fps={FPS},setsar=1,format=yuv420p[st]", f"[4:v]fps={FPS},scale=1080:1920,setsar=1,format=yuv420p[ou]",
             "[st][ou]concat=n=2:v=1:a=0[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(overlays):
        chain.append(f"[{last}][{n_ov + k}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]fade=t=out:st={END - 0.6}:d=0.6[vout]")
    o_ms = int((STORY_END + o_at) * 1000)
    chain.append("[1:a]aresample=48000,volume=1.5[vo1]")
    chain.append(f"[2:a]aresample=48000,volume=1.3,adelay={o_ms}|{o_ms}[vo2]")
    chain.append("[vo1][vo2]amix=inputs=2:normalize=0:duration=longest,apad,asplit=2[vo][key]")
    chain.append(f"[3:a]aresample=48000,volume=0.17,afade=t=out:st={END - 2.0}:d=2.0[mus]")
    chain.append("[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[duck]")
    sfx = []
    for i, (t_, name, vol) in enumerate(CUES):
        ms = int(t_ * 1000)
        chain.append(f"[{n_sfx + i}:a]aresample=48000,volume={vol},adelay={ms}|{ms}[s{i}]")
        sfx.append(f"[s{i}]")
    chain.append(f"[vo][duck]{''.join(sfx)}amix=inputs={2 + len(sfx)}:normalize=0:duration=first,atrim=0:{END}[aout]")
    mp4 = OUT / f"{NAME}.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", f"{END}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
            "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", mp4]
    run(cmd)
    level(mp4)
    stamps["compose"] = time.time() - t
    print(" | ".join(f"{k} {v:.1f}s" for k, v in stamps.items()), f"| TOTAL {time.time() - t_all:.1f}s →", mp4)


def SFX(name):
    return D / "sfx" / f"{name}.mp3"


def stills(times):
    run([sys.executable, D / "tex.py"])
    run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
    shots = json.loads((OUT / "shots.json").read_text())
    jobs = []
    for t in times:
        f = round(t * FPS) + 1
        sc = next(s for s, a, b in shots if a <= f <= b)
        jobs.append((sc, f, f))
    dst = OUT / "stills"
    shutil.rmtree(dst, ignore_errors=True)
    dt = render_shots(str(OUT / "scene.blend"), str(dst), jobs, workers=3)
    fs = sorted(dst.glob("f_*.png"))
    cols, w, h = 6, 360, 640
    sheet = Image.new("RGB", (w * cols, h * (-(-len(fs) // cols))), "black")
    for i, f in enumerate(fs):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(Image.open(f).convert("RGB"), (x, y))
        ImageDraw.Draw(sheet).text((x + 6, y + 6), f"{(int(f.stem[2:]) - 1) / FPS:.1f}s", fill="red")
    sheet.save(OUT / "sheet.jpg", quality=90)
    print(f"{len(times)} stills in {dt:.1f}s → out/sheet.jpg")


if __name__ == "__main__":
    if "--stills" in sys.argv:
        stills([float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")])
    else:
        main(do_render="--no-render" not in sys.argv)
