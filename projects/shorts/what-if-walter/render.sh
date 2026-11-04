#!/usr/bin/env bash
# Full build: VO (vo.py) -> timeline + mix (timeline.py) -> Remotion picture -> mux -> master at -14 LUFS / -1 dBTP.
#   KOKORO_DIR=/path/to/kokoro-model ./render.sh [--skip-vo]
# CHROME: a Chromium that trusts your network's CA (in the cloud sandbox: the full Playwright build, not headless-shell).
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"; R="$D/../../../node/remotion"
CHROME="${CHROME:-/opt/pw-browsers/chromium-1243/chrome-linux64/chrome}"
[[ "${1:-}" == "--skip-vo" ]] || python3 "$D/vo.py"
python3 "$D/timeline.py"
cd "$R"
npx remotion render src/shorts/index.ts WhatIfWalter "$D/out/picture.mp4" --props="$D/out/props.json" --muted \
  --browser-executable="$CHROME" --gl=swangle --concurrency=4 --codec=h264 --crf=17 --pixel-format=yuv420p --timeout=240000
cd "$D/out"
ffmpeg -v error -y -i picture.mp4 -i ../public/mix.wav -map 0:v -map 1:a -c:v copy -c:a pcm_s16le -shortest raw.mkv
# two-pass loudnorm to -14 LUFS integrated, -1.5 dBTP
J=$(ffmpeg -hide_banner -i raw.mkv -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$J" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
ffmpeg -v error -y -i raw.mkv -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000" \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart what-if-walter.mp4
rm -f raw.mkv
echo "-> $D/out/what-if-walter.mp4"
