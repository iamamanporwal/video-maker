import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as loadVT } from "@remotion/google-fonts/VT323";
import { loadFont as loadUrbanist } from "@remotion/google-fonts/Urbanist";
import { noise2D } from "@remotion/noise";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import React, { createContext, useContext, useLayoutEffect, useMemo } from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, Loop, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { TeapotGeometry } from "three/examples/jsm/geometries/TeapotGeometry.js";
import { ease, tween } from "../lib/anim";

/** "I miss Steve": a 89 s vertical mini-documentary. Archival stills in letterbox bars that start as white paper
 *  and turn black; the picture starts black-and-white and colours in as the story moves to the present.
 *  Every cut is keyed to the narrator's real word times (props.json from projects/shorts/i-miss-steve/timeline.py).
 *  Audio (VO, music with ducking, period foley) is mixed here; the master is loudness-normalised afterwards. */

const { fontFamily: SERIF } = loadPlayfair("normal", { weights: ["400", "600", "800"], subsets: ["latin"] });
const { fontFamily: SERIF_I } = loadPlayfair("italic", { weights: ["400", "600"], subsets: ["latin"] });
const { fontFamily: MONO } = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] });
const { fontFamily: VCR } = loadVT("normal", { weights: ["400"], subsets: ["latin"] });
const { fontFamily: URB } = loadUrbanist("normal", { weights: ["800"], subsets: ["latin"] });

type Word = [number, number, string];
type Line = { src: string; start: number; dur: number; text: string; words: Word[] };
export type SteveProps = { fps: number; durationInFrames: number; lines: Line[]; music: { src: string; trackStart: number } };

const W = 1080, BAR = 300, WIN_H = 1920 - 2 * BAR;
const PAPER = "#ECE7DC", INK = "#0A0A0A", CREAM = "#F3EBDD", LIME = "#D4F77C";

// --------------------------------------------------------------------------- timing
const Ctx = createContext<{ p: SteveProps; A: Record<string, number> }>(null as any);
const useT = () => useContext(Ctx);
/** Absolute start (s) of the enclosing Shot, so scenes can use film-time anchors. */
const ShotStart = createContext(0);
const useSec = () => useCurrentFrame() / 30 + useContext(ShotStart);

const anchors = (p: SteveProps) => {
  const L = (i: number) => p.lines[i].start;
  const Wd = (i: number, j: number) => p.lines[i].words[j][0];
  const E = (i: number) => p.lines[i].start + p.lines[i].dur;
  return {
    from1: Wd(0, 5), l2: L(1), finished: Wd(1, 11), l2end: E(1), l3: L(2), next: Wd(2, 9), l4: L(3), pixar: Wd(3, 13),
    l5: L(4), betting: Wd(4, 6), l6: L(5), y1995: Wd(6, 2), toy: Wd(6, 3), l7end: E(6), l8: L(7), l9: L(8), form: Wd(8, 5),
    l10: L(9), thirty: Wd(9, 2), d3: Wd(9, 5), l11: L(10), steep: Wd(10, 2), ideas: Wd(10, 5), trapped: Wd(10, 6),
    l12: L(11), design: Wd(11, 3), design2: Wd(11, 14), l12end: E(11), l13: L(12), vi3w: Wd(12, 1), building: Wd(12, 2),
    sketch: Wd(12, 7), watch: Wd(12, 10), right: Wd(12, 14), l13end: E(12), l14: L(13), anyone: Wd(13, 11),
    l15: L(14), one: Wd(14, 4), l15end: E(14), end: p.durationInFrames / 30,
  };
};

