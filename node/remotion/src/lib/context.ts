import { createContext, useContext } from "react";
import type { Take } from "../types";
import { resolveAsset } from "./anim";

export type FilmCtx = { assetBase: string; takes: Record<string, Take>; debug: boolean };

export const FilmContext = createContext<FilmCtx>({ assetBase: "", takes: {}, debug: false });

export const useFilm = () => useContext(FilmContext);

/** Resolve an asset path, or a take output reference like "take:sedan/out.jpg". */
export const useAsset = () => {
  const { assetBase, takes } = useFilm();
  return (p?: string) => {
    if (!p) return "";
    const m = /^take:([^/]+)\/(.+)$/.exec(p);
    if (m) {
      const t = takes[m[1]];
      const rel = t?.outputs?.[m[2]] ?? `capture/${m[1]}/${m[2]}`;
      return resolveAsset(assetBase, rel);
    }
    return resolveAsset(assetBase, p);
  };
};
