import { loadFont } from "@remotion/google-fonts/Montserrat";
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Img, interpolate, Loop, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import { tween } from "../lib/anim";

// GTA 6 dev facts: ~20 s verified fact over official 16:9 trailer shots (muted, karaoke VO captions, counter /
// list / stamp cards), then the shared Vi3W car plug: our sketch → Vi3W concept → 3D car → logo + Vi3W.in.
// 1080x1920; platform UI owns the bottom ~380 px.

const { fontFamily: MONT } = loadFont("normal", { weights: ["700", "800", "900"], subsets: ["latin"] });

type W = [number, number, string];
type Shot = { src: string; from: number; dur: number; at: number; x?: number; full?: boolean; glitch?: boolean };
type Counter = { kind: "counter"; from: number; dur: number; prefix?: string; value: number; suffix?: string; label: string;
                 rival?: { label: string; value: number }; note?: string };
type List = { kind: "list"; from: number; dur: number; title: string; items: { icon: string; text: string; at: number }[] };
type Stamp = { kind: "stamp"; from: number; dur: number; text: string; sub?: string; color?: string };
type Card = Counter | List | Stamp;
export type GtaFactProps = {
  fps: number;
  durationInFrames: number;
  tag: string;
  credit: string;
  shots: Shot[];
  cards: Card[];
  plug: { from: number; pop: number; end: number; sketch: string; render: string; model: string; logo: string; url: string; bait: string };
  words: W[];
  emphasis?: string[];
  vo?: { src: string; from: number }[];
  cues?: { src: string; from: number; volume: number; dur?: number }[];
};

const BAND = { top: 380, h: 1080 };
const CAP_Y = 1580;
const INK = "#07080C";
const YEL = "#FFE14D";
const PINK = "#FF3E9A";
const ORANGE = "#FF9A3C";
const LIME = "#7CFF6B";
const RED = "#FF2D3B";
const VICE = `linear-gradient(90deg, ${PINK}, ${ORANGE})`;
const stroke = (px: number) => ({ WebkitTextStroke: `${px}px ${INK}`, paintOrder: "stroke fill" as const });
const shadow = "0 6px 24px #000C, 0 0 3px #000";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const fmt = (n: number) => Math.round(n).toLocaleString("en-US");

// --------------------------------------------------------------------------- trailer footage