// Piecewise-linear keyframes over seconds.
const keys = (t: number, k: [number, number][]) =>
  interpolate(t, k.map((x) => x[0]), k.map((x) => x[1]), { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const rnd = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

// --------------------------------------------------------------------------- colour script
/** c: colour amount (0 = B&W), sepia, contrast, grain, bars (0 paper .. 1 black), past (period FX amount). */
const grade = (t: number, A: Record<string, number>) => ({
  c: keys(t, [[0, 0], [A.l3, 0], [A.l5, 0.12], [A.toy - 0.1, 0.22], [A.toy + 1.3, 1], [A.l10 - 0.2, 1], [A.l10 + 0.6, 0.72],
              [A.l12, 0.72], [A.l12 + 1.5, 0.95], [A.l13, 1]]),
  sepia: keys(t, [[0, 0.08], [A.l3, 0.15], [A.l6, 0.4], [A.toy - 0.1, 0.45], [A.toy + 1.3, 0], [A.l10, 0]]),
  contrast: keys(t, [[0, 1.22], [A.toy, 1.12], [A.toy + 1.3, 1.04], [A.l10 + 0.6, 1.08], [A.l13, 1.03]]),
  grain: keys(t, [[0, 0.3], [A.toy, 0.26], [A.toy + 1.5, 0.12], [A.l13, 0.05]]),
  bars: keys(t, [[A.toy - 0.15, 0], [A.toy + 1.1, 1]]),
  past: keys(t, [[0, 1], [A.toy, 1], [A.toy + 1.5, 0.25], [A.l10 + 0.5, 0.08], [A.l13, 0]]),
});

const gradeFilter = (g: ReturnType<typeof grade>, cool = 0) =>
  `grayscale(${1 - g.c}) sepia(${g.sepia}) contrast(${g.contrast}) saturate(${1 + 0.08 * g.c})` +
  (cool ? ` hue-rotate(${-6 * cool}deg) brightness(${1 - 0.06 * cool})` : "");

// --------------------------------------------------------------------------- building blocks
/** A shot: a Sequence from `from` (s) to `to` (s), fading in over `xf` frames on top of the previous shot. */
const Shot: React.FC<{ from: number; to: number; xf?: number; tail?: number; children: React.ReactNode; raw?: boolean }> = (
  { from, to, xf = 8, tail = 10, children }) => {
  const f0 = Math.round(from * 30), f1 = Math.round(to * 30) + tail;
  return (
    <Sequence from={f0} durationInFrames={Math.max(1, f1 - f0)} layout="none">
      <ShotStart.Provider value={f0 / 30}><Fade xf={xf}>{children}</Fade></ShotStart.Provider>
    </Sequence>
  );
};
const Fade: React.FC<{ xf: number; children: React.ReactNode }> = ({ xf, children }) => {
  const f = useCurrentFrame();
  const o = xf ? tween(f, 0, xf, 0, 1, "inOutCubic") : 1;
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

/** Ken Burns still. s0->s1 scale, origin in %, optional drift (px). */
const Photo: React.FC<{ src: string; s0?: number; s1?: number; ox?: number; oy?: number; dx?: number; dy?: number;
  pos?: string; fit?: "cover" | "contain"; bg?: string; dim?: number; filter?: string }> = (
  { src, s0 = 1.04, s1 = 1.14, ox = 50, oy = 40, dx = 0, dy = 0, pos = "50% 50%", fit = "cover", bg = INK, dim = 0, filter }) => {
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = ease("calm")(Math.min(1, f / durationInFrames));
  return (
    <AbsoluteFill style={{ background: bg, overflow: "hidden" }}>
      <Img src={staticFile(`img/${src}.jpg`)} style={{
        width: "100%", height: "100%", objectFit: fit, objectPosition: pos, filter,
        transform: `translate(${dx * p}px, ${dy * p}px) scale(${s0 + (s1 - s0) * p})`, transformOrigin: `${ox}% ${oy}%`,
      }} />
      {dim > 0 && <AbsoluteFill style={{ background: INK, opacity: dim }} />}
    </AbsoluteFill>
  );
};

/** Dymo-style paper label, typed on. Sits top-left of the window. */
const Stamp: React.FC<{ text: string; at: number; until: number }> = ({ text, at, until }) => {
  const t = useSec();
  if (t < at || t > until + 0.4) return null;
  const n = Math.floor(Math.min(text.length, (t - at) * 26));
  const o = t > until ? 1 - (t - until) / 0.4 : 1;
  return (
    <div style={{ position: "absolute", left: 56, top: BAR + 64, opacity: o, transform: `rotate(-1.2deg)` }}>
      <div style={{ background: PAPER, color: INK, fontFamily: MONO, fontWeight: 500, fontSize: 30, letterSpacing: "0.22em",
                    padding: "12px 20px 10px", boxShadow: "0 6px 24px #0007", textTransform: "uppercase" }}>
        {text.slice(0, n)}<span style={{ opacity: n < text.length ? 1 : 0 }}>▌</span>
      </div>
    </div>
  );
};

// --------------------------------------------------------------------------- texture
const Grain: React.FC<{ amount: number }> = ({ amount }) => {
  const f = useCurrentFrame();
  if (amount < 0.01) return null;
  return (
    <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: amount, pointerEvents: "none" }}>
      <svg width={W} height={WIN_H}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves={2} seed={f % 97} />
          <feColorMatrix type="saturate" values="0" /></filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </AbsoluteFill>
  );
};

/** Dust specks and the odd vertical scratch: seeded per frame, scaled by `past`. */
const Dust: React.FC<{ amount: number }> = ({ amount }) => {
  const f = useCurrentFrame();
  if (amount < 0.05) return null;
  const specks = Array.from({ length: 7 }, (_, i) => i).filter((i) => rnd(f * 13 + i) < 0.35 * amount);
  const scratch = rnd(f * 7.3) < 0.18 * amount;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {specks.map((i) => (
        <div key={i} style={{ position: "absolute", left: rnd(f * 3 + i) * W, top: rnd(f * 5 + i * 2) * WIN_H,
                              width: 2 + rnd(f + i) * 5, height: 2 + rnd(f * 2 + i) * 4, borderRadius: 4,
                              background: rnd(i + f) > 0.5 ? "#000" : "#fff", opacity: 0.55 }} />
      ))}
      {scratch && <div style={{ position: "absolute", left: rnd(f * 9.1) * W, top: 0, width: 1.5, height: WIN_H,
                                background: "#fff", opacity: 0.25 }} />}
    </AbsoluteFill>
  );
};

const Vignette: React.FC<{ k?: number }> = ({ k = 0.75 }) => (
  <AbsoluteFill style={{ pointerEvents: "none",
    background: `radial-gradient(ellipse 75% 62% at 50% 46%, transparent 55%, rgba(0,0,0,${k}) 100%)` }} />
);

const Scanlines: React.FC<{ o: number }> = ({ o }) => (o < 0.01 ? null : (
  <AbsoluteFill style={{ pointerEvents: "none", opacity: o,
    background: "repeating-linear-gradient(0deg, rgba(0,0,0,0.35) 0px, rgba(0,0,0,0.35) 1px, transparent 2px, transparent 4px)" }} />
));

/** VHS tracking burst: horizontal tear (displacement along noise bands) + RGB split. g = 0..1. */
const VHSFilter: React.FC<{ g: number }> = ({ g }) => {
  const f = useCurrentFrame();
  return (
    <svg width={0} height={0} style={{ position: "absolute" }}>
      <filter id="vhs" x="-4%" y="0%" width="108%" height="100%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency="0.0004 0.045" numOctaves={1} seed={f} result="n" />
        <feComponentTransfer in="n" result="n2"><feFuncG type="linear" slope={0} intercept={0.5} /></feComponentTransfer>
        <feDisplacementMap in="SourceGraphic" in2="n2" scale={90 * g} xChannelSelector="R" yChannelSelector="G" result="d" />
        <feColorMatrix in="d" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
        <feOffset in="r" dx={10 * g} result="r2" />
        <feColorMatrix in="d" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0" result="gb" />
        <feOffset in="gb" dx={-10 * g} result="gb2" />
        <feBlend in="r2" in2="gb2" mode="screen" />
      </filter>
    </svg>
  );
};

