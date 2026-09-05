// tools/sf-measure.mjs — Xiva starfield o'qilish (legibility) o'lchagichi.
// Headless Chrome (CDP, alohida kutubxona kerak emas) bosh sahifani 9 scroll-nuqtadan o'tkazadi,
// har birida skrinshot oladi va HAR KO'RINADIGAN MATN ELEMENTI ostidagi canvas piksellarining
// yorug'ligini o'lchaydi (canvas CSS opacity hisobga olinadi; DOM-skrimlar hisobga OLINMAYDI).
//   mean / p95 / p99 / max — 0..255 luminance;  bright% = L>60 piksellar ulushi;  hot% = L>140.
// Foydalanish (runserver yoki prod URL bilan):
//   node tools/sf-measure.mjs http://localhost:8000/xo/ /tmp/sf before 1440 900
//   node tools/sf-measure.mjs http://localhost:8000/xo/ /tmp/sf before-m 390 844
//   RM=1 node tools/sf-measure.mjs ...        # prefers-reduced-motion emulyatsiyasi
// Chiqish: <outDir>/<tag>-NN.png skrinshotlar + <tag>-metrics.json + AGGREGATE satri.
// 2026-09-05 baza (HEAD 3cf807a) → tuzatishdan keyin: docs/starfield-implementation.md §11.
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, rmSync } from 'node:fs';

const [, , url = 'http://localhost:8000/xo/', outDir = './out', tag = 'run', wArg = '1440', hArg = '900'] = process.argv;
const W = +wArg, H = +hArg;
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'; // CHROME=... bilan almashtirish mumkin
const port = 9300 + Math.floor(Math.random() * 500);
const profile = `${outDir}/.chrome-profile-${port}`;
mkdirSync(outDir, { recursive: true });
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let targets = [];
for (let i = 0; i < 60; i++) {
  try { const r = await fetch(`http://127.0.0.1:${port}/json/list`); targets = await r.json(); if (targets.some((t) => t.type === 'page')) break; } catch {}
  await sleep(200);
}
const page = targets.find((t) => t.type === 'page');
if (!page) { console.error('no page target'); chrome.kill(); process.exit(1); }
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); } };
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
};

await send('Page.enable');
await send('Runtime.enable');
const jsErrors = [];
const _onmsg = ws.onmessage;
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.method === 'Runtime.exceptionThrown') jsErrors.push(JSON.stringify(m.params.exceptionDetails).slice(0, 400)); if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') jsErrors.push('console.error: ' + JSON.stringify(m.params.args).slice(0, 300)); _onmsg(e); };
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: W < 768 });
if (process.env.RM === '1') await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
await send('Page.navigate', { url });
await sleep(2500);
for (let i = 0; i < 40; i++) { if (await evalJs("!!document.querySelector('body > canvas[aria-hidden]')")) break; await sleep(250); }
await sleep(2500);

