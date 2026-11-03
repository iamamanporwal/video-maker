import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { tween } from "../lib/anim";
import { C, MONT, shadow } from "./RobloxExplainer";

/** Shared Vi3W outro / CTA, 1080x1920, 7 s, silent (each short records its own VO line and aligns "Vi3W.in" to URL_AT).
 *  Background: showcase.mp4 — the Blender turntable of real Vi3W generations (projects/shorts/vi3w-outro/showcase.py).
 *  Foreground: 2D motion graphics only (no 3D text). All copy is props, so wording changes never re-render 3D.
 *  Safe zones: headline top 150-560, CTA 1290-1760 (models live in the middle band). */

export const CTA_FRAMES = 210;
export const URL_AT = 100;                        // frame the typed URL completes (≈3.33 s) — the VO's "Vi3W.in" lands here

export type CtaProps = {
  kicker: string;          // "THIS WHOLE VIDEO?"
  line1: string;           // "MADE WITH THE"
  brand: string;           // "Vi3W"
  line2: string;           // "WORKFLOW"
  chip: string;            // "every model here was made in Vi3W"
  url: string;             // "vi3w.in"
  promise: string;         // "draw it → get it in 3D"
  bio: string;             // "link in bio"
};

export const CTA_DEFAULTS: CtaProps = {
  kicker: "THIS WHOLE VIDEO?",
  line1: "MADE WITH THE",
  brand: "Vi3W",
  line2: "WORKFLOW",
  chip: "every model here was made in Vi3W",
  url: "vi3w.in",
  promise: "draw it → get it in 3D",
  bio: "link in bio",
};

const W = 1080;
const T_KICK = 4, T_HEAD = 30, T_CHIP = 64, T_BAR = 84, T_TYPE = 88, T_CURSOR = 104, T_CLICK = 120, T_PROMISE = 128, T_BIO = 146;

const Pop: React.FC<{ from: number; children: React.ReactNode; style?: React.CSSProperties; dur?: number }> = ({ from, children, style, dur = 9 }) => {
  const f = useCurrentFrame();
  if (f < from) return null;
  const k = tween(f, from, dur, 0, 1, "outBack");
  return <div style={{ transform: `scale(${k})`, opacity: tween(f, from, 4), ...style }}>{children}</div>;
};

/** Words drop in one by one with a squash. */
const Kicker: React.FC<{ text: string; from: number }> = ({ text, from }) => {
  const f = useCurrentFrame();
  return (
    <div style={{ display: "flex", justifyContent: "center", gap: 22, flexWrap: "wrap" }}>
      {text.split(" ").map((w, i) => {
        const s = from + i * 4;
        const y = tween(f, s, 10, -70, 0, "outBack");
        return <span key={i} style={{ display: "inline-block", opacity: tween(f, s, 4), transform: `translateY(${y}px) rotate(${(i % 2 ? 1 : -1) * 2}deg)`,
                                      fontFamily: MONT, fontWeight: 900, fontSize: 84, color: "#fff", letterSpacing: "-0.02em",
                                      textShadow: shadow(0.8) }}>{w}</span>;
      })}
    </div>
  );
};

const Headline: React.FC<{ p: CtaProps }> = ({ p }) => {
  const f = useCurrentFrame();
  const wipe = tween(f, T_HEAD + 8, 10, 0, 1, "outExpo");
  const glow = 0.6 + 0.4 * Math.sin(f / 6);
  return (
    <div style={{ position: "absolute", top: 300, left: 0, right: 0, textAlign: "center" }}>
      <Pop from={T_HEAD}>
        <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 52, color: "#ffffffDD", letterSpacing: "0.12em", textShadow: shadow(0.6) }}>{p.line1}</div>
      </Pop>
      <Pop from={T_HEAD + 6} style={{ marginTop: 6 }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 20, fontFamily: MONT, fontWeight: 900, fontSize: 92, letterSpacing: "-0.03em" }}>
          <span style={{ position: "relative", padding: "0 26px" }}>
            <span style={{ position: "absolute", inset: "6px 0", background: C.accent, borderRadius: 24, transformOrigin: "left",
                           transform: `scaleX(${wipe}) rotate(-2deg)`, boxShadow: `0 0 ${60 * glow}px ${C.accent}AA` }} />
            <span style={{ position: "relative", color: wipe > 0.5 ? C.ink : "#fff" }}>{p.brand}</span>
          </span>
          <span style={{ color: "#fff", textShadow: shadow(0.9) }}>{p.line2}</span>
        </div>
      </Pop>
    </div>
  );
};

const Chip: React.FC<{ text: string }> = ({ text }) => {
  const f = useCurrentFrame();
  return (
    <Pop from={T_CHIP} style={{ position: "absolute", top: 1195, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 34, color: "#fff", padding: "12px 28px", borderRadius: 999,
                    background: "#0B0718CC", border: "2px solid #ffffff40", backdropFilter: "blur(6px)", display: "flex", gap: 12, alignItems: "center" }}>
        <span style={{ transform: `rotate(${f * 4}deg)`, display: "inline-block" }}>✦</span>{text}
      </div>
    </Pop>
  );
};

