"""python sfx.py: comedy SFX via ElevenLabs sound-generation (direct API, cached) → sfx/<name>.mp3."""
import os, sys
from pathlib import Path
import httpx

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))

SFX = {
    "squish": ("cartoon foot squish step on a fluffy tail, short comedic squeak, no music", 0.6),
    "yelp": ("big dog painful yelp, single loud high-pitched yip, close mic, no music", 1.0),
    "growl": ("huge scary dog deep low menacing growl, rumbling, close, no music", 3.0),
    "grow": ("cartoon growing stretch sound, rising pitch, comedic, no music", 1.2),
    "gulp": ("cartoon big gulp swallow, comedic, one gulp, no music", 0.8),
    "bark": ("big angry dog barking aggressively, three fast loud barks, no music", 1.6),
    "scramble": ("cartoon feet scramble running away fast, comedic zip, no music", 1.0),
    "dun": ("dramatic suspense sting dun dun dunnn, orchestral, short", 2.0),
    "kaching": ("cash register ka-ching, bright, short", 1.0),
    "riser": ("short whoosh riser into reveal, airy, no music", 1.2),
}

if __name__ == "__main__":
    out = D / "sfx"
    out.mkdir(exist_ok=True)
    for name, (prompt, dur) in SFX.items():
        p = out / f"{name}.mp3"
        if p.exists():
            continue
        r = httpx.post("https://api.elevenlabs.io/v1/sound-generation", timeout=120,
                       headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                       json={"text": prompt, "duration_seconds": max(0.5, dur), "prompt_influence": 0.6})
        if r.status_code >= 400:
            print(name, r.status_code, r.text[:200])
            continue
        p.write_bytes(r.content)
        print(name, len(r.content))
