// Render many stills from one bundle, reusing one browser (renderStill + puppeteerInstance).
//   node scripts/stills.mjs job.json
// job: { props: path, out: dir, scale, port, jobs: [{ comp, frames: [..] }] }
import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const job = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const inputProps = JSON.parse(fs.readFileSync(job.props, "utf8"));
fs.mkdirSync(job.out, { recursive: true });

const serveUrl = await bundle({ entryPoint: path.join(here, "..", "src", "index.ts") });
const browser = await openBrowser("chrome", { chromiumOptions: { gl: job.gl ?? "angle" } });
const written = [];
try {
  for (const j of job.jobs) {
    const composition = await selectComposition({ serveUrl, id: j.comp, inputProps, puppeteerInstance: browser, port: job.port ?? null });
    for (const frame of j.frames) {
      const f = Math.min(composition.durationInFrames - 1, Math.max(0, frame));
      const output = path.join(job.out, `${j.comp}_f${String(f).padStart(5, "0")}.${job.format ?? "jpeg"}`);
      await renderStill({
        serveUrl,
        composition,
        inputProps,
        frame: f,
        output,
        imageFormat: job.format ?? "jpeg",
        ...((job.format ?? "jpeg") === "jpeg" ? { jpegQuality: 92 } : {}),
        scale: job.scale ?? 1,
        puppeteerInstance: browser,
        port: job.port ?? null,
        timeoutInMilliseconds: job.timeout ?? 240000,
        chromiumOptions: { gl: job.gl ?? "angle" },
      });
      written.push(output);
      process.stdout.write(`still ${output}\n`);
    }
  }
} finally {
  await browser.close({ silent: true });
}
fs.writeFileSync(path.join(job.out, "stills.json"), JSON.stringify(written, null, 1));
