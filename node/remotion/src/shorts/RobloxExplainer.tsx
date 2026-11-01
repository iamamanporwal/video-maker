import { loadFont } from "@remotion/google-fonts/Montserrat";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import React, { useLayoutEffect, useMemo, useRef } from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import * as THREE from "three";
import { tween } from "../lib/anim";
import { useGLB } from "../three/Stage3D";

/** "How Roblox games are made": a 2D + low-poly 3D explainer, 1080x1920, video only.
 *  Audio (VO, SFX, music) and karaoke captions are added by GameReel (reel.yaml), so this keeps the caption band
 *  (y ~1320-1520) and the bottom platform UI (y > 1540) clear. Every beat is keyed to the VO word times. */

const { fontFamily: MONT } = loadFont("normal", { weights: ["700", "800", "900"], subsets: ["latin"] });

const W = 1080, H = 1920;
const C = {
  green: "#4B974B", stud: "#5DAE5D", sky1: "#5EC8FF", sky2: "#D9F3FF", ink: "#07080C", accent: "#7CFF6B",
  yellow: "#F5CD30", blue: "#0D69AC", leg: "#A4BD47", red: "#C4281C", grey: "#A3A2A5", dark: "#1B2A35", gold: "#FFC93C",
};
// Scene lengths (frames) = VO line + ~0.35 s. Order matches script.json / vo.json.
export const SCENES = [87, 135, 96, 129, 105, 180, 123, 147, 219, 120];
export const EXPLAINER_FRAMES = SCENES.reduce((a, b) => a + b, 0);

// --------------------------------------------------------------------------- deterministic helpers
const rnd = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

const shadow = (k = 1) => `0 0 ${4 * k}px ${C.ink}, 0 ${6 * k}px ${26 * k}px ${C.ink}, 0 0 ${40 * k}px ${C.ink}AA`;

// --------------------------------------------------------------------------- 2D pieces
const Tag: React.FC<{ step?: string; label: string; from?: number; color?: string }> = ({ step, label, from = 0, color = C.accent }) => {
  const f = useCurrentFrame();
  const k = tween(f, from, 10, 0, 1, "outBack");
  return (
    <div style={{ position: "absolute", top: 210, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `scale(${k})` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18, padding: "16px 34px", borderRadius: 999, background: `${C.ink}E6`,
                    border: `4px solid ${color}`, boxShadow: `0 10px 40px #0008, 0 0 30px ${color}55` }}>
        {step && <span style={{ fontFamily: MONT, fontWeight: 900, fontSize: 40, color: C.ink, background: color, borderRadius: 999,
                                padding: "4px 18px" }}>{step}</span>}
        <span style={{ fontFamily: MONT, fontWeight: 900, fontSize: 46, color: "#fff", letterSpacing: "-0.01em" }}>{label}</span>
      </div>
    </div>
  );
};

const Big: React.FC<{ text: React.ReactNode; y: number; from: number; size?: number; color?: string; shake?: boolean; until?: number }> = (
  { text, y, from, size = 110, color = "#fff", shake, until }) => {
  const f = useCurrentFrame();
  if (f < from || (until !== undefined && f >= until)) return null;
  const k = tween(f, from, 8, 1.3, 1, "outBack");
  const sx = shake ? Math.sin(f * 2.1) * Math.max(0, 8 - (f - from)) : 0;
  return (
    <div style={{ position: "absolute", top: y, left: 40, right: 40, textAlign: "center", transform: `translate(${sx}px,-50%) scale(${k})`,
                  fontFamily: MONT, fontWeight: 900, fontSize: size, lineHeight: 1.0, letterSpacing: "-0.04em", color,
                  textTransform: "uppercase", WebkitTextStroke: `${Math.round(size / 11)}px ${C.ink}`, paintOrder: "stroke fill",
                  textShadow: shadow(1.2) }}>{text}</div>
  );
};

const fmt = (n: number) => Math.round(n).toLocaleString("en-US");

const Counter: React.FC<{ label: string; to: number; from: number; dur: number; y: number; prefix?: string; size?: number }> = (
  { label, to, from, dur, y, prefix = "", size = 120 }) => {
  const f = useCurrentFrame();
  if (f < from) return null;
  const v = tween(f, from, dur, 0, to, "outCubic");
  const k = tween(f, from, 8, 0.6, 1, "outBack");
  return (
    <div style={{ position: "absolute", top: y, left: 0, right: 0, textAlign: "center", transform: `translateY(-50%) scale(${k})` }}>
      <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: size, color: C.gold, letterSpacing: "-0.04em",
                    WebkitTextStroke: `${Math.round(size / 11)}px ${C.ink}`, paintOrder: "stroke fill", textShadow: shadow(1.2) }}>
        {prefix}{fmt(v)}
      </div>
      <div style={{ fontFamily: MONT, fontWeight: 900, fontSize: 44, color: "#fff", marginTop: -6, letterSpacing: "0.02em",
                    textShadow: shadow(0.8) }}>{label}</div>
    </div>
  );
};

