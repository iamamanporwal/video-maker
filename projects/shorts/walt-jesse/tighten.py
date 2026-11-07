"""python tighten.py: shorten the VO's long pauses (Will at low stability breathes a lot) → out/vo_tight.wav, and remap
out/words.json (originals kept in out/words_raw.json). Dramatic beats keep a longer pause (KEEP: word that follows)."""
import json, re, subprocess
from pathlib import Path

D = Path(__file__).resolve().parent
OUT = D / "out"
raw = OUT / "words_raw.json"
if not raw.exists():
    raw.write_text((OUT / "words.json").read_text())
V = json.loads(raw.read_text())
MAX, KEEP = 0.22, {"clean.": 0.55, "Because": 0.6, "Science,": 0.45, "Albuquerque,": 0.4}
log = subprocess.run(["ffmpeg", "-hide_banner", "-i", V["mp3"], "-af", "silencedetect=n=-38dB:d=0.25", "-f", "null", "-"],
                     capture_output=True, text=True, timeout=120).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
words = V["words"]
cuts = []                                                # (from, to) spans of audio to remove
for a, b in zip(starts, ends):
    nxt = next((w for w in words if w[0] >= b - 0.15), None)
    keep = KEEP.get(nxt[2], MAX) if nxt else MAX
    if b - a > keep:
        mid = (a + b) / 2
        cuts.append((mid - (b - a - keep) / 2, mid + (b - a - keep) / 2))


def remap(t):
    return t - sum(min(t, b) - a for a, b in cuts if t > a)


keep_spans, prev = [], 0.0
for a, b in cuts:
    keep_spans.append((prev, a))
    prev = b
keep_spans.append((prev, V["dur"]))
sel = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in keep_spans)
dst = OUT / "vo_tight.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", V["mp3"], "-af", f"aselect='{sel}',asetpts=N/SR/TB", "-ar", "48000",
                str(dst)], check=True, timeout=120)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)],
                           capture_output=True, text=True).stdout)
nw = [[round(remap(a), 3), round(remap(b), 3), w] for a, b, w in words]
beats = [round(remap(b), 3) for b in V["beats"]]
(OUT / "words.json").write_text(json.dumps({"mp3": str(dst), "dur": dur, "words": nw, "beats": beats}))
print(f"{V['dur']:.1f}s → {dur:.1f}s, {len(cuts)} pauses shortened; beats", beats)
