import { loadFont } from "@remotion/google-fonts/Montserrat";
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, cancelRender, continueRender, delayRender, Img, interpolate, OffthreadVideo, Sequence, staticFile,
         useCurrentFrame } from "remotion";
import { hash, tween } from "../lib/anim";

// "Why did GTA 6 take 13 years?" — satirical mini-doc. Official Rockstar footage (muted) graded per act, GTA-style
// parody UI (year/money HUD, MISSION PASSED / WASTED / BUSTED, wanted stars, loading tips, phone texts), comic-panel
// chapter cards and pre-rendered Blender 3D metaphor shots. 1080x1920; platform UI owns the bottom ~380 px.
// All times are composition frames; Python (build.py) writes every prop from VO word times.

const { fontFamily: MONT } = loadFont("normal", { weights: ["700", "800", "900"], subsets: ["latin"] });
const PD = "Pricedown";
if (typeof document !== "undefined" && ![...(document.fonts as any)].some((f: FontFace) => f.family === PD)) {
  const h = delayRender("pricedown");
  new FontFace(PD, `url(${staticFile("fonts/pricedown.otf")})`).load()
    .then((f) => { (document.fonts as any).add(f); continueRender(h); }).catch((e) => cancelRender(e));
}

type W = [number, number, string];
type Grade = "none" | "warm" | "money" | "cold" | "bw" | "red" | "vice" | "vhs";
type Shot = { src: string; from: number; dur: number; at: number; x?: number; mode?: "full" | "band"; zoom?: number;
              grade?: Grade; speed?: number; glitch?: boolean; still?: boolean; flip?: boolean; credit?: boolean };
type Ov =
  | { kind: "chapter"; from: number; dur: number; n: string; title: string; color?: string }
  | { kind: "passed"; from: number; dur: number; title?: string; sub: string }
  | { kind: "wasted"; from: number; dur: number; text: string; color?: string; sub?: string }
  | { kind: "stars"; from: number; dur: number; n: number }
  | { kind: "tip"; from: number; dur: number; text: string }
  | { kind: "phone"; from: number; dur: number; who: string; msgs: { text: string; at: number; me?: boolean }[] }
  | { kind: "counter"; from: number; dur: number; prefix?: string; value: number; suffix?: string; label: string; note?: string }
  | { kind: "stamp"; from: number; dur: number; text: string; sub?: string; color?: string; rot?: number }
  | { kind: "stack"; from: number; dur: number; title: string; items: { a: string; b: string; at: number }[] }
  | { kind: "timeline"; from: number; dur: number; items: { year: string; text: string; at: number; color?: string }[] }
  | { kind: "cash"; from: number; dur: number; text: string }
  | { kind: "title"; from: number; dur: number; lines: string[]; sub?: string }
  | { kind: "bridge"; from: number; dur: number; sketch: string; model: string; pop: number }
  | { kind: "viewport"; from: number; dur: number; mode: string; tris?: [number, number]; objects?: [number, number]; rec?: boolean }
  | { kind: "pipeline"; from: number; dur: number; steps: { label: string; at: number }[] }
  | { kind: "keys"; from: number; dur: number; keys: number[] }
  | { kind: "console"; from: number; dur: number; lines: { text: string; at: number; warn?: boolean }[] };
export type Gta13Props = {
  fps: number;
  durationInFrames: number;
  shots: Shot[];
  overlays: Ov[];
  hud: { from: number; to: number; years: [number, number][]; cash: [number, number][] };
  credit: { text: string; to: number; perShot?: boolean };
  words: W[];
  captionsFrom: number;
  emphasis?: string[];
  vo?: { src: string; from: number; volume?: number }[];
  cues?: { src: string; from: number; volume: number; dur?: number }[];
};

const INK = "#07080C";
const YEL = "#FFE14D";
const GOLD = "#F5C542";
const PINK = "#FF3E9A";
const ORANGE = "#FF9A3C";
const RED = "#E8303A";
const GREEN = "#6FDB6A";
const VICE = `linear-gradient(90deg, ${PINK}, ${ORANGE})`;
const stroke = (px: number, c = INK) => ({ WebkitTextStroke: `${px}px ${c}`, paintOrder: "stroke fill" as const });
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const fmt = (n: number) => Math.round(n).toLocaleString("en-US");
const BAND = { top: 420, h: 1080 };

