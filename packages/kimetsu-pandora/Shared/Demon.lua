-- Système du démon : sang, chair, âmes, paliers de puissance, faim et régénération. Logique pure (aucun appel moteur), donc testable seule.
-- Les valeurs viennent de Config.Demon ; l'état d'un démon est une table { blood, flesh, souls, sinceFed, sinceCombat }.
-- Le temps avance par pas (Demon.Tick) : on ne lit aucune horloge ici.

-- En jeu : Package.Require (Nanos World). Hors jeu (tests) : require classique.
local Config = Package and Package.Require("Config.lua") or require("Shared.Config")

local Demon = {}

local function settings(cfg)
	return cfg or Config.Demon
end

-- État d'un démon qui vient de naître : plein de sang, sans chair ni âmes, pas de combat récent.
function Demon.New(cfg)
	cfg = settings(cfg)
	return { blood = cfg.blood.max, flesh = 0, souls = 0, sinceFed = 0, sinceCombat = cfg.combatSeconds, meals = 0, dayElapsed = 0 }
end

-- Nombre maximal de repas (proies humaines : cadavres et civils) par jour pour un grade : cfg.meals.caps[grade] si la liste le donne, sinon
-- perRank × numéro du grade (5 au premier grade, 10 au deuxième, 15 au troisième...).
function Demon.DailyCap(cfg, rankIndex)
	cfg = settings(cfg)
	local explicit = cfg.meals.caps and cfg.meals.caps[rankIndex]
	return explicit or cfg.meals.perRank * math.max(1, rankIndex or 1)
end

-- Vrai si un démon de ce grade peut encore dévorer une proie de cette source aujourd'hui. Sinon false, "cap" et le maximum du jour.
-- Une source qui ne compte pas dans la limite (cfg.meals.kinds) passe toujours.
function Demon.CanEat(cfg, demon, rankIndex, kind)
	cfg = settings(cfg)
	if not cfg.meals.kinds[kind] then
		return true
	end
	local cap = Demon.DailyCap(cfg, rankIndex)
	if demon.meals >= cap then
		return false, "cap", cap
	end
	return true
end

-- Palier de puissance pour une quantité d'âmes : renvoie son numéro et sa définition.
function Demon.Tier(cfg, souls)
	cfg = settings(cfg)
	local index = 1
	for i, tier in ipairs(cfg.tiers) do
		if (souls or 0) >= tier.souls then
			index = i
		end
	end
	return index, cfg.tiers[index]
end

-- Bonus du palier actuel : { tier, name, hp, damagePct, regen }.
function Demon.Bonuses(cfg, demon)
	cfg = settings(cfg)
	local index, tier = Demon.Tier(cfg, demon.souls)
	return { tier = index, name = tier.name, hp = tier.hp, damagePct = tier.damagePct, regen = tier.regen }
end

