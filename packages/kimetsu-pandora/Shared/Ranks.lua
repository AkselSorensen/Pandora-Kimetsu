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
	-- Démons : rangs automatiques (corps mangés à vie et temps de jeu en secondes), puis les Lunes, attribuées à la main (manual).
	demon = {
		{ name = "Démon errant", kanji = "鬼", hp = 0, meals = 0, playtime = 0 },
		{ name = "Démon affamé", kanji = "餓", hp = 20, meals = 5, playtime = 3600 },
		{ name = "Démon chasseur", kanji = "狩", hp = 40, meals = 15, playtime = 7200 },
		{ name = "Démon tueur", kanji = "殺", hp = 70, meals = 30, playtime = 14400 },
		{ name = "Démon sanguinaire", kanji = "血", hp = 110, meals = 60, playtime = 28800 },
		{ name = "Démon d'élite", kanji = "精", hp = 160, meals = 100, playtime = 50400 },
		{ name = "Lune Inférieure Six", kanji = "下六", hp = 190, manual = true },
		{ name = "Lune Inférieure Quatre", kanji = "下四", hp = 220, manual = true },
		{ name = "Lune Inférieure Deux", kanji = "下弐", hp = 250, manual = true },
		{ name = "Lune Supérieure Six", kanji = "上六", hp = 280, manual = true },
		{ name = "Lune Supérieure Quatre", kanji = "上四", hp = 310, manual = true },
		{ name = "Lune Supérieure Deux", kanji = "上弐", hp = 340, manual = true },
		{ name = "Lune Supérieure Une", kanji = "上壱", hp = 370, manual = true },
	},
}

-- Grade démon automatique : le plus haut rang (hors Lunes) dont les conditions sont remplies.
function Ranks.DemonAutoIndex(meals, seconds)
	local steps = Ranks.Ladders.demon
	local index = 1
	for i, step in ipairs(steps) do
		if not step.manual and (meals or 0) >= step.meals and (seconds or 0) >= step.playtime then
			index = i
		end
	end
	return index
end

-- Grade à partir de son rang dans l'échelle (même forme que Ranks.Get).
function Ranks.At(ladder, index)
	local steps = Ranks.Ladders[ladder] or Ranks.Ladders.slayer
	index = math.max(1, math.min(#steps, index or 1))
	local step = steps[index]
	local nextStep = steps[index + 1]
	return { index = index, count = #steps, name = step.name, kanji = step.kanji, hp = step.hp, xp = step.xp or 0, nextXp = nextStep and nextStep.xp or nil }
end

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
