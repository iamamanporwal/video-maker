import { loadFont } from "@remotion/google-fonts/Montserrat";
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Img, interpolate, Loop, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import { tween } from "../lib/anim";

// Roblox-dev facts: a 10 s verified-fact hook over creator gameplay (karaoke VO captions + record counter),
// a blueprint freeze where the game's characters become "3D MODEL"s, a white-studio sketch → Vi3W model reveal
// with an in-game style nameplate, then the shared Vi3WOutro clip. 1080x1920; platform UI owns the bottom ~380 px.

const { fontFamily: MONT } = loadFont("normal", { weights: ["700", "800", "900"], subsets: ["latin"] });

type W = [number, number, string];
// kind: "tall" = 1080x1920 source (game area from y0); "wide" = 16:9 source fit to the band height, shifted left by x0;
// "img" = still image (src) with a slow push-in, panning from x0 (px, band coordinates).
type Shot = { src: string; from: number; dur: number; at: number; y0: number; zoom?: number; volume?: number; kind?: "tall" | "wide" | "img"; x0?: number };
export type DevFactProps = {
  fps: number;
  durationInFrames: number;
  tag: string;                                   // series pill, e.g. "ROBLOX DEV FACT #1"
  credit: string;
  shots: Shot[];                                 // hook footage (source frames at 1080x1920, game area from y0)
  stat: { from: number; dur: number; label: string; value: number; rival: string; rivalValue: number; note: string; header?: string; prefix?: string;
          twist?: { at: number; label: string; value: number } };    // twist: rival row is the big number, the hero row lands tiny at `at`
  freeze: { from: number; dur: number; items: { img: string; wire: string; tag: string; at: number }[]; chip: string };
  reveal: { from: number; dur: number; pop: number; baitAt: number; sketch: string; model: string; name: string; rate: string; line: string; bait: string;
            demo?: { src: string; w: number; h: number; label?: string; first?: string } };  // demo: real Vi3W screen recording (sketch → cut at pop → 3D model); label/first override the header and pre-pop chip
  outro: { from: number; src: string };          // src "" = no outro (the reveal runs to the end)
  words: W[];
  emphasis?: string[];
  vo?: { src: string; from: number }[];
  cues?: { src: string; from: number; volume: number }[];
};

const BAND = { top: 400, h: 1000 };
const CAP_Y = 1490;
const INK = "#07080C";
const YEL = "#FFE14D";
const LIME = "#7CFF6B";
const CYAN = "#5EEBFF";
const stroke = (px: number) => ({ WebkitTextStroke: `${px}px ${INK}`, paintOrder: "stroke fill" as const });
const shadow = "0 6px 24px #000C, 0 0 3px #000";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// --------------------------------------------------------------------------- hook footage

const ShotView: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame();
  const z = (s.zoom ?? 1) * (1.04 + 0.05 * (f / Math.max(1, s.dur))) * (f < 6 ? tween(f, 0, 6, 1.08, 1, "outCubic") : 1);
  const video = (style: React.CSSProperties, muted: boolean) => (
    <OffthreadVideo src={staticFile(s.src)} startFrom={s.at} muted={muted} volume={s.volume ?? 0.3} style={style} />
  );
  if (s.kind === "img" || s.kind === "wide") {
    const W = s.kind === "img" ? 1080 * 1.12 : (BAND.h * 16) / 9;
    const H = s.kind === "img" ? 1080 * 1.12 * (1024 / 1088) : BAND.h;
    const x = s.kind === "img" ? -(s.x0 ?? 0) * (1 - 0.5 * (f / Math.max(1, s.dur))) - 30 : -(s.x0 ?? 0);
    const y = s.kind === "img" ? (BAND.h - H) / 2 : 0;
    const media = (style: React.CSSProperties, muted: boolean) => s.kind === "img"
      ? <Img src={staticFile(s.src)} style={style} />
      : <OffthreadVideo src={staticFile(s.src)} startFrom={s.at} muted={muted} volume={s.volume ?? 0.3} style={style} />;
    return (
      <AbsoluteFill>
        <AbsoluteFill style={{ filter: "blur(40px) brightness(0.4) saturate(1.5)", transform: "scale(1.3)" }}>
          {media({ width: "100%", height: "100%", objectFit: "cover" }, true)}
        </AbsoluteFill>
        <div style={{ position: "absolute", left: 0, right: 0, top: BAND.top, height: BAND.h, overflow: "hidden",
                      boxShadow: "0 30px 90px #000, 0 -20px 60px #000A" }}>
          <div style={{ position: "absolute", left: x, top: y, width: W, height: H, transform: `scale(${z})`, transformOrigin: `${-x + 540}px ${BAND.h / 2 - y}px` }}>
            {media({ width: W, height: H }, false)}
          </div>
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: "blur(40px) brightness(0.4) saturate(1.5)", transform: "scale(1.3)" }}>
        {video({ width: "100%", height: "100%", objectFit: "cover" }, true)}
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 0, right: 0, top: BAND.top, height: BAND.h, overflow: "hidden",
                    boxShadow: "0 30px 90px #000, 0 -20px 60px #000A" }}>
        <div style={{ width: 1080, height: 1920, transform: `translateY(${-s.y0}px) scale(${z})`, transformOrigin: `50% ${s.y0 + BAND.h / 2}px` }}>
          {video({ width: 1080, height: 1920 }, false)}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const fmt = (n: number, prefix = "") => prefix + Math.round(n).toLocaleString("en-US");
