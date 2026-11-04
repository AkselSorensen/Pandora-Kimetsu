-- Quêtes : définitions et progression. Logique pure, sans appel moteur.
-- Un état de quêtes a la forme { [questId] = { status = "active" | "done", progress = n } }.

local Quests = {}

-- reward : kamas = yens (le champ garde son ancien nom), xp = expérience pour monter en grade (Ranks.lua).
Quests.List = {
	premier_pas = {
		id = "premier_pas",
		name = "Rejoindre le Corps",
		description = "Va voir le Kakushi : il t'expliquera comment survivre à la nuit.",
		objective = { type = "talk", target = "kakushi", count = 1 },
		reward = { kamas = 50, xp = 20 },
	},
	lame_nichirin = {
		id = "lame_nichirin",
		name = "Une lame à ton nom",
		description = "Va voir le forgeron et choisis ta lame Nichirin.",
		objective = { type = "talk", target = "forgeron", count = 1 },
		reward = { kamas = 100, xp = 30 },
	},
	concentration = {
		id = "concentration",
		name = "Concentration totale",
		description = "Va t'entraîner auprès de l'instructeur de la Concentration totale.",
		objective = { type = "talk", target = "instructeur", count = 1 },
		reward = { kamas = 50, xp = 30 },
	},
	duel_de_bienvenue = {
		id = "duel_de_bienvenue",
		name = "Épreuve de la Sélection finale",
		description = "Remporte 2 duels contre d'autres pourfendeurs.",
		objective = { type = "kill", target = "player", count = 2 },
		reward = { kamas = 150, xp = 100 },
	},
}

function Quests.Get(questId)
	return Quests.List[questId]
end

-- Accepte une quête. Renvoie true, ou false et une raison.
function Quests.Accept(state, questId)
	local quest = Quests.Get(questId)
	if not quest then
		return false, "unknown"
	end
	if state[questId] then
		return false, "already_taken"
	end
	state[questId] = { status = "active", progress = 0 }
	return true
end

-- Fait avancer les quêtes actives qui correspondent à l'événement.
-- event = { type = "talk" | "kill", target = "..." }
-- Renvoie la liste des ids de quêtes terminées par cet événement.
function Quests.OnEvent(state, event)
	local completed = {}
	for questId, progress in pairs(state) do
		local quest = Quests.Get(questId)
		if progress.status == "active" and quest.objective.type == event.type and quest.objective.target == event.target then
			progress.progress = progress.progress + 1
			if progress.progress >= quest.objective.count then
				progress.status = "done"
				table.insert(completed, questId)
			end
		end
	end
	table.sort(completed)
	return completed
end

return Quests
