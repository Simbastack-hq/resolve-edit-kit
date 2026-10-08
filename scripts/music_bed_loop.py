"""Music bed that loops a song musically: beat-tracked, jumping back by the song's own repeat lag so the
chords and the beat stay in phase across every seam. On the song it was built for, the seams were inaudible.

What it does:
1. Beat-tracks the song (spectral-flux onsets + dynamic programming, numpy only).
2. Finds the lag at which the song repeats its progression (chroma similarity, beat-aligned), and the seam
   (a beat late in the song) whose surroundings best match the spot one lag earlier.
3. Plans the passes backwards so the song's own ending lands on the last frame, starts the bed on a beat at
   --start (the cut after the hook), and joins passes with a short equal-power crossfade.
4. Bakes the level in (--gain-db, or --voice + --under to sit N dB under a voice mix), lifts named spans.

Put the WAV on its own "MUSIC" track at frame 0 with clip volume 0 dB. About 20 dB under the voice is a good start.

usage: python3 music_bed_loop.py SONG.mp3 OUT.wav --frames 17928 --start 13.91 \
         [--voice voice_mix.wav --under 20 | --gain-db -25] [--lift 543.6:571.8] [--lift-db 2]
Check the printout: lag/seam similarity should clearly beat the baseline (0.94 vs ~0.80 on the song it was built for).
"""
import argparse, subprocess, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--frames', type=int, required=True); ap.add_argument('--fps', type=float, default=30000 / 1001)
ap.add_argument('--start', type=float, required=True, help='timeline seconds where the music comes in')
ap.add_argument('--gain-db', type=float, default=None); ap.add_argument('--voice'); ap.add_argument('--under', type=float, default=20.0)
ap.add_argument('--lift', action='append', default=[]); ap.add_argument('--lift-db', type=float, default=2.0)
ap.add_argument('--xfade', type=float, default=1.2); ap.add_argument('--fade-in', type=float, default=1.2)
a = ap.parse_args()
SR = 48000
dec = lambda p, ch: np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'],
                                                 capture_output=True, check=True).stdout, dtype=np.float32)
x = dec(a.src, 2).reshape(-1, 2); m = x.mean(1); END = len(m) / SR
T = a.frames / a.fps