const MEASURE = `(() => {
  const canvas = document.querySelector('body > canvas[aria-hidden]');
  if (!canvas) return { error: 'no canvas' };
  const ctx = canvas.getContext('2d');
  const op = parseFloat(getComputedStyle(canvas).opacity) || 1; // CSS layer opacity (post-additive cap)
  const sx = canvas.width / innerWidth, sy = canvas.height / innerHeight;
  const vw = innerWidth, vh = innerHeight;
  const lum = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
  function region(x0, y0, x1, y1) {
    x0 = Math.max(0, Math.floor(x0)); y0 = Math.max(0, Math.floor(y0)); x1 = Math.min(vw, Math.ceil(x1)); y1 = Math.min(vh, Math.ceil(y1));
    const w = Math.round((x1 - x0) * sx), h = Math.round((y1 - y0) * sy); if (w < 1 || h < 1) return null;
    const d = ctx.getImageData(Math.round(x0 * sx), Math.round(y0 * sy), w, h).data;
    const arr = new Float32Array(w * h); let sum = 0, bright = 0, hot = 0;
    for (let i = 0; i < d.length; i += 4) { const a = d[i + 3] / 255; const L = lum(d[i], d[i + 1], d[i + 2]) * a * op; arr[i >> 2] = L; sum += L; if (L > 60) bright++; if (L > 140) hot++; }
    arr.sort();
    const n = arr.length;
    return { mean: +(sum / n).toFixed(2), p95: +arr[Math.floor(n * 0.95)].toFixed(1), p99: +arr[Math.floor(n * 0.99)].toFixed(1), max: +arr[n - 1].toFixed(1), brightFrac: +(bright / n).toFixed(4), hotFrac: +(hot / n).toFixed(4), px: n };
  }
  const SEL = 'h1,h2,h3,h4,p,li,blockquote,.eyebrow,.tag,dt,dd,figcaption,summary,td,th,.stat-num,.metric-num';
  const els = [...document.querySelectorAll(SEL)].filter((el) => {
    if (el.closest('canvas')) return false;
    const t = (el.innerText || '').trim(); if (!t) return false;
    const r = el.getBoundingClientRect();
    return r.width > 20 && r.height > 8 && r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw;
  });
  const items = els.map((el) => {
    const r = el.getBoundingClientRect(); const m = region(r.left, r.top, r.right, r.bottom); if (!m) return null;
    const host = el.closest('.band--sf,.ticker-band--sf,.surface-raised--sf,.hero,.cta-section,.section');
    return Object.assign({ tag: el.tagName.toLowerCase(), cls: String(el.className || '').split(' ').filter(Boolean).slice(0, 2).join('.'),
      text: (el.innerText || '').trim().slice(0, 42).replace(/\\s+/g, ' '), host: host ? host.className.split(' ').find((c) => /--sf|hero|section/.test(c)) : null,
      rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] }, m);
  }).filter(Boolean);
  return { scrollY: Math.round(scrollY), canvasOpacity: op, viewport: region(0, 0, vw, vh), items, cfg: window.XIVA_STARFIELD };
})()`;

const stops = [0, 0.1, 0.22, 0.36, 0.5, 0.64, 0.78, 0.92, 1];
const results = [];
for (const [i, frac] of stops.entries()) {
  await evalJs(`(() => { const m = Math.max(1, document.documentElement.scrollHeight - innerHeight); scrollTo(0, ${frac} * m); return scrollY; })()`);
  await sleep(3300);
  const m = await evalJs(MEASURE);
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  const file = `${outDir}/${tag}-${String(i).padStart(2, '0')}.png`;
  writeFileSync(file, Buffer.from(shot.data, 'base64'));
  results.push(Object.assign({ stop: i, frac, file }, m));
}
writeFileSync(`${outDir}/${tag}-metrics.json`, JSON.stringify(results, null, 1));

// summary: per stop, viewport mean + worst text elements
let worstAll = [];
for (const r of results) {
  if (r.error) { console.log(`stop ${r.stop}: ${r.error}`); continue; }
  const worst = [...r.items].sort((a, b) => b.brightFrac - a.brightFrac).slice(0, 3);
  console.log(`stop ${r.stop} frac=${r.frac} scrollY=${r.scrollY} | viewport mean=${r.viewport.mean} p99=${r.viewport.p99} bright%=${(r.viewport.brightFrac * 100).toFixed(2)} hot%=${(r.viewport.hotFrac * 100).toFixed(2)} | text elems=${r.items.length}`);
  for (const w of worst) console.log(`    ${w.tag}${w.cls ? '.' + w.cls : ''} [${w.host}] "${w.text}" mean=${w.mean} p95=${w.p95} p99=${w.p99} max=${w.max} bright%=${(w.brightFrac * 100).toFixed(2)} hot%=${(w.hotFrac * 100).toFixed(2)}`);
  worstAll.push(...r.items.map((it) => Object.assign({ stop: r.stop }, it)));
}
const agg = worstAll.length ? {
  textElems: worstAll.length,
  meanOfMeans: +(worstAll.reduce((s, x) => s + x.mean, 0) / worstAll.length).toFixed(2),
  avgBrightPct: +(100 * worstAll.reduce((s, x) => s + x.brightFrac, 0) / worstAll.length).toFixed(2),
  avgHotPct: +(100 * worstAll.reduce((s, x) => s + x.hotFrac, 0) / worstAll.length).toFixed(3),
  elemsWithBrightOver5pct: worstAll.filter((x) => x.brightFrac > 0.05).length,
  elemsWithHotOver1pct: worstAll.filter((x) => x.hotFrac > 0.01).length,
} : null;
console.log('AGGREGATE(text under stars):', JSON.stringify(agg));
console.log('JS_ERRORS:', jsErrors.length ? JSON.stringify(jsErrors) : 'none');
try { ws.close(); } catch {}
chrome.kill();
rmSync(profile, { recursive: true, force: true });
