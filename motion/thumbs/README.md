# Thumbnails as HTML pages

Thumbnails use the same design system as the video's graphics (`../lib/base.css`), so they match the video and every
element is editable text, not baked pixels.

1. Pull 2 frames from each piece of the cut, tile contact sheets, and pick 4-6 by expression (laughing, pointing to
   the side where a card can go, close and warm). Ask the person to record 30 seconds of thumbnail faces into the lens
   at the end of a shoot, without sunglasses.
2. Cut the person out: `python3 ../../scripts/person_cutout.py frame.png img/person.png --outline 23`. The `_ol`
   version has a white ring for dark or coloured backgrounds; use the plain one on a photo background.
3. Copy `example-thumb.html`, change the words, the proof and the image. Make 3-4 genuinely different concepts
   (dark + glow, light, full colour, a real photo background), not one design in three colours.
4. `node render.mjs` writes 1920x1080 JPGs to `out/` (well under YouTube's 2 MB).
5. Look at each one at 360x202 and 168x94 before choosing. Use YouTube's Test & compare with the best 2-3.

The thumbnail and the title split the work: the thumbnail tells the story, the title makes the promise. Repeating
the title's words in the thumbnail was the weakest option every time. Real proof (a real screenshot, the real
result) beats an illustration.