const numSize = (s: string) => Math.min(96, Math.floor(1500 / Math.max(1, s.length)));

const StatCard: React.FC<{ s: DevFactProps["stat"] }> = ({ s }) => {
  const f = useCurrentFrame();
  const inK = tween(f, 0, 12, 0, 1, "outBack");
  const out = interpolate(f, [s.dur - 8, s.dur], [1, 0], clamp);
  const count = tween(f, 6, Math.min(48, s.dur - 20), 0, 1, "outCubic");
  const v = count * s.value;
  const beat = v > s.rivalValue;
  const wMax = 760;
  const rivalW = (s.rivalValue / s.value) * wMax;
  const pass = f >= 0 && beat ? 1 - tween(f, 6 + Math.min(48, s.dur - 20) * 0.45, 10, 0, 1, "outCubic") : 0;
  const big = fmt(s.value, s.prefix);
  if (s.twist) return <TwistCard s={s} />;
  return (
    <div style={{ position: "absolute", left: 50, right: 50, top: 150, padding: "34px 40px 30px", borderRadius: 36,
                  background: "linear-gradient(180deg, #0B0F17F2, #0B0F17E0)", border: "3px solid #ffffff22",
                  boxShadow: "0 30px 80px #000C", opacity: out, transform: `scale(${0.8 + 0.2 * inK}) translateY(${(1 - inK) * -40}px)` }}>
      <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 30, color: "#9AA3B5", letterSpacing: "0.06em" }}>{s.header ?? "PLAYERS AT THE SAME TIME"}</div>
      {/* rival */}
      <div style={{ marginTop: 22, display: "flex", alignItems: "center", gap: 18 }}>
        <div style={{ width: rivalW, height: 46, borderRadius: 12, background: "#8A93A8", boxShadow: "inset 0 0 0 3px #ffffff40" }} />
        <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 32, color: "#fff", whiteSpace: "nowrap" }}>{s.rival}</div>
      </div>
      {/* hero */}
      <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 18 }}>
        <div style={{ width: Math.max(8, count * wMax), height: 58, borderRadius: 14, background: beat ? LIME : "#9BE38F",
                      boxShadow: beat ? `0 0 ${30 + 30 * pass}px ${LIME}AA` : "none" }} />
      </div>
      <div style={{ marginTop: 18, display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: numSize(big), letterSpacing: "-0.04em", color: beat ? LIME : "#fff",
                      transform: `scale(${1 + 0.06 * pass})`, transformOrigin: "left center", fontVariantNumeric: "tabular-nums" }}>{fmt(v, s.prefix)}</div>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 36, color: "#fff" }}>{s.label}</div>
        <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 24, color: INK, background: YEL, padding: "6px 14px", borderRadius: 10,
                      opacity: tween(f, 40, 10, 0, 1) }}>{s.note}</div>
      </div>
    </div>
  );
};

