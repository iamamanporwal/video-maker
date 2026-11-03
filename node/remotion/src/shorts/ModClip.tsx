import { loadFont } from "@remotion/google-fonts/Montserrat";
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Img, interpolate, Loop, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import { tween } from "../lib/anim";

// Long-form → short clip: the creator's own footage in a 16:9 band with karaoke captions of what they say,
// then a white-studio Vi3W ending (sketch → spinning 3D model → Vi3W.in). 1080x1920, platform UI owns the
// bottom ~380 px and a ~150 px strip on the right.

const { fontFamily: MONT } = loadFont("normal", { weights: ["700", "800", "900"], subsets: ["latin"] });

type W = [number, number, string];
export type ModClipProps = {
  fps: number;
  durationInFrames: number;
  clip: { src: string; dur: number; cuts: number[]; focus?: number; zoom?: number };
  words: W[];                       // creator speech, frames on the clip timeline
  emphasis?: string[];              // words that get the highlight box
  headline?: { text: string; from: number };
  credit: string;
  cta: { from: number; dur: number; line: string; sub: string; button: string; sketch: string; glb: string; logo: string;
         reveal: number };
  vo?: { src: string; from: number }[];
  cues?: { src: string; from: number; volume: number }[];
};

const BAND = { top: 540, h: 780 };
const CAP_Y = 1430;
const INK = "#07080C";
const YEL = "#FFE14D";
const LIME = "#7CFF6B";
const stroke = (px: number) => ({ WebkitTextStroke: `${px}px ${INK}`, paintOrder: "stroke fill" as const });
const shadow = "0 6px 24px #000C, 0 0 3px #000";

/** "*word*" → accent. */
const Accent: React.FC<{ text: string; color: string }> = ({ text, color }) => (
  <>{text.split(/(\*[^*]+\*)/).filter(Boolean).map((t, i) =>
    t.startsWith("*") ? <span key={i} style={{ color }}>{t.slice(1, -1)}</span> : <span key={i}>{t}</span>)}</>
);

// --------------------------------------------------------------------------- clip section

const Footage: React.FC<{ p: ModClipProps }> = ({ p }) => {
  const f = useCurrentFrame();
  const { clip } = p;
  // Jump cuts alternate a 1.0 / 1.09 punch-in; a slow push runs underneath so nothing is ever static.
  const seg = clip.cuts.filter((c) => c <= f).length;
  const punch = seg % 2 === 1 ? 1.09 : 1;
  const settle = f < 12 ? tween(f, 0, 12, 1.06, 1, "outCubic") : 1;
  const z = (clip.zoom ?? 1.0) * punch * settle * (1 + 0.035 * (f / Math.max(1, clip.dur)));
  const fadeOut = interpolate(f, [clip.dur - 10, clip.dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pos = `${Math.round((clip.focus ?? 0.5) * 100)}% 50%`;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: "blur(44px) brightness(0.38) saturate(1.4)", transform: "scale(1.3)" }}>
        <OffthreadVideo src={staticFile(clip.src)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, #000A 0%, #0000 22%, #0000 70%, #000C 100%)" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: BAND.top, height: BAND.h, overflow: "hidden",
                    boxShadow: "0 30px 90px #000, 0 -20px 60px #000A" }}>
        <div style={{ width: "100%", height: "100%", transform: `scale(${z})`, transformOrigin: pos }}>
          <OffthreadVideo src={staticFile(clip.src)} volume={fadeOut}
                          style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Headline: React.FC<{ h: NonNullable<ModClipProps["headline"]> }> = ({ h }) => {
  const f = useCurrentFrame();
  if (f < h.from) return null;
  const k = tween(f, h.from, 12, 0.82, 1, "outBack");
  const o = tween(f, h.from, 8, 0, 1, "outCubic");
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: 175, height: 330, display: "flex", alignItems: "center",
                  justifyContent: "center", textAlign: "center", opacity: o, transform: `scale(${k})` }}>
      <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 70, lineHeight: 1.06, letterSpacing: "-0.03em",
                    textTransform: "uppercase", color: "#fff", textShadow: shadow, ...stroke(9) }}>
        <Accent text={h.text} color={YEL} />
      </div>
    </div>
  );
};

const Credit: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ position: "absolute", left: 30, top: BAND.top + 24, padding: "8px 18px 9px", borderRadius: 999,
                background: "#000000A6", border: "2px solid #ffffff2e", color: "#fff", fontFamily: MONT, fontWeight: 800,
                fontSize: 26, letterSpacing: "0.01em", display: "flex", alignItems: "center", gap: 10 }}>
    <span style={{ width: 14, height: 14, borderRadius: 99, background: "#FF3B30", display: "inline-block" }} />{text}
  </div>
);

