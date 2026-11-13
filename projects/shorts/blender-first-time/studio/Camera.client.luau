-- StarterPlayerScripts.FilmCamera : sync marker + per-shot camera + client-side Vi3W robot (EditableMesh).
local HS = game:GetService("HttpService")
local RS = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local StarterGui = game:GetService("StarterGui")
local Players = game:GetService("Players")

local TL = HS:JSONDecode(require(RS:WaitForChild("Film"):WaitForChild("Timeline")))
local cam = workspace.CurrentCamera
pcall(function() StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.All, false) end)

-- overlay: black → magenta marker → black → clear (post detects the marker for crop + sync)
local gui = Instance.new("ScreenGui"); gui.IgnoreGuiInset = true; gui.DisplayOrder = 100; gui.ResetOnSpawn = false
gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
local cover = Instance.new("Frame"); cover.Size = UDim2.fromScale(1, 1); cover.BorderSizePixel = 0; cover.BackgroundColor3 = Color3.new(0, 0, 0); cover.Parent = gui

local T0v = RS.Film:WaitForChild("T0", 60)
local T0 = T0v.Value

-- Vi3W robot (real Vi3W mesh rebuilt from vertex data; EditableMesh is client-local) -------------------
-- BuildUV (textured, UVs + normals, split into <=20k-tri parts sharing one bbox) if present, else old vertex-colour Build
local robotProto
if RS.RobotMesh:FindFirstChild("BuildUV") then
	robotProto = require(RS.RobotMesh.BuildUV)(RS.RobotMesh)
else
	local p = require(RS.RobotMesh.Build)(RS.RobotMesh); p.Material = Enum.Material.SmoothPlastic
	robotProto = Instance.new("Model"); p.Name = "P1"; p.Parent = robotProto; robotProto.PrimaryPart = p
end
local robots = {}
local function robotN(i)
	if not robots[i] then local r = robotProto:Clone(); r.Parent = workspace; robots[i] = r end
	return robots[i]
end
local function CF(t) return CFrame.new(t[1], t[2], t[3]) * CFrame.Angles(0, math.rad(t[4] or 0), 0) * CFrame.Angles(math.rad(t[5] or 0), 0, math.rad(t[6] or 0)) end
local baseSize = robotProto.PrimaryPart.Size
local function placeRobot(r, cf, h)
	local sz = baseSize * (h / baseSize.Y)
	local c = cf * CFrame.new(0, sz.Y / 2, 0)
	for _, p in r:GetChildren() do if p:IsA("BasePart") then p.Size = sz; p.CFrame = c end end
end
local function setVisible(r, on)
	for _, p in r:GetChildren() do if p:IsA("BasePart") then p.Transparency = on and 0 or 1 end end
end

local function V(t) return Vector3.new(t[1], t[2], t[3]) end
local function shotAt(t)
	local k = 1
	for i, s in TL.shots do if s.t <= t then k = i end end
	return k
end
local function ease(u, kind)
	if kind == "linear" then return u end
	if kind == "in" then return u * u end
	return 1 - (1 - u) ^ 3      -- out-cubic: fast start, gentle settle (push-ins)
end
local function actorPos(name, off)
	local m = workspace.Cast:FindFirstChild(name) or workspace.Props:FindFirstChild(name) or workspace:FindFirstChild(name)
	if not m then return nil end
	local p = (m:FindFirstChild("ClassicHead") and m.ClassicHead.Position) or (m:IsA("BasePart") and m.Position) or m:GetPivot().Position
	return p + (off and V(off) or Vector3.zero)
end

local lastShot = 0
-- wide viewport → roll the camera 90° so the recording, rotated back, is a full-height vertical frame
local vs = cam.ViewportSize
local ROLL90 = TL.roll90 or (vs.X > vs.Y * 1.25)
-- timeline FOVs are the FINAL video's vertical FOV; convert to the viewport's vertical FOV
local function viewFov(f)
	if not ROLL90 then return f end
	return math.deg(2 * math.atan(math.tan(math.rad(f / 2)) * vs.Y / vs.X))
