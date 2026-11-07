-- Sauvegarde côté serveur via l'API Kimetsu (server/api du dépôt). Le serveur nanos ne parle jamais à la base :
-- il appelle l'API en HTTP. Un échec est signalé dans la console et ne bloque jamais le jeu.
-- Un joueur n'est sauvegardé qu'une fois chargé (state.loaded) : tant que la base n'a pas répondu, rien n'est écrit,
-- pour ne pas écraser un vrai personnage par l'état par défaut.

-- Définit la globale KimetsuApi (voir ServerConfig.example.lua). Sans ce fichier, la sauvegarde reste désactivée.
pcall(Package.Require, "ServerConfig.lua")
KimetsuApi = KimetsuApi or { ApiUrl = "", ServerKey = "" }

local Persistence = {}

local host, base = nil, ""
if type(KimetsuApi) == "table" and type(KimetsuApi.ApiUrl) == "string" then
	host, base = KimetsuApi.ApiUrl:match("^(https?://[^/]+)(.*)$")
	base = (base or ""):gsub("/$", "")
end

-- Vrai si une adresse et une clé sont configurées (sinon le jeu tourne sans sauvegarde).
function Persistence.Enabled()
	return host ~= nil and type(KimetsuApi) == "table" and type(KimetsuApi.ServerKey) == "string" and KimetsuApi.ServerKey ~= ""
end

local FACTION_OF_CAMP = { slayer = 1, demon = 2 }
local CAMP_OF_FACTION = { [1] = "slayer", [2] = "demon" }
local inventoryBusy = {} -- SteamID -> true pendant un envoi d'inventaire
local inventoryPending = {} -- SteamID -> dernier inventaire à envoyer

Persistence.CampOfFaction = CAMP_OF_FACTION
Persistence.FactionOfCamp = FACTION_OF_CAMP

local function decode(text)
	if type(text) ~= "string" or text == "" then
		return nil
	end
	local ok, data = pcall(function() return JSON.parse(text) end)
	return ok and data or nil
end

-- callback(ok, data, status). Ne lève jamais d'erreur.
function Persistence.Request(method, path, body, callback)
	if not host or KimetsuApi.ServerKey == "" then
		if callback then callback(false, nil, 0) end
		return
	end
	local ok, err = pcall(function()
		HTTP.RequestAsync(host, base .. path, method, body and JSON.stringify(body) or "", "application/json", false,
			{ ["X-API-Key"] = KimetsuApi.ServerKey },
			function(status, data)
				local good = status >= 200 and status < 300
				if not good then
					Console.Warn("[kimetsu-api] " .. method .. " " .. path .. " -> " .. tostring(status))
				end
				if callback then callback(good, decode(data), status) end
			end)
	end)
	if not ok then
		Console.Warn("[kimetsu-api] requête impossible : " .. tostring(err))
		if callback then callback(false, nil, 0) end
	end
end

-- Crée le joueur s'il n'existe pas encore (et son inventaire). callback(ok)
function Persistence.Login(steam, displayName, callback)
	Persistence.Request("POST", "/players/" .. steam .. "/login", { display_name = displayName }, function(ok)
		if callback then callback(ok) end
	end)
end

-- Charge le personnage actif et l'inventaire. callback(ok, { character = row | nil, items = list })
function Persistence.Load(steam, callback)
	Persistence.Request("GET", "/players/" .. steam, nil, function(ok, data)
		if not ok or not data then
			if callback then callback(false) end
			return
		end
		local playtime = data.player and data.player.playtime_seconds or 0
		local character = nil
		for _, row in ipairs(data.characters or {}) do
			if row.is_active then character = row break end
		end
		character = character or (data.characters and data.characters[1]) or nil
		if not character then
			if callback then callback(true, { character = nil, items = {}, playtime = playtime }) end
			return
		end
		Persistence.Request("GET", "/players/" .. steam .. "/inventory", nil, function(okInv, invData)
			if callback then callback(okInv, { character = character, items = okInv and invData and invData.items or {}, playtime = playtime }) end
		end)
	end)
end

-- Crée le personnage au choix du camp. callback(characterId | nil)
function Persistence.CreateCharacter(steam, data, callback)
	Persistence.Request("POST", "/players/" .. steam .. "/characters", data, function(ok, res)
		if callback then callback(ok and res and res.character_id or nil) end
	end)
end

-- Sauvegarde l'état du personnage actif : job, PV, niveau, expérience, nom.
function Persistence.SaveCharacter(state, character)
	if not state.characterId then
		return
	end
	local hp, maxHp = nil, nil
	if character and character:IsValid() then
		pcall(function() hp = math.floor(character:GetHealth()) maxHp = math.floor(character:GetMaxHealth()) end)
	end
	Persistence.Request("PUT", "/characters/" .. state.characterId .. "/state", {
		name = state.nick,
		job = state.class,
		faction_id = Persistence.FactionOfCamp[state.camp],
		hp = hp,
		max_hp = maxHp,
		level = state.level or 1,
		xp = state.xp or 0,
		game = {
			kamas = state.kamas,
			stats = state.stats,
			abilityRerolls = state.abilityRerolls,
			abilityPity = state.abilityPity,
			quests = state.quests,
			trail = state.trail,
			trailSize = state.trailSize,
		},
	}, nil)
end

-- Sauvegarde l'apparence : sexe, couleur, peau.
function Persistence.SaveAppearance(state)
	if not state.characterId then
		return
	end
	Persistence.Request("PUT", "/characters/" .. state.characterId .. "/appearance", {
		appearance = { gender = state.gender, color = state.color, skin = state.skin },
	}, nil)
end

-- Remplace l'inventaire en base. Les envois sont sérialisés par joueur : le dernier état gagne.
function Persistence.SaveInventory(steam, state)
	local items = {}
	local inv = state.inventory
	for slot, entry in pairs(inv.slots) do
		table.insert(items, { code = entry.id, count = entry.count, slot = slot })
	end
	for equipSlot, id in pairs(inv.equip) do
		table.insert(items, { code = id, count = 1, equip_slot = equipSlot })
	end

	local function send(payload)
		inventoryBusy[steam] = true
		Persistence.Request("PUT", "/players/" .. steam .. "/inventory", { items = payload }, function()
			inventoryBusy[steam] = nil
			local nextPayload = inventoryPending[steam]
			inventoryPending[steam] = nil
			if nextPayload then
				send(nextPayload)
			end
		end)
	end

	if inventoryBusy[steam] then
		inventoryPending[steam] = items
	else
		send(items)
	end
end

-- Sauvegarde complète d'un joueur chargé.
-- Temps de jeu total du joueur : on envoie le temps écoulé depuis la dernière sauvegarde (state.playtimeMark).
function Persistence.SavePlaytime(steam, state)
	local now = os.time()
	local mark = state.playtimeMark
	state.playtimeMark = now
	if not mark then
		return
	end
	local seconds = math.min(86400, math.max(0, now - mark))
	state.playtimeBase = (state.playtimeBase or 0) + seconds
	if seconds > 0 then
		Persistence.Request("PUT", "/players/" .. steam .. "/playtime", { seconds = seconds }, nil)
	end
end

function Persistence.Save(steam, state, character)
	if not steam or not state or not state.loaded then
		return
	end
	Persistence.SavePlaytime(steam, state)
	Persistence.SaveCharacter(state, character)
	Persistence.SaveAppearance(state)
	Persistence.SaveInventory(steam, state)
end

return Persistence