const Sky: React.FC<{ top?: string; bottom?: string }> = ({ top = C.sky1, bottom = C.sky2 }) => (
  <AbsoluteFill style={{ background: `linear-gradient(180deg, ${top} 0%, ${bottom} 72%)` }} />
);

// --------------------------------------------------------------------------- 3D pieces
const studTexture = () => {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  g.fillStyle = C.green; g.fillRect(0, 0, 64, 64);
  g.fillStyle = "#3E7F3E"; g.beginPath(); g.arc(34, 34, 17, 0, Math.PI * 2); g.fill();
  g.fillStyle = C.stud; g.beginPath(); g.arc(31, 31, 17, 0, Math.PI * 2); g.fill();
  g.strokeStyle = "#3F853F"; g.lineWidth = 2; g.strokeRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(48, 48);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
};

const Baseplate: React.FC<{ size?: number }> = ({ size = 48 }) => {
  const tex = useMemo(studTexture, []);
  return (
    <mesh position={[0, -0.5, 0]} receiveShadow>
      <boxGeometry args={[size, 1, size]} />
      <meshStandardMaterial map={tex} roughness={0.75} />
    </mesh>
  );
};

const Block: React.FC<{ p: [number, number, number]; s: [number, number, number]; color: string; drop?: number; emissive?: string }> = (
  { p, s, color, drop, emissive }) => {
  const f = useCurrentFrame();
  let y = p[1], vis = true;
  if (drop !== undefined) {
    vis = f >= drop;
    y = p[1] + 14 * (1 - tween(f, drop, 14, 0, 1, "outBack"));
  }
  if (!vis) return null;
  return (
    <mesh position={[p[0], y, p[2]]} castShadow receiveShadow>
      <boxGeometry args={s} />
      <meshStandardMaterial color={color} roughness={0.55} emissive={emissive ?? "#000"} emissiveIntensity={emissive ? 1.4 : 0} />
    </mesh>
  );
};

/** Classic blocky avatar (generic box figure). */
const Noob: React.FC<{ p: [number, number, number]; ry?: number; walk?: number; scale?: number }> = ({ p, ry = 0, walk = 0, scale = 1 }) => {
  const sw = Math.sin(walk) * 0.6;
  return (
    <group position={p} rotation={[0, ry, 0]} scale={scale}>
      <mesh position={[0, 3.5, 0]} castShadow><boxGeometry args={[1.1, 1.1, 1.1]} /><meshStandardMaterial color={C.yellow} roughness={0.5} /></mesh>
      <mesh position={[0, 2.25, 0]} castShadow><boxGeometry args={[2, 2, 1]} /><meshStandardMaterial color={C.blue} roughness={0.5} /></mesh>
      <group position={[-1.5, 3.1, 0]} rotation={[sw, 0, 0]}><mesh position={[0, -0.85, 0]} castShadow><boxGeometry args={[1, 2, 1]} /><meshStandardMaterial color={C.yellow} /></mesh></group>
      <group position={[1.5, 3.1, 0]} rotation={[-sw, 0, 0]}><mesh position={[0, -0.85, 0]} castShadow><boxGeometry args={[1, 2, 1]} /><meshStandardMaterial color={C.yellow} /></mesh></group>
      <group position={[-0.5, 1.25, 0]} rotation={[-sw, 0, 0]}><mesh position={[0, -0.6, 0]} castShadow><boxGeometry args={[1, 1.3, 1]} /><meshStandardMaterial color={C.leg} /></mesh></group>
      <group position={[0.5, 1.25, 0]} rotation={[sw, 0, 0]}><mesh position={[0, -0.6, 0]} castShadow><boxGeometry args={[1, 1.3, 1]} /><meshStandardMaterial color={C.leg} /></mesh></group>
    </group>
  );
};

