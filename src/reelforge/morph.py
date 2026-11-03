"""Screenshot → 3D transition clip: the viral clip plays, freezes into a "screenshot", a scan line turns the subject
into a wireframe and then the real 3D render in place, the photo falls away and the model spins centre stage.

    python -m reelforge.morph projects/shorts/concrete-cat/morph.yaml

morph.yaml:
    video: assets/source.mp4        # the borrowed clip (rights are the reel's job)
    start: 4.0                      # clip plays start → freeze
    freeze: 7.0                     # the screenshot frame (same frame as the Vi3W input)
    subject: [211, 231, 527, 821]   # subject box in source pixels at `freeze` (x0, y0, x1, y1), tail to paws
    renders: render/morph           # blender/morph.py output: aligned.png, wire.png, spin/s_####.png
    out: assets/morph.mp4           # 1080x1920 clip with the source audio + pop/whoosh baked in
    cta_out: assets/cta-spin.mp4    # 1410x840 spin for the CTA card, continuing the same rotation
    cta_full_out: assets/cta-full.mp4   # or a 1080x1920 continuation for a CTA `backdrop` (cta_seconds long)
    center_y: 930                   # centre-stage model height on screen
    spin_tail: 156                  # frames of centre-stage spin after the lift
    spin_zoom: 1.0                  # >1 enlarges the centre-stage model; thin parts may brush the edge
    gain: 0.55                      # source audio level under the freeze
    fx_gain: 1.0                    # scales the baked shutter pop + lift whoosh
    gamma: 1.0                      # >1 lifts the midtones of dark renders (aligned, spin); alpha untouched
    spin_turn: 2.2                  # optional: one eased full turn (s), then sway front-on (cta_sway) for the VO
    front: 0                        # spin index that faces the viewer (renders start at the aligned yaw)
    companion:                      # optional second model: the main one lands in the left slot, this one slides
      renders: ../other/render/morph    # in on the right during the spin (only spin/ is used)
      enter: 0.4                    # seconds into the centre-stage spin when it starts sliding in
      height: 800                   # both models scaled to this height (× spin_zoom / zoom), feet on one floor
      main_x: 0.3                   # slot centres as a share of the width
      x: 0.75
      gamma: 1.0
      zoom: 1.0

Python does every frame (PIL); nothing here is generated. Deterministic: same inputs, same clip.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
W, H, FPS = 1080, 1920, 30
INK = (7, 8, 12)
CARD = (13, 15, 20)
ACCENT = (124, 255, 107)
FREEZE_F, SCAN_F, LIFT_F = 15, 36, 24
THUMB = 0.86                       # screenshot thumbnail scale
WIRE_BAND = 170                    # px of wireframe trailing the scan line before the shaded model


def ease(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{cmd[0]} failed:\n{r.stderr[-1500:]}")


def paste(base: Image.Image, im: Image.Image, k: float, off: tuple[float, float]) -> None:
    """Scale RGBA `im` by k and composite it onto RGB `base` with its top-left at off (may be off-canvas)."""
    s = max(1, round(im.width * k))
    r = im.resize((s, s), Image.LANCZOS)
    base.paste(r, (round(off[0]), round(off[1])), r)


def brighten(im: Image.Image, gamma: float) -> Image.Image:
    """Brighten an RGBA render's midtones (gamma > 1); blacks stay black, alpha untouched."""
    if gamma == 1.0:
        return im
    lut = [round(255 * (v / 255) ** (1 / gamma)) for v in range(256)]
    r, g, b, a = im.split()
    return Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))


