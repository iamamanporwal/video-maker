#!/bin/zsh
# Copy finished nakey-mods renders to FinalUploads/ (usage: ./ship.sh [Drafts] ; default all ids)
cd "$(dirname $0)"
F=../../../FinalUploads${1:+/$1}
mkdir -p $F
for d in out/0*/; do
  n=$(basename $d); [[ -f $d/$n.mp4 ]] || continue
  cp $d/$n.mp4 $F/mods-${n#*-}.mp4
  { echo "✅ Creator permission: NakeyJakey OK'd clipping this video (keep the credit line)."; echo; cat $d/caption.txt; } > $F/mods-${n#*-}.txt
  echo "shipped $F/mods-${n#*-}.mp4"
done
