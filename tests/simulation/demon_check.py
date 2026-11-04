"""Simule (sans le jeu) le système du démon de wakfu-rp : logique pure, serveur (camp, sang, dévoration, faim, régénération) et client (écran de camp)."""
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
local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local out = {}
local function say(text) out[#out + 1] = text end
'''

DATA = PRELUDE + r'''
local Demon, Config, Classes, Npcs, Combat = env.Package.Require("Demon.lua"), env.Package.Require("Config.lua"), env.Package.Require("Classes.lua"),
	env.Package.Require("Npcs.lua"), env.Package.Require("Combat.lua")
local cfg = Config.Demon

-- Camps et classes
check(Classes.Camps.slayer.defaultClass == "Eau" and Classes.Camps.demon.defaultClass == "Demon", "voies de depart des camps")
check(Classes.Camps.slayer.ladder == "slayer" and Classes.Camps.demon.ladder == "demon" and #Classes.CampOrder == 2, "echelles et ordre des camps")
local slayers = 0
for name, class in pairs(Classes.List) do
	check(class.camp == (class.ladder == "demon" and "demon" or "slayer") and Classes.CampOf(name) == class.camp, name .. " : camp")
	if class.camp == "slayer" then slayers = slayers + 1 end
end
check(slayers == 7 and Classes.CampOf("Demon") == "demon" and Classes.CampOf("Inconnue") == nil, "7 voies de pourfendeur, 1 de demon")
for _, id in ipairs(Classes.CampOrder) do
	local camp = Classes.Camps[id]
	check(camp.name and camp.kanji and camp.color:match("^#%x%x%x%x%x%x$") and camp.blurb and #camp.points >= 3 and Classes.List[camp.defaultClass].camp == id, id .. " : champs du camp")
end
for name, class in pairs(Classes.List) do
	for _, spell in ipairs(class.spells) do
		check((class.camp == "demon") == (spell.glyph ~= nil), name .. " : kanji de technique seulement pour le demon (" .. spell.id .. ")")
		check(spell.glyph == nil or #spell.glyph >= 3, spell.id .. " : le kanji est un caractere japonais")
	end
end
say("camps : pourfendeur (7 voies, depart Eau) et demon (1 voie, depart Demon), champs d'affichage complets")

-- Reglages coherents
check(#cfg.tiers >= 3 and cfg.tiers[1].souls == 0, "le premier palier commence a 0 ame")
for i = 2, #cfg.tiers do
	local a, b = cfg.tiers[i - 1], cfg.tiers[i]
	check(b.souls > a.souls and b.hp >= a.hp and b.damagePct >= a.damagePct and b.regen >= a.regen, "paliers croissants : " .. b.name)
end
check(cfg.souls.max >= cfg.tiers[#cfg.tiers].souls, "le plafond d'ames permet le dernier palier")
check(#cfg.blood.costs == 4 and cfg.unlock[4] and cfg.unlock[4] <= #cfg.tiers, "4 couts de sang, technique 4 verrouillee a un palier qui existe")
for kind, source in pairs(cfg.sources) do check(source.flesh > 0 and source.souls > 0 and source.heal >= 0 and source.heal < 1, "source " .. kind) end
check(cfg.devour.seconds > 0 and cfg.devour.range >= 100 and cfg.devour.civilRespawn > cfg.devour.seconds, "reglages de la dévoration")
say("reglages : " .. #cfg.tiers .. " paliers croissants, 4 couts de sang, technique 4 verrouillee au palier " .. cfg.unlock[4])

-- Etat de depart, paliers
local d = Demon.New(cfg)
check(d.blood == cfg.blood.max and d.flesh == 0 and d.souls == 0, "demon neuf : plein de sang, sans chair ni ames")
local function tier(souls) return (Demon.Tier(cfg, souls)) end
check(tier(0) == 1 and tier(9) == 1 and tier(10) == 2 and tier(29) == 2 and tier(30) == 3 and tier(99) == 4 and tier(100) == 5 and tier(9999) == 5 and tier(nil) == 1, "seuils de paliers")
local b = Demon.Bonuses(cfg, { souls = 60 }); check(b.tier == 4 and b.hp == 300 and b.damagePct == 20, "bonus du palier 4")
say("paliers : 0, 10, 30, 60, 100 ames -> paliers 1 a 5 ; bonus du palier 4 = +300 PV, +20 % de degats")

-- Sang et verrou
local cost = Demon.SpellCost(cfg, 1); check(cost == 8 and Demon.SpellCost(cfg, 4) == 40 and Demon.SpellCost(cfg, 9) == 0, "couts")
local ok, reason, need = Demon.TryCast(cfg, d, 4); check(not ok and reason == "locked" and need == 4 and d.blood == 100, "technique 4 verrouillee au palier 1, sans payer")
ok = Demon.TryCast(cfg, d, 1); check(ok and d.blood == 92, "technique 1 payee")
d.blood = 5; ok, reason, need = Demon.TryCast(cfg, d, 2); check(not ok and reason == "blood" and need == 12 and d.blood == 5, "pas assez de sang : refuse sans payer")
d.souls = 60; d.blood = 100; ok = Demon.TryCast(cfg, d, 4); check(ok and d.blood == 60, "technique 4 debloquee au palier 4")
say("sang : technique 1 = -8, technique 4 verrouillee puis debloquee au palier 4 (-40), refus sans payer si le sang manque")

-- Repas
d = Demon.New(cfg)
local c = Demon.Consume(cfg, d, "civil")
check(c.flesh == 40 and c.souls == 4 and c.heal == 0.15 and c.xp == 15 and not c.tierUp and d.flesh == 40 and d.souls == 4 and d.sinceFed == 0, "premier civil")
Demon.Consume(cfg, d, "civil"); c = Demon.Consume(cfg, d, "civil")
check(c.tierUp and c.tier == 2 and d.souls == 12 and d.flesh == 100, "3 civils : palier 2, chair plafonnee a 100")
check(Demon.Consume(cfg, d, "joueur") == nil and Demon.Consume(cfg, d, nil) == nil, "aucune source « joueur » : jamais un joueur sans son accord")
for _ = 1, 100 do Demon.Consume(cfg, d, "civil") end
check(d.souls == cfg.souls.max and d.flesh == cfg.flesh.max, "plafonds d'ames et de chair")
say("repas : civil = chair +40, ames +4, +15 XP ; 3 civils = palier 2 ; plafonds respectes ; aucune source joueur")

-- Temps : sang, chair, regeneration
d = Demon.New(cfg); d.blood = 0; d.flesh = 50
local r = Demon.Tick(cfg, d, 1)
check(math.abs(d.blood - cfg.blood.perSecond) < 1e-9 and math.abs(d.flesh - (50 - cfg.flesh.decayPerSecond)) < 1e-9, "sang +, chair -")
local expected = (cfg.regen.base * (1 + cfg.regen.fleshBoost * d.flesh / cfg.flesh.max))
check(math.abs(r.heal - expected) < 1e-9 and r.hunger == nil, "regeneration amplifiee par la chair : " .. r.heal .. " vs " .. expected)
local hungry = Demon.New(cfg); local rh = Demon.Tick(cfg, hungry, 1)
check(math.abs(rh.heal - cfg.regen.base * cfg.regen.hungryFactor) < 1e-9 and rh.heal < r.heal, "affame : regeneration etouffee")
Demon.Hit(d); check(Demon.Tick(cfg, d, 1).heal == 0, "en combat : aucune regeneration")
for _ = 1, cfg.combatSeconds do Demon.Tick(cfg, d, 1) end
check(Demon.Tick(cfg, d, 1).heal > 0, "6 s sans combat : la regeneration reprend")
d.sinceCombat = 99; check(Demon.Tick(cfg, d, 1, { sun = true }).heal == 0, "plein soleil : aucune regeneration")
local tiered = Demon.New(cfg); tiered.souls = 60; tiered.flesh = 50
check(Demon.Tick(cfg, tiered, 1).heal > Demon.Tick(cfg, Demon.New(cfg), 1).heal, "un palier eleve regenere plus")
say("temps : sang +" .. cfg.blood.perSecond .. "/s, chair -" .. cfg.flesh.decayPerSecond .. "/s ; regeneration amplifiee par la chair, etouffee a jeun, coupee en combat et au soleil")

-- Faim : la puissance retombe d'un palier
d = Demon.New(cfg); d.souls = 40; d.sinceFed = 0
local drop
for second = 1, cfg.souls.hungerSeconds do local step = Demon.Tick(cfg, d, 1); if step.hunger then drop = { step.hunger, second } end end
check(drop and drop[1].from == 3 and drop[1].to == 2 and drop[2] == cfg.souls.hungerSeconds and d.souls == cfg.tiers[2].souls, "faim : palier 3 -> 2 apres " .. cfg.souls.hungerSeconds .. " s, ames ramenees a " .. d.souls)
for _ = 1, cfg.souls.hungerSeconds do Demon.Tick(cfg, d, 1) end
check(tier(d.souls) == 1, "un autre delai sans repas : palier 1")
for _ = 1, cfg.souls.hungerSeconds * 2 do Demon.Tick(cfg, d, 1) end
check(d.souls == 0 and tier(d.souls) == 1, "la puissance ne descend pas sous le palier 1")
d.souls = 40; d.sinceFed = cfg.souls.hungerSeconds - 1; Demon.Consume(cfg, d, "civil")
for _ = 1, cfg.souls.hungerSeconds - 1 do check(Demon.Tick(cfg, d, 1).hunger == nil, "un repas remet la faim a zero") end
say("faim : sans repas pendant " .. cfg.souls.hungerSeconds .. " s, la puissance retombe d'un palier, jamais sous le palier 1 ; un repas remet le delai a zero")

-- Vue du HUD
d = Demon.New(cfg); d.souls = 22; d.blood = 62.9; d.flesh = 55.4
local v = Demon.View(cfg, d)
check(v.blood == 62 and v.flesh == 55 and v.souls == 22 and v.soulsFloor == 10 and v.soulsNext == 30 and v.tier == 2 and v.tierCount == 5 and v.tierName == "Chasseur de nuit" and not v.hungry, "vue : jauges arrondies et progression vers le palier 3")
check(v.nextName == "Prédateur", "vue : nom du palier suivant : " .. tostring(v.nextName))
d.souls = 120; v = Demon.View(cfg, d); check(v.tier == 5 and v.soulsNext == nil, "vue : dernier palier sans suivant")
check(v.nextName == nil, "vue : pas de palier suivant au maximum")
check(v.costs[1] == 8 and v.unlock[4] == 4 and Demon.View(cfg, Demon.New(cfg)).hungry, "vue : couts, verrou, faim")
say("vue du HUD : jauges, palier, progression vers le suivant, couts et verrou")

-- Civils
local civils = 0
for _, npc in ipairs(Npcs.List) do
	if npc.civil then
		civils = civils + 1
		check(#npc.services == 0 and #npc.quests == 0 and npc.dialogue ~= "", npc.id .. " : un civil n'a ni service ni quete")
		for _, other in ipairs(Npcs.List) do
			if other ~= npc and not other.showcase then
				local dx, dy = npc.position.x - other.position.x, npc.position.y - other.position.y
				check(dx * dx + dy * dy > 300 * 300, npc.id .. " et " .. other.id .. " trop proches (E parlerait au mauvais)")
			end
		end
	end
end
check(civils == 4, "4 civils, " .. civils)
local near = Npcs.NearestCivil({ x = 700, y = 500, z = 100 }, 220)
check(near and near.id == "civil_villageois", "le civil le plus proche")
check(Npcs.NearestCivil({ x = 700, y = 500, z = 100 }, 220, { civil_villageois = true }) == nil, "un civil absent est ignore")
check(Npcs.NearestCivil({ x = 0, y = 0, z = 100 }, 220) == nil and Npcs.NearestCivil({ x = 200, y = 0, z = 100 }, 220) == nil, "les PNJ de service ne sont pas des proies")
say("civils : 4, sans service ni quete, assez loin des autres PNJ ; le plus proche est trouve, un civil absent ou un PNJ de service est ignore")

-- Limite de repas par jour et par grade
check(cfg.meals.dayLength > 0 and cfg.meals.perRank >= 1 and cfg.meals.kinds.corpse and cfg.meals.kinds.civil and not cfg.meals.kinds.hunt, "reglages des repas")
check(cfg.sources.corpse and cfg.sources.corpse.flesh > cfg.sources.civil.flesh and cfg.sources.corpse.souls > 0 and cfg.sources.corpse.xp > 0, "un cadavre rapporte plus qu'un civil")
check(Config.Corpses.enabled and Config.Corpses.lifetime > 0 and Config.Corpses.demonsLeaveBody == false, "reglages des cadavres")
check(Demon.DailyCap(cfg, 1) == 5 and Demon.DailyCap(cfg, 2) == 10 and Demon.DailyCap(cfg, 3) == 15 and Demon.DailyCap(cfg, 8) == 40 and Demon.DailyCap(cfg, nil) == 5, "5 repas par jour au premier grade, 10 au deuxieme, 15 au troisieme... 40 au huitieme")
local fixed = { meals = { perRank = 5, caps = { [2] = 7 }, kinds = cfg.meals.kinds, dayLength = 100 } }
check(Demon.DailyCap(fixed, 2) == 7 and Demon.DailyCap(fixed, 3) == 15, "la liste caps fixe un maximum a la main, le reste suit perRank")
d = Demon.New(cfg)
check(d.meals == 0 and Demon.CanEat(cfg, d, 1, "corpse"), "demon neuf : aucun repas")
for i = 1, 5 do check(Demon.CanEat(cfg, d, 1, "corpse"), "repas " .. i .. " permis au grade 1"); Demon.Consume(cfg, d, "corpse") end
local allowed, reason, cap = Demon.CanEat(cfg, d, 1, "corpse")
check(not allowed and reason == "cap" and cap == 5 and d.meals == 5, "6e repas refuse au grade 1 : limite 5")
check(not Demon.CanEat(cfg, d, 1, "civil"), "un civil compte dans la limite")
check(Demon.CanEat(cfg, d, 1, "hunt") and Demon.CanEat(cfg, d, 1, "inconnue"), "une source qui ne compte pas passe toujours")
Demon.Consume(cfg, d, "hunt"); check(d.meals == 5, "la chasse ne compte pas dans les repas")
check(Demon.CanEat(cfg, d, 2, "corpse"), "le grade 2 permet 10 repas")
for _ = 1, 5 do Demon.Consume(cfg, d, "corpse") end
check(d.meals == 10 and not Demon.CanEat(cfg, d, 2, "corpse") and Demon.CanEat(cfg, d, 3, "corpse"), "10 repas : le grade 2 est a la limite, le grade 3 non")
Demon.Tick(cfg, d, cfg.meals.dayLength - 1); check(d.meals == 10, "avant la fin du jour, le compteur reste")
Demon.Tick(cfg, d, 1); check(d.meals == 0 and d.dayElapsed == 0 and Demon.CanEat(cfg, d, 1, "corpse"), "un nouveau jour remet les repas a zero")
d.meals = 3; v = Demon.View(cfg, d, 2)
check(v.meals == 3 and v.mealsCap == 10 and Demon.View(cfg, d, 1).mealsCap == 5 and Demon.View(cfg, d).mealsCap == 5, "vue : repas du jour et limite du grade")
say("repas : 5 par jour au grade 1, 10 au grade 2, 15 au grade 3... (liste caps possible) ; cadavres et civils comptent, la chasse non ; un nouveau jour remet a zero")
return out
'''

SERVER = PRELUDE + r'''
local Items = env.Package.Require("Items.lua")
local Config = env.Package.Require("Config.lua")
local Demon = env.Package.Require("Demon.lua")
local clock = 1000
local timeouts, intervals = {}, {}
local remote, subs, handlers, sent, melees, allChars = {}, {}, {}, {}, {}, {}
local nextId = 0
local function vec(x, y, z) return setmetatable({ X = x, Y = y, Z = z }, { __add = function(a, b) return vec(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end, __index = { Distance = function(a, b) return math.sqrt((a.X-b.X)^2 + (a.Y-b.Y)^2 + (a.Z-b.Z)^2) end } }) end
env.Vector = function(x, y, z) return vec(x or 0, y or 0, z or 0) end
env.Rotator = function() return { Yaw = 0 } end
env.Color = function() return Any end
env.Server = { GetTime = function() return clock end }
env.Timer = {
	SetTimeout = function(fn, ms) timeouts[#timeouts + 1] = { fn = fn, ms = ms, done = false }; return #timeouts end,
	SetInterval = function(fn, ms) intervals[#intervals + 1] = { fn = fn, ms = ms, acc = 0, on = true }; return #intervals end,
	ClearInterval = function(id) if intervals[id] then intervals[id].on = false end end,
}
env.Console = { Log = function() end, Warn = function() end, Error = function(m) error("Console.Error : " .. tostring(m), 0) end }
local function newCharacter(location)
	nextId = nextId + 1
	local id, loc = nextId, location
	local c = { hp = 100, maxHp = 100, held = nil, valid = true, values = {}, visible = true }
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
	function c:SetVisibility(v) self.visible = v end
	function c:SetStanceMode(v) self.stance = v end
	function c:PlayAnimation(a) self.anim = a end
	function c:StopAnimation() self.anim = false end
	function c:ApplyDamage(amount) self.hp = math.max(0, self.hp - amount) end
	allChars[#allChars + 1] = c
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
env.StanceMode = { Crouching = "Crouching", Standing = "Standing", None = "None" }
env.HandlingMode = setmetatable({}, { __index = function(_, k) return k end })
env.AnimationSlotType = setmetatable({}, { __index = function(_, k) return k end })
env.CollisionType = { Normal = 0 }
env.Reliability = { Reliable = 1, Unreliable = 2 }
env.DamageType = { Unknown = 0 }
env.TextRender = function() return Any end
env.TextRenderRenderingType = Any
env.StaticMesh = function() return Any end
env.AttachmentRule = { KeepRelative = 0, KeepWorld = 1, SnapToTarget = 2 }
env.Particle = function() local p = { valid = true }; function p:IsValid() return self.valid end; function p:Destroy() self.valid = false end; function p:Activate() end; function p:Deactivate() end; function p:SetScale() end; function p:AttachTo() return true end; function p:SetRelativeLocation() end; return p end

assert(loadfile(ROOT .. "/Server/Index.lua", "t", env))()

local function newPlayer(name)
	local p = { name = name, valid = true }
	nextId = nextId + 1
	local id = nextId
	function p:GetID() return id end
	function p:GetName() return self.name end
	function p:IsValid() return self.valid end
	function p:GetControlledCharacter() return self.character end
	function p:Possess(c) self.character = c; c.player = self end
	players[id] = p
	handlers.PlayerSpawn(p)
	return p
end
local function last(name, player)
	for i = #sent, 1, -1 do if sent[i].name == name and (not player or sent[i].player == player) then return sent[i].args end end
end
local function count(name, player) local n = 0 for _, s in ipairs(sent) do if s.name == name and (not player or s.player == player) then n = n + 1 end end return n end
local function stateOf(player) return last("wakfu:state", player)[1] end
local function lastNotice(player) local a = last("wakfu:notice", player); return a and a[1] end
local function place(player, x, y) player.character:SetLocation(vec(x, y, 100)) end
local function cast(player, i) clock = clock + 100; remote["wakfu:castIndex"](player, i) end
-- Fait avancer les minuteurs a intervalle de ms millisecondes (par pas de 250 ms).
local function advance(ms)
	for _ = 1, math.floor(ms / 250) do
		for i = 1, #intervals do
			local t = intervals[i]
			if t.on then t.acc = t.acc + 250; while t.acc >= t.ms and t.on do t.acc = t.acc - t.ms; t.fn() end end
		end
	end
end
local function fire(ms) for _, t in ipairs(timeouts) do if not t.done and t.ms == ms then t.done = true; t.fn() end end end
local function civilBody(npcId) for _, c in ipairs(allChars) do if c.values.npcId == npcId then return c end end end
local CIV = { { "civil_villageois", 700, 500 }, { "civil_marchande", -700, -400 }, { "civil_bucheron", 1000, -300 }, { "civil_paysanne", -900, 300 } }
local cfg = Config.Demon
local RESPAWN = cfg.devour.civilRespawn * 1000
local savedPerRank, savedDayLength = cfg.meals.perRank, cfg.meals.dayLength
cfg.meals.perRank = 1000 -- la limite de repas est testee plus bas, avec ses propres joueurs

-- 1. Arrivee : aucun camp, l'ecran de choix s'ouvre, rien d'autre ne marche
local p1 = newPlayer("Tanjiro")
handlers.PlayerReady(p1)
check(count("wakfu:openWelcome", p1) == 1 and count("wakfu:openCamp", p1) == 0, "un joueur voit d abord l ecran de bienvenue (le choix du camp suit cote client)")
local s = stateOf(p1)
check(s.camp == nil and s.demon == nil, "pas de camp ni de jauges avant le choix")
remote["wakfu:chooseClass"](p1, "Foudre"); check(stateOf(p1).class == "Eau", "pas de changement de voie avant le camp")
remote["wakfu:classReroll"](p1, "Foudre"); check(stateOf(p1).class == "Eau", "pas de reroll avant le camp")
remote["wakfu:create"](p1, "Foudre", "Homme", 1, "x", nil); check(stateOf(p1).class == "Eau", "pas de creation avant le camp")
for _, bad in ipairs({ "chaos", "", 5, true }) do remote["wakfu:chooseCamp"](p1, bad) end
remote["wakfu:chooseCamp"](p1, nil)
check(stateOf(p1).camp == nil, "un camp inconnu est refuse")
remote["wakfu:devour"](p1); check(count("wakfu:devourStart", p1) == 0, "un joueur sans camp ne dévore rien")
say("arrivee : ecran de choix du camp, voies/creation/reroll refuses avant le choix, camps invalides refuses")

-- 2. Pourfendeur : voie de depart, lame en main, aucun systeme de demon
remote["wakfu:chooseCamp"](p1, "slayer")
s = stateOf(p1)
check(s.camp == "slayer" and s.class == "Eau" and s.demon == nil and s.rank.name == "Mizunoto", "pourfendeur : voie Eau, grade Mizunoto, pas de jauges")
check(p1.character.held and p1.character.held.mesh == "aksel-animations::Katana_sword", "le pourfendeur tient sa lame")
remote["wakfu:chooseCamp"](p1, "demon"); check(stateOf(p1).camp == "slayer" and stateOf(p1).demon == nil, "le camp ne se rechoisit pas")
remote["wakfu:chooseClass"](p1, "Demon"); check(stateOf(p1).class == "Eau", "un pourfendeur ne prend pas la voie des demons (F-touche)")
remote["wakfu:classReroll"](p1, "Demon"); check(stateOf(p1).class == "Eau" and lastNotice(p1):find("définitif", 1, true), "reroll vers l'autre camp refuse : " .. tostring(lastNotice(p1)))
remote["wakfu:create"](p1, "Demon", "Homme", 1, "x", nil); check(stateOf(p1).class == "Eau", "creation d'une voie de l'autre camp refusee")
remote["wakfu:chooseClass"](p1, "Foudre"); check(stateOf(p1).class == "Foudre", "changer de voie dans son camp reste possible")
remote["wakfu:classReroll"](p1, "Vent"); check(stateOf(p1).class == "Vent", "reroll dans son camp")
remote["wakfu:chooseClass"](p1, "Eau")
place(p1, 700, 500); remote["wakfu:devour"](p1)
check(count("wakfu:devourStart", p1) == 0 and count("wakfu:demon", p1) == 0, "un pourfendeur ne dévore pas et ne recoit pas de jauges")
advance(3000); check(count("wakfu:demon", p1) == 0, "le temps du demon ne touche pas un pourfendeur")
say("pourfendeur : voie Eau, lame en main, camp verrouille (autre camp refuse partout), voies de son camp libres, aucun systeme de demon")

-- 3. Demon : voie Demon, pas de lame, jauges, grade des Lunes
local d1 = newPlayer("Muzan")
handlers.PlayerReady(d1)
remote["wakfu:chooseCamp"](d1, "demon")
s = stateOf(d1)
check(s.camp == "demon" and s.class == "Demon" and s.rank.name == "Démon errant", "demon : voie Demon, grade Demon errant")
check(s.demon and s.demon.blood == 100 and s.demon.flesh == 0 and s.demon.souls == 0 and s.demon.tier == 1 and s.demon.hungry and s.demon.bloodMax == 100, "jauges de depart : sang plein, ni chair ni ames")
local function armed(p) return p.character.held ~= nil and p.character.held:IsValid() end
check(not armed(d1), "un demon ne tient pas de lame Nichirin")
check(d1.character.maxHp == 1300, "PV de depart du demon : " .. d1.character.maxHp)
remote["wakfu:weaponCycle"](d1, 1); check(not armed(d1), "les fleches n'arment pas un demon")
subs["Wakfu:EquipWeapon"](d1, "yufu_katana1"); check(not armed(d1), "le menu de props n'arme pas un demon")
remote["wakfu:chooseClass"](d1, "Eau"); remote["wakfu:classReroll"](d1, "Eau"); remote["wakfu:create"](d1, "Eau", "Homme", 1, "x", nil)
check(stateOf(d1).class == "Demon" and stateOf(d1).camp == "demon", "un demon ne devient pas pourfendeur")
remote["wakfu:chooseCamp"](d1, "slayer"); check(stateOf(d1).camp == "demon", "le camp du demon ne se rechoisit pas")
say("demon : voie Demon, grade Demon errant, jauges de depart, PV " .. d1.character.maxHp .. ", sans lame ni fleches, camp verrouille")

-- 4. Techniques : sang et verrou
local target = newPlayer("Cible"); remote["wakfu:chooseCamp"](target, "slayer")
place(d1, 0, 0); place(target, 100, 0)
local function view() return last("wakfu:demon", d1)[1] end
local hpTarget = target.character.hp
cast(d1, 1)
check(count("wakfu:cast", d1) == 1 and view().blood == 92 and target.character.hp < hpTarget, "technique 1 : -8 sang, la cible est blessee")
cast(d1, 4)
check(count("wakfu:cast", d1) == 1 and lastNotice(d1):find("verrouillée", 1, true) and lastNotice(d1):find("Seigneur de sang", 1, true), "technique 4 verrouillee : " .. tostring(lastNotice(d1)))
check(view().blood == 92, "une technique refusee ne coute rien")
d1.character.hp = 600
cast(d1, 3)
check(count("wakfu:cast", d1) == 2 and d1.character.hp == 900 and view().blood == 67, "Regeneration : -25 sang, +300 PV")
for _ = 1, 20 do cast(d1, 2) end
check(lastNotice(d1):find("Pas assez de sang", 1, true) and view().blood < 12, "a court de sang : refus avec message (" .. tostring(lastNotice(d1)) .. ", sang " .. view().blood .. ")")
say("techniques : -8 sang (griffes), Regeneration -25 sang +300 PV, technique 4 verrouillee tant que le palier 4 n'est pas atteint, refus a court de sang")

-- 5. Temps : le sang remonte, la regeneration passive depend du combat
advance(10000)
check(view().blood > 25, "le sang remonte avec le temps : " .. view().blood)
handlers.TakeDamage(d1.character, 10) -- un coup vient d'etre recu
d1.character.hp = 500
local before = d1.character.hp
advance(1000); local inCombat = d1.character.hp
check(inCombat == before, "pas de regeneration juste apres un combat : " .. before .. " -> " .. inCombat)
advance(8000)
check(d1.character.hp > before + 10, "la regeneration passive soigne hors combat : " .. before .. " -> " .. d1.character.hp)
handlers.TakeDamage(d1.character, 10); local hit = d1.character.hp; advance(3000)
check(d1.character.hp == hit, "un coup recu coupe la regeneration")
d1.character.hp = d1.character.maxHp - 50; advance(30000)
check(d1.character.hp == d1.character.maxHp, "la regeneration est plafonnee aux PV max")
say("temps : le sang remonte, regeneration passive hors combat seulement (coupee par un coup recu), plafonnee aux PV max")

-- 6. Devorer : portee, geste, interruptions
place(d1, 0, 0); remote["wakfu:devour"](d1)
check(count("wakfu:devourStart", d1) == 0 and lastNotice(d1) == "Aucune proie à portée", "aucune proie a portee : " .. tostring(lastNotice(d1)))
place(d1, 200, 0); remote["wakfu:devour"](d1)
check(count("wakfu:devourStart", d1) == 0, "un PNJ de service n'est pas une proie")
place(d1, 700, 500)
local fleshBefore = view().flesh
remote["wakfu:devour"](d1)
local startArgs = last("wakfu:devourStart", d1)
check(startArgs and startArgs[1] == "Villageois" and startArgs[2] == cfg.devour.seconds, "le geste commence : " .. tostring(startArgs and startArgs[1]))
check(startArgs[3] and startArgs[3].flesh == 40 and startArgs[3].souls == 4 and startArgs[3].heal == 15 and startArgs[3].xp == 15, "le gain attendu accompagne le debut du geste")
remote["wakfu:devour"](d1); check(count("wakfu:devourStart", d1) == 1, "un seul geste a la fois")
advance(1500); check(count("wakfu:devourStop", d1) == 0 and view().flesh <= fleshBefore, "rien n'est consomme avant la fin du geste")
-- interruption par un coup
handlers.TakeDamage(d1.character, 10)
check(count("wakfu:devourStop", d1) == 1 and lastNotice(d1):find("Repas interrompu", 1, true) and lastNotice(d1):find("frappé", 1, true), "un coup recu interrompt : " .. tostring(lastNotice(d1)))
advance(4000); check(view().souls == 0 and civilBody("civil_villageois").visible, "un geste interrompu ne donne rien et la proie reste la")
-- interruption par une technique
remote["wakfu:devour"](d1); advance(500); cast(d1, 1)
check(count("wakfu:devourStop", d1) == 2 and lastNotice(d1):find("technique", 1, true), "lancer une technique interrompt : " .. tostring(lastNotice(d1)))
-- interruption par la distance
advance(7000)
remote["wakfu:devour"](d1); advance(500); place(d1, 700, 1500); advance(500)
check(count("wakfu:devourStop", d1) == 3 and lastNotice(d1):find("éloigné", 1, true), "s'eloigner interrompt : " .. tostring(lastNotice(d1)))
-- interruption par la mort
place(d1, 700, 500); remote["wakfu:devour"](d1); advance(500)
handlers.Death(d1.character); check(count("wakfu:devourStop", d1) == 4, "mourir interrompt")
fire(Config.RespawnDelay * 1000) -- reapparition au Domaine : le demon garde son etat
advance(6000)
say("dévoration : portee 220 cm, un seul geste a la fois, interrompu par un coup, une technique, la distance ou la mort (rien consomme)")

-- 7. Un repas aboutit : chair, ames, soin, XP, disparition et retour du civil
place(d1, 700, 500)
d1.character.hp = 600
local xpBefore = stateOf(d1).xp
remote["wakfu:devour"](d1); advance(cfg.devour.seconds * 1000)
check(count("wakfu:devourStop", d1) == 5, "le geste se termine")
s = stateOf(d1)
check(s.demon.flesh >= 39 and s.demon.souls == 4 and s.xp == xpBefore + 15, "repas : chair +40, ames +4, XP +15 : " .. s.demon.flesh .. "/" .. s.demon.souls .. "/" .. s.xp)
check(d1.character.hp >= 600 + math.floor(d1.character.maxHp * 0.15) - 1, "repas : soin de 15 % des PV max : " .. d1.character.hp)
check(lastNotice(d1):find("Villageois dévoré", 1, true), "message du repas : " .. tostring(lastNotice(d1)))
check(civilBody("civil_villageois").visible == false, "le civil dévoré disparait")
remote["wakfu:devour"](d1); check(count("wakfu:devourStart", d1) == 5 or lastNotice(d1) == "Aucune proie à portée", "le civil absent n'est pas une proie")
fire(RESPAWN); check(civilBody("civil_villageois").visible == true, "le civil revient apres " .. cfg.devour.civilRespawn .. " s")
say("repas : chair +40, ames +4, +15 XP, +15 % PV, civil absent " .. cfg.devour.civilRespawn .. " s puis de retour")

-- 8. Paliers : trois civils = palier 2, PV max en hausse ; le palier 4 debloque la technique 4
local maxBefore = d1.character.maxHp
local function eat(index)
	local civil = CIV[index]
	place(d1, civil[2], civil[3]); remote["wakfu:devour"](d1); advance(cfg.devour.seconds * 1000 + 250)
	fire(RESPAWN)
end
eat(2); eat(3)
s = stateOf(d1)
check(s.demon.souls == 12 and s.demon.tier == 2 and s.demon.tierName == "Chasseur de nuit", "3 civils : 12 ames, palier 2 : " .. s.demon.souls .. " " .. tostring(s.demon.tierName))
check(d1.character.maxHp == maxBefore + 80, "le palier 2 donne +80 PV max : " .. maxBefore .. " -> " .. d1.character.maxHp)
check(lastNotice(d1):find("palier", 1, true), "message de palier : " .. tostring(lastNotice(d1)))
for i = 1, 12 do eat((i % 4) + 1) end
s = stateOf(d1)
check(s.demon.souls == 60 and s.demon.tier == 4, "15 civils au total : 60 ames, palier 4 : " .. s.demon.souls .. " tier " .. s.demon.tier)
d1.character.hp = d1.character.maxHp
local castsBefore = count("wakfu:cast", d1)
view().blood = 100
d1.character.hp = d1.character.maxHp; clock = clock + 100000
remote["wakfu:castIndex"](d1, 4)
check(count("wakfu:cast", d1) == castsBefore + 1 or lastNotice(d1):find("Pas assez de sang", 1, true), "la technique 4 se lance au palier 4 (ou manque de sang) : " .. tostring(lastNotice(d1)))
check(not (lastNotice(d1) or ""):find("verrouillée", 1, true), "plus de verrou au palier 4")
say("paliers : 3 civils = palier 2 (+80 PV max), 15 civils = palier 4, technique 4 debloquee")

-- 9. Faim : sans repas, la puissance retombe
local f0 = view().tier
advance((cfg.souls.hungerSeconds + 2) * 1000)
local f1 = view().tier -- les jauges arrivent chaque seconde par wakfu:demon
check(f1 == f0 - 1, "apres " .. cfg.souls.hungerSeconds .. " s sans repas : palier " .. f0 .. " -> " .. f1)
check(lastNotice(d1):find("faim", 1, true) or count("wakfu:notice", d1) > 0, "message de faim")
check(d1.character.maxHp < maxBefore + 300 + 1, "les PV max suivent le palier")
say("faim : sans repas pendant " .. cfg.souls.hungerSeconds .. " s, palier " .. f0 .. " -> " .. f1 .. " et PV max en baisse")

-- 10. Mort et reapparition : l'etat du demon reste
local soulsBefore = view().souls
handlers.Death(d1.character); fire(Config.RespawnDelay * 1000)
check(stateOf(d1).demon and stateOf(d1).demon.souls == soulsBefore and stateOf(d1).camp == "demon", "la mort ne retire ni camp ni ames")

-- 11. Remise a zero du camp (support, boutique) : l'ecran de choix revient
local opens = count("wakfu:openCamp", d1)
subs["Wakfu:ResetCamp"](d1)
check(count("wakfu:openCamp", d1) == opens + 1 and stateOf(d1).camp == nil and stateOf(d1).demon == nil and stateOf(d1).class == "Eau", "reset : camp efface, jauges retirees, ecran de choix rouvert")
remote["wakfu:chooseCamp"](d1, "slayer")
check(stateOf(d1).camp == "slayer" and d1.character.held and d1.character.held.mesh == "aksel-animations::Katana_sword", "apres reset, on peut choisir l'autre camp (et la lame revient)")
place(d1, 700, 500); local startsBefore = count("wakfu:devourStart", d1); remote["wakfu:devour"](d1)
check(count("wakfu:devourStart", d1) == startsBefore, "un ancien demon devenu pourfendeur ne dévore plus, meme a cote d'un civil")
subs["Wakfu:ResetCamp"](newPlayer("Nouveau")); subs["Wakfu:ResetCamp"](d1)
say("reset du camp : l'ecran revient, on peut changer de camp, l'ancien etat de demon disparait")

-- 12. Joueur qui part pendant un repas : rien ne plante
local quitter = newPlayer("Fugitif"); remote["wakfu:chooseCamp"](quitter, "demon")
place(quitter, -700, -400); remote["wakfu:devour"](quitter); advance(500)
players[quitter:GetID()] = nil; quitter.valid = false
handlers.PlayerDestroy(quitter)
advance(5000)
say("depart en plein repas : minuteur arrete, aucune erreur")

-- 13. Cadavres : le corps d'un joueur mort reste au sol, il revient au Domaine dans un corps neuf
local function viewOf(player) return last("wakfu:demon", player)[1] end
local function makeCorpse(name, x, y, killer)
	local victim = newPlayer(name)
	remote["wakfu:chooseCamp"](victim, "slayer")
	local body = victim.character
	place(victim, x, y)
	local weapon = body.held
	body.hp = 0
	handlers.Death(body, nil, nil, nil, nil, killer)
	fire(Config.RespawnDelay * 1000)
	return victim, body, weapon
end
local victim1, body1, weapon1 = makeCorpse("Victime", 3000, 3000, nil)
check(victim1.character ~= body1 and victim1.character:IsValid() and victim1.character.hp > 0, "la victime revient dans un corps neuf")
check(body1:IsValid() and body1:IsDead() and body1.values.corpse == true, "l'ancien corps reste au sol, mort, marque comme cadavre")
check(weapon1 ~= nil and not weapon1:IsValid(), "l'arme du mort disparait avec lui")
check(stateOf(victim1).camp == "slayer" and stateOf(victim1).class == "Eau" and victim1.character.held and victim1.character.held:IsValid(), "la victime garde son camp, sa voie et retrouve sa lame")
local demonVictim = newPlayer("Demon mort"); remote["wakfu:chooseCamp"](demonVictim, "demon")
local demonBody = demonVictim.character; demonBody.hp = 0
handlers.Death(demonBody, nil, nil, nil, nil, nil); fire(Config.RespawnDelay * 1000)
check(demonVictim.character == demonBody and demonBody.hp > 0 and demonBody.values.corpse == nil, "un demon mort part en cendres : pas de cadavre, il reapparait dans le meme corps")
local expiring, expiringBody = makeCorpse("Oublie", 3000, -2000, nil)
check(expiringBody:IsValid(), "le corps est la")
fire(Config.Corpses.lifetime * 1000)
check(not expiringBody:IsValid() and not body1:IsValid(), "apres " .. Config.Corpses.lifetime .. " s, les corps disparaissent")
say("cadavres : le corps reste au sol (mort, sans arme), la victime revient dans un corps neuf avec sa lame, un demon mort part en cendres, les corps disparaissent apres " .. Config.Corpses.lifetime .. " s")

-- 14. Dévorer un cadavre : accroupi, gain, le corps disparait
local _, corpseBody = makeCorpse("Victime", 3000, 3000, nil)
local feeder = newPlayer("Charognard"); remote["wakfu:chooseCamp"](feeder, "demon")
place(feeder, 3050, 3000)
remote["wakfu:devour"](feeder)
local startArgs2 = last("wakfu:devourStart", feeder)
check(startArgs2 and startArgs2[1] == "Cadavre de Victime" and startArgs2[3].flesh == 50 and startArgs2[3].souls == 6 and startArgs2[3].heal == 20 and startArgs2[3].xp == 20, "le geste commence sur le cadavre, avec son gain : " .. tostring(startArgs2 and startArgs2[1]))
check(feeder.character.stance == "Crouching", "le demon s'accroupit pour manger")
remote["wakfu:devour"](feeder); check(count("wakfu:devourStart", feeder) == 1, "un seul geste a la fois")
advance(cfg.devour.seconds * 1000 + 250)
local fs = stateOf(feeder)
check(feeder.character.stance == "Standing", "il se releve a la fin du repas")
check(not corpseBody:IsValid(), "le cadavre est devore : il disparait")
check(fs.demon.souls == 6 and fs.demon.flesh == 50 and fs.demon.meals == 1 and fs.xp == 20, "gain du cadavre : ames +6, chair +50, XP +20, 1 repas : " .. fs.demon.souls .. "/" .. fs.demon.flesh .. "/" .. fs.demon.meals .. "/" .. fs.xp)
check(lastNotice(feeder) == "Cadavre de Victime dévoré : chair +50, âmes +6", "message du repas : " .. tostring(lastNotice(feeder)))
remote["wakfu:devour"](feeder); check(count("wakfu:devourStart", feeder) == 1 and lastNotice(feeder) == "Aucune proie à portée", "le cadavre devore ne se mange pas deux fois")
-- animation de repas facultative
cfg.devour.animation = "pack::A_Repas"
local _, animBody = makeCorpse("Victime", 3000, 3000, nil)
remote["wakfu:devour"](feeder)
check(feeder.character.anim == "pack::A_Repas", "l'animation de repas configuree se joue")
advance(cfg.devour.seconds * 1000 + 250)
check(feeder.character.anim == false and not animBody:IsValid(), "l'animation s'arrete a la fin (anim=" .. tostring(feeder.character.anim) .. ", corps valide=" .. tostring(animBody:IsValid()) .. ", notice=" .. tostring(lastNotice(feeder)) .. ")")
cfg.devour.animation = nil
-- un cadavre qui disparait pendant le repas l'interrompt
local _, vanishing = makeCorpse("Victime", 3000, 3000, nil)
local stops = count("wakfu:devourStop", feeder)
remote["wakfu:devour"](feeder); advance(500)
fire(Config.Corpses.lifetime * 1000); advance(500)
check(count("wakfu:devourStop", feeder) == stops + 1 and lastNotice(feeder):find("disparu", 1, true) and feeder.character.stance == "Standing", "un cadavre qui disparait interrompt le repas : " .. tostring(lastNotice(feeder)))
-- un pourfendeur ne mange pas de cadavre
local slayerNear = newPlayer("Pourfendeur"); remote["wakfu:chooseCamp"](slayerNear, "slayer")
local _, slayerCorpse = makeCorpse("Victime", 3000, 3000, nil)
place(slayerNear, 3050, 3000); remote["wakfu:devour"](slayerNear)
check(count("wakfu:devourStart", slayerNear) == 0 and slayerCorpse:IsValid(), "un pourfendeur ne dévore pas")
-- un joueur peut-il etre dévoré vivant ? non : seuls les corps morts sont des proies
check(victim1.character:IsValid() and victim1.character.hp > 0, "un joueur vivant n'est jamais une proie")
place(feeder, 3050, 3000)
local before = count("wakfu:devourStart", feeder); remote["wakfu:devour"](feeder)
check(count("wakfu:devourStart", feeder) == before + 1 and last("wakfu:devourStart", feeder)[1] == "Cadavre de Victime", "le cadavre du pourfendeur est une proie pour le demon")
interruptCheck = nil
advance(cfg.devour.seconds * 1000 + 250)
say("dévorer un cadavre : accroupi pendant le geste, +50 chair +6 ames +20 XP, le corps disparait, animation facultative, interrompu si le corps disparait, jamais un joueur vivant, rien pour un pourfendeur")

-- 15. Limite de repas : 5 par jour au grade 1, 10 au grade 2
cfg.meals.perRank = savedPerRank
local g = newPlayer("Gourmand"); remote["wakfu:chooseCamp"](g, "demon")
place(g, 4000, 0)
local function eatOne()
	local _, body = makeCorpse("Victime", 4000, 0, nil)
	local starts = count("wakfu:devourStart", g)
	remote["wakfu:devour"](g)
	local started = count("wakfu:devourStart", g) == starts + 1
	advance(cfg.devour.seconds * 1000 + 250)
	return started, body
end
for i = 1, 5 do
	local started = eatOne()
	check(started and stateOf(g).demon.meals == i, "repas " .. i .. "/5 au grade 1")
end
check(viewOf(g).meals == 5 and viewOf(g).mealsCap == 5 and stateOf(g).rank.index == 1, "5 repas dont la limite est 5, grade 1")
local startedSixth, sixthBody = eatOne()
check(not startedSixth and lastNotice(g):find("Limite de repas du jour atteinte (5/5)", 1, true) and sixthBody:IsValid(), "6e repas refuse : " .. tostring(lastNotice(g)))
place(g, 700, 500); remote["wakfu:devour"](g)
check(lastNotice(g):find("Limite de repas du jour atteinte", 1, true) and count("wakfu:devourStart", g) == 5, "un civil compte aussi dans la limite")
place(g, 4000, 0)
for i = 1, 4 do -- quatre duels gagnes : 160 XP, grade 2
	local victimKill = newPlayer("Duel" .. i); remote["wakfu:chooseCamp"](victimKill, "slayer")
	victimKill.character.hp = 0; handlers.Death(victimKill.character, nil, nil, nil, nil, g)
end
check(stateOf(g).rank.index == 2 and viewOf(g).mealsCap == 10 or (last("wakfu:state", g)[1].demon.mealsCap == 10), "apres 4 duels gagnes : grade 2, limite de 10")
local startedSeventh = eatOne()
check(startedSeventh and stateOf(g).demon.meals == 6, "au grade 2, un 6e repas est permis : meals " .. stateOf(g).demon.meals)
cfg.meals.dayLength = 60
advance(61000)
check(viewOf(g).meals == 0, "un nouveau jour remet le compteur a zero : " .. viewOf(g).meals)
cfg.meals.dayLength = savedDayLength
local reborn = eatOne(); check(reborn and stateOf(g).demon.meals == 1, "on peut de nouveau manger")
say("limite de repas : 5 au grade 1 (6e refuse, civil aussi), 10 au grade 2 apres 160 XP, un nouveau jour remet a zero")
return out
'''

CLIENT = r'''
local ROOT = ...
local Any = {}
setmetatable(Any, { __index = function() return Any end, __call = function() return Any end, __add = function() return Any end, __sub = function() return Any end,
	__mul = function() return Any end, __div = function() return Any end, __lt = function() return false end, __le = function() return false end, __concat = function() return "" end })
local env = {}
setmetatable(env, { __index = function(_, k) local v = _G[k]; if v == nil then return Any end; return v end })
local hudEvents, uiHandlers, remoteCalls, remoteHandlers, keyHandlers = {}, {}, {}, {}, {}
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
env.Particle = function() return Any end
env.Console = { Warn = function() end, Log = function() end }
local cache = {}
env.Package = { Subscribe = function() end, Require = function(name)
	if name == "VfxAssets.lua" then return { vefects = { "NS_Trail_Water" } } end
	if cache[name] == nil then local f, err
		for _, dir in ipairs({ "Client", "Shared" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
		assert(f, tostring(err)); cache[name] = f() end
	return cache[name] end }

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

-- Donnees envoyees au HUD
local init = last("wakfu:init")
check(init.camps and init.camps.slayer.name == "Pourfendeur" and init.camps.demon.name == "Démon" and init.camps.demon.kanji == "鬼", "le HUD recoit les deux camps")
check(init.campOrder[1] == "slayer" and init.campOrder[2] == "demon" and init.demonKey == "H", "ordre des camps et touche de dévoration")
check(init.classes.Demon.camp == "demon" and init.classes.Eau.camp == "slayer", "les classes portent leur camp")
say("donnees : 2 camps (Pourfendeur, Demon), touche de dévoration " .. init.demonKey .. ", classes marquees par camp")

-- Ecran de choix : obligatoire, il bloque tout
remoteHandlers["wakfu:openCamp"]()
check(last("wakfu:campOpen") == true and state.input == false and state.mouse == true and ui.focus == true and ui.visibility == 1, "l'ecran s'ouvre : souris et focus sur le HUD, jeu bloque")
local opens = count("wakfu:campOpen"); remoteHandlers["wakfu:openCamp"](); check(count("wakfu:campOpen") == opens, "pas de seconde ouverture")
for _, key in ipairs({ "Escape", "E", "H", "C", "I", "J", "F10", "One", "F1", "Left", "F9" }) do check(press(key) == true, "touche " .. key .. " bloquee pendant le choix") end
check(calls("wakfu:interact") == 0 and calls("wakfu:devour") == 0 and calls("wakfu:castIndex") == 0 and calls("wakfu:chooseClass") == 0 and calls("wakfu:weaponCycle") == 0, "aucune touche ne part au serveur")
check(count("wakfu:inventoryOpen") == 0 and count("wakfu:creatorOpen") == 0 and count("wakfu:trailOpen") == 0 and count("wakfu:menuOpen") == 0, "aucun autre ecran ne s'ouvre")
remoteHandlers["wakfu:openClassReroll"](); remoteHandlers["wakfu:openForge"](); remoteHandlers["wakfu:openCreator"]()
check(count("wakfu:rerollOpen") == 0 and count("wakfu:forgeOpen") == 0 and count("wakfu:creatorOpen") == 0, "le serveur ne peut ouvrir ni la forge, ni le changement de voie, ni le createur par-dessus le choix du camp")
say("ecran de camp : ouvert, clavier entierement bloque (Echap, E, H, C, I, J, F-touches...), pas de double ouverture")

-- Choix : part au serveur, l'ecran reste jusqu'a la reponse
uiHandlers["wakfu:chooseCamp"]("demon")
local choose = lastCall("wakfu:chooseCamp")
check(choose and choose.args[1] == 1 and choose.args[2] == "demon", "le choix part au serveur en fiable")
check(last("wakfu:campOpen") == true and state.input == false, "l'ecran reste ouvert tant que le serveur n'a pas repondu")
remoteHandlers["wakfu:state"]({ class = "Eau", kamas = 1 }); check(last("wakfu:campOpen") == true, "un etat sans camp ne ferme pas l'ecran")
remoteHandlers["wakfu:state"]({ camp = "demon", class = "Demon", demon = { blood = 100 } })
check(last("wakfu:campOpen") == false and state.input == true and state.mouse == false and ui.focus == false, "l'etat avec camp ferme l'ecran et rend le jeu")
check(last("wakfu:state").camp == "demon", "l'etat est transmis au HUD")
say("choix : le camp part au serveur, l'ecran se ferme seulement quand l'etat revient avec un camp")

-- Apres le choix : H dévore, le reste marche
state.now = state.now + 1
local devours = calls("wakfu:devour")
press("H"); check(calls("wakfu:devour") == devours + 1 and lastCall("wakfu:devour").args[1] == 1, "H demande a dévorer, en fiable")
press("E"); check(calls("wakfu:interact") == 1, "E interagit de nouveau")
press("One"); check(calls("wakfu:castIndex") == 1, "1 lance une technique")
say("apres le choix : H dévore, E et 1 fonctionnent de nouveau")

-- Evenements du demon vers le HUD
remoteHandlers["wakfu:demon"]({ blood = 55, bloodMax = 100, tier = 2 })
check(last("wakfu:demon").blood == 55 and last("wakfu:demon").tier == 2, "les jauges arrivent au HUD")
remoteHandlers["wakfu:devourStart"]("Villageois", 3.5, { flesh = 40, souls = 4, heal = 15, xp = 15 })
check(last("wakfu:devourStart").name == "Villageois" and last("wakfu:devourStart").seconds == 3.5 and last("wakfu:devourStart").gain.flesh == 40 and last("wakfu:devourStart").gain.xp == 15, "debut du geste vers le HUD, avec le gain attendu")
remoteHandlers["wakfu:devourStop"](); check(count("wakfu:devourStop") == 1, "fin du geste vers le HUD")
say("evenements : jauges, debut et fin du geste de dévoration transmis au HUD")

-- Reset du camp : l'ecran revient
state.now = state.now + 1
remoteHandlers["wakfu:openCamp"](); check(last("wakfu:campOpen") == true and state.input == false, "le reset rouvre l'ecran")
remoteHandlers["wakfu:state"]({ camp = "slayer", class = "Eau" })
check(last("wakfu:campOpen") == false and state.input == true, "le nouveau choix le referme")
say("reset : l'ecran de choix revient puis se referme apres un nouveau choix")
return out
'''

failed = False
for label, root in RP.items():
    print("== wakfu-rp", label)
    for name, code in (("donnees", DATA), ("serveur", SERVER), ("client", CLIENT)):
        try:
            lines = LuaRuntime().eval("function(...) " + code + " end")(root)
            for i in range(1, len(lines) + 1):
                print("  [%s] %s" % (name, str(lines[i]).encode("ascii", "replace").decode()))
        except Exception as error:  # noqa: BLE001
            failed = True
            print("  [%s] %s" % (name, str(error).encode("ascii", "replace").decode()))
sys.exit(1 if failed else 0)
