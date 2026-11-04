-- Côté client : entrées clavier et affichage. Aucune décision de jeu ici.

local Classes = Package.Require("Classes.lua")
local Items = Package.Require("Items.lua")
local Config = Package.Require("Config.lua")
local Zoom = Package.Require("Zoom.lua")
local AnimViewer = Package.Require("AnimViewer.lua")
local VfxPlayer = Package.Require("VfxPlayer.lua")
local VfxPlan = Package.Require("VfxPlan.lua")

-- Apparences spéciales proposées par le créateur (vide tant qu'aucun pack n'est utilisable).
local skinNames = {}
for name in pairs(Config.Skins) do
	table.insert(skinNames, name)
end
table.sort(skinNames)
local Quests = Package.Require("Quests.lua")

-- Touches 1 à 4 : techniques de la classe active.
local SPELL_KEYS = { ["One"] = 1, ["Two"] = 2, ["Three"] = 3, ["Four"] = 4 }

-- F1 à F4 : changer de classe (les quatre premières de l'écran de reroll).
local CLASS_KEYS = {}
for i, key in ipairs({ "F1", "F2", "F3", "F4" }) do
	CLASS_KEYS[key] = Classes.RerollOrder[i]
end

-- E : interagir avec le PNJ le plus proche.
-- F5 : accepter la première quête proposée. F6 : reroll au forgeron.
local dialog = nil

-- HUD en HTML (Client/UI). Il ignore la souris pour ne pas gêner le jeu.
local hud = WebUI("Kimetsu HUD", "file://UI/index.html", WidgetVisibility.VisibleNotHitTestable)
local hudReady = false
local pending = {}

-- Les tables passent au HUD en JSON pour garder la même forme côté JavaScript.
local function toHud(eventName, value)
	local payload = type(value) == "table" and JSON.stringify(value) or value
	if hudReady then
		hud:CallEvent(eventName, payload)
	else
		table.insert(pending, { eventName, payload })
	end
end

-- Tailles de traînée proposées par le menu (Config.Vfx.trail.sizes).
local trailSizes = {}
for _, size in ipairs(Config.Vfx.trail.sizes) do
	trailSizes[#trailSizes + 1] = { id = size.id, label = size.label }
end

hud:Subscribe("Ready", function()
	hudReady = true
	toHud("wakfu:init", { classes = Classes.List, quests = Quests.List, items = Items.List, rerollOrder = Classes.RerollOrder, equipSlots = Items.EquipSlots, slotCount = Items.SlotCount, maxWeight = Items.MaxWeight, skins = skinNames, blades = Items.BladeList, forgeCost = Config.Forge.cost, trails = VfxPlan.TrailList(), trailSizes = trailSizes, trailKey = Config.Vfx.menuKey, camps = Classes.Camps, campOrder = Classes.CampOrder, demonKey = Config.Demon.devourKey })
	for _, event in ipairs(pending) do
		hud:CallEvent(event[1], event[2])
	end
	pending = {}
end)

-- PV : lus sur le personnage contrôlé, mis à jour à chaque changement.
local function sendHealth(character)
	toHud("wakfu:health", { hp = character:GetHealth(), maxHp = character:GetMaxHealth() })
end

local function watchCharacter(character)
	if not character then
		return
	end
	sendHealth(character)
	character:Subscribe("HealthChange", function(self)
		sendHealth(self)
	end)
	character:Subscribe("Respawn", function(self)
		sendHealth(self)
	end)
end

-- Portrait : un SceneCapture qui ne rend que notre personnage, vu de face au niveau de la tête.
local portrait = nil
local PORTRAIT_SIZE = 256

local function updatePortrait(character)
	if not character or not character:IsValid() then
		return
	end
	local rotation = character:GetRotation()
	local forward = rotation:GetForwardVector()
	local location = character:GetLocation() + forward * 75 + Vector(0, 0, 55)

	if not portrait then
		portrait = SceneCapture(location, Rotator(0, 0, 0), PORTRAIT_SIZE, PORTRAIT_SIZE, -1, 1000, 35)
	end
	portrait:SetLocation(location)
	portrait:SetRotation(Rotator(0, rotation.Yaw + 180, 0))
	portrait:ClearRenderActors()
	portrait:AddRenderActor(character)
	portrait:CaptureScene()
	portrait:EncodeToBase64Async(ImageFormat.PNG, function(base64)
		toHud("wakfu:portrait", "data:image/png;base64," .. base64)
	end)
end

-- Rafraîchi une fois par seconde : suit les changements de classe et de mesh.
Timer.SetInterval(function()
	local localPlayer = Client.GetLocalPlayer()
	if localPlayer then
		updatePortrait(localPlayer:GetControlledCharacter())
	end
end, 1000)

Client.Subscribe("SpawnLocalPlayer", function(localPlayer)
	localPlayer:Subscribe("Possess", function(_, character)
		watchCharacter(character)
	end)
end)

-- Rechargement du package : le joueur et son personnage existent déjà.
Package.Subscribe("Load", function()
	local localPlayer = Client.GetLocalPlayer()
	if localPlayer then
		localPlayer:Subscribe("Possess", function(_, character)
			watchCharacter(character)
		end)
		watchCharacter(localPlayer:GetControlledCharacter())
	end
end)

-- Menu pause : la souris et le focus passent au HUD tant qu'il est ouvert.
local menuOpen = false
local menuClosedAt = 0
local nativeOpen = false

local function setMenu(open)
	menuOpen = open
	if not open then
		menuClosedAt = os.clock()
	end
	Input.SetInputEnabled(not open)
	hud:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	Input.SetMouseEnabled(open)
	if open then
		hud:SetFocus()
	else
		hud:RemoveFocus()
	end
	toHud("wakfu:menuOpen", open)
end

-- Créateur de personnage : même principe que le menu, sans voile devant le joueur.
local creatorOpen = false

local creatorAimTimer
local function setCreator(open)
	creatorOpen = open
	if not open then
		menuClosedAt = os.clock()
	end
	Input.SetInputEnabled(not open)
	hud:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	Input.SetMouseEnabled(open)
	if open then
		hud:SetFocus()
	else
		hud:RemoveFocus()
	end

	-- Le serveur isole le personnage sur une plateforme dans le ciel ; la caméra reste derrière lui,
	-- un peu rapprochée, et il se tourne vers elle.
	local localPlayer = Client.GetLocalPlayer()
	if open and localPlayer then
		local yaw = localPlayer:GetCameraRotation().Yaw
		localPlayer:SetCameraArmLength(280)
		localPlayer:SetCameraSocketOffset(Vector(0, 0, 40))
		-- Caméra à hauteur d'yeux : même direction, mais à plat, pour voir le personnage bien en face.
		localPlayer:SetCameraRotation(Rotator(0, yaw, 0))
		Events.CallRemote("wakfu:creatorEnter", Reliability.Reliable, yaw)
		-- On renvoie en continu l'angle réel de la caméra : le personnage la regarde toujours droit dans les yeux.
		creatorAimTimer = Timer.SetInterval(function()
			Events.CallRemote("wakfu:creatorAim", Reliability.Unreliable, localPlayer:GetCameraRotation().Yaw)
		end, 150)
	elseif localPlayer then
		if creatorAimTimer then
			Timer.ClearInterval(creatorAimTimer)
			creatorAimTimer = nil
		end
		localPlayer:ResetCamera()
		Zoom.Reapply()
		Events.CallRemote("wakfu:creatorExit", Reliability.Reliable)
	end
	toHud("wakfu:creatorOpen", open)
end

-- Inventaire (touche I) : le personnage est isolé sur la plateforme du créateur, décalé vers la droite
-- pour laisser la place aux emplacements d'équipement à gauche.
local inventoryOpen = false
-- Réglages mesurés en jeu (écran 16:9) : à 115 cm de bras, le personnage mesure ~56 % de la hauteur d écran ;
-- décalage -100 le plaçait à 61 % de la largeur, hauteur +5 trop bas. Plus le décalage est négatif, plus il va à droite.
local INVENTORY_CAMERA_ARM = 115
local INVENTORY_CAMERA_SHIFT = -146
local INVENTORY_CAMERA_HEIGHT = -65

local function setInventory(open)
	inventoryOpen = open
	Input.SetInputEnabled(not open)
	hud:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	Input.SetMouseEnabled(open)
	if open then
		hud:SetFocus()
	else
		hud:RemoveFocus()
	end

	local localPlayer = Client.GetLocalPlayer()
	if open and localPlayer then
		local yaw = localPlayer:GetCameraRotation().Yaw
		localPlayer:SetCameraArmLength(INVENTORY_CAMERA_ARM)
		localPlayer:SetCameraSocketOffset(Vector(0, INVENTORY_CAMERA_SHIFT, INVENTORY_CAMERA_HEIGHT))
		localPlayer:SetCameraRotation(Rotator(0, yaw, 0))
		Events.CallRemote("wakfu:creatorEnter", Reliability.Reliable, yaw)
		creatorAimTimer = Timer.SetInterval(function()
			Events.CallRemote("wakfu:creatorAim", Reliability.Unreliable, localPlayer:GetCameraRotation().Yaw)
		end, 150)
	elseif localPlayer then
		if creatorAimTimer then
			Timer.ClearInterval(creatorAimTimer)
			creatorAimTimer = nil
		end
		localPlayer:ResetCamera()
		Zoom.Reapply()
		Events.CallRemote("wakfu:creatorExit", Reliability.Reliable)
	end
	toHud("wakfu:inventoryOpen", open)
end

hud:Subscribe("wakfu:inventoryClose", function()
	setInventory(false)
end)

-- Actions du HUD : le serveur valide chacune et renvoie le sac mis à jour.
for _, action in ipairs({ "invUse", "invUnequip", "invMove", "invDrop", "invDelete", "invGive" }) do
	hud:Subscribe("wakfu:" .. action, function(...)
		Events.CallRemote("wakfu:" .. action, Reliability.Reliable, ...)
	end)
end

Events.SubscribeRemote("wakfu:inventory", function(payload)
	toHud("wakfu:inventory", payload)
end)

Events.SubscribeRemote("wakfu:notice", function(text)
	toHud("wakfu:toast", text)
end)

-- Forge des lames Nichirin (PNJ forgeron) : panneau plein écran ; le serveur vérifie la distance, le prix et la place dans le sac.
local forgeOpen = false

local function setForge(open)
	forgeOpen = open
	Input.SetInputEnabled(not open)
	hud:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	Input.SetMouseEnabled(open)
	if open then
		hud:SetFocus()
	else
		hud:RemoveFocus()
	end
	toHud("wakfu:forgeOpen", open)
end

-- Menu de la traînée de l'arme (touche Config.Vfx.menuKey ou bouton de l'inventaire) : panneau plein écran ; le serveur valide le choix.
local trailOpen = false

local function setTrail(open)
	trailOpen = open
	if not open then
		menuClosedAt = os.clock()
	end
	Input.SetInputEnabled(not open)
	hud:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	Input.SetMouseEnabled(open)
	if open then
		hud:SetFocus()
	else
		hud:RemoveFocus()
	end
	toHud("wakfu:trailOpen", open)
end

-- Choix du camp (première connexion) : écran plein et obligatoire, sans moyen de le fermer tant que le serveur n'a pas enregistré le choix.
local campOpen = false

local function setCamp(open)
	campOpen = open
	if not open then
		menuClosedAt = os.clock()
	end
	Input.SetInputEnabled(not open)
	hud:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	Input.SetMouseEnabled(open)
	if open then
		hud:SetFocus()
	else
		hud:RemoveFocus()
	end
	toHud("wakfu:campOpen", open)
end

Events.SubscribeRemote("wakfu:openCamp", function()
	if not campOpen then
		setCamp(true)
	end
end)

-- Écran de bienvenue à l'arrivée (planche « Tengen — Bienvenue ») : il bloque les touches comme l'écran de camp (campOpen),
-- puis « Commencer » ou « Sélection de personnage » le ferment ; sans camp choisi, l'écran de choix du camp suit.
local welcomeOpen = false
local knownCamp = nil -- dernier camp reçu dans wakfu:state

local function setWelcome(open)
	welcomeOpen = open
	campOpen = open
	if not open then
		menuClosedAt = os.clock()
	end
	Input.SetInputEnabled(not open)
	hud:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	Input.SetMouseEnabled(open)
	if open then
		hud:SetFocus()
	else
		hud:RemoveFocus()
	end
	toHud("wakfu:welcomeOpen", open)
end

Events.SubscribeRemote("wakfu:openWelcome", function()
	if not campOpen then
		setWelcome(true)
	end
end)

hud:Subscribe("wakfu:welcomeStart", function()
	if welcomeOpen then
		setWelcome(false)
		if not knownCamp then
			setCamp(true)
		end
	end
end)

hud:Subscribe("wakfu:welcomeCharacter", function()
	if welcomeOpen then
		setWelcome(false)
		if not knownCamp then
			setCamp(true) -- le camp se choisit avant tout le reste
		else
			setCreator(true)
		end
	end
end)

hud:Subscribe("wakfu:chooseCamp", function(camp)
	Events.CallRemote("wakfu:chooseCamp", Reliability.Reliable, camp)
end)

-- Jauges du démon (sang, chair, âmes) et geste de dévoration : le serveur décide, le HUD affiche.
Events.SubscribeRemote("wakfu:demon", function(view)
	toHud("wakfu:demon", view)
end)

Events.SubscribeRemote("wakfu:devourStart", function(name, seconds, gain)
	toHud("wakfu:devourStart", { name = name, seconds = seconds, gain = gain })
end)

Events.SubscribeRemote("wakfu:devourStop", function()
	toHud("wakfu:devourStop", "")
end)

-- Reroll de classe (PNJ Maître des respirations) : écran plein, sans plateforme ; le serveur applique le changement.
local rerollOpen = false

local function setReroll(open)
	rerollOpen = open
	Input.SetInputEnabled(not open)
	hud:SetVisibility(open and WidgetVisibility.Visible or WidgetVisibility.VisibleNotHitTestable)
	Input.SetMouseEnabled(open)
	if open then
		hud:SetFocus()
	else
		hud:RemoveFocus()
	end
	toHud("wakfu:rerollOpen", open)
end

Events.SubscribeRemote("wakfu:openClassReroll", function()
	if not campOpen and not menuOpen and not creatorOpen and not inventoryOpen and not rerollOpen and not forgeOpen and not trailOpen then
		setReroll(true)
	end
end)

Events.SubscribeRemote("wakfu:openForge", function()
	if not campOpen and not menuOpen and not creatorOpen and not inventoryOpen and not rerollOpen and not forgeOpen and not trailOpen then
		setForge(true)
	end
end)

hud:Subscribe("wakfu:forgeClose", function()
	setForge(false)
end)

hud:Subscribe("wakfu:trailClose", function()
	setTrail(false)
end)

hud:Subscribe("wakfu:trailSize", function(sizeId)
	Events.CallRemote("wakfu:trailSize", Reliability.Reliable, sizeId)
end)

-- Bouton « Traînée de l'arme » de l'inventaire : on referme l'inventaire, puis le menu s'ouvre à sa place.
hud:Subscribe("wakfu:trailRequest", function()
	if inventoryOpen then
		setInventory(false)
	end
	if not campOpen and not menuOpen and not creatorOpen and not rerollOpen and not forgeOpen and not trailOpen then
		setTrail(true)
	end
end)

-- Le choix part au serveur, qui l'applique à l'arme tenue ; un aperçu de la traînée se joue tout de suite devant nous.
hud:Subscribe("wakfu:trailChoose", function(choice)
	Events.CallRemote("wakfu:trailChoose", Reliability.Reliable, choice)
	local localPlayer = Client.GetLocalPlayer()
	local character = localPlayer and localPlayer:GetControlledCharacter()
	if character and character:IsValid() then
		local location = character:GetLocation()
		VfxPlayer.Preview(choice, { x = location.X, y = location.Y, z = location.Z }, character:GetRotation().Yaw)
	end
end)

hud:Subscribe("wakfu:forgeBuy", function(bladeId)
	Events.CallRemote("wakfu:forgeBuy", Reliability.Reliable, bladeId)
end)

hud:Subscribe("wakfu:rerollClose", function()
	setReroll(false)
end)

hud:Subscribe("wakfu:classReroll", function(className)
	Events.CallRemote("wakfu:classReroll", Reliability.Reliable, className)
end)

-- Le HUD envoie chaque choix du créateur : le serveur valide et l'applique au personnage.
hud:Subscribe("wakfu:create", function(className, gender, colorIndex, nick, skin)
	Events.CallRemote("wakfu:create", Reliability.Reliable, className, gender, colorIndex, nick, skin)
end)

hud:Subscribe("wakfu:creatorClose", function()
	setCreator(false)
end)

hud:Subscribe("wakfu:menu", function(action)
	if action == "resume" then
		setMenu(false)
	elseif action == "settings" then
		-- Réglages natifs de Nanos : on laisse Échap les fermer.
		setMenu(false)
		nativeOpen = true
		Client.OpenEscapeMenu(true)
	elseif action == "disconnect" then
		Client.Disconnect()
	end
end)

-- Échap est bloqué (retour false) pour que le menu natif de Nanos ne s'ouvre pas à côté du nôtre.
local function isMenuKey(key_name)
	return key_name == "Escape" or key_name == "F10"
end

Input.Subscribe("KeyDown", function(key_name)
	if key_name == "Escape" and not nativeOpen then
		return false
	end
end)

Input.Subscribe("KeyUp", function(key_name)
	if key_name == "Escape" and not nativeOpen then
		return false
	end
end)

-- Le visualiseur d'animations ne s'ouvre que si aucun autre écran n'est ouvert, et garde alors tout le clavier.
AnimViewer.CanOpen = function()
	return not (campOpen or menuOpen or creatorOpen or inventoryOpen or rerollOpen or forgeOpen or trailOpen)
end

Input.Subscribe("KeyPress", function(key_name)
	if AnimViewer.IsOpen() then
		return
	end
	if nativeOpen and key_name == "Escape" then
		nativeOpen = false
		return
	end

	-- Tant que le camp n'est pas choisi, aucune touche ne fait rien d'autre.
	if campOpen then
		return false
	end

	if rerollOpen then
		if key_name == "Escape" then
			setReroll(false)
		end
		return false
	end

	if forgeOpen then
		-- Le HUD gère la recherche de lame au clavier ; Échap ferme ici.
		if key_name == "Escape" then
			setForge(false)
		end
		return false
	end

	if trailOpen then
		if key_name == "Escape" or key_name == (Config.Vfx and Config.Vfx.menuKey) then
			setTrail(false)
		end
		return false
	end

	if inventoryOpen then
		-- Le HUD ferme avec I (hors saisie dans la recherche) ; Échap ferme ici.
		if key_name == "Escape" then
			setInventory(false)
		end
		return false
	end

	if key_name == "I" and not menuOpen and not creatorOpen and os.clock() - menuClosedAt > 0.3 then
		setInventory(true)
		return false
	end

	if creatorOpen then
		-- Pendant la création, le HUD gère le clavier (saisie du nom) et ferme avec Échap.
		if key_name == "Escape" then
			setCreator(false)
		end
		return false
	end

	if Config.Vfx and key_name == Config.Vfx.menuKey and not menuOpen and not creatorOpen and os.clock() - menuClosedAt > 0.3 then
		setTrail(true)
		return false
	end

	if key_name == "C" and not menuOpen and os.clock() - menuClosedAt > 0.3 then
		setCreator(true)
		return false
	end

	if isMenuKey(key_name) then
		-- Le HUD ferme lui-même le menu avec Échap : on évite de le rouvrir dans la foulée.
		if not menuOpen and os.clock() - menuClosedAt > 0.3 then
			setMenu(true)
		elseif menuOpen then
			setMenu(false)
		end
		return false
	end

	local index = SPELL_KEYS[key_name]
	if index then
		Events.CallRemote("wakfu:castIndex", Reliability.Reliable, index)
		return
	end

	-- Essai des effets cuits (Config.Vfx.test) : un effet de la banque se joue devant le joueur, son nom s'affiche.
	local vfxTest = Config.Vfx and Config.Vfx.test
	if vfxTest and vfxTest.enabled and (key_name == vfxTest.nextEffect or key_name == vfxTest.nextPattern) then
		local localPlayer = Client.GetLocalPlayer()
		local character = localPlayer and localPlayer:GetControlledCharacter()
		if character and character:IsValid() then
			local location = character:GetLocation()
			toHud("wakfu:toast", VfxPlayer.Test(key_name == vfxTest.nextPattern, { x = location.X, y = location.Y, z = location.Z }, character:GetRotation().Yaw))
		end
		return
	end

	-- Essai des armes : flèches gauche / droite pour l'arme précédente / suivante (Config.WeaponCycle).
	local cycle = Config.WeaponCycle
	if cycle and cycle.enabled and (key_name == cycle.previous or key_name == cycle.next) then
		Events.CallRemote("wakfu:weaponCycle", Reliability.Reliable, key_name == cycle.next and 1 or -1)
		return
	end

	local className = CLASS_KEYS[key_name]
	if className and Classes.Get(className) then
		Events.CallRemote("wakfu:chooseClass", Reliability.Reliable, className)
		return
	end

	if key_name == "E" then
		Events.CallRemote("wakfu:interact", Reliability.Reliable)
	elseif key_name == Config.Demon.devourKey then -- le serveur ne répond qu'à un démon
		Events.CallRemote("wakfu:devour", Reliability.Reliable)
	elseif key_name == "F5" and dialog and dialog.offered[1] then
		Events.CallRemote("wakfu:acceptQuest", Reliability.Reliable, dialog.offered[1])
	elseif key_name == "F6" then
		Events.CallRemote("wakfu:reroll", Reliability.Reliable)
	end
end)

-- Réception des réponses du serveur, affichées par le HUD.
Events.SubscribeRemote("wakfu:state", function(state)
	toHud("wakfu:state", state)
	knownCamp = state.camp
	if campOpen and not welcomeOpen and state.camp then -- le serveur a enregistré le camp : l'écran de choix se ferme
		setCamp(false)
	end
end)

-- Effet visuel d'une technique lancée près de nous (par nous ou par un autre joueur).
Events.SubscribeRemote("wakfu:fx", function(spellId, x, y, z, yaw)
	VfxPlayer.PlaySpell(spellId, { x = x, y = y, z = z }, yaw)
end)

Events.SubscribeRemote("wakfu:cast", function(spellId, cooldown)
	toHud("wakfu:cast", { id = spellId, cooldown = cooldown })
end)

Events.SubscribeRemote("wakfu:dialog", function(npcId, name, text, offered, services)
	dialog = { npcId = npcId, name = name, text = text, offered = offered, services = services }
	toHud("wakfu:dialog", dialog)
end)

Events.SubscribeRemote("wakfu:openCreator", function()
	if not campOpen and not menuOpen and not creatorOpen then
		setCreator(true)
	end
end)

Events.SubscribeRemote("wakfu:questAccepted", function(questId)
	dialog = nil
	toHud("wakfu:dialogClose", "")
	toHud("wakfu:toast", "Quête acceptée : " .. Quests.Get(questId).name)
end)

Events.SubscribeRemote("wakfu:questDone", function(questId)
	local quest = Quests.Get(questId)
	toHud("wakfu:toast", "Quête terminée : " .. quest.name .. " (+" .. (quest.reward.kamas or 0) .. " yens, +" .. (quest.reward.xp or 0) .. " XP)")
end)

Events.SubscribeRemote("wakfu:rerolled", function(stats)
	toHud("wakfu:toast", "Entraînement : PV +" .. stats.maxHp .. ", dégâts " .. stats.damagePct .. "%, vitesse +" .. stats.speed .. "%")
end)

Events.SubscribeRemote("wakfu:rerollFailed", function()
	toHud("wakfu:toast", "Pas assez de yens pour l'entraînement")
end)

-- Molette de la souris : zoom de la caméra, sauf quand un écran du jeu est ouvert.
Zoom.Init(function()
	return campOpen or menuOpen or creatorOpen or inventoryOpen or rerollOpen or forgeOpen or trailOpen or AnimViewer.IsOpen()
end)
