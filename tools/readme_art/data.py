"""Les données réelles du jeu, lues dans le Lua de packages/kimetsu-pandora/Shared et dans scripts/issues.json : les graphiques ne mentent pas."""
import json
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "packages" / "kimetsu-pandora" / "Shared"
_lua = LuaRuntime(unpack_returned_tuples=True)
_type = _lua.eval("function(x) return type(x) end")


def to_py(value):
    if _type(value) != "table":
        return value
    keys = list(value.keys())
    if keys and sorted(keys) == list(range(1, len(keys) + 1)):  # séquence 1..n : une liste ; sinon un dictionnaire (par exemple unlock = { [4] = 4 })
        return [to_py(value[k]) for k in sorted(keys)]
    return {str(k): to_py(value[k]) for k in keys}


_PRELUDE = """
local Any = {}
setmetatable(Any, { __index = function() return Any end, __call = function() return Any end })
local ROOT = ...
local env = setmetatable({}, { __index = function(_, k) local v = _G[k]; if v == nil then return Any end; return v end })
local cache = {}
env.Package = setmetatable({ Require = function(name)
	if cache[name] == nil then
		local f = loadfile(ROOT .. "/Shared/" .. name, "t", env)
		local ok, value = false, nil
		if f then ok, value = pcall(f) end
		cache[name] = (ok and value ~= nil) and value or Any
	end
	return cache[name]
end }, { __index = function() return Any end })
return function(file)
	local f = assert(loadfile(ROOT .. "/Shared/" .. file, "t", env))
	return f()
end
"""
_runner = _lua.execute(_PRELUDE, SHARED.parent.as_posix())


def load(name):
    """Charge un fichier Shared/*.lua : les autres modules sont remplacés par un objet vide, sauf Classes et Ranks."""
    return to_py(_runner(name))


CLASSES = load("Classes.lua")["List"]
RANKS = load("Ranks.lua")["Ladders"]
DEMON = load("Config.lua")["Demon"]
WEAPONS = len(load("YufuWeapons.lua")["weapons"])
ISSUES = json.loads((ROOT / "scripts" / "issues.json").read_text(encoding="utf-8"))
ORDER = ["Eau", "Foudre", "Flamme", "Vent", "Brume", "Pierre", "Insecte", "Demon"]

if __name__ == "__main__":
    print(len(CLASSES), "classes ;", {k: len(v) for k, v in RANKS.items()}, "grades ;", DEMON["blood"], DEMON["tiers"][1]["name"].encode("ascii", "replace"))
    print(len(ISSUES["issues"]), "issues")
