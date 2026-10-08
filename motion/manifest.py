"""List the rendered graphics with their start frame (from each page's cues file) -> out/manifest.json, which
resolve_kit.place_graphics() reads. Opaque files (ProRes 422) are scenes; files with alpha (4444) are overlays.
usage: python3 manifest.py"""
import glob, json, os, re, subprocess
from kit import FPS, GFX, ROOT
def probe(f):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=pix_fmt,nb_read_packets',
                        '-of', 'json', f], capture_output=True, text=True)
    s = json.loads(r.stdout)['streams'][0]; return s['pix_fmt'], int(s['nb_read_packets'])
out = []
for f in sorted(glob.glob(os.path.join(GFX, '*.mov'))):
    gid = os.path.basename(f)[:-4]; cf = os.path.join(ROOT, 'cues', gid + '.js')
    if not os.path.exists(cf): print('no cues for', gid, '(skipped)'); continue
    G = json.loads(re.search(r'window\.G=(\{.*\});', open(cf).read()).group(1))
    pf, n = probe(f)
    out.append({'id': gid, 'file': f, 'start': round(G['start'] * FPS), 'n': n, 'opaque': 'yuva' not in pf})
os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'out', 'manifest.json'), 'w'), indent=1)
for x in out: print(f"{x['id']:24s} {x['start'] / FPS:8.2f}s  {x['n'] / FPS:5.1f}s  {'scene' if x['opaque'] else 'overlay'}")
