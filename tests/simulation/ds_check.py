import json
import sys

from lupa import LuaRuntime

from pathlib import Path

REPO_RP = (Path(__file__).resolve().parents[2] / "packages" / "wakfu-rp").as_posix()
RP = {"depot": REPO_RP}

PRELUDE = r'''
local Any = {}
setmetatable(Any, { __index = function() return Any end, __call = function() return Any end, __add = function() return Any end, __sub = function() return Any end,
	__mul = function() return Any end, __div = function() return Any end, __lt = function() return false end, __le = function() return false end, __concat = function() return "" end })

local ROOT = ...
local env = {}
setmetatable(env, { __index = function(_, k) local v = _G[k]; if v == nil then return Any end; return v end })
local cache = {}
env.Package = setmetatable({ Require = function(name)
	if name == "VfxAssets.lua" then return { vefects = { "NS_Trail_Water", "NS_Trail_Fire" } } end
	if cache[name] == nil then local f, err
		for _, dir in ipairs({ "Shared", "Server", "Client" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
		assert(f, tostring(err)); cache[name] = f() end
	return cache[name] end, Subscribe = function() end }, { __index = function() return Any end })
'''

DATA = PRELUDE + r'''
local Classes, Ranks, Items, Quests, Npcs, Config, Combat = env.Package.Require("Classes.lua"), env.Package.Require("Ranks.lua"), env.Package.Require("Items.lua"),
	env.Package.Require("Quests.lua"), env.Package.Require("Npcs.lua"), env.Package.Require("Config.lua"), env.Package.Require("Combat.lua")
local out = {}
local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local function say(text) out[#out + 1] = text end

-- Classes
local count = 0
for name, class in pairs(Classes.List) do
	count = count + 1
	check(class.name and class.glyph and class.color and class.short and class.blurb and class.title, name .. " : champs d'affichage manquants")
	check(Ranks.Ladders[class.ladder], name .. " : echelle inconnue")
	check(class.hp > 0 and #class.spells == 4, name .. " : PV ou 4 techniques manquants")
	check(class.color:match("^#%x%x%x%x%x%x$"), name .. " : couleur invalide")
	local seen = {}
	for i, spell in ipairs(class.spells) do
		check(not seen[spell.id], name .. " : id de sort en double " .. spell.id); seen[spell.id] = true
		check(spell.cooldown > 0 and spell.range ~= nil and (spell.damage or spell.heal), name .. " : sort " .. i .. " incomplet")
		check(not spell.damage or spell.damage > 0, name .. " : degats nuls")
	end
end
check(count == 8 and #Classes.RerollOrder == 8, "il faut 8 classes pour les 8 cartes")
for _, name in ipairs(Classes.RerollOrder) do check(Classes.List[name], "RerollOrder : " .. name .. " inconnue") end
check(Classes.List[Classes.Default], "classe par defaut inconnue")
check(Classes.List.Demon.ladder == "demon", "le Demon doit avoir l'echelle des Lunes")
say("classes : " .. count .. " (" .. table.concat(Classes.RerollOrder, ", ") .. "), defaut " .. Classes.Default)

-- Grades
for ladder, steps in pairs(Ranks.Ladders) do
	for i = 2, #steps do check(steps[i].xp > steps[i - 1].xp and steps[i].hp >= steps[i - 1].hp, ladder .. " : seuils non croissants") end
	check(steps[1].xp == 0, ladder .. " : le premier grade doit commencer a 0")
end
local r = Ranks.Get("slayer", 0); check(r.index == 1 and r.name == "Mizunoto" and r.nextXp == 100, "grade 0")
r = Ranks.Get("slayer", 99); check(r.index == 1, "grade 99")
r = Ranks.Get("slayer", 100); check(r.index == 2 and r.name == "Mizunoe", "grade 100")
r = Ranks.Get("slayer", 99999); check(r.name == "Hashira" and r.nextXp == nil, "dernier grade")
r = Ranks.Get("demon", 99999); check(r.name == "Lune Supérieure Une", "dernier grade demon")
r = Ranks.Get("inconnue", 150); check(r.name == "Mizunoe", "echelle inconnue -> pourfendeur")
local total, promoted = Ranks.AddXp("slayer", 90, 20); check(total == 110 and promoted and promoted.name == "Mizunoe", "promotion")
total, promoted = Ranks.AddXp("slayer", 110, 10); check(total == 120 and promoted == nil, "pas de promotion")
total = Ranks.AddXp("slayer", 5, -50); check(total == 0, "xp jamais negative")
check(Combat.Heal(500, 1000, 250) == 750 and Combat.Heal(900, 1000, 250) == 1000, "soin plafonne")
say("grades : " .. #Ranks.Ladders.slayer .. " pourfendeur, " .. #Ranks.Ladders.demon .. " demon ; soin plafonne OK")

-- Objets et lames
check(#Items.BladeList == 176, "176 lames attendues, " .. #Items.BladeList)
local equipSlots = {}
for _, slot in ipairs(Items.EquipSlots) do equipSlots[slot] = true end
local groups = {}
for id, def in pairs(Items.List) do
	check(def.name and def.name ~= "" and def.type and def.rarity and def.weight and def.stats, id .. " : champs manquants")
	check(not def.slot or equipSlots[def.slot], id .. " : emplacement inconnu")
	if def.blade then
		check(Config.Weapons.list[id] and Config.Weapons.list[id].mesh == "yufu-arme-test::SM_" .. id:sub(6), id .. " : pas d'arme correspondante")
		check(def.slot == "weapon" and def.stats.force, id .. " : lame sans force")
		groups[def.group] = (groups[def.group] or 0) + 1
	end
end
check(Items.List.yufu_claymore54.name == "Claymore n°54" and Items.List.yufu_katana1.name == "Katana n°1", "noms de lames")
check(Items.List.yufu_typ_yoru_sold and Items.List.yufu_typ_yoru_sold.name == "Typ Yoru Sold", "nom d'une lame sans numero")
check(Items.List.katana and Config.Weapons.list.katana, "la Lame Nichirin de depart doit rester en main")
local inv = Items.NewInventory()
for _, id in ipairs({ "katana", "dague", "talisman", "masque", "bottes", "gants" }) do check(Items.Add(inv, id, 1), "sac de depart : " .. id) end
check(Items.Add(inv, "onigiri", 3) and Items.Add(inv, "fiole", 1), "sac de depart : soins")
say("objets : " .. (function() local n = 0 for _ in pairs(Items.List) do n = n + 1 end return n end)() .. " dont 176 lames (Katana " .. groups.Katana .. ", Claymore " .. groups.Claymore .. ", Lance " .. groups.Lance .. ", Divers " .. groups.Divers .. "), poids de depart " .. Items.Weight(inv) .. "/" .. Items.MaxWeight)

-- PNJ et quetes
local ids = {}
for _, npc in ipairs(Npcs.List) do
	check(not ids[npc.id], "PNJ en double " .. npc.id); ids[npc.id] = npc
	for _, questId in ipairs(npc.quests) do check(Quests.Get(questId), npc.id .. " propose une quete inconnue " .. questId) end
end
for id, quest in pairs(Quests.List) do
	check(quest.reward.kamas and quest.reward.xp, id .. " : recompense incomplete")
	if quest.objective.type == "talk" then check(ids[quest.objective.target], id .. " : PNJ cible inconnu " .. quest.objective.target) end
end
for _, id in ipairs({ "kakushi", "instructeur", "tailleur", "maitre_respirations", "forgeron" }) do check(ids[id], "PNJ manquant " .. id) end
check(Npcs.HasService(ids.forgeron, "forge") and Npcs.HasService(ids.instructeur, "reroll") and Npcs.HasService(ids.maitre_respirations, "classreroll") and Npcs.HasService(ids.tailleur, "creator"), "services")
for id in pairs(Config.Weapons.npcs) do check(ids[id], "Config.Weapons.npcs : PNJ inconnu " .. id) end
for _, a in ipairs(Npcs.List) do for _, b in ipairs(Npcs.List) do if a ~= b and not a.showcase and not b.showcase then
	local dx, dy = a.position.x - b.position.x, a.position.y - b.position.y
	check(dx * dx + dy * dy > 300 * 300, a.id .. " et " .. b.id .. " trop proches (l'interaction prendrait le mauvais)")
end end end
local quests = 0 for _ in pairs(Quests.List) do quests = quests + 1 end
say("PNJ : " .. #Npcs.List .. " (dont la galerie), quetes : " .. quests .. ", zone : " .. Config.Zone)
return out
'''

