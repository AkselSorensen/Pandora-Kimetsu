-- État par joueur
local states = {}
-- Titans : [character] = { type, last_attack, max_health }
local titans = {}

local function Now()
	return os.clock()
end

local function Length(v)
	return math.sqrt(v.X * v.X + v.Y * v.Y + v.Z * v.Z)
end

local function Dot(a, b)
	return a.X * b.X + a.Y * b.Y + a.Z * b.Z
end

local function GetState(player)
	if (not states[player]) then
		states[player] = {
			hooks = {},
			equipped = false,
			gas = ODM.GasMax,
			blades = ODM.BladesMax,
			spare = ODM.SpareBlades,
			reload_at = 0,
			reel = false,
			last_slash = 0,
			boost_until = 0,
			smoke_timer = 0,
			status_timer = 0,
			spears = ODM.Spears,
			last_spear = 0,
			prev_vz = 0,
			last_hook_time = 0,
			grabbed_by = nil,
			struggle = 0,
		}
	end
	return states[player]
end

local function Say(player, text)
	pcall(function() Chat.SendMessage(player, text) end)
end

---------------------------------------------------------------------
-- Grappins : câble de longueur fixe -> pendule, qui se raccourcit
---------------------------------------------------------------------

local RemoveHook

local function SetEquipped(player, equipped)
	local state = GetState(player)
	state.equipped = equipped
	if (equipped) then
		state.gas = ODM.GasMax
		state.blades = ODM.BladesMax
		state.spare = ODM.SpareBlades
		state.reload_at = 0
		state.spears = ODM.Spears
	else
		RemoveHook(state, "left")
		RemoveHook(state, "right")
	end
	Events.CallRemote("ODM:Equipped", player, Reliability.Reliable, equipped)
	Say(player, equipped
		and "<green>[ODM]</> Equipé : clic gauche/droit grappins, R enrouler, Shift boost (ZQSD pour la direction), F lames, B changer de lames, G lance-foudre."
		or "<red>[ODM]</> Équipement tridimensionnel retiré.")
end

-- Appelé depuis le menu props & armes
Events.Subscribe("ODM:Equip", function(player)
	SetEquipped(player, not GetState(player).equipped)
end)

function RemoveHook(state, side)
	local hook = state.hooks[side]
	if (not hook) then return end
	if (hook.cable and hook.cable:IsValid()) then hook.cable:Destroy() end
	if (hook.anchor and hook.anchor:IsValid()) then hook.anchor:Destroy() end
	state.hooks[side] = nil
end

local function CreateHook(state, character, side, point, target)
	RemoveHook(state, side)

	-- Point d'ancrage invisible pour accrocher l'extrémité du câble
	local anchor = Prop(point, Rotator(), "nanos-world::SM_Cube", CollisionType.NoCollision, false)
	anchor:SetScale(Vector(0.05, 0.05, 0.05))
	anchor:SetVisibility(false)

	local distance = Length(point - character:GetLocation())

	local cable = Cable(character:GetLocation())
	cable:AttachStartTo(character)
	cable:AttachEndTo(anchor)
	cable:SetCableSettings(distance)
	cable:SetRenderingSettings(3, 4, 1)

	-- Accroché à un Titan : le point le suit
	local offset
	if (target and titans[target]) then
		offset = point - target:GetLocation()
	else
		target = nil
	end

	state.hooks[side] = {
		point = point, anchor = anchor, cable = cable,
		target = target, offset = offset,
		length = distance,
	}
end

Events.SubscribeRemote("ODM:Hook", function(player, side, point, target)
	if (side ~= "left" and side ~= "right") then return end
	local state = GetState(player)
	local character = player:GetControlledCharacter()
	if (not character or not state.equipped) then return end

	-- Anti-triche : le point doit être à portée raisonnable
	if (Length(point - character:GetLocation()) > ODM.MaxRange * 1.2) then return end

	CreateHook(state, character, side, point, target)
end)

Events.SubscribeRemote("ODM:Unhook", function(player, side)
	RemoveHook(GetState(player), side)
end)

Events.SubscribeRemote("ODM:Reel", function(player, active)
	GetState(player).reel = (active == true)
end)

