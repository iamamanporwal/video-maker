// Props written by `python -m reelforge.shorts build` (props.json). All times are composition frames.

export type Word = [number, number, string];

export type Brand = { accent: string; ink: string; text: string; font?: string };

export type ClipSeg = {
  type: "clip" | "source";
  from: number;
  dur: number;
  src: string;            // file in the public dir
  startFrom: number;      // source offset, frames
  speed?: number;
  fit?: "frame" | "crop"; // frame: sharp 16:9 band over a blurred fill; crop: fill 9:16 around focus
  focus?: number;         // 0..1 horizontal focus for crop
  zoom?: number;
  gain?: number;          // source audio volume, 0 = muted
  label?: string;
};

export type RevealSeg = {
  type: "reveal";
  from: number;
  dur: number;
  before: string;         // image: sketch, screenshot or subject crop
  beforeLabel?: string;   // card tag for `before` (default "SKETCH"), e.g. "SCREENSHOT"
  after?: string;         // real Vi3W output: screen capture / turntable video, or a still of the model
  glb?: string;           // or a GLB exported from Vi3W, shown as a turntable
  label?: string;         // honesty label, e.g. "Recreated in Vi3W · real output"
  timer?: string;         // real logged time only, e.g. "27 s · real time"
};

export type CtaSeg = {
  type: "cta";
  from: number;
  dur: number;
  line?: string;
  button?: string;
  after?: string;
  glb?: string;
  logo?: string;
  backdrop?: string;      // full-frame video behind the CTA (e.g. a morph spin continuing); replaces the card
};

export type Seg = ClipSeg | RevealSeg | CtaSeg;

export type VoLine = { src: string; from: number; words: Word[] };

export type ReelProps = {
  fps: number;
  durationInFrames: number;
  brand: Brand;
  segments: Seg[];
  vo: VoLine[];
  hook?: { text: string; until: number };
  credit?: string;
  sfx?: { whoosh?: string; pop?: string; riser?: string };
};
