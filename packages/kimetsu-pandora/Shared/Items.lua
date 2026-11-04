-- Objets et inventaire. Logique pure (aucun appel moteur) : le serveur l'utilise pour valider.

local Items = {}

Items.SlotCount = 25
Items.MaxWeight = 30 -- kg portés au maximum

-- Emplacements d'équipement, dans l'ordre d'affichage : colonne gauche puis colonne droite.
Items.EquipSlots = { "head", "chest", "legs", "feet", "hands", "shirt", "ring", "weapon" }

-- rarity : common | uncommon | rare | epic. stats : bonus en % (endurance = PV max, vitesse, force = dégâts).
-- Un objet d'emplacement `weapon` dont l'id existe dans Config.Weapons.list se retrouve en main une fois équipé.
Items.List = {
	masque = { name = "Masque de renard", type = "Équipement", rarity = "rare", slot = "head", weight = 0.5, icon = "mask",
		desc = "Un masque rituel qui éloigne la malchance et inspire le respect aux plus braves.", creator = "Hitaki Minamoto", stats = { endurance = 5 } },
	veste = { name = "Uniforme du Corps", type = "Équipement", rarity = "common", slot = "chest", weight = 2, icon = "vest",
		desc = "L'uniforme noir des pourfendeurs : sobre, résistant, taillé pour les combats de nuit.", creator = "Atelier du Corps", stats = { endurance = 4 } },
	pantalon = { name = "Hakama du Corps", type = "Équipement", rarity = "common", slot = "legs", weight = 1.5, icon = "pants",
		desc = "Large et souple : il ne gêne ni la marche, ni la respiration.", creator = "Atelier du Corps", stats = { vitesse = 2 } },
	bottes = { name = "Waraji renforcés", type = "Équipement", rarity = "uncommon", slot = "feet", weight = 1.5, icon = "boots",
		desc = "Des sandales de paille tressée, resserrées pour ne jamais glisser dans la boue.", creator = "Atelier du Corps", stats = { vitesse = 6 } },
	gants = { name = "Bandages de combat", type = "Équipement", rarity = "common", slot = "hands", weight = 0.5, icon = "gloves",
		desc = "Une prise ferme, même quand la pluie s'en mêle.", creator = "Atelier du Corps", stats = { force = 3 } },
	chemise = { name = "Haori", type = "Équipement", rarity = "common", slot = "shirt", weight = 0.5, icon = "shirt",
		desc = "Un haori léger aux motifs de famille, porté par-dessus l'uniforme.", creator = "Atelier du Corps", stats = { endurance = 2 } },
	talisman = { name = "Boucles hanafuda", type = "Équipement", rarity = "epic", slot = "ring", weight = 1, icon = "talisman",
		desc = "Ces boucles d'oreille se transmettent de génération en génération. Elles donnent à leur porteur une endurance et une force dignes des plus grands mythes...", creator = "Hitaki Minamoto", stats = { endurance = 10, vitesse = 5, force = 10 } },
	dague = { name = "Kunai de glycine", type = "Équipement", rarity = "rare", slot = "weapon", weight = 1, icon = "dagger",
		desc = "Une lame fine dont l'acier est enduit de glycine : un démon touché s'en souvient.", creator = "Forge des Nichirin", stats = { force = 8 } },
	katana = { name = "Lame Nichirin", type = "Équipement", rarity = "epic", slot = "weapon", weight = 1.5, icon = "dagger",
		desc = "Une lame forgée dans l'acier solaire, la seule qui tranche vraiment le cou d'un démon. Elle prend la couleur de son porteur.", creator = "Forge des Nichirin", stats = { force = 12 } },
	onigiri = { name = "Onigiri", type = "Consommable", rarity = "common", weight = 0.2, icon = "onigiri", stack = 20, heal = 30,
		desc = "Une boule de riz préparée pour la route : récupère 30 PV.", creator = "Cuisine du Corps", stats = {} },
	fiole = { name = "Fiole de glycine", type = "Consommable", rarity = "uncommon", weight = 0.3, icon = "orb", stack = 5, heal = 80,
		desc = "Un remède du manoir aux papillons : récupère 80 PV.", creator = "Manoir aux papillons", stats = {} },
}

-- Lames Nichirin du pack yufu-arme-test : un objet par arme de Shared/YufuWeapons.lua (unreal_tools/gen_yufu_weapons.py),
-- de même id que dans Config.Weapons.list (yufu_<nom>), donc en main dès qu'on les équipe.
-- Items.BladeList (id, nom, catégorie) alimente la forge ; les stats et le poids suivent la catégorie.
local Yufu = Package and Package.Require("YufuWeapons.lua") or require("Shared.YufuWeapons")

local BLADE_GROUPS = {
	Katana = { rarity = "rare", weight = 1.5, force = 12, desc = "Une lame courbe, rapide et précise." },
	Claymore = { rarity = "epic", weight = 3, force = 16, desc = "Une grande lame lourde, faite pour les coups qui comptent." },
	Lance = { rarity = "epic", weight = 2.5, force = 14, desc = "Une arme d'hast : elle garde l'ennemi à distance." },
	Divers = { rarity = "rare", weight = 1.5, force = 10, desc = "Une lame singulière, forgée pour un seul porteur." },
}

