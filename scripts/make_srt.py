"""Whisper JSON (word timestamps) -> YouTube SRT: <=2 lines x 42 chars, <=6 s per cue, names fixed, fillers dropped.
Transcribe the FINAL export with a names prompt first, e.g.:
  mlx_whisper final.wav --model mlx-community/whisper-large-v3-turbo --language en --word-timestamps True \
    --output-format json --initial-prompt "the names, brands and places you say"
usage: python3 make_srt.py final.json out.srt [fixes.json]   fixes.json = [["regex", "replacement"], ...] for your own names
"""
import json, re, sys
d = json.load(open(sys.argv[1]))
raw = [dict(t=w['word'].strip(), s=w['start'], e=w['end']) for s in d['segments'] for w in s.get('words', []) if w['word'].strip()]
ws = []
for w in raw:   # glue split numbers/domains: "5" ".5" -> "5.5"; "5" "-10" -> "5–10"
    if ws and re.match(r'^[.\-][0-9a-z]', w['t']) and re.search(r'[0-9a-z]$', ws[-1]['t'], re.I):
        ws[-1]['t'] += w['t'].replace('-', '–') if ws[-1]['t'][-1].isdigit() else w['t']; ws[-1]['e'] = w['e']
    else: ws.append(w)
# A few common mishearings; add your own names with a fixes.json (third argument).
FIX = [(r'\bChatGPD\b', 'ChatGPT'), (r'\bGPD\b', 'GPT'), (r'\bAnthropik\b', 'Anthropic'), (r'\b20X\b', '20x')]
if len(sys.argv) > 3: FIX += [tuple(x) for x in json.load(open(sys.argv[3]))]   # e.g. [["\\bcloud\\b", "Claude"]]
FILLER = {'um', 'uh', 'um,', 'uh,', 'Um,', 'Uh,', 'Um', 'Uh'}
ws = [w for w in ws if w['t'] not in FILLER]
def fix(t):
    for a, b in FIX: t = re.sub(a, b, t)
    return re.sub(r'\b(\w+)( \1\b)+', r'\1', t)          # "and and and" -> "and"
cues, cur = [], []
def flush():
    if cur: cues.append((cur[0]['s'], cur[-1]['e'], fix(' '.join(x['t'] for x in cur)))); cur.clear()
for w in ws:
    if cur and (len(' '.join(x['t'] for x in cur + [w])) > 84 or w['e'] - cur[0]['s'] > 6.0): flush()
    cur.append(w)
    if re.search(r'[.?!]$', w['t']) and w['e'] - cur[0]['s'] > 1.2: flush()
flush()
def wrap(t):
    if len(t) <= 42: return t
    w = t.split(); best = min(((max(len(' '.join(w[:i])), len(' '.join(w[i:]))), i) for i in range(1, len(w))))
    return ' '.join(w[:best[1]]) + '\n' + ' '.join(w[best[1]:])
def ts(x):
    h, r = divmod(x, 3600); m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"
out = []
for i, (s, e, t) in enumerate(cues, 1):
    e = max(e, s + 0.8)
    if i < len(cues): e = min(e, cues[i][0] - 0.02)
    out.append(f"{i}\n{ts(s)} --> {ts(e)}\n{wrap(t)}\n")
open(sys.argv[2], 'w').write('\n'.join(out)); print(len(cues), 'cues ->', sys.argv[2])
