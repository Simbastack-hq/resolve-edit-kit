"""Footage frames for a span of a timeline someone has already edited (so the EDL is out of date).
Read the V1 items from Resolve first: [(start, end, GetLeftOffset()), ...] in frames relative to the timeline start
(for 1.0x pieces GetLeftOffset() is the true source frame; GetSourceStartFrame() can be off by one), save them as
pieces.json, then:
usage: python3 foot_from_timeline.py <id> SOURCE_CLIP pieces.json [first_frame last_frame_exclusive]"""
import json, os, subprocess, sys
from kit import FPS, ROOT
gid, src, pieces = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
lo, hi = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (pieces[0][0], pieces[-1][1])
out = os.path.join(ROOT, 'frames', gid + '_foot'); os.makedirs(out, exist_ok=True); k = 1
for a, b, s in pieces:
    a2, b2 = max(a, lo), min(b, hi)
    if a2 >= b2: continue
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{(s + a2 - a - 0.25) / FPS:.5f}', '-i', src, '-frames:v', str(b2 - a2),
                    '-vf', 'scale=1920:-2', '-q:v', '2', '-start_number', str(k), os.path.join(out, '%05d.jpg')], check=True)
    k += b2 - a2
print(gid, 'frames', k - 1)