const GRADES: Record<Grade, string> = {
  none: "contrast(1.05) saturate(1.1)",
  warm: "sepia(0.35) saturate(1.25) contrast(1.08) brightness(1.03)",
  money: "saturate(1.45) contrast(1.12) hue-rotate(-8deg)",
  cold: "saturate(0.55) contrast(1.15) brightness(0.9) hue-rotate(12deg)",
  bw: "grayscale(1) contrast(1.25) brightness(0.95)",
  red: "grayscale(0.7) sepia(0.4) hue-rotate(-30deg) saturate(2.2) contrast(1.2) brightness(0.8)",
  vice: "saturate(1.55) contrast(1.1) brightness(1.05)",
  vhs: "saturate(0.8) contrast(1.2) blur(0.6px)",
};

// --------------------------------------------------------------------------- footage

const ShotView: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame();
  const z = (s.zoom ?? 1.04) + 0.07 * (f / Math.max(1, s.dur));
  const punch = f < 5 ? tween(f, 0, 5, 1.12, 1, "outCubic") : 1;
  const jit = s.glitch && f < 9 ? Math.sin(f * 7.3) * 26 * (1 - f / 9) : 0;
  const isImg = /\.(png|jpe?g|webp)$/i.test(s.src);
  const vert = /3d\//.test(s.src);                           // Blender shots are rendered 1080x1920
  const full = s.mode !== "band";
  const scale = vert ? 1 : full ? 1920 / 1080 : 1;
  const w = vert ? 1080 : 1920 * scale;
  const h = vert ? 1920 : 1080 * scale;
  const left = -((w - 1080) * (s.x ?? 0.5));
  const media = (style: React.CSSProperties) =>
    isImg ? <Img src={staticFile(s.src)} style={style} />
      : <OffthreadVideo src={staticFile(s.src)} startFrom={s.at} playbackRate={s.speed ?? 1} muted volume={0} style={style} />;
  const grade = GRADES[s.grade ?? "none"];
  return (
    <AbsoluteFill style={{ background: INK }}>
      {!full && (
        <AbsoluteFill style={{ filter: `blur(40px) brightness(0.35) saturate(1.6)`, transform: "scale(1.4)" }}>
          {media({ width: "100%", height: "100%", objectFit: "cover" })}
        </AbsoluteFill>
      )}
      <div style={{ position: "absolute", left: 0, right: 0, top: full ? 0 : BAND.top, height: full ? 1920 : BAND.h, overflow: "hidden",
                    boxShadow: full ? "none" : "0 30px 90px #000, 0 -20px 60px #000A" }}>
        <div style={{ position: "absolute", left: left + jit, top: full ? (1920 - h) / 2 : 0, width: w, height: h, filter: grade,
                      transform: `scale(${z * punch}) scaleX(${s.flip ? -1 : 1})`, transformOrigin: `${-left + 540}px 50%` }}>
          {media({ width: w, height: h, objectFit: "cover" })}
        </div>
        {s.grade === "vhs" && <Vhs />}
        {s.glitch && f < 9 && (
          <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, #ffffff14 0 2px, transparent 2px 6px)",
                                 boxShadow: `inset ${jit}px 0 0 ${PINK}66`, mixBlendMode: "screen" }} />
        )}
      </div>
    </AbsoluteFill>
  );
};