// The twist: a huge number fills its bar, then the "typical" value lands as a red sliver next to it.
const RED = "#FF4D5E";
const TwistCard: React.FC<{ s: DevFactProps["stat"] }> = ({ s }) => {
  const f = useCurrentFrame();
  const t = s.twist!;
  const inK = tween(f, 0, 12, 0, 1, "outBack");
  const out = interpolate(f, [s.dur - 8, s.dur], [1, 0], clamp);
  const count = tween(f, 6, Math.min(40, t.at - 10), 0, 1, "outCubic");
  const rowK = tween(f, t.at, 10, 0, 1, "outBack");
  const tcount = tween(f, t.at, 14, 0, 1, "outCubic");
  const shake = f >= t.at && f < t.at + 12 ? 6 * Math.sin((f - t.at) * 2.4) * (1 - (f - t.at) / 12) : 0;
  const blink = f >= t.at + 14 ? 0.55 + 0.45 * Math.abs(Math.sin((f - t.at) / 5)) : 1;
  const wMax = 860;
  const row = (label: string, color: string, children: React.ReactNode) => (
    <div style={{ marginTop: 20 }}>
      <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 34, color }}>{label}</div>
      {children}
    </div>
  );
  return (
    <div style={{ position: "absolute", left: 50, right: 50, top: 150, padding: "34px 40px 34px", borderRadius: 36,
                  background: "linear-gradient(180deg, #0B0F17F2, #0B0F17E0)", border: "3px solid #ffffff22",
                  boxShadow: "0 30px 80px #000C", opacity: out, transform: `scale(${0.8 + 0.2 * inK}) translate(${shake}px, ${(1 - inK) * -40}px)` }}>
      <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 30, color: "#9AA3B5", letterSpacing: "0.06em" }}>{s.header}</div>
      {row(s.rival, YEL, <>
        <div style={{ marginTop: 10, width: Math.max(8, count * wMax), height: 54, borderRadius: 14, background: YEL, boxShadow: `0 0 40px ${YEL}88` }} />
        <div style={{ marginTop: 8, fontFamily: MONT, fontWeight: 900, fontSize: 88, letterSpacing: "-0.04em", color: YEL,
                      fontVariantNumeric: "tabular-nums" }}>{fmt(count * s.rivalValue, s.prefix)}</div>
      </>)}
      <div style={{ opacity: Math.min(1, rowK), transform: `translateX(${(1 - Math.min(1, rowK)) * 60}px)` }}>
        {row(t.label, RED, <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 10 }}>
          <div style={{ width: 4, height: 54, borderRadius: 2, background: RED, boxShadow: `0 0 24px ${RED}`, opacity: blink }} />
          <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 88, letterSpacing: "-0.04em", color: RED,
                        fontVariantNumeric: "tabular-nums" }}>{fmt(tcount * t.value, s.prefix)}</div>
          <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 64, opacity: tween(f, t.at + 16, 8, 0, 1) }}>💀</div>
        </div>)}
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 14 }}>
        <div style={{ fontFamily: MONT, fontWeight: 800, fontSize: 24, color: INK, background: "#ffffffD0", padding: "6px 14px", borderRadius: 10,
                      opacity: tween(f, 30, 10, 0, 1) }}>{s.note}</div>
      </div>
    </div>
  );
};

// --------------------------------------------------------------------------- blueprint freeze

const FreezeView: React.FC<{ fr: DevFactProps["freeze"] }> = ({ fr }) => {
  const f = useCurrentFrame();
  const cur = [...fr.items].reverse().find((it) => f >= it.at) ?? fr.items[0];
  const t = f - cur.at;
  const scan = tween(t, 4, 16, 0, 1, "inOutCubic");             // wire wipes down over the still
  const tagK = tween(t, 16, 12, 0, 1, "outBack");
  const flash = 1 - tween(t, 0, 8, 0, 1, "outCubic");
  const chipK = tween(f, fr.items[fr.items.length - 1].at + 14, 12, 0, 1, "outBack");
  const img = (src: string, style: React.CSSProperties = {}) => (
    <Img src={staticFile(src)} style={{ position: "absolute", left: 0, top: 0, width: 1080, height: 1190, ...style }} />
  );
  return (
    <AbsoluteFill style={{ background: "#050A14" }}>
      <AbsoluteFill style={{ background: `radial-gradient(90% 60% at 50% 45%, #0E2A44 0%, #050A14 70%)` }} />
      {/* blueprint grid */}
      <AbsoluteFill style={{ opacity: 0.35, backgroundImage: `linear-gradient(${CYAN}22 2px, transparent 2px), linear-gradient(90deg, ${CYAN}22 2px, transparent 2px)`,
                             backgroundSize: "60px 60px" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: BAND.top, height: BAND.h, overflow: "hidden",
                    boxShadow: `0 0 0 4px ${CYAN}55, 0 30px 90px #000` }}>
        <div style={{ position: "absolute", left: 0, top: -80, width: 1080, height: 1190, transform: `scale(${1.02 + 0.03 * Math.min(1, t / 60)})` }}>
          {img(cur.img)}
          <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 0 ${(1 - scan) * 100}% 0)` }}>
            {img(cur.img, { filter: "saturate(0.5) brightness(0.55) hue-rotate(-15deg)" })}
            {img(cur.wire, { filter: "brightness(4.5) contrast(1.4)", mixBlendMode: "screen" })}
          </div>
          {scan > 0 && scan < 1 && <div style={{ position: "absolute", left: 0, right: 0, top: `${scan * 100}%`, height: 10, background: CYAN,
                                                 boxShadow: `0 0 50px 20px ${CYAN}AA` }} />}
        </div>
        <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.7 }} />
      </div>
      {/* tag */}
      <div style={{ position: "absolute", left: 0, right: 0, top: BAND.top + 790, display: "flex", justifyContent: "center",
                    transform: `scale(${tagK})`, opacity: Math.min(1, tagK) }}>
        <div style={{ padding: "16px 34px", borderRadius: 20, background: CYAN, color: INK, fontFamily: MONT, fontWeight: 900, fontSize: 64,
                      letterSpacing: "-0.02em", boxShadow: `0 0 50px ${CYAN}99, 0 16px 40px #000A` }}>{cur.tag}</div>
      </div>
      {/* chip */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 260, display: "flex", justifyContent: "center",
                    transform: `scale(${chipK})`, opacity: Math.min(1, chipK) }}>
        <div style={{ padding: "14px 30px", borderRadius: 999, background: "#000000B0", border: "3px solid #ffffff33", color: "#fff",
                      fontFamily: MONT, fontWeight: 900, fontSize: 48 }}>{fr.chip}</div>
      </div>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- sketch → model reveal

