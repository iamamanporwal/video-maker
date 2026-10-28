"""ffmpeg/ffprobe + Pillow: probing, mastering, spec verification, dark-frame scan, evidence images, SRT."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TARGET_LUFS = -14.0
TARGET_TP = -1.5


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


# --------------------------------------------------------------------------- probe


def probe(path: Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    return json.loads(r.stdout)


def summary(path: Path) -> dict:
    d = probe(path)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    out = {"file": str(path), "duration": float(d["format"]["duration"])}
    if v:
        num, den = (int(x) for x in v["r_frame_rate"].split("/"))
        out.update(width=v["width"], height=v["height"], fps=round(num / den, 3), vcodec=v["codec_name"],
                   profile=v.get("profile"), pix_fmt=v.get("pix_fmt"), nb_frames=int(v.get("nb_frames", 0) or 0))
    if a:
        out.update(acodec=a["codec_name"], sample_rate=int(a["sample_rate"]), channels=a["channels"])
    return out


# --------------------------------------------------------------------------- loudness + master


def loudness(path: Path) -> dict:
    """Integrated loudness and true peak via ebur128."""
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", "ebur128=peak=true",
             "-f", "null", "-"], check=False)
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    lra = re.search(r"LRA:\s+(-?[\d.]+) LU", tail)
    f = lambda m: float(m.group(1)) if m and m.group(1) != "-inf" else float("-inf")
    return {"lufs": f(i), "true_peak": f(tp), "lra": f(lra)}


def master(src: Path, dst: Path, lufs: float = TARGET_LUFS, tp: float = TARGET_TP) -> dict:
    """Two-pass loudnorm to I=-14 / TP=-1.5, 48 kHz AAC 320k, -shortest, +faststart. Video is stream-copied."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    flt = f"loudnorm=I={lufs}:TP={tp}:LRA=11"
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af", flt + ":print_format=json",
             "-f", "null", "-"], check=False)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        # Silent input: no audio to normalise; still guarantee an AAC 48k stereo track.
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(src), "-f", "lavfi", "-i",
             "anullsrc=channel_layout=stereo:sample_rate=48000", "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", str(dst)])
        return {"measured": None}
    meas = json.loads(m.group(0))
    if meas["input_i"] in ("-inf", "inf"):
        shutil.copyfile(src, dst)
        return {"measured": meas}
    def encode(af: str) -> dict:
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(src), "-map", "0:v", "-map", "0:a", "-c:v", "copy",
             "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "320k", "-shortest",
             "-movflags", "+faststart", str(dst)])
        return loudness(dst)

    ok = lambda g: abs(g["lufs"] - lufs) <= 0.4 and g["true_peak"] <= -1.0
    got = encode(f"{flt}:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}"
                 f":measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true,aresample=48000")
    if ok(got):
        return {"measured": meas, "mode": "loudnorm-linear", "result": got}
    # Linear loudnorm is capped by true peak on peaky mixes (SFX hits). Gain + 4x-oversampled limiter, iterated.
    gain = lufs - float(meas["input_i"])
    ceiling = 10 ** ((tp - 0.7) / 20)
    for _ in range(4):
        got = encode(f"aresample=192000,volume={gain:.2f}dB,alimiter=limit={ceiling:.4f}:level=disabled:attack=1:release=60,"
                     f"aresample=48000")
        if ok(got):
            break
        gain += lufs - got["lufs"]
    return {"measured": meas, "mode": "gain+limiter", "result": got}


# --------------------------------------------------------------------------- frames


def luma_series(path: Path, w: int = 64) -> np.ndarray:
    """Mean luma (0..255) for every frame, decoded tiny."""
    info = summary(path)
    h = max(2, int(round(w * info["height"] / info["width"] / 2)) * 2)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    arr = np.frombuffer(r.stdout, dtype=np.uint8)
    n = arr.size // (w * h)
    return arr[: n * w * h].reshape(n, h * w).mean(axis=1)


