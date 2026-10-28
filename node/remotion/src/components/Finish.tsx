import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { C, F } from "../generated/brand";
import { useFormat } from "../lib/layout";

/** Grain at ~8% (hides banding) + vignette. Seeded per frame: deterministic. */
export const Finish: React.FC<{ grain?: number; vignette?: number }> = ({ grain = 0.08, vignette = 0.55 }) => {
  const frame = useCurrentFrame();
  const { w, h } = useFormat();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill
        style={{ background: `radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 45%, rgba(0,0,0,${vignette}) 100%)` }}
      />
      <svg width={w} height={h} style={{ position: "absolute", inset: 0, opacity: grain, mixBlendMode: "overlay" }}>
        <filter id={`g${frame}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={frame % 97} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#g${frame})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Word-by-word caption highlight; unlit words at 72%. Sits in the safe band. */
export const Captions: React.FC<{ captions: [number, number, string][] }> = ({ captions }) => {
  const frame = useCurrentFrame();
  const { safe, u, h, vertical } = useFormat();
  const cur = captions.find(([a, b]) => frame >= a && frame < b);
  if (!cur) return null;
  const [a, b, text] = cur;
  const words = text.split(/\s+/);
  const per = (b - a) / words.length;
  const lit = Math.floor((frame - a) / per);
  const fade = Math.min(1, (frame - a) / 5, (b - frame) / 5);
  return (
    <div
      style={{
        position: "absolute",
        left: safe.left,
        right: safe.right,
        top: vertical ? h - safe.bottom - 90 * u : undefined,
        bottom: vertical ? undefined : safe.bottom,
        textAlign: "center",
        fontFamily: F.body,
        fontWeight: F.bodyWeight,
        fontSize: (vertical ? 46 : 40) * u,
        opacity: fade,
        textShadow: "0 2px 18px rgba(0,0,0,0.8)",
      }}
    >
      {words.map((w, i) => (
        <span key={i} style={{ color: i <= lit ? C.text : C.text, opacity: i <= lit ? 1 : 0.72, marginRight: "0.28em" }}>
          {w}
        </span>
      ))}
    </div>
  );
};

/** Visible in debug renders: scene id + frame + safe zones. */
export const DebugOverlay: React.FC<{ label: string }> = ({ label }) => {
  const frame = useCurrentFrame();
  const { safe, w, h } = useFormat();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: safe.left, top: safe.top, width: w - safe.left - safe.right, height: h - safe.top - safe.bottom, outline: "2px dashed rgba(255,0,128,0.6)" }} />
      <div style={{ position: "absolute", left: 8, top: 8, fontFamily: F.mono, fontSize: 20, color: "#f0f", background: "#000a", padding: 4 }}>
        {label} f{frame}
      </div>
    </AbsoluteFill>
  );
};
