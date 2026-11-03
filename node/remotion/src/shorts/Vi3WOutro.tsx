import { ThreeCanvas } from "@remotion/three";
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import { tween } from "../lib/anim";
import { useGLB } from "../three/Stage3D";
import { Baseplate, Big, C, Cam, Lights, Model, MONT, rnd, shadow, Sky } from "./RobloxExplainer";

/** Reusable Roblox-dev outro, 1080x1920, 8.8 s, audio baked in (VO + SFX). Appended to every Roblox-dev short as a clip.
 *  Beats are keyed to the VO word times in projects/shorts/roblox-dev-outro/vo.json:
 *  A "Need 3D models for your Roblox game?" (confused noob on a baseplate, Blender 6 hrs chip)
 *  B "Just sketch it… and Vi3W makes it 3D!" (real Vi3W sketch → concept → 3D panels)
 *  C "Try Vi3W.in!" (Vi3W-made noob drops on the baseplate, URL + comment CTA). Keeps y > 1540 and the right rail clear. */

const W = 1080, H = 1920;
export const OUTRO_FRAMES = 265;
const B = 83, CC = 180;                                  // beat starts
const VO = [{ at: 3, src: "vo/e3d2fda16bc9.mp3" }, { at: 84, src: "vo/c1ebc512b069.mp3" }, { at: 182, src: "vo/817f42f18286.mp3" }];
const W_SKETCH = 93, W_VI3W = 122, W_3D = 148, W_URL = 194;    // word onsets (frames)
const SFX: [number, string, number][] = [
  [0, "whoosh", 0.45], [9, "pop", 0.55], [76, "bruh", 0.75], [B - 2, "whoosh", 0.4], [W_SKETCH, "pop", 0.35], [W_VI3W, "pop", 0.35],
  [W_3D, "ding", 0.35], [CC, "drop", 0.7], [W_URL - 2, "vineboom", 0.35], [216, "click", 0.55], [224, "aura-short", 0.3],
];

const Stage: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThreeCanvas width={W} height={H} shadows gl={{ alpha: true, antialias: true }} camera={{ fov: 40, near: 0.1, far: 400, position: [20, 14, 20] }}>
    <Lights />
    {children}
  </ThreeCanvas>
);

const Chip: React.FC<{ text: string; y: number; from: number; bg: string; color?: string; shake?: boolean; size?: number }> = (
  { text, y, from, bg, color = "#fff", shake, size = 46 }) => {
  const f = useCurrentFrame();
  if (f < from) return null;
  const k = tween(f, from, 9, 0, 1, "outBack");
  const sx = shake ? Math.sin(f * 2.3) * Math.max(0, 10 - (f - from) * 0.7) : 0;
  return (
    <div style={{ position: "absolute", top: y, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `translateX(${sx}px) scale(${k})` }}>
      <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: size, color, background: bg, padding: "14px 34px", borderRadius: 999,
                    border: `5px solid ${C.ink}`, boxShadow: "0 12px 40px #000A" }}>{text}</div>
    </div>
  );
};