const Vhs: React.FC = () => {
  const f = useCurrentFrame();
  const y = (f * 37) % 1920;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, #0003 0 2px, transparent 2px 4px)" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: y, height: 40, background: "#ffffff22", filter: "blur(6px)" }} />
      <div style={{ position: "absolute", left: 60, top: 230, fontFamily: "monospace", fontSize: 44, color: "#fff", textShadow: "0 0 8px #000" }}>
        ◀◀ REW
      </div>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- GTA-style chrome

const Pd: React.FC<{ size: number; color?: string; s?: number; style?: React.CSSProperties; children: React.ReactNode }> =
  ({ size, color = "#fff", s = 8, style, children }) => (
    <div style={{ fontFamily: PD, fontSize: size, lineHeight: 0.95, color, letterSpacing: "0.01em", ...stroke(s), ...style }}>{children}</div>
  );

const step = (keys: [number, number][], f: number) => {
  let v = keys[0]?.[1] ?? 0;
  for (const [t, y] of keys) if (f >= t) v = y;
  return v;
};
const ramp = (keys: [number, number][], f: number) =>
  keys.length < 2 ? keys[0]?.[1] ?? 0 : interpolate(f, keys.map((k) => k[0]), keys.map((k) => k[1]), { ...clamp });

const Hud: React.FC<{ hud: Gta13Props["hud"] }> = ({ hud }) => {
  const f = useCurrentFrame();
  if (f < hud.from || f >= hud.to) return null;
  const yr = step(hud.years, f);
  const changed = hud.years.reduce((t, [k]) => (f >= k ? k : t), 0);
  const bump = 1 + 0.25 * (1 - tween(f, changed, 10, 0, 1, "outCubic"));
  const cash = ramp(hud.cash, f);
  const op = tween(f, hud.from, 8) * interpolate(f, [hud.to - 8, hud.to], [1, 0], clamp);
  return (
    <div style={{ position: "absolute", right: 46, top: 200, textAlign: "right", opacity: op }}>
      <Pd size={64} s={7} style={{ transform: `scale(${bump})`, transformOrigin: "right center" }}>{yr}</Pd>
      {cash > 0 && <Pd size={52} color={GREEN} s={6} style={{ marginTop: 6 }}>${fmt(cash)}</Pd>}
    </div>
  );
};

const Chapter: React.FC<{ o: Extract<Ov, { kind: "chapter" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 10, 0, 1, "outBack");
  const out = interpolate(f, [o.dur - 6, o.dur], [1, 0], clamp);
  const c = o.color ?? YEL;
  return (
    <AbsoluteFill style={{ opacity: out }}>
      <div style={{ position: "absolute", left: -40, right: -40, top: 330, height: 260, background: INK, transform: `rotate(-4deg) scaleX(${k})`,
                    boxShadow: `0 20px 60px #000C, 0 0 0 6px ${c}` }} />
      <div style={{ position: "absolute", left: 70, top: 345, transform: `rotate(-4deg) translateX(${(1 - k) * -300}px)` }}>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 34, color: c, letterSpacing: "0.3em" }}>{o.n}</div>
        <Pd size={Math.min(128, 1500 / Math.max(6, o.title.length))} s={0} style={{ marginTop: 4, whiteSpace: "nowrap" }}>{o.title}</Pd>
      </div>
    </AbsoluteFill>
  );
};

const Passed: React.FC<{ o: Extract<Ov, { kind: "passed" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 12, 0, 1, "outCubic");
  const out = interpolate(f, [o.dur - 8, o.dur], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: k * out }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 700, height: 300, background: "linear-gradient(90deg, transparent, #000B 20%, #000B 80%, transparent)" }} />
      <div style={{ marginTop: -60, textAlign: "center", transform: `scale(${0.85 + 0.15 * k})` }}>
        <Pd size={150} color={GOLD} s={9}>{o.title ?? "mission passed!"}</Pd>
        <div style={{ marginTop: 18, fontFamily: MONT, fontWeight: 900, fontSize: 58, color: "#fff", letterSpacing: "0.02em",
                      opacity: tween(f, 10, 10), ...stroke(6) }}>{o.sub}</div>
      </div>
    </AbsoluteFill>
  );
};

