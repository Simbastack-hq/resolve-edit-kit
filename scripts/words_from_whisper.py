"""Word-level transcripts for every clip, in frames: the input for the paper edit.

Runs Whisper (mlx-whisper on Apple silicon if installed, else openai-whisper) on each clip's audio and writes
words.json:  { "<clip file name>": { "fps": 29.97, "frames": N, "words": [ {"t": "word", "s": frame, "e": frame}, ... ] } }

Why Whisper and not Resolve's own transcription: Resolve's word timings were often 0.2-0.4 s late and merged
restarts ("everyone... every one" came back as one word). Use them to read, never to place cuts.

usage: python3 words_from_whisper.py FOOTAGE_DIR words.json [clip1.mp4 clip2.mp4 ...] [--prompt "Names, Brands"]
       (no clip names = every video file in FOOTAGE_DIR)
"""
import argparse, json, os, shutil, subprocess, tempfile

VIDEO = ('.mp4', '.mov', '.mxf', '.mkv', '.m4v')
ap = argparse.ArgumentParser()
ap.add_argument('footage'); ap.add_argument('out'); ap.add_argument('clips', nargs='*')
ap.add_argument('--prompt', default='', help='initial prompt with names Whisper should spell right')
ap.add_argument('--model', default='mlx-community/whisper-large-v3-turbo')
ap.add_argument('--language', default='en')
a = ap.parse_args()

def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate,nb_frames:format=duration',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    d = json.loads(out); n, den = d['streams'][0]['r_frame_rate'].split('/')
    fps = float(n) / float(den)
    return fps, int(round(float(d['format']['duration']) * fps))

def whisper(wav, outdir):
    mlx = shutil.which('mlx_whisper')
    if mlx:
        cmd = [mlx, wav, '--model', a.model, '--language', a.language, '--word-timestamps', 'True', '--output-format', 'json', '--output-dir', outdir]
    elif shutil.which('whisper'):
        cmd = ['whisper', wav, '--model', 'large-v3', '--language', a.language, '--word_timestamps', 'True', '--output_format', 'json', '--output_dir', outdir]
    else:
        raise SystemExit('install mlx-whisper (Apple silicon) or openai-whisper first')
    if a.prompt: cmd += ['--initial-prompt' if mlx else '--initial_prompt', a.prompt]
    subprocess.run(cmd, check=True, capture_output=True)
    return json.load(open(os.path.join(outdir, os.path.splitext(os.path.basename(wav))[0] + '.json')))

clips = a.clips or sorted(f for f in os.listdir(a.footage) if f.lower().endswith(VIDEO))
out = json.load(open(a.out)) if os.path.exists(a.out) else {}
tmp = tempfile.mkdtemp()
for c in clips:
    path = os.path.join(a.footage, c); fps, frames = probe(path)
    wav = os.path.join(tmp, os.path.splitext(c)[0] + '.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-map', '0:a:0', '-ac', '1', '-ar', '16000', wav], check=True)
    d = whisper(wav, tmp)
    words = [{'t': w['word'].strip(), 's': round(w['start'] * fps), 'e': round(w['end'] * fps)}
             for s in d['segments'] for w in s.get('words', []) if w['word'].strip()]
    out[c] = {'fps': round(fps, 3), 'frames': frames, 'words': words}
    print(f'{c}: {len(words)} words, {frames} frames')
json.dump(out, open(a.out, 'w'), indent=0)
