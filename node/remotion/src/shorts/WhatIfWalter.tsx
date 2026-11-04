import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { tween } from "../lib/anim";

/** "What if Walter White never had cancer?" A 97 s vertical what-if essay told as a case file.
 *  Timeline A (the show) is amber and harsh. Timeline B (just a cough) is a quiet slate-teal dossier where the dead
 *  get re-stamped ALIVE. No footage, no likenesses, no show logos: everything is drawn type, paper and line art.
 *  All timing comes from props.A (seconds, film time), written by projects/shorts/what-if-walter/timeline.py from the
 *  narrator's measured line times. Audio is mixed there too, then muxed after render. */

const { fontFamily: SERIF } = loadPlayfair("normal", { weights: ["400", "700", "900"], subsets: ["latin"] });
const { fontFamily: SERIF_I } = loadPlayfair("italic", { weights: ["400", "700"], subsets: ["latin"] });
const { fontFamily: MONO } = loadMono("normal", { weights: ["400", "500", "700"], subsets: ["latin"] });
const { fontFamily: SANS } = loadInter("normal", { weights: ["700", "800"], subsets: ["latin"] });

type Word = [number, number, string];
type Line = { src: string; start: number; dur: number; text: string; words: Word[] };
export type WalterProps = { fps: number; durationInFrames: number; lines: Line[]; A: Record<string, number> };

const W = 1080, H = 1920;
const INK = "#0B0A09", PAPER = "#EDE3CC", PAPER_D = "#D9CBAA", AMBER = "#F0A531", RED = "#D7362C", TEAL = "#5FC4B8",
  SLATE = "#1B2427", BONE = "#F4EFE6", GREY = "#8C918F";

// --------------------------------------------------------------------------- time helpers
const useT = () => useCurrentFrame() / 30;
/** 0..1 ease from second a over d seconds. */
const k = (t: number, a: number, d = 0.4, e = "outExpo") => tween(t * 30, a * 30, d * 30, 0, 1, e);
const keys = (t: number, kf: [number, number][]) =>
  interpolate(t, kf.map((x) => x[0]), kf.map((x) => x[1]), { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const rnd = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** A scene: mounted from `a` to `b` (s), cross-fading over fi / fo seconds. */
const Scene: React.FC<{ a: number; b: number; fi?: number; fo?: number; children: React.ReactNode; bg?: string }> = (
  { a, b, fi = 0.25, fo = 0.3, children, bg }) => {
  const t = useT();
  if (t < a || t > b + fo) return null;
  const o = Math.min(fi ? k(t, a, fi, "inOutCubic") : 1, t > b ? 1 - (t - b) / fo : 1);
  return <AbsoluteFill style={{ opacity: o, background: bg }}>{children}</AbsoluteFill>;
};

// --------------------------------------------------------------------------- shared pieces
const Defs: React.FC = () => (
  <svg width={0} height={0} style={{ position: "absolute" }}>
    <filter id="rough" x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={4} result="n" />
      <feDisplacementMap in="SourceGraphic" in2="n" scale={5} xChannelSelector="R" yChannelSelector="G" result="d" />
      <feComponentTransfer in="n" result="holes"><feFuncA type="discrete" tableValues="1 1 1 0.55 1 1 0.8 1" /></feComponentTransfer>
      <feComposite in="d" in2="holes" operator="in" />
    </filter>
    <filter id="glow"><feGaussianBlur stdDeviation="10" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
  </svg>
);

/** Rubber stamp that slams in at `at`. */
const Stamp: React.FC<{ text: string; at: number; color?: string; rot?: number; size?: number; x?: number; y?: number; sub?: string }> = (
  { text, at, color = TEAL, rot = -8, size = 96, x = 50, y = 50, sub }) => {
  const t = useT();
  if (t < at) return null;
  const p = k(t, at, 0.18, "outCubic");
  const s = 2.1 - 1.1 * p;
  return (
    <div style={{ position: "absolute", left: `${x}%`, top: `${y}%`, transform: `translate(-50%, -50%) rotate(${rot}deg) scale(${s})`,
                  opacity: Math.min(1, p * 1.6) * 0.92, filter: "url(#rough)", textAlign: "center" }}>
      <div style={{ border: `${size * 0.09}px solid ${color}`, borderRadius: 14, padding: `${size * 0.08}px ${size * 0.3}px`,
                    fontFamily: MONO, fontWeight: 700, fontSize: size, letterSpacing: "0.08em", color, lineHeight: 1.05,
                    whiteSpace: "nowrap", boxShadow: `inset 0 0 0 ${size * 0.04}px ${color}55` }}>
        {text}
        {sub && <div style={{ fontSize: size * 0.24, letterSpacing: "0.3em", marginTop: 4 }}>{sub}</div>}
      </div>
    </div>
  );
};

const Grain: React.FC<{ o?: number }> = ({ o = 0.12 }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: o, pointerEvents: "none" }}>
      <svg width={W} height={H}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={f % 61} />
          <feColorMatrix type="saturate" values="0" /></filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </AbsoluteFill>
  );
};

const Vignette: React.FC<{ v?: number }> = ({ v = 0.7 }) => (
  <AbsoluteFill style={{ pointerEvents: "none", background: `radial-gradient(ellipse 80% 65% at 50% 46%, transparent 50%, rgba(0,0,0,${v}) 100%)` }} />
);

/** Small mono label with a hairline, the "file system" of the film. */
const Label: React.FC<{ text: string; at: number; x?: number; y: number; color?: string; size?: number; align?: "left" | "center" }> = (
  { text, at, x = 90, y, color = BONE, size = 26, align = "left" }) => {
  const t = useT();
  const p = k(t, at, 0.5);
  return (
    <div style={{ position: "absolute", left: align === "center" ? 0 : x, right: align === "center" ? 0 : undefined, top: y,
                  textAlign: align, fontFamily: MONO, fontWeight: 500, fontSize: size, letterSpacing: "0.32em", color,
                  opacity: p, clipPath: `inset(0 ${100 - 100 * p}% 0 0)` }}>{text}</div>
  );
};