-- Coût en sang de la technique n°index (0 si elle n'en coûte pas).
function Demon.SpellCost(cfg, index)
	cfg = settings(cfg)
	return cfg.blood.costs[index] or 0
end

-- Palier requis pour la technique n°index, ou nil si elle est libre.
function Demon.RequiredTier(cfg, index)
	cfg = settings(cfg)
	return cfg.unlock[index]
end

-- Tente de lancer la technique n°index : paie le sang si elle est débloquée et payable.
-- Renvoie true, ou false avec la raison ("locked" et le palier requis, ou "blood" et le coût).
function Demon.TryCast(cfg, demon, index)
	cfg = settings(cfg)
	local required = Demon.RequiredTier(cfg, index)
	if required and Demon.Tier(cfg, demon.souls) < required then
		return false, "locked", required
	end
	local cost = Demon.SpellCost(cfg, index)
	if demon.blood < cost then
		return false, "blood", cost
	end
	demon.blood = demon.blood - cost
	return true
end

-- Un coup donné ou reçu : la régénération passive s'arrête jusqu'à la fin du délai de combat.
function Demon.Hit(demon)
	demon.sinceCombat = 0
end

-- Dévore une proie de la source donnée (clé de Config.Demon.sources) : monte la chair et les âmes jusqu'à leur plafond et remet la faim à zéro.
-- Renvoie { flesh, souls, heal, tier, tierUp } ou nil si la source n'existe pas. heal = fraction des PV max rendue sur le coup.
function Demon.Consume(cfg, demon, kind)
	cfg = settings(cfg)
	local source = cfg.sources[kind]
	if not source then
		return nil
	end
	local before = Demon.Tier(cfg, demon.souls)
	demon.flesh = math.min(cfg.flesh.max, demon.flesh + source.flesh)
	demon.souls = math.min(cfg.souls.max, demon.souls + source.souls)
	demon.sinceFed = 0
	if cfg.meals.kinds[kind] then
		demon.meals = demon.meals + 1
		demon.totalMeals = (demon.totalMeals or 0) + 1 -- compteur à vie (grades démon)
	end
	local after = Demon.Tier(cfg, demon.souls)
	return { flesh = source.flesh, souls = source.souls, heal = source.heal, xp = source.xp or 0, tier = after, tierUp = after > before }
end

-- Fait avancer le temps de dt secondes : le sang remonte, la chair se vide, la faim ronge la puissance et la régénération passive soigne.
-- opts.sun = true coupe la régénération (plein soleil, plan A21). Renvoie { heal = fraction des PV max à rendre, hunger = { from, to } ou nil }.
function Demon.Tick(cfg, demon, dt, opts)
	cfg = settings(cfg)
	opts = opts or {}
	demon.sinceCombat = demon.sinceCombat + dt
	demon.sinceFed = demon.sinceFed + dt
	-- Un nouveau jour (cfg.meals.dayLength secondes) remet le compteur de repas à zéro.
	demon.dayElapsed = demon.dayElapsed + dt
	if demon.dayElapsed >= cfg.meals.dayLength then
		demon.dayElapsed = 0
		demon.meals = 0
	end
	demon.blood = math.min(cfg.blood.max, demon.blood + cfg.blood.perSecond * dt)
	demon.flesh = math.max(0, demon.flesh - cfg.flesh.decayPerSecond * dt)

	-- Faim : trop longtemps sans repas, la puissance retombe d'un palier (au seuil du palier précédent), puis le délai repart.
	local hunger
	if demon.sinceFed >= cfg.souls.hungerSeconds then
		demon.sinceFed = 0
		local tier = Demon.Tier(cfg, demon.souls)
		if tier > 1 then
			demon.souls = cfg.tiers[tier - 1].souls
			hunger = { from = tier, to = tier - 1 }
		end
	end

	-- Régénération passive, seulement hors combat et hors soleil. La chair l'amplifie, la faim l'étouffe.
	local heal = 0
	if demon.sinceCombat >= cfg.combatSeconds and not opts.sun then
		local factor = cfg.regen.hungryFactor
		if demon.flesh > 0 then
			factor = 1 + cfg.regen.fleshBoost * demon.flesh / cfg.flesh.max
		end
		heal = (cfg.regen.base * factor + Demon.Bonuses(cfg, demon).regen) * dt
	end
	return { heal = heal, hunger = hunger }
end

-- Ce que le HUD affiche : jauges, palier, progression vers le suivant et repas du jour (rankIndex = numéro du grade du joueur).
function Demon.View(cfg, demon, rankIndex)
	cfg = settings(cfg)
	local index, tier = Demon.Tier(cfg, demon.souls)
	local nextTier = cfg.tiers[index + 1]
	return {
		blood = math.floor(demon.blood),
		bloodMax = cfg.blood.max,
		flesh = math.floor(demon.flesh),
		fleshMax = cfg.flesh.max,
		souls = demon.souls,
		soulsFloor = tier.souls,
		soulsNext = nextTier and nextTier.souls or nil,
		nextName = nextTier and nextTier.name or nil,
		tier = index,
		tierCount = #cfg.tiers,
		tierName = tier.name,
		hungry = demon.flesh <= 0,
		meals = demon.meals,
		mealsCap = Demon.DailyCap(cfg, rankIndex),
		costs = cfg.blood.costs,
		unlock = cfg.unlock,
	}
end

return Demon
