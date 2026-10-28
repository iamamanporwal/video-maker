import React, { useMemo } from "react";
import { Img, useCurrentFrame, useVideoConfig } from "remotion";
import { C } from "../generated/brand";
import { multiKeys, pchip } from "../lib/anim";
import { useFilm } from "../lib/context";
import { fitCrop, Rect } from "../lib/layout";
import type { Take } from "../types";

export type CaptureProps = {
  take: string;
  /** [[localFrame, sourceSec], ...] - monotone cubic time remap. */
  timeKeys: [number, number][];
  /** [[localFrame, x, y, w, h], ...] in page coordinates. */
  focusKeys?: number[][];
  width: number;
  height: number;
  cursor?: boolean;
  strokes?: boolean;
  /** Only replay strokes recorded after this source time (e.g. the overlay pass). */
  strokesFrom?: number;
  radius?: number;
};

const frameAt = (take: Take, sec: number) => {
  const t = take.t;
  let lo = 0;
  let hi = t.length - 1;
  if (sec <= t[0]) return 0;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (t[mid] <= sec) lo = mid;
    else hi = mid - 1;
  }
  return lo;
};

const mouseAt = (m: Take["mouse"], sec: number) => {
  if (!m.length) return null;
  if (sec <= m[0][0]) return { x: m[0][1], y: m[0][2], down: !!m[0][3] };
  for (let i = 1; i < m.length; i++) {
    if (m[i][0] >= sec) {
      const a = m[i - 1];
      const b = m[i];
      const k = (sec - a[0]) / Math.max(1e-6, b[0] - a[0]);
      return { x: a[1] + (b[1] - a[1]) * k, y: a[2] + (b[2] - a[2]) * k, down: !!a[3] };
    }
  }
  const l = m[m.length - 1];
  return { x: l[1], y: l[2], down: !!l[3] };
};

/** Pointer-down segments up to sec, as polylines. */
const strokesUpTo = (m: Take["mouse"], sec: number, from: number) => {
  const out: [number, number][][] = [];
  let cur: [number, number][] | null = null;
  for (const [t, x, y, d] of m) {
    if (t > sec) break;
    if (d && t >= from) {
      if (!cur) {
        cur = [];
        out.push(cur);
      }
      cur.push([x, y]);
    } else cur = null;
  }
  return out;
};

const CursorGlyph: React.FC<{ x: number; y: number; scale: number; pressed: boolean }> = ({ x, y, scale, pressed }) => {
  const s = Math.max(0.8, Math.min(2.2, scale)) * (pressed ? 0.9 : 1);
  return (
    <svg
      style={{ position: "absolute", left: x, top: y, overflow: "visible", filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.55))" }}
      width={1}
      height={1}
    >
      <path
        transform={`scale(${s})`}
        d="M0 0 L0 22 L6 16.5 L10 26 L13.5 24.5 L9.6 15.3 L17 15.3 Z"
        fill="#fff"
        stroke="#0B0B0C"
        strokeWidth={1.4}
        strokeLinejoin="round"
      />
    </svg>
  );
};

export const Capture: React.FC<CaptureProps> = ({
  take: takeId,
  timeKeys,
  focusKeys,
  width,
  height,
  cursor = true,
  strokes = true,
  strokesFrom = 0,
  radius = 0,
}) => {
  const frame = useCurrentFrame();
  const { assetBase, takes } = useFilm();
  const take = takes[takeId];
  const remap = useMemo(() => pchip(timeKeys), [timeKeys]);
  const focusFn = useMemo(() => multiKeys(focusKeys ?? []), [focusKeys]);
  if (!take || !take.t?.length) {
    return (
      <div style={{ width, height, borderRadius: radius, background: "#1b1d1a", color: C.muted[0], display: "grid", placeItems: "center", fontSize: 28, fontFamily: "monospace" }}>
        capture "{takeId}" not recorded yet
      </div>
    );
  }
  const sec = remap(frame);
  const page = take.page;
  const f = focusFn(frame);
  const focus: Rect = f.length === 4 ? { x: f[0], y: f[1], w: f[2], h: f[3] } : { x: 0, y: 0, w: page.width, h: page.height };
  const crop = fitCrop(focus, width / height, page);
  const scale = width / crop.w;
  const src = `${assetBase}/${take.dir}/${take.f[frameAt(take, sec)]}`;
  const ms = mouseAt(take.mouse, sec);
  const toBox = (x: number, y: number) => [(x - crop.x) * scale, (y - crop.y) * scale];
  const clicks = take.events.filter((e) => e.name === "click" && e.t <= sec && sec - e.t < 0.6);
  const segs = strokes ? strokesUpTo(take.mouse, sec, strokesFrom) : [];
  return (
    <div style={{ position: "relative", width, height, overflow: "hidden", borderRadius: radius, background: "#111" }}>
      <Img
        src={src}
        style={{ position: "absolute", left: -crop.x * scale, top: -crop.y * scale, width: page.width * scale, height: page.height * scale }}
      />
      {segs.length > 0 && (
        <svg style={{ position: "absolute", inset: 0 }} width={width} height={height}>
          {segs.map((s, i) => (
            <polyline
              key={i}
              points={s.map(([x, y]) => toBox(x, y).join(",")).join(" ")}
              fill="none"
              stroke={C.accent}
              strokeWidth={Math.max(3, 3.2 * scale)}
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ filter: `drop-shadow(0 0 ${6 * scale}px ${C.accent}88)` }}
            />
          ))}
        </svg>
      )}
      {clicks.map((c, i) => {
        const [x, y] = toBox(c.x, c.y);
        const k = (sec - c.t) / 0.6;
        const r = 10 + 46 * (1 - Math.pow(1 - k, 3));
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x - r,
              top: y - r,
              width: r * 2,
              height: r * 2,
              borderRadius: "50%",
              border: `${3 * (1 - k) + 1}px solid ${C.accent}`,
              opacity: 1 - k,
            }}
          />
        );
      })}
      {cursor && ms && (() => {
        const [x, y] = toBox(ms.x, ms.y);
        return <CursorGlyph x={x} y={y} scale={scale * 1.1} pressed={ms.down} />;
      })()}
    </div>
  );
};

/** Source time of a named event in a take (for honest timing tags and keyframes). */
export const eventTime = (take: Take | undefined, name: string, nth = 0) =>
  take?.events.filter((e) => e.name === name)[nth]?.t ?? 0;

export const useCaptureSize = () => useVideoConfig();
