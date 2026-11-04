-- Visualiseur d'animations, côté client : panneau HTML (Client/UI/animations.html) pour parcourir les animations des packs
-- et les jouer sur son personnage. Touche d'ouverture : Config.AnimViewer.key. La liste vient de Shared/Animations.lua.

local Config = Package.Require("Config.lua")
local Animations = Package.Require("Animations.lua")

local AnimViewer = { open = false }

function AnimViewer.IsOpen()
	return AnimViewer.open
end

-- Remplacée par Index.lua : vrai tant qu'aucun autre écran du jeu (menu, créateur, sac...) n'est ouvert.
AnimViewer.CanOpen = function()
	return true
end

if not Config.AnimViewer.enabled then
	return AnimViewer
end

-- Comme le HUD : le panneau ignore la souris tant qu'il est fermé.
local ui = WebUI("Animation viewer", "file://UI/animations.html", WidgetVisibility.VisibleNotHitTestable)
local ready = false
local closedAt = 0

local function setOpen(open)
	AnimViewer.open = open
	if not open then
		closedAt = os.clock()
	end
	Input.SetInputEnabled(not open)
	Input.SetMouseEnabled(open)
	ui:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	if open then
		ui:SetFocus()
	else
		ui:RemoveFocus()
	end
	if ready then
		ui:CallEvent("anim:open", open)
	end
end

ui:Subscribe("Ready", function()
	ready = true
	ui:CallEvent("anim:init", JSON.stringify({ key = Config.AnimViewer.key, packs = Animations.packs }))
	ui:CallEvent("anim:open", AnimViewer.open)
end)

ui:Subscribe("anim:close", function()
	setOpen(false)
end)

ui:Subscribe("anim:play", function(id, slot, loop, rate)
	Events.CallRemote("wakfu:animPlay", Reliability.Reliable, id, slot, loop, rate)
end)

ui:Subscribe("anim:stop", function(id)
	Events.CallRemote("wakfu:animStop", Reliability.Reliable, id)
end)

ui:Subscribe("anim:mark", function(id, mark)
	Events.CallRemote("wakfu:animMark", Reliability.Reliable, id, mark)
end)

-- La touche ne fait qu'ouvrir : la page ferme elle-même avec la même touche (sinon les deux se contrediraient).
-- Échap ferme aussi ici, au cas où la page n'aurait pas le focus.
Input.Subscribe("KeyPress", function(key_name)
	if key_name == Config.AnimViewer.key then
		if not AnimViewer.open and os.clock() - closedAt > 0.3 and AnimViewer.CanOpen() then
			setOpen(true)
		end
	elseif AnimViewer.open and key_name == "Escape" then
		setOpen(false)
	end
end)

return AnimViewer