// --------------------------------------------------------------------------- 3D
const Env: React.FC = () => {
  const { gl, scene } = useThree();
  useLayoutEffect(() => {
    const pm = new THREE.PMREMGenerator(gl);
    scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    pm.dispose();
  }, [gl, scene]);
  return null;
};

const Cam: React.FC<{ pos: [number, number, number]; look?: [number, number, number]; fov?: number }> = (
  { pos, look = [0, 0, 0], fov = 32 }) => {
  const { camera } = useThree();
  useLayoutEffect(() => {
    camera.position.set(...pos);
    (camera as THREE.PerspectiveCamera).fov = fov;
    camera.lookAt(...look);
    camera.updateProjectionMatrix();
  });
  return null;
};

/** Green-phosphor wireframe teapot on a CRT: "computer cartoons". */
const CRTTeapot: React.FC = () => {
  const f = useCurrentFrame();
  const wire = useMemo(() => new THREE.WireframeGeometry(new TeapotGeometry(1, 6)), []);
  const draw = Math.min(1, f / 24);
  return (
    <AbsoluteFill style={{ background: "#020402" }}>
      <AbsoluteFill style={{ inset: 70, top: 170, bottom: 170, borderRadius: 60, overflow: "hidden",
                             background: "radial-gradient(ellipse at 50% 45%, #0c1a0e 0%, #020402 75%)",
                             boxShadow: "inset 0 0 120px #000, 0 0 0 10px #151515, 0 0 0 22px #0b0b0b" }}>
        <ThreeCanvas width={W - 140} height={WIN_H - 340} gl={{ antialias: true }}>
          <Cam pos={[0, 1.1, 5.4 - f * 0.006]} look={[0, 0.25, 0]} fov={34} />
          <lineSegments geometry={wire} rotation={[0.1, f * 0.035, 0]} scale={draw}>
            <lineBasicMaterial color="#7CFF8A" transparent opacity={0.85} />
          </lineSegments>
        </ThreeCanvas>
        <div style={{ position: "absolute", left: 40, top: 34, fontFamily: VCR, fontSize: 44, color: "#7CFF8A",
                      textShadow: "0 0 12px #7CFF8A" }}>RENDER 01 / FRAME {String(1 + Math.floor(f / 2)).padStart(4, "0")}</div>
        <Scanlines o={0.8} />
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, transparent 50%, #000c 100%)" }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const checker = () => {
  const c = document.createElement("canvas");
  c.width = c.height = 2;
  const g = c.getContext("2d")!;
  g.fillStyle = "#E9E1D2"; g.fillRect(0, 0, 2, 2);
  g.fillStyle = "#2B2622"; g.fillRect(0, 0, 1, 1); g.fillRect(1, 1, 1, 1);
  const t = new THREE.CanvasTexture(c);
  t.magFilter = THREE.NearestFilter;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(14, 14);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
};

/** The same teapot, fully rendered: glossy red on the classic checkerboard. "Made entirely on a computer." */
const RenderedTeapot: React.FC = () => {
  const f = useCurrentFrame();
  const geo = useMemo(() => new TeapotGeometry(1, 24), []);
  const wire = useMemo(() => new THREE.WireframeGeometry(new TeapotGeometry(1, 6)), []);
  const tex = useMemo(checker, []);
  const solid = tween(f, 4, 22, 0, 1, "inOutCubic");
  const rot = 0.5 + f * 0.012;
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 30%, #3a2a20 0%, #0d0a08 70%)" }}>
      <ThreeCanvas width={W} height={WIN_H} gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }} shadows>
        <Env />
        <Cam pos={[0, 1.9 - f * 0.002, 6.2 - f * 0.009]} look={[0, 0.45, 0]} fov={30} />
        <ambientLight intensity={0.25} />
        <spotLight position={[3, 6, 3]} angle={0.5} penumbra={0.6} intensity={140} color="#FFE6C8" castShadow
                   shadow-mapSize-width={1024} shadow-mapSize-height={1024} />
        <pointLight position={[-4, 2, -2]} intensity={30} color="#9EC9FF" />
        <mesh geometry={geo} position={[0, 0.78, 0]} rotation={[0, rot, 0]} castShadow>
          <meshPhysicalMaterial color="#B3121E" roughness={0.18} clearcoat={1} clearcoatRoughness={0.05}
                                transparent opacity={solid} />
        </mesh>
        <lineSegments geometry={wire} position={[0, 0.78, 0]} rotation={[0, rot, 0]}>
          <lineBasicMaterial color="#7CFF8A" transparent opacity={1 - solid} />
        </lineSegments>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.22, 0]} receiveShadow>
          <planeGeometry args={[30, 30]} />
          <meshStandardMaterial map={tex} roughness={0.35} metalness={0} transparent opacity={0.25 + 0.75 * solid} />
        </mesh>
      </ThreeCanvas>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, #0d0a08 0%, transparent 22%, transparent 70%, #0d0a08 100%)" }} />
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- scenes
const Years: React.FC<{ t0: number; land: number }> = ({ t0, land }) => {
  const t = useSec();
  const p = interpolate(t, [t0 + 0.2, land], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease("outCubic") });
  const yr = 1986 + Math.round(p * 9);
  const tick = (p * 9) % 1;
  const landed = t >= land;
  const k = landed ? tween(t * 30, land * 30, 12, 1.12, 1, "outExpo") : 1;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, #2a2622 0%, ${INK} 75%)`, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill style={{ opacity: 0.18, background: "repeating-linear-gradient(180deg, transparent 0 58px, #d9cdb5 58px 60px)" }} />
      <div style={{ fontFamily: SERIF, fontWeight: 800, fontSize: 290, color: CREAM, letterSpacing: "-0.02em",
                    transform: `translateY(${landed ? 0 : (tick < 0.15 ? 18 * (1 - tick / 0.15) : 0)}px) scale(${k})`,
                    textShadow: "0 10px 60px #000" }}>{yr}</div>
      <div style={{ position: "absolute", top: WIN_H / 2 + 170, fontFamily: MONO, fontSize: 28, letterSpacing: "0.5em", color: "#B9AE9A" }}>
        {landed ? "" : "YEAR AFTER YEAR"}
      </div>
    </AbsoluteFill>
  );
};

