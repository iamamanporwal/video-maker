import React, { useMemo } from "react";
import { AbsoluteFill, Img, OffthreadVideo, useCurrentFrame } from "remotion";
import { Capture } from "../components/Capture";
import { ChatPanel, Clock, GenericViewport, Msg, Room } from "../components/Set";
import { Headline, LimeLine, Tag, Typed } from "../components/Type";
import { C, F } from "../generated/brand";
import { hash, multiKeys, tween } from "../lib/anim";
import { useAsset, useFilm } from "../lib/context";
import { useFormat } from "../lib/layout";
import { Stage3D } from "../three/Stage3D";

type P = { p: Record<string, any>; dur: number };
type HL = { text: string; at: number; out?: number; size?: number };

const Headlines: React.FC<{ items?: HL[]; size?: number; align?: "left" | "center"; maxWidth?: number }> = ({ items = [], size = 96, align = "left", maxWidth }) => (
  <div style={{ position: "relative" }}>
    {items.map((h, i) => (
      <div key={i} style={{ position: i === 0 ? "relative" : "absolute", top: 0, left: 0, right: 0 }}>
        <Headline text={h.text} at={h.at} out={h.out} size={h.size ?? size} align={align} maxWidth={maxWidth} />
      </div>
    ))}
  </div>
);

// ------------------------------------------------------------------------------------------------ cold_open

