"""Photo or screenshot -> H.264 clip with eased, keyframed camera moves (pans, push-ins, pull-backs).
Resolve stills cap at 150 frames and ignore endFrame, so render moving images to video and place those.
usage: python3 kenburns.py jobs.json IMAGE_DIR [name ...]   -> IMAGE_DIR/<name>-move.mp4
"""
import json, math, os, subprocess, sys
from PIL import Image
from multiprocessing import Pool
W, H = 3840, 2160
def ease(t): return 0.5 - 0.5 * math.cos(math.pi * t)
# jobs.json: {"photo-name": [frames, [[frame, cx, cy, zoom], ...]]}  cx/cy in px of the 3840x2160 canvas, zoom 1 = whole
# frame. The photo is first fitted to 16:9 (letterboxed onto black if needed): pre-compose it the way you want it.
# Time the keyframes to the words (a phrase's timeline frame from the transcript), not to round numbers. A 6%
# push-in is invisible; real moves (into a number as it's said, a pan, a pull-back) read.
def at(keys, f):
    for (f0, x0, y0, z0), (f1, x1, y1, z1) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            t = ease((f - f0) / (f1 - f0)) if f1 > f0 else 1
            z = math.exp(math.log(z0) + (math.log(z1) - math.log(z0)) * t)
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z
    return keys[-1][1:]
JOBS = json.load(open(sys.argv[1])); D = sys.argv[2].rstrip('/') + '/'
def load(name):
    f = next(D + name + x for x in ('.jpg', '.png', '.jpeg') if os.path.exists(D + name + x))
    im = Image.open(f).convert('RGB'); im.thumbnail((W, H), Image.LANCZOS)
    c = Image.new('RGB', (W, H)); c.paste(im, ((W - im.width) // 2, (H - im.height) // 2)); return c
def render(name):
    n, keys = JOBS[name]
    im = load(name)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-framerate', '30000/1001', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
                          '-pix_fmt', 'yuv420p', D + name + '-move.mp4'], stdin=subprocess.PIPE)
    for f in range(n):
        cx, cy, z = at(keys, f)
        w, h = W / z, H / z
        x0 = min(max(cx - w / 2, 0), W - w); y0 = min(max(cy - h / 2, 0), H - h)
        p.stdin.write(im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)).tobytes())
    p.stdin.close(); p.wait()
    return name, n
if __name__ == '__main__':
    with Pool(4) as pool:
        for r in pool.imap_unordered(render, sys.argv[3:] or JOBS): print(r, flush=True)
