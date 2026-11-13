-- ReplicatedStorage.Film.Kit : shared runtime helpers for the in-Studio film (server side uses most of it).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local KSP = game:GetService("KeyframeSequenceProvider")

local K = {}
K.HOLD = Vector3.new(1500, 3, 1500)               -- off-stage holding pen
K.FACES = {
	shocked = "rbxassetid://90364903580238", nervous = "rbxassetid://6748512728", angry = "rbxassetid://17352691019",
	cry = "rbxassetid://87296127405163", grin = "rbxassetid://14821479527", scream = "rbxassetid://77376360443384",
	sleepy = "rbxassetid://87512740314968", happy = "rbxasset://textures/face.png", evil = "rbxassetid://5874771306",
	sad = "rbxassetid://16985277656",
}
K.ANIMS = {
	idle = "rbxassetid://507766388", walk = "rbxassetid://507777826", run = "rbxassetid://507767714",
	wave = "rbxassetid://507770239", point = "rbxassetid://507770453", cheer = "rbxassetid://507770677",
	laugh = "rbxassetid://507770818", dance = "rbxassetid://507771019", dance2 = "rbxassetid://507776043",
	dance3 = "rbxassetid://507777268", jump = "rbxassetid://507765000",
}
local function R(x, y, z) return CFrame.Angles(math.rad(x or 0), math.rad(y or 0), math.rad(z or 0)) end
-- joint-space poses (verified with FK in edit mode); keys are AnimationConstraint names
K.POSES = {
	armsUp = {RightShoulder = R(0, 0, 160), LeftShoulder = R(0, 0, -160)},
	scared = {RightShoulder = R(70, 0, 40), LeftShoulder = R(70, 0, -40)},
	hips = {RightShoulder = R(0, 0, -30), LeftShoulder = R(0, 0, 30), RightElbow = R(-60, 0, 0), LeftElbow = R(-60, 0, 0)},
	shrug = {RightShoulder = R(0, 0, 45), LeftShoulder = R(0, 0, -45), RightElbow = R(0, 0, -60), LeftElbow = R(0, 0, 60), Neck = R(0, 0, 10)},
	facepalm = {RightShoulder = R(150, 0, -20), RightElbow = R(90, 0, 0), Neck = R(15, 0, 0)},
	typing = {RightShoulder = R(70, 0, 10), LeftShoulder = R(70, 0, -10), RightElbow = R(30, 0, 0), LeftElbow = R(30, 0, 0), Neck = R(10, 0, 0)},
	hold = {RightShoulder = R(75, 0, 20), LeftShoulder = R(75, 0, -20), RightElbow = R(20, 0, 0), LeftElbow = R(20, 0, 0)},
	flex = {RightShoulder = R(0, 0, 90), LeftShoulder = R(0, 0, -90), RightElbow = R(0, 0, 90), LeftElbow = R(0, 0, -90)},
	search = {Waist = R(30, 0, 0), RightShoulder = R(60, 0, 15), LeftShoulder = R(50, 0, -10)},
	pointAt = {RightShoulder = R(90, 0, 0)},
}
local JOINT_PART = {Root = "LowerTorso", Waist = "UpperTorso", Neck = "Head", RightShoulder = "RightUpperArm", RightElbow = "RightLowerArm",
	RightWrist = "RightHand", LeftShoulder = "LeftUpperArm", LeftElbow = "LeftLowerArm", LeftWrist = "LeftHand", RightHip = "RightUpperLeg",
	RightKnee = "RightLowerLeg", RightAnkle = "RightFoot", LeftHip = "LeftUpperLeg", LeftKnee = "LeftLowerLeg", LeftAnkle = "LeftFoot"}
local TREE = {HumanoidRootPart = {"LowerTorso"}, LowerTorso = {"UpperTorso", "RightUpperLeg", "LeftUpperLeg"},
	UpperTorso = {"Head", "RightUpperArm", "LeftUpperArm"}, RightUpperArm = {"RightLowerArm"}, RightLowerArm = {"RightHand"},
	LeftUpperArm = {"LeftLowerArm"}, LeftLowerArm = {"LeftHand"}, RightUpperLeg = {"RightLowerLeg"}, RightLowerLeg = {"RightFoot"},
	LeftUpperLeg = {"LeftLowerLeg"}, LeftLowerLeg = {"LeftFoot"}}

