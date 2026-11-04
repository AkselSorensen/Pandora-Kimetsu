-- Yens et rerolls de stats (entraînement). Logique pure : le serveur fournit le générateur aléatoire.
-- La monnaie s'appelle encore « kamas » dans le code (champ state.kamas, reward.kamas) ; le joueur, lui, voit des yens.

local Economy = {}

Economy.RerollCost = 50

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

return Economy