const Wasted: React.FC<{ o: Extract<Ov, { kind: "wasted" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 4, 14, 0, 1, "outCubic");
  const out = interpolate(f, [o.dur - 6, o.dur], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ opacity: out }}>
      <AbsoluteFill style={{ backdropFilter: `grayscale(${k}) contrast(1.2) brightness(${1 - 0.25 * k})`, WebkitBackdropFilter: `grayscale(${k})` }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ marginTop: -120, textAlign: "center", opacity: k, transform: `scale(${1.3 - 0.3 * k})` }}>
          <Pd size={230} color={o.color ?? RED} s={10}>{o.text}</Pd>
          {o.sub && <div style={{ marginTop: 14, fontFamily: MONT, fontWeight: 900, fontSize: 50, color: "#fff", ...stroke(6) }}>{o.sub}</div>}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Stars: React.FC<{ o: Extract<Ov, { kind: "stars" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const out = interpolate(f, [o.dur - 6, o.dur], [1, 0], clamp);
  return (
    <div style={{ position: "absolute", right: 46, top: 360, display: "flex", gap: 6, opacity: out }}>
      {[0, 1, 2, 3, 4].map((i) => {
        const on = i < o.n && f >= i * 5;
        const blink = on && Math.floor(f / 6) % 2 === 0;
        return (
          <div key={i} style={{ fontSize: 66, lineHeight: 1, color: on ? (blink ? "#fff" : GOLD) : "#ffffff33",
                                transform: `scale(${on ? tween(f, i * 5, 8, 1.6, 1, "outBack") : 1})`, textShadow: "0 0 4px #000, 0 3px 0 #000" }}>★</div>
        );
      })}
    </div>
  );
};

const Tip: React.FC<{ o: Extract<Ov, { kind: "tip" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 10) * interpolate(f, [o.dur - 8, o.dur], [1, 0], clamp);
  return (
    <div style={{ position: "absolute", left: 50, right: 150, top: 1330, opacity: k, transform: `translateY(${(1 - k) * 20}px)`,
                  padding: "18px 24px", background: "#000000C8", borderLeft: `8px solid ${YEL}`, borderRadius: 6 }}>
      <div style={{ fontFamily: MONT, fontWeight: 700, fontSize: 34, color: "#fff", lineHeight: 1.25 }}>
        <span style={{ color: YEL, fontWeight: 900 }}>TIP: </span>{o.text}
      </div>
    </div>
  );
};

const Phone: React.FC<{ o: Extract<Ov, { kind: "phone" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const up = tween(f, 0, 14, 0, 1, "outExpo") * (1 - tween(f, o.dur - 10, 10, 0, 1, "inOutCubic"));
  return (
    <div style={{ position: "absolute", right: 60, top: 470 + (1 - up) * 1300, width: 560, height: 820, borderRadius: 60, background: "#111",
                  border: "10px solid #2a2a2e", boxShadow: "0 40px 120px #000E", overflow: "hidden", transform: "rotate(3deg)" }}>
      <div style={{ height: 120, background: "#1d1d22", display: "flex", alignItems: "flex-end", padding: "0 30px 18px", fontFamily: MONT,
                    fontWeight: 900, fontSize: 36, color: "#fff" }}>{o.who}</div>
      <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
        {o.msgs.filter((m) => f >= m.at).map((m, i) => (
          <div key={i} style={{ alignSelf: m.me ? "flex-end" : "flex-start", maxWidth: "82%", padding: "16px 22px", borderRadius: 30,
                                background: m.me ? "#2F80ED" : "#3A3A40", color: "#fff", fontFamily: MONT, fontWeight: 800, fontSize: 42,
                                lineHeight: 1.2, transform: `scale(${tween(f, m.at, 8, 0.6, 1, "outBack")})`,
                                transformOrigin: m.me ? "right bottom" : "left bottom" }}>{m.text}</div>
        ))}
      </div>
    </div>
  );
};

const Panel: React.FC<{ k: number; out: number; top?: number; children: React.ReactNode }> = ({ k, out, top = 330, children }) => (
  <div style={{ position: "absolute", left: 50, right: 50, top, padding: "30px 38px 28px", borderRadius: 18, background: "#0B0B10EE",
                border: `4px solid ${INK}`, boxShadow: `10px 12px 0 ${INK}, 0 30px 80px #000C, inset 0 0 0 3px #ffffff22`, opacity: out,
                transform: `scale(${0.8 + 0.2 * k}) rotate(${(1 - k) * -3}deg)` }}>
    {children}
  </div>
);

const Counter: React.FC<{ o: Extract<Ov, { kind: "counter" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 12, 0, 1, "outBack");
  const out = interpolate(f, [o.dur - 8, o.dur], [1, 0], clamp);
  const n = tween(f, 4, Math.min(36, o.dur - 16), 0, 1, "outCubic");
  return (
    <Panel k={k} out={out}>
      <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 30, color: "#B9C1CC", letterSpacing: "0.08em" }}>{o.label}</div>
      <Pd size={150} color={n >= 1 ? GREEN : "#fff"} s={0} style={{ marginTop: 10, whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" }}>
        {o.prefix}{fmt(n * o.value)}{o.suffix}
      </Pd>
      {o.note && (
        <div style={{ marginTop: 12, display: "inline-block", fontFamily: MONT, fontWeight: 900, fontSize: 28, color: INK, background: YEL,
                      padding: "6px 14px", borderRadius: 8, opacity: tween(f, 30, 10) }}>{o.note}</div>
      )}
    </Panel>
  );
};

const Stamp: React.FC<{ o: Extract<Ov, { kind: "stamp" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 8, 2.2, 1, "outCubic");
  const out = interpolate(f, [o.dur - 6, o.dur], [1, 0], clamp);
  const col = o.color ?? RED;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: Math.min(1, tween(f, 0, 4)) * out }}>
      <div style={{ marginTop: -260, transform: `rotate(${o.rot ?? -8}deg) scale(${k})`, display: "flex", flexDirection: "column", alignItems: "center",
                    padding: "14px 40px 18px", border: `10px solid ${col}`, borderRadius: 20, background: "#000A",
                    boxShadow: `0 0 60px ${col}88, inset 0 0 40px ${col}44` }}>
        <Pd size={140} color={col} s={0}>{o.text}</Pd>
        {o.sub && <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 44, color: "#fff", marginTop: 8 }}>{o.sub}</div>}
      </div>
    </AbsoluteFill>
  );
};

