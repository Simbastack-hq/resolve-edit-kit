"""Paper edit -> EDL. You (or the agent) pick word ranges per section; this turns them into frame-accurate pieces.

Input  paper_edit.json (see examples/paper_edit.example.json):
  sections: [{"label": "Hook", "clip": "A001.mp4", "words": [[0, 21], [30, 44]]},   word-index ranges, inclusive
             {"label": "Pickup", "clip": "P001.mp4", "frames": [[45, 396]]},       hand-set source frames, inclusive
             {"label": "Breather", "gap": 90}]                                       empty frames (e.g. for a screen segment)
  fixes:    [{"clip": "A001.mp4", "s": 2537, "replace": [[2537, 2688]], "note": "drop trailing 'like'"}]
            frame-level fixes found by checking the joins: the piece that starts at frame s is replaced by these ranges
  alts:     [{"label": "ALT hook", "clip": "B002.mp4", "words": [[5, 30]], "align": "Hook"}]   runner-up takes, for A/B review
  pad_pre / pad_post (frames, default 4 / 6), split_gap (frames of silence that split a range into two pieces, default 18)
Input  words.json from words_from_whisper.py.

Output edl.json: {"fps": 29.97, "main": [{"clip", "s", "e", "label", "rec", "txt"}...], "alts": [...], "total": frames}
  s/e are inclusive source frames, rec is the record frame on the timeline. Later steps add "speed".

usage: python3 edl_builder.py paper_edit.json words.json edl.json
"""
import json, sys

P, W = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
OUT = sys.argv[3]
PRE, POST, GAP = P.get('pad_pre', 4), P.get('pad_post', 6), P.get('split_gap', 18)
FIX = {(f['clip'], f['s']): f['replace'] for f in P.get('fixes', [])}
fps = P.get('fps') or next(iter(W.values()))['fps']

def real(w): return w['t'].strip() not in ('', '(...)')

def pieces(clip, ranges):
    ws, out = W[clip]['words'], []
    for i0, i1 in ranges:
        idx = [i for i in range(i0, i1 + 1) if real(ws[i])]
        prev = [i for i in range(i0 - 1, -1, -1) if real(ws[i])]
        nxt = [i for i in range(i1 + 1, len(ws)) if real(ws[i])]
        lo = ws[prev[0]]['e'] + 1 if prev else 0                       # never reach into the neighbouring words
        hi = ws[nxt[0]]['s'] - 1 if nxt else W[clip]['frames'] - 1
        groups = [[idx[0]]]
        for x, y in zip(idx, idx[1:]):
            (groups.append([y]) if ws[y]['s'] - ws[x]['e'] > GAP else groups[-1].append(y))
        for gi, g in enumerate(groups):
            s, e = ws[g[0]]['s'] - PRE, ws[g[-1]]['e'] + POST
            if gi == 0: s = max(s, lo)
            if gi == len(groups) - 1: e = min(e, hi)
            out.append({'clip': clip, 's': max(0, s), 'e': e, 'txt': ' '.join(ws[i]['t'] for i in g)})
    return out

def apply_fixes(ps):
    out = []
    for p in ps:
        for s, e in FIX.get((p['clip'], p['s']), [(p['s'], p['e'])]):
            out.append(dict(p, s=s, e=e))
    return out

main, t = [], 0
for sec in P['sections']:
    if 'gap' in sec:
        main.append({'gap': sec['gap'], 'label': sec.get('label', 'gap'), 'rec': t}); t += sec['gap']; continue
    if 'frames' in sec:
        ps = [{'clip': sec['clip'], 's': a, 'e': b, 'txt': sec.get('txt', '')} for a, b in sec['frames']]
    else:
        ps = apply_fixes(pieces(sec['clip'], sec['words']))
    for p in ps:
        p.update(rec=t, label=sec['label']); t += p['e'] - p['s'] + 1; main.append(p)

starts = {}
for p in main: starts.setdefault(p['label'], p['rec'])
alts = []
for al in P.get('alts', []):
    r = starts[al['align']]
    for p in pieces(al['clip'], al['words']):
        p.update(rec=r, label=al['label']); r += p['e'] - p['s'] + 1; alts.append(p)

json.dump({'fps': fps, 'main': main, 'alts': alts, 'total': t}, open(OUT, 'w'), indent=0)

def tc(f): s = f / fps; return f'{int(s // 60)}:{s % 60:05.2f}'
cur = None
for p in main:
    if p['label'] != cur: cur = p['label']; print(f"\n[{tc(p['rec'])}] {cur}")
    print(f"   gap {p['gap']}f" if 'gap' in p else f"   {p['clip']} {p['s']}-{p['e']} | {p['txt'][:100]}")
print(f"\ntotal {tc(t)} ({t} frames), {sum('clip' in p for p in main)} pieces, {len(alts)} alt pieces -> {OUT}")
