"""Hear the cut the way Resolve will play it: concatenate the EDL pieces (atempo for sped pieces) and transcribe the
result with Whisper, then read it. This catches restarts the transcript hid, clipped words and stray fragments at
joins. If Whisper shows an odd connective ("so") at a join, transcribe both sides on their own before trusting it:
Whisper invents them at splices.

usage: python3 check_joins.py edl.json FOOTAGE_DIR ["Section label" ...]   (no labels = the whole EDL)
"""
import json, os, shutil, subprocess, sys, tempfile

E = json.load(open(sys.argv[1])); src = sys.argv[2].rstrip('/') + '/'
labels = set(sys.argv[3:]); fps = E['fps']; tmp = tempfile.mkdtemp(); lst = []
for i, p in enumerate(q for q in E['main'] if 'clip' in q and (not labels or q.get('label') in labels)):
    af = ['-af', f"atempo={p['speed']}"] if p.get('speed') else []
    out = f'{tmp}/{i:04d}.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{p['s'] / fps:.4f}", '-i', src + p['clip'], '-t', f"{(p['e'] + 1 - p['s']) / fps:.4f}",
                    '-map', '0:a:0', '-ac', '1', '-ar', '16000'] + af + [out], check=True)
    lst.append(f"file '{out}'")
open(f'{tmp}/list.txt', 'w').write('\n'.join(lst))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{tmp}/list.txt', '-c', 'copy', f'{tmp}/cut.wav'], check=True)
mlx = shutil.which('mlx_whisper')
cmd = ([mlx, f'{tmp}/cut.wav', '--model', 'mlx-community/whisper-large-v3-turbo', '--condition-on-previous-text', 'False',
        '--output-format', 'txt', '--output-dir', tmp] if mlx else
       ['whisper', f'{tmp}/cut.wav', '--model', 'large-v3', '--condition_on_previous_text', 'False', '--output_format', 'txt', '--output_dir', tmp])
subprocess.run(cmd + ['--language', 'en'], capture_output=True, check=True)
print(open(f'{tmp}/cut.txt').read())
