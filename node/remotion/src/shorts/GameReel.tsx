import { loadFont } from "@remotion/google-fonts/Montserrat";
import { ThreeCanvas } from "@remotion/three";
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { tween } from "../lib/anim";
import { useGLB } from "../three/Stage3D";
import type { Brand, ClipSeg, CtaSeg, ReelProps, RevealSeg, Seg, VoLine, Word } from "./types";

const { fontFamily: MONT } = loadFont("normal", { weights: ["700", "800", "900"], subsets: ["latin"] });

// 1080x1920 layout. Platform UI covers roughly the bottom 380 px and a 150 px strip on the right.
const SAFE = { left: 70, right: 150 };
const BAND = { top: 560, h: 760 };     // 16:9 gameplay band in "frame" mode
const CAP_Y = { clip: 1420, reveal: 380, cta: 380 } as const;

const font = (b: Brand) => b.font ?? MONT;
const src = (p: string) => (/^(https?:|data:)/.test(p) ? p : staticFile(p));
const isImage = (p: string) => /\.(png|jpe?g|webp)$/i.test(p);
const shadow = (ink: string, k = 1) => `0 0 ${3 * k}px ${ink}, 0 ${6 * k}px ${28 * k}px ${ink}, 0 0 ${48 * k}px ${ink}CC`;

/** The brand is always written "Vi3W" / "Vi3W.in", even inside uppercase text. */
const BrandCase: React.FC<{ text: string }> = ({ text }) => (
  <>
    {text.split(/(vi3w(?:\.in)?)/i).filter(Boolean).map((t, i) =>
      /^vi3w/i.test(t) ? <span key={i} style={{ textTransform: "none" }}>{t.replace(/^vi3w/i, "Vi3W")}</span> : <span key={i}>{t}</span>,
    )}
  </>
);

/** "*word*" → accent colour. */
const Accented: React.FC<{ text: string; brand: Brand }> = ({ text, brand }) => (
  <>
    {text.split(/(\*[^*]+\*)/).filter(Boolean).map((t, i) =>
      t.startsWith("*") ? <span key={i} style={{ color: brand.accent }}><BrandCase text={t.slice(1, -1)} /></span>
                        : <BrandCase key={i} text={t} />,
    )}
  </>
);

// --------------------------------------------------------------------------- segments

const Clip: React.FC<{ s: ClipSeg; first: boolean }> = ({ s, first }) => {
  const f = useCurrentFrame();
  const push = (s.zoom ?? 1) * (1 + 0.06 * (f / Math.max(1, s.dur))) * (first ? 1 : tween(f, 0, 10, 1.12, 1));
  const pos = `${Math.round((s.focus ?? 0.5) * 100)}% 50%`;
  const video = (style: React.CSSProperties, muted: boolean) => (
    <OffthreadVideo src={src(s.src)} startFrom={s.startFrom} playbackRate={s.speed ?? 1} muted={muted}
                    volume={s.gain ?? 0} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, ...style }} />
  );
  if (s.fit === "crop") {
    return <AbsoluteFill style={{ transform: `scale(${push})` }}>{video({}, !(s.gain ?? 0))}</AbsoluteFill>;
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: "blur(38px) brightness(0.45) saturate(1.3)", transform: "scale(1.25)" }}>{video({}, true)}</AbsoluteFill>
      <div style={{ position: "absolute", left: 0, right: 0, top: BAND.top, height: BAND.h, overflow: "hidden",
                    boxShadow: "0 30px 80px #000A, 0 -30px 80px #000A" }}>
        <div style={{ width: "100%", height: "100%", transform: `scale(${push})` }}>{video({}, !(s.gain ?? 0))}</div>
      </div>
    </AbsoluteFill>
  );
};

const Turntable: React.FC<{ url: string; w: number; h: number; spin?: number }> = ({ url, w, h, spin = 0.035 }) => {
  const f = useCurrentFrame();
  const raw = useGLB(url);
  const model = useMemo(() => {
    if (!raw) return null;
    const m = raw.clone(true);
    const box = new THREE.Box3().setFromObject(m);
    const size = box.getSize(new THREE.Vector3());
    const k = 2.2 / Math.max(size.x, size.y, size.z, 1e-6);
    m.scale.setScalar(k);
    m.position.copy(box.getCenter(new THREE.Vector3()).multiplyScalar(-k));
    return m;
  }, [raw]);
  return (
    <ThreeCanvas width={w} height={h} camera={{ position: [0, 0.9, 3.6], fov: 35 }} gl={{ alpha: true, antialias: true }}>
      <ambientLight intensity={0.9} />
      <directionalLight position={[3, 5, 4]} intensity={2.2} />
      <directionalLight position={[-4, 2, -3]} intensity={1.1} color="#9fd4ff" />
      {model && <group rotation={[0, f * spin - 0.6, 0]}><primitive object={model} /></group>}
    </ThreeCanvas>
  );
};