export const ColdOpen: React.FC<P> = ({ p }) => {
  const frame = useCurrentFrame();
  const { w, h, safe, u, vertical } = useFormat();
  const showChat = frame >= (p.chatAt ?? 30);
  const slam = p.slam as { text: string; at: number } | undefined;
  const slamK = slam ? tween(frame, slam.at, 10, 0, 1, "outBack") : 0;
  const shake = slam && frame >= slam.at && frame < slam.at + 8 ? (hash(frame) - 0.5) * 18 * u : 0;
  return (
    <AbsoluteFill style={{ transform: `translate(${shake}px, ${shake * 0.6}px)` }}>
      <Room photo={p.photo} glow={p.stare && frame >= p.stare.at ? 1.25 : 1}>
        {showChat ? (
          <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", background: "#101211" }}>
            <ChatPanel messages={(p.messages ?? []) as Msg[]} width={vertical ? w * 0.8 : w * 0.46} height={vertical ? w * 0.42 : h * 0.5} title={p.channel} />
          </div>
        ) : (
          <GenericViewport />
        )}
      </Room>
      <div style={{ position: "absolute", left: safe.left, top: safe.top }}>
        <Clock text={p.clock ?? "2:47 AM"} at={p.clockAt ?? 4} />
      </div>
      {slam && frame >= slam.at && (
        <AbsoluteFill style={{ display: "grid", placeItems: "center", background: `rgba(11,11,12,${0.55 * slamK})` }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 150 * u, color: C.accent, transform: `scale(${0.6 + 0.4 * slamK})`, textAlign: "center", letterSpacing: "-0.04em" }}>
            {slam.text}
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ chat / plot_twist

export const Chat: React.FC<P> = ({ p }) => {
  const { w, h, vertical } = useFormat();
  return (
    <AbsoluteFill style={{ background: C.ink, display: "grid", placeItems: "center" }}>
      <ChatPanel messages={p.messages ?? []} title={p.channel} width={vertical ? w * 0.86 : w * 0.5} height={vertical ? h * 0.5 : h * 0.66} />
    </AbsoluteFill>
  );
};

export const PlotTwist: React.FC<P> = ({ p }) => {
  const frame = useCurrentFrame();
  const { u, safe, vertical, w, h } = useFormat();
  const big = p.big as { text: string; at: number } | undefined;
  const k = big ? tween(frame, big.at, 9, 0, 1, "outBack") : 0;
  const shake = big && frame >= big.at && frame < big.at + 10 ? (hash(frame + 3) - 0.5) * 22 * u : 0;
  return (
    <AbsoluteFill style={{ background: C.ink, transform: `translateX(${shake}px)` }}>
      <AbsoluteFill style={{ display: "grid", placeItems: "center", opacity: big && frame >= big.at ? 0.25 : 1 }}>
        <ChatPanel messages={p.messages ?? []} title={p.channel} width={vertical ? w * 0.86 : w * 0.5} height={vertical ? h * 0.46 : h * 0.6} />
      </AbsoluteFill>
      {big && frame >= big.at && (
        <AbsoluteFill style={{ display: "grid", placeItems: "center", padding: safe.left }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: (vertical ? 130 : 170) * u, color: C.accent, letterSpacing: "-0.045em", textAlign: "center", transform: `scale(${0.5 + 0.5 * k})`, lineHeight: 0.95 }}>
            {big.text}
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ url_to_logo

export const UrlToLogo: React.FC<P> = ({ p, dur }) => {
  const frame = useCurrentFrame();
  const asset = useAsset();
  const { w, h, u } = useFormat();
  const reflow = p.reflowAt ?? Math.round(dur * 0.45);
  const k = tween(frame, reflow, 22, 0, 1, "inOutExpo");
  const lw = 520 * u;
  return (
    <AbsoluteFill style={{ background: C.ink, display: "grid", placeItems: "center" }}>
      <div style={{ position: "relative", display: "grid", placeItems: "center" }}>
        <div style={{ fontFamily: F.mono, fontSize: 54 * u, color: C.text, opacity: 1 - k, transform: `scale(${1 - 0.4 * k}) translateY(${-40 * k * u}px)`, letterSpacing: `${k * 0.6}em` }}>
          <Typed text={p.url ?? "vi3w.app"} at={4} cps={18} />
        </div>
        <div style={{ position: "absolute", display: "grid", placeItems: "center", opacity: k, transform: `scale(${0.85 + 0.15 * k})` }}>
          {p.logo ? (
            <Img src={asset(p.logo)} style={{ width: 360 * u, mixBlendMode: "screen" }} />
          ) : (
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 180 * u, color: C.text, letterSpacing: "-0.05em" }}>{p.wordmark ?? "Vi3W"}</div>
          )}
        </div>
      </div>
      <div style={{ position: "absolute", left: (w - lw) / 2, top: h / 2 + 130 * u, width: lw, height: 20 }}>
        <LimeLine d={`M 0 10 L ${lw} 10`} at={reflow + 8} dur={20} width={lw} height={20} />
      </div>
      {p.sub && (
        <div style={{ position: "absolute", top: h / 2 + 175 * u, width: "100%", textAlign: "center" }}>
          <Headline text={p.sub} at={reflow + 18} size={44} align="center" color={C.muted[0]} weight={600} />
        </div>
      )}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ product_shot

export const ProductShot: React.FC<P> = ({ p }) => {
  const frame = useCurrentFrame();
  const { w, h, safe, u, vertical, wide, inner } = useFormat();
  const enter = tween(frame, 0, 26, 0, 1, "outExpo"); // no fade from 0: slide + scale only
  const right = (p.side ?? "right") === "right";
  const headlines: HL[] = p.headlines ?? (p.headline ? [{ text: p.headline, at: 6 }] : []);
  const tag = p.tag as { text: string; at: number } | undefined;
  const common = { take: p.take, timeKeys: p.timeKeys ?? [[0, 0]], focusKeys: p.focusKeys, strokesFrom: p.strokesFrom ?? 0, strokes: p.lime !== false };
  if (wide) {
    const cw = w * 0.6;
    const ch = cw * (p.aspect ?? 9 / 16);
    const tilt = p.tilt ?? 7;
    return (
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at ${right ? 70 : 30}% 50%, #171a16 0%, ${C.ink} 65%)` }}>
        <div
          style={{
            position: "absolute",
            top: (h - ch) / 2,
            left: right ? w - cw - safe.right * 0.6 : safe.left * 0.6,
            transform: `perspective(2400px) rotateY(${(right ? -1 : 1) * tilt * (0.6 + 0.4 * enter)}deg) translateX(${(1 - enter) * (right ? 1 : -1) * 220}px) scale(${0.94 + 0.06 * enter})`,
            boxShadow: "0 40px 120px rgba(0,0,0,0.6)",
            borderRadius: 16,
          }}
        >
          <Capture {...common} width={cw} height={ch} radius={16} />
        </div>
        <div style={{ position: "absolute", top: h * 0.34, left: right ? safe.left : w - safe.right - w * 0.3, width: w * 0.3 }}>
          <Headlines items={headlines} size={92} />
          {tag && <div style={{ marginTop: 34 * u }}><Tag text={tag.text} at={tag.at} /></div>}
        </div>
      </AbsoluteFill>
    );
  }
  // Vertical and 4:5: re-composed, full-bleed product (never a crop of the 16:9 master).
  // Keep clear of the caption band at the bottom of the safe area.
  const ch = vertical ? h * 0.5 : inner.h * 0.62;
  const cw = vertical ? w : inner.w;
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", top: vertical ? safe.top - 40 * u : safe.top, left: vertical ? 0 : inner.x, transform: `translateY(${(1 - enter) * 160}px) scale(${0.96 + 0.04 * enter})` }}>
        <Capture {...common} width={cw} height={ch} radius={vertical ? 0 : 18} />
      </div>
      <div style={{ position: "absolute", left: safe.left, right: safe.right, top: (vertical ? safe.top - 40 * u : safe.top) + ch + 44 * u }}>
        <Headlines items={headlines} size={vertical ? 88 : 76} />
        {tag && <div style={{ marginTop: 24 * u }}><Tag text={tag.text} at={tag.at} /></div>}
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ before_after / triptych

export const BeforeAfter: React.FC<P> = ({ p, dur }) => {
  const frame = useCurrentFrame();
  const asset = useAsset();
  const { w, h, u, vertical, inner } = useFormat();
  const wipe = useMemo(() => multiKeys(p.wipeKeys ?? [[0, 0], [12, 0], [Math.max(13, dur * 0.6), 1]]), [p.wipeKeys, dur]);
  const k = Math.min(1, Math.max(0, wipe(frame)[0]));
  const cw = vertical ? inner.w : inner.w * 0.86;
  const ch = Math.min(vertical ? inner.h * 0.62 : inner.h * 0.82, cw * (p.aspect ?? 1));
  const x = (w - cw) / 2;
  const y = vertical ? inner.y : (h - ch) / 2;
  const labels: string[] = p.labels ?? ["before", "after"];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: x, top: y, width: cw, height: ch, borderRadius: 18 * u, overflow: "hidden" }}>
        <Img src={asset(p.before)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover" }} />
        <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 0 0 ${(1 - k) * 100}%)` }}>
          <Img src={asset(p.after)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
        <div style={{ position: "absolute", top: 0, bottom: 0, left: (1 - k) * cw - 3, width: 6, background: C.accent, boxShadow: `0 0 24px ${C.accent}`, opacity: k > 0.001 && k < 0.999 ? 1 : 0 }} />
        <div style={{ position: "absolute", left: 18 * u, top: 18 * u }}><Tag text={labels[0]} dot={false} /></div>
        <div style={{ position: "absolute", right: 18 * u, top: 18 * u, opacity: k }}><Tag text={labels[1]} /></div>
      </div>
      {p.headline && (
        <div style={{ position: "absolute", left: inner.x, right: w - inner.x - inner.w, top: vertical ? y + ch + 40 * u : undefined, bottom: vertical ? undefined : inner.y * 0.6 }}>
          <Headline text={p.headline} at={p.headlineAt ?? 10} size={vertical ? 84 : 72} align={vertical ? "left" : "center"} />
        </div>
      )}
    </AbsoluteFill>
  );
};

export const Triptych: React.FC<P> = ({ p }) => {
  const frame = useCurrentFrame();
  const asset = useAsset();
  const { w, h, u, vertical, inner } = useFormat();
  const imgs: string[] = p.images ?? [];
  const labels: string[] = p.labels ?? [];
  const n = Math.max(1, imgs.length);
  const gap = 24 * u;
  const cw = vertical ? inner.w * 0.82 : (inner.w - gap * (n - 1)) / n;
  const ch = vertical ? (inner.h - gap * (n - 1)) / n : cw * 0.8;
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      {imgs.map((src, i) => {
        const k = tween(frame, 4 + i * 8, 22, 0, 1, "outExpo");
        const x = vertical ? (w - cw) / 2 : inner.x + i * (cw + gap);
        const y = vertical ? inner.y + i * (ch + gap) : (h - ch) / 2;
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: cw, height: ch, borderRadius: 16 * u, overflow: "hidden", transform: `translateY(${(1 - k) * 60}px) scale(${0.95 + 0.05 * k})` }}>
            <Img src={asset(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            {labels[i] && <div style={{ position: "absolute", left: 14 * u, bottom: 14 * u }}><Tag text={labels[i]} at={10 + i * 8} /></div>}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ 3D

export const ImageTo3D: React.FC<P> = ({ p, dur }) => {
  const frame = useCurrentFrame();
  const asset = useAsset();
  const { w, h, u, vertical, safe, inner } = useFormat();
  const scanAt = p.scanAt ?? Math.round(dur * 0.35);
  const scan = tween(frame, scanAt, p.scanDur ?? 60, 0, 1, "inOutCubic");
  const capW = vertical ? w : w * 0.44;
  const capH = vertical ? h * 0.36 : capW * 0.5625;
  const stW = vertical ? w : w * 0.5;
  const stH = vertical ? h * 0.5 : h;
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      {p.take && (
        <div style={{ position: "absolute", left: vertical ? 0 : safe.left * 0.6, top: vertical ? safe.top - 40 * u : (h - capH) / 2 }}>
          <Capture take={p.take} timeKeys={p.timeKeys ?? [[0, 0]]} focusKeys={p.focusKeys} width={capW} height={capH} radius={vertical ? 0 : 14} />
        </div>
      )}
      <div style={{ position: "absolute", right: 0, top: vertical ? h - stH - safe.bottom * 0.4 : 0 }}>
        <Stage3D width={stW} height={stH} glb={asset(p.glb)} hdri={p.hdri ? asset(p.hdri) : undefined} scan={scan} camKeys={p.camKeys} baseColorFactor={p.baseColorFactor} rotateX={p.rotateX} />
      </div>
      {p.headline && (
        <div style={{ position: "absolute", left: inner.x, top: vertical ? safe.top - 40 * u + capH + 30 * u : inner.y }}>
          <Headline text={p.headline} at={p.headlineAt ?? 8} size={vertical ? 76 : 80} />
        </div>
      )}
      {p.tag && (
        <div style={{ position: "absolute", left: inner.x, bottom: vertical ? safe.bottom : inner.y }}>
          <Tag text={p.tag.text} at={p.tag.at} />
        </div>
      )}
    </AbsoluteFill>
  );
};

export const Finale3D: React.FC<P> = ({ p }) => {
  const asset = useAsset();
  const { w, h, inner, vertical } = useFormat();
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <Stage3D
        width={w}
        height={h}
        glb={asset(p.glb)}
        hdri={p.hdri ? asset(p.hdri) : undefined}
        camKeys={p.camKeys}
        carKeys={p.carKeys}
        thrustKeys={p.thrustKeys}
        anchors={p.anchors}
        tunnel={p.tunnel}
        baseColorFactor={p.baseColorFactor}
        rotateX={p.rotateX}
      />
      <div style={{ position: "absolute", left: inner.x, right: w - inner.x - inner.w, bottom: vertical ? undefined : inner.y, top: vertical ? inner.y : undefined }}>
        <Headlines items={p.headlines ?? []} size={vertical ? 96 : 110} />
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ end_room / end_card

export const EndRoom: React.FC<P> = ({ p, dur }) => {
  const frame = useCurrentFrame();
  const asset = useAsset();
  const { safe, inner, vertical, u } = useFormat();
  const sleepAt = p.sleepAt ?? Math.round(dur * 0.4);
  const dim = tween(frame, sleepAt, 30, 1, 0.2, "calm");
  return (
    <AbsoluteFill>
      <Room photo={p.photo} glow={dim}>
        {p.monitor ? <Img src={asset(p.monitor)} style={{ width: "100%", height: "100%", objectFit: "cover", opacity: dim }} /> : null}
      </Room>
      <div style={{ position: "absolute", left: safe.left, top: safe.top }}>
        <Clock text={p.clock ?? "3:52 AM"} />
      </div>
      {p.tagline && (
        <div style={{ position: "absolute", left: inner.x, right: safe.right, bottom: vertical ? safe.bottom : inner.y + 20 * u }}>
          <Headline text={p.tagline} at={p.taglineAt ?? sleepAt + 20} size={vertical ? 72 : 64} weight={800} />
        </div>
      )}
    </AbsoluteFill>
  );
};

// Accent pill for an end-card call to action (accent is reserved for highlights; a CTA is one).
const CtaButton: React.FC<{ text: string; at: number }> = ({ text, at }) => {
  const frame = useCurrentFrame();
  const { u } = useFormat();
  const k = tween(frame, at, 16);
  return (
    <div style={{ opacity: k, transform: `translateY(${(1 - k) * 24 * u}px) scale(${0.96 + 0.04 * k})`, marginTop: 10 * u,
                  background: C.accent, color: C.ink, fontFamily: F.display, fontWeight: 800, fontSize: 40 * u,
                  letterSpacing: "-0.02em", padding: `${18 * u}px ${44 * u}px`, borderRadius: 999,
                  boxShadow: `0 0 ${60 * u}px ${C.accent}55` }}>
      {text} →
    </div>
  );
};

export const EndCard: React.FC<P> = ({ p }) => {
  const asset = useAsset();
  const { w, h, u } = useFormat();
  const lw = 420 * u;
  return (
    <AbsoluteFill style={{ background: C.ink, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 30 * u }}>
      {p.logo ? (
        <Img src={asset(p.logo)} style={{ width: 300 * u, mixBlendMode: "screen" }} />
      ) : (
        <Headline text={p.wordmark ?? "Vi3W"} size={170} align="center" />
      )}
      <div style={{ position: "relative", width: lw, height: 14 }}>
        <LimeLine d={`M 0 7 L ${lw} 7`} at={8} dur={18} width={lw} height={14} strokeWidth={5} />
      </div>
      {p.tagline && <Headline text={p.tagline} at={14} size={54} align="center" weight={600} maxWidth={w * 0.8} />}
      {p.url && <Tag text={p.url} at={26} />}
      {p.cta && !p.ctaButton && <div style={{ fontFamily: F.body, color: C.muted[0], fontSize: 30 * u }}>{p.cta}</div>}
      {p.cta && p.ctaButton && <CtaButton text={p.cta} at={34} />}
      <div style={{ position: "absolute", bottom: h * 0.05 }} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ video_clip / photo_insert

export const VideoClip: React.FC<P> = ({ p }) => {
  const asset = useAsset();
  const { safe, u } = useFormat();
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <OffthreadVideo src={asset(p.src)} startFrom={Math.round((p.trimSec ?? 0) * 30)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      {p.generated !== false && (
        <div style={{ position: "absolute", right: safe.right, top: safe.top, fontFamily: F.mono, fontSize: 18 * Math.max(1, u), color: C.muted[0], opacity: 0.8 }}>generated footage</div>
      )}
      {p.caption && <AbsoluteFill style={{ background: `linear-gradient(to top, ${C.ink}E6 0%, ${C.ink}80 22%, transparent 45%)` }} />}
      {p.caption && (
        <div style={{ position: "absolute", left: safe.left, bottom: safe.bottom + 40 * u }}>
          <Headline text={p.caption} at={6} size={72} />
        </div>
      )}
    </AbsoluteFill>
  );
};

export const PhotoInsert: React.FC<P> = ({ p, dur }) => {
  const frame = useCurrentFrame();
  const asset = useAsset();
  const { safe, u } = useFormat();
  const kb = useMemo(() => multiKeys(p.kenBurns ?? [[0, 1.0, 0, 0], [dur, 1.08, 0, -10]]), [p.kenBurns, dur]);
  const [s, x, y] = kb(frame);
  return (
    <AbsoluteFill style={{ background: C.ink, overflow: "hidden" }}>
      <Img src={asset(p.src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `translate(${x}px, ${y}px) scale(${s})` }} />
      {p.caption && <AbsoluteFill style={{ background: `linear-gradient(to top, ${C.ink}E6 0%, ${C.ink}80 22%, transparent 45%)` }} />}
      {p.caption && (
        <div style={{ position: "absolute", left: safe.left, bottom: safe.bottom + 40 * u }}>
          <Headline text={p.caption} at={6} size={72} />
        </div>
      )}
    </AbsoluteFill>
  );
};

export const Missing: React.FC<{ kind: string }> = ({ kind }) => {
  const { debug } = useFilm();
  return (
    <AbsoluteFill style={{ background: "#300", color: "#fff", display: "grid", placeItems: "center", fontSize: 40 }}>
      {debug ? `unknown scene kind ${kind}` : ""}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ hook

type HookLine = { text: string; at?: number; accent?: boolean; size?: number };

/** Scroll-stopper: full-bleed image / video / real GLB with a punch-in, a flash + shake on the cut, and huge lines
 *  that slam in. Lines are honest claims only (real timings come from the capture log). */
export const Hook: React.FC<P> = ({ p, dur }) => {
  const frame = useCurrentFrame();
  const asset = useAsset();
  const { w, h, safe, u, vertical } = useFormat();
  const zoom = useMemo(() => multiKeys(p.zoomKeys ?? [[0, 1.14], [dur, 1.0]]), [p.zoomKeys, dur]);
  const [z] = zoom(frame);
  const flash = p.flash === false ? 0 : tween(frame, 0, 6, 0.8, 0, "outCubic");
  const shake = frame < 8 ? Math.sin(frame * 2.3) * (8 - frame) * 1.4 * u : 0;
  const bottom = p.place === "bottom";
  return (
    <AbsoluteFill style={{ background: C.ink, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translateX(${shake}px) scale(${z})` }}>
        {p.glb && <Stage3D width={w} height={h} glb={asset(p.glb)} hdri={p.hdri ? asset(p.hdri) : undefined} camKeys={p.camKeys} carKeys={p.carKeys} tunnel={p.tunnel} />}
        {p.src && p.video && <OffthreadVideo src={asset(p.src)} startFrom={Math.round((p.trimSec ?? 0) * 30)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
        {p.src && !p.video && <Img src={asset(p.src)} style={{ width: "100%", height: "100%", objectFit: p.fit ?? "cover" }} />}
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `linear-gradient(to bottom, ${C.ink}D9 0%, transparent 40%, transparent 60%, ${C.ink}D9 100%)` }} />
      {p.generated && (
        <div style={{ position: "absolute", right: safe.right, top: safe.top, fontFamily: F.mono, fontSize: 18 * Math.max(1, u), color: C.muted[0], opacity: 0.8 }}>generated footage</div>
      )}
      <div style={{ position: "absolute", left: safe.left, right: safe.right, top: bottom ? undefined : safe.top + (vertical ? 140 : 30) * u,
                    bottom: bottom ? safe.bottom + (vertical ? 160 : 50) * u : undefined, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 * u }}>
        {((p.lines ?? []) as HookLine[]).map((l, i) => {
          const k = tween(frame, l.at ?? 0, 6, 0, 1, "outCubic");
          return (
            <div key={i} style={{ fontFamily: F.display, fontWeight: 800, fontSize: (l.size ?? (vertical ? 112 : 100)) * u, lineHeight: 1.0,
                                  letterSpacing: "-0.035em", textAlign: "center", color: l.accent ? C.accent : C.text, opacity: k,
                                  transform: `scale(${1.35 - 0.35 * k})`, filter: `blur(${(1 - k) * 8}px)`, textShadow: `0 ${6 * u}px ${36 * u}px ${C.ink}` }}>
              {l.text}
            </div>
          );
        })}
      </div>
      {flash > 0 && <AbsoluteFill style={{ background: "#fff", opacity: flash }} />}
    </AbsoluteFill>
  );
};

export const SCENES: Record<string, React.FC<P>> = {
  hook: Hook,
  cold_open: ColdOpen,
  chat: Chat,
  plot_twist: PlotTwist,
  url_to_logo: UrlToLogo,
  product_shot: ProductShot,
  before_after: BeforeAfter,
  triptych: Triptych,
  image_to_3d: ImageTo3D,
  finale_3d: Finale3D,
  end_room: EndRoom,
  end_card: EndCard,
  video_clip: VideoClip,
  photo_insert: PhotoInsert,
};
