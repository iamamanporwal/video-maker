import { loadFont as loadUrbanist } from "@remotion/google-fonts/Urbanist";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { ThreeCanvas } from "@remotion/three";
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import * as THREE from "three";
import { tween } from "../lib/anim";
import { useGLB } from "../three/Stage3D";
import type { Brand, ClipShot, CountShot, FilmProps, ImageShot, LineShot, LogoShot, ModelsShot, ScanShot, Shot, VoLine } from "./types";

const { fontFamily: SANS } = loadUrbanist("normal", { weights: ["600", "800", "900"], subsets: ["latin"] });
const { fontFamily: MONO } = loadMono("normal", { weights: ["400", "700"], subsets: ["latin"] });

// 1080x1920. Platform UI covers roughly the bottom 380 px and a 150 px strip on the right.
const W = 1080, H = 1920;
const SAFE = { left: 80, right: 150, bottom: 400 };
const src = (p: string) => (/^(https?:|data:)/.test(p) ? p : staticFile(p));

/** The brand is always written "Vi3W", even inside uppercase text. */
const brandCase = (t: string) => t.replace(/vi3w/gi, "Vi3W");

// --------------------------------------------------------------------------- 3D

/** A GLB scaled to fit a unit cube and centred on the origin. */
const Unit: React.FC<{ url: string; size?: number }> = ({ url, size = 1 }) => {
  const raw = useGLB(url);
  const model = useMemo(() => {
    if (!raw) return null;
    const m = raw.clone(true);
    const box = new THREE.Box3().setFromObject(m);
    const s = box.getSize(new THREE.Vector3());
    const k = size / Math.max(s.x, s.y, s.z, 1e-6);
    m.scale.setScalar(k);
    m.position.copy(box.getCenter(new THREE.Vector3()).multiplyScalar(-k));
    return m;
  }, [raw, size]);
  return model ? <primitive object={model} /> : null;
};

const Lights: React.FC<{ brand: Brand }> = ({ brand }) => (
  <>
    <ambientLight intensity={0.85} />
    <directionalLight position={[3, 5, 4]} intensity={2.4} />
    <directionalLight position={[-4, 1.5, -3]} intensity={1.6} color={brand.accent} />
    <directionalLight position={[0, -3, 3]} intensity={0.5} color="#9fb8ff" />
  </>
);

// --------------------------------------------------------------------------- shots

const Clip: React.FC<{ s: ClipShot }> = ({ s }) => {
  const f = useCurrentFrame();
  const [z0, z1] = s.zoom ?? [1.04, 1.12];
  const k = interpolate(f, [0, s.dur], [z0, z1], { extrapolateRight: "clamp" });
  const at = `${Math.round((s.focus ?? 0.5) * 100)}% ${Math.round((s.focusY ?? 0.5) * 100)}%`;
  return (
    // Zoom towards the focus point, so a push-in can also reach into the top or bottom of the frame.
    <AbsoluteFill style={{ transform: `scale(${k})`, transformOrigin: at }}>
      <OffthreadVideo src={src(s.src)} startFrom={s.startFrom} playbackRate={s.speed ?? 1} muted={!s.gain} volume={s.gain ?? 0}
                      style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: at,
                               filter: "contrast(1.08) saturate(1.06) brightness(0.98)" }} />
    </AbsoluteFill>
  );
};