const TitleCard: React.FC = () => {
  const f = useCurrentFrame();
  const title = "Toy Story";
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 0%, #4a2f12 0%, #120b05 55%, #050302 100%)" }}>
      {/* projector beam */}
      <AbsoluteFill style={{ clipPath: "polygon(44% 0, 56% 0, 100% 100%, 0 100%)", filter: "blur(18px)",
                             background: "linear-gradient(180deg, #FFE7B866 0%, #FFD08A22 55%, transparent 100%)",
                             opacity: 0.6 + 0.08 * Math.sin(f * 0.9) }} />
      {Array.from({ length: 40 }, (_, i) => {
        const y = (rnd(i) * WIN_H + f * (0.6 + rnd(i + 9))) % WIN_H;
        const spread = 0.12 + 0.88 * (y / WIN_H);
        const x = W / 2 + (rnd(i + 3) - 0.5) * W * spread + Math.sin(f * 0.05 + i) * 8;
        return <div key={i} style={{ position: "absolute", left: x, top: y, width: 3, height: 3, borderRadius: 3,
                                     background: "#FFE9C4", opacity: 0.25 + 0.4 * rnd(i + 5) }} />;
      })}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex" }}>
          {title.split("").map((ch, i) => {
            const k = tween(f, 2 + i * 2, 18, 0, 1, "outExpo");
            return <span key={i} style={{ fontFamily: SERIF_I, fontWeight: 600, fontSize: 168, color: CREAM, whiteSpace: "pre",
                                          opacity: k, filter: `blur(${(1 - k) * 12}px)`, transform: `translateY(${(1 - k) * 30}px)`,
                                          textShadow: "0 0 50px #FFB24D66" }}>{ch}</span>;
          })}
        </div>
        <div style={{ marginTop: 18, fontFamily: MONO, fontSize: 30, letterSpacing: "0.45em", color: "#E9C78F",
                      opacity: tween(f, 26, 16, 0, 1, "outCubic") }}>NOVEMBER 22, 1995</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const PANELS = ["Subdivision Surface", "UV Unwrap", "Retopology", "Weight Paint", "Shader Nodes", "Normal Bake", "Modifiers",
  "Edge Loops", "Rigging", "Bevel Profile", "Topology", "Mesh Cleanup", "Vertex Groups", "Displacement", "Smooth Groups",
  "Render Passes", "Light Paths", "Constraints", "Texture Bake", "Decimate", "Boolean", "Armature", "Keyframes", "Sculpt Layers"];

/** Present day: an idea (a hand-drawn bulb) gets buried under tool panels, then caged. */
const Complexity: React.FC = () => {
  const t = useSec();
  const { A } = useT();
  const draw = keys(t, [[A.l10 + 0.6, 0], [A.thirty + 0.8, 1]]);
  const cage = keys(t, [[A.trapped - 0.05, 0], [A.trapped + 0.35, 1]]);
  const stmts: [number, number, string][] = [[A.l11, A.steep, "Expensive software."], [A.steep, A.ideas, "Steep learning curves."],
    [A.ideas, A.l12 + 1, "Ideas, trapped behind complexity."]];
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 55%, #1d2228 0%, #0b0d10 75%)" }}>
      {/* the idea */}
      <svg width={W} height={WIN_H} style={{ position: "absolute" }}>
        <g transform={`translate(${W / 2 - 110}, ${WIN_H / 2 - 120}) scale(2.2)`} fill="none" stroke={CREAM} strokeWidth={4}
           strokeLinecap="round" strokeLinejoin="round" pathLength={1} style={{ opacity: 1 - 0.55 * cage }}>
          <path d="M50 8 C24 8 10 28 12 48 C14 66 30 74 32 90 L68 90 C70 74 86 66 88 48 C90 28 76 8 50 8 Z" pathLength={1}
                strokeDasharray={1} strokeDashoffset={1 - draw} />
          <path d="M36 100 L64 100 M40 110 L60 110" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
          <path d="M50 -10 L50 -22 M16 0 L8 -8 M84 0 L92 -8" pathLength={1} strokeDasharray={1}
                strokeDashoffset={1 - keys(t, [[A.thirty + 0.6, 0], [A.thirty + 1.1, 1]])} />
        </g>
      </svg>
      {/* panels pile in from "3D" */}
      {PANELS.map((name, i) => {
        const at = A.d3 + 0.1 + i * 0.16;
        if (t < at) return null;
        const k = tween(t * 30, at * 30, 9, 0, 1, "outBack");
        const col = i % 3, row = Math.floor(i / 3);
        const x = 40 + col * 340 + (rnd(i) - 0.5) * 60, y = 120 + row * 128 + (rnd(i + 7) - 0.5) * 40;
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: 300, padding: "14px 16px", borderRadius: 10,
                                background: "#2a2f36F2", border: "1px solid #ffffff1c", boxShadow: "0 12px 30px #0009",
                                transform: `scale(${k}) rotate(${(rnd(i + 2) - 0.5) * 6}deg)`, opacity: Math.min(1, k) }}>
            <div style={{ fontFamily: MONO, fontSize: 19, color: "#cfd6de", marginBottom: 10 }}>{name}</div>
            {[0, 1].map((j) => (
              <div key={j} style={{ height: 6, borderRadius: 3, background: "#ffffff14", marginTop: 8 }}>
                <div style={{ width: `${20 + rnd(i * 3 + j) * 70}%`, height: 6, borderRadius: 3, background: "#7a8796" }} />
              </div>
            ))}
          </div>
        );
      })}
      {/* cage */}
      {cage > 0 && Array.from({ length: 9 }, (_, i) => (
        <div key={i} style={{ position: "absolute", left: 90 + i * 112, top: 0, width: 10, height: WIN_H * cage,
                              background: "linear-gradient(90deg,#555,#bbb,#444)", boxShadow: "0 0 20px #000" }} />
      ))}
      <AbsoluteFill style={{ background: "#0b0d10", opacity: keys(t, [[A.l11 - 0.1, 0], [A.l11 + 0.3, 0.45]]) }} />
      {stmts.map(([a, b, s]) => (t >= a && t < b) && (
        <div key={s} style={{ position: "absolute", left: 60, right: 60, top: WIN_H - 330, textAlign: "center",
                              fontFamily: SERIF, fontWeight: 600, fontSize: 74, lineHeight: 1.08, color: CREAM,
                              letterSpacing: "-0.015em", textShadow: "0 6px 40px #000",
                              opacity: tween(t * 30, a * 30, 8, 0, 1, "outCubic"),
                              transform: `translateY(${tween(t * 30, a * 30, 14, 24, 0, "outExpo")}px)` }}>{s}</div>
      ))}
    </AbsoluteFill>
  );
};