def scan_dark_frames(path: Path, threshold: float = 8.0, dip_ratio: float = 0.35,
                     allowed: Iterable[tuple[int, int]] = ()) -> dict:
    """Near-black frames and one-frame dips (a frame much darker than both neighbours), minus allowed ranges."""
    y = luma_series(path)
    allowed = list(allowed)
    ok = lambda f: any(a <= f < b for a, b in allowed)
    dark = [int(i) for i in np.where(y < threshold)[0] if not ok(int(i))]
    dips = []
    for i in range(1, len(y) - 1):
        ref = min(y[i - 1], y[i + 1])
        if ref > 20 and y[i] < ref * dip_ratio and not ok(i):
            dips.append(i)
    return {"frames": int(len(y)), "dark": dark, "dips": dips, "mean_luma": float(y.mean()) if len(y) else 0.0}


def _ranges(frames: list[int]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for f in frames:
        if out and f == out[-1][1] + 1:
            out[-1] = (out[-1][0], f)
        else:
            out.append((f, f))
    return out


def decode_errors(path: Path) -> list[str]:
    r = run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], check=False)
    return [l for l in r.stderr.splitlines() if l.strip()]


def verify_specs(path: Path, expect: dict, allowed_dark: Iterable[tuple[int, int]] = ()) -> dict:
    """Fail-the-stage checks. expect: {duration, width, height, fps}."""
    s = summary(path)
    loud = loudness(path)
    dark = scan_dark_frames(path, allowed=allowed_dark)
    errs = decode_errors(path)
    fps = expect.get("fps", 30)
    checks = {
        "duration": abs(s["duration"] - expect["duration"]) <= 0.5 / fps + 0.03,
        "resolution": (s.get("width"), s.get("height")) == (expect["width"], expect["height"]),
        "fps": abs(s.get("fps", 0) - fps) < 0.01,
        "codec": s.get("vcodec") == "h264" and s.get("profile") in ("High", "Main", "Constrained Baseline"),
        "pix_fmt": s.get("pix_fmt") == "yuv420p",
        "audio": s.get("acodec") == "aac" and s.get("sample_rate") == 48000 and s.get("channels") == 2,
        "loudness": abs(loud["lufs"] - TARGET_LUFS) <= 0.5 if loud["lufs"] != float("-inf") else False,
        "true_peak": loud["true_peak"] <= -1.0,
        "decode": not errs,
        "dark_frames": not dark["dark"] and not dark["dips"],
    }
    return {"file": path.name, "summary": s, "loudness": loud, "dark": {
        "dark_ranges": _ranges(dark["dark"]), "dips": dark["dips"]}, "decode_errors": errs[:5],
        "checks": checks, "pass": all(checks.values())}


def spec_table(results: list[dict]) -> str:
    cols = ["duration", "resolution", "fps", "codec", "pix_fmt", "audio", "loudness", "true_peak", "decode", "dark_frames"]
    lines = ["| file | dur | WxH | LUFS | TP | " + " | ".join(cols) + " |",
             "|---" * (5 + len(cols)) + "|"]
    for r in results:
        s, l = r["summary"], r["loudness"]
        lines.append(f"| {r['file']} | {s['duration']:.3f}s | {s.get('width')}x{s.get('height')} | "
                     f"{l['lufs']:.1f} | {l['true_peak']:.1f} | "
                     + " | ".join("pass" if r["checks"][c] else "**FAIL**" for c in cols) + " |")
    return "\n".join(lines) + "\n"


def extract_frames(path: Path, out_dir: Path, fps: float = 2.0, width: int = 480,
                   start: float = 0.0, end: Optional[float] = None) -> list[tuple[float, Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("f_*.jpg"):
        f.unlink()
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start}", "-i", str(path)]
    if end is not None:
        cmd += ["-t", f"{end - start}"]
    cmd += ["-vf", f"fps={fps},scale={width}:-2", "-q:v", "3", str(out_dir / "f_%05d.jpg")]
    run(cmd)
    files = sorted(out_dir.glob("f_*.jpg"))
    return [(start + i / fps, f) for i, f in enumerate(files)]


def still_at(path: Path, seconds: float, out: Path, width: Optional[int] = None) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = ["-vf", f"scale={width}:-2"] if width else []
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{seconds:.3f}", "-i", str(path), "-frames:v", "1", *vf,
         "-q:v", "2", str(out)])
    return out