/** Serif line, letters rising out of a blur with a 1-frame stagger. */
const Rise: React.FC<{ text: string; at: number; size: number; color?: string; italic?: boolean; weight?: number; stagger?: number;
  style?: React.CSSProperties }> = ({ text, at, size, color = BONE, italic, weight = 700, stagger = 1, style }) => {
  const t = useT();
  return (
    <div style={{ lineHeight: 1.0, ...style }}>
      {text.split("").map((ch, i) => {
        const p = tween(t * 30, at * 30 + i * stagger, 14, 0, 1, "outExpo");
        return <span key={i} style={{ display: "inline-block", whiteSpace: "pre", fontFamily: italic ? SERIF_I : SERIF, fontWeight: weight,
                                      fontSize: size, color, letterSpacing: "-0.02em", opacity: p,
                                      transform: `translateY(${(1 - p) * 0.35 * size}px)`, filter: `blur(${(1 - p) * 10}px)` }}>{ch}</span>;
      })}
    </div>
  );
};

/** Typed text: characters appear from `at` at `cps`. */
const typed = (t: number, at: number, s: string, cps = 28) => (t < at ? "" : s.slice(0, Math.floor((t - at) * cps) + 1));

// --------------------------------------------------------------------------- act 1: the cough
const Waveform: React.FC<{ spikes: number[]; amp?: number; color?: string }> = ({ spikes, amp = 1, color = BONE }) => {
  const t = useT();
  const pts: string[] = [];
  for (let x = 0; x <= W; x += 6) {
    const tx = t - 2.2 + (x / W) * 2.4;               // the line scrolls: the right edge is "now"
    let a = 6 + 4 * rnd(Math.floor(tx * 60));
    for (const s of spikes) {
      const d1 = tx - s, d2 = tx - (s + 0.32);
      a += 330 * Math.exp(-(d1 * d1) / 0.004) + 230 * Math.exp(-(d2 * d2) / 0.003);
    }
    const y = Math.sin(tx * 90 + x) * a * amp * (0.6 + 0.4 * rnd(x + Math.floor(t * 30)));
    pts.push(`${x},${H / 2 + y}`);
  }
  return (
    <svg width={W} height={H} style={{ position: "absolute" }}>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth={4} strokeLinejoin="round" filter="url(#glow)" />
    </svg>
  );
};

const Cough: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Waveform spikes={[A.cough + 0.05]} />
      <Label text={`REC  ●  00:00:0${Math.floor(t)}`} at={0.3} y={300} color={RED} />
      <Label text="ALBUQUERQUE, NEW MEXICO" at={0.5} y={1500} align="center" color={GREY} size={24} />
    </AbsoluteFill>
  );
};

/** The case file card (paper). */
const Silhouette: React.FC<{ hat: number; size?: number; fill?: string }> = ({ hat, size = 300, fill = "#2a2620" }) => (
  <svg width={size} height={size * 1.15} viewBox="0 0 200 230">
    <ellipse cx="100" cy="92" rx="44" ry="54" fill={fill} />
    <path d="M20 230 C 26 170, 60 150, 100 150 C 140 150, 174 170, 180 230 Z" fill={fill} />
    <g stroke={PAPER} strokeWidth="3.2" fill="none" opacity={0.85}>
      <rect x="67" y="88" width="26" height="17" rx="5" /><rect x="107" y="88" width="26" height="17" rx="5" />
      <line x1="93" y1="95" x2="107" y2="95" />
    </g>
    <g style={{ transform: `translateY(${(1 - hat) * -60}px)`, opacity: hat }}>
      <path d="M38 62 L162 62 C 158 70, 42 70, 38 62 Z" fill={INK} />
      <path d="M62 62 L66 30 C 80 22, 120 22, 134 30 L138 62 Z" fill={INK} />
      <rect x="64" y="50" width="72" height="7" fill="#3a3530" />
    </g>
  </svg>
);

const CaseCard: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const inP = k(t, A.l2 - 0.1, 0.7);
  const field = (lab: string, val: string, at: number, y: number) => (
    <div style={{ position: "absolute", left: 60, right: 60, top: y, borderBottom: `2px solid ${PAPER_D}`, paddingBottom: 10 }}>
      <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: "0.3em", color: "#7a6d55" }}>{lab}</div>
      <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 44, color: "#1e1a14", marginTop: 6, minHeight: 52 }}>
        {typed(t, at, val)}<span style={{ opacity: t > at && t < at + 1.2 && Math.floor(t * 4) % 2 ? 1 : 0 }}>▌</span>
      </div>
    </div>
  );
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 30%, #3a2c1a 0%, ${INK} 75%)` }}>
      <div style={{ position: "absolute", left: 80, top: 330, width: 920, height: 1080, background: PAPER, borderRadius: 8,
                    boxShadow: "0 40px 120px #000c", transform: `translateY(${(1 - inP) * 900}px) rotate(${-1.5 + inP * 0.5}deg)`,
                    backgroundImage: `repeating-linear-gradient(0deg, transparent 0 62px, ${PAPER_D}66 62px 64px)` }}>
        <div style={{ position: "absolute", left: 60, top: 46, fontFamily: MONO, fontSize: 24, letterSpacing: "0.34em", color: RED }}>
          CASE FILE · No. 0050
        </div>
        <div style={{ position: "absolute", left: 60, top: 100, fontFamily: SERIF, fontWeight: 900, fontSize: 92, color: "#1e1a14",
                      letterSpacing: "-0.02em", lineHeight: 0.95 }}>WALTER H.<br />WHITE</div>
        <div style={{ position: "absolute", right: 60, top: 60, width: 250, height: 290, background: "#cdbf9f",
                      border: "3px solid #1e1a14", overflow: "hidden", display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
          <Silhouette hat={0} size={230} />
        </div>
        {field("AGE", "50", A.fifty, 420)}
        {field("OCCUPATION", "CHEMISTRY TEACHER", A.chem, 580)}
        {field("SECOND JOB", "CAR WASH", A.car - 0.15, 740)}
        <div style={{ position: "absolute", left: 60, bottom: 50, fontFamily: MONO, fontSize: 22, letterSpacing: "0.3em", color: "#7a6d55" }}>
          J.P. WYNNE HIGH SCHOOL
        </div>
      </div>
    </AbsoluteFill>
  );
};