const Quote: React.FC = () => {
  const t = useSec();
  const { p, A } = useT();
  const words = p.lines[11].words;
  const first = words.slice(3, 14), second = words.slice(14);
  const W2 = (w: Word, i: number, size: number, italic = true) => (
    <span key={i} style={{ fontFamily: italic ? SERIF_I : SERIF, fontSize: size, color: CREAM, whiteSpace: "pre",
                           opacity: tween(t * 30, (w[0] - 0.05) * 30, 7, 0, 1, "outCubic") }}>{w[2].replace(/\.+$/, "")}{" "}</span>
  );
  return (
    <AbsoluteFill>
      <Photo src="jobs2010" s0={1.08} s1={1.2} ox={42} oy={22} pos="35% 30%" />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, transparent 30%, #000000d9 64%, #000 100%)" }} />
      <div style={{ position: "absolute", left: 70, right: 70, top: WIN_H - 560 }}>
        <div style={{ fontFamily: SERIF, fontSize: 120, color: "#E9C78F", lineHeight: 0.6, opacity: t >= A.design - 0.1 ? 1 : 0 }}>“</div>
        <div style={{ lineHeight: 1.16 }}>{first.map((w, i) => W2(w, i, 58))}</div>
        <div style={{ marginTop: 22, lineHeight: 1.05 }}>{second.map((w, i) => W2(w, i + 20, 84, false))}</div>
        <div style={{ marginTop: 26, fontFamily: MONO, fontSize: 26, letterSpacing: "0.3em", color: "#B9AE9A",
                      opacity: tween(t * 30, (A.l12end + 0.1) * 30, 12, 0, 1) }}>— STEVE JOBS, 2003</div>
      </div>
    </AbsoluteFill>
  );
};

const Logo: React.FC<{ size: number }> = ({ size }) => (
  <Img src={staticFile("img/vi3w-logo.png")} style={{ width: size, height: size, mixBlendMode: "screen" }} />
);

const Vi3W: React.FC = () => {
  const t = useSec();
  const { A } = useT();
  const s0 = Math.round(useContext(ShotStart) * 30);
  const cardIn = tween(t * 30, A.building * 30, 22, 0, 1, "outExpo");
  const logoK = tween(t * 30, (A.vi3w - 0.15) * 30, 18, 0.6, 1, "outBack");
  const segs: [number, number, number][] = [[A.building, A.watch, 0], [A.watch, A.right, 12.6], [A.right, A.l13end + 1.2, 22.0]];
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, #12161c 0%, #050607 70%)" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: interpolate(cardIn, [0, 1], [WIN_H / 2 - 230, 70]),
                    display: "flex", flexDirection: "column", alignItems: "center",
                    transform: `scale(${logoK * interpolate(cardIn, [0, 1], [1, 0.55])})`, transformOrigin: "50% 0%",
                    opacity: tween(t * 30, (A.vi3w - 0.15) * 30, 10, 0, 1) }}>
        <Logo size={300} />
        <div style={{ fontFamily: URB, fontWeight: 800, fontSize: 130, color: "#fff", letterSpacing: "-0.035em", marginTop: -10 }}>Vi3W</div>
      </div>
      {cardIn > 0 && (
        <div style={{ position: "absolute", left: 30, width: W - 60, top: 400 + (1 - cardIn) * 500, height: 640, borderRadius: 28,
                      overflow: "hidden", opacity: cardIn, border: "1px solid #ffffff24",
                      boxShadow: `0 30px 90px #000, 0 0 60px ${LIME}22` }}>
          {segs.map(([a, b, src], i) => {
            const fa = Math.round(a * 30), fb = Math.round(b * 30);
            const local = t * 30 - fa;
            return (
              <Sequence key={i} from={fa - s0} durationInFrames={fb - fa} layout="none">
                <AbsoluteFill style={{ transform: `scale(${1.02 + 0.0016 * local})` }}>
                  <OffthreadVideo src={staticFile("clips/demo3.mp4")} startFrom={Math.round(src * 30)} muted
                                  style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </AbsoluteFill>
              </Sequence>
            );
          })}
        </div>
      )}
    </AbsoluteFill>
  );
};

