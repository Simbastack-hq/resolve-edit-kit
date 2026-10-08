// Shared building blocks for graphics pages: h() element helper, browser window, file chip, PiP transition, animated wire.
(function(){
const h = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html !== undefined) e.innerHTML = html; return e; };
// Browser window around content
function browser(url, inner, w) {
  const b = h('div', 'browser'); if (w) b.style.width = w + 'px';
  b.innerHTML = `<div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span><div class="url"><span class="lock">🔒</span><span class="u">${url}</span></div></div><div class="vp"></div><div class="load"></div>`;
  b.querySelector('.vp').appendChild(inner); return b;
}
// File chip
function file(name, color = '#D97757') {
  const e = h('div', 'file'); e.innerHTML = `<span class="fi" style="background:${color}"></span>${name}`; return e;
}
// Full frame <-> PiP transition on an element that holds the footage <img>.
// rect: [x,y,w,h]; returns progress 0 (full) .. 1 (pip)
function pip(el, t, tIn, tOut, rect, d = .6) {
  const a = P(t, tIn, tIn + d, 'inOutQuint'), b = P(t, tOut - d, tOut, 'inOutQuint');
  const k = Math.min(a, 1 - b);
  const [x, y, w, hh] = rect;
  el.style.left = mix(0, x, k) + 'px'; el.style.top = mix(0, y, k) + 'px';
  el.style.width = mix(1920, w, k) + 'px'; el.style.height = mix(1080, hh, k) + 'px';
  el.style.borderRadius = mix(0, 30, k) + 'px';
  el.style.boxShadow = `0 30px 80px rgba(0,0,0,${.55*k}),0 0 0 ${3*k}px rgba(255,255,255,${.9*k})`;
  return k;
}
// An SVG path "drawn" over time with moving packets; returns fn(t)
function wire(svg, d, opts = {}) {
  const ns = 'http://www.w3.org/2000/svg';
  const base = document.createElementNS(ns, 'path'); base.setAttribute('d', d); base.setAttribute('fill', 'none');
  base.setAttribute('stroke', opts.color || 'rgba(255,255,255,.25)'); base.setAttribute('stroke-width', opts.w || 6); base.setAttribute('stroke-linecap', 'round');
  base.setAttribute('stroke-dasharray', opts.dash || '2 16');
  const live = base.cloneNode(); live.setAttribute('stroke', opts.live || '#D97757'); live.setAttribute('stroke-dasharray', '');
  svg.appendChild(base); svg.appendChild(live);
  const L = base.getTotalLength(); live.style.strokeDasharray = `${L} ${L}`;
  const dots = [...Array(opts.n || 3)].map(() => { const c = document.createElementNS(ns, 'circle'); c.setAttribute('r', opts.r || 9); c.setAttribute('fill', opts.dot || '#fff'); svg.appendChild(c); return c; });
  return (draw, flow, alpha = 1) => {   // draw 0..1, flow = time for packets
    base.style.opacity = alpha * clamp(draw * 3); live.style.strokeDashoffset = L * (1 - draw); live.style.opacity = alpha;
    dots.forEach((c, i) => { const u = ((flow * (opts.speed || .6)) + i / dots.length) % 1; const pt = base.getPointAtLength(u * L * draw);
      c.setAttribute('cx', pt.x); c.setAttribute('cy', pt.y); c.style.opacity = draw >= 1 ? alpha * Math.sin(Math.PI * u) : 0; });
  };
}
Object.assign(window, { h, browser, file, pip, wire });
})();
