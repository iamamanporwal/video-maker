"""~/models/chatterbox-venv/bin/python vo.py [takes]: Chatterbox best-of-N narration → out/vo/story.wav + out/words.json
({"mp3", "dur", "words": [[s, e, token]], "lines": {key: [i0, i1]}}). Reuses the scoring/alignment helpers of
gta6-billion/vo_cb.py (whisper WER pick + token alignment). ElevenLabs is out until 2026-12-03; Kokoro is banned.

Facts (checked 2026-11-10 against github.com/arjun988/blender-skills @904f095): 94 skills in .claude/skills, MIT
licence, works with Cursor / Claude Code / Kiro / Codex, blender-director routes requests through specialist skills,
executes in Blender via the BlenderMCP addon, 2,409 stars, install = git clone + copy .claude/skills.
"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np, torch, torchaudio as ta

D = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cb", D.parent / "gta6-billion/vo_cb.py")
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)
from chatterbox.tts import ChatterboxTTS  # noqa: E402

OUT = D / "out"
cb.EXAG, cb.TEMP = 0.72, 0.8
TAKES = int(sys.argv[1]) if len(sys.argv) > 1 else 3
LINES = [
    ("h1", "I asked AI to build a scary hallway in Blender."),
    ("h2", "It gave me a grey tube and a cube. That's not horror, that's a fucking IKEA warehouse."),
    ("h3", "So I installed one GitHub repo, and asked again."),
    ("h4", "Okay. Who the fuck put a guy at the end?"),
    ("b1", "It's called Blender Skills. Ninety-four files that turn Claude or Cursor from a clueless intern into a senior tech artist who's seen some shit."),
    ("b2", "One skill per job. Hard surface. Topology. UVs, which nobody understands. Materials. Lighting."),
    ("b3", "Then a director skill reads your prompt and bosses the others around. Like a real studio, minus the crunch and the crying."),
    ("b4", "Style skills change the vibe. Low poly. Anime. Voxel. And horror, for when your mushroom has trauma."),
    ("b5", "And with Blender MCP, it doesn't tell you where to click like some tutorial asshole with a dying mic. It just builds it, inside Blender."),
    ("p1", "So I gave it three jobs."),
    ("p2", "A haunted hallway. A sci-fi crate. And a tiny island where I can hide from my responsibilities."),
    ("p3", "It's open source, over two thousand stars. Clone it, copy one folder, and stop jerking off to donut tutorials."),
    ("p4", "What should I make it build next? Keep it legal, you animals."),
]
GAP = {"h1": 0.2, "h2": 0.35, "h3": 0.25, "h4": 0.35, "b1": 0.25, "b2": 0.25, "b3": 0.25, "b4": 0.3, "b5": 0.3, "p1": 0.2, "p2": 0.3, "p3": 0.3}
cb.NUM.update({"ninetyfour": "ninety four", "94": "ninety four", "uvs": "uvs", "mcp": "m c p", "2000": "two thousand",
               "scifi": "sci fi", "ai": "a i", "github": "github", "ikea": "ikea"})

if __name__ == "__main__":
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    m = ChatterboxTTS.from_local(cb.WEIGHTS, device=dev)
    sr = m.sr
    tdir = OUT / "vo" / "takes"
    tdir.mkdir(parents=True, exist_ok=True)
    audio, words, spans, off, report = [], [], {}, 0.0, []
    for key, text in LINES:
        said = text.replace("UVs", "U-Vs").replace("MCP", "M-C-P").replace("AI ", "A.I. ").replace("IKEA", "Ikea")
        tokens = text.split()
        want = [p for t in tokens for p in cb.norm(t).replace("-", " ").split()]
        best = None
        for k in range(TAKES):
            torch.manual_seed(1000 * k + sum(map(ord, key)))
            w = m.generate(said, exaggeration=cb.EXAG, cfg_weight=cb.CFG, temperature=cb.TEMP)
            p = tdir / f"{key}_{k}.wav"
            ta.save(str(p), w, sr)
            hw = cb.split_words(cb.transcribe(p))
            score = cb.wer(want, [h[0] for h in hw])
            print(f"{key} take {k}: wer={score:.2f} {' '.join(h[0] for h in hw)}", flush=True)
            cand = (score, -cb.pitch_var(w, sr), k, w, hw)
            if best is None or cand[:2] < best[:2]:
                best = cand
            if score == 0 and k >= 1:
                break
        score, _, k, w, hw = best
        x = w.squeeze().numpy()
        s0 = max(0.0, (hw[0][1] if hw else 0) - 0.06)
        s1 = min(len(x) / sr, (hw[-1][2] if hw else len(x) / sr) + 0.15)
        x = x[int(s0 * sr):int(s1 * sr)]
        hw = [(h[0], h[1] - s0, h[2] - s0) for h in hw]
        i0 = len(words)
        for tok, (a, b) in zip(tokens, cb.align(tokens, hw, len(x) / sr)):
            words.append([round(off + a, 3), round(off + b, 3), tok])
        spans[key] = [i0, len(words)]
        g = GAP.get(key, 0.2)
        audio += [x, np.zeros(int(sr * g), dtype=x.dtype)]
        off += len(x) / sr + g
        report.append((key, k, round(score, 2)))
    wav = OUT / "vo" / "story.wav"
    ta.save(str(wav), torch.from_numpy(np.concatenate(audio)).unsqueeze(0), sr)
    (OUT / "words.json").write_text(json.dumps({"mp3": str(wav), "dur": off, "sr": sr, "words": words, "lines": spans}))
    print("picked:", report)
    print(f"{off:.1f}s {len(words)} words")
    for key, (a, b) in spans.items():
        print(key, words[a][0], words[b - 1][1], " ".join(w[2] for w in words[a:b]))