const Cam: React.FC<{ fn: (f: number) => { p: [number, number, number]; t: [number, number, number]; fov?: number } }> = ({ fn }) => {
  const f = useCurrentFrame();
  const { camera } = useThree();
  useLayoutEffect(() => {
    const { p, t, fov } = fn(f);
    camera.position.set(...p);
    camera.lookAt(...t);
    const pc = camera as THREE.PerspectiveCamera;
    if (fov && pc.fov !== fov) { pc.fov = fov; pc.updateProjectionMatrix(); }
  }, [f, fn, camera]);
  return null;
};

const Lights: React.FC = () => (
  <>
    <hemisphereLight args={["#E8F6FF", "#4B974B", 1.1]} />
    <directionalLight position={[18, 30, 12]} intensity={2.4} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048}
                      shadow-camera-left={-30} shadow-camera-right={30} shadow-camera-top={30} shadow-camera-bottom={-30} />
  </>
);

const Stage: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThreeCanvas width={W} height={H} shadows gl={{ alpha: true, antialias: true }} camera={{ fov: 40, near: 0.1, far: 400, position: [20, 14, 20] }}>
    <Lights />
    {children}
  </ThreeCanvas>
);

/** A real Vi3W GLB, normalised to `size` units tall, standing on y=0. Optional wireframe look. */
const Model: React.FC<{ raw: THREE.Group; size?: number; wire?: boolean; ry?: number; y?: number }> = ({ raw, size = 6, wire, ry = 0, y = 0 }) => {
  const pair = useMemo(() => {
    const make = (wf: boolean) => {
      const m = raw.clone(true);
      if (wf) m.traverse((o: any) => { if (o.isMesh) o.material = new THREE.MeshBasicMaterial({ color: C.accent, wireframe: true, transparent: true, opacity: 0.55 }); });
      else m.traverse((o: any) => { if (o.isMesh) o.castShadow = true; });
      const box = new THREE.Box3().setFromObject(m);
      const s = box.getSize(new THREE.Vector3());
      const k = size / Math.max(s.y, 1e-6);
      m.scale.setScalar(k);
      const c = box.getCenter(new THREE.Vector3());
      m.position.set(-c.x * k, -box.min.y * k, -c.z * k);
      return m;
    };
    return { solid: make(false), wire: make(true) };
  }, [raw, size]);
  return <group position={[0, y, 0]} rotation={[0, ry, 0]}><primitive object={wire ? pair.wire : pair.solid} /></group>;
};

// The base everyone builds in scene 2 and that later scenes reuse.
type Part = { p: [number, number, number]; s: [number, number, number]; color: string };
const BASE: Part[] = (() => {
  const out: Part[] = [];
  out.push({ p: [0, 0.25, 0], s: [16, 0.5, 12], color: C.grey });                       // floor
  out.push({ p: [0, 0.55, 2], s: [4, 0.1, 12], color: C.red });                         // red carpet
  for (let i = 0; i < 6; i++) out.push({ p: [-7.5, 1.5 + 0, -5 + i * 2], s: [1, 2.5, 2], color: "#8D6E55" });   // left wall
  for (let i = 0; i < 6; i++) out.push({ p: [7.5, 1.5, -5 + i * 2], s: [1, 2.5, 2], color: "#8D6E55" });        // right wall
  for (let i = 0; i < 8; i++) out.push({ p: [-7 + i * 2, 1.5, -6], s: [2, 2.5, 1], color: "#8D6E55" });         // back wall
  for (const x of [-7.5, 7.5]) for (const z of [-6, 6]) out.push({ p: [x, 3.5, z], s: [1.4, 7, 1.4], color: "#5B5B5E" });  // pillars
  out.push({ p: [0, 7.2, -3], s: [16.5, 0.6, 7], color: "#2C2F38" });                    // roof
  for (let i = 0; i < 5; i++) out.push({ p: [-5 + i * 2.5, 1.3, -4.4], s: [1.6, 1.6, 1.6], color: [C.yellow, "#E26EB5", C.blue, "#F28C28", "#9B59D0"][i] });  // display pads
  out.push({ p: [0, 3.2, -5.4], s: [6, 2, 0.4], color: "#1E1E24" });                     // sign
  out.push({ p: [11, 0.5, 8], s: [4, 1, 4], color: "#6D6E6C" });                         // spawn
  return out;
})();

const BaseParts: React.FC<{ start?: number; every?: number }> = ({ start, every = 1.4 }) => (
  <>{BASE.map((b, i) => <Block key={i} {...b} drop={start === undefined ? undefined : start + Math.round(i * every)} />)}</>
);

// --------------------------------------------------------------------------- scenes