---------------------------------------------------------------------
-- Boost de gaz (direction envoyée par le client : caméra + ZQSD)
---------------------------------------------------------------------

Events.SubscribeRemote("ODM:Boost", function(player, direction)
	local state = GetState(player)
	local character = player:GetControlledCharacter()
	if (not character or not state.equipped) then return end
	if (state.gas < ODM.BoostGasCost) then
		return
	end

	local len = Length(direction)
	if (len < 0.01) then return end

	state.gas = state.gas - ODM.BoostGasCost
	character:AddImpulse((direction / len) * ODM.BoostImpulse, true)
	state.boost_until = Now() + ODM.BoostSmokeDuration
end)

---------------------------------------------------------------------
-- Lames : la nuque est à l'arrière haut du Titan, il faut de la vitesse
---------------------------------------------------------------------

local function GetNapeLocation(titan, data, hint_titan, hint_pos)
	-- Position de l'os envoyée par le client, vérifiée : elle doit rester près du Titan
	if (hint_pos and hint_titan == titan) then
		local scale = data.type.scale
		if (Length(hint_pos - titan:GetLocation()) <= 150 * scale) then
			return hint_pos
		end
	end

	local scale = data.type.scale
	local forward = titan:GetRotation():GetForwardVector()
	return titan:GetLocation() + Vector(0, 0, 60 * scale) - forward * (12 * scale)
end

local function PlayTitanAnimation(titan, asset, loop)
	if (not asset) then return end
	pcall(function()
		titan:PlayAnimation(asset, AnimationSlotType.FullBody or "", loop == true, 0.2, 0.2)
	end)
end

local function StopTitanAnimation(titan, asset)
	if (not asset) then return end
	pcall(function() titan:StopAnimation(asset) end)
end

-- Libère la victime d'un Titan (tombé, étourdi ou mort)
local function ReleaseVictim(titan, data)
	local holding = data.holding
	data.holding = nil
	if (not holding) then return end
	StopTitanAnimation(titan, ODM.Animations.eat)
	local state = states[holding.player]
	if (state) then
		state.grabbed_by = nil
		state.struggle = 0
	end
	if (holding.character:IsValid()) then
		pcall(function() holding.character:Detach() end)
		pcall(function() holding.character:SetInputEnabled(true) end)
	end
end

local function StunTitan(titan, data, seconds)
	ReleaseVictim(titan, data)
	data.down_until = Now() + seconds
	pcall(function() titan:SetRagdollMode(true) end)
end

Events.SubscribeRemote("ODM:Slash", function(player, hint_titan, hint_pos)
	local state = GetState(player)
	local character = player:GetControlledCharacter()
	if (not character or not state.equipped) then return end

	-- Attrapé par un Titan : F sert à se débattre
	if (state.grabbed_by) then
		local titan = state.grabbed_by
		local data = titans[titan]
		state.struggle = state.struggle + 1
		if (data and state.struggle >= ODM.StruggleNeeded) then
			StunTitan(titan, data, ODM.StruggleStun)
			Say(player, "<green>[ODM]</> Tu t'es libéré !")
		end
		return
	end

	local now = Now()
	if (now - state.last_slash < ODM.SlashCooldown) then return end
	if (state.reload_at > 0) then return end
	if (state.blades <= 0) then
		return
	end
	state.last_slash = now

	local my_location = character:GetLocation()
	local speed = Length(character:GetVelocity())
	local hit = false

	for titan, data in pairs(titans) do
		if (titan:IsValid() and titan:GetHealth() > 0) then
			local reach = ODM.NapeRadius * (data.type.scale / 5)
			local titan_location = titan:GetLocation()

			if (Length(GetNapeLocation(titan, data, hint_titan, hint_pos) - my_location) <= reach) then
				hit = true
				if (speed >= ODM.MinSlashSpeed) then
					titan:ApplyDamage(data.type.nape_damage or ODM.NapeDamage, "head", nil, nil, player, character)
				else
					-- trop lent : la lame ricoche sur la nuque
					titan:ApplyDamage(ODM.BladeDamage, nil, nil, nil, player, character)
					Say(player, "<red>[ODM]</> Trop lent ! Il faut de la vitesse pour trancher la nuque.")
				end
			elseif (Length(titan_location - my_location) <= reach * 1.5) then
				hit = true
				titan:ApplyDamage(ODM.BladeDamage, nil, nil, nil, player, character)

			end
		end
	end

	if (hit) then
		state.blades = state.blades - 1
		if (state.blades <= 0) then
			Say(player, "<red>[ODM]</> Lames cassées ! Appuie sur B pour changer de lames.")
		end
	end
end)