const MODELS = ["robot", "panda", "dragon", "anime", "frog", "jet", "deer", "cat", "baddie", "brickguy", "cups", "noob"];

const Gallery: React.FC = () => {
  const f = useCurrentFrame();
  const z = 1 + f * 0.0004;
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 35%, #2c2116 0%, #0c0906 70%)" }}>
      <AbsoluteFill style={{ transform: `scale(${z})` }}>
        {MODELS.map((m, i) => {
          const col = i % 3, row = Math.floor(i / 3);
          const k = tween(f, 4 + i * 3, 14, 0, 1, "outBack");
          return (
            <div key={m} style={{ position: "absolute", left: 10 + col * 353, top: 40 + row * 300, width: 360, height: 360,
                                  transform: `scale(${k})`, opacity: Math.min(1, k) }}>
              <Loop durationInFrames={120}>
                <OffthreadVideo src={staticFile(`tt/${m}.webm`)} transparent muted startFrom={(i * 37) % 120}
                                style={{ width: 360, height: 360 }} />
              </Loop>
            </div>
          );
        })}
      </AbsoluteFill>
      <div style={{ position: "absolute", bottom: 150, left: 0, right: 0, textAlign: "center", fontFamily: MONO, fontSize: 26,
                    letterSpacing: "0.32em", color: "#E9C78F", opacity: tween(f, 50, 20, 0, 1) }}>EVERY MODEL HERE WAS MADE IN Vi3W</div>
    </AbsoluteFill>
  );
};

const EndCard: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: INK, alignItems: "center", justifyContent: "center" }}>
      <div style={{ opacity: tween(f, 0, 16, 0, 1), transform: `scale(${tween(f, 0, 30, 0.9, 1, "outExpo")})`,
                    display: "flex", flexDirection: "column", alignItems: "center" }}>
        <Logo size={260} />
        <div style={{ fontFamily: URB, fontWeight: 800, fontSize: 120, color: "#fff", letterSpacing: "-0.035em", marginTop: -6 }}>Vi3W</div>
        <div style={{ fontFamily: SERIF_I, fontSize: 44, color: CREAM, marginTop: 6, opacity: tween(f, 12, 16, 0, 1) }}>
          Sketch it. See it in 3D.</div>
        <div style={{ fontFamily: MONO, fontWeight: 500, fontSize: 44, letterSpacing: "0.12em", color: LIME, marginTop: 34,
                      opacity: tween(f, 22, 16, 0, 1) }}>Vi3W.in</div>
      </div>
      <div style={{ position: "absolute", bottom: 90, fontFamily: SERIF_I, fontSize: 32, color: "#A89F90",
                    opacity: tween(f, 40, 24, 0, 1) }}>In memory of Steve Jobs, 1955 – 2011</div>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- subtitles
type Chunk = { a: number; b: number; text: string };
const chunks = (lines: Line[]): Chunk[] => {
  const out: Chunk[] = [];
  for (const l of lines) {
    let cur: Word[] = [];
    const push = () => { if (cur.length) out.push({ a: cur[0][0], b: cur[cur.length - 1][1], text: cur.map((w) => w[2]).join(" ") }); cur = []; };
    for (const w of l.words) {
      cur.push(w);
      if (/[.,?!…]$/.test(w[2]) || cur.length >= 6) push();
    }
    push();
  }
  return out;
};

const Subtitles: React.FC = () => {
  const t = useSec();
  const { p, A } = useT();
  const cs = useMemo(() => chunks(p.lines), [p]);
  const hidden = t < 4.5 || (t >= A.toy - 0.05 && t < A.l8) || (t >= A.l11 && t < A.l12) || (t >= A.design - 0.1 && t < A.l13);
  const c = cs.find((x) => t >= x.a - 0.05 && t < x.b + 0.3);
  if (hidden || !c) return null;
  const o = Math.min(tween(t * 30, (c.a - 0.05) * 30, 4, 0, 1), 1 - tween(t * 30, (c.b + 0.15) * 30, 4, 0, 1));
  return (
    <div style={{ position: "absolute", left: 70, right: 70, top: BAR + WIN_H - 210, textAlign: "center", opacity: o,
                  fontFamily: SERIF, fontWeight: 600, fontSize: 46, lineHeight: 1.2, color: "#fff",
                  textShadow: "0 2px 4px #000, 0 0 24px #000, 0 0 40px #000c" }}>
      {c.text.replace(/\.\.\.$/, "…").replace(/\.$/, "")}
    </div>
  );
};

// --------------------------------------------------------------------------- bars
const CHAPTERS: [string, string][] = [["l0", "I  ·  THE FALL"], ["l3", "II  ·  THE BET"], ["toy", "III  ·  THE PROOF"],
  ["l10", "IV  ·  THE GAP"], ["l12", "V  ·  THE BELIEF"], ["l13", "VI  ·  THE NEXT CHAPTER"]];

