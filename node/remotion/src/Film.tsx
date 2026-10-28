import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate } from "remotion";
import { Captions, DebugOverlay, Finish } from "./components/Finish";
import { Headline } from "./components/Type";
import { VoiceCaptions, duckFn } from "./components/VoiceCaptions";
import { C } from "./generated/brand";
import { resolveAsset } from "./lib/anim";
import { FilmContext, useAsset } from "./lib/context";
import { FormatContext, formatInfo, useFormat } from "./lib/layout";
import { Missing, SCENES } from "./scenes/Scenes";
import type { CutTimeline, FilmProps, Fmt } from "./types";

const volumeFn = (keys: [number, number][], segFrom: number, duck: (f: number) => number = () => 1) => (f: number) => {
  // keys are in cut frames; the Audio callback gives frames relative to the segment.
  const g = duck(f + segFrom);
  if (!keys || keys.length === 0) return g;
  if (keys.length === 1) return keys[0][1] * g;
  return g * interpolate(f + segFrom, keys.map((k) => k[0]), keys.map((k) => k[1]), { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
};

export const Film: React.FC<FilmProps & { cut: string; fmt: Fmt }> = ({ timeline, takes, assetBase, sfxFiles, cut, fmt, debug }) => {
  const ct = timeline.cuts.find((c) => c.name === cut) as CutTimeline;
  const duck = duckFn(ct.voice);
  return (
    <FilmContext.Provider value={{ assetBase, takes, debug: !!debug }}>
      <FormatContext.Provider value={formatInfo(fmt)}>
        <AbsoluteFill style={{ background: C.ink }}>
          {ct.scenes.map((s) => {
            const Comp = SCENES[s.kind];
            if (s.duration <= 0) return null; // guard disabled beats
            return (
              <Sequence key={s.id} from={s.from} durationInFrames={s.duration} name={`${s.id} (${s.kind})`}>
                {Comp ? <Comp p={s.props ?? {}} dur={s.duration} /> : <Missing kind={s.kind} />}
                {debug ? <DebugOverlay label={`${s.id} ${s.kind}`} /> : null}
              </Sequence>
            );
          })}
          <Captions captions={ct.captions} />
          {ct.voice?.length ? <VoiceCaptions voice={ct.voice} /> : null}
          <Finish />
        </AbsoluteFill>
        {ct.music.map((m, i) => (
          <Sequence key={`m${i}`} from={m.from} durationInFrames={m.dur} layout="none">
            <Audio src={resolveAsset(assetBase, m.src)} startFrom={Math.round(m.trimSec * ct.fps)} volume={volumeFn(m.volumeKeys, m.from, duck)} />
          </Sequence>
        ))}
        {(ct.voice ?? []).map((v, i) => (
          <Sequence key={`v${i}`} from={v.from} layout="none">
            <Audio src={resolveAsset(assetBase, v.src)} volume={v.vol ?? 1} />
          </Sequence>
        ))}
        {ct.sfx.map(([f, name, vol, durSec], i) =>
          sfxFiles[name] ? (
            <Sequence key={`s${i}`} from={f} durationInFrames={Math.max(1, Math.round(durSec * ct.fps))} layout="none">
              <Audio src={resolveAsset(assetBase, sfxFiles[name])} volume={vol} />
            </Sequence>
          ) : null,
        )}
      </FormatContext.Provider>
    </FilmContext.Provider>
  );
};

/** Poster: split before/after on the accent line plus one line of copy (a composition, not a frame grab). */
const PosterInner: React.FC<{ before?: string; after?: string; copy: string }> = ({ before, after, copy }) => {
  const asset = useAsset();
  const { w, h, vertical, inner } = useFormat();
  const split = vertical ? h * 0.5 : w * 0.5;
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      {before && (
        <div style={{ position: "absolute", left: 0, top: 0, width: vertical ? w : split, height: vertical ? split : h, overflow: "hidden" }}>
          <Img src={asset(before)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "grayscale(0.6) brightness(0.75)" }} />
        </div>
      )}
      {after && (
        <div style={{ position: "absolute", left: vertical ? 0 : split, top: vertical ? split : 0, right: 0, bottom: 0, overflow: "hidden" }}>
          <Img src={asset(after)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
      )}
      <div style={{ position: "absolute", background: C.accent, boxShadow: `0 0 30px ${C.accent}`, ...(vertical ? { left: 0, right: 0, top: split - 4, height: 8 } : { top: 0, bottom: 0, left: split - 4, width: 8 }) }} />
      <div style={{ position: "absolute", left: inner.x, right: w - inner.x - inner.w, bottom: inner.y, textShadow: "0 4px 30px rgba(0,0,0,0.85)" }}>
        <Headline text={copy} at={-30} size={vertical ? 110 : 120} />
      </div>
    </AbsoluteFill>
  );
};

export const Poster: React.FC<FilmProps & { cut: string; fmt: Fmt }> = ({ timeline, takes, assetBase, cut, fmt }) => {
  const ct = timeline.cuts.find((c) => c.name === cut) as CutTimeline;
  const ba = ct.scenes.find((s) => s.kind === "before_after");
  const poster = (timeline as any).posters?.[cut] ?? {};
  return (
    <FilmContext.Provider value={{ assetBase, takes, debug: false }}>
      <FormatContext.Provider value={formatInfo(fmt)}>
        <PosterInner before={poster.before ?? ba?.props.before} after={poster.after ?? ba?.props.after} copy={poster.copy ?? ba?.props.headline ?? timeline.project} />
        <Finish />
      </FormatContext.Provider>
    </FilmContext.Provider>
  );
};
