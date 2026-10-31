#!/bin/zsh
# Render a 360-frame turntable for each Vi3W model, encode to turntable.mp4 (12 s) and a CTA copy starting at 4 s.
cd "$(dirname $0)"
for d in 0*/; do d=${d%/}; mkdir -p /tmp/tt-$d
  /Applications/Blender.app/Contents/MacOS/Blender -b -P ../../../src/reelforge/blender/turntable.py -- $PWD/$d/assets/model.glb /tmp/tt-$d 360 > /tmp/tt-$d.log 2>&1
  ffmpeg -v error -y -framerate 30 -i /tmp/tt-$d/t_%04d.png -c:v libx264 -crf 16 -pix_fmt yuv420p $d/assets/turntable.mp4
  ffmpeg -v error -y -ss 4 -i $d/assets/turntable.mp4 -c:v libx264 -crf 16 -pix_fmt yuv420p $d/assets/turntable-cta.mp4
  echo "done $d $(ls /tmp/tt-$d | wc -l) frames"
done