Events.SubscribeRemote("ODM:Reload", function(player)
	local state = GetState(player)
	if (not state.equipped or state.reload_at > 0) then return end
	if (state.blades >= ODM.BladesMax) then return end
	if (state.spare <= 0) then
		Say(player, "<red>[ODM]</> Plus de lames de rechange.")
		return
	end
	state.reload_at = Now() + ODM.BladeReloadTime
end)

---------------------------------------------------------------------
-- Lances-foudre : projectile explosif qui blesse les Titans dans la zone
---------------------------------------------------------------------

local spears = {} -- [grenade] = instant de lancer

Events.SubscribeRemote("ODM:Spear", function(player, direction)
	local state = GetState(player)
	local character = player:GetControlledCharacter()
	if (not character or not state.equipped) then return end

	local now = Now()
	if (now - state.last_spear < ODM.SpearCooldown) then return end
	if (state.spears <= 0) then
		Say(player, "<red>[ODM]</> Plus de lances-foudre.")
		return
	end

	local len = Length(direction)
	if (len < 0.01) then return end
	local dir = direction / len

	state.last_spear = now
	state.spears = state.spears - 1

	local spear = Grenade(character:GetLocation() + dir * 200 + Vector(0, 0, 60), Rotator())
	spear:SetDamage(ODM.SpearDamage, 20, 500, 1500, 1)
	spear:SetTimeToExplode(ODM.SpearFuse)
	spear:AddImpulse(dir * ODM.SpearThrowForce, true)
	spears[spear] = now
end)

-- Explose au premier contact (on ignore les 0,15 s après le lancer : elle sort de la main)
Grenade.Subscribe("Hit", function(self)
	local thrown_at = spears[self]
	if (thrown_at and Now() - thrown_at > 0.15) then
		spears[self] = nil
		pcall(function() self:Explode() end)
	end
end)

Grenade.Subscribe("Destroy", function(self)
	spears[self] = nil
end)

---------------------------------------------------------------------
-- Titans : types, IA, régénération
---------------------------------------------------------------------

local kills = 0

local function RandomTitanType()
	local total = 0
	for _, t in ipairs(ODM.TitanTypes) do total = total + t.weight end
	local r = math.random() * total
	for _, t in ipairs(ODM.TitanTypes) do
		r = r - t.weight
		if (r <= 0) then return t end
	end
	return ODM.TitanTypes[1]
end

-- Zone de mort visible : une sphère rouge fixée à la nuque du Titan
local function AttachNapeMarker(titan, data)
	local marker = Prop(titan:GetLocation(), Rotator(), "nanos-world::SM_Sphere", CollisionType.NoCollision, false)
	local attached = false
	for _, bone in ipairs(ODM.NapeBones) do
		if (marker:AttachTo(titan, AttachmentRule.SnapToTarget, bone)) then
			attached = true
			break
		end
	end
	if (not attached) then
		marker:Destroy()
		return
	end
	local size = ODM.NapeMarkerSize
	marker:SetScale(Vector(size, size, size))
	pcall(function() marker:SetMaterialColorParameter("Tint", Color(1, 0.05, 0.05)) end)
	data.marker = marker
end

local function RemoveNapeMarker(data)
	if (data.marker and data.marker:IsValid()) then data.marker:Destroy() end
	data.marker = nil
end