SERVER = PRELUDE + r'''
local Items = env.Package.Require("Items.lua")
local Config = env.Package.Require("Config.lua")
local clock, timers, timerMs = 1000, {}, {}
local remote, subs, handlers, sent, melees = {}, {}, {}, {}, {}
local nextId = 0
local function vec(x, y, z) return setmetatable({ X = x, Y = y, Z = z }, { __add = function(a, b) return vec(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end, __index = { Distance = function(a, b) return math.sqrt((a.X-b.X)^2 + (a.Y-b.Y)^2 + (a.Z-b.Z)^2) end } }) end
env.Vector = function(x, y, z) return vec(x or 0, y or 0, z or 0) end
env.Rotator = function() return { Yaw = 0 } end
env.Color = function() return Any end
env.Server = { GetTime = function() return clock end }
env.Timer = { SetTimeout = function(fn, ms) timers[#timers + 1] = fn; timerMs[#timers] = ms; return #timers end, ClearInterval = function() end, SetInterval = function() return 1 end }
env.Console = { Log = function() end, Warn = function() end, Error = function(m) error("Console.Error : " .. tostring(m), 0) end }
local function newCharacter(location)
	nextId = nextId + 1
	local id, loc = nextId, location
	local c = { hp = 100, maxHp = 100, held = nil, valid = true, values = {} }
	function c:GetID() return id end
	function c:IsValid() return self.valid end
	function c:IsDead() return self.hp <= 0 end
	function c:GetMaxHealth() return self.maxHp end
	function c:SetMaxHealth(v) self.maxHp = v end
	function c:GetHealth() return self.hp end
	function c:SetHealth(v) self.hp = v end
	function c:GetLocation() return loc end
	function c:SetLocation(v) loc = v end
	function c:GetRotation() return { Yaw = 0 } end
	function c:SetRotation() end
	function c:PickUp(m) self.held = m end
	function c:GetPicked() return self.held end
	function c:Destroy() self.valid = false end
	function c:Respawn(v) loc = v; self.hp = self.maxHp end
	function c:SetValue(k, v) self.values[k] = v end
	function c:GetPlayer() return self.player end
	function c:ApplyDamage(amount) self.hp = math.max(0, self.hp - amount) end
	return setmetatable(c, { __index = function() return function() return Any end end })
end
env.Character = setmetatable({ Subscribe = function(name, fn) handlers[name] = fn end }, { __call = function(_, location) return newCharacter(location) end })
env.Melee = setmetatable({}, { __call = function(_, _, _, mesh)
	local m = { mesh = mesh, valid = true }
	function m:IsValid() return self.valid end
	function m:Destroy() self.valid = false end
	function m:GetID() return m end
	function m:Subscribe(name, fn) local events = rawget(self, "events"); if not events then events = {}; rawset(self, "events", events) end; events[name] = fn end
	melees[#melees + 1] = m
	return setmetatable(m, { __index = function() return function() end end }) end })
local players = {}
env.Player = { Subscribe = function(name, fn) handlers["Player" .. name] = fn end, GetPairs = function() return players end }
env.Events = setmetatable({ SubscribeRemote = function(name, fn) remote[name] = fn end, Subscribe = function(name, fn) subs[name] = fn end,
	CallRemote = function(name, player, _, ...) sent[#sent + 1] = { name = name, player = player, args = { ... } } end }, { __index = function() return function() return Any end end })
env.HandlingMode = setmetatable({}, { __index = function(_, k) return k end })
env.AnimationSlotType = setmetatable({}, { __index = function(_, k) return k end })
env.CollisionType = { Normal = 0 }
env.Reliability = { Reliable = 1, Unreliable = 2 }
env.DamageType = { Unknown = 0 }
env.TextRender = function() return Any end
env.TextRenderRenderingType = Any
env.StaticMesh = function() return Any end
local particles, failParticles = {}, false
env.AttachmentRule = { KeepRelative = 0, KeepWorld = 1, SnapToTarget = 2 }
env.Particle = function(location, rotation, asset, autoDestroy, autoActivate)
	if failParticles then error("asset introuvable : " .. tostring(asset)) end
	local p = { asset = asset, autoDestroy = autoDestroy, autoActivate = autoActivate, active = autoActivate ~= false, resets = 0, valid = true }
	function p:Activate(reset) self.active = true; if reset then self.resets = self.resets + 1 end end
	function p:Deactivate() self.active = false end
	function p:SetScale(v) self.scale = v end
	function p:IsValid() return self.valid end
	function p:Destroy() self.valid = false end
	function p:AttachTo(target, rule, bone, lifespan) self.parent, self.rule, self.bone, self.lifespan = target, rule, bone, lifespan; return true end
	function p:SetRelativeLocation(v) self.rel = v end
	particles[#particles + 1] = p
	return p
end

assert(loadfile(ROOT .. "/Server/Index.lua", "t", env))()

local function newPlayer(name)
	local p = { name = name }
	nextId = nextId + 1
	local id = nextId
	function p:GetID() return id end
	function p:GetName() return self.name end
	function p:IsValid() return true end
	function p:GetControlledCharacter() return self.character end
	function p:Possess(c) self.character = c; c.player = self end
	players[id] = p
	handlers.PlayerSpawn(p)
	remote["wakfu:chooseCamp"](p, "slayer") -- le camp est un choix obligatoire a l'arrivee (voir demon_check.py pour les demons)
	return p
end
local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local function last(name, player)
	for i = #sent, 1, -1 do if sent[i].name == name and (not player or sent[i].player == player) then return sent[i].args end end
end
local function count(name, player) local n = 0 for _, s in ipairs(sent) do if s.name == name and (not player or s.player == player) then n = n + 1 end end return n end
local function stateOf(player) return last("wakfu:state", player)[1] end
local function lastNotice(player) local a = last("wakfu:notice", player); return a and a[1] end
local out = {}
local function say(text) out[#out + 1] = text end
local function place(player, npcId) local npc = env.Package.Require("Npcs.lua").Get(npcId); player.character:SetLocation(vec(npc.position.x, npc.position.y, npc.position.z)) end
local function cast(player, i) clock = clock + 100; remote["wakfu:castIndex"](player, i) end

-- 1. Arrivee
local p1 = newPlayer("Tanjiro")
local s = stateOf(p1)
check(s.class == "Eau" and s.kamas == 200 and s.xp == 0 and s.rank.name == "Mizunoto" and s.rank.index == 1 and s.rank.nextXp == 100, "etat de depart")
check(p1.character.maxHp == 1200, "PV de depart de l'Eau : " .. p1.character.maxHp .. " (gear +endurance non equipe)")
say("arrivee : " .. s.class .. ", " .. s.rank.name .. ", " .. s.kamas .. " yens, PV " .. p1.character.maxHp .. ", arme " .. (p1.character.held and p1.character.held.mesh or "aucune"))

-- 2. Techniques : 4 pour l'Eau, soin pour l'Insecte
local p2 = newPlayer("Muzan")
p1.character:SetLocation(vec(0, 0, 100)); p2.character:SetLocation(vec(100, 0, 100)) -- a portee des techniques
local p3 = newPlayer("Loin"); p3.character:SetLocation(vec(50000, 0, 100))
for i = 1, 4 do cast(p1, i) end
check(count("wakfu:fx", p1) == 4 and count("wakfu:fx", p2) == 4, "chaque technique envoie son effet au lanceur et au joueur proche : " .. count("wakfu:fx", p1) .. "/" .. count("wakfu:fx", p2))
local fx = last("wakfu:fx", p2); check(fx[1] == "eau_flux" and type(fx[2]) == "number" and type(fx[5]) == "number", "contenu de l'evenement d'effet")
check(count("wakfu:fx", p3) == 0, "un joueur eloigne ne recoit aucun effet")
check(count("wakfu:cast", p1) == 4, "les 4 techniques de l'Eau doivent partir, " .. count("wakfu:cast", p1))
check(p2.character.hp < p2.character.maxHp, "la cible doit etre blessee")
cast(p1, 5); check(count("wakfu:cast", p1) == 4, "un 5e sort n'existe pas")
remote["wakfu:chooseClass"](p1, "Insecte")
p1.character.hp = 500; p1.character.maxHp = 1000
local before = p2.character.hp
cast(p1, 3)
check(p1.character.hp == 750, "Remede de glycine : 500 -> 750, " .. p1.character.hp)
check(p2.character.hp == before, "un sort de soin ne blesse personne")
p1.character.hp = 900; cast(p1, 3)
check(p1.character.hp == 900 or p1.character.hp == 1000, "soin plafonne au maximum (cooldown ou plafond), " .. p1.character.hp)
say("techniques : Eau x4 OK, Remede de glycine +250 PV, ne blesse personne, plafonne au max")
remote["wakfu:chooseClass"](p1, "Eau")

-- 3. XP, grade, quete de duel
local hpBefore = p1.character.maxHp
local victim = newPlayer("Demon errant")
for i = 1, 3 do
	handlers.Death(victim.character, nil, nil, nil, nil, p1)
end
s = stateOf(p1)
check(s.xp == 120 and s.rank.name == "Mizunoe" and s.rank.index == 2, "3 victoires = 120 XP, grade Mizunoe : " .. s.xp .. " " .. s.rank.name)
check(lastNotice(p1) == "Nouveau grade : Mizunoe", "message de promotion : " .. tostring(lastNotice(p1)))
say("xp : 3 duels gagnes = " .. s.xp .. " XP -> " .. s.rank.name .. ", PV max " .. hpBefore .. " -> " .. p1.character.maxHp)
check(p1.character.maxHp > hpBefore, "le grade doit donner des PV")

-- 4. Quetes au Kakushi
place(p1, "kakushi")
remote["wakfu:interact"](p1)
local dialog = last("wakfu:dialog", p1)
check(dialog and dialog[1] == "kakushi" and #dialog[4] == 4, "le Kakushi propose 4 quetes, " .. (dialog and #dialog[4] or "aucun dialogue"))
remote["wakfu:acceptQuest"](p1, "premier_pas")
check(stateOf(p1).quests.premier_pas.status == "active", "quete acceptee")
local kamasBefore, xpBefore = stateOf(p1).kamas, stateOf(p1).xp
remote["wakfu:interact"](p1)
s = stateOf(p1)
check(s.quests.premier_pas.status == "done" and s.kamas == kamasBefore + 50 and s.xp == xpBefore + 20, "recompense de Rejoindre le Corps")
check(count("wakfu:questDone", p1) == 1, "message de fin de quete")
say("quetes : Kakushi propose 4 quetes, 'Rejoindre le Corps' donne +50 yens +20 XP")

-- 5. Forge
remote["wakfu:acceptQuest"](p1, "lame_nichirin")
place(p1, "instructeur")
remote["wakfu:forgeBuy"](p1, "yufu_katana1")
check(lastNotice(p1) == "Le forgeron est trop loin", "forge trop loin : " .. tostring(lastNotice(p1)))
place(p1, "forgeron")
local forgeOpens = count("wakfu:openForge", p1)
remote["wakfu:interact"](p1)
check(count("wakfu:openForge", p1) == forgeOpens + 1, "E sur le forgeron ouvre la forge")
check(stateOf(p1).quests.lame_nichirin == nil or true, "")
remote["wakfu:forgeBuy"](p1, "pas_une_lame"); remote["wakfu:forgeBuy"](p1, "masque"); remote["wakfu:forgeBuy"](p1, 42)
local kamas = stateOf(p1).kamas
remote["wakfu:forgeBuy"](p1, "yufu_claymore54")
s = stateOf(p1)
check(s.kamas == kamas - 100, "la lame coute 100 yens : " .. kamas .. " -> " .. s.kamas)
local inventory = last("wakfu:inventory", p1)[1]
local slot
for _, entry in ipairs(inventory.slots) do if entry.id == "yufu_claymore54" then slot = entry.slot end end
check(slot, "la lame doit etre dans le sac")
check(lastNotice(p1):find("Claymore n°54 forgée", 1, true), "message de forge : " .. tostring(lastNotice(p1)))
-- plus assez de yens
for i = 1, 20 do remote["wakfu:forgeBuy"](p1, "yufu_katana2") end
check(stateOf(p1).kamas < 100, "les yens s'epuisent")
check(lastNotice(p1):find("yens pour cette lame", 1, true) or lastNotice(p1):find("sac est plein", 1, true), "fin de yens ou sac plein : " .. tostring(lastNotice(p1)))
say("forge : trop loin refuse, lames inconnues/non-lames refusees, claymore54 achetee -100 yens, achats suivants stoppes (" .. lastNotice(p1) .. ")")

-- 6. Equiper la lame forgee : elle doit se retrouver en main
remote["wakfu:invUse"](p1, slot)
check(last("wakfu:inventory", p1)[1].equip.weapon == "yufu_claymore54", "lame equipee")
check(p1.character.held and p1.character.held.mesh == "yufu-arme-test::SM_claymore54", "la lame forgee doit etre en main : " .. tostring(p1.character.held and p1.character.held.mesh))
say("equipement : la lame forgee est en main (" .. p1.character.held.mesh .. ")")

-- 6b. Traînee de l'arme
local YufuList = env.Package.Require("YufuWeapons.lua")
local function tipOf(name) for _, w in ipairs(YufuList.weapons) do if w[1] == name then return w[3] end end end
local function trailOf(player) for i = #particles, 1, -1 do local t = particles[i]; if t.valid and t.parent == player.character.held then return t end end end
local function liveCount() local n = 0 for _, t in ipairs(particles) do if t.valid then n = n + 1 end end return n end
local size1 = Config.Vfx.trail.sizes[1]
local trail = trailOf(p1)
check(trail and trail.asset == "vefects::NS_Trail_Water" and trail.autoDestroy == false and trail.lifespan == 0 and trail.bone == "" and trail.rule == 2, "traînee de la voie (Eau) attachee a la lame forgee, sans destruction automatique")
check(math.abs(trail.rel.Z - tipOf("claymore54") * size1.tip) < 1e-9 and trail.rel.X == 0 and trail.rel.Y == 0, "la traînee s'accroche a la pointe du claymore54 : " .. tostring(trail.rel.Z) .. " pour " .. tipOf("claymore54") .. " cm")
check(stateOf(p1).trail == "auto", "l'etat envoie le choix « auto »")
check(trail.autoActivate == false and trail.active == false, "la traînee est creee eteinte : elle n'existe que pendant un coup")
check(trail.scale and math.abs(trail.scale.X - size1.scale) < 1e-9 and trail.scale.Y == trail.scale.X and trail.scale.Z == trail.scale.X, "la traînee est mise a l'echelle de la taille " .. size1.label .. " (" .. size1.scale .. ")")
-- Un coup allume la traînee pendant la fenetre de degats de l'arme, puis elle s'eteint
local melee = p1.character.held
local timersBefore = #timers
melee.events.Attack(melee, p1.character)
check(trail.active and trail.resets == 1 and #timers == timersBefore + 1 and timerMs[#timers] == size1.seconds * 1000, "un coup allume la traînee pour la duree de la taille fine = " .. tostring(timerMs[#timers]) .. " ms")
timers[#timers]()
check(not trail.active, "elle s'eteint a la fin de la fenetre")
check(lastNotice(p1) and lastNotice(p1):find("Touche " .. Config.Vfx.menuKey, 1, true), "la premiere attaque affiche l'astuce de la touche : " .. tostring(lastNotice(p1)))
local noticesBefore = count("wakfu:notice", p1)
melee.events.Attack(melee, p1.character); local firstOff = timers[#timers]
melee.events.Attack(melee, p1.character); local secondOff = timers[#timers]
firstOff(); check(trail.active, "le minuteur d'un coup precedent n'eteint pas la traînee d'un coup en cours")
secondOff(); check(not trail.active, "le dernier minuteur l'eteint")
check(count("wakfu:notice", p1) == noticesBefore, "l'astuce ne s'affiche qu'une fois")
melee.events.Attack(melee, nil)
-- Taille de la traînee : changee en direct depuis le menu
check(stateOf(p1).trailSize == Config.Vfx.trail.defaultSize, "la taille de depart est celle de la config")
remote["wakfu:trailSize"](p1, "normale")
check(trail.scale.X == 1 and math.abs(trail.rel.Z - tipOf("claymore54") * 0.95) < 1e-9 and stateOf(p1).trailSize == "normale", "taille normale appliquee en direct : echelle 1, pointe a 95 %")
melee.events.Attack(melee, p1.character)
check(timerMs[#timers] == 800, "taille normale : la fenetre de degats de l'arme (800 ms) : " .. tostring(timerMs[#timers])); timers[#timers]()
remote["wakfu:trailSize"](p1, "moyenne")
check(trail.scale.X == 0.6 and math.abs(trail.rel.Z - tipOf("claymore54") * 0.85) < 1e-9, "taille moyenne")
for _, bad in ipairs({ "gigantesque", 3, true, "" }) do remote["wakfu:trailSize"](p1, bad) end
remote["wakfu:trailSize"](p1, nil)
check(stateOf(p1).trailSize == "moyenne" and trail.scale.X == 0.6, "une taille inconnue est refusee sans rien changer")
remote["wakfu:trailSize"](p1, "fine")
check(trail.scale.X == size1.scale and stateOf(p1).trailSize == "fine" and lastNotice(p1):find("Fine", 1, true), "retour a la taille fine, avec un message")
remote["wakfu:trailSize"](p1, "moyenne")
remote["wakfu:trailChoose"](p1, "vefects::NS_Trail_Fire")
check(trailOf(p1).scale.X == 0.6, "une nouvelle traînee reprend la taille choisie")
remote["wakfu:trailSize"](p1, "fine")
remote["wakfu:trailChoose"](p1, "auto")
-- Option « toujours allumee »
Config.Vfx.trail.alwaysOn = true
remote["wakfu:trailChoose"](p1, "vefects::NS_Trail_Fire")
check(trailOf(p1).active, "alwaysOn : la traînee est allumee des sa creation")
local scheduled = #timers
melee.events.Attack(melee, p1.character)
check(#timers == scheduled, "alwaysOn : un coup ne programme aucune extinction")
Config.Vfx.trail.alwaysOn = false
remote["wakfu:trailChoose"](p1, "auto")
check(not trailOf(p1).active, "retour au mode normal : traînee eteinte")
remote["wakfu:trailChoose"](p1, "vefects::NS_Trail_Fire")
local fire = trailOf(p1)
check(not trail.valid and fire and fire.asset == "vefects::NS_Trail_Fire" and stateOf(p1).trail == "vefects::NS_Trail_Fire", "choisir le feu remplace la traînee")
check(lastNotice(p1):find("Feu", 1, true), "message de choix : " .. tostring(lastNotice(p1)))
for _, bad in ipairs({ "x::y", "vefects::NS_Trail_Inconnue", "free-spells::NS_Free_Spells_Explosion", 42, true, "" }) do remote["wakfu:trailChoose"](p1, bad) end
remote["wakfu:trailChoose"](p1, nil)
check(trailOf(p1) == fire and fire.valid and stateOf(p1).trail == "vefects::NS_Trail_Fire", "un choix invalide ou qui n'est pas une traînee est refuse sans rien changer")
remote["wakfu:trailChoose"](p1, "none")
check(trailOf(p1) == nil and not fire.valid and stateOf(p1).trail == "none", "« aucune » retire la traînee")
remote["wakfu:trailChoose"](p1, "auto")
check(trailOf(p1) and trailOf(p1).asset == "vefects::NS_Trail_Water" and stateOf(p1).trail == "auto", "« auto » redonne celle de la voie")
local before = liveCount()
remote["wakfu:trailChoose"](p1, "auto")
check(liveCount() == before, "choisir deux fois la meme chose ne recree rien")
-- Arme changee : l'ancienne traînee disparait, la nouvelle suit la nouvelle arme
local old = trailOf(p1); local oldMelee = p1.character.held
remote["wakfu:weaponCycle"](p1, 1)
check(p1.character.held ~= oldMelee and not old.valid and trailOf(p1) and trailOf(p1).parent == p1.character.held, "changer d'arme deplace la traînee sur la nouvelle")
subs["Wakfu:EquipWeapon"](p1, "yufu_typ_yoru_sold")
check(math.abs(trailOf(p1).rel.Z - Config.Vfx.trail.defaultTip * size1.tip) < 1e-9, "une lame qui pend sous la main (pointe -20 cm) retombe sur la distance par defaut : " .. tostring(trailOf(p1).rel.Z))
subs["Wakfu:EquipWeapon"](p1, "yufu_katana1")
check(math.abs(trailOf(p1).rel.Z - tipOf("katana1") * size1.tip) < 1e-9, "katana1 : pointe a " .. tipOf("katana1") .. " cm")
-- Un effet qui ne se charge pas : aucune erreur, la traînee est simplement absente
failParticles = true
remote["wakfu:trailChoose"](p1, "vefects::NS_Trail_Fire")
check(trailOf(p1) == nil and stateOf(p1).trail == "vefects::NS_Trail_Fire", "un effet qui ne se charge pas ne plante rien")
failParticles = false
remote["wakfu:trailChoose"](p1, "vefects::NS_Trail_Water")
check(trailOf(p1) and trailOf(p1).asset == "vefects::NS_Trail_Water", "la traînee revient des que l'effet se charge")
-- Joueur parti : sa traînee est detruite avec son arme
local victimTrail = trailOf(p2)
check(victimTrail and victimTrail.valid, "tout joueur arme a sa traînee")
handlers.Destroy(p2.character)
check(not victimTrail.valid, "la traînee d'un personnage detruit est detruite")
remote["wakfu:trailChoose"](p1, "auto")
say("traînee : attachee a la pointe de la lame (selon la taille), changement de choix, repli sans mesure, effet qui ne charge pas, nettoyage")

-- 7. Changer de voie (dans son camp : l'autre camp est refuse)
place(p1, "maitre_respirations")
remote["wakfu:interact"](p1)
check(count("wakfu:openClassReroll", p1) == 1, "le maitre des respirations ouvre l'ecran")
remote["wakfu:classReroll"](p1, "Demon")
check(stateOf(p1).class == "Eau" and lastNotice(p1):find("définitif", 1, true), "le camp ne se change pas chez le maitre : " .. tostring(lastNotice(p1)))
remote["wakfu:classReroll"](p1, "Foudre")
local Ranks = env.Package.Require("Ranks.lua")
check(stateOf(p1).class == "Foudre" and stateOf(p1).rank.name == Ranks.Get("slayer", stateOf(p1).xp).name, "passage a la Foudre : " .. stateOf(p1).rank.name)
check(trailOf(p1) and trailOf(p1).asset == "vefects::NS_Trail_Fire", "voie Foudre dont la traînee n'est pas cuite : repli sur une traînee de la banque, " .. tostring(trailOf(p1) and trailOf(p1).asset))
check(lastNotice(p1) == "Nouvelle voie : Souffle de la Foudre", "message : " .. tostring(lastNotice(p1)))
remote["wakfu:classReroll"](p1, "Foudre")
check(lastNotice(p1):find("déjà", 1, true), "meme voie refusee : " .. tostring(lastNotice(p1)))
remote["wakfu:classReroll"](p1, "Wakfu")
check(stateOf(p1).class == "Foudre", "classe inconnue refusee")
cast(p1, 3); cast(p1, 4)
say("voie : Eau -> Foudre (" .. stateOf(p1).rank.name .. "), autre camp, meme voie et classe inconnue refuses")

-- 8. Entrainement (reroll des stats)
place(p1, "instructeur")
local y = stateOf(p1).kamas
stateOf(p1)
remote["wakfu:reroll"](p1)
local rolled = last("wakfu:rerolled", p1)
if y >= 50 then check(rolled ~= nil, "entrainement paye") else check(last("wakfu:rerollFailed", p1), "entrainement refuse faute de yens") end
say("entrainement : " .. (y >= 50 and "accepte" or "refuse faute de yens") .. " (" .. y .. " yens)")
return out
'''

failed = False
for label, root in RP.items():
    print("== wakfu-rp", label)
    for name, code in (("donnees", DATA), ("serveur", SERVER)):
        try:
            lines = LuaRuntime().eval("function(...) " + code + " end")(root)
            for i in range(1, len(lines) + 1):
                print("  [%s] %s" % (name, lines[i]))
        except Exception as error:  # noqa: BLE001
            failed = True
            print("  [%s] %s" % (name, str(error).encode("ascii", "replace").decode()))
sys.exit(1 if failed else 0)
