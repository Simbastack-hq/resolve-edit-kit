// Deterministic motion helpers: every visual state is a pure function of t (seconds).
(function(){
const E = {
  linear: x => x,
  outCubic: x => 1 - Math.pow(1 - x, 3),
  outQuart: x => 1 - Math.pow(1 - x, 4),
  outQuint: x => 1 - Math.pow(1 - x, 5),
  outExpo: x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x),
  inExpo: x => x <= 0 ? 0 : Math.pow(2, 10 * x - 10),
  inCubic: x => x * x * x,
  inQuart: x => x * x * x * x,
  inOutCubic: x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2,
  inOutQuint: x => x < .5 ? 16 * Math.pow(x, 5) : 1 - Math.pow(-2 * x + 2, 5) / 2,
  inOutExpo: x => x <= 0 ? 0 : x >= 1 ? 1 : x < .5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2,
  outBack: x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
  outBackSoft: x => { const c1 = 1.1, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
  outElastic: x => x <= 0 ? 0 : x >= 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - .75) * (2 * Math.PI) / 3) + 1,
};
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const mix = (a, b, x) => a + (b - a) * x;
// progress of t through [a,b] with easing
const P = (t, a, b, e = 'outCubic') => E[e](clamp((t - a) / Math.max(1e-6, b - a)));
// keyframes: [[t, v, ease], ...] -> value (numbers or arrays)
function K(t, keys) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1, e] = keys[i], [t0, v0] = keys[i - 1];
    if (t <= t1) {
      const x = E[e || 'inOutCubic'](clamp((t - t0) / (t1 - t0)));
      return Array.isArray(v0) ? v0.map((v, j) => mix(v, v1[j], x)) : mix(v0, v1, x);
    }
  }
  return keys[keys.length - 1][1];
}
// apply a transform/opacity/blur state to an element
function S(el, st) {
  if (!el) return;
  const { x = 0, y = 0, s = 1, sx, sy, r = 0, o, blur, z } = st;
  el.style.transform = `translate3d(${x}px,${y}px,0) rotate(${r}deg) scale(${sx ?? s},${sy ?? s})`;
  if (o !== undefined) el.style.opacity = o;
  if (blur !== undefined) el.style.filter = blur > 0.05 ? `blur(${blur}px)` : 'none';
  if (z !== undefined) el.style.zIndex = z;
}
// enter at t0 (pop / slide), leave at t1: returns {i, o} progress and applies a default style
function life(el, t, t0, t1, opt = {}) {
  const dIn = opt.in ?? .5, dOut = opt.out ?? .32, from = opt.from ?? 'pop', to = opt.to ?? 'fade';
  const a = P(t, t0, t0 + dIn, opt.ein ?? (from === 'pop' ? 'outBack' : 'outExpo'));
  const b = P(t, t1 - dOut, t1, opt.eout ?? 'inCubic');
  let x = 0, y = 0, s = 1, o = Math.min(clamp((t - t0) / (dIn * .35)), 1 - b), blur = 0;
  const dist = opt.dist ?? 80;
  if (from === 'pop') s = mix(opt.s0 ?? .55, 1, a);
  if (from === 'left') x = mix(-dist, 0, a); if (from === 'right') x = mix(dist, 0, a);
  if (from === 'up') y = mix(-dist, 0, a); if (from === 'down') y = mix(dist, 0, a);
  if (to === 'fade') { s *= mix(1, .94, b); blur = 8 * b; }
  if (to === 'left') x += mix(0, -dist * 2, b); if (to === 'right') x += mix(0, dist * 2, b);
  if (to === 'up') y += mix(0, -dist * 2, b); if (to === 'down') y += mix(0, dist * 2, b);
  if (to === 'zoom') { s *= mix(1, 2.4, b); blur = 18 * b; }
  if (opt.drift) { s *= 1 + opt.drift * clamp((t - t0) / Math.max(1, t1 - t0)); }
  if (t < t0 || t > t1) o = 0;
  S(el, { x: x + (opt.x || 0), y: y + (opt.y || 0), s, r: opt.r || 0, o, blur });
  return { i: a, o: b };
}
// reveal text word by word (spans) between t0..t1 or with explicit per-word times
function words(el, text) {
  el.innerHTML = '';
  return text.split(' ').map(w => { const s = document.createElement('span'); s.className = 'w'; s.textContent = w + ' '; el.appendChild(s); return s; });
}
function typeUntil(el, full, n) { el.textContent = full.slice(0, Math.max(0, Math.floor(n))); }
// seeded random
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const $ = (q, r = document) => r.querySelector(q), $$ = (q, r = document) => [...r.querySelectorAll(q)];
Object.assign(window, { E, clamp, mix, P, K, S, life, words, typeUntil, rng, $, $$ });
// frames of footage for PiP scenes: window.FOOT = {dir, n}; setFoot(img, t)
window.setFoot = async (img, t) => {
  if (!window.FOOT) return;
  const i = Math.min(FOOT.n - 1, Math.max(0, Math.round(t * 29.97)));
  const src = `${FOOT.dir}/${String(i + 1).padStart(5, '0')}.jpg`;
  if (img.getAttribute('src') !== src) { img.src = src; await img.decode().catch(() => {}); }
};
})();
