"""Shared Vi3W outro: one pre-rendered silent clip + a FRESH voice-over take per short.

    from reelforge import outro
    mp3, words, at = outro.voice(project_dir)   # new Laura take in <project>/out/vo/, `at` = VO start in the clip
    # video: append outro.CLIP after the story; audio: drop mp3 at story_end + at

The clip (projects/shorts/vi3w-outro/outro.mp4, 6 s) is rendered once by projects/shorts/vi3w-outro/outro.py.
Its 3D title carries the words, so shorts don't caption the outro. The VO is placed so the spoken "Vi3W.in" lands
on the URL pop (outro.json url_at).
"""
import json
from pathlib import Path

from reelforge.shorts import DEFAULTS, tts

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "projects" / "shorts" / "vi3w-outro"
CLIP = DIR / "outro.mp4"
META = json.loads((DIR / "outro.json").read_text())
LINE = "[excited] And this whole video? Made with the Vi3W workflow. Vi3W.in"


def voice(project: Path, line: str = LINE):
    """Record the outro line in this project's own VO cache (so every short gets its own natural take)."""
    pub = Path(project) / "out"
    mp3, words, dur = tts(Path(project), pub, DEFAULTS["voice"], line, DEFAULTS["say"])
    url = next((a for a, b, w in reversed(words) if "Vi3W.in" in w), words[-1][0])
    at = max(0.05, META["url_at"] - url)
    if at + dur > META["dur"]:
        at = max(0.0, META["dur"] - dur)
    return pub / mp3, words, at
