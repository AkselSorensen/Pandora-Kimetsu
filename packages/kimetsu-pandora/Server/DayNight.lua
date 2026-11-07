-- Cycle jour / nuit : 30 minutes de jour, 30 minutes de nuit. Le serveur garde l'heure (0 à 2400) et la diffuse aux joueurs.
-- Le jour va de 6h00 à 18h00 ; la nuit, de 18h00 à 6h00.

local DayNight = {}

DayNight.Time = 800 -- heure de départ (8h00)
DayNight.DAY_START = 600   -- 6h00
DayNight.DUSK = 1800       -- 18h00
DayNight.TICK_SECONDS = 5  -- l'heure est mise à jour (et diffusée) toutes les 5 secondes
-- 2400 unités d'heure en 60 minutes : 30 minutes de jour (1200 unités) et 30 minutes de nuit (1200 unités).
DayNight.UNITS_PER_SECOND = 2400 / 3600

-- Démons la nuit : bonus en pourcentage.
DayNight.DemonNight = { damage = 20, hp = 20 }
-- Démons au soleil (hors d'un abri) : dégâts toutes les `interval` secondes.
DayNight.Burn = { interval = 2, damage = 6 }

function DayNight.IsNight(time)
	time = time or DayNight.Time
	return time >= DayNight.DUSK or time < DayNight.DAY_START
end

-- Fait avancer l'heure de `seconds` secondes. Renvoie true si le jour ou la nuit a changé.
function DayNight.Advance(seconds)
	local wasNight = DayNight.IsNight()
	DayNight.Time = (DayNight.Time + seconds * DayNight.UNITS_PER_SECOND) % 2400
	return wasNight ~= DayNight.IsNight()
end

return DayNight