// ------------------------------------------------------------------ A: the problem
const BeatA: React.FC = () => {
  const f = useCurrentFrame();
  const cam = useMemo(() => (fr: number) => {
    const a = 0.2 - fr * 0.003, r = 24 - tween(fr, 0, 80, 0, 5, "outCubic");
    return { p: [Math.sin(a) * r, 5, Math.cos(a) * r] as [number, number, number], t: [0, 3.2, 0] as [number, number, number], fov: 34 };
  }, []);
  const sad = f >= 76;
  const raw = useGLB(staticFile("noob.glb"));
  return (
    <AbsoluteFill>
      <Sky />
      {raw && <Stage><Cam fn={cam} /><Baseplate /><group rotation={[0, 0, sad ? 0 : Math.sin(f / 5) * 0.06]}><Model raw={raw} size={4.6} ry={0.35 + Math.sin(f / 7) * (sad ? 0.03 : 0.3)} /></group></Stage>}
      {[0, 1].map((i) => {
        const d = 14 + i * 9, o = tween(f, d, 8, 0, 1, "outBack");
        return <div key={i} style={{ position: "absolute", left: [190, 790][i], top: [820, 760][i], fontSize: 120, fontFamily: MONT,
                                     fontWeight: 900, color: C.yellow, transform: `scale(${o}) rotate(${(rnd(i) - 0.5) * 40 + Math.sin(f / 6 + i) * 8}deg)`,
                                     WebkitTextStroke: `10px ${C.ink}`, paintOrder: "stroke fill" }}>?</div>;
      })}
      <Big text={<>need <span style={{ color: C.yellow }}>3D models</span>?</>} y={360} from={9} size={108} shake />
      <Big text="for your roblox game" y={510} from={50} size={64} />
      <Chip text="⏳ Blender: 6 hours… 💀" y={1330} from={76} bg={C.red} shake />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ B: the real Vi3W flow
// Panels in chest-cta.mp4 (1920x1080): 540 px squares at x = 90 / 690 / 1290, y = 236.
const Panel: React.FC<{ i: 0 | 1 | 2; x: number; y: number; s: number; from: number; label: string; hot?: boolean }> = ({ i, x, y, s, from, label, hot }) => {
  const f = useCurrentFrame();
  const k = tween(f, from, 10, 0, 1, "outBack");
  const sc = s / 540;
  const col = hot ? C.accent : "#ffffff";
  return (
    <>
      <div style={{ position: "absolute", left: x, top: y, width: s, height: s, borderRadius: 28, overflow: "hidden", transform: `scale(${k})`,
                    border: `5px solid ${col}`, boxShadow: hot ? `0 0 70px ${C.accent}88, 0 24px 60px #000C` : "0 24px 60px #000C", background: "#0b0d10" }}>
        <OffthreadVideo src={staticFile("chest-cta.mp4")} muted startFrom={30}
                        style={{ position: "absolute", width: 1920 * sc, height: 1080 * sc, left: -[90, 690, 1290][i] * sc, top: -236 * sc, maxWidth: "none" }} />
      </div>
      <div style={{ position: "absolute", left: x, width: s, top: y + s + 14, textAlign: "center", opacity: tween(f, from + 4, 8),
                    fontFamily: MONT, fontWeight: 900, fontSize: 36, color: col, textShadow: shadow(0.7) }}>{label}</div>
    </>
  );
};

const Arrow: React.FC<{ x: number; y: number; from: number; rot?: number }> = ({ x, y, from, rot = 0 }) => {
  const f = useCurrentFrame();
  return <div style={{ position: "absolute", left: x, top: y, fontSize: 70, color: C.accent, fontFamily: MONT, fontWeight: 900, opacity: tween(f, from, 6),
                       transform: `rotate(${rot}deg) translateX(${Math.sin(f / 3) * 6}px)`, textShadow: `0 0 20px ${C.accent}` }}>➜</div>;
};

const BeatB: React.FC = () => {
  const f = useCurrentFrame() + B;   // absolute frame keeps word times readable
  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 80% at 50% 40%, #1a2a1f 0%, #07080C 70%)" }}>
      <div style={{ position: "absolute", inset: 0 }}>
        <Sequence from={-B} layout="none">
          <Big text={<>just <span style={{ color: C.accent }}>sketch it</span> ✏️</>} y={270} from={B} size={96} />
          <Panel i={0} x={50} y={400} s={450} from={W_SKETCH} label="1 · YOUR SKETCH" />
          <Arrow x={505} y={575} from={W_VI3W - 4} />
          <Panel i={1} x={580} y={400} s={450} from={W_VI3W} label="2 · Vi3W" />
          <Arrow x={500} y={925} from={W_3D - 6} rot={90} />
          <Panel i={2} x={215} y={1010} s={560} from={W_3D} label="3 · 3D MODEL ✅" hot />
        </Sequence>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1630, textAlign: "center", fontFamily: MONT, fontWeight: 700, fontSize: 28,
                    color: "#ffffff88", opacity: f >= W_3D ? 1 : 0 }}>real Vi3W output</div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ C: the plug
const BeatC: React.FC = () => {
  const f = useCurrentFrame() + CC;
  const raw = useGLB(staticFile("noob.glb"));
  const cam = useMemo(() => (fr: number) => {
    const a = 0.3 + fr * 0.003;
    return { p: [Math.sin(a) * 24, 4.5, Math.cos(a) * 24] as [number, number, number], t: [0, 3.0, 0] as [number, number, number], fov: 40 };
  }, []);
  const drop = 10 * (1 - tween(f, CC, 14, 0, 1, "outBack"));
  const flash = 1 - tween(f, CC, 10, 0, 1);
  const url = tween(f, W_URL, 10, 1.6, 1, "outBack");
  return (
    <AbsoluteFill>
      <Sky top="#1D1F3A" bottom="#3B7BD8" />
      {raw && <Stage><Cam fn={cam} /><Baseplate /><group position={[0, drop, 0]}><Model raw={raw} size={5.2} ry={0.35 - tween(f, CC, 75, Math.PI * 2, 0, "outCubic")} /></group></Stage>}
      <Img src={staticFile("logo.png")} style={{ position: "absolute", top: 150, left: W / 2 - 75, width: 150, opacity: tween(f, CC + 4, 10),
                                                 filter: "drop-shadow(0 6px 24px #000A)" }} />
      {f >= W_URL && <div style={{ position: "absolute", top: 320, left: 0, right: 0, textAlign: "center", transform: `scale(${url})`, fontFamily: MONT,
                                   fontWeight: 900, fontSize: 150, letterSpacing: "-0.04em", color: C.accent, WebkitTextStroke: `13px ${C.ink}`,
                                   paintOrder: "stroke fill", textShadow: shadow(1.3) }}>Vi3W.in</div>}
      <div style={{ position: "absolute", top: 510, left: 0, right: 0, textAlign: "center", fontFamily: MONT, fontWeight: 900, fontSize: 50, color: "#fff",
                    textShadow: shadow(0.9), opacity: tween(f, W_URL + 8, 10) }}>sketch → Roblox-ready 3D</div>
      <div style={{ position: "absolute", top: 1305, left: 0, right: 0, textAlign: "center", fontFamily: MONT, fontWeight: 800, fontSize: 30,
                    color: "#ffffffCC", textShadow: shadow(0.7), opacity: tween(f, CC + 16, 10) }}>this noob was made in Vi3W</div>
      <Chip text="comment what we should 3D next 👇" y={1375} from={216 - CC} bg={C.accent} color={C.ink} size={44} />
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.85 }} />
    </AbsoluteFill>
  );
};

export const Vi3WOutro: React.FC = () => (
  <AbsoluteFill style={{ background: C.ink }}>
    <Sequence durationInFrames={B}><BeatA /></Sequence>
    <Sequence from={B} durationInFrames={CC - B}><BeatB /></Sequence>
    <Sequence from={CC}><BeatC /></Sequence>
    {VO.map((v, i) => <Sequence key={`vo${i}`} from={v.at}><Audio src={staticFile(v.src)} volume={1} /></Sequence>)}
    {SFX.map(([at, n, g], i) => <Sequence key={`sfx${i}`} from={at}><Audio src={staticFile(`sfx/${n}.mp3`)} volume={g} /></Sequence>)}
  </AbsoluteFill>
);
