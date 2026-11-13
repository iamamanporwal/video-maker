#!/bin/zsh
# ./make_film.sh [take-name]  — fully automatic in-Studio film:
#   film.py (shot list on the VO clock) → push scripts+timeline into the open Studio place via Studio MCP →
#   window-only recording (tools/wincap) + Play → stop → assemble.py (crop/un-roll, glitch-safe, captions, outro, mix)
# Needs: Roblox Studio open on town.rbxlx with "Enable Studio as MCP server" on; assets/ served on localhost:8765.
set -e
cd "${0:A:h}"
TAKE=${1:-take_$(date +%H%M%S)}
MCP=(python3 tools/studio_mcp.py call)
SID=$(python3 tools/studio_mcp.py call list_roblox_studios | python3 -c "import json,sys;print(json.load(sys.stdin)['studios'][0]['id'])")
curl -s -o /dev/null --max-time 3 http://localhost:8765/studio/timeline.json || (cd assets && nohup python3 -m http.server 8765 --bind 127.0.0.1 >/dev/null 2>&1 &; sleep 1)
python3 film.py && cp studio/* assets/studio/
"${MCP[@]}" execute_luau "{\"studio_id\":\"$SID\",\"datamodel_type\":\"Edit\",\"code\":\"local HS=game:GetService('HttpService') local function g(p) return HS:GetAsync('http://localhost:8765/studio/'..p..'?r='..os.clock()) end local f=game.ReplicatedStorage.Film f.Kit.Source=g('Film.luau') f.Timeline.Source='return [==['..g('timeline.json')..']==]' game.ServerScriptService.Director.Source=g('Director.server.luau') game.StarterPlayer.StarterPlayerScripts.FilmCamera.Source=g('Camera.client.luau') return 'pushed'\"}"
END=$(python3 -c "import json;t=json.load(open('studio/timeline.json'));print(int(t['end']+t['lead']+12))")
mkdir -p rec
tools/wincap roblox $END rec/$TAKE.mp4 30 &
REC=$!
sleep 1
"${MCP[@]}" start_stop_play "{\"studio_id\":\"$SID\",\"is_start\":true}"
wait $REC
"${MCP[@]}" start_stop_play "{\"studio_id\":\"$SID\",\"is_start\":false}"
~/models/chatterbox-venv/bin/python assemble.py rec/$TAKE.mp4 | grep -v '^frame'
echo "→ out/blender-first-time-3d.mp4"
