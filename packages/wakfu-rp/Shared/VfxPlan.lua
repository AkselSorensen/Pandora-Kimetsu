-- Effets visuels des techniques : choix des systèmes Niagara cuits et trajectoires des traînées.
-- Logique pure (aucun appel moteur), donc testable seule. Les effets disponibles viennent de VfxAssets.lua, généré après la cuisson
-- des packs de VFX (unreal_tools/gen_vfx_assets.py) : sans effet cuit, aucune technique ne joue d'effet et rien ne plante.

-- En jeu : Package.Require (Nanos World). Hors jeu (tests) : require classique.
local Classes = Package and Package.Require("Classes.lua") or require("Shared.Classes")
local Assets = Package and Package.Require("VfxAssets.lua") or require("Shared.VfxAssets")
-- Meshes d'effet originaux (FxMeshAssets.lua, généré comme VfxAssets.lua) : { pack, meshes = { "SM_FX_..." }, materials = { "MI_FX_..." } }.
local FxAssets = Package and Package.Require("FxMeshAssets.lua") or require("Shared.FxMeshAssets")

local Vfx = {}

-- Un personnage nanos world est positionné au centre de sa capsule : les hauteurs ci-dessous sont comptées depuis les pieds.
Vfx.CapsuleHalfHeight = 90

-- Trajectoires d'une traînée, dans l'ordre d'affichage de l'outil d'essai.
Vfx.Patterns = { "forward", "arc", "spiral", "rise" }

-- Effets préférés de chaque voie, par rôle, du plus au moins voulu (noms de systèmes Niagara, tous packs confondus) :
-- trail = la traînée de la technique, finisher = l'effet d'impact de la technique 4, heal = l'effet des techniques de soin.
-- À ajuster après avoir vu les couleurs en jeu avec les touches d'essai.
Vfx.Style = {
	Eau = { trail = { "NS_Trail_Water" }, finisher = { "NS_Free_Spells_Shockwave", "NS_Free_Magic_Circle1" }, heal = { "NS_Free_Spells_Aura_Healing" } },
	Foudre = { trail = { "NS_Trail_Electric" }, finisher = { "NS_Free_Spells_Aura_Lightning", "NS_Free_Spells_Explosion" }, heal = { "NS_Free_Spells_Aura_Healing" } },
	Flamme = { trail = { "NS_Trail_Fire" }, finisher = { "NS_Free_Spells_Explosion", "NS_Free_Spells_Aura_Fire" }, heal = { "NS_Free_Spells_Aura_Healing" } },
	Vent = { trail = { "NS_Trail_Nature" }, finisher = { "NS_Free_Spells_Aura_Air", "NS_Free_Spells_Shockwave" }, heal = { "NS_Free_Spells_Aura_Healing" } },
	Pierre = { trail = { "NS_Trail_Earth" }, finisher = { "NS_Free_Spells_Shockwave", "NS_Free_Spells_Explosion" }, heal = { "NS_Free_Spells_Buff_Healing", "NS_Free_Spells_Aura_Healing" } },
	Brume = { trail = { "NS_Trail_Ice" }, finisher = { "NS_Free_Magic_Area1", "NS_Free_Spells_Circle" }, heal = { "NS_Free_Spells_Aura_Healing" } },
	Insecte = { trail = { "NS_Trail_Cosmos" }, finisher = { "NS_Free_Magic_Hit1", "NS_Free_Spells_Explosion" }, heal = { "NS_Free_Spells_Aura_Healing", "NS_Free_Spells_Buff_Healing" } },
	Demon = { trail = { "NS_Trail_Dark" }, finisher = { "NS_Free_Spells_Aura_Soul", "NS_Free_Spells_Explosion" }, heal = { "NS_Free_Spells_Buff_Soul", "NS_Free_Spells_Aura_Soul" } },
}

-- Forme de chaque technique (1 à 4) : trajectoire de la traînée, durée en secondes et décalages de lacet (degrés) des traînées jouées ensemble.
Vfx.Slots = {
	{ pattern = "arc", duration = 0.45, yaws = { 0 } },
	{ pattern = "forward", duration = 0.6, yaws = { 0 } },
	{ pattern = "spiral", duration = 0.9, yaws = { 0 } },
	{ pattern = "forward", duration = 0.8, yaws = { -14, 0, 14 }, finisher = true },
}

