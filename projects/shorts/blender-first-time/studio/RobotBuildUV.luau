-- ReplicatedStorage.RobotMesh.BuildUV : real Vi3W mesh rebuilt with EditableMesh + UVs + smooth normals + real texture.
-- Data: ModuleScript children D1..Dn returning chunks of robot_uv.json (dump_mesh_uv.py); TEX: StringValue rbxassetid.
-- Roblox caps a mesh at ~20k tris, so the model is split into N MeshParts of <= PER tris. Every part gets two tiny
-- triangles at the global bbox corners, so all parts share the same bounds/centre: give them all the same CFrame + Size.
-- Returns a Model (parts named P1..Pn, PrimaryPart P1), height 1 stud, pivot at the bbox centre.
local AS = game:GetService("AssetService")
local HS = game:GetService("HttpService")
local PER = 19900
return function(f)
	f = f or script.Parent
	local parts = {}
	for i = 1, 64 do local m = f:FindFirstChild("D" .. i); if not m then break end; parts[i] = require(m) end
	local d = HS:JSONDecode(table.concat(parts))
	local V, UV, N, F = d.v, d.uv, d.n, d.f
	local mn, mx = Vector3.one * math.huge, -Vector3.one * math.huge
	local P = table.create(#V // 3)
	for i = 1, #V // 3 do
		local p = Vector3.new(V[3 * i - 2], V[3 * i - 1] - 0.5, V[3 * i]); P[i] = p
		mn = mn:Min(p); mx = mx:Max(p)
	end
	local model = Instance.new("Model"); model.Name = "Vi3WRobot"
	local ntri = #F // 9
	local k0, pi = 0, 0
	while k0 < ntri do
		pi += 1
		local em = AS:CreateEditableMesh({ FixedSize = false })
		local vid, tid, nid = {}, {}, {}
		local function gv(i) local x = vid[i]; if not x then x = em:AddVertex(P[i]); vid[i] = x end; return x end
		local function gt(i) local x = tid[i]; if not x then x = em:AddUV(Vector2.new(UV[2 * i - 1], UV[2 * i])); tid[i] = x end; return x end
		local function gn(i) local x = nid[i]; if not x then x = em:AddNormal(Vector3.new(N[3 * i - 2], N[3 * i - 1], N[3 * i])); nid[i] = x end; return x end
		local k1 = math.min(ntri, k0 + PER - 2)
		for t = k0, k1 - 1 do
			local k = t * 9 + 1
			local fid = em:AddTriangle(gv(F[k] + 1), gv(F[k + 3] + 1), gv(F[k + 6] + 1))
			em:SetFaceUVs(fid, { gt(F[k + 1] + 1), gt(F[k + 4] + 1), gt(F[k + 7] + 1) })
			em:SetFaceNormals(fid, { gn(F[k + 2] + 1), gn(F[k + 5] + 1), gn(F[k + 8] + 1) })
			if t % 5000 == 0 then task.wait() end
		end
		for _, c in { mn, mx } do                  -- bbox anchors (sub-millimetre, invisible)
			local e = 1e-4
			em:AddTriangle(em:AddVertex(c), em:AddVertex(c + Vector3.new(e, 0, 0)), em:AddVertex(c + Vector3.new(0, 0, e)))
		end
		local mp = AS:CreateMeshPartAsync(Content.fromObject(em))
		mp.Name = "P" .. pi
		mp.Anchored = true; mp.CanCollide = false; mp.CanQuery = false; mp.CastShadow = true
		mp.Color = Color3.new(1, 1, 1)             -- texture is multiplied by Color: the default grey dulls it
		mp.Material = Enum.Material.SmoothPlastic
		mp.TextureID = f.TEX.Value
		mp.Parent = model
		k0 = k1
	end
	model.PrimaryPart = model.P1
	return model
end