const XRay: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const scan = ((t - A.l3) / 1.6) % 1;
  const ring = k(t, A.lung, 0.6, "inOutCubic");
  const lung = (flip: boolean) => (
    <path transform={flip ? "translate(1080,0) scale(-1,1)" : undefined}
          d="M505 520 C 420 500, 300 560, 270 720 C 240 880, 250 1060, 300 1180 C 340 1260, 430 1260, 480 1200 C 515 1150, 520 1000, 520 860 C 520 720, 525 600, 505 520 Z"
          fill="url(#lg)" stroke="#9fd2ff55" strokeWidth={3} />
  );
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, #0f2230 0%, #03070a 75%)" }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <defs>
          <radialGradient id="lg" cx="50%" cy="45%" r="60%"><stop offset="0%" stopColor="#b9dcff" stopOpacity={0.32} />
            <stop offset="100%" stopColor="#6aa8d8" stopOpacity={0.06} /></radialGradient>
        </defs>
        {Array.from({ length: 9 }, (_, i) => (
          <path key={i} d={`M300 ${600 + i * 72} Q 540 ${560 + i * 72} 780 ${600 + i * 72}`} stroke="#cfe6ff26" strokeWidth={10} fill="none" />
        ))}
        <rect x={528} y={480} width={24} height={820} rx={10} fill="#cfe6ff22" />
        {lung(false)}{lung(true)}
        <circle cx={700} cy={760} r={46} fill="#e9f4ff" opacity={0.25 + 0.2 * ring} filter="url(#glow)" />
        <circle cx={700} cy={760} r={110} fill="none" stroke={RED} strokeWidth={8} strokeDasharray={691}
                strokeDashoffset={691 * (1 - ring)} transform="rotate(-90 700 760)" />
        <rect x={0} y={420 + scan * 960} width={W} height={4} fill="#9fd2ff" opacity={0.35} />
      </svg>
      <Label text="PATIENT: WHITE, WALTER H.  ·  AGE 50" at={A.l3} y={300} color="#9fd2ff" size={24} />
      {t > A.lung && <Label text="LUNG CANCER" at={A.lung} x={600} y={900} color={RED} size={30} />}
      <Stamp text="INOPERABLE" at={A.inop} color={RED} rot={-10} size={104} y={64} />
    </AbsoluteFill>
  );
};

const Heisenberg: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const hot = k(t, A.heis - 0.3, 0.9, "inOutCubic");
  const strike = k(t, A.pride, 0.5, "inOutCubic");
  return (
    <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 42%, ${hot > 0 ? "#f7b84a" : "#3a2c1a"} 0%, #b4431c ${30 + 10 * hot}%, #1a0b06 78%)` }}>
      <AbsoluteFill style={{ background: INK, opacity: 0.72 * (1 - hot) }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 340, textAlign: "center" }}>
        <span style={{ position: "relative", fontFamily: MONO, fontWeight: 700, fontSize: 54, letterSpacing: "0.18em", color: hot > 0.5 ? INK : BONE,
                       opacity: 1 - 0.5 * hot }}>
          WALTER H. WHITE
          <span style={{ position: "absolute", left: -10, top: "52%", height: 7, width: `${(100 + 4) * strike}%`, background: RED }} />
        </span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 560, display: "flex", justifyContent: "center",
                    transform: `scale(${1 + 0.04 * k(t, A.l4, 4, "linear")})` }}>
        <Silhouette hat={k(t, A.heis - 0.15, 0.5, "outBack")} size={560} fill={INK} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1240, textAlign: "center" }}>
        <Rise text="HEISENBERG" at={A.heis} size={124} color={INK} weight={900} />
      </div>
      <Label text="TIMELINE A" at={A.l4} y={250} align="center" color={hot > 0.5 ? INK : AMBER} />
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- the turn
const WhatIf: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const split = k(t, A.l5end + 0.15, 1.2, "inOutCubic");
  const y0 = 1130;
  return (
    <AbsoluteFill style={{ background: INK }}>
      <AbsoluteFill style={{ opacity: keys(t, [[A.l5, 0], [A.just - 0.2, 0], [A.just, 1], [A.l5end + 0.2, 1], [A.l5end + 0.5, 0.35]]) }}>
        <Waveform spikes={[]} amp={0.6} color={TEAL} />
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 0, right: 0, top: 470, textAlign: "center" }}>
        <Rise text="What if" at={A.whatif - 0.05} size={170} italic weight={700} />
        <div style={{ height: 30 }} />
        <Rise text="it was just a cough?" at={A.just - 0.1} size={78} italic weight={400} color={TEAL} stagger={0.6} />
      </div>
      <svg width={W} height={H} style={{ position: "absolute", opacity: split > 0 ? 1 : 0 }}>
        <path d={`M 90 ${y0} L 420 ${y0}`} stroke={BONE} strokeWidth={6} />
        <path d={`M 420 ${y0} C 560 ${y0}, 600 ${y0 - 150}, 990 ${y0 - 160}`} stroke={AMBER} strokeWidth={6} fill="none"
              strokeDasharray={700} strokeDashoffset={700 * (1 - split)} />
        <path d={`M 420 ${y0} C 560 ${y0}, 600 ${y0 + 150}, 990 ${y0 + 160}`} stroke={TEAL} strokeWidth={6} fill="none"
              strokeDasharray={700} strokeDashoffset={700 * (1 - split)} />
        <circle cx={420} cy={y0} r={14} fill={BONE} />
      </svg>
      <Label text="A · CANCER → HEISENBERG" at={A.l5end + 0.6} x={500} y={y0 - 230} color={AMBER} size={24} />
      <Label text="B · JUST A COUGH" at={A.l5end + 0.9} x={560} y={y0 + 200} color={TEAL} size={24} />
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- act 2: timeline B dossier
const Clock: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const t0 = A.l5end + 0.8;                            // first tick (matches timeline.py)
  const n = Math.max(0, Math.floor(t - t0) + 1);
  const snap = t >= t0 ? tween((t - t0 - Math.floor(t - t0)) * 30, 0, 4, 0, 1, "outBack") : 0;
  const ang = (n - 1 + snap) * 6;
  return (
    <svg width={96} height={96} viewBox="0 0 100 100">
      <circle cx={50} cy={50} r={44} fill="none" stroke={BONE} strokeWidth={4} opacity={0.8} />
      {Array.from({ length: 12 }, (_, i) => (
        <line key={i} x1={50} y1={10} x2={50} y2={16} stroke={BONE} strokeWidth={3} transform={`rotate(${i * 30} 50 50)`} />
      ))}
      <line x1={50} y1={50} x2={50} y2={24} stroke={BONE} strokeWidth={4} transform="rotate(300 50 50)" />
      <line x1={50} y1={56} x2={50} y2={14} stroke={TEAL} strokeWidth={2.5} transform={`rotate(${ang} 50 50)`} />
      <circle cx={50} cy={50} r={4} fill={TEAL} />
    </svg>
  );
};