def lufs(p):
    out = subprocess.run(['ffmpeg', '-nostats', '-i', p, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(out.split('Summary:')[1].split('I:')[1].split('LUFS')[0])

# 1. beats
hop, n = 512, 2048; fr = SR / hop
F = np.lib.stride_tricks.sliding_window_view(m, n)[::hop] * np.hanning(n)
S = np.log1p(100 * np.abs(np.fft.rfft(F, axis=1)))
o = np.maximum(0, np.diff(S, axis=0)).sum(1); o -= np.convolve(o, np.ones(43) / 43, 'same'); o = np.maximum(o, 0)
ac = np.correlate(o, o, 'full')[len(o) - 1:]; lag = np.arange(len(ac)) / fr
P = np.argmax(ac * ((lag > 60 / 200) & (lag < 60 / 60)))          # beat period in frames (60-200 bpm)
o = o / (o.std() + 1e-9); N = len(o); sc = o.copy(); back = -np.ones(N, int)
for t in range(N):
    lo, hi = max(int(t - 2 * P), 0), int(t - P / 2)
    if hi <= lo: continue
    prev = np.arange(lo, hi); c = sc[prev] - 100 * np.log((t - prev) / P) ** 2; j = np.argmax(c); sc[t] = o[t] + c[j]; back[t] = prev[j]
t = int(np.argmax(sc[-int(2 * P):])) + N - int(2 * P); beats = []
while t >= 0: beats.append(t); t = back[t]
beats = np.array(beats[::-1]) / fr + n / 2 / SR
period = float(np.median(np.diff(beats)))

# 2. repeat lag + seam (chroma + timbre, 4 s before / 3 s after)
n2, h2 = 4096, 2048
F2 = np.lib.stride_tricks.sliding_window_view(m, n2)[::h2] * np.hanning(n2); S2 = np.abs(np.fft.rfft(F2, axis=1)); f = np.fft.rfftfreq(n2, 1 / SR)
ed = np.geomspace(120, 12000, 32); B = np.log1p(50 * np.stack([S2[:, (f >= p) & (f < q)].mean(1) for p, q in zip(ed[:-1], ed[1:])], 1))
k = (f > 80) & (f < 5000); pc = (np.round(12 * np.log2(f[k] / 440)) % 12).astype(int)
C = np.stack([S2[:, k][:, pc == i].sum(1) for i in range(12)], 1); C /= C.sum(1, keepdims=True) + 1e-9
tB = (np.arange(len(B)) * h2 + n2 / 2) / SR
feat = lambda t0, t1: np.concatenate([B[(tB >= t0) & (tB < t1)].ravel(), 3 * C[(tB >= t0) & (tB < t1)].ravel()])
def sim(p, q):
    L = min(len(p), len(q)); p = p[:L] - p[:L].mean(); q = q[:L] - q[:L].mean(); return float(p @ q / (np.linalg.norm(p) * np.linalg.norm(q) + 1e-9))
# global repeat lag: mean chroma similarity between t and t-L over the whole overlap (local windows alone
# are not selective; on the test song this found a 117.07 s lag at 0.94 vs ~0.80 for other lags)
Cs = np.stack([np.convolve(C[:, i], np.ones(24) / 24, 'same') for i in range(12)], 1)   # ~1 s smoothing
Cs /= np.linalg.norm(Cs, axis=1, keepdims=True) + 1e-9
fps2 = SR / h2; lags = np.arange(int(20 * fps2), len(Cs) - int(30 * fps2))
score = np.array([(Cs[L:] * Cs[:-L]).sum(1).mean() for L in lags])
L0 = lags[np.argmax(score)] / fps2; base = float(np.median(score)); best = float(score.max())
# seam: a beat late in the song (before the outro) whose 7 s window matches the window one lag earlier
late = beats[(beats > L0 + 3) & (beats < END - 6)]
E = max(late, key=lambda E: sim(feat(E - 4, E + 3), feat(E - L0 - 4, E - L0 + 3)))
S0 = E - L0; LAG = L0
# refine the lag to the sample with waveform cross-correlation around the seam (aligns transients)
w = m[int((E - 1.5) * SR):int((E + 1.5) * SR)]; i0 = int((S0 - 1.5) * SR)
d = max(range(-1200, 1201, 4), key=lambda d: float(w @ m[i0 + d:i0 + d + len(w)]))
LAG -= d / SR
print(f'bpm {60 / period:.1f} | seam {E:.2f}s -> {E - LAG:.2f}s (lag {LAG:.3f}s), similarity {best:.3f} vs median {base:.3f}')

# 3. passes, planned backwards so the song's ending lands at T
D = T - a.start                                     # seconds of music needed
k = max(0, int(np.ceil((D - END) / LAG)))           # number of jumps; then 0 <= st < LAG < E
st = float(beats[beats >= END + k * LAG - D][0])    # begin on a beat
passes = [(st, END)] if k == 0 else [(st, E)] + [(E - LAG, E)] * (k - 1) + [(E - LAG, END)]
out = np.zeros((int(round(T * SR)), 2), np.float32)
pos = int(round(a.start * SR)); h = int(a.xfade / 2 * SR); fade = np.linspace(0, np.pi / 2, 2 * h); seams = []
for i, (s, e) in enumerate(passes):
    seg = x[int(s * SR) - (h if i else 0): int(e * SR) + (h if i < len(passes) - 1 else 0)].copy()
    if i: seg[:2 * h] *= np.sin(fade)[:, None]
    if i < len(passes) - 1: seg[-2 * h:] *= np.cos(fade)[:, None]
    p = pos - (h if i else 0); L = min(len(seg), len(out) - p); out[p:p + L] += seg[:L]; pos = p + len(seg) - h
    if i < len(passes) - 1: seams.append(round(pos / SR, 2))

# 4. level + envelope
if a.gain_db is None:
    if not a.voice: raise SystemExit('give --gain-db or --voice')
    a.gain_db = (lufs(a.voice) - a.under) - lufs(a.src)
tt = np.arange(len(out)) / SR
env = np.clip((tt - a.start) / a.fade_in, 0, 1) * np.clip((T - tt) / 1.0, 0, 1)
lift = np.zeros_like(tt)
for sp in a.lift:
    s, e = map(float, sp.split(':')); lift = np.maximum(lift, np.clip((tt - s) / 1.5, 0, 1) * np.clip((e - tt) / 1.5, 0, 1))
out *= (env * 10 ** ((a.gain_db + a.lift_db * lift) / 20))[:, None].astype(np.float32)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_s24le', a.out], input=out.tobytes(), check=True)
print(f'wrote {a.out}: {T:.2f}s, starts at song {st:.2f}s, {k} jumps, seams at {seams}, gain {a.gain_db:.1f} dB')
print('check: ffmpeg -ss <start+2> -i OUT -af ebur128 -f null - ; then listen to each seam')
