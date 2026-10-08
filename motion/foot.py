"""Footage frames for a timeline span, exactly as the cut plays them, for picture-in-picture scenes.
Writes frames/<id>_foot/00001.jpg ... A page shows them with: window.FOOT = {dir: '../frames/<id>_foot', n: <frames>}
and `await setFoot(img, t)` in render(). Because the scene's frames match the cut, it can sit on a track above the
footage and hand back to it without a jump; start and end scenes on existing cuts so any small difference hides.
usage: python3 foot.py <id> <start seconds> <duration seconds>"""
import os, subprocess, sys
from kit import FOOTAGE, FPS, ROOT, edl, length
def extract(gid, start, dur, width=1920):
    f0, n = round(start * FPS), round(dur * FPS)
    out = os.path.join(ROOT, 'frames', gid + '_foot'); os.makedirs(out, exist_ok=True); k = 1
    for p in edl():
        if 'clip' not in p: continue
        a, b = max(f0, p['rec']), min(f0 + n, p['rec'] + length(p))
        if a >= b: continue
        sp = p.get('speed', 1.0); t0 = (p['s'] + (a - p['rec']) * sp - 0.25) / FPS   # ffmpeg -ss gives the first frame with pts >= t
        vf = f'setpts=(PTS-STARTPTS)/{sp},fps=30000/1001,scale={width}:-2' if sp != 1.0 else f'scale={width}:-2'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.5f}', '-i', FOOTAGE + p['clip'], '-frames:v', str(b - a), '-vf', vf,
                        '-q:v', '2', '-start_number', str(k), os.path.join(out, '%05d.jpg')], check=True)
        k += b - a
    print(gid, 'frames', k - 1, 'of', n); return k - 1
if __name__ == '__main__': extract(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))