type CardSpec = { at: number; to: number; title: string; sub: string; was?: string; art?: React.ReactNode; stamps: React.ReactNode };

const Card: React.FC<CardSpec & { idx: number }> = ({ at, to, title, sub, was, art, stamps, idx }) => {
  const t = useT();
  if (t < at - 0.4 || t > to + 0.5) return null;
  const inP = k(t, at - 0.3, 0.6);
  const out = t > to ? k(t, to, 0.45, "inOutCubic") : 0;
  return (
    <div style={{ position: "absolute", left: 150, right: 60, top: 520, height: 900, opacity: inP * (1 - out),
                  transform: `translateY(${(1 - inP) * 120 - out * 160}px) rotate(${idx % 2 ? 0.8 : -0.8}deg)` }}>
      <div style={{ position: "absolute", inset: 0, background: "#E7E5DD", borderRadius: 10, boxShadow: "0 30px 90px #000a", overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 50, top: 40, fontFamily: MONO, fontSize: 22, letterSpacing: "0.32em", color: "#3f6f69" }}>
          TIMELINE B · FILE {String(idx + 1).padStart(2, "0")}
        </div>
        <div style={{ position: "absolute", left: 50, right: 40, top: 86, fontFamily: SERIF, fontWeight: 900, fontSize: 76, color: "#161b1c",
                      letterSpacing: "-0.02em", lineHeight: 0.98 }}>{title}</div>
        <div style={{ position: "absolute", left: 50, right: 40, top: 270, fontFamily: SERIF_I, fontSize: 36, color: "#4a5254" }}>{sub}</div>
        <div style={{ position: "absolute", left: 50, right: 50, top: 350, bottom: 140, borderRadius: 6, background: "#d6d4ca", overflow: "hidden" }}>{art}</div>
        {was && (
          <div style={{ position: "absolute", left: 50, right: 40, bottom: 52, fontFamily: MONO, fontSize: 26, letterSpacing: "0.12em", color: "#8a3a33" }}>
            <span style={{ position: "relative" }}>TIMELINE A: {was}
              <span style={{ position: "absolute", left: -6, right: -6, top: "50%", height: 4, background: RED,
                             transform: `scaleX(${k(t, at + 0.5, 0.5, "inOutCubic")})`, transformOrigin: "left" }} />
            </span>
          </div>
        )}
        {stamps}
      </div>
    </div>
  );
};

const Window: React.FC = () => {
  const t = useT();
  return (
    <svg width="100%" height="100%" viewBox="0 0 770 410">
      <rect width={770} height={410} fill="#b8c4c2" />
      <rect x={250} y={50} width={270} height={330} fill="#25343a" stroke="#f1efe7" strokeWidth={16} />
      <line x1={385} y1={50} x2={385} y2={380} stroke="#f1efe7" strokeWidth={10} />
      <path d={`M 258 58 Q ${300 + 12 * Math.sin(t * 2)} 220 270 372 L 258 372 Z`} fill="#c9b48a" opacity={0.9} />
      <text x={385} y={232} textAnchor="middle" fill="#f1efe7" opacity={0.5} fontFamily={MONO} fontSize={22} letterSpacing={4}>NOBODY</text>
    </svg>
  );
};

const Plane: React.FC<{ at: number }> = ({ at }) => {
  const t = useT();
  const p = k(t, at - 0.4, 3.2, "inOutCubic");
  const x = -80 + p * 930, y = 290 - Math.sin(p * Math.PI) * 140 + p * 40;
  return (
    <svg width="100%" height="100%" viewBox="0 0 770 410">
      <defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#6fa3b8" /><stop offset="100%" stopColor="#e9d7b5" /></linearGradient></defs>
      <rect width={770} height={410} fill="url(#sky)" />
      <path d="M0 360 L120 330 L210 350 L330 310 L460 345 L600 300 L770 340 L770 410 L0 410 Z" fill="#a8774f" />
      <path d={`M -80 290 Q 385 ${290 - 280} 850 330`} fill="none" stroke="#ffffff" strokeWidth={3} strokeDasharray="10 12" opacity={0.7} />
      <g transform={`translate(${x} ${y}) rotate(${-14 + 30 * p})`}>
        <path d="M-40 0 L40 -4 L50 0 L40 4 Z" fill="#f4f4f4" />
        <path d="M0 -2 L-12 -30 L-4 -30 L14 -2 Z M0 2 L-12 30 L-4 30 L14 2 Z" fill="#e2e2e2" />
        <path d="M-36 -2 L-46 -14 L-40 -14 L-30 -2 Z" fill="#e2e2e2" />
      </g>
    </svg>
  );
};

const Grill: React.FC = () => {
  const t = useT();
  return (
    <svg width="100%" height="100%" viewBox="0 0 770 410">
      <rect width={770} height={410} fill="#c7b79a" />
      {[0, 1, 2].map((i) => (
        <path key={i} d={`M ${330 + i * 50} 200 C ${310 + i * 50 + 20 * Math.sin(t * 2 + i)} 150, ${360 + i * 50} 110, ${340 + i * 50 + 15 * Math.sin(t * 1.5 + i)} 50`}
              stroke="#ffffff" strokeWidth={10} fill="none" strokeLinecap="round" opacity={0.35 + 0.2 * Math.sin(t * 3 + i)} />
      ))}
      <path d="M250 210 L520 210 C 520 300, 250 300, 250 210 Z" fill="#2b2b2b" />
      <rect x={240} y={200} width={290} height={12} rx={6} fill="#444" />
      <line x1={300} y1={280} x2={270} y2={390} stroke="#2b2b2b" strokeWidth={10} />
      <line x1={470} y1={280} x2={500} y2={390} stroke="#2b2b2b" strokeWidth={10} />
    </svg>
  );
};