const S0Who: React.FC = () => {
  const f = useCurrentFrame();
  const raw = useGLB(staticFile("baddie.glb"));
  const cam = useMemo(() => (fr: number) => {
    const a = 0.35 - fr * 0.008;
    return { p: [Math.sin(a) * 21, 5 + tween(fr, 0, 40, 4, 0), Math.cos(a) * 21] as [number, number, number], t: [0, 3.4, 0] as [number, number, number], fov: 38 };
  }, []);
  return (
    <AbsoluteFill>
      <Sky top="#1D1F3A" bottom="#5A3FA0" />
      {raw && <Stage><Cam fn={cam} /><Baseplate /><Model raw={raw} size={6.5} /></Stage>}
      {[0, 1, 2, 3, 4].map((i) => {
        const d = 6 + i * 7, o = tween(f, d, 8, 0, 1, "outBack");
        return <div key={i} style={{ position: "absolute", left: [110, 820, 160, 860, 470][i], top: [520, 470, 1050, 980, 380][i], fontSize: 130,
                                     fontFamily: MONT, fontWeight: 900, color: C.yellow, transform: `scale(${o}) rotate(${(rnd(i) - 0.5) * 40 + Math.sin(f / 6 + i) * 8}deg)`,
                                     WebkitTextStroke: `10px ${C.ink}`, paintOrder: "stroke fill" }}>?</div>;
      })}
      <Big text={<>who actually<br /><span style={{ color: C.yellow }}>made</span> this?</>} y={290} from={0} size={104} shake />
    </AbsoluteFill>
  );
};

const S1Base: React.FC = () => {
  const cam = useMemo(() => (fr: number) => {
    const k = tween(fr, 0, 50, 0, 1, "outCubic");
    return { p: [THREE.MathUtils.lerp(0.1, 22, k), THREE.MathUtils.lerp(70, 15, k), THREE.MathUtils.lerp(0.1, 28, k)] as [number, number, number], t: [0, 0, 0] as [number, number, number], fov: 42 };
  }, []);
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Sky />
      <Stage><Cam fn={cam} /><Baseplate /><Block p={[11, 0.5, 8]} s={[4, 1, 4]} color="#6D6E6C" />{f >= 50 && <Noob p={[11, 1 + 12 * (1 - tween(f, 50, 14, 0, 1, "outBack")), 8]} ry={0.7} />}</Stage>
      <Tag step="STEP 0" label="Roblox Studio" />
      <Big text={<>empty<br />baseplate</>} y={560} from={57} size={120} />
      {f >= 57 && <div style={{ position: "absolute", top: 760, left: 0, right: 0, textAlign: "center", fontFamily: MONT, fontWeight: 800,
                                fontSize: 40, color: "#fff", textShadow: shadow(0.8), opacity: tween(f, 62, 10) }}>a blank world. nothing in it.</div>}
    </AbsoluteFill>
  );
};

const S2Parts: React.FC = () => {
  const cam = useMemo(() => (fr: number) => {
    const a = 0.75 + fr * 0.006;
    return { p: [Math.sin(a) * 26, 15, Math.cos(a) * 26] as [number, number, number], t: [0, 2, 0] as [number, number, number], fov: 40 };
  }, []);
  return (
    <AbsoluteFill>
      <Sky />
      <Stage><Cam fn={cam} /><Baseplate /><BaseParts start={4} every={1.55} /></Stage>
      <Tag step="STEP 1" label="Build the map" />
      <Counter label="PARTS PLACED" to={4812} from={20} dur={70} y={470} />
    </AbsoluteFill>
  );
};

const S3Artists: React.FC = () => {
  const f = useCurrentFrame();
  const raw = useGLB(staticFile("baddie.glb"));
  const solidAt = 57;
  const cam = useMemo(() => (fr: number) => {
    const a = 0.4 - fr * 0.006;
    return { p: [Math.sin(a) * 20, 6.5, Math.cos(a) * 20] as [number, number, number], t: [0, 4.2, 0] as [number, number, number], fov: 40 };
  }, []);
  const flash = f >= solidAt ? 1 - tween(f, solidAt, 10, 0, 1) : 0;
  return (
    <AbsoluteFill>
      <Sky top={f < solidAt ? "#0B1424" : C.sky1} bottom={f < solidAt ? "#16304A" : C.sky2} />
      {raw && <Stage>
        <Cam fn={cam} />
        {f >= solidAt && <Baseplate />}
        <Block p={[0, 0.4, 0]} s={[7, 0.8, 7]} color="#2C2F38" />
        <Model raw={raw} size={7} y={0.8} wire={f < solidAt} />
      </Stage>}
      <Tag step="STEP 2" label="Model every brainrot" />
      {f < solidAt && <Big text="wireframe…" y={520} from={8} size={80} color={C.accent} />}
      {f >= solidAt && <Big text={<>modeled.<br />textured. done.</>} y={540} from={solidAt + 2} size={86} />}
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.8 }} />
    </AbsoluteFill>
  );
};

