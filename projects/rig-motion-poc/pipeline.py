#!/usr/bin/env python3
"""Local rig -> text-to-motion -> retarget -> animated GLB pipeline (Apple Silicon friendly).

    uv run --no-project --with numpy pipeline.py \
        --input samples/khronos/CesiumMan.glb --strip \
        --prompt "Make this character walk forward, jump and perform a backflip" \
        --out out/cesium --preview

Stages (each writes a file, so any stage can be swapped or re-run on its own):
  1. rig      IN.{glb,fbx,obj} -> out/rigged.glb
                --rigger heuristic   geometry + Blender heat weights (no weights, default)
                --rigger skintokens  SkinTokens via skintokens-cli (Metal), see README
                --rigger none        input is already rigged
  2. motion   prompt -> out/motion.npz  (SOMA-77, Kimodo format)
                --motion kimodo      NVIDIA Kimodo, arbitrary text (needs install + weights)
                --motion clips       offline stand-in: pre-generated Kimodo clips
  3. retarget rigged.glb + motion.npz -> out/animated.glb (+ preview.mp4)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rigmotion.motion import ClipLibraryBackend, KimodoBackend, plan  # noqa: E402
from rigmotion.soma import save_motion  # noqa: E402

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")


def blender(script: str, *args: str) -> None:
    cmd = [BLENDER, "-b", "--factory-startup", "-P", str(HERE / "blender" / script), "--", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("[") or "Error" in line or "Traceback" in line:
            print("   ", line)
    if r.returncode != 0 or "Traceback" in r.stdout + r.stderr:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"blender {script} failed")


def rig(args, out: Path) -> Path:
    dst = out / "rigged.glb"
    if args.rigger == "none":
        return Path(args.input)
    if args.rigger == "heuristic":
        extra = ["--strip"] if args.strip else []
        if args.preview:
            extra += ["--preview", str(out / "rig_preview.png")]
        blender("autorig.py", str(args.input), str(dst), *extra)
        return dst
    if args.rigger == "skintokens":
        cli = shutil.which("skintokens-cli") or args.skintokens_cli
        if not cli or not Path(cli).exists():
            raise SystemExit("skintokens-cli not found: build skin-tokens.cpp (README step 2) "
                             "and pass --skintokens-cli PATH")
        src = Path(args.input)
        if args.strip or src.suffix.lower() != ".glb":  # SkinTokens wants a static .glb mesh
            static = out / "static.glb"
            blender("to_static_glb.py", str(src), str(static))
            src = static
        subprocess.run([cli, "rig", args.skintokens_model, str(src), str(dst),
                        "--device", args.device], check=True)
        return dst
    raise SystemExit(args.rigger)


def motion(args, out: Path) -> Path:
    segs = plan(args.prompt)
    if args.seconds:
        for s, sec in zip(segs, args.seconds):
            s.seconds = sec
    print("   plan:", [(s.prompt, s.seconds) for s in segs])
    if args.motion == "kimodo":
        m = KimodoBackend(model=args.kimodo_model, seed=args.seed,
                          text_encoder_device=args.text_encoder_device).generate(segs, out / "kimodo")
    else:
        m = ClipLibraryBackend(HERE / "samples" / "kimodo_clips").generate(segs)
    dst = out / "motion.npz"
    save_motion(dst, m)
    (out / "plan.json").write_text(json.dumps([s.__dict__ for s in segs], indent=1))
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", default="out/run")
    ap.add_argument("--rigger", choices=["heuristic", "skintokens", "none"], default="heuristic")
    ap.add_argument("--strip", action="store_true", help="discard an existing rig and re-rig")
    ap.add_argument("--motion", choices=["clips", "kimodo"], default="clips")
    ap.add_argument("--seconds", type=float, nargs="*", help="override per-segment durations")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--kimodo-model", default="Kimodo-SOMA-RP-v1.2")
    ap.add_argument("--text-encoder-device", default=None, help="e.g. cpu (Kimodo TEXT_ENCODER_DEVICE)")
    ap.add_argument("--skintokens-cli", default=str(HERE / "vendor/skin-tokens.cpp/build/release/bin/skintokens-cli"))
    ap.add_argument("--skintokens-model", default=str(HERE / "vendor/skin-tokens.cpp/models/SkinTokens-GGUF/F16"))
    ap.add_argument("--device", default="auto", help="skintokens-cli device: auto (Metal) | cpu")
    ap.add_argument("--preview", action="store_true", help="render rig + animation previews")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("1/3 rig ...")
    rigged = rig(args, out)
    t1 = time.time()
    print(f"    -> {rigged}  ({t1 - t0:.1f}s)\n2/3 motion ...")
    mot = motion(args, out)
    t2 = time.time()
    print(f"    -> {mot}  ({t2 - t1:.1f}s)\n3/3 retarget + export ...")
    anim = out / "animated.glb"
    extra = ["--preview", str(out / "frames")] if args.preview else []
    blender("retarget.py", str(rigged), str(mot), str(anim), *extra)
    t3 = time.time()
    print(f"    -> {anim}  ({t3 - t2:.1f}s)")
    if args.preview and shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "30", "-i",
                        str(out / "frames" / "f_%04d.png"), "-pix_fmt", "yuv420p", "-c:v", "libx264",
                        str(out / "preview.mp4")], check=True)
        print(f"    -> {out / 'preview.mp4'}")
    print(f"done in {t3 - t0:.1f}s")


if __name__ == "__main__":
    main()
