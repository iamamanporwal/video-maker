import React from "react";
import { Composition } from "remotion";
import { LaunchFilm } from "./LaunchFilm";
import type { FilmProps } from "./types";

const EMPTY: FilmProps = {
  fps: 30,
  durationInFrames: 90,
  brand: { accent: "#D4F77C", ink: "#0B0B0C", text: "#E2E6DA", paper: "#EFEAE0" },
  shots: [{ type: "black", from: 0, dur: 90 }],
  vo: [], titles: [], counters: [], sfx: [],
};

/** Vertical launch film. Python writes props.json; duration and fps come from it. */
export const LaunchRoot: React.FC = () => (
  <Composition
    id="LaunchFilm"
    component={LaunchFilm as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={EMPTY.durationInFrames}
    defaultProps={EMPTY}
    calculateMetadata={({ props }) => ({ durationInFrames: (props as FilmProps).durationInFrames, fps: (props as FilmProps).fps })}
  />
);
