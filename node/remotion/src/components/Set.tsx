import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import { C, F } from "../generated/brand";
import { tween } from "../lib/anim";
import { useAsset } from "../lib/context";
import { useFormat } from "../lib/layout";
import { Typed } from "./Type";

/** A monitor in a dark room with an empty chair. Optionally a real desk photo (preferred over vectors). */
export const Room: React.FC<{ photo?: string; glow?: number; children?: React.ReactNode; monitor?: boolean }> = ({
  photo,
  glow = 1,
  children,
  monitor = true,
}) => {
  const frame = useCurrentFrame();
  const asset = useAsset();
  const { w, h, vertical, u } = useFormat();
  const drift = 1 + frame * 0.00025; // camera drift: linear allowed
  const mw = vertical ? w * 0.86 : w * 0.56;
  const mh = mw * 0.58;
  const flicker = 0.92 + 0.08 * Math.sin(frame * 0.21) * Math.sin(frame * 0.057);
  return (
    <AbsoluteFill style={{ background: C.ink, overflow: "hidden" }}>
      {photo ? (
        <Img src={asset(photo)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${drift})`, filter: "brightness(0.55) saturate(0.8)" }} />
      ) : (
        <AbsoluteFill style={{ transform: `scale(${drift})` }}>
          <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% ${vertical ? 38 : 42}%, rgba(120,150,170,${0.28 * glow * flicker}) 0%, rgba(11,11,12,0) 55%)` }} />
          <div style={{ position: "absolute", left: 0, right: 0, top: h * 0.74, height: h * 0.26, background: "linear-gradient(#141513, #0b0b0c)" }} />
          {/* empty chair */}
          <div style={{ position: "absolute", left: w * (vertical ? 0.62 : 0.66), top: h * 0.6, width: 120 * u, height: 220 * u, borderRadius: 18 * u, background: "#121311", boxShadow: "inset 0 0 0 2px #1c1e1b" }} />
        </AbsoluteFill>
      )}
      {monitor && (
        <div
          style={{
            position: "absolute",
            left: (w - mw) / 2,
            top: h * (vertical ? 0.3 : 0.18),
            width: mw,
            height: mh,
            borderRadius: 14 * u,
            background: "#0f1112",
            boxShadow: `0 0 ${140 * u * glow}px rgba(150,180,200,${0.25 * glow}), inset 0 0 0 ${3 * u}px #22252a`,
            overflow: "hidden",
          }}
        >
          {children}
        </div>
      )}
    </AbsoluteFill>
  );
};

/** An unbranded default-cube viewport (the "empty 3D app" before the product). */
export const GenericViewport: React.FC = () => {
  const frame = useCurrentFrame();
  const a = frame * 0.6;
  return (
    <AbsoluteFill style={{ background: "#1c1f22", display: "grid", placeItems: "center" }}>
      <AbsoluteFill style={{ backgroundImage: "linear-gradient(#2a2e33 1px, transparent 1px), linear-gradient(90deg, #2a2e33 1px, transparent 1px)", backgroundSize: "40px 40px", opacity: 0.5 }} />
      <div style={{ width: 160, height: 160, transform: `perspective(600px) rotateX(-24deg) rotateY(${a}deg)`, transformStyle: "preserve-3d" }}>
        {[0, 90, 180, 270].map((r) => (
          <div key={r} style={{ position: "absolute", inset: 0, background: "#8a8f96", border: "1px solid #5b6066", transform: `rotateY(${r}deg) translateZ(80px)` }} />
        ))}
        <div style={{ position: "absolute", inset: 0, background: "#a3a8ae", transform: "rotateX(90deg) translateZ(80px)" }} />
      </div>
    </AbsoluteFill>
  );
};

export type Msg = { from: string; text: string; at: number; me?: boolean };

/** Generic, unbranded chat. Messages type in, then land. */
export const ChatPanel: React.FC<{ messages: Msg[]; title?: string; width: number; height: number }> = ({ messages, title = "#3d-team", width, height }) => {
  const frame = useCurrentFrame();
  const { u } = useFormat();
  const shown = messages.filter((m) => frame >= m.at);
  return (
    <div style={{ width, height, background: "#141615", borderRadius: 18 * u, border: `1px solid ${C.muted[2]}`, overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: `${16 * u}px ${22 * u}px`, borderBottom: `1px solid ${C.muted[2]}`, fontFamily: F.mono, color: C.muted[0], fontSize: 22 * u }}>{title}</div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 14 * u, padding: 22 * u }}>
        {shown.map((m, i) => {
          const k = tween(frame, m.at, 14, 0, 1, "outBack");
          return (
            <div key={i} style={{ alignSelf: m.me ? "flex-end" : "flex-start", maxWidth: "82%", opacity: Math.min(1, k * 1.4), transform: `translateY(${(1 - k) * 20}px) scale(${0.92 + 0.08 * k})` }}>
              <div style={{ fontFamily: F.mono, fontSize: 18 * u, color: C.muted[0], marginBottom: 4 * u }}>{m.from}</div>
              <div style={{ fontFamily: F.body, fontWeight: F.bodyWeight, fontSize: 30 * u, color: m.me ? C.ink : C.text, background: m.me ? C.accent : "#232622", padding: `${12 * u}px ${18 * u}px`, borderRadius: 16 * u }}>
                {m.text}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const Clock: React.FC<{ text: string; at?: number; size?: number; style?: React.CSSProperties }> = ({ text, at = 0, size = 64, style }) => {
  const frame = useCurrentFrame();
  const { u } = useFormat();
  return (
    <div style={{ fontFamily: F.mono, fontSize: size * u, color: C.text, opacity: tween(frame, at, 12), letterSpacing: "0.02em", ...style }}>
      <Typed text={text} at={at} cps={14} caret={false} />
    </div>
  );
};
