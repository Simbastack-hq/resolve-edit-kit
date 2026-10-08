# Text-behind-subject composite: footage + text layer (alpha) + person (footage x matte) -> opaque ProRes clip.
# usage: python3 roto/comp.py <id>   (frames/<id>_foot from foot.py, frames/<id> from render.mjs, frames/<id>_matte from personmatte.swift)
import os, sys, glob, subprocess
from PIL import Image, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kit import GFX
gid = sys.argv[1]
F, T, Mt = [os.path.join(ROOT, 'frames', x) for x in (gid + '_foot', gid, gid + '_matte')]
out = os.path.join(ROOT, 'frames', gid + '_comp'); os.makedirs(out, exist_ok=True)
n = len(glob.glob(F + '/*.jpg'))
for i in range(1, n + 1):
    fr = Image.open(f'{F}/{i:05d}.jpg').convert('RGBA')
    tx = Image.open(f'{T}/{i:05d}.png').convert('RGBA') if os.path.exists(f'{T}/{i:05d}.png') else None
    m = Image.open(f'{Mt}/{i:05d}.png').convert('L').filter(ImageFilter.GaussianBlur(1.2))
    comp = fr.copy()
    if tx: comp.alpha_composite(tx)
    person = fr.copy(); person.putalpha(m)
    comp.alpha_composite(person)
    comp.convert('RGB').save(f'{out}/{i:05d}.jpg', quality=95)
os.makedirs(GFX, exist_ok=True); dst = os.path.join(GFX, gid + '.mov')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '30000/1001', '-i', f'{out}/%05d.jpg', '-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le', '-vendor', 'apl0', dst], check=True)
print('ok', n, dst)
