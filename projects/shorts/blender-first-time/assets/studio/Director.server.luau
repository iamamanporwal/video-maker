-- ServerScriptService.Director : plays the shot timeline (ReplicatedStorage.Film.Timeline JSON) against the VO clock.
local HS = game:GetService("HttpService")
local RS = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")

local K = require(RS.Film.Kit)
local TL = HS:JSONDecode(require(RS.Film.Timeline))
Players.CharacterAutoLoads = false

local function V(t) return Vector3.new(t[1], t[2], t[3]) end
local function CF(t)  -- {x,y,z, yaw, pitch, roll} degrees
	return CFrame.new(t[1], t[2], t[3]) * CFrame.Angles(0, math.rad(t[4] or 0), 0) * CFrame.Angles(math.rad(t[5] or 0), 0, math.rad(t[6] or 0))
end

-- actors ---------------------------------------------------------------------------------------------------
local ACT = {}
for _, m in workspace.Cast:GetChildren() do K.prepCast(m); ACT[m.Name] = m end
for _, m in workspace.Props:GetChildren() do ACT[m.Name] = m end
for _, m in workspace.Extras:GetChildren() do ACT[m.Name] = m end
ACT.Cube = workspace.Cube; ACT.Laptop = workspace.Laptop
for name, m in ACT do
	if workspace.Cast:FindFirstChild(name) ~= m then
		for _, d in (m:IsA("BasePart") and {m} or m:GetDescendants()) do if d:IsA("BasePart") then d.Anchored = true end end
	end
end
local BASESCALE = {}
for name, m in ACT do if m:IsA("Model") then BASESCALE[name] = m:GetScale() end end

-- visibility via transparency for props (humanoids go to the holding pen)
local function setVis(m, on)
	local list = m:GetDescendants(); if m:IsA("BasePart") then table.insert(list, m) end
	for _, d in list do
		if d:IsA("BasePart") or d:IsA("Decal") then
			local o = d:GetAttribute("T0"); if o == nil then o = d.Transparency; d:SetAttribute("T0", o) end
			d.Transparency = on and o or 1
		elseif d:IsA("SurfaceGui") then d.Enabled = on
		elseif d:IsA("SelectionBox") then d.Visible = on
		elseif d:IsA("Light") and d.Name ~= "FilmKey" then d.Enabled = on
		elseif d:IsA("Light") and not on then d.Enabled = false end
	end
end

local function bottomOffset(m)
	local cf, sz = m:GetBoundingBox()
	local bottom = (cf - cf.Position) + (cf.Position - cf.UpVector * sz.Y / 2)
	return bottom:ToObjectSpace(m:GetPivot())
end
local function putProp(m, cf, off) m:PivotTo(cf * off) end

-- per-frame prop animations
local live = {}
RunService.Heartbeat:Connect(function()
	local now = workspace:GetServerTimeNow()
	for m, a in live do
		local u = math.clamp((now - a.t0) / a.dur, 0, 1)
		local e = a.ease == "in" and u * u or (a.ease == "linear" and u or 1 - (1 - u) * (1 - u))
		if a.isCube then
			local s = a.s0 + (a.s1 - a.s0) * e
			m.Size = Vector3.new(s, s, s)
			m.CFrame = a.from:Lerp(a.to, e) * CFrame.new(0, s / 2, 0) * CFrame.Angles(math.rad(a.spin * (now - a.t0)), math.rad(a.spin * 0.7 * (now - a.t0)), 0)
		else
			if a.s1 and math.abs(a.s1 - a.s0) > 1e-3 then
				m:ScaleTo(a.s0 + (a.s1 - a.s0) * e); a.off = bottomOffset(m)   -- re-derive after scaling
			end
			local cf = a.from:Lerp(a.to, e)
			local tt = now - a.t0
			if a.bob > 0 then cf = cf + Vector3.new(0, math.abs(math.sin(tt * 9)) * a.bob, 0) end
			if a.wobble > 0 then cf = cf * CFrame.Angles(0, 0, math.rad(math.sin(tt * 14) * a.wobble)) end
			if a.spin ~= 0 then cf = cf * CFrame.Angles(math.rad(a.spin * tt), math.rad(a.spin * 0.6 * tt), 0) end
			putProp(m, cf, a.off)
		end
		if u >= 1 and a.bob == 0 and a.wobble == 0 then live[m] = nil end
	end
end)

