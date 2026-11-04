-- Joue les effets visuels des techniques et sert d'outil d'essai des effets cuits. Côté client uniquement : chaque joueur voit l'effet
-- chez lui (entités locales), le serveur n'envoie que l'identifiant de la technique, sa position et sa direction.
-- Un effet qui ne se charge pas est signalé une seule fois dans le journal du client et ne gêne rien d'autre.

local Vfx = Package.Require("VfxPlan.lua")

local VfxPlayer = {}

local TICK_MS = 33 -- une trajectoire est recalculée environ 30 fois par seconde
local warned = {}
local test = { index = 0, pattern = 1, color = 1 }

-- key regroupe plusieurs messages en un seul avertissement (par défaut, le message lui-même).
local function warnOnce(message, key)
	key = key or message
	if not warned[key] then
		warned[key] = true
		Console.Warn(message)
	end
end

-- Position d'un morceau à l'instant t (0 à 1) : sur sa trajectoire s'il suit un chemin, sinon à son point fixe.
local function place(piece, origin, yaw, t)
	local forward, right, up
	if piece.motion == "path" then
		forward, right, up = Vfx.Offset(piece.pattern, t, piece.range)
	else
		forward, right, up = piece.at[1], piece.at[2], piece.at[3]
	end
	local x, y, z = Vfx.World(origin, yaw + piece.yaw, forward, right, up)
	return Vector(x, y, z)
end

local function destroy(particle)
	if particle:IsValid() then
		particle:Destroy()
	end
end

-- Pose un mesh d'effet dans l'état voulu à l'instant t : place, taille, orientation et opacité (paramètre Fade du matériau).
local function poseMesh(mesh, piece, origin, yaw, t)
	local forward, right, up, scale, pitch, turn, roll, fade = Vfx.MeshAt(piece, t)
	local x, y, z = Vfx.World(origin, yaw, forward, right, up)
	mesh:SetLocation(Vector(x, y, z))
	mesh:SetRotation(Rotator(pitch, yaw + turn, roll))
	mesh:SetScale(Vector(scale, scale, scale))
	mesh:SetMaterialScalarParameter("Fade", fade)
end

-- Joue une forme lumineuse : entité locale sans collision, qui avance, grandit, tourne et s'estompe pendant la durée du morceau.
local function playMesh(piece, origin, yaw)
	local ok, mesh = pcall(function()
		local forward, right, up = Vfx.MeshAt(piece, 0)
		local x, y, z = Vfx.World(origin, yaw, forward, right, up)
		local created = StaticMesh(Vector(x, y, z), Rotator(0, yaw, 0), piece.asset, CollisionType.NoCollision)
		if piece.material then
			created:SetMaterial(piece.material, 0)
		end
		created:SetCastShadow(false)
		poseMesh(created, piece, origin, yaw, 0)
		return created
	end)
	if not ok or not mesh then
		warnOnce("Forme " .. piece.asset .. " impossible à jouer (le pack des formes est-il déployé ?) : " .. tostring(mesh), "mesh-load")
		return
	end
	local startedAt = os.clock()
	local timer
	timer = Timer.SetInterval(function()
		local t = (os.clock() - startedAt) / piece.duration
		if t >= 1 or not mesh:IsValid() then
			Timer.ClearInterval(timer)
			destroy(mesh)
			return
		end
		local posed, problem = pcall(poseMesh, mesh, piece, origin, yaw, t)
		if not posed then -- une forme qu'on ne peut pas animer disparaît, sans gêner le reste
			warnOnce("Forme " .. piece.asset .. " impossible à animer : " .. tostring(problem), "mesh-pose")
			Timer.ClearInterval(timer)
			destroy(mesh)
		end
	end, TICK_MS)
end

local function playPiece(piece, origin, yaw)
	if piece.kind == "mesh" then
		playMesh(piece, origin, yaw)
		return
	end
	-- auto_destroy = false : la durée est celle du plan, un système qui boucle ne reste donc jamais actif.
	local ok, particle = pcall(function()
		return Particle(place(piece, origin, yaw, 0), Rotator(0, yaw + piece.yaw, 0), piece.asset, false, true)
	end)
	if not ok or not particle then
		warnOnce("Effet " .. piece.asset .. " impossible à jouer : " .. tostring(particle))
		return
	end
	if piece.motion ~= "path" then
		Timer.SetTimeout(function()
			destroy(particle)
		end, piece.duration * 1000)
		return
	end
	local startedAt = os.clock()
	local timer
	timer = Timer.SetInterval(function()
		local t = (os.clock() - startedAt) / piece.duration
		if t >= 1 or not particle:IsValid() then
			Timer.ClearInterval(timer)
			destroy(particle)
			return
		end
		particle:SetLocation(place(piece, origin, yaw, t))
	end, TICK_MS)
end

-- Joue une liste de morceaux autour de origin = { x, y, z } (centre du personnage) et du lacet en degrés.
function VfxPlayer.Play(pieces, origin, yaw)
	for _, piece in ipairs(pieces) do
		playPiece(piece, origin, yaw)
	end
end

-- Joue l'effet d'une technique d'après son identifiant.
function VfxPlayer.PlaySpell(spellId, origin, yaw)
	VfxPlayer.Play(Vfx.PlanForSpell(spellId).pieces, origin, yaw)
end

-- Outil d'essai : joue l'effet suivant de la banque (ou change de trajectoire si changePattern) et renvoie le texte à afficher.
function VfxPlayer.Test(changePattern, origin, yaw)
	local bank = Vfx.Bank()
	if #bank == 0 then
		return "Aucun effet cuit pour l'instant : cuis les packs de VFX avec Forge"
	end
	if changePattern then
		test.pattern = test.pattern % #Vfx.Patterns + 1
	end
	if not changePattern or test.index == 0 then
		test.index = test.index % #bank + 1
	end
	local entry = bank[test.index]
	local pattern = Vfx.Patterns[test.pattern]
	if entry.kind == "mesh" then -- pour une forme, la touche de trajectoire change la couleur
		if changePattern then
			test.color = test.color % #Vfx.MeshColors + 1
		end
		local color = Vfx.MeshColors[test.color]
		VfxPlayer.Play(Vfx.TestPieces(entry, pattern, color), origin, yaw)
		return string.format("Effet %d/%d : %s (%s)", test.index, #bank, entry.id, color)
	end
	VfxPlayer.Play(Vfx.TestPieces(entry, pattern), origin, yaw)
	return string.format("Effet %d/%d : %s (%s)", test.index, #bank, entry.id, entry.kind == "trail" and pattern or entry.kind)
end

-- Aperçu d'une traînée choisie dans le menu : un coup balayé joué chez le joueur seulement. Sans effet pour « auto » et « none ».
function VfxPlayer.Preview(choice, origin, yaw)
	for _, entry in ipairs(Vfx.Bank()) do
		if entry.id == choice and entry.kind == "trail" then
			VfxPlayer.Play(Vfx.TestPieces(entry, "arc"), origin, yaw)
			return
		end
	end
end

return VfxPlayer