def framed(photo: Image.Image, fs: float, bg: Image.Image, dy: float = 0, alpha: float = 1.0) -> Image.Image:
    """`photo` shrunk to fs about the centre with a white rounded border, like a phone screenshot thumbnail."""
    out = bg.copy()
    w, h = round(W * fs), round(H * fs)
    b, rad = 14, 44
    card = Image.new("RGB", (w + 2 * b, h + 2 * b), (255, 255, 255))
    card.paste(photo.resize((w, h), Image.LANCZOS), (b, b))
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, card.width - 1, card.height - 1), rad, fill=round(255 * alpha))
    out.paste(card, ((W - card.width) // 2, round((H - card.height) / 2 + dy)), mask)
    return out


def main(spec_path: str) -> int:
    spec_path = Path(spec_path)
    d = spec_path.parent
    spec = yaml.safe_load(spec_path.read_text())
    video, rd = d / spec["video"], d / spec["renders"]
    start, freeze = float(spec["start"]), float(spec["freeze"])
    spin_tail, gain = int(spec.get("spin_tail", 156)), float(spec.get("gain", 0.55))
    fxg = float(spec.get("fx_gain", 1.0))
    spins = sorted((rd / "spin").glob("s_*.png"))
    if not spins:
        raise SystemExit(f"no spin frames in {rd / 'spin'}")

    tmp = Path(tempfile.mkdtemp(prefix="morph-"))
    try:
        # Source frames start → freeze at 30 fps, and the exact freeze frame (frame-accurate seek).
        run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(freeze - start), "-i", str(video),
             "-vf", f"fps={FPS},scale={W}:{H}:flags=lanczos", str(tmp / "a_%04d.png")])
        run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-ss", str(freeze), "-frames:v", "1",
             "-vf", f"scale={W}:{H}:flags=lanczos", str(tmp / "freeze.png")])
        play = sorted(tmp.glob("a_*.png"))
        src_w = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width",
                                    "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip())
        sc = W / src_w

        F = Image.open(tmp / "freeze.png").convert("RGB")
        Fblur = ImageEnhance.Brightness(F.filter(ImageFilter.GaussianBlur(22))).enhance(0.42)
        gamma = float(spec.get("gamma", 1.0))
        aligned = brighten(Image.open(rd / "aligned.png").convert("RGBA"), gamma)
        wire = Image.open(rd / "wire.png").convert("RGBA")
        bb = aligned.getbbox()

        # Aligned placement in photo space: model bottom on the subject's bottom, same height, same centre x.
        x0, y0, x1, y1 = [v * sc for v in spec["subject"]]
        ka = (y1 - y0) / (bb[3] - bb[1])
        oa = ((x0 + x1) / 2 - ka * (bb[0] + bb[2]) / 2, y1 - ka * bb[3])
        def layer(im: Image.Image) -> Image.Image:
            L = Image.new("RGBA", (W, H))
            r = im.resize((round(im.width * ka),) * 2, Image.LANCZOS)
            L.paste(r, (round(oa[0]), round(oa[1])), r)
            return L

        AL, WL = layer(aligned), layer(wire)

        # Centre stage: size to the union of the model's bbox over the whole spin, so it is as big as it can be
        # at every angle without leaving the frame; model centre a little above the middle.
        boxes = [Image.open(p).getchannel("A").getbbox() for p in spins]
        U = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        ucx, ucy, uw, uh = (U[0] + U[2]) / 2, (U[1] + U[3]) / 2, U[2] - U[0], U[3] - U[1]
        # spin_zoom > 1 trades a thin extremity (a tail tip) briefly crossing the edge for a bigger body.
        comp = spec.get("companion")
        kc = min(W * 0.94 / uw, 1050 / uh) * float(spec.get("spin_zoom", 1.0))
        oc = (W / 2 - kc * ucx, float(spec.get("center_y", 930)) - kc * ucy)
        if comp:
            # Duo: both models the same height (comp.height px, before zooms), feet on one floor line, side by side.
            # Widths aren't capped: a wide extremity (a splash ring) may briefly cross the neighbour or the edge.
            cspins = sorted((d / comp["renders"] / "spin").glob("s_*.png"))
            if not cspins:
                raise SystemExit(f"no companion spin frames in {d / comp['renders'] / 'spin'}")
            cgamma = float(comp.get("gamma", 1.0))
            cb = [Image.open(p).getchannel("A").getbbox() for p in cspins]
            CU = (min(b[0] for b in cb), min(b[1] for b in cb), max(b[2] for b in cb), max(b[3] for b in cb))
            hh = float(comp.get("height", 800))
            floor = float(spec.get("center_y", 930)) + hh / 2
            kc = hh / uh * float(spec.get("spin_zoom", 1.0))
            oc = (float(comp.get("main_x", 0.3)) * W - kc * ucx, floor - kc * U[3])
            kcc = hh / (CU[3] - CU[1]) * float(comp.get("zoom", 1.0))
            occ = (float(comp.get("x", 0.75)) * W - kcc * (CU[0] + CU[2]) / 2, floor - kcc * CU[3])
            enter_f, slide_f = round(float(comp.get("enter", 0.4)) * FPS), 14

        def companion(im: Image.Image, idx: int, i: int) -> None:
            """Slide the companion in from the right edge from spin frame `enter_f`, turning in step with the main."""
            if not comp or i < enter_f:
                return
            t = ease((i - enter_f) / slide_f)
            dx = (1 - t) * (W * 0.75)
            cg = glow_c.copy(); cg.putalpha(cg.getchannel("A").point(lambda a: round(a * t)))
            im.paste(cg, (round(dx), 0), cg)
            paste(im, brighten(Image.open(cspins[idx % len(cspins)]).convert("RGBA"), cgamma), kcc, (occ[0] + dx, occ[1]))

        def lift_open(p: Path) -> Image.Image:
            return brighten(Image.open(p).convert("RGBA"), gamma)

        def thumb_xf(k: float, o: tuple[float, float], fs: float, dy: float = 0):
            return k * fs, (W / 2 + fs * (o[0] - W / 2), H / 2 + fs * (o[1] - H / 2) + dy)

        # Backdrops: ink with a soft radial lift, and an accent floor glow under the model.
        bg = Image.new("RGB", (W, H), INK)
        lift = Image.new("L", (W, H), 0)
        ImageDraw.Draw(lift).ellipse((-200, 300, W + 200, 1500), fill=70)
        bg.paste(Image.new("RGB", (W, H), (26, 31, 46)), (0, 0), lift.filter(ImageFilter.GaussianBlur(160)))
        def floor_glow(cx: float, fy: float, rx: float) -> Image.Image:
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse((cx - rx, fy - 50, cx + rx, fy + 50), fill=ACCENT + (95,))
            return g.filter(ImageFilter.GaussianBlur(40))

        floor_y = oc[1] + kc * bb[3] - 10          # under the paws in the aligned pose, not the swinging tail
        if comp:
            glow = floor_glow(float(comp.get("main_x", 0.3)) * W, floor - 10, 240)
            glow_c = floor_glow(float(comp.get("x", 0.75)) * W, floor - 10, 200)
        else:
            glow = floor_glow(W / 2, floor_y, 330)
        line = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
        ImageDraw.Draw(line).rectangle((0, 40, W, 50), fill=ACCENT + (255,))
        line = line.filter(ImageFilter.GaussianBlur(9))
        ImageDraw.Draw(line).rectangle((0, 43, W, 47), fill=(235, 255, 230, 255))

        frames = tmp / "out"; frames.mkdir()
        n = 0

        def emit(im: Image.Image) -> None:
            nonlocal n
            im.save(frames / f"f_{n:05d}.png", compress_level=1)
            n += 1

        # A: the clip plays up to the screenshot frame.
        for p in play:
            emit(Image.open(p).convert("RGB"))
        # B: shutter flash, the frame shrinks into a screenshot thumbnail.
        for i in range(FREEZE_F):
            fs = 1 - (1 - THUMB) * ease(i / (FREEZE_F - 1))
            im = framed(F, fs, bg)
            fl = max(0.0, 1 - i / 6)
            if fl:
                im = Image.blend(im, Image.new("RGB", (W, H), (255, 255, 255)), 0.85 * fl)
            emit(im)
        # C: scan line top → bottom; behind it the photo dims, the wireframe appears, then the shaded model.
        for i in range(SCAN_F):
            yl = round(-60 + (H + 120) * ease(i / (SCAN_F - 1)))
            P = F.copy()
            if yl > 0:
                P.paste(Fblur.crop((0, 0, W, min(yl, H))), (0, 0))
                ys = max(0, min(yl - WIRE_BAND, H))
                if ys > 0:
                    P.paste(AL.crop((0, 0, W, ys)), (0, 0), AL.crop((0, 0, W, ys)))
                band = (0, ys, W, max(ys, min(yl, H)))
                if band[3] > band[1]:
                    P.paste(WL.crop(band), band[:2], WL.crop(band))
            P.paste(line, (0, yl - 45), line)
            emit(framed(P, THUMB, bg))
        done = Fblur.copy(); done.paste(AL, (0, 0), AL)
        # D: the photo falls away, the model flies to centre stage and starts turning.
        k0, o0 = thumb_xf(ka, oa, THUMB)
        for i in range(LIFT_F):
            t = ease(i / (LIFT_F - 1))
            im = framed(Fblur, THUMB - 0.25 * t, bg, dy=260 * t, alpha=1 - t)
            g = glow.copy(); g.putalpha(g.getchannel("A").point(lambda a: round(a * t)))
            im.paste(g, (0, 0), g)
            k = k0 + (kc - k0) * t
            o = (o0[0] + (oc[0] - o0[0]) * t, o0[1] + (oc[1] - o0[1]) * t)
            paste(im, lift_open(spins[i % len(spins)]).convert("RGBA"), k, o)
            emit(im)
        # E: centre-stage spin. spin_turn: one eased full turn in that many seconds, then sway ±cta_sway frames
        # around `front` (the spin index facing the viewer), so the first VO line isn't spoken to the model's back.
        base = bg.copy(); base.paste(glow, (0, 0), glow)
        ns, front = len(spins), int(spec.get("front", 0)) % len(spins)
        turn, sway = round(float(spec.get("spin_turn", 0)) * FPS), float(spec.get("cta_sway", 8))

        def sway_idx(j: int) -> int:
            return round(front + sway * math.sin(2 * math.pi * j / (3 * FPS))) % ns

        for i in range(spin_tail):
            if not turn:
                idx = (LIFT_F + i) % ns
            elif i < turn:
                idx = round(LIFT_F + ((front - LIFT_F) % ns or ns) * ease(i / turn)) % ns
            else:
                idx = sway_idx(i - turn)
            im = base.copy()
            paste(im, lift_open(spins[idx]).convert("RGBA"), kc, oc)
            companion(im, idx, i)
            emit(im)

        # Audio: the clip's own sound up to the freeze, a pop on the shutter, a whoosh on the lift.
        dur = n / FPS
        t_freeze = len(play) / FPS
        t_lift = t_freeze + (FREEZE_F + SCAN_F) / FPS
        sfx = ROOT / "assets" / "shorts-sfx"
        out = d / spec["out"]
        run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(frames / "f_%05d.png"),
             "-ss", str(start), "-t", str(freeze - start), "-i", str(video),
             "-i", str(sfx / "pop.mp3"), "-i", str(sfx / "whoosh.mp3"),
             "-filter_complex",
             f"[1:a]volume={gain},afade=t=out:st={t_freeze - 0.35:.3f}:d=0.35[s];"
             f"[2:a]adelay={round(t_freeze * 1000)}|{round(t_freeze * 1000)},volume={0.8 * fxg:.3f}[p];"
             f"[3:a]adelay={round(t_lift * 1000)}|{round(t_lift * 1000)},volume={0.6 * fxg:.3f}[w];"
             f"[s][p][w]amix=inputs=3:normalize=0:duration=longest,apad,atrim=0:{dur:.3f}[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", str(out)])

        # Full-frame CTA backdrop: the same centre-stage spin, continuing from where the clip ends.
        if spec.get("cta_full_out"):
            fdir = tmp / "full"; fdir.mkdir()
            # cta_settle: whip the remaining turn round to the front in that many seconds, then sway ±cta_sway
            # frames around it, so the model faces the viewer while the CTA line is spoken.
            # With spin_turn the model is already swaying front-on: keep swaying in phase.
            settle = round(float(spec.get("cta_settle", 0)) * FPS)
            k0 = (LIFT_F + spin_tail) % ns
            for i in range(int(float(spec.get("cta_seconds", 6)) * FPS)):
                if turn:
                    idx = sway_idx(spin_tail - turn + i)
                elif not settle:
                    idx = (k0 + i) % ns
                elif i < settle:
                    idx = round(k0 + ((front - k0) % ns) * ease(i / settle)) % ns
                else:
                    idx = sway_idx(i - settle)
                im = base.copy()
                paste(im, lift_open(spins[idx]).convert("RGBA"), kc, oc)
                companion(im, idx, spin_tail + i)
                im.save(fdir / f"c_{i:04d}.png", compress_level=1)
            run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(fdir / "c_%04d.png"),
                 "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(d / spec["cta_full_out"])])

        # CTA card spin (1410x840): same rotation, continuing from where the clip ends.
        if spec.get("cta_out"):
            cw, ch = 1410, 840
            cdir = tmp / "cta"; cdir.mkdir()
            kk = min(cw * 0.9 / uw, ch * 0.88 / uh)
            ok = (cw / 2 - kk * ucx, ch / 2 - kk * ucy)
            first = LIFT_F + spin_tail
            for i in range(len(spins)):
                im = Image.new("RGB", (cw, ch), CARD)
                paste(im, lift_open(spins[(first + i) % len(spins)]).convert("RGBA"), kk, ok)
                im.save(cdir / f"c_{i:04d}.png", compress_level=1)
            run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(cdir / "c_%04d.png"),
                 "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(d / spec["cta_out"])])
        print(f"{out} {dur:.2f}s ({len(play)} play, {FREEZE_F} freeze, {SCAN_F} scan, {LIFT_F} lift, {spin_tail} spin)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
