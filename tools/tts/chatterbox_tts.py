"""Local Chatterbox Multilingual TTS (Apple Silicon / MPS), with voice cloning from a reference clip.

Usage:
  .venv/bin/python chatterbox_tts.py --text-file story.txt --out out/story.wav \
      [--lang hi] [--ref ref/laura.wav] [--exaggeration 0.6] [--cfg 0.4] [--temp 0.8] [--pause 0.22] [--seed 7]

The text is split into one line or sentence per generation (Chatterbox drifts on long inputs),
then the pieces are joined with short pauses and the result is loudness-normalised to -16 LUFS.
"""
import argparse, re, subprocess, time
from pathlib import Path

import torch
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS


def split_text(text: str) -> list[str]:
    parts = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # split after sentence enders (Hindi danda, ! ?), keep the punctuation
        parts += [p.strip() for p in re.split(r"(?<=[।!?])\s+", line) if p.strip()]
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="hi")
    ap.add_argument("--ref", default=None, help="reference voice clip (~10 s, clean)")
    ap.add_argument("--exaggeration", type=float, default=0.6)
    ap.add_argument("--cfg", type=float, default=0.4)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--pause", type=float, default=0.22)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    print(f"model loaded on {device} in {time.time() - t0:.1f}s")

    pieces = split_text(Path(a.text_file).read_text(encoding="utf-8"))
    gap = torch.zeros(1, int(model.sr * a.pause))
    chunks = []
    t1 = time.time()
    for i, s in enumerate(pieces):
        torch.manual_seed(a.seed + i)
        wav = model.generate(s, language_id=a.lang, audio_prompt_path=a.ref,
                             exaggeration=a.exaggeration, cfg_weight=a.cfg, temperature=a.temp)
        print(f"  [{i + 1}/{len(pieces)}] {wav.shape[-1] / model.sr:.2f}s  {s}")
        chunks += [wav.cpu(), gap]
    audio = torch.cat(chunks[:-1], dim=-1)
    gen = time.time() - t1

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_suffix(".raw.wav")
    ta.save(str(raw), audio, model.sr)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", "48000", str(out)], check=True)
    raw.unlink()
    dur = audio.shape[-1] / model.sr
    print(f"done: {out}  {dur:.1f}s audio in {gen:.1f}s ({dur / gen:.2f}x realtime)")


if __name__ == "__main__":
    main()
