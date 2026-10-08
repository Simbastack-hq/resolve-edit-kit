#!/bin/sh
# Final audio pass on a Resolve render: oversampled true-peak limiter, AAC 320k, video stream copied untouched.
# Resolve's PCM render of a typical voice + music mix sat around -15 LUFS / +0.3 dBTP. level=false matters:
# alimiter's default auto-level adds gain (it pushed one export to +0.7 dBTP).
# usage: limit_audio.sh render.mov final.mp4 [ceiling]   (ceiling default 0.79 = -2 dBFS; re-measure, AAC can overshoot)
IN="$1"; OUT="$2"; C="${3:-0.79}"
ffmpeg -v error -y -i "$IN" -map 0:v:0 -map 0:a:0 -c:v copy \
  -af "aresample=192000,alimiter=limit=$C:level=false:attack=2:release=50,aresample=48000" \
  -c:a aac -b:a 320k -movflags +faststart "$OUT" || exit 1
ffmpeg -nostats -i "$OUT" -vn -af ebur128=peak=true -f null - 2>&1 | sed -n '/Summary/,$p' | grep -E "I:|Peak:"
echo "If Peak is above -1 dBFS, run again with a lower ceiling (0.72 worked when 0.79 overshot)."