const Bars: React.FC<{ k: number }> = ({ k }) => {
  const t = useSec();
  const { A } = useT();
  const bg = `rgb(${interpolate(k, [0, 1], [236, 8])},${interpolate(k, [0, 1], [231, 8])},${interpolate(k, [0, 1], [220, 8])})`;
  const fg = k < 0.5 ? "#3d3a34" : "#9b968c";
  const idx = CHAPTERS.reduce((acc, [key], i) => (t >= (key === "l0" ? 4.5 : A[key]) ? i : acc), -1);
  const at = idx >= 0 ? (CHAPTERS[idx][0] === "l0" ? 4.5 : A[CHAPTERS[idx][0]]) : 0;
  const o = idx >= 0 && t < A.l15end ? tween(t * 30, at * 30, 14, 0, 1) : 0;
  return (
    <>
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: BAR, background: bg }}>
        <div style={{ position: "absolute", bottom: 26, width: "100%", textAlign: "center", fontFamily: MONO, fontWeight: 500,
                      fontSize: 24, letterSpacing: "0.42em", color: fg, opacity: o }}>{idx >= 0 ? CHAPTERS[idx][1] : ""}</div>
      </div>
      <div style={{ position: "absolute", left: 0, top: BAR + WIN_H, width: W, height: BAR, background: bg }} />
    </>
  );
};

// --------------------------------------------------------------------------- audio
const SFX: [string, string, number][] = [
  ["vhs", "0", 0.9], ["shutter", "from1-0.08", 0.5], ["shutter", "l2-0.5", 0.45], ["burn", "l2end+0.05", 0.7],
  ["typewriter", "next+0.62", 0.45], ["shutter", "l5-0.35", 0.4], ["burn", "l7end-0.5", 0.0],
  ["projector", "l7end-4.4", 0.18], ["riser", "toy-2.6", 0.32], ["burn", "l10-1.2", 0.6], ["burn", "l13-1.1", 0.45],
  ["shutter", "l14-0.85", 0.55],
];
const at = (expr: string, A: Record<string, number>) => {
  if (/^[\d.]+$/.test(expr)) return parseFloat(expr);
  const m = expr.match(/^([a-z][a-z0-9]*)([+-][\d.]+)?$/i)!;
  return A[m[1]] + (m[2] ? parseFloat(m[2]) : 0);
};

