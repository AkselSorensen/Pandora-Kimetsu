import sys

from lupa import LuaRuntime

from pathlib import Path

REPO_RP = (Path(__file__).resolve().parents[2] / "packages" / "wakfu-rp").as_posix()
RP = {"depot": REPO_RP}

# Les vrais noms des systemes Niagara trouves dans le projet Unreal (packs Fab et Vefects) ; les noms de packs cuits sont des suppositions.
FREE_MAGIC = ["Area1", "Area2", "Attack1", "Attack2", "Attack_Line", "Aura", "Buff", "Circle1", "Circle2", "Hit1", "Hit2", "Projectile1",
              "Projectile1_Base", "Projectile2", "Projectile2_Base", "Slash", "Slash2"]
FREE_SPELLS = [f"{kind}_{el}" for kind in ("Aura", "Buff") for el in ("Air", "Fire", "Healing", "Lightning", "Mana", "Notes", "Soul")] + [
    "Circle", "Explosion", "LevelUp", "Shockwave"]
FAKE = {
    "free-magic": ["NS_Free_Magic_" + n for n in FREE_MAGIC],
    "free-spells": ["NS_Free_Spells_" + n for n in FREE_SPELLS],
    "sword-trail-vfx": ["NS_Trail_%02d" % i for i in range(1, 19)],
    "vefects": ["NS_Trail_" + n for n in ("Cosmos", "Dark", "Earth", "Electric", "Fire", "Ice", "Nature", "Sound", "Void", "Water")],
}
TOTAL = sum(len(v) for v in FAKE.values())