end
local robotLight = Instance.new("PointLight"); robotLight.Range = 60; robotLight.Brightness = 1.2; robotLight.Color = Color3.fromRGB(255, 225, 190)
robotLight.Parent = robotProto.PrimaryPart
local isNight = function() local c = game.Lighting.ClockTime; return c < 5 or c > 19 end
RunService:BindToRenderStep("FilmCam", Enum.RenderPriority.Camera.Value + 1, function()
	local now = workspace:GetServerTimeNow()
	local t = now - T0
	-- marker timing
	if t < -3.6 then cover.BackgroundColor3 = Color3.new(0, 0, 0); cover.BackgroundTransparency = 0
	elseif t < -2.6 then cover.BackgroundColor3 = Color3.fromRGB(255, 0, 255); cover.BackgroundTransparency = 0
	elseif t < 0 then cover.BackgroundColor3 = Color3.new(0, 0, 0); cover.BackgroundTransparency = 0
	elseif t > TL["end"] then cover.BackgroundColor3 = Color3.new(0, 0, 0); cover.BackgroundTransparency = 0
	else cover.BackgroundTransparency = 1 end

	cam.CameraType = Enum.CameraType.Scriptable
	local k = shotAt(math.max(0, t))
	local s = TL.shots[k]
	local s1 = TL.shots[k + 1]
	local dur = (s1 and s1.t or TL["end"]) - s.t
	local u = math.clamp((math.max(0, t) - s.t) / dur, 0, 1)
	local c = s.cam
	local e = ease(u, c.ease)
	local p = V(c.p0):Lerp(V(c.p1 or c.p0), e)
	local l = V(c.l0):Lerp(V(c.l1 or c.l0), e)
	if c.track then local tp = actorPos(c.track, c.trackOff); if tp then l = tp end end
	if c.follow then local tp = actorPos(c.follow); if tp then p = tp + V(c.followOff) end end
	local fov = (c.fov or 50) + ((c.fov1 or c.fov or 50) - (c.fov or 50)) * e
	local st = math.max(0, t) - s.t
	if c.snap then fov = fov + 22 * math.max(0, 1 - st / 0.16) end            -- snap zoom: wide → tight in 0.16 s
	local roll = (c.roll or 0) + ((c.roll1 or c.roll or 0) - (c.roll or 0)) * e
	local cf = CFrame.lookAt(p, l)
	if c.shake then
		local a = c.shake * math.max(0, 1 - st / 0.6)
		cf = cf * CFrame.Angles(math.rad(math.sin(now * 61) * a * 3), math.rad(math.cos(now * 53) * a * 3), 0)
	end
	cf = cf * CFrame.Angles(0, 0, math.rad(roll + (ROLL90 and 90 or 0)))
	cam.CFrame = cf
	cam.FieldOfView = viewFov(fov)

	-- robots (client actors)
	local specs = s.actors.Robot or {}
	for i, r in robots do if not specs[i] then setVisible(r, false) end end
	for i, rs in specs do
		local r = robotN(i)
		local ru = math.clamp((st - (rs.delay or 0)) / (rs.dur or 0.01), 0, 1)
		local re = ease(ru, rs.ease)
		local from, to = CF(rs.cf), CF(rs.to or rs.cf)
		local h = rs.h + ((rs.h1 or rs.h) - rs.h) * re
		local cfr = from:Lerp(to, re)
		if rs.bob then cfr = cfr + Vector3.new(0, math.abs(math.sin(st * 6)) * rs.bob, 0) end
		setVisible(r, true)
		placeRobot(r, cfr, h)
		local pl = r.PrimaryPart:FindFirstChildOfClass("PointLight"); if pl then pl.Enabled = isNight(); pl.Range = math.clamp(h * 2, 16, 60) end
	end
	if k ~= lastShot then lastShot = k end
end)
