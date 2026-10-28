import React, { useMemo } from "react";
import { useCurrentFrame } from "remotion";
import { C, F } from "../generated/brand";
import { tween } from "../lib/anim";
import { useFormat } from "../lib/layout";
import type { VoiceLine } from "../types";

type Word = [number, number, string];
type Chunk = { words: Word[]; from: number; to: number; capY?: number };

const MAX_WORDS = 3;

/** Group a line's words into short chunks (≤3 words, break after punctuation), each held until the next starts. */
export const chunkVoice = (voice: VoiceLine[]): Chunk[] => {
  const out: Chunk[] = [];
  for (const line of voice) {
    if (line.caption === false || !line.words.length) continue;
    let cur: Word[] = [];
    const flush = () => {
      if (cur.length) out.push({ words: cur, from: cur[0][0] - 2, to: cur[cur.length - 1][1] + 8, capY: line.capY });
      cur = [];
    };
    for (const w of line.words) {
      cur.push(w);
      if (cur.length >= MAX_WORDS || /[.,!?…:]$/.test(w[2])) flush();
    }
    flush();
  }
  out.sort((a, b) => a.from - b.from);
  for (let i = 0; i < out.length - 1; i++) out[i].to = Math.min(out[i].to, out[i + 1].from);
  return out;
};

/** Karaoke captions from real TTS word timings: the spoken word lights up in the accent and pops. */
export const VoiceCaptions: React.FC<{ voice: VoiceLine[] }> = ({ voice }) => {
  const frame = useCurrentFrame();
  const { h, safe, u, vertical } = useFormat();
  const chunks = useMemo(() => chunkVoice(voice), [voice]);
  const c = chunks.find((k) => frame >= k.from && frame < k.to);
  if (!c) return null;
  const enter = tween(frame, c.from, 5, 0, 1, "outCubic");
  const y = (c.capY ?? (vertical ? 0.66 : 0.8)) * h;
  return (
    <div style={{ position: "absolute", left: safe.left, right: safe.right, top: y, transform: `translateY(-50%) scale(${0.9 + 0.1 * enter})`,
                  opacity: enter, display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: 18 * u, rowGap: 4 * u }}>
      {c.words.map(([a, b, w], i) => {
        const on = frame >= a && frame < Math.max(b, a + 4);
        const said = frame >= a;
        const pop = on ? 1 + 0.12 * (1 - tween(frame, a, 6, 0, 1, "outCubic")) : 1;
        return (
          <span key={i} style={{ fontFamily: F.display, fontWeight: 800, fontSize: (vertical ? 92 : 76) * u, lineHeight: 1.05,
                                 letterSpacing: "-0.03em", textTransform: "uppercase", color: on ? C.accent : said ? C.text : `${C.text}B3`,
                                 transform: `scale(${pop})`, display: "inline-block",
                                 textShadow: `0 0 ${2 * u}px ${C.ink}, 0 ${5 * u}px ${24 * u}px ${C.ink}, 0 0 ${40 * u}px ${C.ink}CC` }}>
            {w}
          </span>
        );
      })}
    </div>
  );
};

/** Music gain multiplier: dips under every voice line (ramped so it doesn't pump). */
export const duckFn = (voice: VoiceLine[] | undefined, depth = 0.38, ramp = 6) => {
  const spans = (voice ?? []).filter((v) => v.words.length).map((v) => [v.words[0][0] - ramp, v.words[v.words.length - 1][1] + ramp]);
  return (f: number) => {
    let g = 1;
    for (const [a, b] of spans) {
      if (f < a - ramp || f > b + ramp) continue;
      const k = f < a ? (f - (a - ramp)) / ramp : f > b ? 1 - (f - b) / ramp : 1;
      g = Math.min(g, 1 - (1 - depth) * Math.max(0, Math.min(1, k)));
    }
    return g;
  };
};
