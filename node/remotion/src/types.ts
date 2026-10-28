export type Fmt = "16x9" | "9x16" | "4x5" | "5x4";

export type Scene = {
  id: string;
  kind: string;
  from: number;
  duration: number;
  props: Record<string, any>;
};

export type MusicSegment = {
  src: string;
  from: number;
  trimSec: number;
  dur: number;
  volumeKeys: [number, number][];
};

export type CutTimeline = {
  name: string;
  fps: number;
  durationInFrames: number;
  formats: Fmt[];
  bpm: number;
  scenes: Scene[];
  sfx: [number, string, number, number][];
  captions: [number, number, string][];
  music: MusicSegment[];
  voice?: VoiceLine[];
};

export type VoiceLine = {
  src: string;
  from: number;
  vol?: number;
  words: [number, number, string][];
  capY?: number;
  caption?: boolean;
};

export type Timeline = {
  version: number;
  project: string;
  brand: Record<string, any>;
  cuts: CutTimeline[];
};

export type Take = {
  take: string;
  dir: string;
  page: { width: number; height: number };
  dpr: number;
  t: number[];
  f: string[];
  events: { t: number; name: string; [k: string]: any }[];
  mouse: [number, number, number, number][];
  outputs: Record<string, string>;
  duration: number;
};

export type FilmProps = {
  timeline: Timeline;
  takes: Record<string, Take>;
  assetBase: string;
  sfxFiles: Record<string, string>;
  debug?: boolean;
};
