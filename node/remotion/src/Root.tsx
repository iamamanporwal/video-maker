import React from "react";
import { Composition, getInputProps } from "remotion";
import { Film, Poster } from "./Film";
import "./generated/brand";
import defaults from "./generated/default-props.json";
import { SIZES } from "./lib/layout";
import type { FilmProps, Fmt } from "./types";

/**
 * Compositions are generated from timeline.json: one per cut x format ("hero-16x9"), plus "Poster-hero-16x9".
 * Python passes the project's timeline, takes and asset server URL as input props.
 */
export const RemotionRoot: React.FC = () => {
  const input = getInputProps() as Partial<FilmProps>;
  const props: FilmProps = input && input.timeline ? (input as FilmProps) : (defaults as unknown as FilmProps);
  return (
    <>
      {props.timeline.cuts.flatMap((ct) =>
        ct.formats.flatMap((fmt: Fmt) => {
          const [w, h] = SIZES[fmt];
          return [
            <Composition
              key={`${ct.name}-${fmt}`}
              id={`${ct.name}-${fmt}`}
              component={Film as any}
              durationInFrames={ct.durationInFrames}
              fps={ct.fps}
              width={w}
              height={h}
              defaultProps={{ ...props, cut: ct.name, fmt }}
            />,
            <Composition
              key={`Poster-${ct.name}-${fmt}`}
              id={`Poster-${ct.name}-${fmt}`}
              component={Poster as any}
              durationInFrames={1}
              fps={ct.fps}
              width={w}
              height={h}
              defaultProps={{ ...props, cut: ct.name, fmt }}
            />,
          ];
        }),
      )}
    </>
  );
};
