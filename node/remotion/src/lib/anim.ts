import { Easing, interpolate } from "remotion";

// Named easings. No linear motion except the caret and camera drift.
export const EASES = {
  outExpo: Easing.bezier(0.16, 1, 0.3, 1),
  inOutExpo: Easing.bezier(0.87, 0, 0.13, 1),
  outCubic: Easing.bezier(0.33, 1, 0.68, 1),
  inOutCubic: Easing.bezier(0.65, 0, 0.35, 1),
  outBack: Easing.bezier(0.34, 1.56, 0.64, 1),
  calm: Easing.bezier(0.4, 0, 0.2, 1),
  linear: (t: number) => t,
} as const;

export type EaseName = keyof typeof EASES;

export const ease = (name?: string) => EASES[(name as EaseName) ?? "outExpo"] ?? EASES.outExpo;

/** Clamped tween from a to b over [start, start+dur]. */
export const tween = (frame: number, start: number, dur: number, a = 0, b = 1, e: string = "outExpo") =>
  interpolate(frame, [start, start + Math.max(1, dur)], [a, b], {
    easing: ease(e),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/**
 * Monotone cubic (PCHIP / Fritsch-Carlson) interpolation through keyframes [[x, y], ...].
 * Used for the capture time-remap so speed ramps are smooth with no stalls or overshoot.
 */
export const pchip = (keys: [number, number][]) => {
  const k = [...keys].sort((a, b) => a[0] - b[0]);
  const n = k.length;
  if (n === 0) return () => 0;
  if (n === 1) return () => k[0][1];
  const xs = k.map((p) => p[0]);
  const ys = k.map((p) => p[1]);
  const h = xs.slice(1).map((x, i) => x - xs[i]);
  const d = h.map((hi, i) => (ys[i + 1] - ys[i]) / hi);
  const m = new Array(n).fill(0);
  m[0] = d[0];
  m[n - 1] = d[n - 2];
  for (let i = 1; i < n - 1; i++) {
    if (d[i - 1] * d[i] <= 0) m[i] = 0;
    else {
      const w1 = 2 * h[i] + h[i - 1];
      const w2 = h[i] + 2 * h[i - 1];
      m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]);
    }
  }
  return (x: number) => {
    if (x <= xs[0]) return ys[0];
    if (x >= xs[n - 1]) return ys[n - 1];
    let i = 0;
    while (i < n - 2 && x > xs[i + 1]) i++;
    const t = (x - xs[i]) / h[i];
    const t2 = t * t;
    const t3 = t2 * t;
    return (
      (2 * t3 - 3 * t2 + 1) * ys[i] +
      (t3 - 2 * t2 + t) * h[i] * m[i] +
      (-2 * t3 + 3 * t2) * ys[i + 1] +
      (t3 - t2) * h[i] * m[i + 1]
    );
  };
};

/** Interpolate multi-value keyframes [[frame, a, b, c, ...], ...] smoothly (PCHIP per channel). */
export const multiKeys = (keys: number[][]) => {
  if (!keys || keys.length === 0) return () => [] as number[];
  const channels = keys[0].length - 1;
  const fns = Array.from({ length: channels }, (_, c) => pchip(keys.map((k) => [k[0], k[c + 1]] as [number, number])));
  return (f: number) => fns.map((fn) => fn(f));
};

/** Deterministic hash noise in [0, 1) - no Math.random() at render time. */
export const hash = (n: number) => {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453123;
  return s - Math.floor(s);
};

export const resolveAsset = (base: string, p?: string) => {
  if (!p) return "";
  if (/^(https?:|data:)/.test(p)) return p;
  return `${base.replace(/\/$/, "")}/${p.replace(/^\//, "")}`;
};
