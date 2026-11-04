-- Visualiseur d'animations, côté serveur : le client demande, le serveur joue l'animation sur le personnage du joueur
-- (les autres joueurs la voient aussi) et note dans le journal les animations retenues ou buggées.
-- Pour récupérer les noms : chercher « Animation retenue » dans .logs/NanosWorldCore.log du serveur.

local Config = Package.Require("Config.lua")

if not Config.AnimViewer.enabled then
	return
end

local SLOTS = {
	UpperBody = AnimationSlotType.UpperBody,
	FullBody = AnimationSlotType.FullBody,
	Head = AnimationSlotType.Head,
}

local MARK_LABELS = {
	keep = "Animation retenue",
	bug = "Animation bugguée",
	clear = "Animation retirée de la liste",
}

-- Même forme qu'une référence d'asset nanos : pack::Nom (lettres, chiffres, _ et -).
local function validId(id)
	return type(id) == "string" and #id <= 120 and id:match("^[%w_%-]+::[%w_]+$") ~= nil
end

local function controlled(player)
	local character = player:GetControlledCharacter()
	if character and character:IsValid() then
		return character
	end
end

Events.SubscribeRemote("wakfu:animPlay", function(player, id, slot, loop, rate)
	local character = controlled(player)
	if not character or not validId(id) or not SLOTS[slot] then
		return
	end
	rate = type(rate) == "number" and math.min(3, math.max(0.1, rate)) or 1
	local ok, err = pcall(function()
		character:PlayAnimation(id, SLOTS[slot], loop == true, 0.25, 0.25, rate, true)
	end)
	if ok then
		Console.Log(string.format("Animation jouée : %s (%s, boucle %s, x%.2f)", id, slot, tostring(loop == true), rate))
	else
		Console.Error("Animation " .. id .. " : " .. tostring(err))
	end
end)

Events.SubscribeRemote("wakfu:animStop", function(player, id)
	local character = controlled(player)
	if not character or not validId(id) then
		return
	end
	local ok, err = pcall(function()
		character:StopAnimation(id)
	end)
	if not ok then
		Console.Error("Arrêt de l'animation " .. id .. " : " .. tostring(err))
	end
end)

Events.SubscribeRemote("wakfu:animMark", function(player, id, mark)
	if validId(id) and MARK_LABELS[mark] then
		Console.Log(MARK_LABELS[mark] .. " : " .. id)
	end
end)
