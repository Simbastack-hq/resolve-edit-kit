// Brand logos for graphics pages. Empty on purpose: logos are trademarks, so add only the ones you have the right to use.
// Simple Icons (https://simpleicons.org, CC0 SVG paths) is a good source: copy a 24x24 icon's path into an entry.
//   window.LOGOS.github = {vb: "0 0 24 24", d: ["M12 .297c-6.63 ..."]};
// Then in a page: el.appendChild(logo('github', '#fff', 48)).
window.LOGOS = window.LOGOS || {};
window.logo = function(name, color, size){
  const L = LOGOS[name], ns = 'http://www.w3.org/2000/svg', s = document.createElementNS(ns, 'svg');
  s.style.width = s.style.height = (size || 48) + 'px'; s.style.display = 'block';
  if (!L) { s.setAttribute('viewBox', '0 0 24 24'); const c = document.createElementNS(ns, 'circle'); c.setAttribute('cx', 12); c.setAttribute('cy', 12); c.setAttribute('r', 11); c.setAttribute('fill', color || 'currentColor'); s.appendChild(c); return s; }
  s.setAttribute('viewBox', L.vb);
  for (const d of L.d) { const p = document.createElementNS(ns, 'path'); p.setAttribute('d', d); p.setAttribute('fill', color || 'currentColor'); s.appendChild(p); }
  return s;
};
