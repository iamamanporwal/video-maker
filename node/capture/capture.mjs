// ReelForge capture driver: runs one take as a list of primitive steps against the real product.
//
//   node capture.mjs job.json
//
// Records a CDP screencast (JPEG frames with timestamps), every named event and every pointer
// position, so the film's cursor, click ripples and stroke overlays can be rebuilt from logs.
// Product UI is never altered; the only cosmetics are text swaps declared in the job (e.g. the
// test email -> "Studio"), applied during capture only.

import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const job = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = job.outDir;
fs.mkdirSync(path.join(out, "frames"), { recursive: true });
fs.mkdirSync(path.join(out, "shots"), { recursive: true });

const VW = job.viewport?.width ?? 1920;
const VH = job.viewport?.height ?? 1080;
const DPR = job.dpr ?? 2;

const frames = []; // {t, file}
const events = []; // {t, name, ...}
const mouse = []; // {t, x, y, down}
let t0 = null;
const now = () => (t0 === null ? 0 : Date.now() - t0);
const ev = (name, extra = {}) => {
  events.push({ t: now(), name, ...extra });
  log(`event ${name}`);
};
function log(msg) {
  process.stdout.write(`[capture ${job.take} ${(now() / 1000).toFixed(2)}s] ${msg}\n`);
}

const ctx = await chromium.launchPersistentContext(job.profileDir, {
  headless: job.headless ?? false,
  executablePath: job.chromePath || undefined,
  viewport: { width: VW, height: VH },
  deviceScaleFactor: DPR,
  acceptDownloads: true,
  ...(job.storageState ? { storageState: job.storageState } : {}),
});

// --- auth: seed the app session into localStorage before any app script runs.
if (job.auth?.token) {
  await ctx.addInitScript(
    ([key, token, extra]) => {
      try {
        localStorage.setItem(key, token);
        for (const [k, v] of Object.entries(extra || {})) localStorage.setItem(k, v);
      } catch {}
    },
    [job.auth.key ?? "auth_token", job.auth.token, job.auth.extra ?? {}],
  );
}

// --- cosmetics (capture only): swap text nodes, e.g. the test email for a studio name.
if (job.cosmetics?.replaceText && Object.keys(job.cosmetics.replaceText).length) {
  await ctx.addInitScript((map) => {
    const swap = (root) => {
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = w.nextNode())) {
        for (const [a, b] of Object.entries(map)) if (n.nodeValue.includes(a)) n.nodeValue = n.nodeValue.split(a).join(b);
      }
    };
    new MutationObserver((ms) => ms.forEach((m) => m.addedNodes.forEach((x) => x.nodeType === 1 && swap(x)))).observe(
      document,
      { childList: true, subtree: true, characterData: true },
    );
    document.addEventListener("DOMContentLoaded", () => swap(document.body));
  }, job.cosmetics.replaceText);
}