-- lighting / laptop screen ------------------------------------------------------------------------------
local function light(mode)
	local cc = Lighting:FindFirstChildOfClass("ColorCorrectionEffect"); local at = Lighting:FindFirstChildOfClass("Atmosphere")
	local night = mode == "night"
	Lighting.ClockTime = night and 0.2 or (mode == "morning" and 9.5 or 15.2)
	Lighting.Brightness = night and 1.4 or 2.6
	Lighting.Ambient = night and Color3.fromRGB(70, 80, 125) or Color3.fromRGB(110, 100, 95)
	Lighting.OutdoorAmbient = night and Color3.fromRGB(95, 105, 160) or Color3.fromRGB(150, 140, 130)
	-- night key lights on every actor so faces read
	for _, m in ACT do
		local host = m:IsA("BasePart") and m or (m:FindFirstChild("HumanoidRootPart") or m:FindFirstChildWhichIsA("BasePart", true))
		if host then
			local kl = host:FindFirstChild("FilmKey") or Instance.new("PointLight")
			kl.Name = "FilmKey"; kl.Color = Color3.fromRGB(255, 205, 160); kl.Brightness = (m == ACT.Cube) and 0.35 or 0.7
			kl.Range = (m == ACT.Cube) and 18 or 8; kl.Shadows = false; kl.Enabled = night; kl.Parent = host
		end
	end
	cc.TintColor = night and Color3.fromRGB(190, 205, 255) or Color3.fromRGB(255, 244, 228)
	cc.Saturation = night and 0.05 or 0.2; cc.Contrast = night and 0.15 or 0.1
	at.Density = night and 0.32 or 0.3; at.Color = night and Color3.fromRGB(60, 70, 110) or Color3.fromRGB(225, 215, 200)
	at.Decay = night and Color3.fromRGB(30, 35, 70) or Color3.fromRGB(150, 160, 190)
	for _, l in workspace.Lamps:GetDescendants() do if l:IsA("Light") then l.Enabled = night end end
end
local function screen(mode)
	local c = workspace.Laptop.Screen.SurfaceGui.BG.Viewport.CubeUI
	c.Visible = mode ~= "empty"
	local corner, hole = c:FindFirstChild("UICorner"), c:FindFirstChild("Hole")
	local col = ({donut = Color3.fromRGB(240, 130, 190), cube = Color3.fromRGB(150, 150, 152), horse = Color3.fromRGB(190, 140, 95)})[mode]
	if col then c.BackgroundColor3 = col end
	if corner then corner.CornerRadius = UDim.new(mode == "donut" and 0.5 or (mode == "horse" and 0.2 or 0), 0) end
	if hole then hole.Visible = mode == "donut" end
	for _, ch in c:GetChildren() do if ch:IsA("Frame") and ch.Name ~= "Hole" then ch.Visible = mode == "cube" end end
end