const S4Vi3W: React.FC = () => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 12, 0.7, 1, "outBack");
  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 80% at 50% 40%, #1a2a1f 0%, #07080C 70%)" }}>
      <Big text={<>or… just<br /><span style={{ color: C.accent }}>sketch it</span></>} y={330} from={0} size={92} />
      <div style={{ position: "absolute", left: 60, right: 60, top: 470, height: 560, borderRadius: 34, overflow: "hidden", transform: `scale(${k})`,
                    border: `5px solid ${C.accent}`, boxShadow: `0 0 70px ${C.accent}55, 0 30px 80px #000C`, background: "#0b0d10" }}>
        <OffthreadVideo src={staticFile("chest-cta.mp4")} muted style={{ width: "100%", height: "100%", objectFit: "contain" }} />
      </div>
      <div style={{ position: "absolute", top: 1060, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 22, opacity: tween(f, 10, 10) }}>
        {["✏️ sketch", "🖼️ image", "🧊 3D"].map((t, i) => (
          <span key={i} style={{ fontFamily: MONT, fontWeight: 900, fontSize: 40, color: f >= 20 + i * 18 ? C.ink : "#fff",
                                 background: f >= 20 + i * 18 ? C.accent : "#ffffff22", padding: "10px 26px", borderRadius: 999 }}>{t}</span>
        ))}
      </div>
      <div style={{ position: "absolute", top: 1160, left: 0, right: 0, textAlign: "center", fontFamily: MONT, fontWeight: 700, fontSize: 30,
                    color: "#ffffffAA" }}>real Vi3W output</div>
    </AbsoluteFill>
  );
};

const CODE: { t: string; c: string }[][] = [
  [{ t: "prompt.Triggered:", c: "#DCDCAA" }, { t: "Connect(", c: "#DCDCAA" }],
  [{ t: "function", c: "#C586C0" }, { t: "(player)", c: "#9CDCFE" }],
  [{ t: "  if ", c: "#C586C0" }, { t: "rot.Owner ~= player ", c: "#9CDCFE" }, { t: "then", c: "#C586C0" }],
  [{ t: "    rot.Owner = player", c: "#9CDCFE" }, { t: " -- steal!", c: "#6A9955" }],
  [{ t: "    cash.Value ", c: "#9CDCFE" }, { t: "+= ", c: "#D4D4D4" }, { t: "100", c: "#B5CEA8" }],
  [{ t: "  end", c: "#C586C0" }],
  [{ t: "end", c: "#C586C0" }, { t: ")", c: "#D4D4D4" }],
];

