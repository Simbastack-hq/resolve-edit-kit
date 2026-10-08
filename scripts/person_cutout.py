"""Clean person cut-out from a 4K frame for thumbnails (macOS, Apple Vision).

Apple Vision's subject lift (cutout.swift) keeps sharp hair edges but also grabs whatever touches the person (a
cushion they lean on), and the person matte (motion/roto/personmatte.swift) often counts that object as the person too.
This combines them:
  alpha = subject-lift alpha  x  dilated person matte  x  (not --key-hue)  x  the region connected to the face
The flood fill from the face drops anything not attached to the person; --open removes thin slivers that survive.
Check the result on a grey background; if a sliver remains, --clear x0:x1:y0:y1 (fractions of the crop) wipes it.

usage: python3 person_cutout.py frame.png out.png [--key-hue 95:202] [--open 9] [--clear 0:.055:.40:.72] [--outline 23]
  writes out.png (cropped RGBA) and, with --outline, out_ol.png with a white ring for dark/coloured backgrounds.
"""
import argparse, os, subprocess, tempfile, numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument('frame'); ap.add_argument('out')
ap.add_argument('--key-hue', default='', help="hue range (deg) to drop, e.g. 95:202 for a teal cushion behind the person; empty = off")
ap.add_argument('--open', type=int, default=9, help='opening size at 1/4 scale (removes slivers ~4x this wide)')
ap.add_argument('--clear', action='append', default=[]); ap.add_argument('--outline', type=int, default=0)
a = ap.parse_args()
tmp = tempfile.mkdtemp()
def tool(src, name):
    exe = os.path.join(tmp, name); subprocess.run(['swiftc', '-O', src, '-o', exe], check=True, capture_output=True); return exe
cut_exe = tool(os.path.join(HERE, 'cutout.swift'), 'cutout')
pm_exe = tool(os.path.join(HERE, '..', 'motion', 'roto', 'personmatte.swift'), 'personmatte')
os.makedirs(f'{tmp}/in'); Image.open(a.frame).convert('RGB').save(f'{tmp}/in/f.jpg', quality=95)
subprocess.run([cut_exe, a.frame, f'{tmp}/cut.png'], check=True, capture_output=True)
subprocess.run([pm_exe, f'{tmp}/in', f'{tmp}/pm'], check=True, capture_output=True)
cut = Image.open(f'{tmp}/cut.png').convert('RGBA'); A = np.array(cut.getchannel('A')).astype(np.float32)
pm = Image.open(f'{tmp}/pm/f.png').convert('L').resize(cut.size).point(lambda v: 255 if v > 90 else 0).filter(ImageFilter.MaxFilter(15))
keep = (A > 100) & (np.array(pm) > 0)
if a.key_hue:
    lo, hi = map(float, a.key_hue.split(':'))
    hsv = np.array(Image.open(a.frame).convert('RGB').convert('HSV')).astype(np.float32)
    H, S, V = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
    keep &= ~(((H > lo) & (H < hi) & (S > 0.05)) | ((V < 0.18) & (H > lo - 5) & (H < hi + 8)))
q = (cut.width // 4, cut.height // 4)
m = Image.fromarray((keep * 255).astype(np.uint8)).resize(q, Image.BILINEAR).point(lambda v: 255 if v > 127 else 0)
m = m.filter(ImageFilter.MinFilter(a.open)).filter(ImageFilter.MaxFilter(a.open))
arr = np.array(m); ys = np.nonzero(arr.any(1))[0]; sy = ys[0] + 30; row = np.nonzero(arr[sy] > 0)[0]
ImageDraw.floodfill(m, (int(row.mean()), int(sy)), 128)                     # seed just below the top of the head
comp = Image.fromarray(((np.array(m) == 128) * 255).astype(np.uint8)).resize(cut.size, Image.BILINEAR)
comp = comp.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(3))
cut.putalpha(Image.fromarray((A * np.array(comp) / 255).astype(np.uint8)))
cut = cut.crop(cut.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox())
if a.clear:
    al = np.array(cut.getchannel('A')); h, w = al.shape
    for c in a.clear:
        x0, x1, y0, y1 = map(float, c.split(':')); al[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 0
    cut.putalpha(Image.fromarray(al)); cut = cut.crop(cut.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox())
cut.save(a.out)
if a.outline:
    pad = a.outline * 2; base = Image.new('RGBA', (cut.width + 2 * pad, cut.height + pad), (0, 0, 0, 0)); base.alpha_composite(cut, (pad, pad))
    ring = base.getchannel('A').filter(ImageFilter.MaxFilter(a.outline | 1)).filter(ImageFilter.GaussianBlur(1.5))
    ol = Image.new('RGBA', base.size, (255, 255, 255, 0)); ol.putalpha(ring); ol.alpha_composite(base)
    ol.save(a.out.replace('.png', '_ol.png'))
print('wrote', a.out, cut.size)
