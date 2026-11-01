#!/bin/zsh
# Render each gallery model as a 120-frame transparent turntable -> public/tt/<name>.webm (VP9 + alpha)
cd "${0:A:h}/.." && R="$PWD/../../.."
B=/Applications/Blender.app/Contents/MacOS/Blender
typeset -A M
M=(robot $R/Input/robot.glb panda $R/Input/panda.glb brickguy $R/Input/brickguy.glb deer $R/Input/forest-deer.glb
   cups $R/Input/strawcups.glb cat $R/projects/shorts/concrete-cat/cat.glb frog $R/projects/shorts/gta-frog/frog.glb
   dragon $R/projects/shorts/playground-serpent/assets/dragon.glb jet $R/projects/artist-who-couldnt-create/capture/jet/model.glb
   anime $R/projects/shorts/anime-gf/assets/model.glb baddie $R/projects/shorts/roblox-explainer/public/baddie.glb noob $R/Input/roblox.glb)
mkdir -p public/tt
for n f in ${(kv)M}; do
  [[ -f public/tt/$n.webm ]] && continue
  rm -rf /tmp/claude-501/tt_$n; $B -b -P tools/gallery_tt.py -- $f /tmp/claude-501/tt_$n 120 > /tmp/claude-501/tt_$n.log 2>&1
  ffmpeg -y -v error -framerate 30 -i /tmp/claude-501/tt_$n/t_%04d.png -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 3M public/tt/$n.webm && echo "ok $n"
done
