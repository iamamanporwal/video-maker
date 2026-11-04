#!/usr/bin/env bash
# Full build: VO (vo.py) -> timeline + mix (timeline.py) -> Remotion picture -> mux -> master at -14 LUFS / -1 dBTP.
#   KOKORO_DIR=/path/to/kokoro-model ./render.sh [--skip-vo | --mux-only]
# CHROME: a Chromium that trusts your network's CA (in the cloud sandbox: the full Playwright build, not headless-shell).
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"; R="$D/../../../node/remotion"
CHROME="${CHROME:-/opt/pw-browsers/chromium-1243/chrome-linux64/chrome}"
MODE="${1:-}"
if [[ "$MODE" != "--mux-only" ]]; then
[[ "$MODE" == "--skip-vo" ]] || python3 "$D/vo.py"
python3 "$D/timeline.py"
cd "$R"
npx remotion render src/shorts/index.ts WhatIfWalter "$D/out/picture.mp4" --props="$D/out/props.json" --muted \
  --browser-executable="$CHROME" --gl=swangle --concurrency=4 --codec=h264 --crf=17 --pixel-format=yuv420p --timeout=240000
fi
cd "$D/out"
ffmpeg -v error -y -i picture.mp4 -i ../public/mix.wav -map 0:v -map 1:a -vf "noise=alls=5:allf=t+u,format=yuv420p" \
  -c:v libx264 -preset slow -crf 22 -maxrate 8M -bufsize 16M -c:a pcm_s16le -shortest raw.mkv
# measured gain to -14 LUFS integrated, then a peak limiter at -1.5 dBFS (as in what-if-100/build.py)
I=$(ffmpeg -hide_banner -i raw.mkv -af acompressor=threshold=0.1:ratio=3:attack=5:release=120:makeup=1,ebur128 -f null - 2>&1 | grep -A6 Summary | grep -oE "I: +-?[0-9.]+" | grep -oE "\-?[0-9.]+$")
G=$(python3 -c "print(round(-14.0 - ($I), 2))")
ffmpeg -v error -y -i raw.mkv -c:v copy -af "acompressor=threshold=0.1:ratio=3:attack=5:release=120:makeup=1,volume=${G}dB,alimiter=limit=0.84:level=false:attack=3:release=60,aresample=48000" \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart what-if-walter.mp4
rm -f raw.mkv
echo "-> $D/out/what-if-walter.mp4"
