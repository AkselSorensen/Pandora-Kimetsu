-- Clic gauche / droit = grappins (maintenir), R = enrouler vite, Shift = boost (ZQSD = direction),
-- F = trancher, B = changer de lames, G = lance-foudre

local ui = WebUI("ODM UI", "file://UI/index.html", WidgetVisibility.Hidden)
local ui_ready = false
local last_status = { gas = ODM.GasMax, blades = ODM.BladesMax, spare = ODM.SpareBlades, reloading = false, spears = ODM.Spears }

local function PushStatus()
	if (ui_ready) then
		ui:CallEvent("ODM:Status", last_status.gas, ODM.GasMax, last_status.blades, ODM.BladesMax,
			last_status.spare, last_status.reloading, last_status.spears)
	end
end

ui:Subscribe("Ready", function()
	ui_ready = true
	PushStatus()
end)

local is_equipped = false
local speed_factor = 0          -- 0..1, lissé
local last_sent_factor = -1
local last_sent_time = 0
local base_arm_length = nil

Events.SubscribeRemote("ODM:Equipped", function(equipped)
	is_equipped = equipped
	ui:SetVisibility(equipped and WidgetVisibility.VisibleNotHitTestable or WidgetVisibility.Hidden)
	if (not equipped) then
		speed_factor = 0
		if (ui_ready) then ui:CallEvent("ODM:Speed", 0) end
		local player = Client.GetLocalPlayer()
		if (player and base_arm_length) then
			pcall(function() player:SetCameraArmLength(base_arm_length) end)
		end
	end
end)

Events.SubscribeRemote("ODM:Status", function(gas, blades, spare, reloading, spears)
	last_status = { gas = gas, blades = blades, spare = spare, reloading = reloading, spears = spears }
	PushStatus()
end)

local function GetCharacter()
	local player = Client.GetLocalPlayer()
	if (not player) then return nil end
	return player:GetControlledCharacter()
end

-- Direction de la caméra à travers le viseur
local function GetView()
	return Viewport.DeprojectScreenToWorld(Viewport.GetViewportSize() / 2)
end

local function Fire(side)
	local character = GetCharacter()
	if (not character) then return end

	local view = GetView()
	local start_location = view.Position + view.Direction * 50
	local end_location = view.Position + view.Direction * ODM.MaxRange
	local channels = CollisionChannel.WorldStatic | CollisionChannel.WorldDynamic | CollisionChannel.PhysicsBody
		| CollisionChannel.Vehicle | CollisionChannel.Pawn | CollisionChannel.Mesh

	local result = Trace.LineSingle(
		start_location,
		end_location,
		channels,
		TraceMode.ReturnEntity | TraceMode.TraceOnlyVisibility,
		{ character }
	)

	if (result.Success) then
		Events.CallRemote("ODM:Hook", Reliability.Reliable, side, result.Location, result.Entity)
	end
end

-- Direction du boost : touches de déplacement (ZQSD ou WASD) par rapport à la caméra, sinon vers le viseur
local function GetBoostDirection()
	local view = GetView()
	local forward = view.Direction

	local f, r = 0, 0
	if (Input.IsKeyDown("W") or Input.IsKeyDown("Z")) then f = f + 1 end
	if (Input.IsKeyDown("S")) then f = f - 1 end
	if (Input.IsKeyDown("D")) then r = r + 1 end
	if (Input.IsKeyDown("A") or Input.IsKeyDown("Q")) then r = r - 1 end

	if (f == 0 and r == 0) then
		return forward
	end

	-- axe droit de la caméra (à plat)
	local flat_len = math.sqrt(forward.X * forward.X + forward.Y * forward.Y)
	if (flat_len < 0.001) then return forward end
	local flat = Vector(forward.X / flat_len, forward.Y / flat_len, 0)
	local right = Vector(-flat.Y, flat.X, 0)

	return forward * f + right * r
end

-- Position réelle de la nuque d'un Titan (os du squelette, lu côté client)
local function GetNapePosition(titan)
	for _, bone in ipairs(ODM.NapeBones) do
		local ok, transform = pcall(function() return titan:GetSocketTransform(bone) end)
		if (ok and transform and transform.Location) then
			return transform.Location
		end
	end
	return nil