-- Formes lumineuses dessinées par code (unreal_tools/gen_fx_meshes.py), jouées en plus des systèmes Niagara. Chaque voie a la couleur de son
-- matériau MI_FX_<voie> et ses propres formes : slash = coup de la technique 1 (roll = inclinaison en degrés), dash = botte de la 2,
-- twirl = tourbillon de la 3, finisher = impact de la 4 (avec un anneau au sol). Les soins jouent un grand anneau et le tourbillon.
Vfx.MeshStyle = {
	Eau = { slash = "SlashWide", roll = -25, dash = "Wave", twirl = "Spiral", finisher = "Burst" },
	Foudre = { slash = "SlashThin", roll = 55, dash = "Streak", twirl = "Wind", finisher = "Burst" },
	Flamme = { slash = "SlashV", roll = -40, dash = "Wave", twirl = "Spiral", finisher = "Burst" },
	Vent = { slash = "SlashH", roll = 0, dash = "Wave", twirl = "Wind", finisher = "RingWide" },
	Pierre = { slash = "SlashWide", roll = 20, dash = "Streak", twirl = "Spiral", finisher = "Burst" },
	Brume = { slash = "SlashThin", roll = -70, dash = "Wave", twirl = "Wind", finisher = "Burst" },
	Insecte = { slash = "Claw", roll = -30, dash = "Streak", twirl = "Spiral", finisher = "RingWide" },
	Demon = { slash = "Claw", roll = 25, dash = "Wave", twirl = "Wind", finisher = "Burst" },
}

-- Couleurs proposées par l'outil d'essai (une instance MI_FX_<couleur> chacune) : le blanc puis les 8 voies.
Vfx.MeshColors = { "Blanc", "Eau", "Foudre", "Flamme", "Vent", "Pierre", "Brume", "Insecte", "Demon" }

-- Formes qui se jouent autour du lanceur, au sol ; les autres se jouent devant lui.
local CENTERED = { Ring = true, RingWide = true, Spiral = true, Wind = true, Burst = true }

-- Type d'un effet d'après son nom : "trail" (ruban qui suit une trajectoire), "oriented" (joué devant le lanceur, dans sa direction :
-- coups, projectiles, lignes) ou "burst" (joué sur place : auras, cercles, explosions).
function Vfx.KindOf(name)
	if name:find("Trail", 1, true) then
		return "trail"
	end
	for _, word in ipairs({ "Slash", "Attack", "Projectile", "Line" }) do
		if name:find(word, 1, true) then
			return "oriented"
		end
	end
	return "burst"
end

-- Vrai si au moins un effet est cuit sur ce serveur.
function Vfx.HasAssets()
	return next(Assets) ~= nil
end

local function listed(names, wanted)
	for _, name in ipairs(names or {}) do
		if name == wanted then
			return true
		end
	end
	return false
end

-- Vrai si les meshes d'effet sont cuits sur ce serveur.
function Vfx.HasMeshes()
	return type(FxAssets.pack) == "string" and FxAssets.pack ~= "" and #(FxAssets.meshes or {}) > 0
end

