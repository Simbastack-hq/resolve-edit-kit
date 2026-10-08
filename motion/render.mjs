// Render a graphics page (g/<id>.html) frame by frame in headless Chromium, then encode it for Resolve.
//   overlays (transparent) -> ProRes 4444 with alpha (Resolve reads it as "Straight");  pages with window.OPAQUE -> ProRes 422 HQ
// usage: node render.mjs <id> [--stills t1,t2,...] [--from s] [--to s] [--workers 5] [--out DIR] [--suffix -v2]
// needs: npm install (playwright-core), a Chromium (npx playwright install chromium, or set CHROME_PATH), ffmpeg on PATH.
import { chromium } from 'playwright-core';
import fs from 'fs'; import path from 'path'; import { fileURLToPath, pathToFileURL } from 'url'; import { execFileSync } from 'child_process';
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const cfgFile = process.env.KIT_CONFIG || path.join(ROOT, 'kit.json');
const CFG = fs.existsSync(cfgFile) ? JSON.parse(fs.readFileSync(cfgFile, 'utf8')) : {};
const FPS = Math.abs((CFG.fps ?? 29.97) - 29.97) < 0.01 ? 30000 / 1001 : CFG.fps;
const RATE = Math.abs(FPS - 30000 / 1001) < 1e-6 ? '30000/1001' : String(FPS);
const args = process.argv.slice(2); const id = args[0];
const opt = k => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : undefined; };
if (!id) { console.error('usage: node render.mjs <id> [--stills ...]'); process.exit(1); }
const file = path.join(ROOT, 'g', id + '.html');
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined,
  args: ['--allow-file-access-from-files', '--disable-web-security', '--force-color-profile=srgb', '--font-render-hinting=none'] });
async function newPage() {
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await page.goto(pathToFileURL(file).href);
  await page.evaluate(() => document.fonts.ready);
  if (await page.evaluate(() => typeof window.setup === 'function')) await page.evaluate(() => window.setup());
  return page;
}
const probe = await newPage();
const meta = await probe.evaluate(() => ({ dur: window.DUR, opaque: !!window.OPAQUE }));
async function shot(page, t, out) {
  await page.evaluate(async t => { await window.render(t); }, t);
  const buf = await page.screenshot({ omitBackground: !meta.opaque, type: meta.opaque ? 'jpeg' : 'png', quality: meta.opaque ? 95 : undefined });
  fs.writeFileSync(out, buf);
}
const stills = opt('stills');
if (stills) {
  const dir = path.join(ROOT, 'out', 'stills', id); fs.mkdirSync(dir, { recursive: true });
  for (const s of stills.split(',')) await shot(probe, parseFloat(s), path.join(dir, `${id}_${s}.png`));
  console.log('stills ->', dir); await browser.close(); process.exit(0);
}
const t0 = parseFloat(opt('from') ?? 0), t1 = parseFloat(opt('to') ?? meta.dur);
const n = Math.round((t1 - t0) * FPS);
const fdir = path.join(ROOT, 'frames', id); fs.rmSync(fdir, { recursive: true, force: true }); fs.mkdirSync(fdir, { recursive: true });
const W = parseInt(opt('workers') ?? 5);
const pages = [probe]; for (let i = 1; i < W; i++) pages.push(await newPage());
const ext = meta.opaque ? 'jpg' : 'png';
let next = 0; const tStart = Date.now();
await Promise.all(pages.map(async pg => { while (true) { const i = next++; if (i >= n) break; await shot(pg, t0 + i / FPS, path.join(fdir, `${String(i + 1).padStart(5, '0')}.${ext}`)); } }));
await browser.close();
const outDir = opt('out') || CFG.gfx_out || path.join(ROOT, 'out', 'gfx'); fs.mkdirSync(outDir, { recursive: true });
const out = path.join(outDir, id + (opt('suffix') ?? '') + '.mov');
const enc = meta.opaque ? ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le'] : ['-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', '-alpha_bits', '16'];
execFileSync('ffmpeg', ['-v', 'error', '-y', '-framerate', RATE, '-i', path.join(fdir, `%05d.${ext}`), ...enc, '-vendor', 'apl0', out]);
console.log(JSON.stringify({ id, frames: n, secs: ((Date.now() - tStart) / 1000).toFixed(1), out }));