/** Browser bar: the URL types itself, a cursor flies in and clicks; the bar flashes accent with a ripple. */
const UrlBar: React.FC<{ url: string }> = ({ url }) => {
  const f = useCurrentFrame();
  if (f < T_BAR) return null;
  const n = Math.min(url.length, Math.max(0, Math.floor((f - T_TYPE) / ((URL_AT - T_TYPE) / url.length))));
  const caret = f < T_CLICK && Math.floor(f / 8) % 2 === 0;
  const press = f >= T_CLICK ? 1 - 0.07 * Math.sin(Math.min(1, (f - T_CLICK) / 6) * Math.PI) : 1;
  const hot = f >= T_CLICK + 2;
  const k = tween(f, T_BAR, 10, 0.6, 1, "outBack") * press;
  const cx = tween(f, T_CURSOR, 16, 520, 250, "outCubic"), cy = tween(f, T_CURSOR, 16, 260, 52, "outCubic");
  const rip = f >= T_CLICK ? (f - T_CLICK) / 18 : -1;
  const pulse = hot ? 1 + 0.03 * Math.sin((f - T_CLICK) / 4) : 1;
  return (
    <div style={{ position: "absolute", top: 1300, left: (W - 860) / 2, width: 860, height: 128, opacity: tween(f, T_BAR, 5) }}>
      {rip >= 0 && rip <= 1 && (
        <div style={{ position: "absolute", inset: 0, borderRadius: 999, border: `6px solid ${C.accent}`, opacity: 1 - rip,
                      transform: `scale(${1 + rip * 0.35})` }} />
      )}
      <div style={{ position: "absolute", inset: 0, borderRadius: 999, transform: `scale(${k * pulse})`, display: "flex", alignItems: "center", gap: 22,
                    padding: "0 40px", background: hot ? C.accent : "#ffffff", boxShadow: hot ? `0 0 80px ${C.accent}AA, 0 20px 50px #000C` : "0 20px 50px #000C" }}>
        <Img src={staticFile("logo.png")} style={{ width: 64, height: 64, borderRadius: 14 }} />
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 66, color: C.ink, letterSpacing: "-0.02em", flex: 1 }}>
          {url.slice(0, n)}<span style={{ opacity: caret ? 1 : 0, color: "#7c3aed" }}>|</span>
        </div>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 56, color: C.ink, transform: `translateX(${hot ? Math.sin(f / 4) * 6 : 0}px)` }}>➜</div>
      </div>
      {f >= T_CURSOR && f < T_CLICK + 40 && (
        <svg width="70" height="86" viewBox="0 0 24 30" style={{ position: "absolute", left: cx + 380, top: cy,
                                                                  transform: `scale(${f >= T_CLICK && f < T_CLICK + 5 ? 0.85 : 1})`,
                                                                  filter: "drop-shadow(0 6px 10px #000A)", opacity: 1 - tween(f, T_CLICK + 28, 10) }}>
          <path d="M2 2 L2 24 L8 18 L12 28 L16 26 L12 16 L20 16 Z" fill="#fff" stroke="#07080C" strokeWidth="1.8" strokeLinejoin="round" />
        </svg>
      )}
    </div>
  );
};

const Bottom: React.FC<{ p: CtaProps }> = ({ p }) => {
  const f = useCurrentFrame();
  const bob = Math.sin(f / 5) * 8;
  return (
    <>
      <Pop from={T_PROMISE} style={{ position: "absolute", top: 1462, left: 0, right: 0, textAlign: "center" }}>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 64, color: "#fff", letterSpacing: "-0.01em", textShadow: shadow(0.9) }}>{p.promise}</div>
      </Pop>
      <Pop from={T_BIO} style={{ position: "absolute", top: 1575, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: MONT, fontWeight: 900, fontSize: 44, color: C.ink, background: C.yellow,
                      padding: "14px 34px", borderRadius: 999, border: `4px solid ${C.ink}`, boxShadow: "0 12px 36px #000B",
                      transform: `scale(${1 + 0.04 * Math.sin(f / 4)})` }}>
          <span style={{ display: "inline-block", transform: `translateY(${-Math.abs(bob)}px)` }}>👆</span>{p.bio}
        </div>
      </Pop>
    </>
  );
};

export const Vi3WCta: React.FC<Partial<CtaProps>> = (props) => {
  const p = { ...CTA_DEFAULTS, ...props };
  const f = useCurrentFrame();
  const flash = 1 - tween(f, 0, 8, 0, 1);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <OffthreadVideo src={staticFile("showcase.mp4")} muted />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, #0B0618E6 0%, #0B061899 22%, #0B061800 36%, #0B061800 60%, #0B0618AA 74%, #0B0618EE 100%)" }} />
      <div style={{ position: "absolute", top: 170, left: 0, right: 0 }}><Kicker text={p.kicker} from={T_KICK} /></div>
      <Headline p={p} />
      <Chip text={p.chip} />
      <UrlBar url={p.url} />
      <Bottom p={p} />
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.9 }} />
    </AbsoluteFill>
  );
};