const ShotView: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame();
  const z = (1.03 + 0.06 * (f / Math.max(1, s.dur))) * (f < 5 ? tween(f, 0, 5, 1.1, 1, "outCubic") : 1);
  const jit = s.glitch && f < 10 ? Math.sin(f * 7.3) * 18 * (1 - f / 10) : 0;
  // 1920x1080 source; band mode shows it at native size (height 1080), `x` picks the 1080 px window.
  const scale = s.full ? 1920 / 1080 : 1;
  const w = 1920 * scale;
  const left = -((w - 1080) * (s.x ?? 0.5));
  const video = (style: React.CSSProperties, muted: boolean) => (
    <OffthreadVideo src={staticFile(s.src)} startFrom={s.at} muted={muted} volume={0} style={style} />
  );
  return (
    <AbsoluteFill>
      {!s.full && (
        <AbsoluteFill style={{ filter: "blur(40px) brightness(0.35) saturate(1.6)", transform: "scale(1.4)" }}>
          {video({ width: "100%", height: "100%", objectFit: "cover" }, true)}
        </AbsoluteFill>
      )}
      <div style={{ position: "absolute", left: 0, right: 0, top: s.full ? 0 : BAND.top, height: s.full ? 1920 : BAND.h, overflow: "hidden",
                    boxShadow: s.full ? "none" : "0 30px 90px #000, 0 -20px 60px #000A" }}>
        <div style={{ position: "absolute", left: left + jit, top: 0, width: w, height: 1080 * scale, transform: `scale(${z})`,
                      transformOrigin: `${-left + 540}px 50%` }}>
          {video({ width: w, height: 1080 * scale }, true)}
        </div>
        {s.glitch && f < 10 && (
          <AbsoluteFill style={{ background: `repeating-linear-gradient(0deg, #ffffff10 0 2px, transparent 2px 6px)`,
                                 boxShadow: `inset ${jit}px 0 0 ${RED}55`, mixBlendMode: "screen" }} />
        )}
      </div>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- cards

const Panel: React.FC<{ k: number; out: number; children: React.ReactNode }> = ({ k, out, children }) => (
  <div style={{ position: "absolute", left: 50, right: 50, top: 150, padding: "30px 38px 28px", borderRadius: 34,
                background: "linear-gradient(180deg, #120A1EF4, #0B0711E6)", border: `3px solid ${PINK}66`,
                boxShadow: `0 30px 80px #000C, 0 0 60px ${PINK}33`, opacity: out,
                transform: `scale(${0.8 + 0.2 * k}) translateY(${(1 - k) * -40}px)` }}>
    {children}
  </div>
);

const CounterCard: React.FC<{ c: Counter }> = ({ c }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 12, 0, 1, "outBack");
  const out = interpolate(f, [c.dur - 8, c.dur], [1, 0], clamp);
  const n = tween(f, 4, Math.min(40, c.dur - 16), 0, 1, "outCubic");
  const v = n * c.value;
  const beat = c.rival ? v > c.rival.value : n >= 1;
  const wMax = 900;
  return (
    <Panel k={k} out={out}>
      <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 30, color: "#C9B8D9", letterSpacing: "0.06em" }}>{c.label}</div>
      {c.rival && (
        <>
          <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{ width: (c.rival.value / c.value) * wMax * 0.78, height: 44, borderRadius: 12, background: "#7C7590" }} />
            <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 30, color: "#fff", whiteSpace: "nowrap" }}>{c.rival.label}</div>
          </div>
          <div style={{ marginTop: 14, width: Math.max(8, n * wMax * 0.78), height: 56, borderRadius: 14, background: VICE,
                        boxShadow: beat ? `0 0 40px ${PINK}AA` : "none" }} />
        </>
      )}
      <div style={{ marginTop: 10, fontFamily: MONT, fontWeight: 900, fontSize: 112, letterSpacing: "-0.04em", lineHeight: 1.05,
                    color: beat ? YEL : "#fff", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
        {c.prefix}{fmt(v)}{c.suffix}
      </div>
      {c.note && (
        <div style={{ marginTop: 8, display: "inline-block", fontFamily: MONT, fontWeight: 900, fontSize: 26, color: INK, background: YEL,
                      padding: "6px 14px", borderRadius: 10, opacity: tween(f, 36, 10, 0, 1) }}>{c.note}</div>
      )}
    </Panel>
  );
};

const ListCard: React.FC<{ c: List }> = ({ c }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 12, 0, 1, "outBack");
  const out = interpolate(f, [c.dur - 8, c.dur], [1, 0], clamp);
  return (
    <Panel k={k} out={out}>
      <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 30, color: "#C9B8D9", letterSpacing: "0.06em" }}>{c.title}</div>
      <div style={{ marginTop: 16, display: "flex", gap: 18, justifyContent: "space-between" }}>
        {c.items.map((it, i) => {
          const p = tween(f, it.at, 12, 0, 1, "outBack");
          return (
            <div key={i} style={{ flex: 1, padding: "18px 10px 16px", borderRadius: 22, background: "#ffffff12", border: "2px solid #ffffff22",
                                  textAlign: "center", opacity: Math.min(1, p), transform: `scale(${p}) rotate(${(1 - Math.min(1, p)) * 10}deg)` }}>
              <div style={{ fontSize: 96, lineHeight: 1.1 }}>{it.icon}</div>
              <div style={{ marginTop: 6, fontFamily: MONT, fontWeight: 900, fontSize: 32, color: "#fff" }}>{it.text}</div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
};

const StampCard: React.FC<{ c: Stamp }> = ({ c }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 8, 2.2, 1, "outCubic");
  const out = interpolate(f, [c.dur - 6, c.dur], [1, 0], clamp);
  const col = c.color ?? RED;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: Math.min(1, tween(f, 0, 4)) * out }}>
      <div style={{ marginTop: -220, transform: `rotate(-8deg) scale(${k})`, display: "flex", flexDirection: "column", alignItems: "center",
                    padding: "14px 40px 18px", border: `10px solid ${col}`, borderRadius: 24, background: "#0008",
                    boxShadow: `0 0 60px ${col}88, inset 0 0 40px ${col}44` }}>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 130, color: col, letterSpacing: "0.02em", lineHeight: 1 }}>{c.text}</div>
        {c.sub && <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 46, color: "#fff", marginTop: 6 }}>{c.sub}</div>}
      </div>
    </AbsoluteFill>
  );
};

