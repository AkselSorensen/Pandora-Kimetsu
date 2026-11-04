-- Zoom de la caméra à la troisième personne : molette de la souris (ou PageHaut / PageBas).
-- La distance choisie est gardée quand on ferme un écran qui remet la caméra à zéro.

local Zoom = {}

local DEFAULT_ARM = 300 -- distance de caméra de base, en centimètres
local MIN_ARM = 60
local MAX_ARM = 700
local STEP = 40

local arm = nil -- nil tant que le joueur n'a pas zoomé
local isBusy = function()
	return false
end

local function apply()
	local localPlayer = Client.GetLocalPlayer()
	if localPlayer and arm then
		localPlayer:SetCameraArmLength(arm)
	end
end

local function zoomBy(direction)
	if isBusy() then
		return
	end
	arm = math.max(MIN_ARM, math.min(MAX_ARM, (arm or DEFAULT_ARM) - direction * STEP))
	apply()
end

-- isBusyFn() renvoie true quand un écran du jeu (menu, créateur, inventaire...) est ouvert.
function Zoom.Init(isBusyFn)
	isBusy = isBusyFn
	Input.Subscribe("MouseScroll", function(_, _, delta)
		if delta and delta ~= 0 then
			zoomBy(delta > 0 and 1 or -1)
		end
	end)
	Input.Subscribe("KeyPress", function(key_name)
		if key_name == "PageUp" then
			zoomBy(1)
		elseif key_name == "PageDown" then
			zoomBy(-1)
		end
	end)
end

-- À appeler après un ResetCamera() pour retrouver la distance choisie.
Zoom.Reapply = apply

return Zoom