const Papers: React.FC<{ at: number }> = ({ at }) => {
  const t = useT();
  return (
    <svg width="100%" height="100%" viewBox="0 0 770 410">
      <rect width={770} height={410} fill="#cfd3cf" />
      {[0, 1, 2, 3].map((i) => (
        <g key={i} transform={`translate(${200 + i * 8} ${70 - i * 10}) rotate(${-4 + i * 2.5})`}>
          <rect width={360} height={300} fill="#fbfaf4" stroke="#b9b9b0" />
          {Array.from({ length: 8 }, (_, j) => <line key={j} x1={30} x2={330} y1={50 + j * 30} y2={50 + j * 30} stroke="#c9d6e8" strokeWidth={2} />)}
        </g>
      ))}
      <path d="M260 160 L290 190 L350 120" stroke={RED} strokeWidth={9} fill="none" strokeLinecap="round" strokeLinejoin="round"
            strokeDasharray={170} strokeDashoffset={170 * (1 - k(t, at, 0.35, "inOutCubic"))} />
      <path d="M260 240 L290 270 L350 200" stroke={RED} strokeWidth={9} fill="none" strokeLinecap="round" strokeLinejoin="round"
            strokeDasharray={170} strokeDashoffset={170 * (1 - k(t, at + 0.5, 0.35, "inOutCubic"))} />
      <text x={470} y={210} fill={RED} fontFamily={SERIF_I} fontSize={72} opacity={k(t, at + 1, 0.4)}>C+</text>
    </svg>
  );
};

const RideAlong: React.FC = () => (
  <svg width="100%" height="100%" viewBox="0 0 770 410">
    <rect width={770} height={410} fill="#c9cfcf" />
    <g transform="translate(205 70)">
      <rect width={360} height={270} rx={10} fill="#fbfaf4" stroke="#9aa3a3" strokeWidth={3} />
      <rect width={360} height={58} rx={10} fill="#3f6f69" />
      <text x={180} y={40} textAnchor="middle" fill="#fff" fontFamily={MONO} fontSize={26} letterSpacing={6}>CALENDAR</text>
      {Array.from({ length: 15 }, (_, i) => (
        <rect key={i} x={20 + (i % 5) * 66} y={78 + Math.floor(i / 5) * 62} width={56} height={50} fill={i === 7 ? "#e7c7a0" : "#eceae2"} />
      ))}
      <text x={180} y={232} textAnchor="middle" fill="#6b4b2a" fontFamily={MONO} fontSize={15} letterSpacing={2}>RIDE-ALONG</text>
    </g>
  </svg>
);

const Dossier: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const cards: CardSpec[] = [
    { at: A.l6, to: A.l7 - 0.25, title: "The ride-along", sub: "with his brother-in-law, Hank", was: "WALT SEES THE BUST", art: <RideAlong />,
      stamps: <Stamp text="CANCELLED" at={A.ride + 0.25} color={RED} rot={-9} size={84} y={60} /> },
    { at: A.l7, to: A.l8 - 0.25, title: "Jesse Pinkman", sub: "former student, out the window", was: "PARTNERS", art: <Window />,
      stamps: <Stamp text="NEVER MET" at={A.window} color="#3f6f69" rot={7} size={84} y={60} /> },
    { at: A.l8, to: A.l9 - 0.25, title: "Jesse Pinkman", sub: "keeps cooking small", was: "HELD CAPTIVE",
      art: <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(135deg, #d6d4ca 0 22px, #cfcdc2 22px 44px)" }} />,
      stamps: <>
        <Stamp text="ARRESTED?" at={A.caught - 0.05} color="#6f7779" rot={-5} size={58} x={34} y={44} />
        <Stamp text="ALIVE*" at={A.lives} color="#2f8c80" rot={-8} size={104} x={60} y={64} sub="*PROBABLY" />
      </> },
    { at: A.l9, to: A.plane - 0.45, title: "Jane Margolis", sub: "wakes up", was: "OVERDOSE",
      art: <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, #f0d9a8, #e7b97f)" }} />,
      stamps: <Stamp text="ALIVE" at={A.jane + 0.45} color="#2f8c80" rot={-7} size={110} y={58} /> },
    { at: A.plane - 0.3, to: A.l10 - 0.25, title: "Wayfarer 515", sub: "over Albuquerque", was: "MID-AIR COLLISION", art: <Plane at={A.plane} />,
      stamps: <Stamp text="LANDED" at={A.plane + 0.25} color="#2f8c80" rot={6} size={104} y={58} /> },
    { at: A.l10, to: A.l11 - 0.25, title: "Hank Schrader", sub: "never chases Heisenberg", was: "KILLED IN THE DESERT", art: <Grill />,
      stamps: <Stamp text="RETIRED" at={A.retires + 0.05} color="#2f8c80" rot={-6} size={104} y={58} /> },
    { at: A.l11, to: A.l12 - 0.2, title: "Walter White", sub: "keeps grading papers", was: "HEISENBERG", art: <Papers at={A.grading} />,
      stamps: <Stamp text="STILL TEACHING" at={A.swallow} color="#6f7779" rot={-4} size={62} y={58} /> },
  ];
  const lineP = k(t, A.l6 - 0.6, 1.2, "inOutCubic");
  const idx = cards.reduce((m, c, i) => (t >= c.at - 0.3 ? i : m), 0);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 30%, #26353a 0%, ${SLATE} 55%, #0c1113 100%)` }}>
      <div style={{ position: "absolute", left: 90, top: 300, width: 6, height: 1250 * lineP, background: TEAL, borderRadius: 3 }} />
      {cards.map((c, i) => (
        <div key={i} style={{ position: "absolute", left: 79, top: 560 + i * 130, width: 28, height: 28, borderRadius: 14,
                              border: `4px solid ${TEAL}`, background: i <= idx ? TEAL : SLATE, opacity: lineP,
                              transform: `scale(${i === idx ? 1 + 0.4 * (1 - k(t, c.at - 0.3, 0.5)) : 1})` }} />
      ))}
      <div style={{ position: "absolute", left: 150, top: 300, display: "flex", alignItems: "center", gap: 26 }}>
        <Clock A={A} />
        <div>
          <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 30, letterSpacing: "0.3em", color: TEAL }}>TIMELINE B</div>
          <div style={{ fontFamily: SERIF_I, fontSize: 34, color: BONE, opacity: 0.8 }}>just a cough</div>
        </div>
      </div>
      {cards.map((c, i) => <Card key={i} {...c} idx={i} />)}
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- act 3: the twist
const Twist: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const kick = t >= A.heis2;
  const flash = kick ? 1 - k(t, A.heis2, 0.6, "outCubic") : 0;
  return (
    <AbsoluteFill style={{ background: kick ? `radial-gradient(circle at 50% 50%, #3a1a0c 0%, ${INK} 70%)` : INK }}>
      <div style={{ position: "absolute", left: 80, right: 80, top: 520 }}>
        <Rise text="The cancer" at={A.l12 + 0.05} size={110} italic weight={400} stagger={0.7} />
        <Rise text="didn't create" at={A.cancer12 + 0.25} size={110} italic weight={400} stagger={0.7} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 900, textAlign: "center",
                    transform: `scale(${kick ? 1 + 0.25 * flash : 1})` }}>
        <Rise text="HEISENBERG." at={A.heis2 - 0.05} size={124} color={AMBER} weight={900} stagger={0.5} />
      </div>
      <AbsoluteFill style={{ background: AMBER, opacity: 0.55 * flash, mixBlendMode: "screen" }} />
    </AbsoluteFill>
  );
};

