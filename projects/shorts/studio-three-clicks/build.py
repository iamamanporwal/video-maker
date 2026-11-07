"""Render the Blender previsual with its word-timed VO.

Use --preview first (540×960, 15 fps source frames doubled to 30 fps), inspect
out/contact.jpg, then run without it for the 1080×1920 master.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from reelforge.blender.render import BLENDER, render  # noqa: E402

FPS = 30
OUT = D / "out"
NAME = "studio-three-clicks"


def run(command):
    subprocess.run([str(x) for x in command], check=True)


def main(preview=False):
    words = json.loads((OUT / "words.json").read_text())
    frames = OUT / ("preview" if preview else "frames")
    if frames.exists():
        shutil.rmtree(frames)
    run([BLENDER, "-b", "-P", D / "scene.py", "--", OUT / "scene.blend"])
    last = round((words["dur"] + 0.6) * FPS) + 1
    step, scale = (2, 50) if preview else (1, 100)
    render(str(OUT / "scene.blend"), str(frames), workers=3, frames=(1, last), step=step, scale=scale, quiet=False)
    source_fps = FPS / step
    frame_list = OUT / "frames.txt"
    duration = 1 / source_fps
    rendered = sorted(frames.glob("f_*.jpg"))
    frame_list.write_text("".join(f"file '{frame.resolve()}'\nduration {duration:.8f}\n" for frame in rendered))
    target = OUT / f"{NAME}{'-preview' if preview else ''}.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", frame_list, "-i", Path(words["mp3"]),
        "-vf", "fps=30,scale=1080:1920:flags=lanczos,format=yuv420p", "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "19", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", target,
    ])
    print(target)


if __name__ == "__main__":
    main(preview="--preview" in sys.argv)
