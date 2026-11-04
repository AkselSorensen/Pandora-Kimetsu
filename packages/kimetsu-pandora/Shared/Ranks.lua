-- Grades : le rang monte avec l'expérience (XP). Logique pure, sans appel moteur.
-- Une échelle par camp : les pourfendeurs gravissent les dix rangs du Corps jusqu'à Hashira, les démons les Lunes.
-- hp : bonus de PV max accordé par le grade.

local Ranks = {}

Ranks.Ladders = {
	slayer = {
		{ name = "Mizunoto", kanji = "癸", xp = 0, hp = 0 },
		{ name = "Mizunoe", kanji = "壬", xp = 100, hp = 20 },
		{ name = "Kanoto", kanji = "辛", xp = 250, hp = 40 },
		{ name = "Kanoe", kanji = "庚", xp = 450, hp = 60 },
		{ name = "Tsuchinoto", kanji = "己", xp = 700, hp = 80 },
		{ name = "Tsuchinoe", kanji = "戊", xp = 1000, hp = 100 },
		{ name = "Hinoto", kanji = "丁", xp = 1400, hp = 130 },
		{ name = "Hinoe", kanji = "丙", xp = 1900, hp = 160 },
		{ name = "Kinoto", kanji = "乙", xp = 2500, hp = 190 },
		{ name = "Kinoe", kanji = "甲", xp = 3200, hp = 220 },
		{ name = "Hashira", kanji = "柱", xp = 4500, hp = 300 },
	},
	demon = {
		{ name = "Démon errant", kanji = "鬼", xp = 0, hp = 0 },
		{ name = "Lune Inférieure Six", kanji = "下六", xp = 150, hp = 30 },
		{ name = "Lune Inférieure Quatre", kanji = "下四", xp = 500, hp = 80 },
		{ name = "Lune Inférieure Deux", kanji = "下弐", xp = 1000, hp = 130 },
		{ name = "Lune Supérieure Six", kanji = "上六", xp = 1800, hp = 190 },
		{ name = "Lune Supérieure Quatre", kanji = "上四", xp = 2600, hp = 240 },
		{ name = "Lune Supérieure Deux", kanji = "上弐", xp = 3500, hp = 280 },
		{ name = "Lune Supérieure Une", kanji = "上壱", xp = 4500, hp = 320 },
	},
}

-- Grade d'un joueur pour une échelle et une quantité d'XP.
-- Renvoie { index, count, name, kanji, hp, xp = seuil du grade, nextXp = seuil du suivant ou nil au dernier grade }.
function Ranks.Get(ladder, xp)
	local steps = Ranks.Ladders[ladder] or Ranks.Ladders.slayer
	xp = math.max(0, xp or 0)
	local index = 1
	for i, step in ipairs(steps) do
		if xp >= step.xp then
			index = i
		end
	end
	local step = steps[index]
	local nextStep = steps[index + 1]
	return {
		index = index,
		count = #steps,
		name = step.name,
		kanji = step.kanji,
		hp = step.hp,
		xp = step.xp,
		nextXp = nextStep and nextStep.xp or nil,
	}
end

-- Ajoute de l'XP (jamais négative) : renvoie le nouveau total et, si le grade a changé, la nouvelle définition de grade.
function Ranks.AddXp(ladder, xp, amount)
	local before = Ranks.Get(ladder, xp)
	local total = math.max(0, (xp or 0) + (amount or 0))
	local after = Ranks.Get(ladder, total)
	return total, after.index ~= before.index and after or nil
end

return Ranks
