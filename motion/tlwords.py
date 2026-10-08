"""Every kept word mapped to timeline seconds -> cues/tlwords.json, which cues.py searches by phrase.
Re-run after every re-cut, then re-render the graphics: their cues follow the words, so nothing is retimed by hand.
usage: python3 tlwords.py"""
import json, os
from kit import CFG, FPS, ROOT, edl, length
W = json.load(open(CFG['words']))
out = []
for p in edl():
    if 'clip' not in p: continue
    sp = p.get('speed', 1.0)
    for w in W[p['clip']]['words']:
        if p['s'] <= w['s'] <= p['e']:
            t = (p['rec'] + (w['s'] - p['s']) / sp) / FPS
            te = (p['rec'] + (min(w['e'], p['e']) - p['s']) / sp) / FPS
            out.append({'t': round(t, 3), 'te': round(te, 3), 'w': w['t']})
os.makedirs(os.path.join(ROOT, 'cues'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'cues', 'tlwords.json'), 'w'))
print(len(out), 'words ->', os.path.join(ROOT, 'cues', 'tlwords.json'))