const CardView: React.FC<{ c: Card }> = ({ c }) =>
  c.kind === "counter" ? <CounterCard c={c} /> : c.kind === "list" ? <ListCard c={c} /> : <StampCard c={c} />;

// --------------------------------------------------------------------------- Vi3W plug

const PlugView: React.FC<{ p: GtaFactProps["plug"]; dur: number }> = ({ p, dur }) => {
  const f = useCurrentFrame();
  const R = p.pop;
  const E = p.end;
  const draw = tween(f, 2, 22, 0, 1, "inOutCubic");             // sketch "draws" on left → right
  const sketchIn = tween(f, 0, 12, 0.7, 1, "outBack");
  const tuck = tween(f, R, 16, 0, 1, "outExpo");
  const flash = f >= R ? 1 - tween(f, R, 10, 0, 1, "outCubic") : 0;
  const grow = tween(f, R, 18, 0.3, 1, "outBack");
  const chip = tween(f, R + 10, 12, 0, 1, "outBack");
  const end = tween(f, E, 14, 0, 1, "outBack");
  const bob = 6 * Math.sin((f - R) / 16);
  const sw = interpolate(tuck, [0, 1], [980, 330]);
  const sx = interpolate(tuck, [0, 1], [50, 40]);
  const sy = interpolate(tuck, [0, 1], [620, 210]);
  const rw = 330;
  const rIn = tween(f, R + 6, 14, 0, 1, "outBack");
  const carUp = interpolate(end, [0, 1], [0, -90]);
  const top = 1 - tween(f, E, 10, 0, 1, "outCubic");
  return (
    <AbsoluteFill style={{ background: "radial-gradient(110% 70% at 50% 40%, #3A1450 0%, #170A24 55%, #07040C 100%)" }}>
      {/* sunset floor grid */}
      <div style={{ position: "absolute", left: -200, right: -200, top: 1150, height: 900, transform: "perspective(600px) rotateX(62deg)",
                    backgroundImage: `linear-gradient(${PINK}55 2px, transparent 2px), linear-gradient(90deg, ${PINK}55 2px, transparent 2px)`,
                    backgroundSize: "90px 90px", backgroundPosition: `0 ${(f * 3) % 90}px`, opacity: 0.6 }} />
      {/* 3D car */}
      {f >= R && (
        <div style={{ position: "absolute", left: 40, top: 560 + carUp, width: 1000, height: 776, borderRadius: 34, overflow: "hidden",
                      transform: `translateY(${bob}px) scale(${grow})`, boxShadow: `0 40px 100px #000C, 0 0 0 4px ${PINK}88, 0 0 80px ${PINK}55` }}>
          <Sequence from={R} layout="none">
            <Loop durationInFrames={180}>
              <OffthreadVideo src={staticFile(p.model)} muted startFrom={20} style={{ width: 1000, height: 776, objectFit: "cover", transform: "scale(1.12)" }} />
            </Loop>
          </Sequence>
          <div style={{ position: "absolute", right: 18, top: 18, padding: "8px 18px", borderRadius: 999, background: LIME, color: INK,
                        fontFamily: MONT, fontWeight: 900, fontSize: 30 }}>3D MODEL ✓</div>
        </div>
      )}
      {/* AI concept render */}
      {f >= R && (
        <div style={{ position: "absolute", right: 40, top: 210, width: rw, height: rw * 663 / 1177, borderRadius: 20, overflow: "hidden",
                      transform: `scale(${rIn}) rotate(${4}deg)`, opacity: Math.min(1, rIn) * top, boxShadow: "0 20px 50px #000C, 0 0 0 4px #fff" }}>
          <Img src={staticFile(p.render)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
      )}
      {f >= R && (
        <div style={{ position: "absolute", left: 395, top: 260, fontFamily: MONT, fontWeight: 900, fontSize: 80, color: YEL, opacity: Math.min(1, rIn) * top,
                      ...stroke(8) }}>→</div>
      )}
      {/* our sketch */}
      <div style={{ position: "absolute", left: sx, top: sy, width: sw, height: sw * 756 / 1310, borderRadius: 26, overflow: "hidden",
                    background: "#06070A", opacity: top, transform: `scale(${sketchIn}) rotate(${interpolate(tuck, [0, 1], [-2, -5])}deg)`,
                    boxShadow: `0 30px 70px #000C, 0 0 0 5px #fff` }}>
        <Img src={staticFile(p.sketch)} style={{ width: "100%", height: "100%", objectFit: "cover", clipPath: `inset(0 ${(1 - draw) * 100}% 0 0)` }} />
        <div style={{ position: "absolute", left: 14, top: 14, padding: "6px 14px", borderRadius: 999, background: YEL, color: INK,
                      fontFamily: MONT, fontWeight: 900, fontSize: interpolate(tuck, [0, 1], [34, 18]) }}>OUR SKETCH ✏️</div>
      </div>
      {/* made-with chip */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 1370 + carUp, display: "flex", justifyContent: "center",
                    transform: `scale(${chip})`, opacity: Math.min(1, chip) * (1 - Math.min(1, end)) }}>
        <div style={{ padding: "12px 28px", borderRadius: 999, background: INK, border: `3px solid ${LIME}`, color: LIME,
                      fontFamily: MONT, fontWeight: 900, fontSize: 40 }}>sketch → 3D with Vi3W ⚡</div>
      </div>
      {/* end card */}
      {f >= E && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 1290, display: "flex", alignItems: "center", justifyContent: "center", gap: 22,
                      transform: `scale(${end})`, opacity: Math.min(1, end) }}>
          <Img src={staticFile(p.logo)} style={{ width: 130, height: 130, borderRadius: "50%", boxShadow: `0 0 50px #4FA3FF88` }} />
          <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 110, color: "#fff", letterSpacing: "-0.03em", ...stroke(10) }}>{p.url}</div>
        </div>
      )}
      {f >= E + 10 && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 250, display: "flex", justifyContent: "center",
                      transform: `scale(${tween(f, E + 10, 12, 0, 1, "outBack")})` }}>
          <div style={{ maxWidth: 940, textAlign: "center", padding: "18px 32px", borderRadius: 24, background: VICE, color: "#fff", fontFamily: MONT, fontWeight: 900, fontSize: 56, lineHeight: 1.1,
                        ...stroke(6), boxShadow: "0 20px 50px #000A" }}>{p.bait}</div>
        </div>
      )}
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.85 }} />
      <AbsoluteFill style={{ background: "#000", opacity: interpolate(f, [dur - 8, dur], [0, 0.6], clamp) }} />
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- captions + chrome