const RevealView: React.FC<{ r: DevFactProps["reveal"] }> = ({ r }) => {
  const f = useCurrentFrame();
  const R = r.pop;
  const sketchIn = tween(f, 0, 14, 0.6, 1, "outBack");
  const scan = tween(f, 8, R - 12, 0, 1, "inOutCubic");
  const toCorner = tween(f, R, 16, 0, 1, "outExpo");
  const flash = f >= R ? 1 - tween(f, R, 10, 0, 1, "outCubic") : 0;
  const grow = tween(f, R, 18, 0.25, 1, "outBack");
  const plate = tween(f, R + 12, 14, 0, 1, "outBack");
  const bait = tween(f, r.baitAt, 12, 0, 1, "outBack");
  const bob = 8 * Math.sin((f - R) / 14);
  const size = interpolate(toCorner, [0, 1], [700, 220]);
  const cx = interpolate(toCorner, [0, 1], [540, 190]);
  const cy = interpolate(toCorner, [0, 1], [880, 1300]);
  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 70% at 50% 45%, #ffffff 0%, #f3f4f7 60%, #e3e6ee 100%)" }}>
      <div style={{ position: "absolute", left: 320, width: 440, top: 1210, height: 60, borderRadius: "50%",
                    background: "radial-gradient(closest-side, #00000033, #0000)", opacity: f >= R ? 1 : 0 }} />
      {f >= R && (
        <div style={{ position: "absolute", left: 130, top: 420, width: 820, height: 820,
                      transform: `translateY(${bob}px) scale(${grow}) rotate(${(1 - Math.min(1, grow)) * -12}deg)` }}>
          <Sequence from={R} layout="none">
            <Loop durationInFrames={300}>
              <OffthreadVideo src={staticFile(r.model)} transparent muted playbackRate={0.5} style={{ width: 820, height: 820 }} />
            </Loop>
          </Sequence>
        </div>
      )}
      {/* in-game style nameplate */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
                    transform: `scale(${plate})`, opacity: Math.min(1, plate) }}>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 58, color: LIME, ...stroke(10), textShadow: "0 6px 0 #0006" }}>{r.rate}</div>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 52, color: "#fff", background: "linear-gradient(90deg,#FF3BD4,#FFB800,#3BFF8A,#3BC8FF)",
                      padding: "0 22px 4px", borderRadius: 14, ...stroke(6) }}>OG</div>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 84, letterSpacing: "-0.02em", color: "#fff", ...stroke(12),
                      textShadow: "0 8px 0 #0005" }}>{r.name}</div>
      </div>
      {/* sketch card */}
      <div style={{ position: "absolute", left: cx - size / 2, top: cy - size / 2, width: size, height: size, borderRadius: 26, overflow: "hidden",
                    background: "#fff", transform: `rotate(${interpolate(toCorner, [0, 1], [-2, -7])}deg) scale(${sketchIn})`,
                    boxShadow: "0 30px 70px #0003, 0 0 0 5px #fff" }}>
        <Img src={staticFile(r.sketch)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        {f < R && <div style={{ position: "absolute", top: 0, bottom: 0, left: `${scan * 100}%`, width: 12, background: LIME,
                                boxShadow: `0 0 40px 16px ${LIME}AA`, opacity: scan > 0 && scan < 1 ? 1 : 0 }} />}
        <div style={{ position: "absolute", left: 14, top: 14, padding: "6px 14px", borderRadius: 999, background: INK, color: "#fff",
                      fontFamily: MONT, fontWeight: 800, fontSize: interpolate(toCorner, [0, 1], [32, 20]) }}>OUR SKETCH ✏️</div>
      </div>
      {/* "made with" chip next to the tucked sketch */}
      <div style={{ position: "absolute", left: 330, top: 1268, opacity: Math.min(1, plate), transform: `translateX(${(1 - Math.min(1, plate)) * 40}px)` }}>
        <div style={{ padding: "12px 24px", borderRadius: 999, background: INK, color: LIME, fontFamily: MONT, fontWeight: 900, fontSize: 36 }}>
          sketch → 3D with Vi3W ⚡
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1420, display: "flex", justifyContent: "center",
                    transform: `scale(${bait})`, opacity: Math.min(1, bait) }}>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 50, color: INK }}>{r.bait}</div>
      </div>
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.85 }} />
    </AbsoluteFill>
  );
};

