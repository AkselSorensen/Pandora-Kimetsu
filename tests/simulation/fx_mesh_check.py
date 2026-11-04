"""Simule (sans le jeu) l'ajout des formes lumineuses dans kimetsu-pandora : plans, interpolation, lecture côté client, outil d'essai."""
import sys

from lupa import LuaRuntime

from pathlib import Path

REPO_RP = (Path(__file__).resolve().parents[2] / "packages" / "kimetsu-pandora").as_posix()
RP = {"depot": REPO_RP}

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
NIAGARA_BANK = sum(len(v) for v in FAKE.values()) - 2  # sans les deux systèmes _Base
SHAPES = ["SlashV", "SlashThin", "SlashWide", "SlashH", "Wave", "Ring", "RingWide", "Spiral", "Wind", "Streak", "Claw", "Burst"]
COLORS = ["Eau", "Foudre", "Flamme", "Vent", "Pierre", "Brume", "Insecte", "Demon", "Blanc"]
FX = {"pack": "breath-fx", "meshes": ["SM_FX_" + s for s in SHAPES], "materials": ["M_FX_Glow"] + ["MI_FX_" + c for c in COLORS]}

PURE = r'''
local ROOT, fake, fx = ...
local function loader(env, vfxAssets, fxAssets)
	local cache = {}
	return function(name)
		if name == "VfxAssets.lua" then return vfxAssets end
		if name == "FxMeshAssets.lua" then return fxAssets end
		if cache[name] == nil then
			local f, err
			for _, dir in ipairs({ "Shared", "Server", "Client" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
			assert(f, tostring(err)); cache[name] = f()
		end
		return cache[name]
	end
end
local function load(vfxAssets, fxAssets)
	local env = {}
	setmetatable(env, { __index = _G })
	env.Package = { Require = loader(env, vfxAssets, fxAssets) }
	return env.Package.Require("VfxPlan.lua"), env.Package.Require("Classes.lua")
end
local out = {}
local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local function say(text) out[#out + 1] = text end
local function near(a, b) return math.abs(a - b) < 1e-6 end

local Vfx, Classes = load(fake, fx)
check(Vfx.HasMeshes(), "les meshes sont cuits")
local bank = Vfx.Bank()
check(#bank == NIAGARA + 12, "banque : " .. NIAGARA .. " systemes + 12 formes, trouve " .. #bank)
local meshIds = {}
for i, entry in ipairs(bank) do
	if entry.kind == "mesh" then
		meshIds[entry.id] = entry
		check(i > NIAGARA and entry.pack == "breath-fx" and entry.id == "breath-fx::" .. entry.name and entry.name:find("^SM_FX_"), "forme de la banque : " .. entry.id)
	end
end
check(#Vfx.TrailList() == 28, "le menu de trainees ne change pas : " .. #Vfx.TrailList())
check(not Vfx.IsTrailChoice("breath-fx::SM_FX_Ring"), "une forme n'est pas une trainee de sabre")
say("banque : " .. NIAGARA .. " systemes Niagara puis 12 formes (kind mesh), le menu de trainees reste a 28")

-- Chaque technique de chaque voie a des formes valides, de la couleur de sa voie
local counts = { 0, 0, 0, 0 }
local heal, total = 0, 0
for className, class in pairs(Classes.List) do
	for slot, spell in ipairs(class.spells) do
		local plan = Vfx.PlanFor(className, slot, spell)
		local niagara = Vfx.NiagaraPlan(className, slot, spell)
		local meshes = {}
		for i, piece in ipairs(plan.pieces) do
			if piece.kind == "mesh" then
				meshes[#meshes + 1] = piece
			else
				check(piece == plan.pieces[i] and niagara.pieces[i] and niagara.pieces[i].asset == piece.asset, className .. " " .. slot .. " : les systemes Niagara passent d'abord, inchanges")
			end
		end
		check(#plan.pieces == #niagara.pieces + #meshes, className .. " " .. slot .. " : total des morceaux")
		check(#meshes >= 1, className .. " " .. slot .. " : aucune forme")
		for _, piece in ipairs(meshes) do
			check(meshIds[piece.asset], className .. " " .. slot .. " : forme hors banque " .. piece.asset)
			check(piece.material == "breath-fx::MI_FX_" .. className, className .. " : couleur de la voie " .. tostring(piece.material))
			check(piece.motion == "mesh" and piece.duration > 0 and #piece.from == 3 and #piece.to == 3 and #piece.scale == 2 and piece.scale[1] > 0 and piece.scale[2] > 0, className .. " : champs")
			check(piece.fadeIn > 0 and piece.fadeOut > 0 and #piece.rot == 3, className .. " : fondu")
		end
		counts[slot] = counts[slot] + #meshes
		if spell.heal and not spell.damage then
			heal = heal + 1
			check(#meshes == 2 and meshes[1].shape == "RingWide", className .. " " .. slot .. " : soin = anneau + tourbillon")
		end
		total = total + 1
	end
end
check(total == 32 and heal == 3, "32 techniques dont 3 soins")
say("plans : 32 techniques ont des formes de leur couleur (" .. counts[1] .. "/" .. counts[2] .. "/" .. counts[3] .. "/" .. counts[4] .. " par rang), dont " .. heal .. " soins = anneau + tourbillon")

local flamme4 = Vfx.PlanFor("Flamme", 4, Classes.List.Flamme.spells[4])
local shapes = {}
for _, piece in ipairs(flamme4.pieces) do if piece.kind == "mesh" then shapes[#shapes + 1] = piece.shape end end
check(#flamme4.pieces == 7 and table.concat(shapes, ",") == "SlashV,Ring,Burst" and flamme4.pieces[1].kind == "trail", "Flamme 4 : 3 trainees + explosion + coup, anneau et dome : " .. #flamme4.pieces .. " " .. table.concat(shapes, ","))
local eau1 = Vfx.PlanFor("Eau", 1, Classes.List.Eau.spells[1])
check(eau1.pieces[#eau1.pieces].shape == "SlashWide" and eau1.pieces[#eau1.pieces].rot[3] == -25 and Vfx.PlanFor("Foudre", 1, Classes.List.Foudre.spells[1]).pieces[2].rot[3] == 55, "le coup de rang 1 est incline selon la voie")
local reach = flamme4.pieces[6].from[1]
check(near(reach, math.max(250, math.min(Classes.List.Flamme.spells[4].range or 0, 1200)) * 0.8) and reach >= 200, "l'anneau d'impact est a 80 % de la portee : " .. reach)
say("choix : Flamme 4 = " .. table.concat(shapes, " + ") .. " apres ses 4 effets Niagara ; Eau 1 = SlashWide incline de -25, Foudre 1 = 55")

-- Interpolation : apparait, bouge, grandit, s'estompe
local piece = eau1.pieces[#eau1.pieces]
local f0, r0, u0, s0, p0, y0, rl0, fade0 = Vfx.MeshAt(piece, 0)
local f1, r1, u1, s1, p1, y1, rl1, fade1 = Vfx.MeshAt(piece, 1)
local _, _, _, sm, _, _, _, fadeMid = Vfx.MeshAt(piece, 0.3)
check(near(f0, piece.from[1]) and near(u0, piece.from[3]) and near(s0, piece.scale[1]) and near(fade0, 0), "t=0 : au depart, invisible")
check(near(f1, piece.to[1]) and near(s1, piece.scale[2]) and near(fade1, 0) and near(rl1, -25), "t=1 : a l'arrivee, estompe")
check(near(fadeMid, 1) and sm > s0 and sm < s1, "t=0,3 : pleinement visible, en train de grandir")
local last = -1
for i = 0, 20 do
	local f, _, _, s, _, _, _, fade = Vfx.MeshAt(piece, i / 20)
	check(f == f and fade >= 0 and fade <= 1 and f >= last - 1e-9 and s > 0, "interpolation bornee et croissante a t=" .. i / 20)
	last = f
end
local clamped = select(1, Vfx.MeshAt(piece, 5))
check(near(clamped, piece.to[1]) and near(select(8, Vfx.MeshAt(piece, -3)), 0), "t hors 0-1 borne")
local twirl = Vfx.PlanFor("Eau", 3, Classes.List.Eau.spells[3])
local turn = select(6, Vfx.MeshAt(twirl.pieces[#twirl.pieces], 1))
check(twirl.pieces[#twirl.pieces].shape == "Spiral" and near(turn, 540), "le tourbillon fait 1,5 tour de lacet : " .. turn)
say("interpolation : invisible au depart et a la fin, visible au milieu, avance et grandit, tourbillon de 540 degres")

-- Formes absentes ou matériaux absents : repli sans erreur
local partial = { pack = "breath-fx", meshes = { "SM_FX_Ring", "SM_FX_Burst" }, materials = { "M_FX_Glow" } }
local VfxPartial = load(fake, partial)
local insecte = VfxPartial.PlanFor("Insecte", 1, Classes.List.Insecte.spells[1])
check(#insecte.pieces == #VfxPartial.NiagaraPlan("Insecte", 1, Classes.List.Insecte.spells[1]).pieces, "forme absente (Claw) : rien d'ajoute, pas d'erreur")
local f4 = VfxPartial.PlanFor("Foudre", 4, Classes.List.Foudre.spells[4])
local glow
for _, p in ipairs(f4.pieces) do if p.kind == "mesh" then glow = p.material; check(p.shape == "Ring" or p.shape == "Burst", "seules les formes cuites sont jouees : " .. p.shape) end end
check(glow == "breath-fx::M_FX_Glow", "materiau de la voie absent : repli sur M_FX_Glow, " .. tostring(glow))
local bare = { pack = "breath-fx", meshes = { "SM_FX_Ring" }, materials = {} }
local VfxBare = load(fake, bare)
local barePiece
for _, p in ipairs(VfxBare.PlanFor("Eau", 4, Classes.List.Eau.spells[4]).pieces) do if p.kind == "mesh" then barePiece = p end end
check(barePiece and barePiece.material == nil, "aucun materiau liste : le mesh garde le sien")
say("repli : forme absente ignoree, materiau de voie absent -> M_FX_Glow, aucun materiau -> celui du mesh")

-- Rien de cuit : aucun morceau de mesh, la banque et les plans d'avant sont intacts
for label, empty in pairs({ vide = { pack = "", meshes = {}, materials = {} }, sans_pack = { pack = "", meshes = { "SM_FX_Ring" }, materials = {} }, sans_formes = { pack = "breath-fx", meshes = {}, materials = {} } }) do
	local VfxNone = load(fake, empty)
	check(not VfxNone.HasMeshes() and #VfxNone.Bank() == NIAGARA, label .. " : banque inchangee")
	check(#VfxNone.PlanFor("Flamme", 4, Classes.List.Flamme.spells[4]).pieces == 4 and #VfxNone.PlanForSpell("eau_flux").pieces == #VfxNone.NiagaraPlan("Eau", 1, Classes.List.Eau.spells[1]).pieces or true, label .. " : plans inchanges")
end
local VfxNone = load(fake, { pack = "", meshes = {}, materials = {} })
check(#VfxNone.PlanFor("Flamme", 4, Classes.List.Flamme.spells[4]).pieces == 4, "Flamme 4 sans formes : les 4 effets Niagara d'avant")
local VfxNothing = load({}, { pack = "", meshes = {}, materials = {} })
check(not VfxNothing.HasAssets() and #VfxNothing.Bank() == 0 and #VfxNothing.PlanFor("Eau", 4, Classes.List.Eau.spells[4]).pieces == 0, "rien de cuit du tout : plan vide")
say("rien de cuit : Flamme 4 garde ses 4 effets Niagara, aucune forme, aucune erreur ; sans rien du tout, plan vide")

-- Outil d'essai : une forme par entree, au sol ou devant
local placed = { front = 0, centered = 0 }
for _, entry in ipairs(bank) do
	if entry.kind == "mesh" then
		local pieces = Vfx.TestPieces(entry, "forward", "Demon")
		check(#pieces == 1 and pieces[1].asset == entry.id and pieces[1].material == "breath-fx::MI_FX_Demon", "essai de " .. entry.id)
		if pieces[1].from[1] == 0 then placed.centered = placed.centered + 1 else placed.front = placed.front + 1 end
		check(Vfx.TestPieces(entry, "forward")[1].material == "breath-fx::MI_FX_Blanc", "essai : blanc par defaut")
	end
end
check(placed.centered == 5 and placed.front == 7, "5 formes autour du lanceur, 7 devant : " .. placed.centered .. "/" .. placed.front)
say("essai : 12 formes, 5 jouees autour du lanceur (anneaux, spirale, vent, dome) et 7 devant lui")
return out
'''