type Chunk = { words: W[]; from: number; to: number };
const chunk = (words: W[], max = 3): Chunk[] => {
  const out: Chunk[] = [];
  let cur: W[] = [];
  const flush = () => { if (cur.length) out.push({ words: cur, from: cur[0][0], to: cur[cur.length - 1][1] + 8 }); cur = []; };
  words.forEach((w, i) => {
    const next = words[i + 1];
    cur.push(w);
    const len = cur.reduce((n, x) => n + x[2].length, 0);
    if (cur.length >= max || len > 15 || /[.,!?…:;]$/.test(w[2]) || (next && next[0] - w[1] > 9)) flush();
  });
  flush();
  for (let i = 0; i < out.length - 1; i++) out[i].to = Math.min(out[i].to, out[i + 1].from);
  return out;
};

const Captions: React.FC<{ words: W[]; emphasis: string[] }> = ({ words, emphasis }) => {
  const f = useCurrentFrame();
  const chunks = useMemo(() => chunk(words), [words]);
  const c = chunks.find((k) => f >= k.from && f < k.to);
  if (!c) return null;
  const enter = tween(f, c.from, 4, 0, 1, "outCubic");
  const clean = (w: string) => w.replace(/[^\p{L}\p{N}'*.$]/gu, "").replace(/\.+$/, "").toLowerCase();
  return (
    <div style={{ position: "absolute", left: 60, right: 140, top: CAP_Y, transform: `translateY(-50%) scale(${0.88 + 0.12 * enter})`,
                  display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", columnGap: 24, rowGap: 6 }}>
      {c.words.map(([a, b, w], i) => {
        const on = f >= a && f < Math.max(b, a + 4);
        const pop = on ? 1 + 0.08 * (1 - tween(f, a, 6, 0, 1, "outCubic")) : 1;
        const em = emphasis.includes(clean(w));
        return (
          <span key={i} style={{ display: "inline-block", transform: `scale(${pop}) rotate(${em && on ? -2 : 0}deg)`,
                                 fontFamily: MONT, fontWeight: 900, fontSize: 84, lineHeight: 1.08, letterSpacing: "-0.025em",
                                 textTransform: "uppercase", color: em ? "#fff" : on ? YEL : "#fff",
                                 background: em ? (on ? VICE : PINK) : "transparent", padding: em ? "0 14px 4px" : 0,
                                 borderRadius: em ? 14 : 0, textShadow: em ? "none" : shadow, ...(em ? stroke(6) : stroke(10)) }}>
            {w.replace(/[,;:…]+$/, "").replace(/\.+$/, "")}
          </span>
        );
      })}
    </div>
  );
};

const Pill: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ position: "absolute", left: 0, right: 0, top: 210, display: "flex", justifyContent: "center" }}>
    <div style={{ padding: "12px 30px 14px", borderRadius: 999, background: VICE, color: "#fff", fontFamily: MONT, fontWeight: 900, fontSize: 38,
                  letterSpacing: "0.02em", boxShadow: "0 10px 30px #0008", ...stroke(5) }}>{text}</div>
  </div>
);

const Credit: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ position: "absolute", left: 30, top: BAND.top + BAND.h - 64, padding: "7px 16px 8px", borderRadius: 999,
                background: "#000000A6", border: "2px solid #ffffff2e", color: "#fff", fontFamily: MONT, fontWeight: 800, fontSize: 24 }}>{text}</div>
);