-- Tous les effets disponibles : { pack, name, id = "pack::NOM", kind }, triés par pack puis par nom, puis les formes de mesh (kind "mesh").
-- Les systèmes _Base (modèles) sont exclus.
function Vfx.Bank()
	local packs = {}
	for pack in pairs(Assets) do
		packs[#packs + 1] = pack
	end
	table.sort(packs)
	local bank = {}
	for _, pack in ipairs(packs) do
		local names = {}
		for _, name in ipairs(Assets[pack]) do
			names[#names + 1] = name
		end
		table.sort(names)
		for _, name in ipairs(names) do
			if name:sub(-5) ~= "_Base" then
				bank[#bank + 1] = { pack = pack, name = name, id = pack .. "::" .. name, kind = Vfx.KindOf(name) }
			end
		end
	end
	if Vfx.HasMeshes() then
		local shapes = {}
		for _, name in ipairs(FxAssets.meshes) do
			shapes[#shapes + 1] = name
		end
		table.sort(shapes)
		for _, name in ipairs(shapes) do
			bank[#bank + 1] = { pack = FxAssets.pack, name = name, id = FxAssets.pack .. "::" .. name, kind = "mesh" }
		end
	end
	return bank
end

-- Premier effet de la liste de noms voulus qui est disponible, ou nil.
function Vfx.Find(names)
	local bank = Vfx.Bank()
	for _, wanted in ipairs(names or {}) do
		for _, entry in ipairs(bank) do
			if entry.name == wanted then
				return entry
			end
		end
	end
	return nil
end

-- Repli quand l'effet voulu n'est pas cuit : un effet du même type pris dans la banque, toujours le même pour une même graine.
function Vfx.Fallback(kind, seed)
	local candidates = {}
	for _, entry in ipairs(Vfx.Bank()) do
		if entry.kind == kind then
			candidates[#candidates + 1] = entry
		end
	end
	if #candidates == 0 then
		return nil
	end
	return candidates[(seed - 1) % #candidates + 1]
end

-- Position d'une traînée, dans le repère du lanceur (avant, droite, haut) en cm, à l'instant t (0 à 1) de la trajectoire.
function Vfx.Offset(pattern, t, range)
	t = math.max(0, math.min(1, t))
	if pattern == "arc" then -- coup balayé de gauche à droite, du haut vers le bas
		local angle = math.rad(-70 + 140 * t)
		local radius = math.min(range, 260)
		return radius * math.cos(angle), radius * math.sin(angle), 170 - 120 * t
	elseif pattern == "spiral" then -- tourbillon autour du lanceur, qui monte
		local angle = 2 * math.pi * 2 * t
		local radius = 110 + 110 * t
		return radius * math.cos(angle), radius * math.sin(angle), 30 + 180 * t
	elseif pattern == "rise" then -- colonne qui monte le long du corps
		local angle = 2 * math.pi * 3 * t
		return 60 * math.cos(angle), 60 * math.sin(angle), 250 * t
	end
	return 120 + (range - 120) * t, 0, 100 -- "forward" : droit devant, à hauteur de poitrine
end

-- Position dans le monde : origine = centre du personnage {x, y, z}, lacet en degrés, décalage (avant, droite, haut) du repère du lanceur.
-- Dans Unreal, lacet 0 regarde vers +X et la droite est +Y ; à lacet 90 l'avant est +Y et la droite -X.
function Vfx.World(origin, yaw, forward, right, up)
	local rad = math.rad(yaw)
	local cos, sin = math.cos(rad), math.sin(rad)
	return origin.x + cos * forward - sin * right, origin.y + sin * forward + cos * right, origin.z - Vfx.CapsuleHalfHeight + up
end

local function trailPiece(entry, pattern, duration, range, yaw)
	return { asset = entry.id, kind = "trail", motion = "path", pattern = pattern, duration = duration, range = range, yaw = yaw or 0 }
end

local function staticPiece(entry, duration, at)
	return { asset = entry.id, kind = entry.kind, motion = "static", duration = duration, at = at, yaw = 0 }
end

-- Morceau de mesh : la forme (sans le préfixe SM_FX_) dans la couleur d'une voie (matériau MI_FX_<couleur>, à défaut M_FX_Glow, à défaut celui
-- du mesh), nil si la forme n'est pas cuite. spec : from et to = position de départ et d'arrivée (avant, droite, haut) en cm, scale = { début, fin },
-- duration en secondes, roll et spin (tours de lacet en degrés sur la durée) facultatifs. Le morceau se déplace de from à to en ralentissant.
local function meshPiece(color, shape, spec)
	local name = "SM_FX_" .. tostring(shape)
	if not Vfx.HasMeshes() or not listed(FxAssets.meshes, name) then
		return nil
	end
	local material
	for _, candidate in ipairs({ "MI_FX_" .. color, "M_FX_Glow" }) do
		if listed(FxAssets.materials, candidate) then
			material = FxAssets.pack .. "::" .. candidate
			break
		end
	end
	return {
		asset = FxAssets.pack .. "::" .. name, material = material, kind = "mesh", motion = "mesh", shape = shape, yaw = 0,
		from = spec.from, to = spec.to, scale = spec.scale, duration = spec.duration,
		rot = { 0, 0, spec.roll or 0 }, spin = spec.spin or 0, fadeIn = spec.fadeIn or 0.15, fadeOut = spec.fadeOut or 0.45,
	}
end

-- État d'un morceau de mesh à l'instant t (0 à 1) : avant, droite, haut (cm), échelle, tangage, lacet (en plus de celui du lanceur), roulis
-- (degrés) et opacité (0 à 1 : le mesh apparaît vite puis s'estompe). Mouvement et échelle ralentissent vers la fin.
function Vfx.MeshAt(piece, t)
	t = math.max(0, math.min(1, t))
	local eased = 1 - (1 - t) * (1 - t)
	local function lerp(a, b)
		return a + (b - a) * eased
	end
	local fade = math.min(1, t / math.max(piece.fadeIn, 0.01)) * math.min(1, (1 - t) / math.max(piece.fadeOut, 0.01))
	return lerp(piece.from[1], piece.to[1]), lerp(piece.from[2], piece.to[2]), lerp(piece.from[3], piece.to[3]), lerp(piece.scale[1], piece.scale[2]),
		piece.rot[1], piece.rot[2] + piece.spin * t, piece.rot[3], fade
end

-- Morceaux de mesh de la technique `slot` de la voie className, vides si les meshes ne sont pas cuits ou si la voie n'a pas de style.
local function meshPieces(className, slot, spell, range)
	local pieces = {}
	local style = Vfx.MeshStyle[className]
	if not style or not Vfx.HasMeshes() then
		return pieces
	end
	local function add(shape, spec)
		pieces[#pieces + 1] = meshPiece(className, shape, spec)
	end
	if spell.heal and not spell.damage then
		add("RingWide", { from = { 0, 0, 6 }, to = { 0, 0, 6 }, scale = { 0.5, 1.7 }, duration = 1.6 })
		add(style.twirl, { from = { 0, 0, 0 }, to = { 0, 0, 30 }, scale = { 0.9, 1.1 }, duration = 1.8, spin = 360 })
		return pieces
	end
	local reach = range * 0.8
	if slot == 1 then
		add(style.slash, { from = { 80, 0, 110 }, to = { 200, 0, 110 }, roll = style.roll, scale = { 0.7, 1.2 }, duration = 0.4 })
	elseif slot == 2 then
		add(style.dash, { from = { 60, 0, 70 }, to = { range * 0.7, 0, 70 }, scale = { 0.5, 1.0 }, duration = 0.55 })
	elseif slot == 3 then
		add(style.twirl, { from = { 0, 0, 0 }, to = { 0, 0, 40 }, scale = { 0.6, 1.3 }, duration = 0.9, spin = 540 })
	else
		add(style.slash, { from = { 100, 0, 110 }, to = { 230, 0, 110 }, roll = style.roll, scale = { 1.0, 1.7 }, duration = 0.5 })
		add("Ring", { from = { reach, 0, 6 }, to = { reach, 0, 6 }, scale = { 0.3, 2.0 }, duration = 0.8 })
		add(style.finisher, { from = { reach, 0, 0 }, to = { reach, 0, 0 }, scale = { 0.3, 1.5 }, duration = 0.9 })
	end
	return pieces
end

-- Morceau d'essai d'une forme de la banque (entry.kind == "mesh"), dans une couleur de Vfx.MeshColors.
local function meshTestPiece(entry, color)
	local shape = entry.name:gsub("^SM_FX_", "")
	local spec = { scale = { 0.8, 1.0 }, duration = 2.0, fadeIn = 0.1, fadeOut = 0.5 }
	if CENTERED[shape] then
		spec.from, spec.to = { 0, 0, 0 }, { 0, 0, 0 }
		spec.spin = (shape == "Spiral" or shape == "Wind") and 360 or 0
	else
		spec.from, spec.to = { 120, 0, 110 }, { 260, 0, 110 }
	end
	return meshPiece(color, shape, spec)
end

-- Plan d'une technique : liste de morceaux { asset, kind, motion = "path" | "static" | "mesh", ... }, vide si rien n'est cuit.
function Vfx.PlanFor(className, slot, spell)
	local plan = Vfx.NiagaraPlan(className, slot, spell)
	local range = math.max(250, math.min(spell.range or 0, 1200))
	for _, piece in ipairs(meshPieces(className, slot, spell, range)) do
		plan.pieces[#plan.pieces + 1] = piece
	end
	return plan
end

-- Plan des seuls systèmes Niagara d'une technique (traînées, aura, impact).
function Vfx.NiagaraPlan(className, slot, spell)
	local pieces = {}
	local style = Vfx.Style[className]
	if not style then
		return { pieces = pieces }
	end
	local range = math.max(250, math.min(spell.range or 0, 1200))
	local trail = Vfx.Find(style.trail) or Vfx.Fallback("trail", slot)
	if spell.heal and not spell.damage then -- technique de soin : aura sur place et colonne qui monte
		local heal = Vfx.Find(style.heal) or Vfx.Fallback("burst", slot)
		if heal then
			pieces[#pieces + 1] = staticPiece(heal, 2.5, { 0, 0, 0 })
		end
		if trail then
			pieces[#pieces + 1] = trailPiece(trail, "rise", 1.0, range, 0)
		end
		return { pieces = pieces }
	end
	local shape = Vfx.Slots[math.max(1, math.min(slot, #Vfx.Slots))]
	if trail then
		for _, yaw in ipairs(shape.yaws) do
			pieces[#pieces + 1] = trailPiece(trail, shape.pattern, shape.duration, range, yaw)
		end
	end
	if shape.finisher then -- impact de la technique 4, là où la traînée s'arrête
		local finisher = Vfx.Find(style.finisher) or Vfx.Fallback("burst", slot)
		if finisher then
			pieces[#pieces + 1] = staticPiece(finisher, 2.0, { range * 0.8, 0, 0 })
		end
	end
	return { pieces = pieces }
end

-- Plan d'une technique d'après son identifiant (celui de Classes.lua) ; vide si elle n'existe pas.
function Vfx.PlanForSpell(spellId)
	for className, class in pairs(Classes.List) do
		for slot, spell in ipairs(class.spells) do
			if spell.id == spellId then
				return Vfx.PlanFor(className, slot, spell)
			end
		end
	end
	return { pieces = {} }
end

-- Morceaux d'essai d'un effet de la banque : une traînée suit la trajectoire choisie, un coup ou un projectile se joue devant le
-- joueur, une aura ou une explosion se joue sur lui.
function Vfx.TestPieces(entry, pattern, color)
	if entry.kind == "trail" then
		return { trailPiece(entry, pattern, 1.0, 600, 0) }
	elseif entry.kind == "mesh" then
		local piece = meshTestPiece(entry, color or "Blanc")
		return piece and { piece } or {}
	elseif entry.kind == "oriented" then
		return { staticPiece(entry, 2.0, { 120, 0, 100 }) }
	end
	return { staticPiece(entry, 3.0, { 0, 0, 0 }) }
end

-- Traînées proposables au joueur : les effets de type trail de la banque, avec un nom lisible et un groupe pour le menu.
Vfx.TrailLabels = {
	NS_Trail_Cosmos = "Cosmos", NS_Trail_Dark = "Obscure", NS_Trail_Earth = "Terre", NS_Trail_Electric = "Foudre", NS_Trail_Fire = "Feu",
	NS_Trail_Ice = "Glace", NS_Trail_Nature = "Nature", NS_Trail_Sound = "Son", NS_Trail_Void = "Vide", NS_Trail_Water = "Eau",
}

function Vfx.TrailList()
	local elemental, others = {}, {}
	for _, entry in ipairs(Vfx.Bank()) do
		if entry.kind == "trail" then
			local label = Vfx.TrailLabels[entry.name]
			if label then
				elemental[#elemental + 1] = { id = entry.id, name = label, group = "Élémentaires" }
			else
				others[#others + 1] = { id = entry.id, name = "Traînée " .. (entry.name:match("(%d+)$") or entry.name), group = "Sabre" }
			end
		end
	end
	for _, entry in ipairs(others) do -- les élémentaires d'abord, plus parlantes que les traînées numérotées
		elemental[#elemental + 1] = entry
	end
	return elemental
end

-- Traînée par défaut d'une voie (celle de Vfx.Style, sinon une traînée quelconque de la banque), ou nil si aucune n'est cuite.
function Vfx.DefaultTrail(className)
	local style = Vfx.Style[className]
	return (style and Vfx.Find(style.trail)) or Vfx.Fallback("trail", 1)
end

-- Vrai si le choix est valable : "auto", "none" ou l'identifiant d'une traînée de la banque.
function Vfx.IsTrailChoice(choice)
	if choice == "auto" or choice == "none" then
		return true
	end
	if type(choice) ~= "string" then
		return false
	end
	for _, entry in ipairs(Vfx.Bank()) do
		if entry.id == choice and entry.kind == "trail" then
			return true
		end
	end
	return false
end

-- Traînée à accrocher à l'arme d'un joueur d'après son choix : nil ou "auto" = celle de sa voie, "none" = aucune, sinon la traînée choisie
-- (un identifiant devenu inconnu retombe sur celle de la voie).
function Vfx.ResolveTrail(className, choice)
	if choice == "none" then
		return nil
	end
	if choice and choice ~= "auto" then
		for _, entry in ipairs(Vfx.Bank()) do
			if entry.id == choice and entry.kind == "trail" then
				return entry
			end
		end
	end
	return Vfx.DefaultTrail(className)
end

return Vfx