const Stack: React.FC<{ o: Extract<Ov, { kind: "stack" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 12, 0, 1, "outBack");
  const out = interpolate(f, [o.dur - 8, o.dur], [1, 0], clamp);
  return (
    <Panel k={k} out={out}>
      <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 30, color: "#B9C1CC", letterSpacing: "0.08em" }}>{o.title}</div>
      <div style={{ marginTop: 18, display: "flex", gap: 16 }}>
        {o.items.map((it, i) => {
          const p = tween(f, it.at, 12, 0, 1, "outBack");
          return (
            <div key={i} style={{ flex: 1, padding: "20px 8px", borderRadius: 14, background: "#ffffff10", border: "3px solid #ffffff2a",
                                  textAlign: "center", opacity: Math.min(1, p), transform: `translateY(${(1 - Math.min(1, p)) * 60}px) scale(${p})` }}>
              <Pd size={84} s={0} color={i === o.items.length - 1 ? YEL : "#fff"}>{it.a}</Pd>
              <div style={{ marginTop: 8, fontFamily: MONT, fontWeight: 900, fontSize: 32, color: "#B9C1CC" }}>{it.b}</div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
};

const Timeline: React.FC<{ o: Extract<Ov, { kind: "timeline" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 12, 0, 1, "outBack");
  const out = interpolate(f, [o.dur - 8, o.dur], [1, 0], clamp);
  return (
    <Panel k={k} out={out} top={300}>
      {o.items.map((it, i) => {
        const p = tween(f, it.at, 10, 0, 1, "outExpo");
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 26, padding: "10px 0", opacity: p,
                                transform: `translateX(${(1 - p) * -80}px)`, borderBottom: i < o.items.length - 1 ? "2px solid #ffffff18" : "none" }}>
            <Pd size={72} s={0} color={it.color ?? YEL} style={{ width: 200 }}>{it.year}</Pd>
            <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 40, color: "#fff", lineHeight: 1.1 }}>{it.text}</div>
          </div>
        );
      })}
    </Panel>
  );
};

const Cash: React.FC<{ o: Extract<Ov, { kind: "cash" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: 9 }).map((_, i) => {
        const t0 = i * 4;
        if (f < t0) return null;
        const p = (f - t0) / 26;
        const x = 120 + hash(i * 13.7) * 760;
        const y = 1250 - p * 560 - hash(i * 3.1) * 200;
        return (
          <Pd key={i} size={64 + hash(i) * 30} color={GREEN} s={6}
              style={{ position: "absolute", left: x, top: y, opacity: interpolate(p, [0, 0.15, 0.8, 1], [0, 1, 1, 0], clamp) }}>
            {o.text}
          </Pd>
        );
      })}
    </AbsoluteFill>
  );
};