const CodePanel: React.FC<{ from: number; cps?: number }> = ({ from, cps = 1.25 }) => {
  const f = useCurrentFrame();
  let budget = Math.max(0, (f - from) * cps * 2);
  return (
    <div style={{ position: "absolute", left: 40, right: 40, top: 320, borderRadius: 28, overflow: "hidden", background: "#1E1E1ECC",
                  boxShadow: "0 30px 80px #000A", border: "2px solid #ffffff22", transform: `scale(${tween(f, from, 10, 0.85, 1, "outBack")})` }}>
      <div style={{ height: 54, background: "#2D2D2DEE", display: "flex", alignItems: "center", gap: 12, padding: "0 22px" }}>
        {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 18, height: 18, borderRadius: 9, background: c }} />)}
        <span style={{ fontFamily: "Menlo, monospace", fontSize: 26, color: "#ccc", marginLeft: 14 }}>StealScript.lua — Luau</span>
      </div>
      <div style={{ padding: "22px 26px 28px", fontFamily: "Menlo, monospace", fontSize: 37, lineHeight: 1.5, whiteSpace: "pre" }}>
        {CODE.map((line, li) => (
          <div key={li} style={{ minHeight: 48 }}>
            <span style={{ color: "#858585" }}>{String(li + 1).padStart(2, " ")}  </span>
            {line.map((tok, ti) => {
              const n = Math.min(tok.t.length, Math.max(0, Math.floor(budget)));
              budget -= tok.t.length;
              return <span key={ti} style={{ color: tok.c }}>{tok.t.slice(0, n)}</span>;
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

const Coin: React.FC<{ p: [number, number, number]; at: number }> = ({ p, at }) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = tween(f, at, 10, 0, 1, "outBack");
  return (
    <mesh position={[p[0], p[1] + 2 * tween(f, at, 30, 0, 1), p[2]]} rotation={[Math.PI / 2, 0, f * 0.2]} scale={k}>
      <cylinderGeometry args={[0.9, 0.9, 0.25, 24]} />
      <meshStandardMaterial color={C.gold} metalness={0.7} roughness={0.25} emissive="#7a5200" emissiveIntensity={0.4} />
    </mesh>
  );
};

const S5Script: React.FC = () => {
  const f = useCurrentFrame();
  const cam = useMemo(() => (fr: number) => {
    const a = 0.18 + fr * 0.0015;
    return { p: [Math.sin(a) * 30, 9, Math.cos(a) * 30] as [number, number, number], t: [0, 9, 0] as [number, number, number], fov: 40 };
  }, []);
  const walk = tween(f, 20, 140, 0, 1, "inOutCubic");
  const pops = [83, 95, 114, 126, 146, 156];
  return (
    <AbsoluteFill>
      <Sky />
      <Stage>
        <Cam fn={cam} /><Baseplate /><BaseParts />
        <Noob p={[THREE.MathUtils.lerp(9, 0, walk), 0.5, THREE.MathUtils.lerp(10, 3, walk)]} ry={-2.2} walk={f * 0.5} />
        {pops.map((at, i) => <Coin key={i} p={[-3 + (i % 3) * 3, 3, 3 + Math.floor(i / 3) * 2]} at={at} />)}
      </Stage>
      <Tag step="STEP 3" label="Code it in Luau" />
      <CodePanel from={4} />
      {pops.map((at, i) => f >= at && f < at + 24 && (
        <div key={i} style={{ position: "absolute", left: 300 + (i % 3) * 170, top: 1150 - (f - at) * 4, fontFamily: MONT, fontWeight: 900, fontSize: 64,
                              color: C.gold, WebkitTextStroke: `6px ${C.ink}`, paintOrder: "stroke fill", opacity: 1 - (f - at) / 24 }}>+$100</div>
      ))}
    </AbsoluteFill>
  );
};

const Rack: React.FC<{ x: number }> = ({ x }) => {
  const f = useCurrentFrame();
  return (
    <group position={[x, 0, 0]}>
      <mesh position={[0, 4, 0]} castShadow><boxGeometry args={[3, 8, 3]} /><meshStandardMaterial color="#20242C" roughness={0.4} metalness={0.3} /></mesh>
      {Array.from({ length: 7 }).map((_, r) => (
        <group key={r}>
          <mesh position={[0, 1 + r * 1.05, 1.52]}><boxGeometry args={[2.6, 0.7, 0.05]} /><meshStandardMaterial color="#2E3440" /></mesh>
          {[0, 1, 2].map((l) => {
            const on = rnd(x * 31 + r * 7 + l + Math.floor(f / 4)) > 0.45;
            return <mesh key={l} position={[-1 + l * 0.35, 1 + r * 1.05, 1.56]}><boxGeometry args={[0.18, 0.18, 0.05]} />
              <meshStandardMaterial color={l === 2 ? "#3BE8FF" : C.accent} emissive={l === 2 ? "#3BE8FF" : C.accent} emissiveIntensity={on ? 2.2 : 0.1} /></mesh>;
          })}
        </group>
      ))}
    </group>
  );
};

const S6Servers: React.FC = () => {
  const f = useCurrentFrame();
  const cam = useMemo(() => (fr: number) => ({ p: [THREE.MathUtils.lerp(-10, 4, fr / 123), 6, 16] as [number, number, number],
                                               t: [THREE.MathUtils.lerp(-6, 6, fr / 123), 4, 0] as [number, number, number], fov: 42 }), []);
  const cards = ["🧠 Brainrots: 37", "💰 Cash: $1.2M", "🏠 Base: Level 9"];
  return (
    <AbsoluteFill>
      <Sky top="#0E1B2C" bottom="#1E3A5F" />
      <Stage>
        <Cam fn={cam} />
        <mesh position={[0, -0.5, 0]} receiveShadow><boxGeometry args={[60, 1, 30]} /><meshStandardMaterial color="#2A3442" /></mesh>
        {[-12, -8, -4, 0, 4, 8, 12, 16].map((x) => <Rack key={x} x={x} />)}
      </Stage>
      <Tag step="STEP 4" label="Save your data" color="#3BE8FF" />
      {cards.map((c, i) => {
        const at = 12 + i * 14, k = tween(f, at, 12, 0, 1, "outBack"), fly = tween(f, at + 30, 26, 0, 1, "inOutCubic");
        if (f < at) return null;
        return <div key={i} style={{ position: "absolute", left: 120 + i * 40, top: 470 + i * 120 + fly * 420, transform: `scale(${k * (1 - fly * 0.7)})`,
                                     opacity: 1 - fly, padding: "18px 30px", borderRadius: 22, background: "#fff", fontFamily: MONT, fontWeight: 900,
                                     fontSize: 48, color: C.ink, boxShadow: "0 18px 50px #0009" }}>{c}</div>;
      })}
      <Big text={<>saved ✅<br /><span style={{ fontSize: 60 }}>DataStore</span></>} y={600} from={93} size={110} color={C.accent} />
    </AbsoluteFill>
  );
};

const S7Test: React.FC = () => {
  const f = useCurrentFrame();
  const cam = useMemo(() => (fr: number) => {
    const a = 1.1 + fr * 0.004;
    return { p: [Math.sin(a) * 28, 16, Math.cos(a) * 28] as [number, number, number], t: [0, 2, 0] as [number, number, number], fov: 40 };
  }, []);
  const bugs = Array.from({ length: 9 }).map((_, i) => ({ x: 150 + rnd(i + 3) * 700, y: 560 + rnd(i + 11) * 600, at: 6 + i * 6, die: 30 + i * 5 }));
  const ver = Math.min(52, Math.floor(tween(f, 60, 80, 1, 52, "linear")));
  return (
    <AbsoluteFill>
      <Sky />
      <Stage><Cam fn={cam} /><Baseplate /><BaseParts /></Stage>
      <Tag step="STEP 5" label="Test · fix · update" color="#FF6B6B" />
      {bugs.map((b, i) => f >= b.at && (
        <div key={i} style={{ position: "absolute", left: b.x, top: b.y, fontSize: 96, transform: `scale(${f < b.die ? tween(f, b.at, 8, 0, 1, "outBack") : 1})` }}>
          {f < b.die ? "🐛" : <span style={{ color: "#FF3B3B", fontFamily: MONT, fontWeight: 900, WebkitTextStroke: `6px ${C.ink}`, paintOrder: "stroke fill",
                                             opacity: 1 - tween(f, b.die + 8, 10, 0, 1) }}>✖</span>}
        </div>
      ))}
      {f >= 60 && f < 85 && <div style={{ position: "absolute", top: 400, left: 0, right: 0, textAlign: "center", fontFamily: MONT, fontWeight: 900, fontSize: 64,
                                          color: "#fff", textShadow: shadow(1) }}>
        <span style={{ background: C.ink, padding: "10px 28px", borderRadius: 18 }}>update v{ver} 🚀</span></div>}
      <Big text="every." y={460} from={85} until={110} size={150} />
      <Big text="single." y={460} from={110} until={129} size={150} />
      <Big text={<span style={{ color: "#FF3B3B" }}>week.</span>} y={460} from={129} size={170} shake />
    </AbsoluteFill>
  );
};

const Crowd: React.FC<{ count: number }> = ({ count }) => {
  const N = 1400;
  const body = useRef<THREE.InstancedMesh>(null);
  const head = useRef<THREE.InstancedMesh>(null);
  const pos = useMemo(() => Array.from({ length: N }).map((_, i) => {
    const r = Math.sqrt(i) * 0.62 + 3, a = i * 2.39996;
    return [Math.cos(a) * r, Math.sin(a) * r, rnd(i) * Math.PI * 2] as const;
  }), []);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), v = new THREE.Vector3();
    const colors = [C.blue, C.red, "#E26EB5", "#F28C28", "#9B59D0", "#2BB673"];
    for (let i = 0; i < N; i++) {
      const vis = i < count ? 1 : 0;
      q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), pos[i][2]);
      s.set(vis, vis, vis);
      body.current!.setMatrixAt(i, m.compose(v.set(pos[i][0], 0.9, pos[i][1]), q, s));
      head.current!.setMatrixAt(i, m.compose(v.set(pos[i][0], 2.15, pos[i][1]), q, s));
      body.current!.setColorAt(i, new THREE.Color(colors[i % colors.length]));
    }
    body.current!.instanceMatrix.needsUpdate = true;
    head.current!.instanceMatrix.needsUpdate = true;
    if (body.current!.instanceColor) body.current!.instanceColor.needsUpdate = true;
  }, [count, pos]);
  return (
    <>
      <instancedMesh ref={body} args={[undefined as any, undefined as any, N]} castShadow>
        <boxGeometry args={[1, 1.8, 0.6]} /><meshStandardMaterial roughness={0.5} />
      </instancedMesh>
      <instancedMesh ref={head} args={[undefined as any, undefined as any, N]}>
        <boxGeometry args={[0.7, 0.7, 0.7]} /><meshStandardMaterial color={C.yellow} roughness={0.5} />
      </instancedMesh>
    </>
  );
};