const GrayMatter: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const grow = k(t, A.billions - 0.6, 1.5, "inOutExpo");
  const v = Math.round(5000 * Math.pow(400000, grow));
  const shown = grow > 0.98 ? "BILLIONS" : "$" + v.toLocaleString("en-US");
  const base = 1290;
  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, #1a0f08 0%, ${INK} 100%)` }}>
      <Label text="GRAY MATTER TECHNOLOGIES" at={A.l13} y={280} align="center" color={AMBER} size={30} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 340, textAlign: "center", fontFamily: SERIF_I, fontSize: 40, color: BONE, opacity: k(t, A.l13 + 0.3) }}>
        co-founded by Walter White
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 440, textAlign: "center", fontFamily: grow > 0.98 ? SERIF : MONO, fontWeight: grow > 0.98 ? 900 : 700,
                    fontSize: grow > 0.98 ? 150 : 96, color: AMBER, opacity: grow > 0.02 ? 1 : 0,
                    transform: `scale(${grow > 0.98 ? tween(t * 30, (A.billions + 0.9) * 30, 10, 1.12, 1) : 1})`,
                    textShadow: `0 0 50px ${AMBER}66` }}>{shown}</div>
      {/* Walt's share */}
      <div style={{ position: "absolute", left: 170, width: 260, bottom: H - base, height: 14 * k(t, A.five - 0.2, 0.5), background: BONE }} />
      <div style={{ position: "absolute", left: 130, width: 340, top: base + 30, textAlign: "center", fontFamily: MONO, fontSize: 24, letterSpacing: "0.22em", color: GREY }}>
        WALT'S SHARE, SOLD
      </div>
      <div style={{ position: "absolute", left: 130, width: 340, top: base - 110, textAlign: "center", fontFamily: MONO, fontWeight: 700, fontSize: 58,
                    color: BONE, opacity: k(t, A.five - 0.1) }}>$5,000</div>
      {/* company */}
      <div style={{ position: "absolute", left: 650, width: 260, bottom: H - base, height: 14 + 600 * grow,
                    background: `linear-gradient(0deg, ${AMBER}, #ffd27a)`, boxShadow: `0 0 ${60 * grow}px ${AMBER}88` }} />
      <div style={{ position: "absolute", left: 600, width: 360, top: base + 30, textAlign: "center", fontFamily: MONO, fontSize: 24, letterSpacing: "0.22em", color: GREY }}>
        THE COMPANY, LATER
      </div>
      <div style={{ position: "absolute", left: 90, right: 90, top: base, height: 3, background: GREY }} />
    </AbsoluteFill>
  );
};

const Pride: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const fill = k(t, A.pride2, 1.4, "inOutCubic");
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, #2b1608 0%, ${INK} 70%)` }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 520, textAlign: "center", fontFamily: SERIF, fontWeight: 900, fontSize: 290,
                    letterSpacing: "-0.03em", color: "transparent", WebkitTextStroke: `4px ${AMBER}`,
                    backgroundImage: `linear-gradient(0deg, ${AMBER} ${fill * 100}%, transparent ${fill * 100}%)`,
                    WebkitBackgroundClip: "text", backgroundClip: "text", opacity: k(t, A.l14, 0.5) }}>PRIDE</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 860, textAlign: "center" }}>
        <Rise text="was always there." at={A.pride2 + 0.4} size={72} italic weight={400} stagger={0.6} />
      </div>
      <Stamp text="PERMISSION GRANTED" at={A.permission} color={RED} rot={-7} size={74} y={62} />
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- act 4: the long, quiet life
const Age: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const p = keys(t, [[A.lives15, 0], [A.eighty, 1]]);
  const e = p < 1 ? 1 - Math.pow(1 - p, 2.2) : 1;
  const age = 50 + Math.round(30 * e);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, #233033 0%, ${SLATE} 50%, #0b0f10 100%)` }}>
      <Label text="TIMELINE B · WALTER WHITE" at={A.l15} y={300} align="center" color={TEAL} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 560, textAlign: "center", fontFamily: MONO, fontSize: 34, letterSpacing: "0.4em", color: GREY }}>AGE</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 600, textAlign: "center", fontFamily: SERIF, fontWeight: 900, fontSize: 420,
                    color: BONE, letterSpacing: "-0.04em", lineHeight: 1 }}>{age}</div>
      <svg width={W} height={200} style={{ position: "absolute", top: 1150 }}>
        {Array.from({ length: 31 }, (_, i) => (
          <line key={i} x1={120 + i * 28} x2={120 + i * 28} y1={i % 5 ? 70 : 50} y2={110} stroke={i <= age - 50 ? TEAL : "#3d4a4d"} strokeWidth={4} />
        ))}
        <text x={120} y={160} fill={GREY} fontFamily={MONO} fontSize={24}>50</text>
        <text x={960} y={160} fill={GREY} fontFamily={MONO} fontSize={24} textAnchor="end">80</text>
      </svg>
    </AbsoluteFill>
  );
};

