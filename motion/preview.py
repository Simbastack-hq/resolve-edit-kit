"""Composite a graphic's stills over the real footage at that moment and tile them: out/sheet_<id>.jpg.
Render stills first (node render.mjs <id> --stills 0.5,1.2,...). Always look at the sheet: it's how you catch a
card sitting on someone's face. Opaque scenes are shown as they are.
usage: python3 preview.py <id> [cols]"""
import glob, json, os, re, subprocess, sys
from PIL import Image
from kit import FOOTAGE, FPS, ROOT, source_at
def frame(t):
    hit = source_at(round(t * FPS))
    if not hit: return Image.new('RGBA', (1920, 1080), 'black')
    clip, f = hit; out = os.path.join(ROOT, 'out', 'bg', f'{clip}_{f}.jpg'); os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.exists(out):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{(f - 0.25) / FPS:.5f}', '-i', FOOTAGE + clip, '-frames:v', '1',
                        '-vf', 'scale=1920:1080', '-q:v', '3', out], check=True)
    return Image.open(out).convert('RGBA')
def sheet(gid, cols=4, w=640):
    cf = os.path.join(ROOT, 'cues', gid + '.js'); g = re.search(r'window\.G=(\{.*\});', open(cf).read()) if os.path.exists(cf) else None
    start = json.loads(g.group(1))['start'] if g else 0
    files = sorted(glob.glob(os.path.join(ROOT, 'out', 'stills', gid, '*.png')), key=lambda f: float(f.rsplit('_', 1)[1][:-4]))
    tiles = []
    for f in files:
        im = Image.open(f).convert('RGBA'); rel = float(f.rsplit('_', 1)[1][:-4])
        bg = frame(start + rel) if im.getchannel('A').getextrema()[0] < 255 else Image.new('RGBA', im.size)
        bg.alpha_composite(im.resize(bg.size)); tiles.append(bg.convert('RGB').resize((w, w * 9 // 16)))
    rows = (len(tiles) + cols - 1) // cols; W = Image.new('RGB', (cols * w, rows * w * 9 // 16), 'black')
    for i, t in enumerate(tiles): W.paste(t, ((i % cols) * w, (i // cols) * w * 9 // 16))
    out = os.path.join(ROOT, 'out', f'sheet_{gid}.jpg'); W.save(out, quality=85); print(out)
if __name__ == '__main__': sheet(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4)