const S8Stats: React.FC = () => {
  const f = useCurrentFrame();
  const cam = useMemo(() => (fr: number) => {
    const k = tween(fr, 100, 110, 0, 1, "inOutCubic");
    const a = 0.7 + fr * 0.004;
    const r = THREE.MathUtils.lerp(16, 40, k);
    return { p: [Math.sin(a) * r, THREE.MathUtils.lerp(8, 34, k), Math.cos(a) * r] as [number, number, number], t: [0, 1, 0] as [number, number, number], fov: 42 };
  }, []);
  const count = Math.floor(tween(f, 116, 60, 0, 1400, "inOutCubic"));
  return (
    <AbsoluteFill>
      <Sky top="#4FB6FF" bottom="#E7F7FF" />
      <Stage><Cam fn={cam} /><Baseplate size={70} /><Noob p={[0, 0, 0]} ry={0.6} /><Crowd count={count} /></Stage>
      <Big text={<>grow a <span style={{ color: "#6BE36B" }}>garden</span></>} y={270} from={0} size={96} />
      {f >= 59 && f < 116 && <Big text={<>first version:<br /><span style={{ color: C.gold }}>~3 days</span></>} y={560} from={59} size={100} />}
      {f >= 116 && <Counter label="PLAYING AT ONCE" to={21000000} from={116} dur={50} y={560} size={124} />}
      {f >= 116 && <div style={{ position: "absolute", top: 1250, left: 0, right: 0, textAlign: "center", fontFamily: MONT, fontWeight: 700, fontSize: 26,
                                 color: "#ffffffCC", textShadow: shadow(0.6) }}>peak concurrent players, June 2025 (AP)</div>}
    </AbsoluteFill>
  );
};

