#!/bin/zsh
# ./prep_robot.sh path/to/model.glb  → assets/robot_uv.json + assets/robot_tex_ao.png (Roblox-ready Vi3W model)
# Then upload the texture via Studio MCP upload_image (http://localhost:8765/robot_tex_ao.png), set
# ReplicatedStorage.RobotMesh.TEX to the returned id, and reload D1..Dn from robot_uv.json (see ROBLOX_MODEL_FIX.md).
set -e
cd "${0:A:h}"
GLB=${1:-../vi3w-outro/assets/robot.glb}
B=/Applications/Blender.app/Contents/MacOS/Blender
PY=~/models/chatterbox-venv/bin/python
$B -b -P bake_ao.py -- "$GLB" assets 2048 64 2>&1 | grep "AO baked"          # AO from the FULL-res mesh
$B -b -P dump_mesh_uv.py -- "$GLB" assets 57000 1024 2>&1 | grep "recalc\|^verts"   # outward normals, 57k tris, UVs
$PY tex_pad.py assets 1024 && mv assets/robot_tex.png assets/robot_tex_ao.png  # AO x albedo, gutter dilation, 1K