const Title: React.FC<{ o: Extract<Ov, { kind: "title" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const out = interpolate(f, [o.dur - 8, o.dur], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: out }}>
      <div style={{ marginTop: -200, textAlign: "center" }}>
        {o.lines.map((l, i) => {
          const p = tween(f, i * 6, 12, 0, 1, "outBack");
          return (
            <Pd key={i} size={i === o.lines.length - 1 ? 260 : 120} s={12} color={i === o.lines.length - 1 ? YEL : "#fff"}
                style={{ transform: `scale(${p}) rotate(${-3 + i * 2}deg)`, opacity: Math.min(1, p) }}>{l}</Pd>
          );
        })}
        {o.sub && <div style={{ marginTop: 24, fontFamily: MONT, fontWeight: 900, fontSize: 44, color: "#fff", opacity: tween(f, 18, 10), ...stroke(6) }}>{o.sub}</div>}
      </div>
    </AbsoluteFill>
  );
};

// Loading-screen comic panels: our sketch (draws on), then the real Vi3W 3D model slams in below it.
const Bridge: React.FC<{ o: Extract<Ov, { kind: "bridge" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const a = tween(f, 0, 12, 0, 1, "outBack");
  const draw = tween(f, 2, 18, 0, 1, "inOutCubic");
  const b = tween(f, o.pop, 12, 0, 1, "outBack");
  const flash = f >= o.pop ? 1 - tween(f, o.pop, 10, 0, 1, "outCubic") : 0;
  const frame = (c: string) => ({ position: "absolute" as const, overflow: "hidden", border: `8px solid ${INK}`, borderRadius: 6,
                                  boxShadow: `14px 16px 0 ${INK}, 0 0 0 4px ${c}, 0 40px 90px #000C` });
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: "#000", opacity: 0.45 * Math.min(1, a) }} />
      <div style={{ ...frame(YEL), left: 60, top: 250, width: 900, height: 900 * 756 / 1310, background: "#06070A",
                    transform: `rotate(-4deg) scale(${a})`, opacity: Math.min(1, a) }}>
        <Img src={staticFile(o.sketch)} style={{ width: "100%", height: "100%", objectFit: "cover", clipPath: `inset(0 ${(1 - draw) * 100}% 0 0)` }} />
        <div style={{ position: "absolute", left: 16, top: 14, padding: "6px 16px", background: YEL, color: INK, fontFamily: PD, fontSize: 52 }}>our sketch</div>
      </div>
      {f >= o.pop && (
        <div style={{ ...frame(GREEN), left: 140, top: 790, width: 820, height: 820 * 1096 / 1410, background: "#000",
                      transform: `rotate(3deg) scale(${b})`, opacity: Math.min(1, b) }}>
          <Sequence from={o.pop} layout="none">
            <OffthreadVideo src={staticFile(o.model)} muted startFrom={20} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </Sequence>
          <div style={{ position: "absolute", right: 16, top: 14, padding: "6px 16px", background: GREEN, color: INK, fontFamily: PD, fontSize: 52 }}>3d model</div>
        </div>
      )}
      {f >= o.pop && (
        <Pd size={120} color={YEL} s={10} style={{ position: "absolute", left: 470, top: 700, transform: `scale(${b}) rotate(90deg)` }}>➜</Pd>
      )}
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.7 }} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------- dev UI: viewport header, pipeline, timeline, console
const MONO = "Menlo, 'SF Mono', monospace";

