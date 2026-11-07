-- Yens et rerolls de stats (entraînement). Logique pure : le serveur fournit le générateur aléatoire.
-- La monnaie s'appelle encore « kamas » dans le code (champ state.kamas, reward.kamas) ; le joueur, lui, voit des yens.

local Economy = {}

Economy.RerollCost = 50

-- Reroll de capacité : les classes seront affectées à une rareté définitive plus tard.
Economy.AbilityReroll = {
	cost = 50,
	rarityWeights = { common = 92, rare = 7, epic = 0.9, mythic = 0.1, pandorium = 0 },
	pity = { rare = 20, epic = 80, mythic = 250, pandorium = 2000 },
}

-- Plages de bonus possibles à chaque reroll (en pourcentage ou en points).
Economy.RerollRanges = {
	maxHp = { min = 0, max = 200 },
	damagePct = { min = -5, max = 15 },
	speed = { min = 0, max = 10 },
}

-- Dépense des yens. Renvoie le nouveau solde, ou nil si le solde est insuffisant.
function Economy.Spend(kamas, cost)
	if kamas < cost then
		return nil
	end
	return kamas - cost
end

-- Tire de nouveaux bonus de stats. rng(min, max) doit renvoyer un entier dans [min, max].
function Economy.RollStats(rng)
	local stats = {}
	for name, range in pairs(Economy.RerollRanges) do
		stats[name] = rng(range.min, range.max)
	end
	return stats
end

-- Ajoute les yens d'une récompense.
function Economy.Reward(kamas, amount)
	return kamas + amount
end

-- Pitié du reroll de capacité : une pitié par capacité de la liste (celles de l'interface). Chaque reroll :
-- la capacité obtenue repart à zéro, toutes les autres gagnent +1. Une pitié qui atteint son seuil garantit sa capacité.
Economy.PityOrder = { "kibutsuji", "kamado", "tsugikuni", "rengoku", "tomioka" }
Economy.PityCaps = { kibutsuji = 2000, kamado = 1250, tsugikuni = 1000, rengoku = 250, tomioka = 150 }

-- Capacité garantie au prochain reroll (la première dont la pitié a atteint son seuil), sinon nil.
function Economy.PityGuarantee(pity)
	pity = pity or {}
	for _, name in ipairs(Economy.PityOrder) do
		if (pity[name] or 0) >= Economy.PityCaps[name] then
			return name
		end
	end
	return nil
end

-- Après un reroll : `won` est la capacité pitiable obtenue (ou nil si ce n'en est pas une).
function Economy.UpdatePity(pity, won)
	for _, name in ipairs(Economy.PityOrder) do
		if name == won then
			pity[name] = 0
		else
			pity[name] = (pity[name] or 0) + 1
		end
	end
	return pity
end

return Economy
