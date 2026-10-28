import { createContext, useContext } from "react";
import type { Fmt } from "../types";

export const SIZES: Record<Fmt, [number, number]> = {
  "16x9": [1920, 1080],
  "9x16": [1080, 1920],
  "4x5": [1080, 1350],
  "5x4": [1350, 1080],
};

export type Safe = { top: number; bottom: number; left: number; right: number };

// 9:16 avoids platform UI: top 220, bottom 420, right 120. 4:5 keeps a 60px margin.
export const SAFE: Record<Fmt, Safe> = {
  "16x9": { top: 70, bottom: 70, left: 96, right: 96 },
  "9x16": { top: 220, bottom: 420, left: 60, right: 120 },
  "4x5": { top: 60, bottom: 60, left: 60, right: 60 },
  "5x4": { top: 60, bottom: 60, left: 72, right: 72 },
};

export type FormatInfo = {
  fmt: Fmt;
  w: number;
  h: number;
  safe: Safe;
  vertical: boolean;
  wide: boolean;
  /** Type scale relative to a 1080px short side. */
  u: number;
  inner: { x: number; y: number; w: number; h: number };
};

export const formatInfo = (fmt: Fmt): FormatInfo => {
  const [w, h] = SIZES[fmt];
  const safe = SAFE[fmt];
  return {
    fmt,
    w,
    h,
    safe,
    vertical: h > w,
    wide: w / h > 1.5,
    u: Math.min(w, h) / 1080,
    inner: { x: safe.left, y: safe.top, w: w - safe.left - safe.right, h: h - safe.top - safe.bottom },
  };
};

export const FormatContext = createContext<FormatInfo>(formatInfo("16x9"));
export const useFormat = () => useContext(FormatContext);

export type Rect = { x: number; y: number; w: number; h: number };

/** Expand a focus rect (page coords) to the target aspect around its centre, then clamp it inside the page. */
export const fitCrop = (focus: Rect, aspect: number, page: { width: number; height: number }): Rect => {
  let { w, h } = focus;
  if (w / h > aspect) h = w / aspect;
  else w = h * aspect;
  if (w > page.width) {
    w = page.width;
    h = w / aspect;
  }
  if (h > page.height) {
    h = page.height;
    w = h * aspect;
  }
  const cx = focus.x + focus.w / 2;
  const cy = focus.y + focus.h / 2;
  const x = Math.min(Math.max(cx - w / 2, 0), page.width - w);
  const y = Math.min(Math.max(cy - h / 2, 0), page.height - h);
  return { x, y, w, h };
};