PURE = r'''
local ROOT, fake = ...
local env = {}
setmetatable(env, { __index = _G })
local cache = {}
env.Package = { Require = function(name)
	if name == "FxMeshAssets.lua" then return { pack = "", meshes = {}, materials = {} } end if name == "VfxAssets.lua" then return fake end
	if cache[name] == nil then local f, err
		for _, dir in ipairs({ "Shared", "Server", "Client" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
		assert(f, tostring(err)); cache[name] = f() end
	return cache[name] end }
local Vfx, Classes = env.Package.Require("VfxPlan.lua"), env.Package.Require("Classes.lua")
local out = {}
local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local function say(text) out[#out + 1] = text end
local function near(a, b) return math.abs(a - b) < 1e-6 end

local bank = Vfx.Bank()
check(Vfx.HasAssets(), "des effets sont cuits")
local ids = {}
for _, entry in ipairs(bank) do check(not ids[entry.id] and entry.id:find("::", 1, true) and entry.name:sub(-5) ~= "_Base", "banque : " .. entry.id); ids[entry.id] = entry end
check(#bank == ... + 0 or true, "")
say("banque : " .. #bank .. " effets (les systemes _Base exclus)")

check(Vfx.KindOf("NS_Trail_Water") == "trail" and Vfx.KindOf("NS_Trail_07") == "trail", "traînees")
check(Vfx.KindOf("NS_Free_Magic_Slash") == "oriented" and Vfx.KindOf("NS_Free_Magic_Attack_Line") == "oriented" and Vfx.KindOf("NS_Free_Magic_Projectile2") == "oriented", "coups")
check(Vfx.KindOf("NS_Free_Spells_Aura_Fire") == "burst" and Vfx.KindOf("NS_Free_Spells_Shockwave") == "burst" and Vfx.KindOf("NS_Free_Magic_Circle1") == "burst", "auras")

-- Un plan par technique de chaque voie
local total, healPlans = 0, 0
local patterns = {}
for _, p in ipairs(Vfx.Patterns) do patterns[p] = true end
for className, class in pairs(Classes.List) do
	for slot, spell in ipairs(class.spells) do
		local plan = Vfx.PlanFor(className, slot, spell)
		check(#plan.pieces >= 1, className .. " " .. slot .. " : aucun morceau")
		local statics = 0
		for _, piece in ipairs(plan.pieces) do
			check(ids[piece.asset], className .. " " .. slot .. " : effet hors banque " .. piece.asset)
			check(piece.duration > 0 and piece.yaw ~= nil, className .. " : duree")
			if piece.motion == "path" then check(patterns[piece.pattern] and piece.range >= 250 and piece.range <= 1200, className .. " : trajectoire") else statics = statics + 1; check(#piece.at == 3, className .. " : point fixe") end
		end
		if spell.heal and not spell.damage then healPlans = healPlans + 1; check(statics >= 1, className .. " : le soin doit avoir une aura") end
		local byId = Vfx.PlanForSpell(spell.id)
		check(#byId.pieces == #plan.pieces, spell.id .. " : plan par identifiant")
		total = total + 1
	end
end
check(total == 32 and healPlans == 3, "32 techniques dont 3 soins : " .. total .. " " .. healPlans)
check(#Vfx.PlanForSpell("inconnue").pieces == 0, "technique inconnue")
say("plans : " .. total .. " techniques (8 voies x 4) ont un effet, dont " .. healPlans .. " soins")

local eau = Vfx.PlanFor("Eau", 2, Classes.List.Eau.spells[2])
check(#eau.pieces == 1 and eau.pieces[1].asset == "vefects::NS_Trail_Water" and eau.pieces[1].pattern == "forward", "Eau 2 : traînee d'eau devant")
local flamme = Vfx.PlanFor("Flamme", 4, Classes.List.Flamme.spells[4])
check(#flamme.pieces == 4 and flamme.pieces[1].yaw == -14 and flamme.pieces[3].yaw == 14 and flamme.pieces[4].asset == "free-spells::NS_Free_Spells_Explosion", "Flamme 4 : 3 traînees en eventail et une explosion")
say("choix : Eau 2 = " .. eau.pieces[1].asset .. " ; Flamme 4 = 3 traînees + " .. flamme.pieces[4].asset)

-- Trajectoires
local f0 = Vfx.Offset("forward", 0, 900); local f1 = Vfx.Offset("forward", 1, 900)
check(near(f0, 120) and near(f1, 900), "forward va de 120 a la portee")
for _, pattern in ipairs(Vfx.Patterns) do
	for i = 0, 20 do
		local f, r, u = Vfx.Offset(pattern, i / 20, 900)
		check(f == f and r == r and u == u and math.abs(f) <= 900 and math.abs(r) <= 900 and u >= 0 and u <= 260, pattern .. " : position hors limites a t=" .. i / 20)
	end
end
local af, ar = Vfx.Offset("arc", 0.5, 900); check(near(af, 260) and near(ar, 0), "arc : au milieu, droit devant a 260 cm")
local x, y, z = Vfx.World({ x = 100, y = 200, z = 190 }, 0, 50, 10, 30); check(near(x, 150) and near(y, 210) and near(z, 130), "lacet 0 : avant = +X, droite = +Y")
x, y = Vfx.World({ x = 100, y = 200, z = 190 }, 90, 50, 10, 0); check(near(x, 90) and near(y, 250), "lacet 90 : avant = +Y, droite = -X")
say("trajectoires : bornees, avant/droite corrects")

-- Effet voulu absent : repli sur une traînee de la banque
local without = {}
for pack, names in pairs(fake) do without[pack] = {} for _, n in ipairs(names) do if n ~= "NS_Trail_Water" then table.insert(without[pack], n) end end end
local env2 = {}
setmetatable(env2, { __index = _G })
env2.Package = { Require = function(name)
	if name == "FxMeshAssets.lua" then return { pack = "", meshes = {}, materials = {} } end if name == "VfxAssets.lua" then return without end
	local f = assert(loadfile(ROOT .. "/Shared/" .. name, "t", env2)); return f() end }
local Vfx2 = env2.Package.Require("VfxPlan.lua")
local plan2 = Vfx2.PlanFor("Eau", 1, Classes.List.Eau.spells[1])
check(#plan2.pieces == 1 and plan2.pieces[1].kind == "trail" and plan2.pieces[1].asset ~= "vefects::NS_Trail_Water", "repli sur une autre traînee")
say("repli : sans NS_Trail_Water, l'Eau prend " .. plan2.pieces[1].asset)

-- Traînees proposees au joueur
local trails = Vfx.TrailList()
local groups = {}
for _, t in ipairs(trails) do
	groups[t.group] = (groups[t.group] or 0) + 1
	check(t.id and t.name ~= "" and ids[t.id] and ids[t.id].kind == "trail", "traînee de menu : " .. tostring(t.id))
end
check(#trails == 28 and groups["Élémentaires"] == 10 and groups["Sabre"] == 18, "28 traînees (10 elementaires, 18 de sabre) : " .. #trails)
check(Vfx.IsTrailChoice("auto") and Vfx.IsTrailChoice("none") and Vfx.IsTrailChoice("vefects::NS_Trail_Fire") and not Vfx.IsTrailChoice("free-magic::NS_Free_Magic_Slash") and not Vfx.IsTrailChoice("x") and not Vfx.IsTrailChoice(5) and not Vfx.IsTrailChoice(nil), "choix valables")
check(Vfx.ResolveTrail("Eau", nil).id == "vefects::NS_Trail_Water" and Vfx.ResolveTrail("Eau", "auto").id == "vefects::NS_Trail_Water" and Vfx.ResolveTrail("Eau", "none") == nil and Vfx.ResolveTrail("Eau", "sword-trail-vfx::NS_Trail_07").id == "sword-trail-vfx::NS_Trail_07" and Vfx.ResolveTrail("Eau", "x::inconnu").id == "vefects::NS_Trail_Water", "resolution du choix")
say("menu de traînees : 28 traînees, choix valides, auto / none / identifiant / identifiant inconnu resolus")

-- Rien de cuit : rien a jouer, aucune erreur
local env3 = {}
setmetatable(env3, { __index = _G })
env3.Package = { Require = function(name)
	if name == "FxMeshAssets.lua" then return { pack = "", meshes = {}, materials = {} } end if name == "VfxAssets.lua" then return {} end
	local f = assert(loadfile(ROOT .. "/Shared/" .. name, "t", env3)); return f() end }
local Vfx3 = env3.Package.Require("VfxPlan.lua")
check(not Vfx3.HasAssets() and #Vfx3.Bank() == 0 and #Vfx3.PlanFor("Eau", 4, Classes.List.Eau.spells[4]).pieces == 0 and #Vfx3.PlanForSpell("eau_flux").pieces == 0, "rien de cuit")
say("rien de cuit : banque vide, aucun plan, aucune erreur")
return out
'''

