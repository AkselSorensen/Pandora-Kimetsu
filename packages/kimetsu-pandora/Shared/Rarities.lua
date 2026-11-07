-- Raretés des pouvoirs (souffles et pouvoirs démoniaques). Chaque pouvoir aura une de ces raretés.
-- factor : multiplicateur des âmes de départ (300 × factor). weight : chance de tirage au reroll, en %.

local Rarities = {}

Rarities.List = {
	{ id = "common", label = "Commun", color = "#aeb4ba", factor = 1, weight = 92 },
	{ id = "rare", label = "Rare", color = "#168de2", factor = 1.5, weight = 7 },
	{ id = "epic", label = "Épique", color = "#9b45e8", factor = 2, weight = 0.9 },
	{ id = "mythic", label = "Mythique", color = "#e52d38", factor = 3, weight = 0.1 },
	{ id = "pandorium", label = "Pandorium", color = "#111111", factor = 4, weight = 0 },
}

-- Multiplicateurs par identifiant, pour lire vite la rareté d'un pouvoir.
Rarities.Factors = {}
for _, rarity in ipairs(Rarities.List) do
	Rarities.Factors[rarity.id] = rarity.factor
end

-- Renvoie la définition d'une rareté, ou la commune si l'identifiant est inconnu.
function Rarities.Get(id)
	for _, rarity in ipairs(Rarities.List) do
		if rarity.id == id then return rarity end
	end
	return Rarities.List[1]
end

return Rarities