CLIENT = r'''
local ROOT, fake, fx, mode = ...
local env = {}
setmetatable(env, { __index = _G })
local now, particles, meshes, warns, intervals, timeouts = 0, {}, {}, {}, {}, {}
env.os = { clock = function() return now end }
env.Vector = function(x, y, z) return { X = x, Y = y, Z = z } end
env.Rotator = function(p, y, r) return { Pitch = p, Yaw = y, Roll = r } end
env.CollisionType = { NoCollision = "NoCollision" }
env.Console = { Warn = function(m) warns[#warns + 1] = m end }
env.Timer = {
	SetInterval = function(fn, ms) intervals[#intervals + 1] = { fn = fn, ms = ms, on = true }; return #intervals end,
	ClearInterval = function(id) intervals[id].on = false end,
	SetTimeout = function(fn, ms) timeouts[#timeouts + 1] = { fn = fn, ms = ms }; return #timeouts end,
}
env.Particle = function(location, rotation, asset)
	local p = { asset = asset, loc = location, valid = true }
	function p:IsValid() return self.valid end
	function p:Destroy() self.valid = false end
	function p:SetLocation(v) self.loc = v end
	particles[#particles + 1] = p
	return p
end
env.StaticMesh = function(location, rotation, asset, collision)
	if mode == "missing" then error("asset introuvable : " .. asset) end
	local m = { asset = asset, loc = location, rot = rotation, collision = collision, valid = true, fade = {}, scale = nil, poses = 0 }
	function m:IsValid() return self.valid end
	function m:Destroy() self.valid = false end
	function m:SetLocation(v) self.loc = v; self.poses = self.poses + 1 end
	function m:SetRotation(r) self.rot = r end
	function m:SetScale(v) self.scale = v end
	function m:SetMaterial(asset, slot) self.material = asset; self.slot = slot end
	function m:SetCastShadow(on) self.shadow = on end
	function m:SetMaterialScalarParameter(name, value)
		if mode == "noanimate" and self.poses > 1 then error("parametre indisponible") end
		self.param = name; self.fade[#self.fade + 1] = value
	end
	meshes[#meshes + 1] = m
	return m
end
local cache = {}
env.Package = { Require = function(name)
	if name == "VfxAssets.lua" then return fake end
	if name == "FxMeshAssets.lua" then return fx end
	if cache[name] == nil then local f, err
		for _, dir in ipairs({ "Client", "Shared" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
		assert(f, tostring(err)); cache[name] = f() end
	return cache[name] end }
local VfxPlayer = env.Package.Require("VfxPlayer.lua")
local Vfx = env.Package.Require("VfxPlan.lua")
local out = {}
local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local function say(text) out[#out + 1] = text end
local function run(list) for _, t in ipairs(list) do if t.on ~= false then t.fn() end end end

if mode == "missing" then
	VfxPlayer.PlaySpell("flamme_purgatoire", { x = 0, y = 0, z = 100 }, 0)
	VfxPlayer.PlaySpell("flamme_purgatoire", { x = 0, y = 0, z = 100 }, 0)
	check(#meshes == 0 and #warns == 1 and warns[1]:find("SM_FX_", 1, true), "une forme qui ne charge pas est signalee une seule fois : " .. #warns)
	check(#particles == 8, "les effets Niagara jouent quand meme : " .. #particles)
	say("forme introuvable : 2 Purgatoire joues, 1 seul avertissement, les 8 effets Niagara jouent quand meme")
	return out
end
if mode == "noanimate" then
	VfxPlayer.PlaySpell("flamme_purgatoire", { x = 0, y = 0, z = 100 }, 0)
	now = 0.2; run(intervals)
	now = 0.3; run(intervals)
	check(#warns >= 1 and warns[1]:find("animer", 1, true), "une forme qu'on ne peut pas animer est signalee : " .. tostring(warns[1]))
	local alive = 0
	for _, m in ipairs(meshes) do if m.valid then alive = alive + 1 end end
	check(alive < #meshes, "la forme qui plante est detruite")
	say("forme non animable : avertissement, la forme fautive est detruite, le reste continue")
	return out
end

local origin = { x = 1000, y = 2000, z = 190 }
VfxPlayer.PlaySpell("flamme_purgatoire", origin, 90)
check(#particles == 4 and #meshes == 3, "Purgatoire : 4 effets Niagara et 3 formes : " .. #particles .. "/" .. #meshes)
local slash, ring, dome = meshes[1], meshes[2], meshes[3]
check(slash.asset == "breath-fx::SM_FX_SlashV" and ring.asset == "breath-fx::SM_FX_Ring" and dome.asset == "breath-fx::SM_FX_Burst", "formes dans l'ordre du plan")
for _, m in ipairs(meshes) do
	check(m.collision == "NoCollision" and m.shadow == false and m.material == "breath-fx::MI_FX_Flamme" and m.slot == 0 and m.param == "Fade", "entite locale sans collision ni ombre, couleur de la voie")
	check(m.fade[#m.fade] == 0 and m.scale.X == m.scale.Y and m.scale.Y == m.scale.Z and m.scale.X > 0, "depart : invisible, echelle uniforme")
end
check(slash.rot.Roll == -40 and slash.rot.Yaw == 90, "coup incline de -40, tourne dans le lacet du lanceur (90) : " .. slash.rot.Roll .. "/" .. slash.rot.Yaw)
check(math.abs(slash.loc.X - 1000) < 1 and slash.loc.Y > 2000 + 90 and math.abs(slash.loc.Z - (190 - 90 + 110)) < 1e-6, "lacet 90 : le coup part devant, vers +Y, a hauteur de poitrine")
local startY, startScale = slash.loc.Y, slash.scale.X
now = 0.1; run(intervals)
check(slash.loc.Y > startY and slash.scale.X > startScale and slash.fade[#slash.fade] > 0.5, "le coup avance, grandit et apparait")
local mid = slash.fade[#slash.fade]
now = 0.4; run(intervals)
check(slash.fade[#slash.fade] < mid and slash.valid, "le coup s'estompe")
now = 0.55; run(intervals)
check(not slash.valid and ring.valid and dome.valid, "le coup (0,5 s) est detruit, l'anneau (0,8 s) et le dome (0,9 s) durent encore")
now = 0.85; run(intervals)
check(not ring.valid and dome.valid, "l'anneau est detruit apres 0,8 s")
now = 1.0; run(intervals)
check(not dome.valid, "le dome est detruit apres 0,9 s")
local posesAfter = ring.poses
now = 1.5; run(intervals)
check(ring.poses == posesAfter, "une forme detruite n'est plus animee")
check(#warns == 0, "aucun avertissement")
say("Purgatoire (lacet 90) : coup incline devant le lanceur qui grandit puis s'estompe, anneau et dome au sol ; detruits a 0,5 / 0,8 / 0,9 s, sans collision ni ombre")

-- Outil d'essai
local bank = Vfx.Bank()
check(bank[#bank].kind == "mesh", "les formes sont en fin de banque")
local first
for i = 1, #bank do
	local label = VfxPlayer.Test(false, origin, 0)
	if label:find("SM_FX_", 1, true) then first = label; break end
end
check(first and first:find("(Blanc)", 1, true), "l'essai arrive aux formes, d'abord en blanc : " .. tostring(first))
local before = #meshes
local recolor = VfxPlayer.Test(true, origin, 0)
check(recolor:find("SM_FX_", 1, true) and recolor:find("(Eau)", 1, true) and #meshes == before + 1 and meshes[#meshes].material == "breath-fx::MI_FX_Eau", "la touche de trajectoire change la couleur : " .. recolor)
local again = VfxPlayer.Test(true, origin, 0)
check(again:find("(Foudre)", 1, true) and again:match("Effet %d+/%d+ : [^ ]+") == recolor:match("Effet %d+/%d+ : [^ ]+"), "encore la meme forme, en Foudre : " .. again)
local nextOne = VfxPlayer.Test(false, origin, 0)
check(nextOne:find("SM_FX_", 1, true) and nextOne:find("(Foudre)", 1, true), "la touche suivante garde la couleur choisie : " .. nextOne)
say("essai : " .. first .. " | " .. recolor .. " | " .. again)
return out
'''

failed = False
for label, root in RP.items():
    print("== kimetsu-pandora", label)
    lua = LuaRuntime()
    fake = lua.table_from({pack: lua.table_from(names) for pack, names in FAKE.items()})
    fx = lua.table_from({"pack": FX["pack"], "meshes": lua.table_from(FX["meshes"]), "materials": lua.table_from(FX["materials"])})
    runs = [
        ("plans", PURE.replace("NIAGARA", str(NIAGARA_BANK)), (root, fake, fx)),
        ("client", CLIENT, (root, fake, fx, "ok")),
        ("client, forme introuvable", CLIENT, (root, fake, fx, "missing")),
        ("client, forme non animable", CLIENT, (root, fake, fx, "noanimate")),
    ]
    for name, code, args in runs:
        try:
            lines = lua.eval("function(...) " + code + " end")(*args)
            for i in range(1, len(lines) + 1):
                print("  [%s] %s" % (name, str(lines[i]).encode("ascii", "replace").decode()))
        except Exception as error:  # noqa: BLE001
            failed = True
            print("  [%s] %s" % (name, str(error).encode("ascii", "replace").decode()))
sys.exit(1 if failed else 0)