-- "typ_yoru_sold" -> "Typ Yoru Sold", "claymore54" -> "Claymore n°54".
local function bladeName(key)
	local base, number = key:match("^(.-)(%d*)$")
	base = base:gsub("_", " "):gsub("^%s+", ""):gsub("%s+$", "")
	base = base:gsub("(%a)([%w']*)", function(first, rest)
		return first:upper() .. rest
	end)
	return number ~= "" and (base .. " n°" .. number) or base
end

Items.BladeList = {}
for _, blade in ipairs(Yufu.weapons) do
	local key, group = blade[1], blade[2]
	local spec = BLADE_GROUPS[group] or BLADE_GROUPS.Divers
	local id = "yufu_" .. key
	Items.List[id] = { name = bladeName(key), type = "Équipement", rarity = spec.rarity, slot = "weapon", weight = spec.weight, icon = "dagger",
		blade = true, group = group, desc = "Lame Nichirin. " .. spec.desc, creator = "Forge des Nichirin", stats = { force = spec.force } }
	Items.BladeList[#Items.BladeList + 1] = { id = id, name = Items.List[id].name, group = group }
end

function Items.Get(id)
	return Items.List[id]
end

local function stackSize(def)
	return def.stack or 1
end

-- Inventaire : { slots = { [1..SlotCount] = { id, count } | nil }, equip = { [slot] = id } }
function Items.NewInventory()
	return { slots = {}, equip = {} }
end

function Items.Weight(inv)
	local total = 0
	for _, entry in pairs(inv.slots) do
		total = total + Items.List[entry.id].weight * entry.count
	end
	for _, id in pairs(inv.equip) do
		total = total + Items.List[id].weight
	end
	return total
end

-- Ajoute count objets (empile d'abord). Renvoie true si tout est entré, sinon ne change rien.
function Items.Add(inv, id, count)
	local def = Items.List[id]
	count = count or 1
	if not def or count < 1 or Items.Weight(inv) + def.weight * count > Items.MaxWeight then
		return false
	end
	local free, room = {}, 0
	for i = 1, Items.SlotCount do
		local entry = inv.slots[i]
		if not entry then
			table.insert(free, i)
			room = room + stackSize(def)
		elseif entry.id == id then
			room = room + stackSize(def) - entry.count
		end
	end
	if room < count then
		return false
	end
	for i = 1, Items.SlotCount do
		local entry = inv.slots[i]
		if entry and entry.id == id and count > 0 then
			local put = math.min(count, stackSize(def) - entry.count)
			entry.count = entry.count + put
			count = count - put
		end
	end
	for _, i in ipairs(free) do
		if count <= 0 then
			break
		end
		local put = math.min(count, stackSize(def))
		inv.slots[i] = { id = id, count = put }
		count = count - put
	end
	return true
end

-- Retire count objets du slot (tout si count est nil). Renvoie l'id retiré et la quantité, ou nil.
function Items.Take(inv, slot, count)
	local entry = inv.slots[slot]
	if not entry then
		return nil
	end
	count = math.min(count or entry.count, entry.count)
	entry.count = entry.count - count
	if entry.count <= 0 then
		inv.slots[slot] = nil
	end
	return entry.id, count
end

function Items.Swap(inv, from, to)
	if from == to or from < 1 or to < 1 or from > Items.SlotCount or to > Items.SlotCount then
		return false
	end
	local a, b = inv.slots[from], inv.slots[to]
	if not a then
		return false
	end
	if b and b.id == a.id and stackSize(Items.List[a.id]) > 1 then
		local put = math.min(a.count, stackSize(Items.List[a.id]) - b.count)
		b.count = b.count + put
		a.count = a.count - put
		if a.count <= 0 then
			inv.slots[from] = nil
		end
		return true
	end
	inv.slots[from], inv.slots[to] = b, a
	return true
end

-- Équipe l'objet du slot ; l'ancien équipement revient dans le slot libéré.
function Items.Equip(inv, slot)
	local entry = inv.slots[slot]
	local def = entry and Items.List[entry.id]
	if not def or not def.slot or entry.count ~= 1 then
		return false
	end
	local previous = inv.equip[def.slot]
	inv.equip[def.slot] = entry.id
	inv.slots[slot] = previous and { id = previous, count = 1 } or nil
	return true
end

function Items.Unequip(inv, equipSlot)
	local id = inv.equip[equipSlot]
	if not id then
		return false
	end
	inv.equip[equipSlot] = nil
	if not Items.Add(inv, id, 1) then
		inv.equip[equipSlot] = id
		return false
	end
	return true
end

-- Somme des bonus de l'équipement : { endurance, vitesse, force } en %.
function Items.GearStats(inv)
	local sum = { endurance = 0, vitesse = 0, force = 0 }
	for _, id in pairs(inv.equip) do
		for stat, value in pairs(Items.List[id].stats) do
			sum[stat] = sum[stat] + value
		end
	end
	return sum
end

return Items
