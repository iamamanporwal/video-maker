import { evolvePath } from "@remotion/paths";
import React from "react";
import { useCurrentFrame } from "remotion";
import { C, F, BRAND } from "../generated/brand";
import { tween } from "../lib/anim";
import { useFormat } from "../lib/layout";

/**
 * Per-word opacity + rise + blur-in. (Masked wipes slice glyphs into slivers - reviewers flagged that every time.)
 * Words wrapped in *asterisks* are drawn in the accent colour.
 */
export const Headline: React.FC<{
  text: string;
  at?: number;
  out?: number;
  size?: number;
  stagger?: number;
  align?: "left" | "center" | "right";
  color?: string;
  weight?: number;
  maxWidth?: number;
  style?: React.CSSProperties;
}> = ({ text, at = 0, out, size = 96, stagger = 4, align = "left", color = C.text, weight = F.displayWeight, maxWidth, style }) => {
  const frame = useCurrentFrame();
  const { u } = useFormat();
  const words = text.split(/\s+/).filter(Boolean);
  const outK = out !== undefined ? tween(frame, out, 10, 0, 1, "inOutCubic") : 0;
  return (
    <div
      style={{
        fontFamily: F.display,
        fontWeight: weight,
        fontSize: size * u,
        lineHeight: 1.02,
        letterSpacing: BRAND.tracking.headline,
        color,
        textAlign: align,
        maxWidth,
        opacity: 1 - outK,
        transform: `translateY(${-outK * 18 * u}px)`,
        ...style,
      }}
    >
      {words.map((w, i) => {
        const s = at + i * stagger;
        const k = tween(frame, s, 18, 0, 1, "outExpo");
        const accent = /^\*.*\*$/.test(w);
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              marginRight: "0.24em",
              opacity: k,
              transform: `translateY(${(1 - k) * 0.35}em)`,
              filter: `blur(${(1 - k) * 14 * u}px)`,
              color: accent ? C.accent : undefined,
            }}
          >
            {accent ? w.slice(1, -1) : w}
          </span>
        );
      })}
    </div>
  );
};

/** Mono tag, 18px or larger. Used for honest timing labels ("3 min 7 s - real time"). */
export const Tag: React.FC<{ text: string; at?: number; style?: React.CSSProperties; dot?: boolean }> = ({ text, at = 0, style, dot = true }) => {
  const frame = useCurrentFrame();
  const { u } = useFormat();
  const k = tween(frame, at, 14);
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10 * u,
        fontFamily: F.mono,
        fontSize: Math.max(18, 22 * u),
        color: C.text,
        background: "rgba(11,11,12,0.72)",
        border: `1px solid ${C.muted[2]}`,
        padding: `${8 * u}px ${14 * u}px`,
        borderRadius: 999,
        opacity: k,
        transform: `translateY(${(1 - k) * 10}px)`,
        ...style,
      }}
    >
      {dot && <span style={{ width: 9 * u, height: 9 * u, borderRadius: "50%", background: C.accent }} />}
      {text}
    </div>
  );
};

/** The motif: a lime line that becomes the next object. */
export const LimeLine: React.FC<{
  d: string;
  at?: number;
  dur?: number;
  width: number;
  height: number;
  strokeWidth?: number;
  glow?: boolean;
  style?: React.CSSProperties;
}> = ({ d, at = 0, dur = 24, width, height, strokeWidth = 6, glow = true, style }) => {
  const frame = useCurrentFrame();
  const k = tween(frame, at, dur, 0, 1, "inOutCubic");
  const ev = evolvePath(Math.max(0.0001, k), d);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", ...style }}>
      <path
        d={d}
        fill="none"
        stroke={C.accent}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={ev.strokeDasharray}
        strokeDashoffset={ev.strokeDashoffset}
        style={glow ? { filter: `drop-shadow(0 0 10px ${C.accent}99)` } : undefined}
      />
    </svg>
  );
};

/** Typewriter with a linear caret (one of the two places linear motion is allowed). */
export const Typed: React.FC<{ text: string; at?: number; cps?: number; style?: React.CSSProperties; caret?: boolean }> = ({
  text,
  at = 0,
  cps = 24,
  style,
  caret = true,
}) => {
  const frame = useCurrentFrame();
  const n = Math.max(0, Math.min(text.length, Math.floor(((frame - at) / 30) * cps)));
  const blink = Math.floor(frame / 15) % 2 === 0;
  return (
    <span style={style}>
      {text.slice(0, n)}
      {caret && <span style={{ opacity: n < text.length || blink ? 1 : 0, color: C.accent }}>▍</span>}
    </span>
  );
};
