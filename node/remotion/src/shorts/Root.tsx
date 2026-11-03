import React from "react";
import { Composition } from "remotion";
import { DevFact } from "./DevFact";
import { GameReel } from "./GameReel";
import { GtaFact } from "./GtaFact";
import { IMissSteve } from "./IMissSteve";
import { ModClip } from "./ModClip";
import { EXPLAINER_FRAMES, RobloxExplainer } from "./RobloxExplainer";
import type { ReelProps } from "./types";
import { OUTRO_FRAMES, Vi3WOutro } from "./Vi3WOutro";
import { CTA_DEFAULTS, CTA_FRAMES, Vi3WCta } from "./Vi3WCta";

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
    id="ModClip"
    component={ModClip as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={900}
    defaultProps={{}}
    calculateMetadata={({ props }) => ({ durationInFrames: (props as any).durationInFrames ?? 900, fps: 30 })}
  />
  <Composition
    id="DevFact"
    component={DevFact as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={900}
    defaultProps={{}}
    calculateMetadata={({ props }) => ({ durationInFrames: (props as any).durationInFrames ?? 900, fps: 30 })}
  />
  <Composition
    id="GtaFact"
    component={GtaFact as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={900}
    defaultProps={{}}
    calculateMetadata={({ props }) => ({ durationInFrames: (props as any).durationInFrames ?? 900, fps: 30 })}
  />
  <Composition
    id="Vi3WCta"
    component={Vi3WCta as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={CTA_FRAMES}
    defaultProps={CTA_DEFAULTS}
  />
  <Composition
    id="Vi3WOutro"
    component={Vi3WOutro as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={OUTRO_FRAMES}
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
