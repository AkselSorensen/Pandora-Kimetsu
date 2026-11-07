-- Serveur autoritaire : valide les sorts, les quêtes, les yens, les grades et les rerolls, applique les dégâts.
-- Les PV vivent sur le Character (moteur) ; ce fichier garde le reste de l'état du joueur.

local Classes = Package.Require("Classes.lua")
local Combat = Package.Require("Combat.lua")
local Config = Package.Require("Config.lua")
local Demon = Package.Require("Demon.lua")
local Economy = Package.Require("Economy.lua")
local Items = Package.Require("Items.lua")
local Npcs = Package.Require("Npcs.lua")
local Quests = Package.Require("Quests.lua")
local Ranks = Package.Require("Ranks.lua")
local Persistence = Package.Require("Persistence.lua")
local DayNight = Package.Require("DayNight.lua") -- cycle jour / nuit -- sauvegarde via l'API Kimetsu (server/api)
local Vfx = Package.Require("VfxPlan.lua")
Package.Require("AnimViewer.lua") -- visualiseur d'animations (outil de mise au point)

-- État par joueur, indexé par player:GetID() :
-- { class, camp, demon, cooldowns, kamas (= yens), xp, quests, stats }
-- camp = "slayer" ou "demon" (nil tant que le joueur n'a pas choisi) ; demon = état du système du démon (Shared/Demon.lua), seulement pour un démon
-- stats = bonus issus des rerolls : { maxHp, damagePct, speed }
local players = {}
local pendingSpawns = {}
-- Plateformes du créateur de personnage, par joueur.
local creatorStages = {}
local leaveCreator -- défini plus bas, avec le reste du créateur
local syncWeapon -- défini plus bas, avec giveWeapon
local interruptDevour -- défini plus bas, avec le système du démon

-- Les modules partagés travaillent sur des tables { x, y, z } ; le moteur sur des Vector (X, Y, Z).
local function toPosition(vector)
	return { x = vector.X, y = vector.Y, z = vector.Z }
end

local function randomSpawn()
	local point = Config.SpawnPoints[math.random(#Config.SpawnPoints)]
	return Vector(point.x, point.y, point.z)
end

local function newState()
	local inventory = Items.NewInventory()
	for _, id in ipairs({ "katana", "dague", "talisman", "masque", "bottes", "gants" }) do
		Items.Add(inventory, id, 1)
	end
	Items.Add(inventory, "onigiri", 3)
	Items.Add(inventory, "fiole", 1)
	return { class = Classes.Default, gender = Config.Genders[1], color = 1, skin = nil, nick = nil, cooldowns = {}, kamas = Config.StartingYens or 0, xp = 0, quests = {}, stats = {}, abilityRerolls = 0, abilityPity = {}, inventory = inventory }
end

local function sendRemote(player, eventName, ...)
	Events.CallRemote(eventName, player, Reliability.Reliable, ...)
end

-- Sauvegarde : un changement est écrit en base quelques secondes après, une seule fois (évite les rafales).
local SAVE_DELAY_MS = 3000
local SAVE_EVERY_MS = 60000

local function steamOf(player)
	local ok, id = pcall(function() return player:GetSteamID() end)
	if ok and id and tostring(id) ~= "" and tostring(id) ~= "0" then
		return tostring(id)
	end
	return nil
end

local function savePlayer(player)
	local state = players[player:GetID()]
	if state and state.loaded then
		Persistence.Save(state.steam, state, player:GetControlledCharacter())
	end
end

local function persistDirty(player)
	local state = players[player:GetID()]
	if not state or not state.loaded or state.saveQueued then
		return
	end
	state.saveQueued = true
	Timer.SetTimeout(function()
		state.saveQueued = nil
		if player:IsValid() then
			savePlayer(player)
		end
	end, SAVE_DELAY_MS)
end

-- Envoie le sac et l'équipement au HUD (slot = position dans le sac, 1 à SlotCount).
local function sendInventory(player)
	local state = players[player:GetID()]
	if not state then
		return
	end
	local inv = state.inventory
	local slots = {}
	for slot, entry in pairs(inv.slots) do
		table.insert(slots, { slot = slot, id = entry.id, count = entry.count })
	end
	sendRemote(player, "wakfu:inventory", { slots = slots, equip = inv.equip, weight = Items.Weight(inv) })
	persistDirty(player)
end

-- Grade du joueur : celui de l'échelle de son camp (pourfendeur ou démon), à défaut de celle de sa classe, pour son XP.
local playtimeTotal -- défini plus bas, avec le temps de jeu

-- Grade : un démon suit ses corps mangés et son temps de jeu (ou la Lune attribuée par un admin) ; les autres suivent l'XP.
local function rankOf(state)
	if state.camp == "demon" then
		if state.lune then
			return Ranks.At("demon", state.lune)
		end
		local meals = state.demon and state.demon.totalMeals or 0
		return Ranks.At("demon", Ranks.DemonAutoIndex(meals, playtimeTotal(state) or 0))
	end
	local camp = state.camp and Classes.Camps[state.camp]
	return Ranks.Get(camp and camp.ladder or Classes.Get(state.class).ladder, state.xp)
end

-- Ce que le HUD affiche du système du démon (jauges, palier), ou nil pour un joueur qui n'est pas un démon.
local function demonView(state)
	return state.demon and Demon.View(Config.Demon, state.demon, rankOf(state).index) or nil
end

-- Jauges du démon, seules : renvoyées après chaque tir de technique, repas et pas du temps.
local function sendDemon(player)
	local state = players[player:GetID()]
	if state and state.demon then
		sendRemote(player, "wakfu:demon", demonView(state))
	end
end

-- Envoie au client ce que le HUD affiche : classe, grade, yens, bonus et quêtes.
-- Temps de jeu total du joueur (secondes) : celui de la base, plus la session en cours. nil tant que l'état n'est pas chargé.
playtimeTotal = function(state)
	if not state.loaded then
		return nil
	end
	return (state.playtimeBase or 0) + math.max(0, os.time() - (state.playtimeMark or os.time()))
end

local function sendState(player)
	local state = players[player:GetID()]
	if state then
		sendInventory(player)
		sendRemote(player, "wakfu:state", { name = state.nick or player:GetName(), gender = state.gender, color = state.color, skin = state.skin, class = state.class, camp = state.camp, demon = demonView(state), trail = state.trail or "auto", trailSize = state.trailSize or Config.Vfx.trail.defaultSize, kamas = state.kamas, xp = state.xp, rank = rankOf(state), stats = state.stats, quests = state.quests, abilityRerolls = state.abilityRerolls or 0, abilityPity = state.abilityPity or {}, playtime = playtimeTotal(state) })
	end
end

-- PV max et vitesse : classe + grade + rerolls + équipement. heal remet les PV au maximum (apparition).
local function applyStats(character, state, heal)
	local class = Classes.Get(state.class)
	local gear = Items.GearStats(state.inventory)
	local demonHp = state.demon and Demon.Bonuses(Config.Demon, state.demon).hp or 0
	local nightHp = (state.camp == "demon" and DayNight.IsNight()) and (1 + DayNight.DemonNight.hp / 100) or 1
	local maxHp = math.floor((class.hp + rankOf(state).hp + demonHp + (state.stats.maxHp or 0)) * (1 + gear.endurance / 100) * nightHp)
	local ratio = character:GetMaxHealth() > 0 and character:GetHealth() / character:GetMaxHealth() or 1
	character:SetMaxHealth(maxHp)
	character:SetHealth(heal and maxHp or math.max(1, math.floor(maxHp * ratio)))
	character:SetSpeedMultiplier(1 + ((state.stats.speed or 0) + gear.vitesse) / 100)
	syncWeapon(character, state)
end

-- Applique la classe et les bonus du joueur à son personnage.
local function applyClass(character, state)
	local class = Classes.Get(state.class)
	local mesh = (Config.UseCustomModels and class.model) or class.fallbackModel
	if state.gender == "Femme" and not Config.UseCustomModels then
		mesh = Config.FemaleModel
	end
	local skin = state.skin and Config.Skins[state.skin]
	if skin then
		local ok = pcall(function()
			character:SetMesh(skin)
		end)
		if not ok then
			skin = nil
			character:SetMesh(mesh)
		end
	else
		character:SetMesh(mesh)
	end
	-- Teinte du personnage : le nom du paramètre dépend du mesh, on essaie sans planter.
	local tint = Config.Colors[state.color]
	if tint and not skin then
		pcall(function()
			character:SetMaterialColorParameter("Tint", Color(tint[1], tint[2], tint[3]))
		end)
	end
	applyStats(character, state, true)
end

-- Armes (Melee) tenues en main, par personnage : { id = id d'arme, melee = entité }. Voir Config.Weapons.
local weapons = {}

-- Traînée de l'arme : allumée seulement pendant un coup (événement Attack du Melee) et éteinte à la fin de sa fenêtre, par défaut celle des dégâts
-- de l'arme (damageStart + damageDuration). Deux coups qui s'enchaînent prolongent l'effet : seul le dernier minuteur éteint.
local function flashTrail(character)
	local held = character and character:IsValid() and weapons[character:GetID()]
	if not held or not held.trail or not held.trail:IsValid() then
		return
	end
	local player = character:GetPlayer()
	local state = player and players[player:GetID()]
	if state and not state.trailHinted then -- première attaque : on dit comment choisir la traînée
		state.trailHinted = true
		sendRemote(player, "wakfu:notice", "Touche " .. Config.Vfx.menuKey .. " : choisir la traînée de ton arme et sa taille")
	end
	local def = Config.Weapons.list[held.id]
	local settings = Config.Vfx and Config.Vfx.trail or {}
	local seconds = held.trailSeconds or ((def and def.damageStart or 0) + (def and def.damageDuration or 0.5))
	held.trailSeq = (held.trailSeq or 0) + 1
	local sequence = held.trailSeq
	held.trail:Activate(true)
	if settings.alwaysOn then
		return
	end
	Timer.SetTimeout(function()
		if held.trail and held.trail:IsValid() and held.trailSeq == sequence then
			held.trail:Deactivate()
		end
	end, seconds * 1000)
end

local function giveWeapon(character, weaponId)
	local cfg = Config.Weapons
	if not cfg.enabled then
		return
	end
	-- Un mesh, une animation ou un id inconnu ne doit pas empêcher le serveur de démarrer : on log l'erreur et on continue.
	local ok, err = pcall(function()
		local def = cfg.list[weaponId]
		local old = weapons[character:GetID()]
		if old and old.trail and old.trail:IsValid() then
			old.trail:Destroy()
		end
		if old and old.melee:IsValid() then
			old.melee:Destroy()
		end
		-- Appel de la doc de Melee : avec les arguments en plus de default-weapons, l'arme n'était plus tenue en main.
		-- La pose de la main vient de def.handling (HandlingMode) : une main (SingleHandedMelee) par défaut.
		local handling = HandlingMode[def.handling or "SingleHandedMelee"] or HandlingMode.SingleHandedMelee
		local melee = Melee(character:GetLocation(), Rotator(0, 0, 0), def.mesh, CollisionType.Normal, true, handling, "")
		if cfg.grip then -- réglage commun à toutes les armes (Config.Weapons.grip), relatif à hand_r_socket
			local grip = cfg.grip
			melee:SetAttachmentSettings(Vector(grip.x, grip.y, grip.z), Rotator(grip.pitch, grip.yaw, grip.roll))
		end
		if def.scale then
			melee:SetScale(Vector(def.scale, def.scale, def.scale))
		end
		-- Slot de l'animation : UpperBody n'anime que le haut du corps, FullBody tout le corps (def.slot, UpperBody par défaut).
		local slot = AnimationSlotType[def.slot or "UpperBody"]
		for _, animation in ipairs(def.animations) do
			melee:AddAnimationCharacterUse(animation, def.rate or 1.0, slot)
		end
		melee:SetDamageSettings(def.damageStart, def.damageDuration)
		melee:SetCooldown(def.cooldown)
		melee:SetBaseDamage(def.damage)
		melee:Subscribe("Attack", function(_, attacker)
			flashTrail(attacker)
		end)
		character:PickUp(melee)
		weapons[character:GetID()] = { id = weaponId, melee = melee }
		Console.Log("Arme " .. weaponId .. " en main (personnage " .. tostring(character:GetID()) .. ")")
		-- Contrôle après coup que l'arme est restée en main (journal du serveur) et la remet sinon : le moteur peut la
		-- lâcher pendant l'apparition du joueur.
		Timer.SetTimeout(function()
			if not character:IsValid() or not melee:IsValid() then
				return
			end
			local known, picked = pcall(function()
				return character:GetPicked()
			end)
			if not known then
				return Console.Warn("Arme " .. weaponId .. " : GetPicked indisponible, contrôle impossible")
			end
			if picked == nil or picked:GetID() ~= melee:GetID() then
				Console.Warn("Arme " .. weaponId .. " plus en main après 1 s : on la remet")
				character:PickUp(melee)
			else
				Console.Log("Arme " .. weaponId .. " toujours en main après 1 s")
			end
		end, 1000)
	end)
	if not ok then
		Console.Error("Arme " .. tostring(weaponId) .. " : " .. tostring(err))
	end
end

-- Retire l'arme tenue par ce personnage (l'objet d'inventaire, lui, ne bouge pas).
local function removeWeapon(character)
	local held = weapons[character:GetID()]
	if held and held.trail and held.trail:IsValid() then
		held.trail:Destroy()
	end
	if held and held.melee:IsValid() then
		held.melee:Destroy()
	end
	weapons[character:GetID()] = nil
end

-- Taille de la traînée du joueur (Config.Vfx.trail.sizes) : échelle du composant, point d'attache sur la lame et durée allumée par coup.
local function trailSize(state)
	local settings = Config.Vfx.trail
	for _, size in ipairs(settings.sizes) do
		if size.id == (state.trailSize or settings.defaultSize) then
			return size
		end
	end
	return settings.sizes[1]
end

-- Place la traînée de l'arme tenue selon la taille choisie : valable à la création comme en direct quand le joueur change de taille.
local function placeTrail(held, state)
	local size = trailSize(state)
	local def = Config.Weapons.list[held.id]
	local tip = def and def.tip
	if not tip or tip < 40 then -- pas de mesure, ou une lame qui pend sous la main : repli sur la distance moyenne
		tip = Config.Vfx.trail.defaultTip
	end
	held.trail:SetRelativeLocation(Vector(0, 0, tip * size.tip))
	held.trail:SetScale(Vector(size.scale, size.scale, size.scale))
	held.trailSeconds = size.seconds
end

-- Traînée de l'arme tenue : une Particle attachée au Melee, à la pointe de la lame (Config.Vfx.trail). Elle suit l'animation de l'arme et se
-- recrée quand le joueur change d'arme, de voie ou de choix (state.trail : nil = celle de sa voie, "none" = aucune, ou une traînée de la banque).
local function syncTrail(character, state)
	local held = weapons[character:GetID()]
	if not held or not held.melee:IsValid() then
		return
	end
	local fx = Config.Vfx
	local wanted = fx and fx.enabled and fx.weaponTrail and Vfx.HasAssets() and Vfx.ResolveTrail(state.class, state.trail) or nil
	local wantedId = wanted and wanted.id or nil
	if held.trailId == wantedId and (wanted == nil or (held.trail and held.trail:IsValid())) then
		return
	end
	if held.trail and held.trail:IsValid() then
		held.trail:Destroy()
	end
	held.trail, held.trailId = nil, nil
	if not wanted then
		return
	end
	local ok, result = pcall(function()
		-- Même schéma que la torche de nanos world (sandbox) : auto_destroy = false, attachée à l'arme, décalée le long de la lame (axe Z du mesh).
		-- auto_activate = false : la traînée n'existe que pendant un coup (flashTrail) ; trail.alwaysOn la garde allumée en permanence.
		local particle = Particle(Vector(), Rotator(), wanted.id, false, false)
		particle:AttachTo(held.melee, AttachmentRule.SnapToTarget, "", 0)
		held.trail = particle
		placeTrail(held, state)
		if fx.trail.alwaysOn then
			particle:Activate()
		end
	end)
	if ok then
		held.trailId = wantedId
	else
		if held.trail and held.trail:IsValid() then
			held.trail:Destroy()
		end
		held.trail = nil
		Console.Warn("Traînée " .. wanted.id .. " : " .. tostring(result))
	end
end

Character.Subscribe("Destroy", function(character)
	removeWeapon(character)
end)

-- Arme voulue pour un joueur : celle choisie avec les flèches (Config.WeaponCycle), sinon celle de l'objet équipé dans
-- l'emplacement arme s'il en a une, sinon Config.Weapons.players.
local function wantedWeapon(state)
	local cfg = Config.Weapons
	if not cfg.enabled or state.camp == "demon" then -- un démon se bat avec ses griffes et son sang, pas avec une lame Nichirin
		return false
	end
	if state.cycledWeapon and cfg.list[state.cycledWeapon] then
		return state.cycledWeapon
	end
	local equipped = state.inventory.equip.weapon
	if equipped and cfg.list[equipped] then
		return equipped
	end
	return cfg.players
end

-- Met la bonne arme en main d'un joueur et retire l'autre. Appelé par applyStats, donc après chaque changement d'équipement.
syncWeapon = function(character, state)
	local wanted = wantedWeapon(state)
	local held = weapons[character:GetID()]
	local holding = held ~= nil and held.melee:IsValid()
	if wanted and not (holding and held.id == wanted) then
		giveWeapon(character, wanted)
	elseif not wanted and holding then
		removeWeapon(character)
	end
	syncTrail(character, state)
end

-- Essai des armes (Config.WeaponCycle) : le client demande l'arme suivante (1) ou précédente (-1) de la liste.
Events.SubscribeRemote("wakfu:weaponCycle", function(player, step)
	local cycle = Config.WeaponCycle
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if not (cycle and cycle.enabled and state and character and character:IsValid()) or (step ~= 1 and step ~= -1) or state.camp == "demon" then
		return
	end
	local list, index = cycle.list, 0
	for i, id in ipairs(list) do
		if id == wantedWeapon(state) then
			index = i
		end
	end
	index = index + step
	if index > #list then
		index = 1
	elseif index < 1 then
		index = #list
	end
	state.cycledWeapon = list[index]
	syncWeapon(character, state)
	Console.Log("Arme " .. index .. "/" .. #list .. " : " .. list[index])
end)

-- Arme demandée par un autre package (menu de props, onglet Weapons) : même effet que les flèches, elle prime sur l'équipement.
Events.Subscribe("Wakfu:EquipWeapon", function(player, weaponId)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if state and character and character:IsValid() and Config.Weapons.list[weaponId] and state.camp ~= "demon" then
		state.cycledWeapon = weaponId
		syncWeapon(character, state)
		Console.Log("Arme " .. weaponId .. " équipée depuis le menu de props")
	end
end)

-- Cadavres (Config.Corpses) : le corps d'un joueur mort reste au sol pendant Config.Corpses.lifetime secondes. Un démon peut le dévorer
-- (système du démon, plus bas). Registre par id du Character : { character, label, name, eaten }.
local corpses = {}

local function removeCorpse(id)
	local corpse = corpses[id]
	if not corpse then
		return
	end
	corpses[id] = nil
	pcall(function()
		if corpse.label and corpse.label:IsValid() then
			corpse.label:Destroy()
		end
	end)
	pcall(function()
		if corpse.character:IsValid() then
			corpse.character:Destroy()
		end
	end)
end

-- Laisse le corps mort du joueur au sol : son arme disparaît avec lui, un nom flottant le signale, et il disparaît après sa durée de vie.
local function leaveCorpse(player, character, state)
	local name = state.nick or player:GetName()
	local id = character:GetID()
	removeWeapon(character)
	pcall(function()
		character:SetRagdollMode(true) -- le corps reste étendu où il est tombé
	end)
	local label
	if Config.Corpses.label then
		local location = character:GetLocation()
		label = TextRender(location + Vector(0, 0, 80), Rotator(0, 0, 0), "† " .. name, 20, Color(0.82, 0.76, 0.7), TextRenderRenderingType.UnlitCameraAligned)
	end
	corpses[id] = { character = character, label = label, name = name, eaten = false }
	character:SetValue("corpse", true, true)
	Timer.SetTimeout(function()
		removeCorpse(id)
	end, Config.Corpses.lifetime * 1000)
end

-- Fait (ré)apparaître le joueur à un point d'apparition du Domaine avec sa classe actuelle. Un joueur mort laisse son corps au sol et revient dans
-- un corps neuf ; un démon part en cendres et réapparaît dans le même corps (Config.Corpses.demonsLeaveBody).
local function spawnPlayer(player)
	local state = players[player:GetID()]
	if not state then
		return
	end

	local character = player:GetControlledCharacter()
	if not character then
		local id = player:GetID()
		pendingSpawns[id] = (pendingSpawns[id] or 0) + 1
		if pendingSpawns[id] <= 20 then
			Timer.SetTimeout(function()
				if players[id] then spawnPlayer(player) end
			end, 250)
			return
		end
		pendingSpawns[id] = nil
	else
		pendingSpawns[player:GetID()] = nil
	end
	if Config.Corpses.enabled and character and character:IsValid() and character:IsDead() and (state.camp ~= "demon" or Config.Corpses.demonsLeaveBody) then
		leaveCorpse(player, character, state)
		character = nil
	end
	if character then
		character:Respawn(randomSpawn(), Rotator(0, 0, 0))
	else
		character = Character(randomSpawn(), Rotator(0, 0, 0), Classes.Get(state.class).fallbackModel)
		player:Possess(character)
	end
	removeWeapon(character) -- après une mort, l'ancienne arme est restée au sol : applyClass en remet une si besoin
	applyClass(character, state)
	sendState(player)
end

-- Donne de l'XP à un joueur ; un nouveau grade améliore ses PV max et le fait savoir. L'appelant renvoie l'état au HUD.
local function addXp(player, amount)
	local state = players[player:GetID()]
	if not state or type(amount) ~= "number" or amount <= 0 then
		return
	end
	local total, promoted = Ranks.AddXp(Classes.Get(state.class).ladder, state.xp, amount)
	state.xp = total
	if promoted then
		local character = player:GetControlledCharacter()
		if character and character:IsValid() then
			applyStats(character, state, false)
		end
		sendRemote(player, "wakfu:notice", "Nouveau grade : " .. promoted.name)
	end
end

-- Applique les événements de quête et prévient le joueur des quêtes terminées.
local function questEvent(player, event)
	local state = players[player:GetID()]
	if not state then
		return
	end
	for _, questId in ipairs(Quests.OnEvent(state.quests, event)) do
		local quest = Quests.Get(questId)
		state.kamas = Economy.Reward(state.kamas, quest.reward.kamas or 0)
		addXp(player, quest.reward.xp)
		sendRemote(player, "wakfu:questDone", questId)
	end
	sendState(player)
end

-- Corps des PNJ civils, par id : { character, label }. Un démon qui en dévore un le fait disparaître le temps de son retour.
local civilBodies = {}

-- Les PNJ du Domaine prennent corps dans le monde : un personnage immobile et un nom flottant.
local function spawnNpcs()
	for _, npc in ipairs(Npcs.List) do
		if npc.manual then
			goto continue
		end
		local location = Vector(npc.position.x, npc.position.y, npc.position.z)
		-- Ils regardent vers le centre du Domaine, là où apparaissent les joueurs.
		local character = Character(location, Rotator(0, npc.yaw or 180, 0), npc.mesh)
		character:SetInvulnerable(true)
		character:SetValue("npcId", npc.id, true)
		local weaponId = Config.Weapons.npcs[npc.id] or (npc.showcase and Config.Weapons.showcase)
		if weaponId then
			giveWeapon(character, weaponId)
		end
		local label = TextRender(location + Vector(0, 0, 125), Rotator(0, 0, 0), npc.name, 22, Color(1, 0.75, 0.1), TextRenderRenderingType.UnlitCameraAligned)
		if npc.civil then
			civilBodies[npc.id] = { character = character, label = label }
		end
		::continue::
	end
end

Events.Subscribe("PropsMenu:EntitySpawned", function(entity, npcId)
	if not entity or not npcId then return end
	local npc = Npcs.Get(npcId)
	if not npc or not npc.manual then return end
	entity:SetInvulnerable(true)
	entity:SetValue("npcId", npcId, true)
	Npcs.RegisterEntity(npcId, entity)
	local label = TextRender(entity:GetLocation() + Vector(0, 0, 125), Rotator(0, 0, 0), npc.name, 22, Color(1, 0.75, 0.1), TextRenderRenderingType.UnlitCameraAligned)
	Character.Subscribe("Destroy", function(character)
		if character == entity then
			Npcs.UnregisterEntity(character)
			if label and label:IsValid() then label:Destroy() end
		end
	end)
end)

spawnNpcs()

-- Remet l'état sauvegardé en place : camp, job, nom, XP, apparence, sac et équipement, PV.
local function restoreFromSave(player, state, data)
	local saved = data.character
	if not saved then
		return
	end
	state.characterId = saved.character_id
	state.camp = Persistence.CampOfFaction[saved.faction_id] or state.camp
	state.demon = state.camp == "demon" and Demon.New(Config.Demon) or nil
	if saved.job and Classes.Get(saved.job) then
		state.class = saved.job
	end
	-- La voie doit appartenir au camp : sinon on prend la voie de départ de ce camp.
	if state.camp and Classes.CampOf(state.class) ~= state.camp then
		state.class = Classes.Camps[state.camp].defaultClass
	end
	if saved.name and saved.name ~= "" then
		state.nick = saved.name
	end
	state.xp = saved.xp or 0
	state.playtimeBase = data.playtime or 0
	if state.demon then
		state.demon.totalMeals = (saved.game and saved.game.totalMeals) or 0
	end
	state.lune = saved.game and saved.game.lune or nil
	local game = saved.game or {}
	state.kamas = game.kamas or state.kamas
	state.stats = game.stats or {}
	state.abilityRerolls = game.abilityRerolls or 0
	state.abilityPity = game.abilityPity or {}
	state.quests = game.quests or {}
	state.trail = game.trail
	state.trailSize = game.trailSize
	state.level = saved.level or 1
	local look = saved.appearance
	if look then
		state.gender = look.gender or state.gender
		state.color = look.color or state.color
		state.skin = look.skin or state.skin
	end

	local inv = Items.NewInventory()
	for _, row in ipairs(data.items or {}) do
		if Items.List[row.code] then
			if row.equip_slot then
				inv.equip[row.equip_slot] = row.code
			elseif row.slot then
				inv.slots[row.slot] = { id = row.code, count = row.count }
			else
				Items.Add(inv, row.code, row.count)
			end
		end
	end
	state.inventory = inv

	local character = player:GetControlledCharacter()
	if character and character:IsValid() then
		applyClass(character, state)
		if saved.hp and saved.max_hp then
			pcall(function()
				character:SetMaxHealth(saved.max_hp)
				character:SetHealth(math.max(1, math.min(saved.hp, saved.max_hp)))
			end)
		end
	end
end

-- Charge le personnage du joueur depuis l'API. Si l'API ne répond pas, le joueur reste sans sauvegarde :
-- rien n'est écrit en base tant que l'état n'a pas été chargé.
local function loadPlayer(player)
	local state = players[player:GetID()]
	if not state then
		return
	end
	-- Sans sauvegarde disponible, le joueur joue quand même : on ouvre l'écran de bienvenue sans enregistrement.
	local function giveUp(reason)
		if not player:IsValid() or players[player:GetID()] ~= state then
			return
		end
		Console.Warn("[kimetsu-api] " .. reason .. " : jeu sans sauvegarde pour " .. player:GetName())
		if state.welcomePending then
			state.welcomePending = nil
			sendState(player)
			sendRemote(player, "wakfu:openWelcome")
			pcall(function() Chat.SendMessage(player, "Sauvegarde indisponible : ta progression ne sera pas enregistrée") end)
		end
	end
	if not state.steam or not Persistence.Enabled() then
		return giveUp("pas de sauvegarde configurée")
	end
	Persistence.Login(state.steam, player:GetName(), function(ok)
		if not ok then
			return giveUp("connexion à l'API impossible")
		end
		if not player:IsValid() or players[player:GetID()] ~= state then
			return
		end
		Persistence.Load(state.steam, function(okLoad, data)
			if not okLoad or not data then
				return giveUp("chargement impossible")
			end
			if not player:IsValid() or players[player:GetID()] ~= state then
				return
			end
			restoreFromSave(player, state, data)
			state.loaded = true
			state.playtimeMark = os.time() -- début du comptage du temps de jeu
			sendState(player)
			sendInventory(player)
			if state.welcomePending then
				state.welcomePending = nil
				sendRemote(player, "wakfu:openWelcome")
			end
		end)
	end)
end

local function onPlayerSpawn(player)
	players[player:GetID()] = newState()
	players[player:GetID()].steam = steamOf(player)
	players[player:GetID()].player = player
	spawnPlayer(player)
	loadPlayer(player)
end

-- Sauvegarde périodique de tous les joueurs chargés.
Timer.SetInterval(function()
	for _, state in pairs(players) do
		if state.loaded and state.player and state.player:IsValid() then
			savePlayer(state.player)
		end
	end
end, SAVE_EVERY_MS)

Player.Subscribe("Spawn", onPlayerSpawn)

-- Le client a fini de charger : il peut maintenant recevoir l'état pour son HUD. Un joueur qui n'a pas encore choisi son camp voit l'écran de choix.
Player.Subscribe("Ready", function(player)
	local state = players[player:GetID()]
	print("DBG ready state=" .. tostring(state) .. " loaded=" .. tostring(state and state.loaded))
	if not state then
		return
	end
	sendState(player)
	Events.CallRemote("Kimetsu:Time", player, Reliability.Reliable, DayNight.Time)
	-- L'écran de bienvenue attend la sauvegarde : un joueur déjà enregistré ne revoit pas le choix du camp.
	if state.loaded or not Persistence.Enabled() then
		sendRemote(player, "wakfu:openWelcome") -- l'écran de bienvenue ouvre ensuite le choix du camp s'il n'est pas fait
	else
		state.welcomePending = true
	end
end)

-- Rechargement du package : les joueurs déjà connectés repartent d'un état neuf.
Package.Subscribe("Load", function()
	for _, player in pairs(Player.GetPairs()) do
		if not players[player:GetID()] then
			onPlayerSpawn(player)
		end
	end
end)

Player.Subscribe("Destroy", function(player)
	if creatorStages[player:GetID()] then
		leaveCreator(player)
	end
	interruptDevour(player)
	savePlayer(player) -- dernière sauvegarde avant de quitter, le personnage existe encore
	local character = player:GetControlledCharacter()
	if character then
		character:Destroy()
	end
	players[player:GetID()] = nil
end)

-- Un coup reçu (arme ou technique) : un démon touché ne se régénère plus pendant le délai de combat et lâche sa proie.
Character.Subscribe("TakeDamage", function(character)
	local player = character:GetPlayer()
	local state = player and players[player:GetID()]
	if state and state.demon then
		Demon.Hit(state.demon)
		interruptDevour(player, "Tu as été frappé")
	end
end)

-- Mort d'un joueur : le tueur avance ses quêtes, la victime réapparaît après un délai.
Character.Subscribe("Death", function(character, _, _, _, _, instigator)
	local victim = character:GetPlayer()
	if not victim then
		return
	end
	interruptDevour(victim)

	if instigator and instigator:IsValid() and instigator:GetID() ~= victim:GetID() then
		addXp(instigator, Config.Xp.kill)
		questEvent(instigator, { type = "kill", target = "player" })
	end

	Timer.SetTimeout(function()
		if victim:IsValid() and character:IsValid() then
			spawnPlayer(victim)
		end
	end, Config.RespawnDelay * 1000)
end)

-- Effets visuels d'une technique : envoyés aux joueurs proches, qui les jouent chez eux (Client/VfxPlayer.lua). Rien n'est envoyé
-- tant qu'aucun effet n'est cuit sur ce serveur.
local function broadcastFx(character, spell)
	local fx = Config.Vfx
	if not (fx and fx.enabled and Vfx.HasAssets()) then
		return
	end
	local location = character:GetLocation()
	local yaw = character:GetRotation().Yaw
	local origin = toPosition(location)
	for _, other in pairs(Player.GetPairs()) do
		local otherCharacter = other:GetControlledCharacter()
		if otherCharacter and otherCharacter:IsValid() and Combat.InRange(origin, toPosition(otherCharacter:GetLocation()), fx.radius) then
			sendRemote(other, "wakfu:fx", spell.id, location.X, location.Y, location.Z, yaw)
		end
	end
end

-- Le client demande le sort n°index de sa classe.
Events.SubscribeRemote("wakfu:castIndex", function(player, index)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if not state or not character or character:IsDead() or type(index) ~= "number" then
		return
	end

	local spell = Classes.GetSpell(state.class, index)
	if not spell then
		return
	end

	-- Horloge du serveur en secondes entières : suffisant pour des cooldowns de plusieurs secondes.
	local now = Server.GetTime()
	if not Combat.CanCast(state.cooldowns, spell, now) then
		return
	end
	-- Un démon paie ses techniques en sang, et la plus puissante attend un palier de puissance (Config.Demon.unlock).
	if state.demon then
		local paid, reason, need = Demon.TryCast(Config.Demon, state.demon, index)
		if not paid then
			if reason == "locked" then
				sendRemote(player, "wakfu:notice", "Technique verrouillée : il faut le palier « " .. Config.Demon.tiers[need].name .. " »")
			else
				sendRemote(player, "wakfu:notice", "Pas assez de sang (" .. need .. " requis)")
			end
			return
		end
		Demon.Hit(state.demon)
		interruptDevour(player, "Tu as lancé une technique")
		sendDemon(player)
	end
	state.cooldowns[spell.id] = now
	sendRemote(player, "wakfu:cast", spell.id, spell.cooldown)
	broadcastFx(character, spell)

	-- Un sort de soin rend des PV à son lanceur ; sans dégâts il s'arrête là.
	if spell.heal then
		character:SetHealth(Combat.Heal(character:GetHealth(), character:GetMaxHealth(), spell.heal))
	end
	if not spell.damage then
		return
	end

	local origin = toPosition(character:GetLocation())
	local demonPct = state.demon and Demon.Bonuses(Config.Demon, state.demon).damagePct or 0
	local nightPct = (state.camp == "demon" and DayNight.IsNight()) and DayNight.DemonNight.damage or 0
	local damage = Combat.Damage(spell, (state.stats.damagePct or 0) + Items.GearStats(state.inventory).force + demonPct + nightPct)
	for _, target in pairs(Player.GetPairs()) do
		local targetCharacter = target:GetControlledCharacter()
		local targetState = players[target:GetID()]
		if target:GetID() ~= player:GetID() and targetState and targetCharacter and not targetCharacter:IsDead() then
			if Combat.InRange(origin, toPosition(targetCharacter:GetLocation()), spell.range) then
				targetCharacter:ApplyDamage(damage, "", DamageType.Unknown, Vector(0, 0, 0), player)
				if targetState.demon then -- un démon touché ne se régénère plus et lâche sa proie
					Demon.Hit(targetState.demon)
					interruptDevour(target, "Tu as été frappé")
				end
			end
		end
	end
end)

-- Le joueur appuie sur interagir : on renvoie le PNJ le plus proche et ses quêtes disponibles.
Events.SubscribeRemote("wakfu:interact", function(player)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if not state or not character then
		return
	end

	local npc = Npcs.Nearest(toPosition(character:GetLocation()))
	if not npc then
		return
	end

	questEvent(player, { type = "talk", target = npc.id })

	-- Le Créateur ouvre directement l'écran de création, sans dialogue.
	if Npcs.HasService(npc, "creator") then
		sendRemote(player, "wakfu:openCreator")
		return
	end

	-- Le Maître des respirations ouvre directement l'écran de reroll de classe.
	if Npcs.HasService(npc, "classreroll") then
		sendRemote(player, "wakfu:openClassReroll")
		return
	end

	-- Le PNJ Yushiro ouvre le panneau de sélection des trois re-rolls.
	if Npcs.HasService(npc, "rerollselector") then
		sendRemote(player, "wakfu:openRerollSelector")
		return
	end

	-- Le forgeron ouvre directement la forge des lames Nichirin.
	if Npcs.HasService(npc, "forge") then
		sendRemote(player, "wakfu:openForge")
		return
	end

	local offered = {}
	for _, questId in ipairs(npc.quests) do
		if state.quests[questId] == nil then
			table.insert(offered, questId)
		end
	end
	sendRemote(player, "wakfu:dialog", npc.id, npc.name, npc.dialogue, offered, npc.services)
end)

-- Accepter une quête auprès d'un PNJ qui la propose, à portée.
Events.SubscribeRemote("wakfu:acceptQuest", function(player, questId)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if not state or not character or type(questId) ~= "string" then
		return
	end

	local npc = Npcs.Nearest(toPosition(character:GetLocation()))
	if not npc then
		return
	end

	local isOffered = false
	for _, id in ipairs(npc.quests) do
		if id == questId then
			isOffered = true
		end
	end
	if not isOffered then
		return
	end

	local ok = Quests.Accept(state.quests, questId)
	if ok then
		sendRemote(player, "wakfu:questAccepted", questId)
		sendState(player)
	end
end)

-- Reroll des stats auprès de l'instructeur (entraînement) : coûte des yens, tire de nouveaux bonus.
Events.SubscribeRemote("wakfu:reroll", function(player)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if not state or not character then
		return
	end

	local npc = Npcs.Nearest(toPosition(character:GetLocation()))
	if not npc or not Npcs.HasService(npc, "reroll") then
		return
	end

	local remaining = Economy.Spend(state.kamas, Economy.RerollCost)
	if remaining == nil then
		sendRemote(player, "wakfu:rerollFailed", "not_enough_kamas")
		return
	end

	state.kamas = remaining
	state.stats = Economy.RollStats(math.random)
	spawnPlayer(player)
	sendRemote(player, "wakfu:rerolled", state.stats, state.kamas)
end)

-- Reroll de capacité : une nouvelle classe remplace la voie actuelle, sans toucher au camp, au grade ou à l'équipement.
Events.SubscribeRemote("wakfu:abilityReroll", function(player)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if not state or not character or not state.camp then return sendRemote(player, "wakfu:abilityRerollFailed", "unavailable") end
	local npc = Npcs.Nearest(toPosition(character:GetLocation()))
	if not npc or not Npcs.HasService(npc, "rerollselector") then return sendRemote(player, "wakfu:abilityRerollFailed", "unavailable") end
	if (state.abilityRerolls or 0) < 1 then
		sendRemote(player, "wakfu:abilityRerollFailed", "no_reroll")
		return
	end
	local remaining = Economy.Spend(state.kamas, Economy.AbilityReroll.cost)
	if not remaining then
		sendRemote(player, "wakfu:abilityRerollFailed", "not_enough_kamas")
		return
	end
	local pool = {}
	for name in pairs(Classes.List) do
		if name ~= state.class and Classes.CampOf(name) == state.camp then table.insert(pool, name) end
	end
	if #pool == 0 then return sendRemote(player, "wakfu:abilityRerollFailed", "unavailable") end
	state.abilityPity = state.abilityPity or {}
	-- Une pitié qui a atteint son seuil garantit sa capacité (si elle est disponible dans le camp), sinon tirage au hasard.
	local forced = Economy.PityGuarantee(state.abilityPity)
	local selected
	if forced and Classes.Get(forced) and Classes.CampOf(forced) == state.camp and forced ~= state.class then
		selected = forced
	else
		selected = pool[math.random(#pool)]
	end
	local rarity = Classes.Get(selected).rarity or "common"
	local won = Economy.PityCaps[selected] and selected or nil
	state.kamas = remaining
	state.abilityRerolls = (state.abilityRerolls or 0) - 1 -- un reroll disponible est consommé
	Economy.UpdatePity(state.abilityPity, won)
	state.class = selected
	applyClass(character, state)
	sendRemote(player, "wakfu:abilityRerolled", { class = selected, rarity = rarity, rerolls = state.abilityRerolls, pity = state.abilityPity, kamas = state.kamas })
	sendState(player)
	sendInventory(player)
	notice(player, "Nouvelle capacité : " .. Classes.Get(selected).name)
end)

-- Choix de classe, effectif à la prochaine réapparition.
Events.SubscribeRemote("wakfu:chooseClass", function(player, className)
	local state = players[player:GetID()]
	-- Le camp est un choix unique : une voie de l'autre camp (ou toute voie tant que le camp n'est pas choisi) est refusée.
	if state and type(className) == "string" and Classes.Get(className) and state.camp and Classes.CampOf(className) == state.camp then
		state.class = className
		sendState(player)
		persistDirty(player)
	end
end)

-- Créateur de personnage : chaque choix est validé ici, puis appliqué tout de suite au personnage.
Events.SubscribeRemote("wakfu:create", function(player, className, gender, colorIndex, nick, skin)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if not state or not character or character:IsDead() then
		return
	end
	if type(className) ~= "string" or not Classes.Get(className) or not state.camp or Classes.CampOf(className) ~= state.camp then
		return
	end
	local validGender = false
	for _, g in ipairs(Config.Genders) do
		if g == gender then
			validGender = true
		end
	end
	if not validGender or type(colorIndex) ~= "number" or not Config.Colors[colorIndex] then
		return
	end

	state.class = className
	state.gender = gender
	state.color = colorIndex
	state.skin = type(skin) == "string" and Config.Skins[skin] and skin or nil
	if type(nick) == "string" then
		nick = nick:gsub("[%c<>]", ""):sub(1, Config.MaxNameLength)
		state.nick = nick ~= "" and nick or nil
	end

	applyClass(character, state)
	sendState(player)
	persistDirty(player)
	if state.characterId then
		Persistence.SaveAppearance(state)
	end
end)

-- Créateur : le personnage monte sur une plateforme bleue haut dans le ciel, loin de tout décor,
-- et revient à sa place en sortant. Une plateforme par joueur, détruite à la sortie.
local CREATOR_HEIGHT = 40000 -- cm au-dessus de la carte

-- Teinte un mesh ; le nom du paramètre de couleur dépend du matériau, on essaie sans planter.
local function tintMesh(mesh, color, alpha)
	pcall(function()
		if alpha then
			mesh:SetMaterial("nanos-world::M_NanosTranslucent", 0)
		end
		mesh:SetMaterialColorParameter("Tint", Color(color[1], color[2], color[3], alpha or 1))
	end)
end

leaveCreator = function(player)
	local stage = creatorStages[player:GetID()]
	if not stage then
		return
	end
	creatorStages[player:GetID()] = nil
	if stage.timer then
		Timer.ClearInterval(stage.timer)
	end
	for _, part in ipairs(stage.parts) do
		if part:IsValid() then
			part:Destroy()
		end
	end
	local character = player:GetControlledCharacter()
	if character and character:IsValid() then
		character:SetInvulnerable(false)
		character:SetLocation(stage.back)
	end
end

Events.SubscribeRemote("wakfu:creatorEnter", function(player, cameraYaw)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if not state or not character or character:IsDead() or type(cameraYaw) ~= "number" or creatorStages[player:GetID()] then
		return
	end

	local base = Vector(200000 + (player:GetID() % 50) * 2000, 0, CREATOR_HEIGHT)
	local platform = StaticMesh(base, Rotator(0, 0, 0), "nanos-world::SM_Cylinder")
	platform:SetScale(Vector(3.2, 3.2, 0.1))
	-- Simple disque bleu translucide sous le personnage.
	tintMesh(platform, { 0.09, 0.72, 0.93 }, 0.35)

	local stage = { parts = { platform }, back = character:GetLocation() }
	creatorStages[player:GetID()] = stage

	character:SetInvulnerable(true)
	character:SetLocation(base + Vector(0, 0, 130))
	-- Le personnage fait face à la caméra, qui reste derrière lui.
	character:SetRotation(Rotator(0, cameraYaw + 180, 0))
end)

Events.SubscribeRemote("wakfu:creatorAim", function(player, cameraYaw)
	local character = player:GetControlledCharacter()
	if creatorStages[player:GetID()] and character and character:IsValid() and type(cameraYaw) == "number" then
		character:SetRotation(Rotator(0, cameraYaw + 180, 0))
	end
end)

Events.SubscribeRemote("wakfu:creatorExit", leaveCreator)

-- Inventaire : le client demande, le serveur valide et renvoie le sac mis à jour.
local GIVE_RANGE = 500 -- cm

local function notice(player, text)
	sendRemote(player, "wakfu:notice", text)
end

local function withInventory(player)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	if state and character and character:IsValid() and not character:IsDead() then
		return state, character
	end
end

local function slotNumber(value)
	if type(value) == "number" and value >= 1 and value <= Items.SlotCount and value == math.floor(value) then
		return value
	end
end

local function refreshInventory(player, state, character)
	applyStats(character, state, false)
	sendInventory(player)
end

Events.SubscribeRemote("wakfu:invUse", function(player, slot)
	local state, character = withInventory(player)
	slot = slotNumber(slot)
	local entry = state and slot and state.inventory.slots[slot]
	if not entry then
		return
	end
	local def = Items.Get(entry.id)
	if def.heal then
		if character:GetHealth() >= character:GetMaxHealth() then
			return notice(player, "Tes PV sont déjà au maximum")
		end
		Items.Take(state.inventory, slot, 1)
		character:SetHealth(math.min(character:GetMaxHealth(), character:GetHealth() + def.heal))
		notice(player, def.name .. " : +" .. def.heal .. " PV")
	elseif not Items.Equip(state.inventory, slot) then
		return
	end
	refreshInventory(player, state, character)
end)

Events.SubscribeRemote("wakfu:invUnequip", function(player, equipSlot)
	local state, character = withInventory(player)
	if not state or type(equipSlot) ~= "string" or not state.inventory.equip[equipSlot] then
		return
	end
	if not Items.Unequip(state.inventory, equipSlot) then
		return notice(player, "Ton sac est plein")
	end
	refreshInventory(player, state, character)
end)

Events.SubscribeRemote("wakfu:invMove", function(player, from, to)
	local state, character = withInventory(player)
	from, to = slotNumber(from), slotNumber(to)
	if state and from and to and Items.Swap(state.inventory, from, to) then
		refreshInventory(player, state, character)
	end
end)

-- Jeter et supprimer retirent tout le slot ; jeter garde une trace différente dans le message.
local function removeSlot(verb)
	return function(player, slot)
		local state, character = withInventory(player)
		slot = slotNumber(slot)
		local entry = state and slot and state.inventory.slots[slot]
		if not entry then
			return
		end
		local def = Items.Get(entry.id)
		Items.Take(state.inventory, slot)
		notice(player, def.name .. (entry.count > 1 and " x" .. entry.count or "") .. " " .. verb)
		refreshInventory(player, state, character)
	end
end

Events.SubscribeRemote("wakfu:invDrop", removeSlot("jeté"))
Events.SubscribeRemote("wakfu:invDelete", removeSlot("supprimé"))

Events.SubscribeRemote("wakfu:invGive", function(player, slot)
	local state, character = withInventory(player)
	slot = slotNumber(slot)
	local entry = state and slot and state.inventory.slots[slot]
	if not entry then
		return
	end
	local here = character:GetLocation()
	local best, bestDistance
	for _, other in pairs(Player.GetPairs()) do
		local otherState, otherCharacter = withInventory(other)
		if other:GetID() ~= player:GetID() and otherState then
			local distance = here:Distance(otherCharacter:GetLocation())
			if distance <= GIVE_RANGE and (not bestDistance or distance < bestDistance) then
				best, bestDistance = other, distance
			end
		end
	end
	if not best then
		return notice(player, "Personne à proximité")
	end
	local otherState, otherCharacter = withInventory(best)
	local def = Items.Get(entry.id)
	if not Items.Add(otherState.inventory, entry.id, entry.count) then
		return notice(player, "Son sac est plein ou trop lourd")
	end
	Items.Take(state.inventory, slot)
	notice(player, def.name .. " donné à " .. (otherState.nick or best:GetName()))
	notice(best, (state.nick or player:GetName()) .. " t'a donné : " .. def.name)
	refreshInventory(player, state, character)
	refreshInventory(best, otherState, otherCharacter)
end)

-- Forge : le joueur choisit une lame Nichirin auprès du forgeron ; elle entre dans son sac contre des yens.
Events.SubscribeRemote("wakfu:forgeBuy", function(player, bladeId)
	local state, character = withInventory(player)
	local def = type(bladeId) == "string" and Items.Get(bladeId)
	if not state or not def or not def.blade then
		return
	end
	local npc = Npcs.Nearest(toPosition(character:GetLocation()))
	if not npc or not Npcs.HasService(npc, "forge") then
		return notice(player, "Le forgeron est trop loin")
	end
	local cost = Config.Forge.cost
	local remaining = Economy.Spend(state.kamas, cost)
	if remaining == nil then
		return notice(player, "Il te faut " .. cost .. " yens pour cette lame")
	end
	if not Items.Add(state.inventory, bladeId, 1) then
		return notice(player, "Ton sac est plein ou trop lourd")
	end
	state.kamas = remaining
	notice(player, def.name .. " forgée (-" .. cost .. " yens)")
	sendState(player)
end)

-- Traînée de l'arme : le joueur choisit dans le menu celle qui suit la pointe de ses armes (Config.Vfx, Vfx.ResolveTrail).
Events.SubscribeRemote("wakfu:trailChoose", function(player, choice)
	local state, character = withInventory(player)
	if not state or not Vfx.IsTrailChoice(choice) then
		return
	end
	state.trail = choice ~= "auto" and choice or nil
	syncTrail(character, state)
	local label = choice == "none" and "aucune" or choice == "auto" and "celle de ta voie" or choice
	for _, trail in ipairs(Vfx.TrailList()) do
		if trail.id == choice then
			label = trail.group .. " " .. trail.name
		end
	end
	notice(player, "Traînée : " .. label)
	sendState(player)
end)

-- Taille de la traînée : un des réglages de Config.Vfx.trail.sizes, appliqué tout de suite à la traînée de l'arme tenue.
Events.SubscribeRemote("wakfu:trailSize", function(player, sizeId)
	local state, character = withInventory(player)
	if not state or type(sizeId) ~= "string" then
		return
	end
	local chosen
	for _, size in ipairs(Config.Vfx.trail.sizes) do
		if size.id == sizeId then
			chosen = size
		end
	end
	if not chosen then
		return
	end
	state.trailSize = sizeId
	local held = weapons[character:GetID()]
	if held and held.trail and held.trail:IsValid() then
		placeTrail(held, state)
	end
	notice(player, "Taille de la traînée : " .. chosen.label)
	sendState(player)
end)

-- Reroll de classe : on change de classe sans toucher au nom, à l'apparence ni à l'équipement.
Events.SubscribeRemote("wakfu:classReroll", function(player, className)
	local state, character = withInventory(player)
	if not state or type(className) ~= "string" or not Classes.Get(className) or not state.camp then
		return
	end
	if Classes.CampOf(className) ~= state.camp then
		return notice(player, "Le camp est un choix définitif pour ce personnage")
	end
	if state.class == className then
		return notice(player, "Tu suis déjà cette voie : " .. Classes.Get(className).name)
	end
	state.class = className
	applyClass(character, state)
	sendState(player)
	sendInventory(player)
	notice(player, "Nouvelle voie : " .. Classes.Get(className).name)
end)

-- ===== Système du démon (Shared/Demon.lua, réglages dans Config.Demon) =====

-- Choix du camp à l'arrivée : unique par personnage. Le camp donne la voie de départ (Eau pour un pourfendeur, la voie sanguinaire pour un démon),
-- l'échelle de grades et, pour un démon, l'état du système (sang, chair, âmes).
local function applyCamp(player, state, camp)
	local def = Classes.Camps[camp]
	state.camp = camp
	state.abilityRerolls = 1 -- un reroll offert à la création du personnage
	state.class = def.defaultClass
	state.demon = camp == "demon" and Demon.New(Config.Demon) or nil
	state.cycledWeapon = nil
	local character = player:GetControlledCharacter()
	if character and character:IsValid() then
		applyClass(character, state)
	end
	sendState(player)
	sendInventory(player)
	-- Premier choix de camp : le personnage est créé en base, puis sauvegardé comme les autres changements.
	if state.loaded and not state.characterId and state.steam then
		Persistence.CreateCharacter(state.steam, {
			name = player:GetName(),
			faction_id = Persistence.FactionOfCamp[camp],
			job = state.class,
		}, function(characterId)
			if characterId and players[player:GetID()] == state then
				state.characterId = characterId
				persistDirty(player)
			end
		end)
	end
end

Events.SubscribeRemote("wakfu:chooseCamp", function(player, camp)
	local state = players[player:GetID()]
	if not state or state.camp or type(camp) ~= "string" or not Classes.Camps[camp] then
		return
	end
	if camp == "demon" and not Config.Demon.enabled then
		return notice(player, "Le camp des démons est fermé pour l'instant")
	end
	applyCamp(player, state, camp)
	notice(player, "Tu es " .. (camp == "demon" and "un démon : " .. Config.Demon.devourKey .. " pour dévorer une proie" or "un pourfendeur du Corps"))
end)

-- Dévoration : un démon proche d'un civil maintient le geste quelques secondes ; un coup reçu, une technique lancée, la mort ou un pas de trop
-- l'interrompent. Les civils dévorés disparaissent le temps de leur retour (Config.Demon.devour.civilRespawn).
local devouring = {} -- id de joueur -> { npcId, elapsed, timer }
local consumedCivils = {} -- id de PNJ -> true pendant son absence

local function setCivilPresent(npcId, present)
	local body = civilBodies[npcId]
	if not body then
		return
	end
	consumedCivils[npcId] = (not present) or nil
	pcall(function()
		if body.character:IsValid() then
			body.character:SetVisibility(present)
		end
	end)
	pcall(function()
		if body.label:IsValid() then
			body.label:SetVisibility(present)
		end
	end)
end

-- Pose du démon qui mange : accroupi (et une animation en boucle si Config.Demon.devour.animation en nomme une). Chaque appel est protégé :
-- un nom de posture ou d'animation inconnu ne doit pas empêcher le repas.
local function eatingPose(character, eating)
	pcall(function()
		character:SetStanceMode(eating and StanceMode.Crouching or StanceMode.Standing)
	end)
	local animation = Config.Demon.devour.animation
	if animation then
		pcall(function()
			if eating then
				character:PlayAnimation(animation, AnimationSlotType.FullBody, true, 0.2, 0.2)
			else
				character:StopAnimation(animation)
			end
		end)
	end
end

local function stopDevour(playerId)
	local run = devouring[playerId]
	if run then
		devouring[playerId] = nil
		Timer.ClearInterval(run.timer)
		if run.character and run.character:IsValid() then
			eatingPose(run.character, false)
		end
	end
	return run
end

-- Interrompt le repas en cours du joueur, s'il y en a un ; reason (facultative) s'affiche dans un message.
interruptDevour = function(player, reason)
	if not stopDevour(player:GetID()) then
		return
	end
	sendRemote(player, "wakfu:devourStop", "")
	if reason then
		notice(player, "Repas interrompu : " .. reason)
	end
end

-- Proies : un cadavre (kind "corpse", id = id du corps) ou un civil (kind "civil", npc = le PNJ). preyPosition renvoie sa position actuelle, ou
-- nil s'il a disparu ; nearestPrey, la plus proche à portée.
local function preyPosition(prey)
	if prey.kind == "corpse" then
		local corpse = corpses[prey.id]
		if corpse and not corpse.eaten and corpse.character:IsValid() then
			return toPosition(corpse.character:GetLocation())
		end
		return nil
	end
	return prey.npc.position
end

local function nearestPrey(position, range)
	local best, bestDistance
	local civil = Npcs.NearestCivil(position, range, consumedCivils)
	if civil then
		best, bestDistance = { kind = "civil", id = civil.id, name = civil.name, npc = civil }, Combat.DistanceSquared(position, civil.position)
	end
	for id, corpse in pairs(corpses) do
		if not corpse.eaten and corpse.character:IsValid() then
			local distance = Combat.DistanceSquared(position, toPosition(corpse.character:GetLocation()))
			if distance <= range * range and (not bestDistance or distance < bestDistance) then
				best, bestDistance = { kind = "corpse", id = id, name = "Cadavre de " .. corpse.name }, distance
			end
		end
	end
	return best
end

local function mealLimitNotice(player, state, cap)
	notice(player, "Limite de repas du jour atteinte (" .. state.demon.meals .. "/" .. cap .. ") : monte en grade pour en dévorer plus")
end

local function finishDevour(player, prey)
	local state = players[player:GetID()]
	local character = player:GetControlledCharacter()
	stopDevour(player:GetID())
	sendRemote(player, "wakfu:devourStop", "")
	if not state or not state.demon or not character or not character:IsValid() then
		return
	end
	-- Un autre démon a pu prendre la proie pendant le geste.
	if prey.kind == "civil" then
		if consumedCivils[prey.id] then
			return notice(player, "Quelqu'un a déjà dévoré cette proie")
		end
	elseif not preyPosition(prey) then
		return notice(player, "Quelqu'un a déjà dévoré ce cadavre")
	end
	local allowed, _, cap = Demon.CanEat(Config.Demon, state.demon, rankOf(state).index, prey.kind)
	if not allowed then
		return mealLimitNotice(player, state, cap)
	end
	local result = Demon.Consume(Config.Demon, state.demon, prey.kind)
	if prey.kind == "civil" then
		setCivilPresent(prey.id, false)
		Timer.SetTimeout(function()
			setCivilPresent(prey.id, true)
		end, Config.Demon.devour.civilRespawn * 1000)
	else
		corpses[prey.id].eaten = true
		removeCorpse(prey.id) -- le corps est dévoré : il disparaît
	end
	if result.tierUp then
		applyStats(character, state, false) -- les PV max montent avec le palier
	end
	character:SetHealth(Combat.Heal(character:GetHealth(), character:GetMaxHealth(), math.floor(character:GetMaxHealth() * result.heal)))
	local text = prey.name .. " dévoré : chair +" .. result.flesh .. ", âmes +" .. result.souls
	if result.tierUp then
		text = text .. " · palier « " .. Config.Demon.tiers[result.tier].name .. " »"
	end
	notice(player, text)
	if result.xp and result.xp > 0 then
		addXp(player, result.xp)
	end
	sendState(player)
end

Events.SubscribeRemote("wakfu:devour", function(player)
	local state, character = withInventory(player)
	local cfg = Config.Demon
	if not state or not state.demon or not cfg.enabled or devouring[player:GetID()] then
		return
	end
	local prey = nearestPrey(toPosition(character:GetLocation()), cfg.devour.range)
	if not prey then
		return notice(player, "Aucune proie à portée")
	end
	local allowed, _, cap = Demon.CanEat(cfg, state.demon, rankOf(state).index, prey.kind)
	if not allowed then
		return mealLimitNotice(player, state, cap)
	end
	local id, step = player:GetID(), 0.25
	local run = { prey = prey, elapsed = 0, character = character }
	devouring[id] = run
	-- Le HUD montre le gain attendu (jauges hachurées, pastille) : chair, âmes, PV rendus en % des PV max, XP.
	local source = cfg.sources[prey.kind]
	sendRemote(player, "wakfu:devourStart", prey.name, cfg.devour.seconds, { flesh = source.flesh, souls = source.souls, heal = math.floor(source.heal * 100 + 0.5), xp = source.xp or 0 })
	eatingPose(character, true)
	run.timer = Timer.SetInterval(function()
		if not player:IsValid() then
			return stopDevour(id)
		end
		local current = player:GetControlledCharacter()
		if not current or not current:IsValid() or current:IsDead() then
			return interruptDevour(player)
		end
		local at = preyPosition(prey)
		if not at then
			return interruptDevour(player, "la proie a disparu")
		end
		if not Combat.InRange(toPosition(current:GetLocation()), at, cfg.devour.range * 1.5) then
			return interruptDevour(player, "tu t'es éloigné de ta proie")
		end
		run.elapsed = run.elapsed + step
		if run.elapsed >= cfg.devour.seconds then
			finishDevour(player, prey)
		end
	end, step * 1000)
end)

-- Le temps du démon avance d'une seconde à la fois : sang qui remonte, chair qui se vide, faim, régénération passive hors combat.
local DEMON_TICK = 1
Timer.SetInterval(function()
	for _, player in pairs(Player.GetPairs()) do
		local state = players[player:GetID()]
		local character = player:GetControlledCharacter()
		if state and state.demon and character and character:IsValid() and not character:IsDead() then
			local step = Demon.Tick(Config.Demon, state.demon, DEMON_TICK, { sun = false })
			local maxHp = character:GetMaxHealth()
			if step.heal > 0 and character:GetHealth() < maxHp then
				character:SetHealth(Combat.Heal(character:GetHealth(), maxHp, math.max(1, math.floor(maxHp * step.heal))))
			end
			if step.hunger then
				applyStats(character, state, false)
				notice(player, "La faim te ronge : tu retombes au palier « " .. Config.Demon.tiers[step.hunger.to].name .. " »")
			end
			sendDemon(player)
		end
	end
end, DEMON_TICK * 1000)

-- Remise à zéro du camp d'un joueur (support, produit de boutique) : appelée par un autre package, par exemple nanos-admin ou pandora-store,
-- avec Events.Call("Wakfu:ResetCamp", player). Le joueur revoit l'écran de choix.
Events.Subscribe("Wakfu:ResetCamp", function(player)
	local state = players[player:GetID()]
	if not state then
		return
	end
	interruptDevour(player)
	state.camp, state.demon, state.cycledWeapon = nil, nil, nil
	state.class = Classes.Default
	local character = player:GetControlledCharacter()
	if character and character:IsValid() then
		applyClass(character, state)
	end
	sendState(player)
	sendRemote(player, "wakfu:openCamp")
end)

-- Commandes admin (nanos-admin/Server/KimetsuCommands.lua) : rerolls et changement de camp.
Events.Subscribe("Kimetsu:Admin:GiveRerolls", function(player, amount)
	local state = players[player:GetID()]
	if not state or not state.loaded or type(amount) ~= "number" then
		return
	end
	state.abilityRerolls = math.max(0, (state.abilityRerolls or 0) + amount)
	persistDirty(player)
	sendState(player)
end)

-- Changer de camp : la classe revient à la voie par défaut du nouveau camp ; le personnage garde son nom, son apparence et son équipement.
Events.Subscribe("Kimetsu:Admin:SetCamp", function(player, camp)
	local state = players[player:GetID()]
	if not state or not state.loaded or not Classes.Camps[camp] or state.camp == camp then
		return
	end
	state.camp = camp
	state.class = Classes.Camps[camp].defaultClass
	state.demon = camp == "demon" and Demon.New(Config.Demon) or nil
	state.cycledWeapon = nil
	local character = player:GetControlledCharacter()
	if character and character:IsValid() then
		applyClass(character, state)
	end
	persistDirty(player)
	sendState(player)
	sendInventory(player)
end)


-- Cycle jour / nuit : l'heure est diffusée, et les démons changent de force quand la nuit tombe ou se lève.
-- L'ombre est mesurée par le client du démon (Trace n'existe pas côté serveur) et envoyée ici.
Events.SubscribeRemote("Kimetsu:Shade", function(player, shaded)
	local state = players[player:GetID()]
	if state and state.camp == "demon" then
		state.shaded = shaded == true
	end
end)

Timer.SetInterval(function()
	local changed = DayNight.Advance(DayNight.TICK_SECONDS)
	Events.BroadcastRemote("Kimetsu:Time", Reliability.Reliable, DayNight.Time)
	if changed then
		for _, state in pairs(players) do
			local player = state.player
			if state.loaded and state.camp == "demon" and player and player:IsValid() then
				local character = player:GetControlledCharacter()
				if character and character:IsValid() and not character:IsDead() then
					applyStats(character, state, false)
				end
			end
		end
	end
end, DayNight.TICK_SECONDS * 1000)

-- Démons au soleil : brûlure avec flammes, sauf à l'abri (quelque chose au-dessus de la tête).
Timer.SetInterval(function()
	if DayNight.IsNight() then return end
	for _, state in pairs(players) do
		local player = state.player
		if state.camp == "demon" and player and player:IsValid() then
			local character = player:GetControlledCharacter()
			if character and character:IsValid() and not character:IsDead() and not state.shaded then
				character:ApplyDamage(DayNight.Burn.damage, "", DamageType.Unknown, Vector(0, 0, 0), nil)
				local flame = Particle(character:GetLocation() + Vector(0, 0, 80), Rotator(), "nanos-world::P_Fire", false)
				Timer.SetTimeout(function()
					pcall(function() flame:Destroy() end)
				end, DayNight.Burn.interval * 1000 + 500)
			end
		end
	end
end, DayNight.Burn.interval * 1000)

-- Commande admin !time (nanos-admin) : change l'heure et met à jour les démons.
Events.Subscribe("Kimetsu:Admin:SetTime", function(mode)
	DayNight.SetMode(mode)
	Events.BroadcastRemote("Kimetsu:Time", Reliability.Reliable, DayNight.Time)
	for _, state in pairs(players) do
		local player = state.player
		if state.loaded and state.camp == "demon" and player and player:IsValid() then
			local character = player:GetControlledCharacter()
			if character and character:IsValid() and not character:IsDead() then
				applyStats(character, state, false)
			end
		end
	end
end)

-- Grade démon : la montée est automatique (corps mangés et temps de jeu), contrôlée toutes les 30 secondes.
local function checkDemonGrades()
	for _, state in pairs(players) do
		local player = state.player
		if state.loaded and state.camp == "demon" and player and player:IsValid() then
			local grade = rankOf(state)
			if state.gradeIndex ~= grade.index then
				local old = state.gradeIndex
				state.gradeIndex = grade.index
				local character = player:GetControlledCharacter()
				if character and character:IsValid() and not character:IsDead() then
					applyStats(character, state, false)
				end
				sendState(player)
				if old then
					pcall(function() Chat.SendMessage(player, "Nouveau grade : " .. grade.name) end)
				end
			end
		end
	end
end
Timer.SetInterval(checkDemonGrades, 30000)

-- Commande admin !lune (nanos-admin) : attribue une Lune (index dans l'échelle démon) ; 0 la retire.
Events.Subscribe("Kimetsu:Admin:SetLune", function(player, index)
	local state = players[player:GetID()]
	if not state or not state.loaded or state.camp ~= "demon" then return end
	local steps = Ranks.Ladders.demon
	if index == 0 then
		state.lune = nil
	elseif type(index) == "number" and steps[index] and steps[index].manual then
		state.lune = index
	else
		return
	end
	state.gradeIndex = nil
	persistDirty(player)
	checkDemonGrades()
end)
