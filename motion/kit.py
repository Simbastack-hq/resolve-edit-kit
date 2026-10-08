"""Project settings shared by the motion tools: motion/kit.json (or the file named by $KIT_CONFIG).
{
  "footage_dir": "/path/to/footage",          source clips named in the EDL
  "edl": "/path/to/edit/edl.json",            the cut the graphics are timed against
  "words": "/path/to/edit/words.json",        from scripts/words_from_whisper.py
  "gfx_out": "/path/to/edit/gfx",             where render.mjs writes .mov files (default motion/out/gfx)
  "fps": 29.97
}"""
import json, os
ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.environ.get('KIT_CONFIG', os.path.join(ROOT, 'kit.json'))))
FPS = 30000 / 1001 if abs(CFG.get('fps', 29.97) - 29.97) < 0.01 else CFG['fps']
FOOTAGE = CFG['footage_dir'].rstrip('/') + '/'
GFX = CFG.get('gfx_out') or os.path.join(ROOT, 'out', 'gfx')
_edl = None
def edl():
    global _edl
    if _edl is None: _edl = json.load(open(CFG['edl']))['main']
    return _edl
def length(p): return round((p['e'] + 1 - p['s']) / p.get('speed', 1.0))
def source_at(tl_frame):
    """Timeline frame -> (clip, source frame) for the piece playing there (None in a gap)."""
    for p in edl():
        if 'clip' in p and p['rec'] <= tl_frame < p['rec'] + length(p):
            return p['clip'], p['s'] + round((tl_frame - p['rec']) * p.get('speed', 1.0))
    return None