// Real Vi3W screen recording in a device card: sketch part, hard cut at `pop` to the 3D model.
const DemoReveal: React.FC<{ r: DevFactProps["reveal"] }> = ({ r }) => {
  const f = useCurrentFrame();
  const d = r.demo!;
  const R = r.pop;
  const inK = tween(f, 0, 14, 0.7, 1, "outBack");
  const flash = f >= R ? 1 - tween(f, R, 10, 0, 1, "outCubic") : 0;
  const plate = tween(f, R + 6, 14, 0, 1, "outBack");
  const bait = tween(f, r.baitAt, 12, 0, 1, "outBack");
  const W = 1000;
  const H = Math.round((W * d.h) / d.w);
  const punch = f >= R ? 1 + 0.06 * (1 - tween(f, R, 14, 0, 1, "outCubic")) : 1;
  const chip = (text: string, bg: string, fg: string) => (
    <div style={{ position: "absolute", left: 22, top: 22, padding: "8px 18px", borderRadius: 999, background: bg, color: fg,
                  fontFamily: MONT, fontWeight: 900, fontSize: 34, boxShadow: "0 8px 20px #0006" }}>{text}</div>
  );
  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 70% at 50% 45%, #ffffff 0%, #f3f4f7 60%, #e3e6ee 100%)" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 170, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 40, color: "#59607A", letterSpacing: "0.04em" }}>{d.label ?? "REAL Vi3W SCREEN RECORDING"}</div>
        <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 76, letterSpacing: "-0.02em", color: INK, transform: `scale(${Math.max(0.001, plate)})`,
                      opacity: Math.min(1, plate) }}>{r.name}</div>
      </div>
      <div style={{ position: "absolute", left: (1080 - W) / 2, top: 820 - H / 2, width: W, height: H, borderRadius: 30, overflow: "hidden",
                    background: "#000", boxShadow: "0 40px 90px #0004, 0 0 0 6px #fff, 0 0 0 9px #0001",
                    transform: `scale(${inK * punch})` }}>
        <OffthreadVideo src={staticFile(d.src)} muted style={{ width: W, height: H }} />
        {f < R ? chip(d.first ?? "OUR SKETCH ✏️", "#fff", INK) : chip("3D MODEL ⚡ Vi3W", LIME, INK)}
        <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.85 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1300, display: "flex", justifyContent: "center",
                    transform: `scale(${Math.max(0.001, bait)})`, opacity: Math.min(1, bait) }}>
        <div style={{ padding: "12px 28px", borderRadius: 999, background: INK, color: LIME, fontFamily: MONT, fontWeight: 900, fontSize: 40 }}>{r.bait}</div>
      </div>
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