const Viewport: React.FC<{ o: Extract<Ov, { kind: "viewport" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 8) * interpolate(f, [o.dur - 5, o.dur], [1, 0], clamp);
  const n = (r?: [number, number]) => (r ? Math.round(interpolate(f, [4, o.dur - 6], r, { ...clamp, easing: (t) => t * t })) : null);
  const tris = n(o.tris);
  const objs = n(o.objects);
  return (
    <div style={{ position: "absolute", left: 40, top: 250, opacity: k, display: "flex", flexDirection: "column", gap: 10, alignItems: "flex-start" }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <div style={{ padding: "8px 18px", borderRadius: 8, background: "#2B2B2BEE", border: "2px solid #4A4A4A", color: "#fff",
                      fontFamily: MONT, fontWeight: 800, fontSize: 30 }}>{o.mode} ▾</div>
        {o.rec && <div style={{ width: 22, height: 22, borderRadius: 11, background: RED, opacity: Math.floor(f / 10) % 2 ? 1 : 0.3 }} />}
      </div>
      {(tris !== null || objs !== null) && (
        <div style={{ padding: "8px 14px", borderRadius: 8, background: "#000000B0", fontFamily: MONO, fontSize: 28, color: "#E6E6E6", lineHeight: 1.35 }}>
          {objs !== null && <div>Objects <span style={{ color: YEL }}>{fmt(objs)}</span></div>}
          {tris !== null && <div>Triangles <span style={{ color: YEL }}>{fmt(tris)}</span></div>}
        </div>
      )}
    </div>
  );
};

const Pipeline: React.FC<{ o: Extract<Ov, { kind: "pipeline" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 10) * interpolate(f, [o.dur - 6, o.dur], [1, 0], clamp);
  return (
    <div style={{ position: "absolute", left: 40, right: 140, top: 1310, display: "flex", flexWrap: "wrap", gap: 10, opacity: k }}>
      {o.steps.map((s, i) => {
        const done = f >= s.at;
        const p = tween(f, s.at, 8, 0, 1, "outBack");
        return (
          <div key={i} style={{ padding: "8px 16px", borderRadius: 999, fontFamily: MONT, fontWeight: 900, fontSize: 28,
                                background: done ? GREEN : "#00000099", color: done ? INK : "#ffffffAA", border: `3px solid ${done ? INK : "#ffffff33"}`,
                                transform: `scale(${done ? 0.9 + 0.1 * p + 0.15 * (1 - p) : 0.9})` }}>{done ? "✓ " : ""}{s.label}</div>
        );
      })}
    </div>
  );
};

const Keys: React.FC<{ o: Extract<Ov, { kind: "keys" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 8) * interpolate(f, [o.dur - 5, o.dur], [1, 0], clamp);
  const head = (f / o.dur) * 100;
  return (
    <div style={{ position: "absolute", left: 40, right: 40, top: 1300, height: 120, borderRadius: 12, background: "#1E1E1EE8", border: "2px solid #3C3C3C",
                  opacity: k, overflow: "hidden" }}>
      {Array.from({ length: 25 }).map((_, i) => (
        <div key={i} style={{ position: "absolute", left: `${i * 4}%`, top: 0, bottom: 0, width: 1, background: i % 5 ? "#ffffff10" : "#ffffff26" }} />
      ))}
      {o.keys.map((t, i) => f >= t && (
        <div key={i} style={{ position: "absolute", left: `${(t / o.dur) * 100}%`, top: 44, width: 26, height: 26, marginLeft: -13,
                              background: YEL, transform: `rotate(45deg) scale(${tween(f, t, 6, 1.8, 1, "outBack")})`, border: `2px solid ${INK}` }} />
      ))}
      <div style={{ position: "absolute", left: `${head}%`, top: 0, bottom: 0, width: 4, background: "#4FA3FF" }} />
    </div>
  );
};

const Console: React.FC<{ o: Extract<Ov, { kind: "console" }> }> = ({ o }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 8, 0, 1, "outExpo") * interpolate(f, [o.dur - 5, o.dur], [1, 0], clamp);
  return (
    <div style={{ position: "absolute", left: 40, right: 140, top: 250, padding: "16px 20px", borderRadius: 12, background: "#0C0C0FEE",
                  border: `2px solid ${RED}88`, opacity: k, transform: `translateY(${(1 - k) * -30}px)`, fontFamily: MONO, fontSize: 27, lineHeight: 1.4 }}>
      {o.lines.filter((l) => f >= l.at).map((l, i) => (
        <div key={i} style={{ color: l.warn ? YEL : "#FF6B6B", whiteSpace: "nowrap", overflow: "hidden" }}>{l.warn ? "⚠ " : "✖ "}{l.text}</div>
      ))}
    </div>
  );
};

const OvView: React.FC<{ o: Ov }> = ({ o }) => {
  switch (o.kind) {
    case "chapter": return <Chapter o={o} />;
    case "passed": return <Passed o={o} />;
    case "wasted": return <Wasted o={o} />;
    case "stars": return <Stars o={o} />;
    case "tip": return <Tip o={o} />;
    case "phone": return <Phone o={o} />;
    case "counter": return <Counter o={o} />;
    case "stamp": return <Stamp o={o} />;
    case "stack": return <Stack o={o} />;
    case "timeline": return <Timeline o={o} />;
    case "cash": return <Cash o={o} />;
    case "title": return <Title o={o} />;
    case "bridge": return <Bridge o={o} />;
    case "viewport": return <Viewport o={o} />;
    case "pipeline": return <Pipeline o={o} />;
    case "keys": return <Keys o={o} />;
    case "console": return <Console o={o} />;
  }
};