const Card: React.FC<{ label: string; brand: Brand; style: React.CSSProperties; children: React.ReactNode }> = ({ label, brand, style, children }) => (
  <div style={{ position: "absolute", borderRadius: 34, overflow: "hidden", background: "#0d0f14",
                border: `4px solid ${brand.text}22`, boxShadow: "0 40px 90px #000C", ...style }}>
    {children}
    <div style={{ position: "absolute", left: 22, top: 22, padding: "8px 18px", borderRadius: 999, background: `${brand.ink}D9`,
                  color: brand.text, fontFamily: font(brand), fontWeight: 800, fontSize: 30, letterSpacing: "0.06em" }}>{label}</div>
  </div>
);

const Reveal: React.FC<{ s: RevealSeg; brand: Brand }> = ({ s, brand }) => {
  const f = useCurrentFrame();
  const tAfter = Math.round(s.dur * 0.38);
  const inB = tween(f, 0, 14, 0, 1, "outBack");
  const scan = tween(f, 6, tAfter - 8, 0, 1, "inOutCubic");
  const clicks = [0, 1, 2].map((i) => f >= 8 + i * Math.round((tAfter - 10) / 3));
  const inA = tween(f, tAfter, 16, 0, 1, "outBack");
  const flash = f >= tAfter ? 1 - tween(f, tAfter, 8, 0, 1, "outCubic") : 0;
  const afterW = 940, afterH = 560;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 50% 40%, #1a1f2e 0%, ${brand.ink} 70%)` }}>
      <Card label={s.beforeLabel ?? "SKETCH"} brand={brand} style={{ left: 90, top: 540, width: 560, height: 400, transform: `rotate(-4deg) scale(${inB})` }}>
        <Img src={src(s.before)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        <div style={{ position: "absolute", top: 0, bottom: 0, left: `${scan * 100}%`, width: 10, background: brand.accent,
                      boxShadow: `0 0 40px 14px ${brand.accent}AA`, opacity: scan > 0 && scan < 1 ? 1 : 0 }} />
      </Card>
      <div style={{ position: "absolute", right: SAFE.right - 40, top: 580, display: "flex", flexDirection: "column", gap: 18, opacity: inB }}>
        {clicks.map((on, i) => (
          <div key={i} style={{ width: 110, height: 110, borderRadius: 999, display: "grid", placeItems: "center",
                                background: on ? brand.accent : "#ffffff14", color: on ? brand.ink : `${brand.text}66`,
                                fontFamily: font(brand), fontWeight: 900, fontSize: 52, transform: `scale(${on ? 1 : 0.85})` }}>{i + 1}</div>
        ))}
      </div>
      {f >= tAfter && (
        <Card label="3D · Vi3W" brand={brand} style={{ left: (1080 - afterW) / 2, top: 990, width: afterW, height: afterH,
                                                       transform: `scale(${inA})`, borderColor: brand.accent }}>
          {s.after && isImage(s.after) && (
            <Img src={src(s.after)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${1 + 0.08 * tween(f, tAfter, s.dur - tAfter, 0, 1, "linear")})` }} />
          )}
          {s.after && !isImage(s.after) && (
            // Start the clip when the card appears, not when the segment does, so the reveal opens on its first frame.
            <Sequence from={tAfter} layout="none">
              <OffthreadVideo src={src(s.after)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </Sequence>
          )}
          {!s.after && s.glb && <Turntable url={src(s.glb)} w={afterW} h={afterH} />}
        </Card>
      )}
      {s.timer && f >= tAfter && (
        <div style={{ position: "absolute", left: SAFE.left + 20, top: 920, padding: "10px 22px", borderRadius: 999, background: brand.accent,
                      color: brand.ink, fontFamily: font(brand), fontWeight: 900, fontSize: 34, opacity: inA }}>⏱ {s.timer}</div>
      )}
      {s.label && f >= tAfter && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 990 + afterH + 20, textAlign: "center", color: `${brand.text}B3`,
                      fontFamily: font(brand), fontWeight: 700, fontSize: 28, letterSpacing: "0.04em", opacity: inA }}>{s.label}</div>
      )}
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.7 }} />
    </AbsoluteFill>
  );
};

const Cta: React.FC<{ s: CtaSeg; brand: Brand }> = ({ s, brand }) => {
  const f = useCurrentFrame();
  const a = tween(f, 0, 14, 0, 1, "outBack");
  const pulse = 1 + 0.04 * Math.sin((f / 30) * Math.PI * 2 * 1.2);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(110% 70% at 50% 45%, #1d2333 0%, ${brand.ink} 75%)` }}>
      {/* Stacked column between the caption band (~380) and the bottom platform UI (~1540). */}
      <div style={{ position: "absolute", top: 490, bottom: 380, left: SAFE.left, right: SAFE.left, display: "flex",
                    flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 44 }}>
        {(s.after || s.glb) && (
          <div style={{ width: 900, height: 520, borderRadius: 34, overflow: "hidden", transform: `scale(${a})`,
                        boxShadow: `0 40px 90px #000C, 0 0 0 4px ${brand.accent}55` }}>
            {s.after ? (isImage(s.after) ? <Img src={src(s.after)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                                         : <OffthreadVideo src={src(s.after)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />)
                     : <Turntable url={src(s.glb!)} w={900} h={520} spin={0.05} />}
          </div>
        )}
        {s.logo && <Img src={src(s.logo)} style={{ height: 100, opacity: a }} />}
        <div style={{ textAlign: "center", color: brand.text, fontFamily: font(brand), fontWeight: 900, fontSize: 76, lineHeight: 1.02,
                      letterSpacing: "-0.03em", textTransform: "uppercase", transform: `translateY(${(1 - a) * 40}px)`, opacity: a,
                      textShadow: shadow(brand.ink) }}>
          <Accented text={s.line ?? "Sketch → 3D at *Vi3W.in*"} brand={brand} />
        </div>
        <div style={{ padding: "26px 56px", borderRadius: 999, background: brand.accent, color: brand.ink, fontFamily: font(brand),
                      fontWeight: 900, fontSize: 48, transform: `scale(${a * pulse})`, boxShadow: `0 0 60px ${brand.accent}88`,
                      whiteSpace: "nowrap" }}>{s.button ?? "Make yours at Vi3W.in"}</div>
      </div>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------------------- overlays

const Hook: React.FC<{ text: string; until: number; brand: Brand }> = ({ text, until, brand }) => {
  const f = useCurrentFrame();
  if (f >= until) return null;
  // Fully legible on frame 0 (it's the thumbnail); only a scale settle, then a quick exit.
  const k = tween(f, 0, 8, 1.08, 1) * tween(f, until - 6, 6, 1, 0.92, "inOutCubic");
  const o = tween(f, until - 6, 6, 1, 0, "inOutCubic");
  return (
    <div style={{ position: "absolute", left: SAFE.left, right: SAFE.right - 60, top: 230, height: 300, display: "flex", alignItems: "center",
                  justifyContent: "center", textAlign: "center", color: brand.text, fontFamily: font(brand), fontWeight: 900, fontSize: 82,
                  lineHeight: 1.0, letterSpacing: "-0.035em", textTransform: "uppercase", transform: `scale(${k})`, opacity: o,
                  textShadow: shadow(brand.ink) }}>
      <div><Accented text={text} brand={brand} /></div>
    </div>
  );
};

type Chunk = { words: Word[]; from: number; to: number };

const chunk = (vo: VoLine[], max = 3): Chunk[] => {
  const out: Chunk[] = [];
  for (const line of vo) {
    let cur: Word[] = [];
    const flush = () => {
      if (cur.length) out.push({ words: cur, from: cur[0][0] - 2, to: cur[cur.length - 1][1] + 8 });
      cur = [];
    };
    for (const w of line.words) {
      cur.push(w);
      if (cur.length >= max || /[.,!?…:]$/.test(w[2])) flush();
    }
    flush();
  }
  out.sort((a, b) => a.from - b.from);
  for (let i = 0; i < out.length - 1; i++) out[i].to = Math.min(out[i].to, out[i + 1].from);
  return out;
};

const Captions: React.FC<{ vo: VoLine[]; segments: Seg[]; hookEnd: number; brand: Brand }> = ({ vo, segments, hookEnd, brand }) => {
  const f = useCurrentFrame();
  const chunks = useMemo(() => chunk(vo), [vo]);
  const c = chunks.find((k) => f >= k.from && f < k.to);
  // The hook title already carries the opening line; don't say it twice on screen.
  if (!c || c.from < hookEnd) return null;
  const seg = segments.find((s) => f >= s.from && f < s.from + s.dur);
  const y = seg?.type === "reveal" ? CAP_Y.reveal : seg?.type === "cta" ? CAP_Y.cta : CAP_Y.clip;
  const enter = tween(f, c.from, 5, 0, 1, "outCubic");
  return (
    <div style={{ position: "absolute", left: SAFE.left, right: SAFE.right, top: y, transform: `translateY(-50%) scale(${0.9 + 0.1 * enter})`,
                  opacity: enter, display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: 20, rowGap: 4 }}>
      {c.words.map(([a, b, w], i) => {
        const on = f >= a && f < Math.max(b, a + 4);
        const pop = on ? 1 + 0.14 * (1 - tween(f, a, 6, 0, 1, "outCubic")) : 1;
        return (
          <span key={i} style={{ fontFamily: font(brand), fontWeight: 900, fontSize: 96, lineHeight: 1.05, letterSpacing: "-0.03em",
                                 textTransform: "uppercase", display: "inline-block", transform: `scale(${pop})`,
                                 color: on ? brand.accent : f >= a ? brand.text : `${brand.text}B3`, textShadow: shadow(brand.ink) }}><BrandCase text={w} /></span>
        );
      })}
    </div>
  );
};

/** Creator credit: shown over gameplay only (reveal/CTA put captions in the top band).
 *  Third-party footage ("source") is credited from its first frame, under the band while the hook title holds the top. */
const Credit: React.FC<{ text: string; from: number; segments: Seg[]; brand: Brand }> = ({ text, from, segments, brand }) => {
  const f = useCurrentFrame();
  const seg = segments.find((s) => f >= s.from && f < s.from + s.dur);
  if (seg && seg.type !== "clip" && seg.type !== "source") return null;
  const o = seg?.type === "source" ? 1 : tween(f, Math.max(from, seg?.from ?? 0), 10, 0, 1, "outCubic");
  const top = f < from ? BAND.top + BAND.h + 24 : 250;
  return (
    <div style={{ position: "absolute", left: SAFE.left, top, padding: "10px 22px", borderRadius: 999, background: `${brand.ink}B3`,
                  border: `2px solid ${brand.text}26`, color: brand.text, fontFamily: font(brand), fontWeight: 800, fontSize: 30, opacity: o }}>
      {text}
    </div>
  );
};

// --------------------------------------------------------------------------- reel

export const GameReel: React.FC<ReelProps> = ({ segments, vo, hook, credit, brand, sfx }) => {
  const reveal = segments.find((s) => s.type === "reveal") as RevealSeg | undefined;
  const hookEnd = hook?.until ?? 0;
  return (
    <AbsoluteFill style={{ background: brand.ink }}>
      {segments.map((s, i) => (
        <Sequence key={i} from={s.from} durationInFrames={s.dur}>
          {s.type === "reveal" ? <Reveal s={s} brand={brand} /> : s.type === "cta" ? <Cta s={s} brand={brand} /> : <Clip s={s} first={i === 0} />}
          {(s.type === "clip" || s.type === "source") && s.label && (
            <div style={{ position: "absolute", left: 0, right: 0, top: BAND.top - 60, textAlign: "center", color: `${brand.text}CC`,
                          fontFamily: font(brand), fontWeight: 700, fontSize: 30, letterSpacing: "0.04em" }}>{s.label}</div>
          )}
        </Sequence>
      ))}
      {sfx?.whoosh && segments.slice(1).map((s, i) => (
        <Sequence key={`w${i}`} from={Math.max(0, s.from - 6)}><Audio src={src(sfx.whoosh!)} volume={0.55} /></Sequence>
      ))}
      {sfx?.pop && reveal && (
        <Sequence from={reveal.from + Math.round(reveal.dur * 0.38)}><Audio src={src(sfx.pop)} volume={0.7} /></Sequence>
      )}
      {vo.map((v, i) => <Sequence key={`v${i}`} from={v.from}><Audio src={src(v.src)} /></Sequence>)}
      {credit && <Credit text={credit} from={hookEnd} segments={segments} brand={brand} />}
      {hook && <Hook text={hook.text} until={hook.until} brand={brand} />}
      <Captions vo={vo} segments={segments} hookEnd={hookEnd} brand={brand} />
    </AbsoluteFill>
  );
};
