-- Logique de combat pure (aucun appel au moteur), donc testable seule.

local Combat = {}

-- Un sort est utilisable si son cooldown est écoulé pour ce joueur.
-- cooldowns : table { [spellId] = timestamp de la dernière utilisation }
function Combat.CanCast(cooldowns, spell, now)
	local last = cooldowns[spell.id]
	if last == nil then
		return true
	end
	return (now - last) >= spell.cooldown
end

-- Distance au carré entre deux positions {x, y, z}. Évite la racine carrée.
function Combat.DistanceSquared(a, b)
	local dx = a.x - b.x
	local dy = a.y - b.y
	local dz = a.z - b.z
	return dx * dx + dy * dy + dz * dz
end

-- Vrai si la cible est à portée du sort.
function Combat.InRange(origin, target, range)
	return Combat.DistanceSquared(origin, target) <= range * range
end

-- Dégâts finaux : le sort, modulé par le bonus de dégâts du joueur (en %, peut être négatif).
function Combat.Damage(spell, bonusPct)
	return math.floor(spell.damage * (1 + (bonusPct or 0) / 100))
end

-- Soigne : renvoie les PV après soin, plafonnés au maximum.
function Combat.Heal(hp, maxHp, amount)
	return math.min(maxHp, hp + amount)
end

-- Applique des dégâts et renvoie les PV restants (jamais négatifs).
function Combat.ApplyDamage(hp, damage)
	return math.max(0, hp - damage)
end

return Combat
