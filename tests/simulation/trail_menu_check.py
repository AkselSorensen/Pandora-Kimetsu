import sys

from lupa import LuaRuntime

from pathlib import Path

REPO_RP = (Path(__file__).resolve().parents[2] / "packages" / "wakfu-rp").as_posix()
RP = {"depot": REPO_RP}

CODE = r'''
local ROOT = ...
local Any = {}
setmetatable(Any, { __index = function() return Any end, __call = function() return Any end, __add = function() return Any end, __sub = function() return Any end,
	__mul = function() return Any end, __div = function() return Any end, __lt = function() return false end, __le = function() return false end, __concat = function() return "" end })
local env = {}
setmetatable(env, { __index = function(_, k) local v = _G[k]; if v == nil then return Any end; return v end })
local hudEvents, uiHandlers, remoteCalls, remoteHandlers, keyHandlers, spawned = {}, {}, {}, {}, {}, {}
local state = { input = true, mouse = false, now = 100 }
env.os = { clock = function() return state.now end }
env.JSON = { stringify = function(t) return t end }
env.Reliability = { Reliable = 1, Unreliable = 2 }
env.WidgetVisibility = { Visible = 1, VisibleNotHitTestable = 2 }
local ui = {}
function ui:Subscribe(name, fn) uiHandlers[name] = fn end
function ui:CallEvent(name, payload) hudEvents[#hudEvents + 1] = { name = name, payload = payload } end
function ui:SetVisibility(v) self.visibility = v end
function ui:SetFocus() self.focus = true end
function ui:RemoveFocus() self.focus = false end
env.WebUI = function() return ui end
env.Input = { Subscribe = function(name, fn) keyHandlers[name] = keyHandlers[name] or {}; table.insert(keyHandlers[name], fn) end,
	SetInputEnabled = function(v) state.input = v end, SetMouseEnabled = function(v) state.mouse = v end }
env.Events = setmetatable({ SubscribeRemote = function(name, fn) remoteHandlers[name] = fn end, CallRemote = function(name, ...) remoteCalls[#remoteCalls + 1] = { name = name, args = { ... } } end, Subscribe = function() end },
	{ __index = function() return function() end end })
local character = {}
function character:IsValid() return true end
function character:GetLocation() return { X = 0, Y = 0, Z = 100 } end
function character:GetRotation() return { Yaw = 0 } end
function character:Subscribe() end
local player = setmetatable({ GetControlledCharacter = function() return character end, GetCameraRotation = function() return { Yaw = 0 } end },
	{ __index = function() return function() return Any end end })
env.Client = { GetLocalPlayer = function() return player end, Subscribe = function() end, OpenEscapeMenu = function() end, Disconnect = function() end }
env.Timer = { SetInterval = function() return 1 end, ClearInterval = function() end, SetTimeout = function() return 1 end }
env.Vector = function(x, y, z) return { X = x, Y = y, Z = z } end
env.Rotator = function(p, y, r) return { Pitch = p, Yaw = y, Roll = r } end
env.Particle = function(_, _, asset)
	local p = { asset = asset }
	function p:IsValid() return true end
	function p:Destroy() end
	function p:SetLocation() end
	spawned[#spawned + 1] = p
	return p
end
env.Console = { Warn = function() end, Log = function() end }
local cache = {}
env.Package = { Subscribe = function() end, Require = function(name)
	if cache[name] == nil then local f, err
		for _, dir in ipairs({ "Client", "Shared" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
		assert(f, tostring(err)); cache[name] = f() end
	return cache[name] end }

local KEY = env.Package.Require("Config.lua").Vfx.menuKey
assert(loadfile(ROOT .. "/Client/Index.lua", "t", env))()
uiHandlers.Ready()

local out = {}
local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local function say(text) out[#out + 1] = text end
local function press(key)
	local blocked = false
	for _, fn in ipairs(keyHandlers.KeyPress or {}) do if fn(key) == false then blocked = true end end
	return blocked
end
local function last(name) for i = #hudEvents, 1, -1 do if hudEvents[i].name == name then return hudEvents[i].payload end end end
local function count(name) local n = 0 for _, e in ipairs(hudEvents) do if e.name == name then n = n + 1 end end return n end
local function calls(name) local n = 0 for _, c in ipairs(remoteCalls) do if c.name == name then n = n + 1 end end return n end
local function lastCall(name) for i = #remoteCalls, 1, -1 do if remoteCalls[i].name == name then return remoteCalls[i] end end end
local function settle() state.now = state.now + 1 end

-- Donnees envoyees au menu
local init = last("wakfu:init")
check(init and #init.trails == 28 and #init.trailSizes == 3, "le HUD recoit 28 traînees et 3 tailles : " .. tostring(init and #init.trails) .. "/" .. tostring(init and #init.trailSizes))
check(init.trailSizes[1].id == "fine" and init.trailSizes[1].label == "Fine" and init.trails[1].group == "Élémentaires" and init.trails[11].group == "Sabre", "tailles et groupes (les elementaires d'abord)")
say("donnees : " .. #init.trails .. " traînees (elementaires d'abord) et tailles " .. init.trailSizes[1].label .. " / " .. init.trailSizes[2].label .. " / " .. init.trailSizes[3].label)

-- Touche J : ouvre le menu, bloque le reste du clavier, Echap le ferme
check(press(KEY) == true and last("wakfu:trailOpen") == true and state.input == false and state.mouse == true and ui.visibility == 1 and ui.focus == true, "J ouvre le menu : souris et focus sur le HUD, jeu bloque")
check(press("E") == true and press("C") == true and press("I") == true and press("One") == true, "le menu ouvert garde le clavier : E, C, I, 1 ne font rien")
check(count("wakfu:inventoryOpen") == 0 and count("wakfu:creatorOpen") == 0 and calls("wakfu:interact") == 0 and calls("wakfu:castIndex") == 0, "rien d'autre ne s'ouvre ni ne part au serveur")
press("Escape")
check(last("wakfu:trailOpen") == false and state.input == true and state.mouse == false and ui.focus == false, "Echap ferme le menu et rend le jeu")
check(KEY == "J", "la touche du menu est J")
say("touche " .. KEY .. " : ouvre, bloque le clavier, Echap ferme et rend la main")

-- Choix et taille : le serveur les recoit, un apercu se joue devant le joueur
settle(); press(KEY)
uiHandlers["wakfu:trailChoose"]("vefects::NS_Trail_Fire")
local choose = lastCall("wakfu:trailChoose")
check(choose and choose.args[1] == 1 and choose.args[2] == "vefects::NS_Trail_Fire", "le choix part au serveur en fiable")
check(#spawned == 1 and spawned[1].asset == "vefects::NS_Trail_Fire", "un apercu de la traînee se joue chez le joueur")
uiHandlers["wakfu:trailChoose"]("auto"); uiHandlers["wakfu:trailChoose"]("none")
check(#spawned == 1 and calls("wakfu:trailChoose") == 3, "auto et none partent au serveur sans apercu")
uiHandlers["wakfu:trailSize"]("fine")
local size = lastCall("wakfu:trailSize")
check(size and size.args[1] == 1 and size.args[2] == "fine", "la taille part au serveur en fiable")
uiHandlers["wakfu:trailClose"]()
check(last("wakfu:trailOpen") == false and state.input == true, "le bouton Fermer du menu le ferme")
say("choix : vefects::NS_Trail_Fire envoye + apercu ; auto/none sans apercu ; taille envoyee ; Fermer ferme")

-- Depuis l'inventaire : le bouton referme le sac puis ouvre le menu
settle(); check(press("I") == true and last("wakfu:inventoryOpen") == true, "I ouvre l'inventaire")
check(press(KEY) == true and last("wakfu:trailOpen") ~= true, "J est ignoree quand l'inventaire est ouvert")
uiHandlers["wakfu:trailRequest"]()
check(last("wakfu:inventoryOpen") == false and last("wakfu:trailOpen") == true and state.input == false, "le bouton de l'inventaire ferme le sac et ouvre le menu")
press("Escape"); settle()
check(last("wakfu:trailOpen") == false and state.input == true, "Echap ferme")
say("inventaire : le bouton « Traînée de l'arme » ferme le sac et ouvre le menu")

-- Un autre ecran ouvert l'empeche, et il empeche les autres
settle(); press("Escape"); check(last("wakfu:menuOpen") == true, "Echap ouvre le menu pause"); local trailOpens = count("wakfu:trailOpen")
press(KEY); check(count("wakfu:trailOpen") == trailOpens, "J ne s'ouvre pas par-dessus le menu pause")
press("Escape"); settle()
press(KEY)
remoteHandlers["wakfu:openForge"](); remoteHandlers["wakfu:openClassReroll"]()
check(count("wakfu:forgeOpen") == 0 and count("wakfu:rerollOpen") == 0, "la forge et le changement de voie ne s'ouvrent pas par-dessus le menu")
press(KEY); settle()
check(last("wakfu:trailOpen") == false, "J referme le menu")
say("exclusivite : pas de menu par-dessus un autre, ni l'inverse ; J referme")
return out
'''

failed = False
for label, root in RP.items():
    print("==", label)
    try:
        lines = LuaRuntime().eval("function(...) " + CODE + " end")(root)
        for i in range(1, len(lines) + 1):
            print("  " + str(lines[i]).encode("ascii", "replace").decode())
    except Exception as error:  # noqa: BLE001
        failed = True
        print("  " + str(error).encode("ascii", "replace").decode())
sys.exit(1 if failed else 0)
