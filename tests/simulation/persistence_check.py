"""Test de la sauvegarde : le serveur kimetsu-pandora parle à un faux serveur d'API (même logique que server/api).

Vérifie : premier choix de camp -> création en base, sauvegarde après changement (job, PV, nom, sac, apparence),
déconnexion puis reconnexion -> état restauré, et aucune écriture tant que l'API ne répond pas.

    python tests/simulation/persistence_check.py
"""
import sys
from pathlib import Path

from lupa import LuaRuntime

REPO_RP = (Path(__file__).resolve().parents[2] / "packages" / "kimetsu-pandora").as_posix()

LUA = r'''
local ROOT = ...
local Any = {}
setmetatable(Any, { __index = function() return Any end, __call = function() return Any end, __add = function() return Any end, __sub = function() return Any end,
	__mul = function() return Any end, __div = function() return Any end, __lt = function() return false end, __le = function() return false end, __concat = function() return "" end })

local log = {}
local function note(text) log[#log + 1] = text end

-- ── faux serveur d'API (en mémoire, même contrat que server/api/app.py) ──────────────────────────
local db = { players = {}, characters = {}, inventories = {}, appearance = {}, nextId = 0, down = false }
local function newId(prefix) db.nextId = db.nextId + 1; return prefix .. db.nextId end
local requests = {}
local registry, regN = {}, 0
local function fakeJsonStringify(t) regN = regN + 1; registry[regN] = t; return "#" .. regN end
local function fakeJsonParse(s) if type(s) == "string" and s:sub(1, 1) == "#" then return registry[tonumber(s:sub(2))] end return nil end

local function api(method, path, body)
	requests[#requests + 1] = method .. " " .. path
	if db.down then return 0, nil end
	local b = body and body ~= "" and fakeJsonParse(body) or nil
	local steam, rest = path:match("^/players/([^/]+)(.*)$")
	if path:match("^/players/[^/]+/login$") then
		local p = db.players[steam] or { player_id = newId("p") }
		db.players[steam] = p
		db.inventories[p.player_id] = db.inventories[p.player_id] or { inventory_id = newId("i") }
		return 200, fakeJsonStringify({ player_id = p.player_id })
	end
	if steam and rest == "" and method == "GET" then
		local p = db.players[steam]
		if not p then return 404, nil end
		local list = {}
		for _, c in pairs(db.characters) do if c.player_id == p.player_id then list[#list + 1] = c end end
		table.sort(list, function(a, b) return a.character_id < b.character_id end)
		local out = {}
		for _, c in ipairs(list) do
			local copy = {}
			for k, v in pairs(c) do copy[k] = v end
			copy.appearance = db.appearance[c.character_id]
			out[#out + 1] = copy
		end
		return 200, fakeJsonStringify({ player = { player_id = p.player_id }, characters = out })
	end
	if steam and rest == "/inventory" then
		local p = db.players[steam]
		if not p then return 404, nil end
		if method == "GET" then
			local inv = db.inventories[p.player_id]
			return 200, fakeJsonStringify({ items = inv and inv.items or {} })
		end
		local inv = db.inventories[p.player_id]
		inv.items = {}
		for _, row in ipairs(b.items or {}) do
			inv.items[#inv.items + 1] = { code = row.code, count = row.count, slot = row.slot, equip_slot = row.equip_slot }
		end
		return 200, fakeJsonStringify({ saved = #inv.items })
	end
	if steam and rest == "/characters" and method == "POST" then
		local p = db.players[steam]
		if not p then return 404, nil end
		local id = newId("c")
		db.characters[id] = { character_id = id, player_id = p.player_id, name = b.name, faction_id = b.faction_id, job = b.job,
			hp = b.hp, max_hp = b.max_hp, level = 1, xp = 0, is_active = true }
		return 200, fakeJsonStringify({ character_id = id })
	end
	local cid, action = path:match("^/characters/([^/]+)/(%a+)$")
	if cid and action == "state" and method == "PUT" then
		local c = db.characters[cid]
		if not c then return 404, nil end
		for k, v in pairs(b) do if v ~= nil then c[k] = v end end
		return 200, fakeJsonStringify({ saved = true })
	end
	if cid and action == "appearance" and method == "PUT" then
		if not db.characters[cid] then return 404, nil end
		db.appearance[cid] = b.appearance
		return 200, fakeJsonStringify({ saved = true })
	end
	return 404, nil
end

local env = {}
env.HTTP = { RequestAsync = function(host, path, method, body, ctype, flag, headers, callback)
	local status, data = api(method, path, body)
	callback(status, data)
end }
env.JSON = { stringify = fakeJsonStringify, parse = fakeJsonParse }
env.KimetsuApi = { ApiUrl = "http://127.0.0.1:8080", ServerKey = "test" }
env.Console = { Warn = function(text) note("WARN " .. text) end, Log = function() end }

-- ── minuteurs et événements ────────────────────────────────────────────────────────────────────
local timers, intervals, handlers, remotes = {}, {}, {}, {}
env.Timer = {
	SetTimeout = function(fn) timers[#timers + 1] = fn end,
	SetInterval = function(fn) intervals[#intervals + 1] = fn end,
	ClearInterval = function() end,
}
local function flush()
	local n = 0
	while #timers > 0 do
		local fn = table.remove(timers, 1)
		fn()
		n = n + 1
	end
	return n
end
env.Events = { Subscribe = function(name, fn) handlers[name] = fn end, SubscribeRemote = function(name, fn) remotes[name] = fn end,
	CallRemote = function() end }
env.Player = { Subscribe = function(name, fn) handlers[name] = fn end, GetAll = function() return {} end, GetPairs = function() return {} end }
env.Character = setmetatable({ Subscribe = function() end }, { __call = function() return Any end, __index = function() return Any end })
env.Package = { Subscribe = function(name, fn) handlers["pkg:" .. name] = fn end }

-- joueurs et personnages factices
local characters, hpOf, maxOf = {}, {}, {}
local function makeCharacter(id)
	local c = { IsValid = function() return true end, IsDead = function() return false end }
	c.GetHealth = function() return hpOf[id] or 0 end
	c.GetMaxHealth = function() return maxOf[id] or 0 end
	c.SetHealth = function(_, v) hpOf[id] = v end
	c.SetMaxHealth = function(_, v) maxOf[id] = v end
	return setmetatable(c, { __index = Any })
end
local function makePlayer(id, steam, name)
	local p = { GetID = function() return id end, GetSteamID = function() return steam end, GetName = function() return name end,
		IsValid = function() return true end, GetControlledCharacter = function() return characters[id] end }
	return setmetatable(p, { __index = Any })
end

env.Package.Require = function(name)
	if name == "ServerConfig.lua" then return true end
	if name == "VfxAssets.lua" then return { vefects = {} } end
	if env.__cache[name] == nil then
		local f, err
		for _, dir in ipairs({ "Shared", "Server", "Client" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
		assert(f, tostring(err))
		env.__cache[name] = f()
	end
	return env.__cache[name]
end
env.__cache = {}
setmetatable(env, { __index = function(_, k) local v = _G[k]; if v == nil then return Any end; return v end })
env.Package.Subscribe = function(name, fn) handlers["pkg:" .. name] = fn end

local Index = loadfile(ROOT .. "/Server/Index.lua", "t", env)
assert(Index, "Index.lua ne se charge pas")
Index()

local function check(ok, message) if not ok then error("ECHEC : " .. message, 0) end end
local out = {}
local function say(text) out[#out + 1] = text end

local STEAM = "76561198000000001"
local classes = env.Package.Require("Classes.lua")
local items = env.Package.Require("Items.lua")

-- 1. première connexion : pas de personnage, l'état est chargé, rien n'est encore écrit au choix du camp
local p1 = makePlayer(1, STEAM, "Azrael")
characters[1] = makeCharacter(1)
hpOf[1], maxOf[1] = 1200, 1200
handlers["Spawn"](p1)
flush()
check(db.players[STEAM] ~= nil, "le joueur doit être créé à la connexion")
check(next(db.characters) == nil, "aucun personnage avant le choix du camp")

-- 2. choix du camp : création du personnage en base
remotes["wakfu:chooseCamp"](p1, "slayer")
flush()
local _, character = next(db.characters)
check(character ~= nil, "le personnage doit être créé au choix du camp")
check(character.faction_id == 1, "pourfendeurs = faction 1, reçu " .. tostring(character.faction_id))
say("création au choix du camp : OK (faction " .. character.faction_id .. ")")

-- 3. créateur, PV et inventaire : tout doit partir en base après le délai
remotes["wakfu:create"](p1, "Eau", env.Package.Require("Config.lua").Genders[1], 1, "Nezuko", nil)
hpOf[1] = 730
handlers["Destroy"] = handlers["Destroy"]
flush()
check(character.name == "Nezuko", "le nom du créateur doit être sauvegardé, reçu " .. tostring(character.name))
check(character.job == "Eau", "le job doit être sauvegardé")
check(character.hp == 730, "les PV doivent être sauvegardés, reçu " .. tostring(character.hp))
check(character.max_hp == 1200, "les PV max doivent être sauvegardés")
local inv = db.inventories[db.players[STEAM].player_id]
check(inv.items and #inv.items > 0, "l'inventaire doit être sauvegardé")
say("sauvegarde : nom " .. character.name .. ", job " .. character.job .. ", PV " .. character.hp .. "/" .. character.max_hp .. ", " .. #inv.items .. " lignes d'inventaire")

-- 4. déconnexion : dernière sauvegarde, puis reconnexion avec un état neuf
hpOf[1] = 500
handlers["Destroy"](p1)
check(character.hp == 500, "la déconnexion doit sauvegarder les PV, reçu " .. tostring(character.hp))
local p2 = makePlayer(2, STEAM, "Azrael")
characters[2] = makeCharacter(2)
hpOf[2], maxOf[2] = 1, 1
handlers["Spawn"](p2)
flush()
local state2 = nil
-- l'état est dans le module serveur : on vérifie par ce que le serveur envoie à la place de l'état par défaut
check(hpOf[2] == 500, "les PV doivent être restaurés à la reconnexion, reçu " .. tostring(hpOf[2]))
check(maxOf[2] == 1200, "les PV max doivent être restaurés")
check(next(db.characters, nil) ~= nil and (function() local n = 0 for _ in pairs(db.characters) do n = n + 1 end return n == 1 end)(), "reconnexion : pas de nouveau personnage")
remotes["wakfu:chooseCamp"](p2, "demon")
flush()
local n2 = 0
for _ in pairs(db.characters) do n2 = n2 + 1 end
check(n2 == 1, "le camp restauré ne doit pas pouvoir être rechoisi")
check(character.name == "Nezuko" and character.job == "Eau", "le nom et le job doivent survivre à la reconnexion")
say("reconnexion : PV restaurés " .. hpOf[2] .. "/" .. maxOf[2])

-- 5. API hors ligne : aucune écriture ne doit partir
local before = #requests
db.down = true
local p3 = makePlayer(3, "76561198000000099", "Nouveau")
characters[3] = makeCharacter(3)
handlers["Spawn"](p3)
flush()
remotes["wakfu:chooseCamp"](p3, "demon")
flush()
handlers["Destroy"](p3)
flush()
local writes = 0
for i = before + 1, #requests do
	if requests[i]:match("^PUT") or requests[i]:match("^POST /players/76561198000000099/characters") then writes = writes + 1 end
end
check(writes == 0, "API hors ligne : aucune écriture attendue, reçu " .. writes)
say("API hors ligne : aucune écriture")

local warns = 0
for _, line in ipairs(log) do if line:match("^WARN") then warns = warns + 1 end end
say("avertissements de l'API hors ligne : " .. warns)
return table.concat(out, "\n")
'''


def main() -> int:
    lua = LuaRuntime(unpack_returned_tuples=True)
    run = lua.eval("function(root) " + LUA.replace("local ROOT = ...", "local ROOT = root") + " end")
    try:
        print(run(REPO_RP))
    except Exception as err:  # noqa: BLE001
        print(f"ECHEC : {err}")
        return 1
    print("persistance : OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
