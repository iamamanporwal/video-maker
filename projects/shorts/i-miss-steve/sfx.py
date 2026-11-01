"""Period foley via fal ElevenLabs sound effects -> public/sfx/<name>.mp3 (cached)."""
import json, os, httpx
from pathlib import Path
d = Path(__file__).parent
SFX = {
    "vhs": ("VHS cassette inserted into a VCR, mechanical clunk and motor whirr, then a soft tape hiss", 2.5),
    "projector": ("old 16mm film projector running, steady mechanical clatter, warm and soft", 6.0),
    "typewriter": ("three quick vintage typewriter key strikes and a carriage ding, close and crisp", 1.6),
    "shutter": ("vintage film camera shutter click with film advance, single", 0.8),
    "burn": ("soft cinematic whoosh with a film reel flutter, transition, airy", 1.4),
    "riser": ("gentle warm cinematic swell, soft shimmering reverse cymbal rising into a bright bloom", 3.0),
}
key = os.environ["FAL_KEY"]
(d / "public/sfx").mkdir(parents=True, exist_ok=True)
for name, (text, secs) in SFX.items():
    f = d / "public/sfx" / f"{name}.mp3"
    if f.exists():
        continue
    r = httpx.post("https://fal.run/fal-ai/elevenlabs/sound-effects/v2", timeout=180, headers={"Authorization": f"Key {key}"},
                   json={"text": text, "duration_seconds": secs, "prompt_influence": 0.5})
    r.raise_for_status()
    f.write_bytes(httpx.get(r.json()["audio"]["url"], timeout=120).content)
    with open(d / "costs.jsonl", "a") as c:
        c.write(json.dumps({"provider": "fal", "what": "sfx", "name": name, "secs": secs}) + "\n")
    print("ok", name)
