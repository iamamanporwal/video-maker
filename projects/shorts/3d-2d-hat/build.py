"""python build.py [--preview]: scene.py → parallel EEVEE render → captions + VO → out/3d-2d-hat.mp4.

--preview renders at 50 % and every 2nd frame (about 4x faster) for timing/blocking checks.
VO is the reference Short's own narration (Zack D. Films) as a TEMP track: the result goes to
FinalUploads/Drafts and is not for posting without their permission.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from reelforge.blender.render import BLENDER, render  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

OUT, FPS, SECS = D / "out", 30, 10.0
REF = D / "ref" / "zack_2d_hat.mp4"
AUDIO_END = 9.62                       # last word "2D" ends ~9.6 s; next word starts 9.72
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
SENTENCE_STARTS = {0, 4, 8}
PHRASES = [["You", "reach"], ["into", "the", "2d", "world"], ["and", "take", "off"], ["the", "girl's", "hat"],
           ["then", "you"], ["flip", "it", "around"], ["and", "put", "it", "on"], ["backward"],
           ["now", "if", "the", "girl"], ["has", "only", "ever"], ["existed", "in", "2d"]]


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def caption_cards(words, out_dir, w=1080, h=1920, y=0.70):
    """One transparent PNG per phrase, Zack-style: white rounded bold, soft dark shadow. → [(png, t0, t1)]"""
    out_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(FONT, 66)
    i, cards = 0, []
    for k, ph in enumerate(PHRASES):
        seg = words[i:i + len(ph)]
        assert [s[0].lower().strip(".,") for s in seg] == [p.lower() for p in ph], (seg, ph)
        i += len(ph)
        text = " ".join(s[0].strip(".,") for s in seg).replace("2d", "2D")
        if k in SENTENCE_STARTS:
            text = text[0].upper() + text[1:]
        im = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(im)
        tw = d.textlength(text, font=font)
        x, yy = (w - tw) / 2, int(h * y)
        sh = Image.new("RGBA", (w, h))
        ImageDraw.Draw(sh).text((x + 2, yy + 6), text, font=font, fill=(0, 0, 0, 200), stroke_width=8,
                                stroke_fill=(0, 0, 0, 200))
        im = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)), im)
        ImageDraw.Draw(im).text((x, yy), text, font=font, fill="white", stroke_width=4, stroke_fill=(20, 22, 28, 235))
        p = out_dir / f"cap_{k:02d}.png"
        im.save(p)
        cards.append((p, seg[0][1], None))
    # each card holds until the next phrase starts (last one until the audio ends)
    return [(p, t0, cards[j + 1][1] if j + 1 < len(cards) else AUDIO_END + 0.25) for j, (p, t0, _) in enumerate(cards)]


def main(preview=False):
    t_all = time.time()
    stamps = {}
    t = time.time()
    run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
    stamps["scene"] = time.time() - t

    frames = OUT / ("preview" if preview else "frames")
    shutil.rmtree(frames, ignore_errors=True)
    stamps["render"] = render(str(OUT / "scene.blend"), str(frames), workers=3, frames=(1, int(SECS * FPS)),
                              step=2 if preview else 1, scale=50 if preview else 100)

    t = time.time()
    words = json.loads((D / "ref" / "words.json").read_text())
    cards = caption_cards(words, OUT / "captions")
    fps_in = FPS / 2 if preview else FPS
    seq = sorted(frames.glob("f_*.jpg"))
    lst = OUT / "frames.txt"                        # concat list: works for every-frame and every-2nd-frame runs
    lst.write_text("".join(f"file '{p}'\nduration {1 / fps_in:.6f}\n" for p in seq))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
           "-ss", "0", "-t", f"{AUDIO_END}", "-i", REF]
    for p, *_ in cards:
        cmd += ["-i", p]
    W = 540 if preview else 1080
    chain, last = [f"[0:v]fps={FPS},scale={W}:-2,format=yuv420p[v0]"], "v0"
    for k, (p, a, b) in enumerate(cards):
        chain.append(f"[{k + 2}:v]scale={W}:-2[c{k}]")
        chain.append(f"[{last}][c{k}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k + 1}]")
        last = f"v{k + 1}"
    chain.append(f"[1:a]afade=t=out:st={AUDIO_END - 0.12}:d=0.12,apad=whole_dur={SECS},"
                 f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    name = "3d-2d-hat" + ("-preview" if preview else "")
    mp4 = OUT / f"{name}.mp4"
    cmd += ["-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "[a]", "-t", f"{SECS}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", mp4]
    run(cmd)
    stamps["captions+encode"] = time.time() - t
    total = time.time() - t_all
    print(" | ".join(f"{k} {v:.1f}s" for k, v in stamps.items()), f"| TOTAL {total:.1f}s →", mp4)
    if not preview:
        dst = ROOT / "FinalUploads" / "Drafts"
        shutil.copy(mp4, dst / f"{name}.mp4")
        (dst / f"{name}.txt").write_text(
            "PILOT / NOT FOR POSTING: narration is Zack D. Films' audio (temp track, no permission).\n"
            "Replace with our own ElevenLabs VO before publishing.\n\n"
            "You can't turn your own hat around... if you only exist in 2D 🧢\n\n"
            "#3d #blender #animation #vi3w\n")


if __name__ == "__main__":
    main(preview="--preview" in sys.argv)