-- shot application --------------------------------------------------------------------------------------
local walkers = {}
local function applyActor(name, sp, t0)
	local m = ACT[name]; if not m then return end
	local isHum = m:FindFirstChildOfClass("Humanoid") ~= nil
	if isHum then
		K.place(m, V(sp.pos), sp.look and V(sp.look))
		if sp.face then K.face(m, sp.face) end
		local hum = m:FindFirstChildOfClass("Humanoid")
		if sp.to then
			hum.WalkSpeed = sp.speed or 10
			K.anim(m, (sp.speed or 10) > 13 and "run" or "walk")
			if sp.layer then K.layer(m, sp.layer) end
			hum:MoveTo(V(sp.to))
			walkers[m] = sp.after or "idle"
		else
			hum:MoveTo(m.HumanoidRootPart.Position); walkers[m] = nil
			K.anim(m, sp.anim or "idle", sp.animSpeed)
		end
	elseif m == ACT.Cube then
		setVis(m, not sp.ghost)
		m.Sel.Visible = true
		if sp.face then m.face.Texture = K.FACES[sp.face] or sp.face end
		m.face.Transparency = sp.face and 0 or 1
		m.Sel.LineThickness = (sp.size1 or sp.size or 3) > 10 and 0.35 or 0.08
		live[m] = {isCube = true, from = CF(sp.cf), to = CF(sp.to or sp.cf), s0 = sp.size or 3, s1 = sp.size1 or sp.size or 3,
			dur = sp.dur or 0.01, t0 = t0 + (sp.delay or 0), spin = sp.spin or 0, ease = sp.ease, bob = 0, wobble = 0}
	else
		setVis(m, true)
		if m:IsA("Model") then
			local s0 = (sp.scale or 1) * (BASESCALE[name] or 1)
			if math.abs(m:GetScale() - s0) > 1e-3 then m:ScaleTo(s0) end
			local off = bottomOffset(m)
			local a = {from = CF(sp.cf), to = CF(sp.to or sp.cf), dur = sp.dur or 0.01, t0 = t0 + (sp.delay or 0), off = off,
				s0 = s0, s1 = sp.scale1 and sp.scale1 * (BASESCALE[name] or 1), bob = sp.bob or 0, wobble = sp.wobble or 0,
				spin = sp.spin or 0, ease = sp.ease}
			putProp(m, a.from, off)
			live[m] = a
		else
			m.CFrame = CF(sp.cf)
		end
	end
end

for m, _ in pairs({}) do end
RunService.Heartbeat:Connect(function()
	for m, after in walkers do
		local hum = m:FindFirstChildOfClass("Humanoid")
		if hum and hum.MoveDirection.Magnitude < 0.05 and (m.HumanoidRootPart.AssemblyLinearVelocity.Magnitude < 0.5) then
			walkers[m] = nil; K.anim(m, after)
		end
	end
end)

CURRENT_LIGHT = "day"
local function applyShot(shot, t0)
	if shot.light then light(shot.light) end
	if shot.screen then screen(shot.screen) end
	for name, m in ACT do
		local sp = shot.actors[name]
		if sp == nil then
			live[m] = nil; walkers[m] = nil
			if m:FindFirstChildOfClass("Humanoid") then K.place(m, K.HOLD + Vector3.new(math.random(-40, 40), 0, math.random(-40, 40)))
			else setVis(m, false) end
		end
	end
	for name, sp in shot.actors do if name ~= "Robot" then applyActor(name, sp, t0) end end
	CURRENT_LIGHT = shot.light or CURRENT_LIGHT
	light(CURRENT_LIGHT)                                  -- re-assert key lights after visibility changes
	for _, ev in shot.events or {} do
		task.delay(math.max(0, t0 + ev.at - workspace:GetServerTimeNow()), function()
			local m = ACT[ev.actor]; if not m then return end
			if ev.face then if m == ACT.Cube then m.face.Texture = K.FACES[ev.face] else K.face(m, ev.face) end end
			if ev.anim then K.anim(m, ev.anim, ev.animSpeed) end
			if ev.prop then applyActor(ev.actor, ev.prop, workspace:GetServerTimeNow()) end
		end)
	end
end

-- go -----------------------------------------------------------------------------------------------------
local pen = Instance.new("Part"); pen.Anchored = true; pen.Size = Vector3.new(200, 2, 200); pen.Position = K.HOLD - Vector3.new(0, 4, 0); pen.Transparency = 1; pen.Parent = workspace
light(TL.shots[1].light or "day")
-- stage shot 1 early so the first frame after the marker is already correct
applyShot(TL.shots[1], workspace:GetServerTimeNow())
local T0 = workspace:GetServerTimeNow() + (TL.lead or 5)
local tv = Instance.new("NumberValue"); tv.Name = "T0"; tv.Value = T0; tv.Parent = RS.Film
for i, shot in TL.shots do
	local at = T0 + shot.t
	local wait = at - workspace:GetServerTimeNow()
	if wait > 0 then task.wait(wait) end
	if i > 1 then applyShot(shot, at) else applyShot(shot, at) end
	print(string.format("[film] shot %d %s at %.2f", i, shot.id or "", workspace:GetServerTimeNow() - T0))
end
task.wait(math.max(0, T0 + TL["end"] - workspace:GetServerTimeNow()))
print("[film] END")