const Captions: React.FC<{ words: W[]; emphasis: string[]; dark: (f: number) => boolean }> = ({ words, emphasis, dark }) => {
  const f = useCurrentFrame();
  const chunks = useMemo(() => chunk(words), [words]);
  const c = chunks.find((k) => f >= k.from && f < k.to);
  if (!c) return null;
  const enter = tween(f, c.from, 4, 0, 1, "outCubic");
  const clean = (w: string) => w.replace(/[^\p{L}\p{N}'*.]/gu, "").replace(/\.$/, "").toLowerCase();
  const onWhite = !dark(f);
  return (
    <div style={{ position: "absolute", left: 60, right: 140, top: CAP_Y, transform: `translateY(-50%) scale(${0.88 + 0.12 * enter})`,
                  display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", columnGap: 26, rowGap: 6 }}>
      {c.words.map(([a, b, w], i) => {
        const on = f >= a && f < Math.max(b, a + 4);
        const pop = on ? 1 + 0.08 * (1 - tween(f, a, 6, 0, 1, "outCubic")) : 1;
        const em = emphasis.includes(clean(w));
        return (
          <span key={i} style={{ display: "inline-block", transform: `scale(${pop}) rotate(${em && on ? -2 : 0}deg)`,
                                 fontFamily: MONT, fontWeight: 900, fontSize: 84, lineHeight: 1.08, letterSpacing: "-0.025em",
                                 textTransform: "uppercase", color: em ? INK : on ? YEL : "#fff",
                                 background: em ? (on ? YEL : LIME) : "transparent", padding: em ? "0 14px 4px" : 0,
                                 borderRadius: em ? 14 : 0, textShadow: em || onWhite ? "none" : shadow, ...(em ? {} : stroke(onWhite ? 12 : 10)) }}>
            {w.replace(/[,.;:…]+$/, "")}
          </span>
        );
      })}
    </div>
  );
};

const Pill: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ position: "absolute", left: 0, right: 0, top: 120, display: "flex", justifyContent: "center" }}>
    <div style={{ padding: "10px 26px 12px", borderRadius: 999, background: YEL, color: INK, fontFamily: MONT, fontWeight: 900, fontSize: 34,
                  letterSpacing: "0.02em", boxShadow: "0 10px 30px #0008" }}>{text}</div>
  </div>
);

const Credit: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ position: "absolute", left: 30, top: BAND.top + BAND.h - 70, padding: "8px 18px 9px", borderRadius: 999,
                background: "#000000A6", border: "2px solid #ffffff2e", color: "#fff", fontFamily: MONT, fontWeight: 800, fontSize: 26 }}>{text}</div>
);

// --------------------------------------------------------------------------- composition

export const DevFact: React.FC<DevFactProps> = (p) => {
  const f = useCurrentFrame();
  const hookEnd = p.freeze.from;
  const wipe = (at: number) => interpolate(f, [at - 6, at, at + 6], [0, 1, 0], clamp);
  const isDark = (fr: number) => fr < p.reveal.from;
  return (
    <AbsoluteFill style={{ background: INK }}>
      {p.shots.map((s, i) => (
        <Sequence key={`s${i}`} from={s.from} durationInFrames={s.dur}><ShotView s={s} /></Sequence>
      ))}
      <Sequence durationInFrames={hookEnd}><Credit text={p.credit} /></Sequence>
      <Sequence from={p.stat.from} durationInFrames={p.stat.dur}><StatCard s={p.stat} /></Sequence>
      <Sequence from={p.freeze.from} durationInFrames={p.freeze.dur}><FreezeView fr={p.freeze} /></Sequence>
      <Sequence from={p.reveal.from} durationInFrames={p.reveal.dur}>{p.reveal.demo ? <DemoReveal r={p.reveal} /> : <RevealView r={p.reveal} />}</Sequence>
      <Sequence durationInFrames={p.outro.from}>
        {f < p.stat.from || f >= p.stat.from + p.stat.dur ? (f < p.reveal.from ? <Pill text={p.tag} /> : null) : null}
        <Captions words={p.words} emphasis={p.emphasis ?? []} dark={isDark} />
      </Sequence>
      {p.outro.src ? <Sequence from={p.outro.from}><OffthreadVideo src={staticFile(p.outro.src)} /></Sequence> : null}
      {p.cues?.map((c, i) => <Sequence key={`c${i}`} from={c.from}><Audio src={staticFile(c.src)} volume={c.volume} /></Sequence>)}
      {p.vo?.map((v, i) => <Sequence key={`v${i}`} from={v.from}><Audio src={staticFile(v.src)} /></Sequence>)}
      <AbsoluteFill style={{ background: "#fff", opacity: Math.max(wipe(p.reveal.from), wipe(p.outro.from)), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
