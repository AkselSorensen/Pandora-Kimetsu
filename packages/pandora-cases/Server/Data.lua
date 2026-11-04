-- Saved data: settings, rarities, catalog (items, cases, keys), players, market and stats.
-- Everything lives in PandoraCases/data.json next to the server executable, so updating the package keeps it.
local FILE = "PandoraCases/data.json"

local function copy(t) local r = {} for k, v in pairs(t) do r[k] = type(v) == "table" and copy(v) or v end return r end

-- Example catalog of the first start (base nanos-world assets). Edit it in game.
local function seed()
    return {
        next = 100, admins = {}, players = {}, market = {}, sales = {}, featured = {},
        items = {
            i1 = { name = "100 Credits", rarity = "Common", kind = "credits", amount = 100, sell = 0 },
            i2 = { name = "250 Credits", rarity = "Uncommon", kind = "credits", amount = 250, sell = 0 },
            i3 = { name = "Classic Male", rarity = "Common", kind = "model", asset = "nanos-world::SK_ClassicMale", sell = 40 },
            i4 = { name = "AK-47", rarity = "Rare", kind = "weapon", asset = "nanos-world::SK_AK47", sell = 200 },
            i5 = { name = "AWP", rarity = "Uncommon", kind = "weapon", asset = "nanos-world::SK_AWP", sell = 120 },
            i6 = { name = "Mannequin", rarity = "Epic", kind = "model", asset = "nanos-world::SK_Mannequin", sell = 600 },
            i7 = { name = "Post Apocalyptic", rarity = "Legendary", kind = "model", asset = "nanos-world::SK_PostApocalyptic", sell = 1500 },
            i8 = { name = "1000 Credits", rarity = "Legendary", kind = "credits", amount = 1000, sell = 0 },
            i9 = { name = "AK-47 [PERMA]", rarity = "Epic", kind = "weapon", asset = "nanos-world::SK_AK47", perma = true, shop = true, price = 5000, sell = 1000 },
        },
        keys = {
            k1 = { name = "Gold Key", price = 150, color = "#e0a030", shop = true },
        },
        cases = {
            c1 = { name = "Starter Case", price = 100, rarity = "Common", shop = true, items = {
                { item = "i1", weight = 50 }, { item = "i3", weight = 30 }, { item = "i5", weight = 14 },
                { item = "i4", weight = 5 }, { item = "i6", weight = 1 } } },
            c2 = { name = "Gold Case", price = 250, rarity = "Rare", key = "k1", shop = true, items = {
                { item = "i2", weight = 40 }, { item = "i5", weight = 30 }, { item = "i4", weight = 18 },
                { item = "i6", weight = 8 }, { item = "i7", weight = 3, mystery = true }, { item = "i8", weight = 1 } } },
            c3 = { name = "Daily Case", price = 0, rarity = "Common", shop = true, cooldown = 86400, items = {
                { item = "i1", weight = 70 }, { item = "i2", weight = 25 }, { item = "i8", weight = 1 } } },
        },
    }
end

function Cases.Load()
    local data
    if File.Exists(FILE) then
        local ok, parsed = pcall(function() return JSON.parse(File(FILE):Read()) end)
        if ok and type(parsed) == "table" then data = parsed end
    end
    data = data or seed()
    for _, k in ipairs({ "admins", "players", "market", "items", "keys", "cases", "sales", "featured" }) do data[k] = data[k] or {} end
    data.next = data.next or 100
    if type(data.rarities) ~= "table" or #data.rarities == 0 then data.rarities = copy(CasesRarities) end
    data.settings = data.settings or {}
    for k, v in pairs(CasesConfig.Defaults) do if data.settings[k] == nil then data.settings[k] = v end end
    Cases.Data = data
end

function Cases.Setting(name) return Cases.Data.settings[name] end

function Cases.Rarity(name)
    for i, r in ipairs(Cases.Data.rarities) do if r.name == name then return r, i end end
end

local dirty = false
function Cases.SaveNow()
    dirty = false
    local ok, err = pcall(function()
        local file = File(FILE, true)
        file:Write(JSON.stringify(Cases.Data))
        file:Close()
    end)
    if not ok then Console.Warn("[pandora-cases] could not save " .. FILE .. ": " .. tostring(err)) end
end

-- Saves a moment later, so many changes in a row write the file once.
function Cases.Save()
    if dirty then return end
    dirty = true
    Timer.SetTimeout(Cases.SaveNow, 2000)
end

Package.Subscribe("Unload", function() if dirty then Cases.SaveNow() end end)

function Cases.NewId(prefix)
    Cases.Data.next = Cases.Data.next + 1
    return prefix .. Cases.Data.next
end

-- Player record, created with the starting credits the first time.
function Cases.PlayerData(id, name)
    local p = Cases.Data.players[id]
    if not p then
        p = { credits = Cases.Setting("StartCredits"), inv = {}, name = name }
        Cases.Data.players[id] = p
        Cases.Save()
    end
    if name then p.name = name end
    p.inv = p.inv or {}
    p.perma = p.perma or {}
    p.bought = p.bought or {}
    p.pending = p.pending or {}
    return p
end

-- Inventory entries: { u = unique id, t = "case" | "key" | "item", r = catalog id }
function Cases.Give(id, kind, ref)
    local p = Cases.PlayerData(id)
    local entry = { u = Cases.NewId("u"), t = kind, r = ref }
    table.insert(p.inv, entry)
    Cases.Save()
    return entry
end

function Cases.FindEntry(p, uid)
    for i, e in ipairs(p.inv) do if e.u == uid then return e, i end end
end

function Cases.TakeEntry(p, uid)
    local e, i = Cases.FindEntry(p, uid)
    if e then table.remove(p.inv, i) Cases.Save() end
    return e
end

function Cases.CatalogOf(kind)
    return (kind == "case" and Cases.Data.cases) or (kind == "key" and Cases.Data.keys) or Cases.Data.items
end

-- Model equipped / perma items only count while the player still owns them.
function Cases.Owns(p, kind, ref)
    for _, e in ipairs(p.inv) do if e.t == kind and e.r == ref then return true end end
    return false
end

function Cases.CleanOwnership(p)
    if p.equipped and not Cases.Owns(p, "item", p.equipped) then p.equipped = nil end
    for id in pairs(p.perma) do if not Cases.Owns(p, "item", id) then p.perma[id] = nil end end
end

Cases.Load()
