import React from "react";
import { Composition } from "remotion";
import { GameReel } from "./GameReel";
import { IMissSteve } from "./IMissSteve";
import { EXPLAINER_FRAMES, RobloxExplainer } from "./RobloxExplainer";
import type { ReelProps } from "./types";

const EMPTY: ReelProps = {
  fps: 30,
  durationInFrames: 90,
  brand: { accent: "#7CFF6B", ink: "#07080C", text: "#FFFFFF" },
  segments: [{ type: "cta", from: 0, dur: 90 }],
  vo: [],
};

/** Vertical shorts. Python writes props.json; duration and fps come from it. */
export const ShortsRoot: React.FC = () => (
  <>
  <Composition
    id="IMissSteve"
    component={IMissSteve as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={2663}
    defaultProps={{}}
    calculateMetadata={({ props }) => ({ durationInFrames: (props as any).durationInFrames ?? 2663, fps: 30 })}
  />
  <Composition
    id="RobloxExplainer"
    component={RobloxExplainer as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={EXPLAINER_FRAMES}
    defaultProps={{}}
  />
  <Composition
    id="GameReel"
    component={GameReel as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={EMPTY.durationInFrames}
    defaultProps={EMPTY}
    calculateMetadata={({ props }) => ({ durationInFrames: (props as ReelProps).durationInFrames, fps: (props as ReelProps).fps })}
  />
  </>
);