const Mix: React.FC = () => {
  const { p, A } = useT();
  const speech = p.lines.map((l) => [l.start, l.start + l.dur] as const);
  const music = (f: number) => {
    const t = f / 30 + 0; // Audio's callback frame is relative to its Sequence (starts at 0)
    let d = Infinity;
    for (const [a, b] of speech) d = Math.min(d, t < a ? a - t : t > b ? t - b : 0);
    const duck = Math.min(1, Math.max(0, (d - 0.05) / 0.4));
    const base = 0.17 + (0.5 - 0.17) * duck;
    const fadeIn = interpolate(t, [0.8, 2.5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    const fadeOut = interpolate(t, [A.end - 3, A.end - 0.2], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    return base * fadeIn * fadeOut;
  };
  return (
    <>
      <Audio src={staticFile(p.music.src)} startFrom={Math.round(p.music.trackStart * 30)} volume={music} />
      {p.lines.map((l, i) => (
        <Sequence key={i} from={Math.round(l.start * 30)} layout="none"><Audio src={staticFile(l.src)} volume={1} /></Sequence>
      ))}
      {SFX.filter(([, , v]) => v > 0).map(([n, e, v], i) => (
        <Sequence key={`s${i}`} from={Math.max(0, Math.round(at(e, A) * 30))} layout="none">
          <Audio src={staticFile(`sfx/${n}.mp3`)} volume={v} />
        </Sequence>
      ))}
    </>
  );
};

// --------------------------------------------------------------------------- film
const GLITCH: [string, number, number][] = [["0.55", 0.75, 1], ["l2end-0.05", 0.5, 0.8], ["pixar-0.05", 0.22, 0.35],
  ["betting-0.12", 0.3, 0.6], ["l10-0.3", 0.55, 1], ["l13-0.3", 0.35, 0.5]];

export const IMissSteve: React.FC<SteveProps> = (p) => {
  const f = useCurrentFrame();
  const t = f / 30;
  const A = useMemo(() => anchors(p), [p]);
  const g = grade(t, A);
  const glitch = Math.max(0, ...GLITCH.map(([e, d, k]) => {
    const a = at(e, A), x = (t - a) / d;
    return x >= 0 && x <= 1 ? k * Math.sin(Math.PI * x) ** 0.6 : 0;
  }));
  // VHS power-on: black, static, then the picture rolls down into place.
  const roll = t < 1.25 ? interpolate(t, [0.75, 1.25], [-WIN_H * 0.35, 0], { extrapolateLeft: "clamp", easing: ease("outCubic") }) : 0;
  const staticAmt = keys(t, [[0.3, 0], [0.4, 1], [0.85, 1], [1.2, 0]]);
  const weave = g.past * 1.6;
  const wx = noise2D("wx", t * 3, 0) * weave, wy = noise2D("wy", t * 3, 0) * weave;
  const flicker = 1 - g.past * 0.05 * (0.5 + 0.5 * noise2D("fl", t * 12, 0));
  const cool = keys(t, [[A.l10, 0], [A.l10 + 0.6, 1], [A.l12, 1], [A.l12 + 1.5, 0]]);
  const flash = keys(t, [[A.toy - 0.08, 0], [A.toy, 0.85], [A.toy + 0.6, 0]]);

  return (
    <Ctx.Provider value={{ p, A }}>
      <AbsoluteFill style={{ background: INK }}>
        <VHSFilter g={glitch} />
        {/* the window between the bars */}
        <div style={{ position: "absolute", left: 0, top: BAR, width: W, height: WIN_H, overflow: "hidden" }}>
          <AbsoluteFill style={{ filter: glitch > 0.01 ? "url(#vhs)" : undefined }}>
            <AbsoluteFill style={{ transform: `translate(${wx}px, ${wy + roll}px)`, filter: `${gradeFilter(g, cool)} brightness(${flicker})`,
                                   opacity: t < 0.75 ? 0 : 1 }}>
              <Shot from={0.7} to={A.from1} xf={0}><Photo src="jobs1984b" s0={1.06} s1={1.2} ox={50} oy={35} pos="50% 30%" /></Shot>
              <Shot from={A.from1} to={A.l2} xf={0}><Photo src="jobs1984" s0={1.0} s1={1.12} ox={50} oy={62} pos="50% 50%" /></Shot>
              <Shot from={A.l2 - 0.4} to={A.l2end + 0.3} xf={10}>
                <Photo src="reagan1985" s0={1.25} s1={1.45} ox={66} oy={30} pos="68% 30%" dim={keys(t, [[A.finished, 0], [A.l2end + 0.3, 0.85]])} />
              </Shot>
              <Shot from={A.l3 - 0.1} to={A.next} xf={10}><Photo src="nextoffice" s0={1.05} s1={1.22} ox={55} oy={50} /></Shot>
              <Shot from={A.next} to={A.l4} xf={0}><Photo src="nextcube2" fit="contain" bg="#f4f4f2" s0={0.92} s1={1.02} oy={50} /></Shot>
              <Shot from={A.l4 - 0.1} to={A.pixar} xf={8}><Photo src="pixarcomputer" s0={1.1} s1={1.3} ox={40} oy={50} dx={-40} /></Shot>
              <Shot from={A.pixar} to={A.l5} xf={0}><Photo src="pixarhq" s0={1.15} s1={1.3} ox={50} oy={40} pos="50% 40%" /></Shot>
              <Shot from={A.l5 - 0.1} to={A.betting} xf={8}><Photo src="jobsloc" s0={1.3} s1={1.5} ox={50} oy={22} pos="50% 20%" /></Shot>
              <Shot from={A.betting} to={A.l6} xf={0}><CRTTeapot /></Shot>
              <Shot from={A.l6 - 0.15} to={A.toy} xf={8}><Years t0={A.l6} land={A.y1995} /></Shot>
              <Shot from={A.toy} to={A.l8} xf={0}><TitleCard /></Shot>
              <Shot from={A.l8 - 0.2} to={A.l9} xf={10}><RenderedTeapot /></Shot>
              <Shot from={A.l9 - 0.1} to={A.form} xf={8}><Photo src="pixarhq" s0={1.0} s1={1.12} oy={45} pos="50% 40%" /></Shot>
              <Shot from={A.form} to={A.l10} xf={6}><Photo src="jobs2005" s0={1.05} s1={1.18} ox={58} oy={40} pos="58% 40%" /></Shot>
              <Shot from={A.l10 - 0.2} to={A.l12} xf={6}><Complexity /></Shot>
              <Shot from={A.l12 - 0.3} to={A.l13} xf={12}><Quote /></Shot>
              <Shot from={A.l13 - 0.25} to={A.l14 - 0.85} xf={8}><Vi3W /></Shot>
              <Shot from={A.l14 - 0.85} to={A.anyone} xf={0}><Photo src="jobs1984" s0={1.1} s1={1.32} ox={50} oy={24} pos="50% 30%" /></Shot>
              <Shot from={A.anyone - 0.2} to={A.l15end + 0.25} xf={14}><Gallery /></Shot>
              <Shot from={A.l15end + 0.25} to={A.end} xf={12} tail={0}><EndCard /></Shot>
            </AbsoluteFill>
            <AbsoluteFill style={{ background: `radial-gradient(ellipse at 80% 10%, #FFB86B 0%, transparent 60%)`,
                                   mixBlendMode: "screen", opacity: keys(t, [[A.toy, 0], [A.toy + 0.4, 0.55], [A.toy + 2.5, 0]]) }} />
            <AbsoluteFill style={{ background: "#FFF6E6", opacity: flash }} />
            <Dust amount={g.past} />
            <Grain amount={g.grain} />
            <Scanlines o={Math.max(glitch * 0.9, keys(t, [[0, 0.5], [1.4, 0.5], [2.2, 0]]))} />
            <Vignette k={0.55 + 0.25 * g.past} />
            {staticAmt > 0 && (
              <AbsoluteFill style={{ opacity: staticAmt, mixBlendMode: "normal" }}>
                <svg width={W} height={WIN_H}>
                  <filter id="static"><feTurbulence type="fractalNoise" baseFrequency="0.9 0.35" seed={f} /><feColorMatrix type="saturate" values="0" /></filter>
                  <rect width="100%" height="100%" filter="url(#static)" />
                </svg>
              </AbsoluteFill>
            )}
          </AbsoluteFill>
          {/* VCR OSD */}
          {(t > 0.35 && t < 3.6) && (
            <div style={{ position: "absolute", left: 48, top: 40, fontFamily: VCR, fontSize: 60, color: "#fff",
                          textShadow: "3px 0 #f004, -3px 0 #0ff4, 0 0 10px #fff8", opacity: Math.floor(t * 2) % 2 === 0 || t > 1.3 ? 1 : 0.4 }}>
              PLAY ►</div>
          )}
          <Stamp text="Cupertino · 1985" at={4.6} until={A.l2end} />
          <Stamp text="NeXT · 1985" at={A.next + 0.05} until={A.l4 - 0.2} />
          <Stamp text="San Rafael · 1986" at={A.l4 + 0.3} until={A.pixar - 0.1} />
          <Stamp text="Today" at={A.thirty} until={A.l11 - 0.2} />
        </div>
        <Bars k={g.bars} />
        <Subtitles />
        <Mix />
      </AbsoluteFill>
    </Ctx.Provider>
  );
};