// --------------------------------------------------------------------------- captions

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

const Captions: React.FC<{ words: W[]; emphasis: string[]; from: number }> = ({ words, emphasis, from }) => {
  const f = useCurrentFrame();
  const chunks = useMemo(() => chunk(words.filter((w) => w[0] >= from)), [words, from]);
  const c = chunks.find((k) => f >= k.from && f < k.to);
  if (!c) return null;
  const enter = tween(f, c.from, 4, 0, 1, "outCubic");
  const clean = (w: string) => w.replace(/[^\p{L}\p{N}'$]/gu, "").toLowerCase();
  return (
    <div style={{ position: "absolute", left: 60, right: 140, top: 1530, transform: `translateY(-50%) scale(${0.88 + 0.12 * enter})`,
                  display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", columnGap: 22, rowGap: 4 }}>
      {c.words.map(([a, b, w], i) => {
        const on = f >= a && f < Math.max(b, a + 4);
        const em = emphasis.includes(clean(w));
        return (
          <span key={i} style={{ display: "inline-block", transform: `scale(${on ? 1 + 0.08 * (1 - tween(f, a, 6, 0, 1, "outCubic")) : 1})`,
                                 fontFamily: PD, fontSize: 96, lineHeight: 1.05, letterSpacing: "0.01em",
                                 color: em ? YEL : on ? "#fff" : "#E8E8E8", ...stroke(11) }}>
            {w.replace(/[,;:…]+$/, "").replace(/\.+$/, "")}
          </span>
        );
      })}
    </div>
  );
};

// --------------------------------------------------------------------------- composition

const Grain: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: 0.09, mixBlendMode: "overlay",
                           backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", backgroundSize: "5px 5px",
                           backgroundPosition: `${hash(f) * 5}px ${hash(f + 7) * 5}px` }} />
  );
};

export const Gta13: React.FC<Gta13Props> = (p) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: INK }}>
      {p.shots.map((s, i) => (
        <Sequence key={`s${i}`} from={s.from} durationInFrames={s.dur}><ShotView s={s} /></Sequence>
      ))}
      <AbsoluteFill style={{ pointerEvents: "none", background: "radial-gradient(120% 80% at 50% 45%, transparent 55%, #000A 100%)" }} />
      <Grain />
      {p.overlays.map((o, i) => (
        <Sequence key={`o${i}`} from={o.from} durationInFrames={o.dur}><OvView o={o} /></Sequence>
      ))}
      <Hud hud={p.hud} />
      {f < p.credit.to && (!p.credit.perShot || p.shots.some((s) => s.credit && f >= s.from && f < s.from + s.dur)) && (
        <div style={{ position: "absolute", left: 30, top: 205, padding: "6px 14px 7px", borderRadius: 999, background: "#000000A6",
                      color: "#fffC", fontFamily: MONT, fontWeight: 800, fontSize: 22 }}>{p.credit.text}</div>
      )}
      {!p.overlays.some((o) => (o.kind === "chapter" || o.kind === "title") && f >= o.from && f < o.from + o.dur) && (
        <Captions words={p.words} emphasis={p.emphasis ?? []} from={p.captionsFrom} />
      )}
      {p.cues?.map((c, i) => (
        <Sequence key={`c${i}`} from={c.from} durationInFrames={c.dur}><Audio src={staticFile(c.src)} volume={c.volume} /></Sequence>
      ))}
      {p.vo?.map((v, i) => <Sequence key={`v${i}`} from={v.from}><Audio src={staticFile(v.src)} volume={v.volume ?? 1} /></Sequence>)}
      <AbsoluteFill style={{ background: "#fff", pointerEvents: "none",
                             opacity: p.shots.some((s) => s.glitch && f >= s.from && f < s.from + 3) ? 0.35 : 0 }} />
    </AbsoluteFill>
  );
};
