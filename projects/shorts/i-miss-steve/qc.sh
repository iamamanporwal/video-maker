#!/bin/zsh
# film-qc technical gate + evidence. usage: qc.sh out/film.mp4
cd "${0:A:h}"; f=$1; mkdir -p review/qc
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,sample_rate -show_entries format=duration -of compact "$f"
ffmpeg -nostats -i "$f" -af ebur128=peak=true -f null - 2>&1 | grep -A12 "Summary" | grep -E "I:|LRA:|Peak:"
echo "-- black"; ffmpeg -nostats -i "$f" -vf blackdetect=d=0.25:pix_th=0.06 -an -f null - 2>&1 | grep -o "black_start.*" | head
echo "-- freeze"; ffmpeg -nostats -i "$f" -vf "crop=1080:1320:0:300,freezedetect=n=0.001:d=1.5" -an -f null - 2>&1 | grep -oE "freeze_(start|end): [0-9.]+" | paste - - | head
echo "-- silence"; ffmpeg -nostats -i "$f" -af silencedetect=n=-45dB:d=1.0 -vn -f null - 2>&1 | grep -oE "silence_(start|end): [0-9.]+" | paste - - | head
ffmpeg -v error -y -i "$f" -vf "fps=1,scale=180:-1,tile=10x9" -frames:v 1 review/qc/sheet.jpg
ffmpeg -v error -y -i "$f" -filter_complex "showwavespic=s=1800x300:split_channels=0" -frames:v 1 review/qc/wave.png
