# Motion graphics as HTML pages

Graphics are HTML/SVG pages animated as a pure function of time, rendered frame by frame in headless Chromium and
encoded to ProRes for Resolve. An agent writes them well: it's just a web page with a `render(t)` function, and
every cue comes from the transcript, so a re-cut means re-render, not re-animate.

## Setup

```
cd motion && npm install            # playwright-core
npx playwright install chromium     # or point CHROME_PATH at any Chrome/Chromium
cp ../examples/kit.example.json kit.json   # footage dir, edl.json, words.json, output dir, fps
```

Copy this whole `motion/` folder into each video's project folder; the pages you write there are that video's.

## Files

- `lib/base.css`: design tokens and classes (`.big`, `.kicker`, `.card`, `.card.dark`, `.chip`, `.tag`, `.bubble.me/.ai`,
  `.browser`, `.grain`, `.glow`). Change the tokens at the top to make it your look.
- `lib/anim.js`, as globals:
  - easings `E` (`outCubic`, `outBack`, `inOutQuint`, …)
  - `P(t, a, b, ease)` (0..1 progress), `K(t, keys)` (keyframes), `mix`, `clamp`
  - `S(el, {x, y, s, r, o, blur})` (sets transform, opacity, blur)
  - `life(el, t, t0, t1, {from, to, in, out, dist, drift, s0})` (enter at t0, leave at t1)
  - `words(el, text)` (split into word spans), `rng(seed)`, `$`, `$$`
  - `setFoot(img, t)` (footage frame for scenes)
- `lib/components.js`: `h()`, `browser(url, inner, w)`, `file(name)`, `pip(el, t, tIn, tOut, rect)` (full frame to
  picture-in-picture and back), `wire(svg, path)` (a line drawn along a path with moving packets).
- `lib/logos.js`: empty logo registry plus `logo(name, color, px)`. Add only logos you have the right to use.
- `kit.py` + `kit.json`: project settings for the Python tools.
- `tlwords.py`: every kept word mapped to timeline seconds (`cues/tlwords.json`). Run it after every re-cut.
- `cues.py`: `find("a phrase")` gives that phrase's timeline time. `write(id, start, dur, cues)` writes `cues/<id>.js`
  for a page.
- `foot.py` / `foot_from_timeline.py`: footage frames for a scene, exactly as the cut plays them.
- `render.mjs`: `node render.mjs <id> --stills 0.5,1.2,…` for stills, `node render.mjs <id>` for the full `.mov`.
  A page with `window.OPAQUE = true` is a full-screen scene (ProRes 422 HQ); anything else keeps its alpha
  (ProRes 4444; Resolve reads it as "Straight").
- `preview.py <id>`: composites the stills over the real footage at that moment into `out/sheet_<id>.jpg`.
- `manifest.py`: lists rendered files with their start frames; `resolve_kit.place_graphics()` puts them on a timeline.
- `roto/`: "text behind the speaker" (Apple Vision person matte + composite).
- `thumbs/`: thumbnails built from the same system.
- `g/example-overlay.html`, `g/example-pip-scene.html`, `g/aside-scene.html`: exemplars. Copy one to start.

## Rules that kept graphics good

1. **Deterministic.** Everything is a function of `t`: no `Date.now`, no CSS transitions or animations, no
   unseeded randomness. Then any frame renders the same every time, in parallel.
2. **Never cover the face.** Overlays live in the side zones, a top band for small items, or a bottom band for lower
   thirds. Check every graphic against real frames (`preview.py`, then the Resolve composite) because people sit in
   different places in different takes. A full-screen scene keeps the speaker visible in a PiP and uses `pip()` in
   and out.
3. **Readable on a phone.** Main words 44 px or more, secondary 30 px or more, nothing under 24 px. High contrast:
   white cards with dark text, or solid chips. Never bare text over footage.
4. **Motion.** Entrances ease out (`outBack` for pops, `outExpo` for slides), exits are quick. Nothing sits frozen
   for more than about 0.8 s (add a slow drift). Every animation shows cause and effect. Stagger related items by
   0.1-0.2 s. An element lands on or just before its word.
5. **Truth.** Show only what the speaker says. No invented numbers or testimonials. A stylised UI is fine; a
   pixel copy of a real product's UI isn't. Real proof (the actual screenshot) beats a drawing of it.
6. **Don't overdo it.** Wall-to-wall animation gets tiring; leave stretches with just the person talking.
7. **A thread beats a slideshow.** One recurring element (a mock product that evolves, a step tracker, a
   problem that gets solved at the end) makes the graphics tell a story instead of decorating sentences.

## Parallel builders

For a long video, one agent can build the engine and 2 exemplars, then hand sections to several builder agents:
each gets the speaker's exact words with times, the story beats, these rules, and the files it owns
(`g/<id>.html`, `cues/<id>.js`, `frames/<id>*`, `out/stills/<id>`, its `.mov`). Builders never touch Resolve; one
agent places everything at the end. Render stills, check the sheet, fix, and only then render the full clip.
