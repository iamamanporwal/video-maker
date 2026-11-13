"""python rerender.py t1,t2,...: re-render only the shots that contain these timeline seconds (frames overwrite in out/frames)."""
import json, sys
from pathlib import Path
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parents[2] / "src"))
from reelforge.blender.render import render_shots
shots = json.loads((D / "out/shots.json").read_text())
ts = [float(x) for x in sys.argv[1].split(",")]
jobs = [s for s in shots if any(s[1] <= round(t * 30) + 1 <= s[2] for t in ts)]
print(len(jobs), "shots,", sum(b - a + 1 for _, a, b in jobs), "frames")
print(f"{render_shots(str(D / 'out/scene.blend'), str(D / 'out/frames'), jobs, workers=3):.0f}s")
