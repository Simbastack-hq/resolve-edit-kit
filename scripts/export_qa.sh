#!/bin/sh
# QA the rendered file itself (not the timeline): format, bitrate, loudness, full transcript with timestamps (-> chapters), frames.
# usage: export_qa.sh /path/to/final.mp4 /tmp/qa_dir
F="$1"; D="${2:-/tmp/video_qa}"; mkdir -p "$D"
ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_name,width,height,r_frame_rate -of compact "$F"
ffmpeg -hide_banner -i "$F" -map 0:a:0 -af loudnorm=print_format=summary -f null - 2>&1 | grep -E "Input Integrated|Input True Peak"
ffmpeg -v error -y -i "$F" -map 0:a:0 -ac 1 -ar 16000 "$D/final.wav"
if command -v mlx_whisper >/dev/null; then mlx_whisper "$D/final.wav" --model mlx-community/whisper-large-v3-turbo --language en --word-timestamps True --output-format json --output-dir "$D" >/dev/null 2>&1
else whisper "$D/final.wav" --model large-v3 --language en --word_timestamps True --output_format json --output_dir "$D" >/dev/null 2>&1; fi
python3 -c "
import json; d=json.load(open('$D/final.json'))
for s in d['segments']: print(f\"{int(s['start']//60)}:{s['start']%60:04.1f} {s['text'].strip()}\")"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$F"); n=9
for i in $(seq 1 $n); do t=$(python3 -c "print(round($dur*($i-0.5)/$n,1))"); ffmpeg -v error -y -ss $t -i "$F" -frames:v 1 -vf scale=640:-1 "$D/frame_$(printf %02d $i).jpg"; done
echo "frames in $D (tile them and look)"
