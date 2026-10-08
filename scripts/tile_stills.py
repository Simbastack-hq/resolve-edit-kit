"""Tile exported stills into one contact sheet you can look at in one go.
usage: python3 tile_stills.py STILLS_DIR TAG [cols]   -> STILLS_DIR/TAG_grid.jpg (files named TAG_<seconds>.png)"""
import os, sys
from PIL import Image
d, tag = sys.argv[1], sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
fs = sorted((f for f in os.listdir(d) if f.startswith(tag + '_') and f.endswith('.png')), key=lambda f: float(f[len(tag) + 1:-4]))
ims = [Image.open(os.path.join(d, f)).convert('RGB').resize((640, 360)) for f in fs]
rows = (len(ims) + cols - 1) // cols; W = Image.new('RGB', (cols * 640, rows * 360))
for i, im in enumerate(ims): W.paste(im, ((i % cols) * 640, (i // cols) * 360))
out = os.path.join(d, f'{tag}_grid.jpg'); W.save(out, quality=85); print(out, len(ims))
