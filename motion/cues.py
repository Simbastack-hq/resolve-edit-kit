"""Time graphics to the words, never to hard-coded seconds.
  find("a phrase from the transcript", after=0, end=False) -> timeline seconds of that phrase (cues/tlwords.json, see tlwords.py)
  write(id, start, dur, {"pop": find(...), ...}) -> cues/<id>.js with DUR, CUES (relative to start) and G, loaded by the page
usage: python3 cues.py "a phrase" [after_seconds]   prints where the phrase is"""
import json, re, sys, os
ROOT = os.path.dirname(os.path.abspath(__file__))
TW = json.load(open(os.path.join(ROOT, 'cues', 'tlwords.json')))
def norm(s): return re.sub(r"[^a-z0-9$]", '', s.lower())
NW = [norm(w['w']) for w in TW]
def find(phrase, after=0.0, end=False):
    ws = [norm(x) for x in phrase.split()]
    for i in range(len(TW)):
        if TW[i]['t'] < after: continue
        if NW[i:i+len(ws)] == ws:
            return TW[i+len(ws)-1]['te'] if end else TW[i]['t']
    raise KeyError(f'{phrase!r} after {after}')
def words_between(a, b):
    return [{'t': w['t'], 'te': w['te'], 'w': w['w']} for w in TW if a <= w['t'] < b]
def write(gid, start, dur, cues, extra=None):
    rel = {k: round(v - start, 3) if isinstance(v, (int, float)) else v for k, v in cues.items()}
    d = {'start': round(start, 3), 'dur': round(dur, 3), 'cues': rel}
    if extra: d.update(extra)
    open(os.path.join(ROOT, 'cues', gid + '.js'), 'w').write(f'window.DUR={round(dur,3)};window.CUES={json.dumps(rel)};window.G={json.dumps(d)};\n')
    return d
if __name__ == '__main__':
    after = float(sys.argv[2]) if len(sys.argv) > 2 else 0
    t = find(sys.argv[1], after); print(f'{int(t//60)}:{t%60:05.2f}  ({t:.2f}s)')