const Forgotten: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const word = (w: string, at: number, i: number, fadeOut = false) => {
    const p = k(t, at - 0.05, 0.5);
    const gone = fadeOut ? keys(t, [[A.l16end + 0.2, 0], [A.l17 - 0.1, 1]]) : 0;
    return (
      <div key={w} style={{ fontFamily: SERIF_I, fontSize: 120, color: i === 2 ? GREY : BONE, opacity: p * (1 - gone),
                            filter: `blur(${(1 - p) * 8 + gone * 14}px)`, letterSpacing: `${-0.02 + gone * 0.2}em`,
                            transform: `translateY(${(1 - p) * 30}px)`, margin: "18px 0" }}>{w}</div>
    );
  };
  return (
    <AbsoluteFill style={{ background: "#121516", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", marginTop: -120 }}>
        {word("Safe.", A.safe, 0)}{word("Respected.", A.respected, 1)}{word("Forgotten.", A.forgotten, 2, true)}
      </div>
    </AbsoluteFill>
  );
};

const Quote: React.FC<{ A: Record<string, number>; line: Line }> = ({ A, line }) => {
  const t = useT();
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Label text="TIMELINE A · THE LAST DAY" at={A.l17 + 0.1} y={330} align="center" color={AMBER} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 400, textAlign: "center", fontFamily: SERIF_I, fontSize: 44, color: GREY,
                    opacity: k(t, A.l17 + 0.3, 0.6) * (1 - k(t, A.l18 - 0.2, 0.4)) }}>he finally admitted it</div>
      <div style={{ position: "absolute", left: 90, right: 90, top: 520, fontFamily: SERIF, fontSize: 84, lineHeight: 1.18, color: BONE }}>
        <span style={{ fontFamily: SERIF, fontSize: 180, color: AMBER, position: "absolute", left: -20, top: -110, opacity: k(t, A.l18 - 0.2) }}>“</span>
        {line.words.map(([a, , w], i) => {
          const p = k(t, a - 0.04, 0.35);
          const last = i === line.words.length - 1;
          const clean = w.replace(/\.\.\.$/, "…");
          return (
            <span key={i} style={{ display: "inline-block", marginRight: "0.24em", opacity: 0.08 + 0.92 * p, transform: `translateY(${(1 - p) * 14}px)`,
                                   color: last ? AMBER : BONE, fontStyle: last ? "italic" : "normal", fontWeight: last ? 700 : 400,
                                   textShadow: last && p > 0.5 ? `0 0 40px ${AMBER}aa` : undefined }}>{clean}</span>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 90, top: 1340, fontFamily: MONO, fontSize: 24, letterSpacing: "0.26em", color: GREY,
                    opacity: k(t, A.l18end - 0.2, 0.6) }}>— WALTER WHITE, “FELINA”</div>
    </AbsoluteFill>
  );
};

const TwoLines: React.FC<{ A: Record<string, number> }> = ({ A }) => {
  const t = useT();
  const x0 = 120, x1 = 960, span = x1 - x0;
  const ax = x0 + span * (2 / 30);
  const bP = k(t, A.l19 + 0.3, Math.max(0.6, A.thirty + 0.9 - A.l19), "inOutCubic");
  const glow = k(t, A.alive2, 0.6);
  const dim = k(t, A.never, 0.6);
  const endCard = k(t, A.l20end + 0.6, 0.8, "inOutCubic");
  const yA = 760, yB = 1040;
  return (
    <AbsoluteFill style={{ background: INK }}>
      <div style={{ opacity: 1 - 0.75 * endCard, transform: `translateY(${-160 * endCard}px)` }}>
        <svg width={W} height={H} style={{ position: "absolute" }}>
          <line x1={x0} x2={x1} y1={1250} y2={1250} stroke="#2c2c2c" strokeWidth={3} />
          {[50, 60, 70, 80].map((a) => (
            <g key={a}><line x1={x0 + span * (a - 50) / 30} x2={x0 + span * (a - 50) / 30} y1={1240} y2={1262} stroke={GREY} strokeWidth={3} />
              <text x={x0 + span * (a - 50) / 30} y={1300} fill={GREY} fontFamily={MONO} fontSize={24} textAnchor="middle">{a}</text></g>
          ))}
          <line x1={x0} x2={ax} y1={yA} y2={yA} stroke={AMBER} strokeWidth={14 + 6 * glow} strokeLinecap="round"
                style={{ filter: `drop-shadow(0 0 ${12 + 40 * glow}px ${AMBER})` }} opacity={k(t, A.l19, 0.5)} />
          <circle cx={ax} cy={yA} r={14 + 8 * glow} fill="#fff4d8" opacity={k(t, A.l19, 0.5)} style={{ filter: `drop-shadow(0 0 ${30 * glow}px ${AMBER})` }} />
          <line x1={x0} x2={x0 + span * bP} y1={yB} y2={yB} stroke={GREY} strokeWidth={10} strokeLinecap="round" opacity={1 - 0.55 * dim} />
        </svg>
        <div style={{ position: "absolute", left: x0, top: yA - 110, fontFamily: MONO, fontWeight: 700, fontSize: 28, letterSpacing: "0.2em", color: AMBER,
                      opacity: k(t, A.l19 + 0.2) }}>A · CANCER</div>
        <div style={{ position: "absolute", left: ax + 40, top: yA - 26, fontFamily: SERIF_I, fontSize: 46, color: AMBER, opacity: k(t, A.l19 + 0.4) }}>2 years</div>
        <div style={{ position: "absolute", left: x0, top: yB - 110, fontFamily: MONO, fontWeight: 700, fontSize: 28, letterSpacing: "0.2em", color: GREY,
                      opacity: k(t, A.l19 + 0.5) }}>B · JUST A COUGH</div>
        <div style={{ position: "absolute", right: 120, top: yB + 40, fontFamily: SERIF_I, fontSize: 46, color: GREY, opacity: k(t, A.thirty) }}>30 years</div>
      </div>
      {/* end card */}
      <div style={{ position: "absolute", left: 80, right: 80, top: 1050, textAlign: "center", opacity: endCard, transform: `translateY(${(1 - endCard) * 40}px)` }}>
        <div style={{ fontFamily: MONO, fontSize: 26, letterSpacing: "0.32em", color: GREY }}>WHAT IF WALTER WHITE NEVER HAD CANCER?</div>
        <div style={{ fontFamily: SERIF, fontWeight: 900, fontSize: 96, color: BONE, marginTop: 34, lineHeight: 1.02, letterSpacing: "-0.02em" }}>
          Which life would <span style={{ fontFamily: SERIF_I, color: AMBER }}>you</span> choose?</div>
        <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 34, letterSpacing: "0.2em", color: BONE, marginTop: 40 }}>
          <span style={{ color: AMBER }}>A</span> or <span style={{ color: TEAL }}>B</span> · comment below</div>
      </div>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- captions
