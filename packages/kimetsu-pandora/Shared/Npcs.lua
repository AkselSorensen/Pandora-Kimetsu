-- PNJ du Corps des Pourfendeurs : position, dialogue, quêtes proposées et services.

-- En jeu : Package.Require (Nanos World). Hors jeu (tests) : require classique.
local Combat = Package and Package.Require("Combat.lua") or require("Shared.Combat")
local Config = Package and Package.Require("Config.lua") or require("Shared.Config")

local Npcs = {}

Npcs.InteractDistance = 300 -- cm

-- services : reroll = entraînement (nouveaux bonus), creator = apparence, classreroll = style de respiration, forge = lames Nichirin.
Npcs.List = {
	{
		id = "kakushi",
		name = "Kakushi",
		position = { x = 200, y = 0, z = 100 },
		mesh = "nanos-world::SK_ClassicMale",
		dialogue = "Le Corps a besoin de bras. Ici, on ne demande pas d'où tu viens : on demande combien de démons tu as arrêtés.",
		quests = { "premier_pas", "lame_nichirin", "concentration", "duel_de_bienvenue" },
		services = {},
	},
	{
		id = "instructeur",
		name = "Instructeur de la Concentration totale",
		position = { x = -200, y = 300, z = 100 },
		mesh = "nanos-world::SK_Male",
		dialogue = "Respire sans t'arrêter, jour et nuit. Tu veux retenter ta chance sur tes aptitudes ? L'entraînement coûte 50 yens.",
		quests = {},
		services = { "reroll" },
	},
	{
		id = "tailleur",
		name = "Tailleur du Corps",
		position = { x = 0, y = -300, z = 100 },
		mesh = "nanos-world::SK_Female",
		dialogue = "Change ton apparence, ton style ou ton nom quand tu veux.",
		quests = {},
		services = { "creator" },
	},
	{
		id = "maitre_respirations",
		name = "Maître des respirations",
		position = { x = -400, y = -200, z = 100 },
		mesh = "nanos-world::SK_Mannequin",
		dialogue = "Chaque souffle a sa voie. Change de style sans perdre ton personnage ; le camp, lui, ne se change pas.",
		quests = {},
		services = { "classreroll" },
	},
	{
		id = "forgeron",
		name = "Forgeron de lames Nichirin",
		position = { x = 400, y = -250, z = 100 },
		mesh = "nanos-world::SK_Male",
		dialogue = "Une lame Nichirin ne ment jamais : elle prend la couleur de celui qui la tient. Choisis la tienne.",
		quests = {},
		services = { "forge" },
	},
}

-- Civils du Domaine (civil = true) : des villageois sans service ni quête. Un démon peut les dévorer (touche Config.Demon.devourKey) ;
-- ils reviennent après Config.Demon.devour.civilRespawn secondes.
local CIVILS = {
	{ id = "civil_villageois", name = "Villageois", x = 700, y = 500, mesh = "nanos-world::SK_Male", dialogue = "Les nuits sont longues, ici. On dit que quelque chose rôde." },
	{ id = "civil_marchande", name = "Marchande de thé", x = -700, y = -400, mesh = "nanos-world::SK_Female", dialogue = "Un thé chaud ? Rentre avant la tombée de la nuit, c'est plus prudent." },
	{ id = "civil_bucheron", name = "Bûcheron", x = 1000, y = -300, mesh = "nanos-world::SK_ClassicMale", dialogue = "J'ai entendu des cris du côté de la forêt, hier soir." },
	{ id = "civil_paysanne", name = "Paysanne", x = -900, y = 300, mesh = "nanos-world::SK_Female", dialogue = "Mon mari n'est pas rentré des champs. Tu l'as vu ?" },
}

for _, civil in ipairs(CIVILS) do
	table.insert(Npcs.List, {
		id = civil.id,
		name = civil.name,
		position = { x = civil.x, y = civil.y, z = 100 },
		mesh = civil.mesh,
		dialogue = civil.dialogue,
		quests = {},
		services = {},
		civil = true,
	})
end

-- Galerie : un PNJ par personnage du pack pandora-demonslayer (Config.Skins), par ordre alphabétique,
-- alignés sur l'axe X à partir de Config.Showcase. Ce sont des figurants : ni quête ni service.
local SHOWCASE_PACK = "pandora-demonslayer::"

local function addShowcase()
	local names = {}
	for name, mesh in pairs(Config.Skins) do
		if mesh:sub(1, #SHOWCASE_PACK) == SHOWCASE_PACK then
			table.insert(names, name)
		end
	end
	table.sort(names)

	local show = Config.Showcase
	local startX = show.x - (#names - 1) * show.spacing / 2
	for i, name in ipairs(names) do
		local mesh = Config.Skins[name]
		table.insert(Npcs.List, {
			id = "demonslayer_" .. mesh:sub(#SHOWCASE_PACK + 4):lower(),
			name = name,
			position = { x = startX + (i - 1) * show.spacing, y = show.y, z = show.z },
			yaw = show.yaw,
			mesh = mesh,
			dialogue = "Je suis " .. name .. ".",
			quests = {},
			services = {},
			showcase = true,
		})
	end
end

addShowcase()

-- Renvoie le PNJ le plus proche de la position, s'il est à portée d'interaction, sinon nil.
function Npcs.Nearest(position)
	local best, bestDistance = nil, nil
	local limit = Npcs.InteractDistance * Npcs.InteractDistance
	for _, npc in ipairs(Npcs.List) do
		local distance = Combat.DistanceSquared(position, npc.position)
		if distance <= limit and (bestDistance == nil or distance < bestDistance) then
			best, bestDistance = npc, distance
		end
	end
	return best
end

-- Civil le plus proche de la position dans la portée (cm), hors ceux de la liste skip ({ [id] = true }), sinon nil.
function Npcs.NearestCivil(position, range, skip)
	local best, bestDistance = nil, nil
	local limit = range * range
	for _, npc in ipairs(Npcs.List) do
		if npc.civil and not (skip and skip[npc.id]) then
			local distance = Combat.DistanceSquared(position, npc.position)
			if distance <= limit and (bestDistance == nil or distance < bestDistance) then
				best, bestDistance = npc, distance
			end
		end
	end
	return best
end

-- Vrai si le PNJ rend le service donné.
function Npcs.HasService(npc, service)
	for _, offered in ipairs(npc.services) do
		if offered == service then
			return true
		end
	end
	return false
end

-- Renvoie le PNJ d'id donné, ou nil.
function Npcs.Get(npcId)
	for _, npc in ipairs(Npcs.List) do
		if npc.id == npcId then
			return npc
		end
	end
	return nil
end

return Npcs
