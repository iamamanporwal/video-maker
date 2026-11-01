"""vo.json + pacing -> out/props.json for the IMissSteve composition. Pure data; re-run after any VO/pacing change."""
import json
from pathlib import Path

d = Path(__file__).parent
FPS = 30
LEAD = 1.3                       # VHS insert + picture roll before the first word
# Breath after each line (s). Long ones are deliberate: after "finished", before/after the payoff, after the quote.
GAPS = [0.8, 0.9, 0.5, 0.45, 0.5, 1.0, 1.5, 0.35, 1.6, 0.4, 1.1, 1.4, 1.0, 0.7]
TAIL = 4.2                       # end card hold after the last line
MUSIC_HIT = 43.8                 # measured swell in the track (ebur128 momentary jumps -15 -> -8.6 LU at 43.6-44.0 s)

vo = json.loads((d / "vo.json").read_text())
t, lines = LEAD, []
for i, l in enumerate(vo):
    lines.append({"src": l["src"], "start": round(t, 3), "dur": l["dur"], "text": l["text"],
                  "words": [[round(t + a, 3), round(t + b, 3), w] for a, b, w in l["words"]]})
    t += l["dur"] + (GAPS[i] if i < len(GAPS) else 0)
total = t + TAIL
toy = next(w for w in lines[6]["words"] if w[2].startswith("Toy"))[0]
props = {"fps": FPS, "durationInFrames": round(total * FPS), "lines": lines,
         "music": {"src": "music/cinematic-documentary.mp3", "trackStart": round(MUSIC_HIT - toy, 3)}}
(d / "out").mkdir(exist_ok=True)
(d / "out/props.json").write_text(json.dumps(props, indent=1))
for i, l in enumerate(lines):
    print(f"L{i+1:<2} {l['start']:6.2f}-{l['start']+l['dur']:6.2f}  {l['text'][:60]}")
print(f"total {total:.2f}s  toy-story word at {toy:.2f}s  music starts at track {props['music']['trackStart']:.2f}s")
