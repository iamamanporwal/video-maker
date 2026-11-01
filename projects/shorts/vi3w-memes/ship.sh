#!/bin/zsh
# Copy finished vi3w-memes renders to FinalUploads/ with caption + rights warning (usage: ./ship.sh 02-more-3d ...).
cd "$(dirname $0)"
F=../../../FinalUploads
typeset -A WARN
WARN[01-blender-hour-9]="⚠️ Before posting: ask permission for the monkey typing template (Bengali Trifling) and the Blender armor timelapse (Smooth). See projects/shorts/vi3w-memes/RIGHTS.md"
WARN[02-more-3d]="⚠️ Before posting: ask permission for the hacker typing clip (@thebige8905) and the Korean rage meme (@misterhirobrin). See projects/shorts/vi3w-memes/RIGHTS.md"
WARN[03-anime-hair]="⚠️ Before posting: ask permission for the Blender hair timelapse (dollme). Keyboard Cat green screen is the creator's own template. See projects/shorts/vi3w-memes/RIGHTS.md"
WARN[04-baddie-3d]="⚠️ Before posting: ask permission for the sweaty gamer meme (@justwantlifetobefunny9953). @EazyEthan clip is cleared. See projects/shorts/vi3w-memes/RIGHTS.md"
WARN[05-code-vs-models]="⚠️ Before posting: ask permission for the monkey typing template, hacker typing clip and Korean rage meme. See projects/shorts/vi3w-memes/RIGHTS.md"
WARN[07-chest-race]="⚠️ Before posting: ask permission for the monkey typing template (Bengali Trifling) and the treasure-chest timelapse (Blender Forbeg, -9zV5CHnIq0). Vi3W footage is yours. See projects/shorts/vi3w-memes/RIGHTS.md"
WARN[08-car-race]="⚠️ Before posting: ask permission for the Korean rage meme (@misterhirobrin), Keyboard Dog (@AndrewDameluz) and the Audi R8 timelapse (HOKIROYA, lNjWB_zMr1s). Vi3W footage is yours. See projects/shorts/vi3w-memes/RIGHTS.md"
WARN[09-jet-race]="⚠️ Before posting: ask permission for the rage clip (@jun_azusa) and the F-22 timelapse (Kentackle, Ra6Tow7t-9g). The Vi3W demo is yours. See projects/shorts/vi3w-memes/RIGHTS.md"
WARN[06-game-jam]="⚠️ Before posting: ask permission for the rage clips (@garytheelite337, @jun_azusa) and the hacker typing clip. Doodle Derby is cleared. See projects/shorts/vi3w-memes/RIGHTS.md"
for n in "$@"; do
  name=meme-${n#*-}
  cp $n/out/*-9x16.mp4 $F/$name.mp4
  { echo "${WARN[$n]}"; echo; cat $n/out/caption.txt; } > $F/$name.txt
  echo "shipped $F/$name.mp4"
done