// --------------------------------------------------------------------------- composition

export const GtaFact: React.FC<GtaFactProps> = (p) => {
  const f = useCurrentFrame();
  const cardOn = p.cards.some((c) => c.kind !== "stamp" && f >= c.from && f < c.from + c.dur);
  const plugDur = p.durationInFrames - p.plug.from;
  const wipe = interpolate(f, [p.plug.from - 5, p.plug.from, p.plug.from + 5], [0, 1, 0], clamp);
  return (
    <AbsoluteFill style={{ background: INK }}>
      {p.shots.map((s, i) => (
        <Sequence key={`s${i}`} from={s.from} durationInFrames={s.dur}><ShotView s={s} /></Sequence>
      ))}
      <Sequence durationInFrames={p.plug.from}><Credit text={p.credit} /></Sequence>
      {p.cards.map((c, i) => (
        <Sequence key={`k${i}`} from={c.from} durationInFrames={c.dur}><CardView c={c} /></Sequence>
      ))}
      <Sequence from={p.plug.from}><PlugView p={p.plug} dur={plugDur} /></Sequence>
      {!cardOn && f < p.plug.from && <Pill text={p.tag} />}
      <Captions words={p.words} emphasis={p.emphasis ?? []} />
      {p.cues?.map((c, i) => (
        <Sequence key={`c${i}`} from={c.from} durationInFrames={c.dur}><Audio src={staticFile(c.src)} volume={c.volume} /></Sequence>
      ))}
      {p.vo?.map((v, i) => <Sequence key={`v${i}`} from={v.from}><Audio src={staticFile(v.src)} /></Sequence>)}
      <AbsoluteFill style={{ background: PINK, opacity: wipe * 0.8, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