local function SpawnTitan(location, titan_type)
	if (not ODM.TitansEnabled) then return nil end
	titan_type = titan_type or RandomTitanType()
	local titan = Character(location, Rotator(0, math.random(0, 359), 0), titan_type.mesh or ODM.TitanMesh,
		CollisionType.Auto, true, titan_type.health)
	titan:SetScale(Vector(titan_type.scale, titan_type.scale, titan_type.scale))
	titan:SetSpeedMultiplier(titan_type.speed)
	if (titan_type.sprint) then
		pcall(function() titan:SetGaitMode(GaitMode.Sprinting) end)
	end
	titan:SetValue("odm_titan", true, true)
	titans[titan] = {
		type = titan_type, last_attack = 0, last_leap = 0, max_health = titan:GetHealth(),
		down_until = 0, holding = nil, hold_until = 0,
	}
	AttachNapeMarker(titan, titans[titan])
	return titan
end

local function CountTitans()
	local n = 0
	for _ in pairs(titans) do n = n + 1 end
	return n
end

local function BossAlive()
	for _, data in pairs(titans) do
		if (data.type.boss) then return true end
	end
	return false
end

local function PlayerCharacters()
	local list = {}
	for _, player in pairs(Player.GetAll()) do
		local character = player:GetControlledCharacter()
		if (character) then list[#list + 1] = character end
	end
	return list
end

local function SpawnNearPlayers(titan_type)
	local list = PlayerCharacters()
	if (#list == 0) then return nil end
	local center = list[math.random(1, #list)]
	local angle = math.rad(math.random(0, 359))
	local distance = (titan_type and titan_type.boss) and 7000 or 4000
	local offset = Vector(math.cos(angle) * distance, math.sin(angle) * distance, 200)
	return SpawnTitan(center:GetLocation() + offset, titan_type)
end

local function Announce(text)
	for _, player in pairs(Player.GetAll()) do Say(player, text) end
end

local function Steam(location, scale)
	local smoke = Particle(location, Rotator(), ODM.SmokeAsset, true, true)
	smoke:SetScale(Vector(scale, scale, scale))
	smoke:SetLifeSpan(ODM.SmokeLifetime)
end

-- Mort d'un Titan : il fume, son corps disparaît lentement, puis un autre arrive
Character.Subscribe("Death", function(self)
	local data = titans[self]
	if (not data) then return end

	ReleaseVictim(self, data)
	RemoveNapeMarker(data)
	kills = kills + 1
	if (data.type.boss) then
		Announce("<green>[ODM]</> Le Titan colossal est tombé !")
	end

	local scale = data.type.scale
	local pulses = 0
	Timer.SetInterval(function()
		pulses = pulses + 1
		if (not self:IsValid() or pulses > ODM.DeathSteamPulses) then return false end
		local jitter = Vector(math.random(-40, 40) * scale, math.random(-40, 40) * scale, math.random(0, 60) * scale)
		Steam(self:GetLocation() + jitter, scale * 0.8)
	end, 400)

	Timer.SetTimeout(function()
		if (not self:IsValid()) then return end
		local s = scale
		Timer.SetInterval(function()
			if (not self:IsValid()) then return false end
			s = s * 0.88
			if (s < 0.3) then
				self:Destroy()
				return false
			end
			self:SetScale(Vector(s, s, s))
		end, 200)
	end, ODM.BodyLinger * 1000)

	-- Remplaçant : le colossal quand assez de Titans sont morts, sinon un Titan normal
	Timer.SetTimeout(function()
		if (kills >= ODM.BossAfterKills and not BossAlive()) then
			kills = 0
			if (SpawnNearPlayers(ODM.BossType)) then
				Announce("<red>[ODM]</> Le Titan colossal apparaît ! Sa vapeur brûle : reste loin et vise la nuque.")
			end
		elseif (CountTitans() < ODM.TitanMax) then
			SpawnNearPlayers()
		end
	end, ODM.TitanRespawnDelay * 1000)
end)

Character.Subscribe("Destroy", function(self)
	local data = titans[self]
	if (data) then
		ReleaseVictim(self, data)
		RemoveNapeMarker(data)
	end
	titans[self] = nil
end)

local function GrabVictim(titan, data, player, victim)
	local state = GetState(player)
	RemoveHook(state, "left")
	RemoveHook(state, "right")
	victim:AttachTo(titan, AttachmentRule.SnapToTarget, "hand_r")
	pcall(function() victim:SetInputEnabled(false) end)
	state.grabbed_by = titan
	state.struggle = 0
	data.holding = { player = player, character = victim }
	data.hold_until = Now() + ODM.EatTime
	PlayTitanAnimation(titan, ODM.Animations.grab, false)
	Timer.SetTimeout(function()
		if (titan:IsValid() and data.holding) then
			PlayTitanAnimation(titan, ODM.Animations.eat, true)
		end
	end, 700)
	Say(player, "<red>[ODM]</> Un Titan t'a attrapé ! Appuie vite sur F pour te débattre !")
end

-- IA des Titans (toutes les 0,5 s)
Timer.SetInterval(function()
	local now = Now()
	local players = Player.GetAll()

	for titan, data in pairs(titans) do
		if (titan:IsValid() and titan:GetHealth() > 0) then
			local titan_type = data.type
			local titan_location = titan:GetLocation()

			-- relevé après une chute
			if (data.down_until > 0 and now >= data.down_until) then
				data.down_until = 0
				pcall(function() titan:SetRagdollMode(false) end)
			end

			-- régénération
			local health = titan:GetHealth()
			if (health < data.max_health) then
				titan:SetHealth(math.min(data.max_health, health + ODM.TitanRegenPerTick))
			end

			-- vapeur brûlante du colossal
			if (titan_type.boss) then
				Steam(titan_location + Vector(0, 0, 40 * titan_type.scale), titan_type.scale * 0.7)
				for _, player in pairs(players) do
					local character = player:GetControlledCharacter()
					if (character and Length(character:GetLocation() - titan_location) <= ODM.BossSteamRadius) then
						character:ApplyDamage(ODM.BossSteamDamage, nil, nil, nil, nil, titan)
					end
				end
			end

			if (data.down_until == 0) then
				if (data.holding) then
					-- victime en cours de dévoration
					local victim = data.holding.character
					if (not victim:IsValid() or victim:GetHealth() <= 0) then
						ReleaseVictim(titan, data)
					elseif (now >= data.hold_until) then
						local eaten_player = data.holding.player
						ReleaseVictim(titan, data)
						victim:ApplyDamage(ODM.EatDamage, nil, nil, nil, nil, titan)
						Say(eaten_player, "<red>[ODM]</> Tu as été mangé...")
					end
				else
					-- cible la plus proche
					local nearest, nearest_player, nearest_dist
					for _, player in pairs(players) do
						local character = player:GetControlledCharacter()
						if (character and character:GetHealth() > 0) then
							local d = Length(character:GetLocation() - titan_location)
							if (not nearest_dist or d < nearest_dist) then
								nearest, nearest_player, nearest_dist = character, player, d
							end
						end
					end

					if (nearest) then
						titan:MoveTo(nearest:GetLocation())
						local ready = now - data.last_attack >= titan_type.attack_cd

						if (titan_type.kind == "sauteur" and nearest_dist > 600 and nearest_dist < 2400
							and now - data.last_leap >= ODM.LeapCooldown) then
							-- bond vers le joueur
							data.last_leap = now
							local flat = nearest:GetLocation() - titan_location
							local flat_len = math.sqrt(flat.X * flat.X + flat.Y * flat.Y)
							if (flat_len > 1) then
								local dir = Vector(flat.X / flat_len, flat.Y / flat_len, 0)
								titan:AddImpulse(dir * ODM.LeapForce + Vector(0, 0, ODM.LeapUp), true)
							end
						elseif (nearest_dist <= titan_type.range and ready) then
							data.last_attack = now
							if (titan_type.kind == "mangeur") then
								if (not states[nearest_player] or not states[nearest_player].grabbed_by) then
									GrabVictim(titan, data, nearest_player, nearest)
								end
							else
								PlayTitanAnimation(titan, ODM.Animations.attack, false)
								nearest:ApplyDamage(titan_type.damage, nil, nil, nil, nil, titan)
							end
						end
					end
				end
			end
		end
	end
end, 500)

Player.Subscribe("Possess", function(player, character)
	Timer.SetTimeout(function()
		if (not character:IsValid()) then return end
		while (CountTitans() < ODM.TitanMax) do
			if (not SpawnNearPlayers()) then break end
		end
	end, 2000)
end)

---------------------------------------------------------------------
-- Boucle principale
---------------------------------------------------------------------

Server.Subscribe("Tick", function(delta_time)
	local now = Now()

	for player, state in pairs(states) do
		local character = player:GetControlledCharacter()

		if (not character or not state.equipped) then
			RemoveHook(state, "left")
			RemoveHook(state, "right")
		else
			local velocity = character:GetVelocity()
			local location = character:GetLocation()


			-- Dégâts de chute : freinage brutal après une chute rapide, sans grappin récent
			if (next(state.hooks) ~= nil) then state.last_hook_time = now end
			local vz = velocity.Z
			if (state.prev_vz < -ODM.FallSafeSpeed and vz > state.prev_vz + 800 and now - state.last_hook_time > 0.4) then
				local impact = -state.prev_vz
				if (state.gas >= ODM.FallGasCost) then
					state.gas = state.gas - ODM.FallGasCost
				else
					character:ApplyDamage(math.floor((impact - ODM.FallSafeSpeed) * ODM.FallDamagePerSpeed))
					Say(player, "<red>[ODM]</> Atterrissage brutal : plus assez de gaz pour amortir.")
				end
			end
			state.prev_vz = vz

			for side, hook in pairs(state.hooks) do
				local release = false

				-- Le grappin suit le Titan auquel il est accroché
				if (hook.target) then
					if (hook.target:IsValid() and hook.target:GetHealth() > 0) then
						hook.point = hook.target:GetLocation() + hook.offset
						if (hook.anchor:IsValid()) then hook.anchor:SetLocation(hook.point) end
					else
						release = true
					end
				end

				if (not release) then
					-- raccourcissement du câble : lent tout seul, rapide avec R (coûte du gaz)
					local rate = ODM.AutoReel
					if (state.reel and state.gas > 0) then
						rate = ODM.ReelSpeed
						state.gas = math.max(0, state.gas - ODM.ReelGasPerSecond * delta_time)
					end
					hook.length = hook.length - rate * delta_time

					local to_point = hook.point - location
					local distance = Length(to_point)

					if (hook.length < ODM.MinDistance or distance < ODM.MinDistance) then
						release = true
					elseif (distance > hook.length) then
						-- câble tendu : on annule la vitesse qui s'éloigne (pendule) et on rappelle
						local toward = to_point / distance
						local outward_speed = -Dot(velocity, toward)
						if (outward_speed > 0) then
							character:AddImpulse(toward * outward_speed, true)
						end
						local pull = math.min((distance - hook.length) * ODM.RopeStiffness, ODM.MaxCorrection)
						character:AddImpulse(toward * pull * delta_time, true)
					end
				end

				if (release) then RemoveHook(state, side) end
			end
		end

		-- Recharge de gaz permanente
		state.gas = math.min(ODM.GasMax, state.gas + ODM.GasRegenPerSecond * delta_time)

		-- Changement de lames
		if (state.reload_at > 0 and now >= state.reload_at) then
			state.reload_at = 0
			state.blades = ODM.BladesMax
			state.spare = math.max(0, state.spare - 1)
		end

		-- Traînée de fumée pendant le boost
		if (character and state.equipped and now < state.boost_until) then
			state.smoke_timer = state.smoke_timer + delta_time
			if (state.smoke_timer >= ODM.SmokeInterval) then
				state.smoke_timer = 0
				local smoke = Particle(character:GetLocation() - Vector(0, 0, 40), Rotator(), ODM.SmokeAsset, true, true)
				smoke:SetScale(Vector(ODM.SmokeScale, ODM.SmokeScale, ODM.SmokeScale))
				smoke:SetLifeSpan(ODM.SmokeLifetime)
			end
		end

		-- État envoyé à l'interface 10 fois par seconde
		state.status_timer = state.status_timer + delta_time
		if (state.equipped and state.status_timer >= 0.1) then
			state.status_timer = 0
			Events.CallRemote("ODM:Status", player, Reliability.Unreliable,
				state.gas, state.blades, state.spare, state.reload_at > 0, state.spears)
		end
	end
end)

Player.Subscribe("Destroy", function(player)
	local state = states[player]
	if (state) then
		RemoveHook(state, "left")
		RemoveHook(state, "right")
	end
	states[player] = nil
end)