type Chunk = { words: W[]; from: number; to: number };
const chunk = (words: W[], max = 3): Chunk[] => {
  const out: Chunk[] = [];
  let cur: W[] = [];
  const flush = () => { if (cur.length) out.push({ words: cur, from: cur[0][0], to: cur[cur.length - 1][1] + 6 }); cur = []; };
  words.forEach((w, i) => {
    const next = words[i + 1];
    cur.push(w);
    const len = cur.reduce((n, x) => n + x[2].length, 0);
    if (cur.length >= max || len > 16 || /[.,!?…:;]$/.test(w[2]) || (next && next[0] - w[1] > 9)) flush();
  });
  flush();
  for (let i = 0; i < out.length - 1; i++) out[i].to = Math.min(out[i].to, out[i + 1].from);
  return out;
};

const Captions: React.FC<{ words: W[]; emphasis: string[]; end: number }> = ({ words, emphasis, end }) => {
  const f = useCurrentFrame();
  const chunks = useMemo(() => chunk(words), [words]);
  const c = chunks.find((k) => f >= k.from && f < Math.min(k.to, end));
  if (!c) return null;
  const enter = tween(f, c.from, 4, 0, 1, "outCubic");
  const clean = (w: string) => w.replace(/[^\p{L}\p{N}'*]/gu, "").toLowerCase();
  return (
    <div style={{ position: "absolute", left: 60, right: 150, top: CAP_Y, transform: `translateY(-50%) scale(${0.88 + 0.12 * enter})`,
                  display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", columnGap: 30, rowGap: 6 }}>
      {c.words.map(([a, b, w], i) => {
        const on = f >= a && f < Math.max(b, a + 4);
        const pop = on ? 1 + 0.07 * (1 - tween(f, a, 6, 0, 1, "outCubic")) : 1;
        const em = emphasis.includes(clean(w));
        return (
          <span key={i} style={{ display: "inline-block", transform: `scale(${pop}) rotate(${em && on ? -2 : 0}deg)`,
                                 fontFamily: MONT, fontWeight: 900, fontSize: 82, lineHeight: 1.08, letterSpacing: "-0.025em",
                                 textTransform: "uppercase", color: em ? INK : on ? YEL : "#fff",
                                 background: em ? (on ? YEL : LIME) : "transparent", padding: em ? "0 14px 4px" : 0,
                                 borderRadius: em ? 14 : 0, textShadow: em ? "none" : shadow, ...(em ? {} : stroke(10)) }}>
            {w.replace(/[,.;:]$/, "")}
          </span>
        );
      })}
    </div>
  );
};

// --------------------------------------------------------------------------- white-studio ending

/** Pre-rendered transparent Blender turntable (tools/robot_tt.py), looped; pops in with a quick spin-scale. */
const Robot: React.FC<{ src: string; t0: number }> = ({ src, t0 }) => {
  const f = useCurrentFrame();
  const t = f - t0;
  const grow = tween(t, 0, 18, 0.25, 1, "outBack");
  const bob = 8 * Math.sin(t / 14);
  return (
    <div style={{ width: 900, height: 900, transform: `translateY(${bob}px) scale(${grow}) rotate(${(1 - Math.min(1, grow)) * -12}deg)` }}>
      <Loop durationInFrames={150}>
        <OffthreadVideo src={src} transparent muted style={{ width: 900, height: 900 }} />
      </Loop>
    </div>
  );
};

const Ending: React.FC<{ c: ModClipProps["cta"] }> = ({ c }) => {
  const f = useCurrentFrame();
  const R = c.reveal;                              // sketch → 3D pop
  const sketchIn = tween(f, 2, 14, 0.6, 1, "outBack");
  const scan = tween(f, 10, R - 14, 0, 1, "inOutCubic");
  const toCorner = tween(f, R, 16, 0, 1, "outExpo");
  const flash = f >= R ? 1 - tween(f, R, 10, 0, 1, "outCubic") : 0;
  const lock = tween(f, R + 10, 14, 0, 1, "outBack");
  const pulse = 1 + 0.035 * Math.sin((f / 30) * Math.PI * 2 * 1.1);
  // Sketch card: big + centred while it's scanned, then tucked bottom-left as "the input".
  const size = interpolate(toCorner, [0, 1], [640, 250]);
  const cx = interpolate(toCorner, [0, 1], [540, 190]);
  const cy = interpolate(toCorner, [0, 1], [860, 1080]);
  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 70% at 50% 45%, #ffffff 0%, #f3f4f7 60%, #e6e8ee 100%)" }}>
      {/* floor shadow */}
      <div style={{ position: "absolute", left: 360, width: 500, top: 1150, height: 70, borderRadius: "50%",
                    background: "radial-gradient(closest-side, #0000002e, #0000)", opacity: lock > 0 ? Math.min(1, lock) : 0 }} />
      {f >= R && <div style={{ position: "absolute", left: 160, top: 300, width: 900, height: 900 }}><Sequence from={R} layout="none"><Robot src={staticFile(c.glb)} t0={0} /></Sequence></div>}
      <div style={{ position: "absolute", left: cx - size / 2, top: cy - size / 2, width: size, height: size, borderRadius: 26,
                    overflow: "hidden", background: "#fff", transform: `rotate(${interpolate(toCorner, [0, 1], [-3, -6])}deg) scale(${sketchIn})`,
                    boxShadow: "0 30px 70px #0003, 0 0 0 5px #fff" }}>
        <Img src={staticFile(c.sketch)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        {f < R && <div style={{ position: "absolute", top: 0, bottom: 0, left: `${scan * 100}%`, width: 12, background: LIME,
                                boxShadow: `0 0 40px 16px ${LIME}AA`, opacity: scan > 0 && scan < 1 ? 1 : 0 }} />}
        <div style={{ position: "absolute", left: 14, top: 14, padding: "6px 14px", borderRadius: 999, background: INK, color: "#fff",
                      fontFamily: MONT, fontWeight: 800, fontSize: interpolate(toCorner, [0, 1], [30, 20]) }}>MY SKETCH ✏️</div>
      </div>
      {/* headline */}
      <div style={{ position: "absolute", left: 60, right: 60, top: 190, textAlign: "center", fontFamily: MONT, fontWeight: 900,
                    fontSize: 74, lineHeight: 1.04, letterSpacing: "-0.035em", textTransform: "uppercase", color: INK,
                    opacity: tween(f, 0, 10, 0, 1), transform: `translateY(${(1 - tween(f, 0, 14, 0, 1)) * 30}px)` }}>
        <Accent text={c.line} color="#16A34A" />
      </div>
      {/* lockup */}
      <div style={{ position: "absolute", left: 60, right: 60, top: 1215, display: "flex", flexDirection: "column", alignItems: "center",
                    gap: 18, opacity: Math.min(1, lock), transform: `translateY(${(1 - lock) * 40}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
          <div style={{ width: 96, height: 96, borderRadius: 26, background: "#000", overflow: "hidden", boxShadow: "0 10px 30px #0004" }}>
            <Img src={staticFile(c.logo)} style={{ width: "100%", height: "100%", transform: "scale(1.25)" }} />
          </div>
          <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 100, letterSpacing: "-0.045em", color: INK }}>Vi3W.in</div>
        </div>
        <div style={{ fontFamily: MONT, fontWeight: 700, fontSize: 38, color: "#3b3f4a", textAlign: "center", lineHeight: 1.15 }}>{c.sub}</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1452, display: "flex", justifyContent: "center", opacity: Math.min(1, lock) }}>
        <div style={{ padding: "22px 52px", borderRadius: 999, background: INK, color: LIME, fontFamily: MONT, fontWeight: 900, fontSize: 44,
                      transform: `scale(${lock * pulse})`, boxShadow: "0 18px 40px #0004", whiteSpace: "nowrap" }}>{c.button}</div>
      </div>
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.85 }} />
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- composition

export const ModClip: React.FC<ModClipProps> = (p) => {
  const f = useCurrentFrame();
  const wipe = interpolate(f, [p.cta.from - 7, p.cta.from, p.cta.from + 6], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Sequence durationInFrames={p.cta.from}>
        <Footage p={p} />
        <Credit text={p.credit} />
        {p.headline && <Headline h={p.headline} />}
        <Captions words={p.words} emphasis={p.emphasis ?? []} end={p.cta.from} />
      </Sequence>
      <Sequence from={p.cta.from} durationInFrames={p.cta.dur}><Ending c={p.cta} /></Sequence>
      {p.cues?.map((c, i) => <Sequence key={`c${i}`} from={c.from}><Audio src={staticFile(c.src)} volume={c.volume} /></Sequence>)}
      {p.vo?.map((v, i) => <Sequence key={`v${i}`} from={v.from}><Audio src={staticFile(v.src)} /></Sequence>)}
      <AbsoluteFill style={{ background: "#fff", opacity: wipe, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