const Still: React.FC<{ s: ImageShot; brand: Brand }> = ({ s, brand }) => {
  const f = useCurrentFrame();
  const [z0, z1] = s.zoom ?? [1, 1.1];
  const k = interpolate(f, [0, s.dur], [z0, z1], { extrapolateRight: "clamp" });
  if (!s.paper) {
    return <Img src={src(s.src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${k})` }} />;
  }
  // On paper the image sits in the lower half; the kinetic type owns the top.
  return (
    <AbsoluteFill style={{ background: brand.paper }}>
      <div style={{ position: "absolute", left: 110, right: 110, top: 800, height: 760, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Img src={src(s.src)} style={{ maxWidth: "100%", maxHeight: "100%", transform: `scale(${k})`, boxShadow: "0 30px 80px #0005" }} />
      </div>
    </AbsoluteFill>
  );
};

const Count: React.FC<{ s: CountShot; brand: Brand }> = ({ s, brand }) => {
  const f = useCurrentFrame();
  const k = tween(f, 0, 10, 1.35, 1, "outExpo");
  const flash = 1 - tween(f, 0, 6, 0, 1, "outCubic");
  const ring = tween(f, 0, 16, 0, 1, "outExpo");
  return (
    <AbsoluteFill style={{ background: brand.ink, alignItems: "center", justifyContent: "center" }}>
      <div style={{ position: "absolute", width: 760, height: 760, borderRadius: 999, border: `6px solid ${brand.accent}`,
                    transform: `scale(${0.6 + 0.5 * ring})`, opacity: 1 - ring }} />
      <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 720, lineHeight: 1, color: brand.accent, transform: `scale(${k})`,
                    letterSpacing: "-0.06em", marginTop: -120 }}>{s.n}</div>
      <div style={{ position: "absolute", top: 1330, fontFamily: MONO, fontWeight: 700, fontSize: 40, letterSpacing: "0.22em",
                    color: brand.text, opacity: tween(f, 3, 8, 0, 1) }}>{s.label}</div>
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.85 }} />
    </AbsoluteFill>
  );
};

const Pending: React.FC<{ brand: Brand }> = ({ brand }) => (
  <div style={{ position: "absolute", left: 0, right: 0, top: 1240, textAlign: "center", fontFamily: MONO, fontSize: 30,
                color: "#ff6b6b", letterSpacing: "0.12em" }}>VI3W OUTPUT PENDING · drop assets/robot.glb</div>
);

const Scan: React.FC<{ s: ScanShot; brand: Brand }> = ({ s, brand }) => {
  const f = useCurrentFrame();
  if (s.phase === "scan") {
    const sweep = tween(f, 4, s.dur - 10, 0, 1, "inOutCubic");
    return (
      <AbsoluteFill style={{ background: brand.paper }}>
        <div style={{ position: "absolute", left: 90, right: 90, top: 470, height: 900, overflow: "hidden", borderRadius: 20,
                      boxShadow: "0 30px 80px #0004", transform: `scale(${1 + 0.04 * sweep})` }}>
          <Img src={src(s.before)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          {/* Behind the scan the drawing becomes the Vi3W output (or lime "data" when there is none yet). */}
          {s.after ? (
            <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 0 ${(1 - sweep) * 100}% 0)` }}>
              <Img src={src(s.after)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </div>
          ) : (
            <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: `${sweep * 100}%`, background: `${brand.accent}`,
                          mixBlendMode: "multiply", opacity: 0.55 }} />
          )}
          <div style={{ position: "absolute", left: 0, right: 0, top: `${sweep * 100}%`, height: 8, background: brand.accent,
                        boxShadow: `0 0 50px 18px ${brand.accent}AA`, opacity: sweep > 0 && sweep < 1 ? 1 : 0 }} />
        </div>
        {s.label && <div style={{ position: "absolute", left: 0, right: 0, top: 1410, textAlign: "center", fontFamily: MONO, fontSize: 32,
                                  letterSpacing: "0.18em", color: brand.ink }}>{s.label}</div>}
      </AbsoluteFill>
    );
  }
  const rise = tween(f, 0, 14, 0, 1, "outExpo");
  return (
    <AbsoluteFill style={{ background: `radial-gradient(90% 60% at 50% 45%, #1b2014 0%, ${brand.ink} 70%)` }}>
      <div style={{ position: "absolute", left: 70, top: 300, width: 300, height: 300, borderRadius: 14, overflow: "hidden",
                    transform: `rotate(-5deg) scale(${rise})`, boxShadow: "0 20px 60px #000A", border: `3px solid ${brand.text}33` }}>
        <Img src={src(s.before)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", left: 0, top: 380, width: W, height: 1100, opacity: rise, transform: `translateY(${(1 - rise) * 80}px)` }}>
        {s.glb ? (
          <ThreeCanvas width={W} height={1100} camera={{ position: [0, 0.25, 2.5], fov: 34 }} gl={{ alpha: true, antialias: true }}>
            <Lights brand={brand} />
            <group rotation={[0.05, -0.9 + f * 0.045, 0]}><Unit url={src(s.glb)} size={1.25} /></group>
          </ThreeCanvas>
        ) : s.after ? (
          <Img src={src(s.after)} style={{ width: "100%", height: "100%", objectFit: "contain", transform: `scale(${1 + 0.06 * f / s.dur})` }} />
        ) : <Pending brand={brand} />}
      </div>
      {s.label && <div style={{ position: "absolute", left: 0, right: 0, top: 1450, textAlign: "center", fontFamily: MONO, fontSize: 30,
                                letterSpacing: "0.16em", color: `${brand.text}AA`, opacity: rise }}>{s.label}</div>}
    </AbsoluteFill>
  );
};