// --- keep frames flowing: a 1px rAF-animated element forces continuous compositor frames.
await ctx.addInitScript(() => {
  const go = () => {
    const d = document.createElement("div");
    d.style.cssText = "position:fixed;left:0;top:0;width:1px;height:1px;opacity:0.01;pointer-events:none;z-index:2147483647";
    document.documentElement.appendChild(d);
    let i = 0;
    const tick = () => {
      d.style.transform = `translateX(${(i++ % 2) * 0.5}px)`;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
  else go();
});

const page = ctx.pages()[0] ?? (await ctx.newPage());
const cdp = await ctx.newCDPSession(page);
let frameNo = 0;
cdp.on("Page.screencastFrame", async (f) => {
  const file = `f_${String(frameNo++).padStart(6, "0")}.jpg`;
  fs.writeFileSync(path.join(out, "frames", file), Buffer.from(f.data, "base64"));
  const tsMs = f.metadata.timestamp ? f.metadata.timestamp * 1000 : Date.now();
  frames.push({ t: tsMs - (t0 ?? tsMs), file });
  cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
});

// --- humanised pointer
let pos = { x: VW / 2, y: VH / 2 };
let down = false;
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
async function moveTo(x, y, ms = 650) {
  const sx = pos.x, sy = pos.y;
  const dx = x - sx, dy = y - sy;
  const dist = Math.hypot(dx, dy);
  const steps = Math.max(8, Math.round(ms / 16));
  // Slight arc: control point offset perpendicular to the path.
  const arc = Math.min(120, dist * 0.12);
  const cx = sx + dx / 2 - (dy / (dist || 1)) * arc;
  const cy = sy + dy / 2 + (dx / (dist || 1)) * arc;
  for (let i = 1; i <= steps; i++) {
    const t = easeInOut(i / steps);
    const px = (1 - t) * (1 - t) * sx + 2 * (1 - t) * t * cx + t * t * x;
    const py = (1 - t) * (1 - t) * sy + 2 * (1 - t) * t * cy + t * t * y;
    await page.mouse.move(px, py);
    mouse.push({ t: now(), x: px, y: py, down });
    await page.waitForTimeout(ms / steps);
  }
  pos = { x, y };
}

function locate(target) {
  if (!target) throw new Error("missing target");
  if (target.selector) return page.locator(target.selector).first();
  if (target.role) {
    const name = target.regex ? new RegExp(target.regex, "i") : target.name;
    return page.getByRole(target.role, name ? { name } : {}).first();
  }
  if (target.placeholder) return page.getByPlaceholder(target.placeholder).first();
  if (target.regex) return page.getByText(new RegExp(target.regex, "i")).first();
  if (target.text) return page.getByText(target.text, { exact: target.exact ?? false }).first();
  throw new Error(`bad target ${JSON.stringify(target)}`);
}

async function centre(loc) {
  await loc.waitFor({ state: "visible", timeout: 30000 });
  const b = await loc.boundingBox();
  return { b, x: b.x + b.width / 2, y: b.y + b.height / 2 };
}

async function imageSrcs(minSize = 0) {
  return page.evaluate((min) => [...document.images]
    .filter((i) => !min || (i.complete && Math.min(i.naturalWidth, i.naturalHeight) >= min)) // skip logos/icons
    .map((i) => i.currentSrc || i.src).filter((s) => /^https?:|^blob:/.test(s)), minSize);
}

let knownImages = new Set();
let lastNewImage = null;

const actions = {
  async goto(s) {
    await page.goto(s.url, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(s.settleMs ?? 1200);
    knownImages = new Set(await imageSrcs());
  },
  async click(s) {
    const { x, y } = await centre(locate(s.target));
    await moveTo(x, y, s.moveMs ?? 650);
    await page.mouse.down();
    down = true;
    mouse.push({ t: now(), x, y, down });
    ev("click", { x, y, label: s.label ?? s.target.text ?? s.target.name ?? s.target.regex });
    await page.waitForTimeout(60);
    await page.mouse.up();
    down = false;
    mouse.push({ t: now(), x, y, down });
    if (s.event) ev(s.event);
    await page.waitForTimeout(s.afterMs ?? 400);
  },
  async move(s) {
    const { x, y } = await centre(locate(s.target));
    await moveTo(x + (s.dx ?? 0), y + (s.dy ?? 0), s.moveMs ?? 650);
  },
  async fill(s) {
    const loc = locate(s.target);
    const { x, y } = await centre(loc);
    await moveTo(x, y, s.moveMs ?? 500);
    await loc.click();
    await loc.fill(""); // stale prompt text is a known failure
    ev("typeStart", { text: s.text });
    await loc.pressSequentially(s.text, { delay: s.delay ?? 30 });
    ev("typeEnd");
    await page.waitForTimeout(s.afterMs ?? 300);
  },
  async press(s) {
    await page.keyboard.press(s.key);
  },
  async draw(s) {
    const { b } = await centre(locate(s.target));
    const toPx = ([u, v]) => [b.x + u * b.width, b.y + v * b.height];
    for (const [i, stroke] of s.strokes.entries()) {
      const [sx, sy] = toPx(stroke[0]);
      await moveTo(sx, sy, s.travelMs ?? 380);
      await page.mouse.down();
      down = true;
      ev("strokeStart", { i });
      for (const p of stroke.slice(1)) {
        const [x, y] = toPx(p);
        await page.mouse.move(x, y);
        mouse.push({ t: now(), x, y, down });
        pos = { x, y };
        await page.waitForTimeout(s.pointMs ?? 14);
      }
      await page.mouse.up();
      down = false;
      mouse.push({ t: now(), x: pos.x, y: pos.y, down });
      ev("strokeEnd", { i });
      await page.waitForTimeout(s.gapMs ?? 120);
    }
  },
  async wait(s) {
    await page.waitForTimeout(s.ms);
  },
  async wait_for(s) {
    await locate(s.target).waitFor({ state: s.state ?? "visible", timeout: s.timeoutMs ?? 60000 });
    if (s.event) ev(s.event);
  },
  // "Image ready" = a new http image src that wasn't on the page before. Counting images fires early.
  async wait_new_image(s) {
    const t = Date.now();
    while (Date.now() - t < (s.timeoutMs ?? 180000)) {
      const fresh = (await imageSrcs(s.minSize)).filter((x) => !knownImages.has(x));
      if (fresh.length) {
        lastNewImage = fresh[fresh.length - 1];
        fresh.forEach((x) => knownImages.add(x));
        await page.waitForTimeout(s.settleMs ?? 600);
        ev(s.event ?? "imageReady", { src: lastNewImage, waitMs: Date.now() - t });
        return;
      }
      await page.waitForTimeout(250);
    }
    throw new Error("timed out waiting for a new image");
  },
  async save_image(s) {
    if (!lastNewImage) throw new Error("no new image to save");
    const r = await page.request.get(lastNewImage);
    fs.writeFileSync(path.join(out, s.as ?? "out.jpg"), await r.body());
    ev("imageSaved", { file: s.as ?? "out.jpg" });
  },
  async download(s) {
    const [dl] = await Promise.all([
      page.waitForEvent("download", { timeout: s.timeoutMs ?? 600000 }),
      actions.click({ target: s.target, afterMs: 0 }),
    ]);
    await dl.saveAs(path.join(out, s.as ?? "model.glb"));
    ev("downloaded", { file: s.as ?? "model.glb" });
  },
  async screenshot(s) {
    await page.screenshot({ path: path.join(out, "shots", s.as ?? `shot_${events.length}.png`) });
  },
  async event(s) {
    ev(s.name, s.data ?? {});
  },
  async dump_ui(s) {
    const ui = await page.evaluate(() => {
      const els = [...document.querySelectorAll("button, a, input, textarea, select, [role], canvas, img")];
      return els
        .filter((e) => {
          const r = e.getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        })
        .slice(0, 600)
        .map((e) => {
          const r = e.getBoundingClientRect();
          return {
            tag: e.tagName.toLowerCase(),
            role: e.getAttribute("role"),
            text: (e.innerText || e.value || e.getAttribute("aria-label") || e.getAttribute("placeholder") || "").trim().slice(0, 80),
            box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
          };
        });
    });
    fs.writeFileSync(path.join(out, s.as ?? "ui.json"), JSON.stringify(ui, null, 1));
    ev("uiDumped", { count: ui.length });
  },
};

let ok = true;
let error = null;
try {
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: job.jpegQuality ?? 85, maxWidth: VW * DPR, maxHeight: VH * DPR, everyNthFrame: 1 });
  t0 = Date.now();
  ev("recordStart");
  for (const [i, step] of job.steps.entries()) {
    if (!actions[step.action]) throw new Error(`unknown action ${step.action}`);
    log(`step ${i} ${step.action}`);
    await actions[step.action](step);
  }
  ev("recordEnd");
} catch (e) {
  ok = false;
  error = String(e?.stack || e);
  log(`ERROR ${error}`);
  await page.screenshot({ path: path.join(out, "shots", "error.png") }).catch(() => {});
} finally {
  await cdp.send("Page.stopScreencast").catch(() => {});
  await new Promise((r) => setTimeout(r, 300));
  fs.writeFileSync(path.join(out, "frames.json"), JSON.stringify(frames));
  fs.writeFileSync(path.join(out, "events.json"), JSON.stringify(events, null, 1));
  fs.writeFileSync(path.join(out, "mouse.json"), JSON.stringify(mouse));
  fs.writeFileSync(
    path.join(out, "take.json"),
    JSON.stringify({ take: job.take, ok, error, viewport: { width: VW, height: VH }, dpr: DPR, frames: frames.length, wallMs: now() }, null, 1),
  );
  await ctx.close();
}
process.exit(ok ? 0 : 1);
