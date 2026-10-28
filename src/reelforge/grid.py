"""BPM grid math. At 120 BPM / 30 fps: 1 beat = 15 frames, 1 bar = 60 frames."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Grid:
    bpm: int = 120
    fps: int = 30
    beats_per_bar: int = 4
    offset_frames: int = 0

    @property
    def beat_frames(self) -> float:
        return self.fps * 60.0 / self.bpm

    @property
    def bar_frames(self) -> float:
        return self.beat_frames * self.beats_per_bar

    def sec_to_frame(self, s: float) -> int:
        return int(round(s * self.fps))

    def frame_to_sec(self, f: int) -> float:
        return f / self.fps

    def nearest_beat(self, frame: float) -> int:
        n = round((frame - self.offset_frames) / self.beat_frames)
        return int(round(self.offset_frames + n * self.beat_frames))

    def nearest_bar(self, frame: float) -> int:
        n = round((frame - self.offset_frames) / self.bar_frames)
        return int(round(self.offset_frames + n * self.bar_frames))

    def on_beat(self, frame: float, tol: int = 1) -> bool:
        return abs(frame - self.nearest_beat(frame)) <= tol

    def on_bar(self, frame: float, tol: int = 1) -> bool:
        return abs(frame - self.nearest_bar(frame)) <= tol

    def snap_seconds(self, s: float) -> float:
        return self.frame_to_sec(self.nearest_beat(self.sec_to_frame(s)))

    def describe(self) -> str:
        return (f"{self.bpm} BPM at {self.fps} fps: 1 beat = {self.beat_frames:g} frames "
                f"({self.beat_frames / self.fps:g}s), 1 bar = {self.bar_frames:g} frames "
                f"({self.bar_frames / self.fps:g}s)")


def timecode(frame: int, fps: int = 30) -> str:
    s = frame / fps
    return f"{int(s // 60):02d}:{s % 60:04.1f}"