/** Every model from the film, stacked in a slow zig-zag helix that fills the vertical frame. */
const Ring: React.FC<{ glbs: string[]; f: number; gather?: number; brand: Brand }> = ({ glbs, f, gather = 0, brand }) => (
  <ThreeCanvas width={W} height={H} camera={{ position: [0, 0, 4.8 - 0.4 * Math.min(1, f / 150)], fov: 38 }} gl={{ alpha: true, antialias: true }}>
    <Lights brand={brand} />
    <group rotation={[0.08, Math.sin(f / 90) * 0.35, 0]}>
      {glbs.map((g, i) => {
        const keep = 1 - gather;
        const y = ((glbs.length - 1) / 2 - i) * 0.66 * keep + 0.06 * Math.sin(f / 22 + i * 1.7);
        const x = (i % 2 ? 0.36 : -0.36) * keep;
        return (
          <group key={g} position={[x, y, (i % 2 ? -0.2 : 0.2) * keep]} rotation={[0, -0.6 + f * 0.035 + i, 0]} scale={Math.max(0.001, keep)}>
            <Unit url={src(g)} size={0.78} />
          </group>
        );
      })}
    </group>
  </ThreeCanvas>
);

const Models: React.FC<{ s: ModelsShot; brand: Brand }> = ({ s, brand }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: `radial-gradient(80% 55% at 50% 50%, #1a1f12 0%, ${brand.ink} 72%)` }}>
      <AbsoluteFill style={{ opacity: tween(f, 0, 12, 0, 1) }}><Ring glbs={s.glbs} f={f} brand={brand} /></AbsoluteFill>
    </AbsoluteFill>
  );
};

/** The models gather into a point, the point becomes a lime pencil line on paper (the brand motif). */
const Line: React.FC<{ s: LineShot; brand: Brand }> = ({ s, brand }) => {
  const f = useCurrentFrame();
  const cut = Math.round(s.dur * 0.32);
  if (f < cut) {
    const g = tween(f, 0, cut, 0, 1, "inOutExpo");
    return (
      <AbsoluteFill style={{ background: `radial-gradient(80% 55% at 50% 50%, #1a1f12 0%, ${brand.ink} 72%)` }}>
        <Ring glbs={s.glbs} f={f + 150} gather={g} brand={brand} />
        <div style={{ position: "absolute", left: W / 2 - 14, top: H / 2 - 14, width: 28, height: 28, borderRadius: 99,
                      background: brand.accent, boxShadow: `0 0 60px 20px ${brand.accent}`, opacity: g }} />
      </AbsoluteFill>
    );
  }
  const t = tween(f, cut, s.dur - cut - 6, 0, 1, "inOutCubic");
  const path = "M 120 1010 C 260 930, 360 1090, 500 1000 S 760 900, 960 980";
  return (
    <AbsoluteFill style={{ background: brand.paper }}>
      <svg width={W} height={H} style={{ position: "absolute" }}>
        <path d={path} fill="none" stroke={brand.ink} strokeWidth={9} strokeLinecap="round" pathLength={1}
              strokeDasharray={1} strokeDashoffset={1 - t} />
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1090, height: 30,
                    background: `radial-gradient(40% 50% at ${10 + 80 * t}% 50%, ${brand.accent}88, transparent)` }} />
    </AbsoluteFill>
  );
};

const Cursor: React.FC<{ brand: Brand; down: boolean }> = ({ brand, down }) => (
  <svg width={70} height={90} viewBox="0 0 24 30" style={{ transform: `scale(${down ? 0.86 : 1})`, filter: "drop-shadow(0 6px 18px #000)" }}>
    <path d="M2 2 L2 24 L8 18 L12 28 L16 26 L12 16 L20 16 Z" fill={brand.text} stroke={brand.ink} strokeWidth={1.4} />
  </svg>
);

