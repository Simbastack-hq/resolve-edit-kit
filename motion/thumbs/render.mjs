// Render thumbnail pages (thumbs/*.html) to 1920x1080 JPG next to this folder's parent. usage: node render.mjs [ids...]
// Check every design at phone size too (360x202 and 168x94) before choosing.
import { chromium } from 'playwright-core';
import fs from 'fs'; import path from 'path'; import { fileURLToPath, pathToFileURL } from 'url';
const ROOT = path.dirname(fileURLToPath(import.meta.url)); const OUT = path.join(ROOT, 'out'); fs.mkdirSync(OUT, { recursive: true });
const ids = process.argv.slice(2).length ? process.argv.slice(2) : fs.readdirSync(ROOT).filter(f => f.endsWith('.html')).map(f => f.replace('.html', ''));
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined, args: ['--allow-file-access-from-files', '--force-color-profile=srgb', '--font-render-hinting=none'] });
for (const id of ids) {
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage(); page.on('pageerror', e => console.error(id, 'PAGE ERROR', e.message));
  await page.goto(pathToFileURL(path.join(ROOT, id + '.html')).href); await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState('networkidle');
  fs.writeFileSync(path.join(OUT, id + '.jpg'), await page.screenshot({ type: 'jpeg', quality: 92 }));
  console.log('ok', id, '->', path.join(OUT, id + '.jpg')); await ctx.close();
}
await browser.close();