const S9Respect: React.FC = () => {
  const f = useCurrentFrame();
  const raw = useGLB(staticFile("baddie.glb"));
  const cam = useMemo(() => (fr: number) => {
    const k = tween(fr, 0, 100, 0, 1, "inOutCubic");
    const a = 0.12 + fr * 0.003;
    const r = THREE.MathUtils.lerp(22, 36, k);
    return { p: [Math.sin(a) * r, THREE.MathUtils.lerp(7, 20, k), Math.cos(a) * r] as [number, number, number], t: [0, 3, 4] as [number, number, number], fov: 40 };
  }, []);
  return (
    <AbsoluteFill>
      <Sky />
      {raw && <Stage><Cam fn={cam} /><Baseplate /><BaseParts /><group position={[0, 0, 8.5]}><Model raw={raw} size={5} y={0.5} ry={Math.sin(f * 0.05) * 0.4} /></group></Stage>}
      <Big text={<>respect<br />the dev 🫡</>} y={520} from={79} size={128} shake />
      {f >= 79 && Array.from({ length: 60 }).map((_, i) => {
        const t = f - 79, x = rnd(i) * 1080, y = -40 + t * (9 + rnd(i + 5) * 9), rot = t * (4 + rnd(i + 9) * 10);
        return <div key={i} style={{ position: "absolute", left: x, top: y, width: 22, height: 34, background: [C.accent, C.gold, "#FF5FA2", "#5EC8FF"][i % 4],
                                     transform: `rotate(${rot}deg)`, borderRadius: 4 }} />;
      })}
    </AbsoluteFill>
  );
};

const ORDER = [S0Who, S1Base, S2Parts, S3Artists, S4Vi3W, S5Script, S6Servers, S7Test, S8Stats, S9Respect];

export const RobloxExplainer: React.FC<{ only?: number }> = ({ only }) => {
  let t = 0;
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      {ORDER.map((S, i) => {
        const from = t;
        t += SCENES[i];
        if (only !== undefined && only !== i) return null;
        return <Sequence key={i} from={from} durationInFrames={SCENES[i]}><S /></Sequence>;
      })}
    </AbsoluteFill>
  );
};