const Logo: React.FC<{ s: LogoShot; brand: Brand }> = ({ s, brand }) => {
  const f = useCurrentFrame();
  const last = s.clicks[s.clicks.length - 1] ?? 0;
  const inL = tween(f, last + 2, 18, 0, 1, "outExpo");
  const preLine = 1 - tween(f, 0, 10, 0, 1);
  return (
    <AbsoluteFill style={{ background: brand.ink, alignItems: "center" }}>
      {/* Continues the pencil line from the shot before, then the clicks. */}
      <div style={{ position: "absolute", left: 120, right: 120, top: 1000, height: 9, borderRadius: 9, background: brand.accent, opacity: preLine }} />
      {f < last + 4 && (
        <div style={{ position: "absolute", left: W / 2 - 20, top: H / 2 - 120 }}>
          {s.clicks.map((c, i) => {
            const r = tween(f, c, 14, 0, 1, "outExpo");
            return f >= c && r < 1 ? (
              <div key={i} style={{ position: "absolute", left: -60, top: -60, width: 140, height: 140, borderRadius: 999,
                                    border: `5px solid ${brand.accent}`, transform: `scale(${0.3 + 1.4 * r})`, opacity: 1 - r }} />
            ) : null;
          })}
          <Cursor brand={brand} down={s.clicks.some((c) => f >= c && f < c + 3)} />
        </div>
      )}
      {f >= last && (
        <>
          <Img src={src(s.logo)} style={{ position: "absolute", top: 470, width: 400, height: 400, transform: `scale(${0.7 + 0.3 * inL})`,
                                         opacity: inL, filter: `drop-shadow(0 0 ${60 * inL}px #5b8cff66)` }} />
          <div style={{ position: "absolute", top: 900, fontFamily: SANS, fontWeight: 900, fontSize: 190, letterSpacing: "-0.04em",
                        color: brand.text, opacity: inL, transform: `translateY(${(1 - inL) * 40}px)` }}>Vi3W</div>
          <div style={{ position: "absolute", top: 1125, fontFamily: SANS, fontWeight: 800, fontSize: 78, letterSpacing: "-0.03em",
                        color: brand.accent, opacity: tween(f, last + 10, 14, 0, 1) }}>{s.line}</div>
          <div style={{ position: "absolute", top: 1260, fontFamily: MONO, fontWeight: 400, fontSize: 40, letterSpacing: "0.12em",
                        color: `${brand.text}CC`, opacity: tween(f, last + 20, 14, 0, 1) }}>{brandCase(s.url)}</div>
        </>
      )}
    </AbsoluteFill>
  );
};

const ShotView: React.FC<{ s: Shot; brand: Brand }> = ({ s, brand }) => {
  switch (s.type) {
    case "clip": return <Clip s={s} />;
    case "image": return <Still s={s} brand={brand} />;
    case "count": return <Count s={s} brand={brand} />;
    case "scan": return <Scan s={s} brand={brand} />;
    case "models": return <Models s={s} brand={brand} />;
    case "line": return <Line s={s} brand={brand} />;
    case "logo": return <Logo s={s} brand={brand} />;
    default: return <AbsoluteFill style={{ background: "#000" }} />;
  }
};

// --------------------------------------------------------------------------- overlays

const dark = (k = 1) => `0 0 ${4 * k}px #000C, 0 ${6 * k}px ${30 * k}px #000B`;

