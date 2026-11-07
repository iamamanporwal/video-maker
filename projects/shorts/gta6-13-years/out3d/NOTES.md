# 3D inserts: gta6-13-years

Build: `.venv/bin/python out3d/build.py calendar,consoles,printer,hourglass,vault [--stills] [--full]`, run from the project dir.
- `scene.py <shot> <blend>` builds one shot per .blend in `out3d/blend/`.
- `--stills` renders 2 frames per shot at 50 % into `out3d/sheet.jpg`.
- `--full` renders with 3 workers into `out3d/frames/<shot>/` and encodes `public/3d/<shot>.mp4` (H.264 yuv420p tv-range, crf 18, no audio).
- EEVEE runs at 10 samples with AgX Punchy and the `L.post` bloom, dispersion and vignette.

| shot | dur | s/frame | flicker median | look (self-score) |
|---|---|---|---|---|
| calendar | 4.0 s | 0.29 | 16 (the flying pages are real motion; the static bg tests at 2.3) | 8 |
| consoles | 4.0 s | 0.23 | 1.4 | 7.5 |
| printer | 4.0 s | 0.24 | 8.9 (real motion from the flying bills) | 8 |
| hourglass | 3.0 s | 0.34 | 1.6 | 7.5 |
| vault | 3.0 s | 0.23 | — | 8 |

The shots contain no text, numbers or logos.
- Calendar pages use a procedural texture: pink header, ink slab, grid, and a red "deadline" ring.
- Bills use a procedural guilloche/oval/rosette pattern with no marks.

Known compromises:
- consoles: the three boxes are fairly small in frame, a side effect of 9:16 with three side-by-side objects plus a clean top 35 %. The pink wall fills the upper area.
- hourglass: the glass is faked with alpha 0.14 plus clearcoat. EEVEE transmission rendered milky grey. As a result the sand reads peach-orange rather than deep gold.
- calendar: the haze volume is subtle. The blind stripes come from a spot light behind slats that are invisible to the camera.