local poseIds = {}
local function poseAnimId(name)
	if poseIds[name] then return poseIds[name] end
	local spec = K.POSES[name]
	local byPart = {}
	for joint, cf in spec do byPart[JOINT_PART[joint]] = cf end
	local ks = Instance.new("KeyframeSequence"); ks.Loop = true; ks.Priority = Enum.AnimationPriority.Action
	for _, tt in {0, 1} do
		local kf = Instance.new("Keyframe"); kf.Time = tt
		local function build(partName, parent)
			local p = Instance.new("Pose"); p.Name = partName; p.CFrame = byPart[partName] or CFrame.new()
			p.Weight = byPart[partName] and 1 or 0
			p.Parent = parent
			for _, ch in TREE[partName] or {} do build(ch, p) end
		end
		build("HumanoidRootPart", kf)
		kf.Parent = ks
	end
	local id = KSP:RegisterKeyframeSequence(ks)
	poseIds[name] = id
	return id
end

local tracks = setmetatable({}, {__mode = "k"})
function K.anim(m, name, speed)
	local hum = m:FindFirstChildOfClass("Humanoid"); if not hum then return end
	local animator = hum:FindFirstChildOfClass("Animator") or Instance.new("Animator", hum)
	tracks[m] = tracks[m] or {}
	local T = tracks[m]
	for _, tr in animator:GetPlayingAnimationTracks() do tr:Stop(0.15) end
	local function play(id, prio)
		T[id] = T[id] or animator:LoadAnimation((function() local a = Instance.new("Animation"); a.AnimationId = id; return a end)())
		local tr = T[id]; tr.Priority = prio; tr.Looped = true; tr:Play(0.15); tr:AdjustSpeed(speed or 1)
	end
	-- base layer: idle (or walk/run); upper layer: pose or emote
	if name == "walk" or name == "run" then play(K.ANIMS[name], Enum.AnimationPriority.Movement)
	else
		play(K.ANIMS.idle, Enum.AnimationPriority.Idle)
		if K.ANIMS[name] and name ~= "idle" then play(K.ANIMS[name], Enum.AnimationPriority.Action)
		elseif K.POSES[name] then play(poseAnimId(name), Enum.AnimationPriority.Action) end
	end
end
function K.layer(m, poseName)     -- add a pose on top of whatever (e.g. walk + hold)
	local hum = m:FindFirstChildOfClass("Humanoid"); local animator = hum:FindFirstChildOfClass("Animator")
	local a = Instance.new("Animation"); a.AnimationId = poseAnimId(poseName)
	local tr = animator:LoadAnimation(a); tr.Priority = Enum.AnimationPriority.Action; tr.Looped = true; tr:Play(0.1)
end

function K.face(m, key)
	local ch = m:FindFirstChild("ClassicHead")
	if ch and ch:FindFirstChild("face") then ch.face.Texture = K.FACES[key] or key end
end

-- make edit-time anchored FK rigs playable: unanchor, weld classic head, reset joints
function K.prepCast(model)
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then d.Anchored = false; d.CanCollide = (d.Name == "HumanoidRootPart") end
	end
	local ch = model:FindFirstChild("ClassicHead")
	if ch then
		ch.Massless = true; ch.CanCollide = false
		ch.CFrame = model.Head.CFrame
		for _, w in ch:GetChildren() do if w:IsA("WeldConstraint") then w:Destroy() end end
		local w = Instance.new("WeldConstraint"); w.Part0 = model.Head; w.Part1 = ch; w.Parent = ch
	end
	for _, acc in model:GetChildren() do
		if acc:IsA("Accessory") and acc:FindFirstChild("Handle") then acc.Handle.Massless = true; acc.Handle.CanCollide = false end
	end
	local hum = model:FindFirstChildOfClass("Humanoid")
	hum.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	hum.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
	if not hum:FindFirstChildOfClass("Animator") then Instance.new("Animator", hum) end
	model.HumanoidRootPart:SetNetworkOwner(nil)
end

function K.place(m, pos, look)
	local hrp = m:FindFirstChild("HumanoidRootPart")
	local hum = m:FindFirstChildOfClass("Humanoid")
	local h = hum and (hum.HipHeight + hrp.Size.Y / 2) or 0
	local p = Vector3.new(pos.X, pos.Y + h, pos.Z)
	local cf = look and CFrame.lookAt(p, Vector3.new(look.X, p.Y, look.Z)) or CFrame.new(p)
	m:PivotTo(cf)
	if hrp then hrp.AssemblyLinearVelocity = Vector3.zero end
end

return K
