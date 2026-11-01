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
  sub?: string;           // smaller line under `line` (e.g. the brand promise)
  button?: string;
  after?: string;
  glb?: string;
  logo?: string;
  backdrop?: string;      // full-frame video behind the CTA (e.g. a morph spin continuing); replaces the card
};

export type Seg = ClipSeg | RevealSeg | CtaSeg;

export type VoLine = { src: string; from: number; words: Word[] };

/** Timed meme caption from reel.yaml `texts` (independent of the VO captions). */
export type TextOv = {
  from: number;
  to: number;
  text: string;
  y: number;              // centre line, px from the top of the 1080x1920 frame
  size?: number;
  style?: "box" | "stroke";  // box: black on a white rounded card (TikTok), stroke: white with a heavy outline
  accent?: string;        // colour for *word* (default: red in box style, brand accent in stroke style)
  align?: "left" | "center" | "right";
  bg?: string;            // box style: card colour (default white); text turns white on dark cards
};

export type ReelProps = {
  fps: number;
  durationInFrames: number;
  brand: Brand;
  segments: Seg[];
  vo: VoLine[];
  hook?: { text: string; until: number };
  credit?: string;
  /** Frame the credit badge may first appear (default: when the hook title ends). Keeps the hook text-free. */
  creditFrom?: number;
  sfx?: { whoosh?: string; pop?: string; riser?: string };
  cues?: { src: string; from: number; volume: number }[];  // one-shot SFX from reel.yaml `cues`
  texts?: TextOv[];
  captions?: boolean;     // false: no karaoke captions for the VO (default true)
};
