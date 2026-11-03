"""Archival subclips -> public/clips/arch/<name>.mp4 (30 fps, 720p, no audio). Sources in sources/ (see RIGHTS.md)."""
import subprocess
from pathlib import Path
d = Path(__file__).parent.parent
CLIPS = {  # name: (source, start s, duration s)
    "bowtie":    ("mac1984lost", 24.0, 5.0),   # 1984 Mac launch: Jobs in bow tie
    "macreveal": ("mac1984lost", 66.0, 4.0),   # Mac on the pedestal
    "insanely":  ("mac1984lost", 122.0, 4.0),  # "insanely great" on the Mac screen
    "ovation":   ("mac1984lost", 266.6, 4.5),  # standing ovation
    "smile84":   ("mac1984lost", 257.5, 4.0),  # Jobs beaming at the applause
    "shine":     ("tv1985", 8.5, 3.0),         # NewsHour 1985 "Losing its shine?"
    "stage85":   ("tv1985", 37.0, 5.0),        # Jobs on stage, purple light
    "close85":   ("tv1985", 129.5, 4.0),       # close-up, yellow tie
    "forehead":  ("tv1985", 151.3, 3.5),       # hand on forehead
    "nextlogo":  ("nextshort", 48.6, 1.8),     # NeXT logo cube
    "rose1":     ("pixar1996", 377.0, 1.5),    # Charlie Rose 1996, Jobs as Pixar CEO
    "rose2":     ("pixar1996", 1058.0, 5.0),
    "tstest":    ("ts-test1992", 8.5, 6.0),    # early Toy Story test footage
}
# Toy Story trailer montage: (start, dur) cut on motion.
MONTAGE = [(19.6, 1.3), (5.8, 1.1), (33.6, 1.1), (63.6, 1.1), (21.6, 1.0), (55.8, 1.0), (70.2, 1.3)]
out = d / "public/clips/arch"; out.mkdir(parents=True, exist_ok=True)
for n, (src, ss, dur) in CLIPS.items():
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", str(dur), "-i", str(d / f"sources/{src}.mp4"),
                    "-vf", "fps=30,scale=-2:720", "-an", "-c:v", "libx264", "-crf", "16", str(out / f"{n}.mp4")], check=True)
parts = "".join(f"[0:v]trim=start={s}:duration={t},setpts=PTS-STARTPTS,fps=30,scale=1280:720[v{i}];" for i, (s, t) in enumerate(MONTAGE))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "sources/ts-trailer.mp4"), "-filter_complex",
                parts + "".join(f"[v{i}]" for i in range(len(MONTAGE))) + f"concat=n={len(MONTAGE)}:v=1:a=0[o]",
                "-map", "[o]", "-c:v", "libx264", "-crf", "16", str(out / "toystory.mp4")], check=True)
print("ok", len(CLIPS) + 1)
