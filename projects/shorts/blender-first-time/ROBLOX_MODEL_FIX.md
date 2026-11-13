# Making a Vi3W model look right inside Roblox

Ep1 (blender-first-time-3d.mp4) robot looked grey, smeared and eyeless in Roblox. Root causes and fixes, verified in Studio 2026-11-13:

| # | Cause | Effect in Roblox | Fix |
|---|-------|------------------|-----|
| 1 | GLB material is `doubleSided: true`; ~22% of faces (112,790 / 500k) were wound inward | Roblox culls back faces → pupils + panels vanished, you saw dark insides ("black smears") | Recalculate normals outward before export (`bmesh.ops.recalc_face_normals`), or emit both windings |
| 2 | 4K texture baked to ~13k vertex colours | eyes/smile/segment lines lost, blotchy | Keep UVs + a real texture (`TextureID`, 1024² = Roblox max) |
| 3 | `img.pixels` (already sRGB) gamma-encoded again | light blue washed to grey | No extra gamma on 8-bit textures |
| 4 | No ambient occlusion on Roblox meshes | concave detail (eye sockets, seams) reads flat | Bake AO from the full-res mesh, multiply into albedo (strength 0.85) |
| 5 | 500k → 9k tris | fine detail collapsed | 20k tris per MeshPart cap → split into parts (57k total, 3 parts sharing one bbox) |
| 6 | MeshPart default colour grey (163,162,165) | multiplies/dulls the texture | `Color = white`, SmoothPlastic |
| 7 | Black UV gutters | seams/mips bleed dark | 16 px island dilation before resize |

Pipeline: `./prep_robot.sh model.glb` → upload `robot_tex_ao.png` (MCP upload_image) → `RobotMesh.TEX` → `RobotMesh.BuildUV` (EditableMesh, UVs, normals, multi-part).