end

-- Titan dont la nuque est la plus proche de nous (envoyé au serveur avec le coup)
local function FindNapeTarget()
	local character = GetCharacter()
	if (not character) then return nil end
	local my_location = character:GetLocation()

	local best, best_pos, best_dist
	for _, other in pairs(Character.GetAll()) do
		if (other ~= character and other:GetValue("odm_titan")) then
			local pos = GetNapePosition(other)
			if (pos) then
				local d = pos - my_location
				local dist = math.sqrt(d.X * d.X + d.Y * d.Y + d.Z * d.Z)
				if (not best_dist or dist < best_dist) then
					best, best_pos, best_dist = other, pos, dist
				end
			end
		end
	end
	return best, best_pos
end

Input.Subscribe("KeyPress", function(key_name)
	if (key_name == "LeftShift") then
		Events.CallRemote("ODM:Boost", Reliability.Reliable, GetBoostDirection())
	elseif (key_name == "F") then
		local titan, nape = FindNapeTarget()
		if (titan) then
			Events.CallRemote("ODM:Slash", Reliability.Reliable, titan, nape)
		else
			Events.CallRemote("ODM:Slash", Reliability.Reliable)
		end
	elseif (key_name == "G") then
		Events.CallRemote("ODM:Spear", Reliability.Reliable, GetView().Direction)
	elseif (key_name == "B") then
		Events.CallRemote("ODM:Reload", Reliability.Reliable)
	elseif (key_name == "R") then
		Events.CallRemote("ODM:Reel", Reliability.Reliable, true)
	end
end)

Input.Subscribe("KeyUp", function(key_name)
	if (key_name == "R") then
		Events.CallRemote("ODM:Reel", Reliability.Reliable, false)
	end
end)

-- Les clics souris ont leurs propres événements
Input.Subscribe("MouseDown", function(key_name)
	if (key_name == "LeftMouseButton") then
		Fire("left")
	elseif (key_name == "RightMouseButton") then
		Fire("right")
	end
end)

Input.Subscribe("MouseUp", function(key_name)
	if (key_name == "LeftMouseButton") then
		Events.CallRemote("ODM:Unhook", Reliability.Reliable, "left")
	elseif (key_name == "RightMouseButton") then
		Events.CallRemote("ODM:Unhook", Reliability.Reliable, "right")
	end
end)

-- Effet de vitesse : bords sombres et flous, lignes de vent (interface) + caméra qui recule
Client.Subscribe("Tick", function(delta_time)
	if (not is_equipped) then return end
	local character = GetCharacter()
	if (not character) then return end

	local v = character:GetVelocity()
	local speed = math.sqrt(v.X * v.X + v.Y * v.Y + v.Z * v.Z)
	local target = (speed - ODM.SpeedEffectStart) / (ODM.SpeedEffectFull - ODM.SpeedEffectStart)
	target = math.max(0, math.min(1, target))

	-- lissage : monte vite, redescend doucement
	local rate = (target > speed_factor) and 6 or 2.5
	speed_factor = speed_factor + (target - speed_factor) * math.min(1, rate * delta_time)

	-- envoi à l'interface au plus 20 fois par seconde
	local now = os.clock()
	if (ui_ready and now - last_sent_time > 0.05 and math.abs(speed_factor - last_sent_factor) > 0.01) then
		last_sent_time = now
		last_sent_factor = speed_factor
		ui:CallEvent("ODM:Speed", speed_factor)

		-- la caméra recule avec la vitesse (le FOV n'est pas réglable quand on possède un personnage)
		local player = Client.GetLocalPlayer()
		if (player) then
			pcall(function()
				if (not base_arm_length) then base_arm_length = player:GetCameraArmLength(true) end
				player:SetCameraArmLength(base_arm_length + ODM.SpeedCameraPullBack * speed_factor)
			end)
		end
	end
end)

Console.Log("[odm-gear] client charge")
