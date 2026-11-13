"""python build.py [--no-render] [--stills 4,8.5,...]: tex.py → scene.py → parallel EEVEE (PS2 360x640) →
official GTA 6 trailer hook (muted, 0-3.7 s) + nearest-neighbour upscale + PS2 captions + stamps + SFX + ducked music
+ shared Vi3W outro. VO: Kokoro am_michael (vo.py), outro: cached Laura take.
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
HOOK_END, STORY_END = 3.7, 49.0
END = STORY_END + outro.META["dur"]
NAME = "gta6-ai-slop"
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MUSIC, MUSIC_AT = D / "music/fluffing-a-duck.mp3", 7.7    # Kevin MacLeod, "Fluffing a Duck", CC BY 4.0
CLIPS = ROOT / "projects/shorts/gta6-facts/public/clips"
TRAILER = [("t1.mp4", 13.5, 1.85, "iw:ih:0:0"), ("t2.mp4", 50.3, 1.85, "1920:864:0:108")]  # (file, start, dur, letterbox crop) — official Rockstar trailers, muted
SFX = D / "sfx"
STAMPS = [("delayed", 19.85, 20.6), ("skill", 44.85, 45.75)]
CUES = [(3.62, "vhs", 0.45), (7.7, "whoosh", 0.4), (11.05, "yt-boing", 0.7), (14.75, "vineboom", 0.8),
        (19.84, "pop", 0.5), (19.86, "slam", 0.6), (23.62, "dun", 0.5), (28.99, "shock", 0.5), (32.52, "shutter", 0.5),
        (36.62, "error", 0.45), (39.18, "vineboom", 0.8), (41.32, "whoosh", 0.35), (42.46, "sadflute-short", 0.55),
        (44.85, "slam", 0.6), (46.47, "whoosh", 0.35), (STORY_END - 0.5, "riser", 0.45), (STORY_END + 4.0, "click", 0.6)]
MERGE = [(("five", "point", "five"), "5.5"), (("GTA", "six"), "GTA 6"), (("five", "star"), "5-star"),
         (("five-year-old",), "5-year-old")]


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
        if len(cur) >= max_words or w[2][-1] in ".,?!" or (nxt and (nxt[0] - w[1] > 0.3 or nxt[3] != w[3])):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def card(text, path, size=64, y=0.70, fill="#f8e800"):
    font = ImageFont.truetype(FONT, size)
    im = Image.new("RGBA", (1080, 1920))
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=font)
    d.text(((1080 - tw) / 2, int(1920 * y)), text, font=font, fill=fill, stroke_width=5, stroke_fill="black")
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
        cards.append((p, ch[0][0], min(t1, ch[-1][1] + 0.45)))
    return cards


def lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])


def level(mp4, target=-13.6):
    gain = target - lufs(mp4)
    tmp = mp4.with_suffix(".lvl.mp4")
    run(["ffmpeg", "-y", "-i", mp4, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp])
    tmp.replace(mp4)


def hook_clip():
    """Official trailer shots, centre-cropped to 9:16, silent, exactly HOOK_END long."""
    hk = OUT / "hook.mp4"
    cmd, parts = ["ffmpeg", "-y"], []
    for f, ss, du, _ in TRAILER:
        cmd += ["-ss", str(ss), "-t", str(du), "-i", CLIPS / f]
    for i, (*_, lb) in enumerate(TRAILER):
        parts.append(f"[{i}:v]crop={lb},fps={FPS},scale=-2:1920,crop=1080:1920,setsar=1,format=yuv420p[h{i}]")
    fc = ";".join(parts) + ";" + "".join(f"[h{i}]" for i in range(len(TRAILER))) + f"concat=n={len(TRAILER)}:v=1:a=0[v]"
    run(cmd + ["-filter_complex", fc, "-map", "[v]", "-t", str(HOOK_END), "-an", "-c:v", "libx264", "-crf", "16", hk])
    return hk


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
    cards = caption_cards(vo["words"], OUT / "captions")
    seq = [p for p in sorted(frames.glob("f_*.png")) if int(p.stem[2:]) >= round(HOOK_END * FPS) + 1][: int((STORY_END - HOOK_END) * FPS)]
    lst = OUT / "frames.txt"
    lst.write_text("".join(f"file '{p}'\nduration {1 / FPS:.6f}\n" for p in seq))
    hk = hook_clip()
    o_mp3, _, o_at = outro.voice(D)
    cmd = ["ffmpeg", "-y", "-i", hk, "-f", "concat", "-safe", "0", "-i", lst, "-i", vo["mp3"], "-i", o_mp3,
           "-stream_loop", "-1", "-i", MUSIC, "-i", outro.CLIP]
    n_sfx = 6
    for _, name, _v in CUES:
        cmd += ["-i", SFX / f"{name}.mp3"]
    n_ov = n_sfx + len(CUES)
    overlays = cards + [(OUT / f"stamp_{n}.png", a, b) for n, a, b in STAMPS]
    for p, *_ in overlays:
        cmd += ["-i", p]
    chain = [f"[0:v]fps={FPS},setsar=1,format=yuv420p[hk]",
             f"[1:v]fps={FPS},scale=1080:1920:flags=neighbor,setsar=1,format=yuv420p[st]",
             f"[5:v]fps={FPS},scale=1080:1920,setsar=1,format=yuv420p[ou]",
             "[hk][st][ou]concat=n=3:v=1:a=0[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(overlays):
        chain.append(f"[{last}][{n_ov + k}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[{last}]fade=t=out:st={END - 0.6}:d=0.6[vout]")
    o_ms, m_ms = int((STORY_END + o_at) * 1000), int(MUSIC_AT * 1000)
    chain.append("[2:a]aresample=48000,volume=1.6[vo1]")
    chain.append(f"[3:a]aresample=48000,volume=1.3,adelay={o_ms}|{o_ms}[vo2]")
    chain.append("[vo1][vo2]amix=inputs=2:normalize=0:duration=longest,apad,asplit=2[vo][key]")
    chain.append(f"[4:a]aresample=48000,volume=0.15,adelay={m_ms}|{m_ms},afade=t=out:st={END - 2.0}:d=2.0[mus]")
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