/** The VO as kinetic type: the line builds word by word, centred, accent words in lime. */
const Kinetic: React.FC<{ vo: VoLine[]; shots: Shot[]; brand: Brand }> = ({ vo, shots, brand }) => {
  const f = useCurrentFrame();
  const i = vo.findIndex((v, k) => {
    const end = Math.min(v.words[v.words.length - 1][1] + 14, vo[k + 1]?.from ?? Infinity);
    return f >= v.words[0][0] - 2 && f < end;
  });
  if (i < 0 || vo[i].hide) return null;
  const v = vo[i];
  const shot = shots.find((s) => f >= s.from && f < s.from + s.dur);
  const onPaper = shot && ((shot.type === "image" && shot.paper) || (shot.type === "line" && f - shot.from >= Math.round(shot.dur * 0.32)));
  const color = onPaper ? brand.ink : brand.text;
  const end = v.words[v.words.length - 1][1] + 14;
  const out = 1 - tween(f, end - 6, 6, 0, 1, "inOutCubic");
  const acc = new Set((v.accent ?? []).map((w) => w.toLowerCase()));
  return (
    <div style={{ position: "absolute", left: SAFE.left, right: SAFE.right - 70, top: v.y ?? 560, transform: "translateY(-50%)", opacity: out,
                  display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: 24, rowGap: 0 }}>
      {v.words.map(([a, , w], k) => {
        if (f < a - 1) return null;
        const e = tween(f, a - 1, 7, 0, 1, "outExpo");
        const bare = w.replace(/[^\w']/g, "").toLowerCase();
        const hot = acc.has(bare);
        // Lime text vanishes on paper, so there the accent becomes a highlighter stroke behind ink text.
        const mark = hot && onPaper ? { background: `linear-gradient(transparent 58%, ${brand.accent} 58%, ${brand.accent} 92%, transparent 92%)` } : {};
        return (
          <span key={k} style={{ fontFamily: SANS, fontWeight: 800, fontSize: 104, lineHeight: 1.04, letterSpacing: "-0.035em",
                                 display: "inline-block", opacity: e, transform: `translateY(${(1 - e) * 26}px)`, ...mark,
                                 color: hot && !onPaper ? brand.accent : color, textShadow: onPaper ? "none" : dark() }}>{brandCase(w)}</span>
        );
      })}
    </div>
  );
};

const Titles: React.FC<{ p: FilmProps }> = ({ p }) => {
  const f = useCurrentFrame();
  return (
    <>
      {p.titles.filter((t) => f >= t.from && f < t.to).map((t, i) => {
        // Fully legible on its first frame (frame 0 is the thumbnail); a settle, then a quick exit.
        const k = tween(f, t.from, 8, 1.06, 1);
        const o = 1 - tween(f, t.to - 5, 5, 0, 1, "inOutCubic");
        return (
          <div key={i} style={{ position: "absolute", left: SAFE.left, right: SAFE.right - 70, top: t.y ?? 420, transform: `translateY(-50%) scale(${k})`,
                                textAlign: "center", fontFamily: SANS, fontWeight: 900, fontSize: t.size ?? 120, lineHeight: 0.98,
                                letterSpacing: "-0.04em", color: p.brand.text, opacity: o, textShadow: dark(1.2) }}>{brandCase(t.text)}</div>
        );
      })}
      {p.counters.filter((c) => f >= c.from && f < c.to).map((c, i) => {
        const n = Math.round(interpolate(f, [c.from, c.to - 4], [c.a, c.b], { extrapolateRight: "clamp" }));
        return (
          <div key={`c${i}`} style={{ position: "absolute", left: SAFE.left, top: 1400, padding: "14px 26px", borderRadius: 10,
                                      background: "#000B", border: "2px solid #ffffff22", fontFamily: MONO, fontWeight: 700, fontSize: 40,
                                      color: p.brand.text, letterSpacing: "0.06em" }}>
            {c.label} <span style={{ color: "#ff6b6b" }}>{String(n).padStart(2, "0")}</span>/{String(c.b).padStart(2, "0")}
          </div>
        );
      })}
    </>
  );
};

const Credit: React.FC<{ shots: Shot[]; brand: Brand }> = ({ shots, brand }) => {
  const f = useCurrentFrame();
  const s = shots.find((x) => f >= x.from && f < x.from + x.dur);
  if (!s?.credit) return null;
  return (
    <div style={{ position: "absolute", left: SAFE.left, bottom: SAFE.bottom + 20, padding: "8px 16px", borderRadius: 8,
                  background: "#000A", fontFamily: MONO, fontSize: 24, color: `${brand.text}D0`, letterSpacing: "0.04em" }}>{s.credit}</div>
  );
};

/** Film grain + vignette over everything, so phone, screen and render footage read as one camera. */
const Finish: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <AbsoluteFill style={{ background: "radial-gradient(120% 85% at 50% 50%, transparent 60%, #0007 100%)", pointerEvents: "none" }} />
      <svg width={W} height={H} style={{ position: "absolute", opacity: 0.09, mixBlendMode: "overlay" }}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={f % 12} /></filter>
        <rect width={W} height={H} filter="url(#grain)" />
      </svg>
    </>
  );
};

// --------------------------------------------------------------------------- film

export const LaunchFilm: React.FC<FilmProps> = (p) => {
  const busy = useMemo(() => p.vo.map((v) => [v.words[0][0] - 6, v.words[v.words.length - 1][1] + 6] as const), [p.vo]);
  return (
    <AbsoluteFill style={{ background: p.brand.ink }}>
      {p.shots.map((s, i) => (
        <Sequence key={i} from={s.from} durationInFrames={s.dur}><ShotView s={s} brand={p.brand} /></Sequence>
      ))}
      <Finish />
      <Titles p={p} />
      <Kinetic vo={p.vo} shots={p.shots} brand={p.brand} />
      <Credit shots={p.shots} brand={p.brand} />
      {p.music && (
        <Audio src={src(p.music.src)} volume={(f) => {
          const near = busy.some(([a, b]) => f >= a && f <= b);
          return p.music!.volume * (near ? p.music!.duck : 1);
        }} />
      )}
      {p.vo.map((v, i) => <Sequence key={`v${i}`} from={v.from}><Audio src={src(v.src)} /></Sequence>)}
      {p.sfx.map((c, i) => <Sequence key={`s${i}`} from={c.from}><Audio src={src(c.src)} volume={c.volume ?? 0.8} /></Sequence>)}
    </AbsoluteFill>
  );
};
