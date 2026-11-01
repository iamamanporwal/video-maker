"""Split-screen meme body for a vertical short: split.yaml -> one 1080x1920 mp4 with the panes' own audio mixed in.

    python -m reelforge.split projects/shorts/vi3w-memes/01-blender-hour-8

A split.yaml is a list of shots. Each shot is either a top/bottom pair (two 1080x960 panes, a thin black divider)
or one full-frame pane:

    out: assets/body.mp4
    shots:
    - dur: 4.6
      top:    {src: ../ref/armor.mp4, in: 35, speed: 72}
      bottom: {src: ../ref/monkey.mp4, in: 0.6, gain: 1.0, fx: [shake]}
    - dur: 2.0
      full:   {src: ../assets/sketch.png}            # images get a slow push-in

Pane keys: src, in (s), crop ([x, y, w, h] fractions), speed, gain (pane audio, 0 = muted), focus / focus_y (0..1 crop anchor), zoom,
fit (cover | contain: sharp frame over a blurred fill, or an image on a flat `bg`), freeze (hold the frame at
`in`), fx (shake, red, bw, bright, dim).
The result goes into reel.yaml as an ordinary `clip` segment (fit: crop), so text, VO, CTA and the mix stay in
reelforge.shorts.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

W, FULL_H, HALF_H, FPS, SR = 1080, 1920, 960, 30, 48000
IMAGE = {".png", ".jpg", ".jpeg", ".webp"}


def _run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffmpeg failed:\n{r.stderr[-2500:]}")
    return r.stdout


def _has_audio(p: Path) -> bool:
    return bool(_run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                      "-of", "csv=p=0", str(p)]).strip())


def _atempo(speed: float) -> str:
    out, s = [], speed
    while s > 2.0:
        out.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        out.append("atempo=0.5")
        s /= 0.5
    out.append(f"atempo={s:.4f}")
    return ",".join(out)


def pane(p: dict, base: Path, dur: float, h: int, idx: int, ins: list, vf: list, af: list, tag: str, w: int = W) -> None:
    """Append ffmpeg inputs + filter chains for one pane; the video ends as [tag], audio (if any) as [tag_a].
    A `pip:` pane (the meme reaction) is composited into a corner: {src, in, gain, w, h, pos: tl|tr|bl|br}."""
    src = (base / p["src"]).resolve()
    if not src.exists():
        raise SystemExit(f"missing pane source: {src}")
    speed, zoom = float(p.get("speed", 1)), float(p.get("zoom", 1))
    fx = set(p.get("fx") or [])
    if "shake" in fx:
        zoom = max(zoom, 1.08)
    fxx, fxy = float(p.get("focus", 0.5)), float(p.get("focus_y", 0.5))
    is_img = src.suffix.lower() in IMAGE
    k = len(ins)
    if is_img:
        ins.append(["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(src)])
    elif p.get("freeze"):
        ins.append(["-ss", f"{float(p.get('in', 0)):.3f}", "-i", str(src)])
    else:
        ins.append(["-ss", f"{float(p.get('in', 0)):.3f}", "-t", f"{dur * speed + 0.1:.3f}", "-i", str(src)])

    chain = [f"[{k}:v]"]
    if p.get("crop"):   # [x, y, w, h] as fractions of the source frame, e.g. a face cam in a screen recording
        cx, cy, cw_, ch_ = p["crop"]
        chain.append(f"crop=iw*{cw_}:ih*{ch_}:iw*{cx}:ih*{cy},")
    if is_img:
        n = round(dur * FPS)
        # Slow push-in: pre-scale to cover at 2x so zoompan has pixels to work with.
        if p.get("fit") == "contain":   # whole image on a flat backdrop (`bg`, default white paper)
            fit = (f"scale={round(w * 2 * 0.92)}:{round(h * 2 * 0.92)}:force_original_aspect_ratio=decrease,"
                   f"pad={w * 2}:{h * 2}:(ow-iw)/2:(oh-ih)/2:color={p.get('bg', 'white')},")
        else:
            fit = f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
        chain.append(f"{fit}"
                     f"zoompan=z='{zoom}+0.08*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={FPS},")
    else:
        if p.get("freeze"):
            chain.append(f"trim=end_frame=1,loop=loop=-1:size=1,setpts=N/{FPS}/TB,")
        else:
            chain.append(f"setpts=(PTS-STARTPTS)/{speed},")
        chain.append(f"fps={FPS},")
        if p.get("fit") == "contain" and p.get("bg"):   # sharp frame on a flat colour
            chain.append(f"scale={round(w * zoom)}:{round(h * zoom)}:force_original_aspect_ratio=decrease,"
                         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={p['bg']},")
        elif p.get("fit") == "contain":
            chain.append(f"split=2[{tag}bg][{tag}fg];[{tag}bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
                         f"crop={w}:{h},boxblur=30:2,eq=brightness=-0.25[{tag}bgb];"
                         f"[{tag}fg]scale={round(w * zoom)}:{round(h * zoom)}:force_original_aspect_ratio=decrease[{tag}fgs];"
                         f"[{tag}bgb][{tag}fgs]overlay=(w-w)/2:(H-h)/2,")
        else:
            cw, ch = round(w * zoom), round(h * zoom)
            chain.append(f"scale={cw}:{ch}:force_original_aspect_ratio=increase,")
            if "shake" in fx:
                chain.append(f"crop={w}:{h}:x='(iw-{w})*{fxx}+(iw-{w})*0.45*sin(2*PI*t*7.3)':"
                             f"y='(ih-{h})*{fxy}+(ih-{h})*0.45*cos(2*PI*t*9.1)',")
            else:
                chain.append(f"crop={w}:{h}:x=(iw-{w})*{fxx}:y=(ih-{h})*{fxy},")
    if "red" in fx:
        chain.append("colorchannelmixer=rr=1.25:rg=0.1:gg=0.55:bb=0.55,eq=saturation=1.3,")
    if "bw" in fx:
        chain.append("hue=s=0,")
    if "bright" in fx:
        chain.append("eq=brightness=0.05:gamma=1.45:saturation=1.15,")
    if "dim" in fx:
        chain.append("eq=brightness=-0.12,")
    pip = p.get("pip")
    out = f"{tag}m" if pip else tag
    chain.append(f"trim=duration={dur:.3f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[{out}]")
    vf.append("".join(chain))
    if pip:
        pw, ph, m, bd = int(pip.get("w", 400)), int(pip.get("h", 330)), 30, 7
        pane(pip, base, dur, ph, idx, ins, vf, af, f"{tag}p", w=pw)
        pos = pip.get("pos", "br")
        x = m if "l" in pos else w - pw - 2 * bd - m
        y = m if pos[0] == "t" else h - ph - 2 * bd - m
        vf.append(f"[{tag}p]pad={pw + 2 * bd}:{ph + 2 * bd}:{bd}:{bd}:color=white[{tag}pb];"
                  f"[{out}][{tag}pb]overlay={x}:{y},format=yuv420p[{tag}]")

    gain = float(p.get("gain", 0))
    if gain and not is_img and not p.get("freeze") and _has_audio(src):
        t = "" if speed == 1 else _atempo(speed) + ","
        af.append(f"[{k}:a]asetpts=PTS-STARTPTS,{t}aresample={SR},volume={gain},atrim=0:{dur:.3f}[{tag}a]")


def shot(s: dict, base: Path, out: Path) -> None:
    dur = float(s["dur"])
    ins, vf, af = [], [], []
    if "full" in s:
        pane(s["full"], base, dur, FULL_H, 0, ins, vf, af, "f")
        vf.append("[f]null[v]")
        tags = ["f"]
    else:
        pane(s["top"], base, dur, HALF_H, 0, ins, vf, af, "t")
        pane(s["bottom"], base, dur, HALF_H, 1, ins, vf, af, "b")
        vf.append("[t][b]vstack=2,drawbox=x=0:y=954:w=iw:h=12:color=black:t=fill[v]")
        tags = ["t", "b"]
    alabs = [re.search(r"\[\w+\]$", x).group(0) for x in af]
    if alabs:
        af.append("".join(alabs) + f"amix=inputs={len(alabs)}:normalize=0,apad=whole_dur={dur:.3f},"
                  f"atrim=0:{dur:.3f},aformat=channel_layouts=stereo[a]")
    else:
        af.append(f"anullsrc=r={SR}:cl=stereo,atrim=0:{dur:.3f}[a]")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + [x for a in ins for x in a]
    cmd += ["-filter_complex", ";".join(vf + af), "-map", "[v]", "-map", "[a]", "-r", str(FPS),
            "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-t", f"{dur:.3f}", str(out)]
    _run(cmd)


def build(d: Path) -> Path:
    d = d.resolve()
    spec = yaml.safe_load((d / "split.yaml").read_text())
    out = d / spec.get("out", "assets/body.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, s in enumerate(spec["shots"]):
            p = Path(tmp) / f"s{i:02d}.mp4"
            shot(s, d, p)
            parts.append(p)
        lst = Path(tmp) / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
              "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    return out


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(build(Path(a)))