/** Word-lit subtitles in phrase chunks. Off for the first 4.5 s and wherever the words are already the picture. */
const Captions: React.FC<{ lines: Line[]; skip: number[] }> = ({ lines, skip }) => {
  const t = useT();
  if (t < 4.5) return null;
  const li = lines.findIndex((l) => t >= l.start - 0.05 && t <= l.start + l.dur + 0.35);
  if (li < 0 || skip.includes(li)) return null;
  const ws = lines[li].words;
  const chunks: Word[][] = [];
  let cur: Word[] = [];
  ws.forEach((w, i) => {
    cur.push(w);
    if (cur.length >= 4 || /[.,?!]$/.test(w[2]) || i === ws.length - 1) { chunks.push(cur); cur = []; }
  });
  const ch = chunks.find((c, i) => t < (chunks[i + 1]?.[0][0] ?? Infinity)) ?? chunks[chunks.length - 1];
  if (t < ch[0][0] - 0.05) return null;
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: 1440, textAlign: "center" }}>
      {ch.map(([a, , w], i) => {
        const on = t >= a - 0.03;
        return (
          <span key={i} style={{ display: "inline-block", margin: "0 0.16em", fontFamily: SANS, fontWeight: 800, fontSize: 64,
                                 color: on ? (/\d|Heisenberg|cancer/i.test(w) ? AMBER : "#FFFFFF") : "#FFFFFF66",
                                 textShadow: "0 4px 24px #000, 0 0 3px #000", transform: `scale(${on ? 1 : 0.96})` }}>{w.replace(/\.\.\.$/, "…")}</span>
        );
      })}
    </div>
  );
};

// --------------------------------------------------------------------------- film
export const WhatIfWalter: React.FC<WalterProps> = (p) => {
  const t = useT();
  const A = p.A;
  if (!A) return <AbsoluteFill style={{ background: INK }} />;
  // camera shake on every stamp / impact
  const hits = [A.inop, A.ride + 0.25, A.lives, A.jane + 0.45, A.plane + 0.25, A.retires + 0.05, A.heis2, A.permission];
  let sh = 0;
  for (const h of hits) if (t >= h && t < h + 0.3) sh = Math.max(sh, 1 - (t - h) / 0.3);
  const sx = (rnd(Math.floor(t * 30)) - 0.5) * 22 * sh, sy = (rnd(Math.floor(t * 30) + 9) - 0.5) * 22 * sh;
  // rewind tear before "But what if"
  const rw = keys(t, [[A.l5 - 0.8, 0], [A.l5 - 0.6, 1], [A.l5 - 0.1, 1], [A.l5 + 0.05, 0]]);
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Defs />
      <AbsoluteFill style={{ transform: `translate(${sx}px, ${sy}px) scale(1.02)`, filter: rw > 0 ? `blur(${rw * 1.5}px) hue-rotate(${rw * 20}deg)` : undefined }}>
        <Scene a={0} b={A.l2 - 0.2} fi={0}><Cough A={A} /></Scene>
        <Scene a={A.l2 - 0.2} b={A.l3 - 0.15}><CaseCard A={A} /></Scene>
        <Scene a={A.l3 - 0.15} b={A.l4 - 0.15} fi={0.1}><XRay A={A} /></Scene>
        <Scene a={A.l4 - 0.15} b={A.l5 - 0.1} fo={0.05}><Heisenberg A={A} /></Scene>
        <Scene a={A.l5 - 0.1} b={A.l6 - 0.3} fi={0}><WhatIf A={A} /></Scene>
        <Scene a={A.l6 - 0.6} b={A.l12 - 0.15} fi={0.5} fo={0.1}><Dossier A={A} /></Scene>
        <Scene a={A.l12 - 0.15} b={A.l13 - 0.15} fi={0.1}><Twist A={A} /></Scene>
        <Scene a={A.l13 - 0.15} b={A.l14 - 0.2}><GrayMatter A={A} /></Scene>
        <Scene a={A.l14 - 0.2} b={A.l15 - 0.25}><Pride A={A} /></Scene>
        <Scene a={A.l15 - 0.25} b={A.l16 - 0.3}><Age A={A} /></Scene>
        <Scene a={A.l16 - 0.3} b={A.l17 - 0.1} fi={0.4}><Forgotten A={A} /></Scene>
        <Scene a={A.l17 - 0.1} b={A.l19 - 0.25} fi={0.3}><Quote A={A} line={p.lines[17]} /></Scene>
        <Scene a={A.l19 - 0.25} b={A.end + 1} fi={0.4}><TwoLines A={A} /></Scene>
      </AbsoluteFill>
      {/* VCR rewind overlay */}
      {rw > 0 && (
        <AbsoluteFill style={{ pointerEvents: "none" }}>
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} style={{ position: "absolute", left: 0, right: 0, top: rnd(i + Math.floor(t * 30) * 3) * H, height: 10 + rnd(i * 7) * 40,
                                  background: "#ffffff", opacity: 0.18 * rw, transform: `translateX(${(rnd(i + t) - 0.5) * 80}px)` }} />
          ))}
          <div style={{ position: "absolute", left: 90, top: 300, fontFamily: MONO, fontWeight: 700, fontSize: 52, color: BONE, opacity: rw,
                        textShadow: "3px 0 #f00, -3px 0 #0ff" }}>◀◀ REWIND</div>
        </AbsoluteFill>
      )}
      <Captions lines={p.lines} skip={[11, 15, 17]} />
      <Vignette v={0.55} />
      {/* film grain is added at mux time (ffmpeg noise): an SVG turbulence layer per frame renders ~10x slower */}
      {/* fade from black at the start, to black at the very end */}
      <AbsoluteFill style={{ background: "#000", opacity: Math.max(1 - k(t, 0, 0.5, "linear"), k(t, A.end - 0.6, 0.6, "linear")), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