def _font(size: int) -> ImageFont.ImageFont:
    for p in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def tile(images: list[tuple[str, Path]], out: Path, cols: int = 6, cell_w: int = 320, pad: int = 6,
         bg=(20, 20, 22), title: str = "") -> Path:
    """Tile labelled images into a contact sheet (Pillow, since some ffmpeg builds lack drawtext)."""
    if not images:
        raise ValueError("no images to tile")
    ims = [(label, Image.open(p).convert("RGB")) for label, p in images]
    ar = ims[0][1].height / ims[0][1].width
    cell_h = int(cell_w * ar)
    rows = (len(ims) + cols - 1) // cols
    head = 36 if title else 0
    W = cols * cell_w + (cols + 1) * pad
    H = head + rows * (cell_h + 22) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(sheet)
    font, tfont = _font(14), _font(20)
    if title:
        d.text((pad, 8), title, fill=(226, 230, 218), font=tfont)
    for i, (label, im) in enumerate(ims):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = head + pad + r * (cell_h + 22 + pad)
        sheet.paste(im.resize((cell_w, cell_h)), (x, y))
        d.text((x + 2, y + cell_h + 3), label, fill=(212, 247, 124), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    return out


def contact_sheet(src: Path, out: Path, fps: float = 2.0, cols: int = 8, cell_w: int = 240,
                  title: str = "") -> Path:
    """Video -> timecoded contact sheet; directory of images -> tiled sheet."""
    from ..grid import timecode

    if src.is_dir():
        files = sorted([*src.glob("*.png"), *src.glob("*.jpg")])
        return tile([(f.stem, f) for f in files], out, cols=cols, cell_w=cell_w, title=title or src.name)
    with tempfile.TemporaryDirectory() as td:
        frames = extract_frames(src, Path(td), fps=fps, width=cell_w * 2)
        return tile([(timecode(int(round(t * 30))), f) for t, f in frames], out, cols=cols, cell_w=cell_w,
                    title=title or src.name)


def strip(src: Path, out: Path, start: float, end: float, fps: float = 10.0, cell_w: int = 240) -> Path:
    """10 fps strip for checking a transition."""
    from ..grid import timecode

    with tempfile.TemporaryDirectory() as td:
        frames = extract_frames(src, Path(td), fps=fps, width=cell_w * 2, start=start, end=end)
        return tile([(timecode(int(round(t * 30))), f) for t, f in frames], out, cols=min(10, len(frames)),
                    cell_w=cell_w, title=f"{src.name} {start:.2f}-{end:.2f}s @ {fps}fps")


def waveform(src: Path, out: Path, size: str = "1600x240") -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex",
         f"aformat=channel_layouts=mono,showwavespic=s={size}:colors=#D4F77C", "-frames:v", "1", str(out)])
    return out


def thumbnail(src_img: Path, out: Path, width: int = 320) -> Path:
    im = Image.open(src_img).convert("RGB")
    im.thumbnail((width, width * 4))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=90)
    return out


# --------------------------------------------------------------------------- SRT


def srt(captions: list[tuple[int, int, str]], fps: int = 30) -> str:
    def ts(f: int) -> str:
        ms = int(round(f / fps * 1000))
        h, ms = divmod(ms, 3600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    blocks = [f"{i}\n{ts(a)} --> {ts(b)}\n{text}\n" for i, (a, b, text) in enumerate(sorted(captions), 1)]
    return "\n".join(blocks)


# --------------------------------------------------------------------------- conform (fal clips, photos)


def conform(src: Path, dst: Path, width: int, height: int, fps: int = 30, seconds: Optional[float] = None,
            grade_toward: Optional[str] = None, strength: float = 0.25) -> Path:
    """30 fps CFR, cover-crop to the cut's resolution, optional grade toward the brand ink, audio stripped."""
    vf = [f"fps={fps}", f"scale={width}:{height}:force_original_aspect_ratio=increase",
          f"crop={width}:{height}", "setsar=1"]
    if grade_toward:
        r, g, b = (int(grade_toward.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
        # Lift shadows toward the ink colour and pull saturation down a touch.
        vf += [f"colorbalance=rs={(r - 0.5) * strength:.3f}:gs={(g - 0.5) * strength:.3f}:bs={(b - 0.5) * strength:.3f}",
               "eq=saturation=0.85:contrast=1.05"]
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src)]
    if seconds:
        cmd += ["-t", f"{seconds}"]
    cmd += ["-vf", ",".join(vf), "-an", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(dst)]
    dst.parent.mkdir(parents=True, exist_ok=True)
    run(cmd)
    return dst
