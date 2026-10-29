// Props written by `python -m reelforge.launch build` (props.json). All times are composition frames.

export type Word = [number, number, string];

export type Brand = { accent: string; ink: string; text: string; paper: string };

type Base = { from: number; dur: number; credit?: string };

export type ClipShot = Base & {
  type: "clip";
  src: string;            // file in the public dir
  startFrom: number;      // source offset, frames
  speed?: number;
  focus?: number;         // 0..1 horizontal focus of the 9:16 crop
  focusY?: number;
  zoom?: [number, number]; // scale at the first and last frame (slow push)
  gain?: number;          // source audio volume, 0 = muted
};

export type ImageShot = Base & { type: "image"; src: string; zoom?: [number, number]; paper?: boolean };

export type CountShot = Base & { type: "count"; n: number; label: string };

/** Sketch → Vi3W → 3D: the drawing on paper, a lime scan, then the real Vi3W output (GLB turntable or image). */
export type ScanShot = Base & { type: "scan"; before: string; after?: string; glb?: string; phase: "scan" | "model"; label?: string };

export type ModelsShot = Base & { type: "models"; glbs: string[] };

export type LineShot = Base & { type: "line"; glbs: string[] };

export type LogoShot = Base & { type: "logo"; logo: string; line: string; url: string; clicks: number[] };

export type BlackShot = Base & { type: "black" };

export type Shot = ClipShot | ImageShot | CountShot | ScanShot | ModelsShot | LineShot | LogoShot | BlackShot;

/** A VO line; its words are shown as kinetic type. `accent` words are drawn in the brand accent. */
export type VoLine = { src: string; from: number; words: Word[]; accent?: string[]; y?: number; hide?: boolean };

export type Title = { from: number; to: number; text: string; y?: number; size?: number };

export type Counter = { from: number; to: number; label: string; a: number; b: number };

export type Cue = { src: string; from: number; volume?: number };

export type FilmProps = {
  fps: number;
  durationInFrames: number;
  brand: Brand;
  shots: Shot[];
  vo: VoLine[];
  titles: Title[];
  counters: Counter[];
  sfx: Cue[];
  music?: { src: string; volume: number; duck: number };
};
