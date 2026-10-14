// Renders the X article visuals into docs/assets/x/.
// Usage (from this folder): npm ci && npx playwright install chromium && python3 fetch_fonts.py && node render-x.mjs
// PW_EXE=/path/to/chromium uses an existing browser instead of the one Playwright downloads.
import { chromium } from "playwright";
import { mkdirSync, rmSync } from "fs";
import { execFileSync } from "child_process";

const OUT = "../x";
mkdirSync(OUT, { recursive: true });
const b = await chromium.launch(process.env.PW_EXE ? { executablePath: process.env.PW_EXE } : {});
const url = (f) => "file://" + process.cwd() + "/" + f;

async function still(src, out, w, h, scale) {
  const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: scale });
  await p.goto(url(src));
  await p.waitForFunction(() => window.ready === true);
  await (await p.$("#stage")).screenshot({ path: `${OUT}/${out}` });
  await p.close();
}
await still("x-cover.html?w=1600&h=900", "cover.png", 1600, 900, 1);
await still("x-cover.html?w=1500&h=600", "cover-wide.png", 1500, 600, 1);
await still("x-race.html?ladder=1", "cold-ladder.png", 1200, 675, 2);
await still("x-redeploy.html", "redeploy.png", 1200, 675, 2);
await still("x-waterfall.html", "waterfall.png", 1200, 675, 2);

// Animated race, encoded with ffmpeg.
const p = await b.newPage({ viewport: { width: 1200, height: 675 }, deviceScaleFactor: 1 });
await p.goto(url("x-race.html"));
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
  "-loop", "0", `${OUT}/race.gif`], { stdio: "inherit" });
rmSync("frames", { recursive: true, force: true });