CLIENT = r'''
local ROOT, fake, useMissing = ...
local env = {}
setmetatable(env, { __index = _G })
local now, spawned, warns, intervals, timeouts = 0, {}, {}, {}, {}
env.os = { clock = function() return now end }
env.Vector = function(x, y, z) return { X = x, Y = y, Z = z } end
env.Rotator = function(p, y, r) return { Pitch = p, Yaw = y, Roll = r } end
env.Console = { Warn = function(m) warns[#warns + 1] = m end }
env.Timer = {
	SetInterval = function(fn, ms) intervals[#intervals + 1] = { fn = fn, ms = ms, on = true }; return #intervals end,
	ClearInterval = function(id) intervals[id].on = false end,
	SetTimeout = function(fn, ms) timeouts[#timeouts + 1] = { fn = fn, ms = ms }; return #timeouts end,
}
env.Particle = function(location, rotation, asset, autoDestroy, autoActivate)
	if asset:find("missing", 1, true) then error("asset introuvable : " .. asset) end
	local p = { asset = asset, loc = location, valid = true, moves = 0, autoDestroy = autoDestroy, autoActivate = autoActivate }
	function p:IsValid() return self.valid end
	function p:Destroy() self.valid = false end
	function p:SetLocation(v) self.loc = v; self.moves = self.moves + 1 end
	spawned[#spawned + 1] = p
	return p
end
local cache = {}
env.Package = { Require = function(name)
	if name == "FxMeshAssets.lua" then return { pack = "", meshes = {}, materials = {} } end if name == "VfxAssets.lua" then return fake end
	if cache[name] == nil then local f, err
		for _, dir in ipairs({ "Client", "Shared" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
		assert(f, tostring(err)); cache[name] = f() end
	return cache[name] end }
local VfxPlayer = env.Package.Require("VfxPlayer.lua")
local out = {}
local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local function say(text) out[#out + 1] = text end
local function run(list, only) for _, t in ipairs(list) do if t.on ~= false then t.fn() end end end

if useMissing then
	VfxPlayer.PlaySpell("eau_surface", { x = 0, y = 0, z = 100 }, 0)
	VfxPlayer.PlaySpell("eau_maree", { x = 0, y = 0, z = 100 }, 0)
	check(#spawned == 0 and #warns == 1, "un effet qui ne charge pas est signale une seule fois : " .. #warns .. " avertissement(s), " .. #spawned .. " entite(s)")
	say("effet introuvable : 2 techniques jouees, 1 seul avertissement, aucune erreur")
	return out
end

VfxPlayer.PlaySpell("flamme_purgatoire", { x = 0, y = 0, z = 100 }, 90)
check(#spawned == 4 and #intervals == 3 and #timeouts == 1, "Purgatoire : 3 traînees et 1 impact : " .. #spawned .. "/" .. #intervals .. "/" .. #timeouts)
for _, p in ipairs(spawned) do check(p.autoDestroy == false and p.autoActivate == true, "creation sans destruction automatique") end
local starts = {}
for i, p in ipairs(spawned) do starts[i] = { p.loc.X, p.loc.Y } end
now = 0.4; run(intervals)
local moved = 0
for i = 1, 3 do if spawned[i].moves >= 1 and (spawned[i].loc.X ~= starts[i][1] or spawned[i].loc.Y ~= starts[i][2]) then moved = moved + 1 end end
check(moved == 3, "les traînees avancent : " .. moved)
check(spawned[1].loc.Y > starts[1][2] and math.abs(spawned[1].loc.X) < 300, "lacet 90 : la traînee part vers +Y")
now = 1.2; run(intervals)
for i = 1, 3 do check(not spawned[i].valid, "traînee " .. i .. " detruite en fin de trajectoire") end
check(spawned[4].valid, "l'impact dure encore"); for _, t in ipairs(timeouts) do t.fn() end
check(not spawned[4].valid, "l'impact est detruit apres sa duree")
check(#warns == 0, "aucun avertissement")
say("Purgatoire (lacet 90) : 3 traînees avancent vers +Y, detruites a la fin, impact detruit apres " .. timeouts[1].ms .. " ms")

-- Outil d'essai
local labels = {}
local origin = { x = 0, y = 0, z = 100 }
local bank = env.Package.Require("VfxPlan.lua").Bank()
for i = 1, 3 do labels[i] = VfxPlayer.Test(false, origin, 0) end
check(labels[1]:find("Effet 1/" .. #bank, 1, true) and labels[2]:find("Effet 2/", 1, true) and labels[3]:find("Effet 3/", 1, true), "l'essai passe d'un effet au suivant : " .. labels[3])
local label
for i = 1, #bank do label = VfxPlayer.Test(false, origin, 0); if label:find("(forward)", 1, true) then break end end
check(label:find("(forward)", 1, true), "l'essai atteint un effet de type traînee : " .. tostring(label))
local first = VfxPlayer.Test(true, origin, 0)
local second = VfxPlayer.Test(true, origin, 0)
local function effect(text) return text:match("Effet %d+/%d+ : [^ ]+") end
check(effect(first) == effect(second) and first ~= second and first:find("(arc)", 1, true) and second:find("(spiral)", 1, true), "changer de trajectoire garde l'effet : " .. first .. " / " .. second)
local wrapped
for i = 1, #bank do wrapped = VfxPlayer.Test(false, origin, 0) end
check(effect(wrapped) == effect(second), "apres un tour complet on revient au meme effet : " .. wrapped)
say("essai : " .. labels[1] .. " | " .. labels[2] .. " | trajectoire : " .. first .. " puis " .. second)

-- Apercu d'une traînee choisie dans le menu
local count = #spawned
VfxPlayer.Preview("auto", origin, 0); VfxPlayer.Preview("none", origin, 0); VfxPlayer.Preview("free-magic::NS_Free_Magic_Slash", origin, 0); VfxPlayer.Preview("x::y", origin, 0)
check(#spawned == count, "aucun apercu pour auto, none, un effet qui n'est pas une traînee ou un inconnu")
VfxPlayer.Preview("vefects::NS_Trail_Fire", origin, 0)
check(#spawned == count + 1 and spawned[#spawned].asset == "vefects::NS_Trail_Fire", "apercu de la traînee choisie")
say("apercu : la traînee choisie se joue devant le joueur, rien pour auto / none / inconnu")
return out
'''

failed = False
for label, root in RP.items():
    print("== wakfu-rp", label)
    lua = LuaRuntime()
    fake = lua.table_from({pack: lua.table_from(names) for pack, names in FAKE.items()})
    runs = [
        ("plans", PURE.replace('check(#bank == ... + 0 or true, "")\n', f'check(#bank == {TOTAL - 2}, "banque : {TOTAL - 2} effets attendus, " .. #bank)\n'), fake, None),
        ("client", CLIENT, fake, False),
    ]
    missing = lua.table_from({"x": lua.table_from(["NS_Trail_missing"])})
    runs.append(("client, effet introuvable", CLIENT, missing, True))
    for name, code, assets, flag in runs:
        try:
            args = (root, assets) if flag is None else (root, assets, flag)
            lines = lua.eval("function(...) " + code + " end")(*args)
            for i in range(1, len(lines) + 1):
                print("  [%s] %s" % (name, str(lines[i]).encode("ascii", "replace").decode()))
        except Exception as error:  # noqa: BLE001
            failed = True
            print("  [%s] %s" % (name, str(error).encode("ascii", "replace").decode()))
sys.exit(1 if failed else 0)
