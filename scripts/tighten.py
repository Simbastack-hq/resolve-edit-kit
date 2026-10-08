"""Tighten an EDL: cut the real pauses (found in the audio, not the transcript) and level the pace per section.

- Every silence longer than --max-pause (default 0.35 s, detected with ffmpeg silencedetect at --noise dB) inside a
  piece is cut down to about 2 x --keep (default 0.125 s each side, so ~0.25 s remains).
- --speeds '{"Hook": 1.05, "Setup": 1.08}' plays whole sections faster, with pitch correction in Resolve. Keep it at
  1.10 or below; measure words per minute per section (printed below) instead of guessing. Speeding the whole video
  is rarely right: fix the slow stretches.
- --protect "Label A,Label B" leaves sections untouched (e.g. ones with graphics timed to the speech).
- --strict "Label" cuts pauses harder there (0.28 s max, 0.10 s kept).

usage: python3 tighten.py edl.json edl_tight.json --footage FOOTAGE_DIR [--speeds JSON] [--protect A,B] [--strict C]
"""
import argparse, json, re, subprocess
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument('edl'); ap.add_argument('out'); ap.add_argument('--footage', required=True)
ap.add_argument('--max-pause', type=float, default=0.35); ap.add_argument('--keep', type=float, default=0.125)
ap.add_argument('--noise', default='-30dB'); ap.add_argument('--min-silence', type=float, default=0.2)
ap.add_argument('--speeds', default='{}'); ap.add_argument('--protect', default=''); ap.add_argument('--strict', default='')
a = ap.parse_args()
E = json.load(open(a.edl)); fps = E['fps']
SPEED = json.loads(a.speeds); PROTECT = set(filter(None, a.protect.split(','))); STRICT = set(filter(None, a.strict.split(',')))
src = a.footage.rstrip('/') + '/'
ORIG = list(E['main'])

def dur_of(q): return round((q['e'] + 1 - q['s']) / q.get('speed', 1.0))

out, removed, t = [], 0.0, 0
for p in E['main']:
    if 'clip' not in p or p.get('label') in PROTECT:
        q = dict(p, rec=t); t += q['gap'] if 'gap' in q else dur_of(q); out.append(q); continue
    t0, dur = p['s'] / fps, (p['e'] + 1 - p['s']) / fps
    log = subprocess.run(['ffmpeg', '-hide_banner', '-ss', f'{t0:.4f}', '-t', f'{dur:.4f}', '-i', src + p['clip'], '-map', '0:a:0',
                          '-af', f'silencedetect=noise={a.noise}:d={a.min_silence}', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr.replace('\n', ' ')
    maxp, keep = (0.28, 0.10) if p.get('label') in STRICT else (a.max_pause, a.keep)
    cuts = []
    for s0, s1 in re.findall(r'silence_start: ([\d.]+).*?silence_end: ([\d.]+)', log):
        s0, s1 = float(s0), float(s1)
        if s1 - s0 > maxp and s0 > 0.05 and s1 < dur - 0.05:          # interior pauses only
            cuts.append((p['s'] + round((s0 + keep) * fps), p['s'] + round((s1 - keep) * fps) - 1))
    segs, cur = [], p['s']
    for c0, c1 in cuts:
        if c1 >= c0: segs.append((cur, c0 - 1)); cur = c1 + 1; removed += (c1 - c0 + 1) / fps
    segs.append((cur, p['e']))
    for s, e in segs:
        if e - s < 3: continue
        q = dict(p, s=s, e=e, rec=t)
        if p.get('label') in SPEED: q['speed'] = SPEED[p['label']]
        t += dur_of(q); out.append(q)

E['main'], E['total'] = out, t
json.dump(E, open(a.out, 'w'), indent=0)
wpm = defaultdict(lambda: [0, 0])
for q in out:
    if 'clip' in q: wpm[q['label']][1] += dur_of(q)
for p in ORIG:
    if 'clip' in p: wpm[p['label']][0] += len(p.get('txt', '').split())
print('words per minute by section (aim for roughly 195-230 for a talking head):')
for lab, (w, f) in wpm.items():
    if f: print(f'  {lab:<30} {w / (f / fps / 60):6.0f}')
print(f'pieces {len(out)}, removed {removed:.1f}s of pauses, runtime {int(t / fps // 60)}:{t / fps % 60:04.1f} -> {a.out}')
