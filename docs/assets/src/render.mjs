// Renders docs/assets/hero.gif, shapes.png and redeploy.png from the HTML files in this folder.
// Usage (from this folder): npm ci && npx playwright install chromium && python3 fetch_fonts.py && node render.mjs
// PW_EXE=/path/to/chromium uses an existing browser instead of the one Playwright downloads.
import { chromium } from "playwright";
import { mkdirSync, rmSync } from "fs";
import { execFileSync } from "child_process";

const b = await chromium.launch(process.env.PW_EXE ? { executablePath: process.env.PW_EXE } : {});
const url = (f) => "file://" + process.cwd() + "/" + f;

// Static diagrams at 2x for sharp text.
for (const [src, out, h] of [["shapes.html", "../shapes.png", 620], ["redeploy.html", "../redeploy.png", 560]]) {
  const p = await b.newPage({ viewport: { width: 1280, height: h }, deviceScaleFactor: 2 });
  await p.goto(url(src));
  await p.waitForFunction(() => window.ready === true);
  await (await p.$("#stage")).screenshot({ path: out });
}

// Animated hero: step the timeline frame by frame, then encode with ffmpeg.
const p = await b.newPage({ viewport: { width: 1280, height: 740 }, deviceScaleFactor: 1 });
await p.goto(url("hero.html"));
await p.waitForFunction(() => window.ready === true);
rmSync("frames", { recursive: true, force: true });
mkdirSync("frames");
const fps = 15, dur = await p.evaluate(() => window.DURATION);
const el = await p.$("#stage");
for (let i = 0; i < Math.round(dur * fps); i++) {
  await p.evaluate((t) => window.setT(t), i / fps);
  await el.screenshot({ path: `frames/${String(i).padStart(4, "0")}.png` });
}
await b.close();
execFileSync("ffmpeg", ["-v", "error", "-y", "-framerate", String(fps), "-i", "frames/%04d.png", "-vf",
  "split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
  "-loop", "0", "../hero.gif"], { stdio: "inherit" });
rmSync("frames", { recursive: true, force: true });
