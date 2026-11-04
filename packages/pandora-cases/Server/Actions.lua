-- Everything the menu can ask for. The client only sends ids; prices, odds and rewards are decided here.
local Config = CasesConfig
local notify = Cases.Notify
local last_action = {}

-- ── Data sent to the menu ─────────────────────────────────────────────────────────────────────
local function menuData(player)
    local id = Cases.IdOf(player)
    local me = Cases.PlayerData(id, player:GetName())
    Cases.CleanOwnership(me)
    local admin = Cases.IsAdmin(player)
    local market = {}
    for _, l in ipairs(Cases.Data.market) do
        market[#market + 1] = { n = l.n, seller = l.sellerName, mine = (l.seller == id), t = l.entry.t, r = l.entry.r, price = l.price, at = l.at }
    end
    local now, wait = os.time(), {}
    for cid, b in pairs(me.bought) do
        local c = Cases.Data.cases[cid]
        if c and (tonumber(c.cooldown) or 0) > 0 and b.at then
            local left = b.at + c.cooldown - now
            if left > 0 then wait[cid] = left end
        end
    end
    local players, others = {}, {}
    for _, p in ipairs(Cases.AllPlayers()) do
        if p ~= player then others[#others + 1] = { id = p:GetID(), name = p:GetName(), trading = Cases.InTrade(p) } end
        if admin then
            local d = Cases.PlayerData(Cases.IdOf(p), p:GetName())
            players[#players + 1] = { id = p:GetID(), name = p:GetName(), credits = d.credits, inv = d.inv }
        end
    end
    return Cases.Encode({
        currency = Config.Currency, crate = Config.CrateMesh, menuKey = Config.MenuKey, settings = Cases.Data.settings, rarities = Cases.Data.rarities,
        items = Cases.Data.items, cases = Cases.Data.cases, keys = Cases.Data.keys,
        me = { credits = me.credits, inv = me.inv, equipped = me.equipped, perma = me.perma, bought = me.bought, wait = wait, name = player:GetName() },
        market = market, featured = Cases.Data.featured,
        sales = Cases.Data.sales,
        admin = admin, players = players, others = others,
    })
end

function Cases.SendData(player)
    local p = Cases.PlayerData(Cases.IdOf(player), player:GetName())
    -- messages kept while the player was away (sales on the market)
    if #p.pending > 0 then
        for _, text in ipairs(p.pending) do notify(player, text, "ok") end
        p.pending = {}
        Cases.Save()
    end
    Events.CallRemote("Cases:Data", player, Reliability.Reliable, menuData(player))
end

-- ── Rewards ──────────────────────────────────────────────────────────────────────────────────
local function applyModel(player, asset)
    local c = player:GetControlledCharacter()
    if c and asset then pcall(function() c:SetMesh(asset) end) end
end

local function giveWeapon(player, asset)
    local c = player:GetControlledCharacter()
    if not c then return false end
    return (pcall(function()
        local w = Weapon(c:GetLocation() + Vector(0, 0, 50), Rotator(0, 0, 0), asset)
        c:PickUp(w)
    end))
end

-- An entry leaves the inventory: a trade offer keeps it locked.
local function take(player, p, uid)
    if Cases.Offered(player, uid) then notify(player, "This item is in your trade offer", "error") return nil end
    local e = Cases.TakeEntry(p, uid)
    if e then Cases.CleanOwnership(p) end
    return e
end

local function sold(kind, id, qty) local k = kind .. ":" .. id Cases.Data.sales[k] = (Cases.Data.sales[k] or 0) + (qty or 1) end

-- ── Player actions ───────────────────────────────────────────────────────────────────────────
local A = {}
for name, fn in pairs(Cases.TradeActions) do A[name] = fn end

-- buy { kind = "case" | "key" | "item", id, qty }
function A.buy(player, p, a)
    local id = tostring(a.id)
    local def = Cases.CatalogOf(a.kind)[id]
    local qty = math.floor(tonumber(a.qty) or 1)
    if not def or not def.shop or qty < 1 or qty > 10 then return end
    if a.kind == "item" and not tonumber(def.price) then return end
    if a.kind == "case" then
        local b = p.bought[id] or { n = 0 }
        local limit, cooldown = tonumber(def.limit) or 0, tonumber(def.cooldown) or 0
        if limit > 0 and b.n + qty > limit then return notify(player, "Purchase limit reached (" .. limit .. ")", "error") end
        if cooldown > 0 then
            if qty > 1 then qty = 1 end
            if b.at and os.time() - b.at < cooldown then return notify(player, "Not available yet", "error") end
        end
    end
    local cost = (tonumber(def.price) or 0) * qty
    if p.credits < cost then return notify(player, "Not enough " .. Config.Currency, "error") end
    p.credits = p.credits - cost
    for _ = 1, qty do Cases.Give(Cases.IdOf(player), a.kind, id) end
    if a.kind == "case" then
        local b = p.bought[id] or { n = 0 }
        p.bought[id] = { n = b.n + qty, at = os.time() }
    end
    sold(a.kind, id, qty)
    notify(player, "Bought " .. qty .. " × " .. def.name, "ok")
end

local function roll(case)
    local total = 0
    for _, e in ipairs(case.items) do if Cases.Data.items[e.item] then total = total + math.max(0, tonumber(e.weight) or 0) end end
    if total <= 0 then return nil end
    local x = math.random() * total
    for _, e in ipairs(case.items) do
        if Cases.Data.items[e.item] then
            x = x - math.max(0, tonumber(e.weight) or 0)
            if x <= 0 then return e.item end
        end
    end
    return case.items[#case.items].item
end

local function announces(rarity)
    local _, from = Cases.Rarity(Cases.Setting("AnnounceFrom") or "")
    local _, this = Cases.Rarity(rarity)
    return from ~= nil and this ~= nil and this >= from
end

-- open { uid, count } : opens 1, 3 or 5 cases of the same kind from the inventory (each uses a key when the case needs one)
function A.open(player, p, a)
    local entry = Cases.FindEntry(p, a.uid)
    if not entry or entry.t ~= "case" then return end
    local case = Cases.Data.cases[entry.r]
    if not case then return notify(player, "This case no longer exists", "error") end
    local count = math.floor(tonumber(a.count) or 1)
    if count ~= 3 and count ~= 5 then count = 1 end
    -- the clicked case first, then other cases of the same kind, each with its key
    local boxes, keys, used = { entry }, {}, { [entry.u] = true }
    for _, e in ipairs(p.inv) do
        if #boxes >= count then break end
        if e.t == "case" and e.r == entry.r and not used[e.u] and not Cases.Offered(player, e.u) then boxes[#boxes + 1] = e used[e.u] = true end
    end
    if #boxes < count then return notify(player, "You need " .. count .. " " .. case.name, "error") end
    if case.key and case.key ~= "" then
        for _, e in ipairs(p.inv) do
            if #keys >= count then break end
            if e.t == "key" and e.r == case.key and not Cases.Offered(player, e.u) then keys[#keys + 1] = e end
        end
        if #keys < count then return notify(player, "You need " .. count .. " × " .. Cases.NameOf("key", case.key) .. " to open this", "error") end
    end
    if not roll(case) then return notify(player, "This case is empty", "error") end
    local rolls = {}
    for i = 1, count do
        if not take(player, p, boxes[i].u) then break end
        if keys[i] then take(player, p, keys[i].u) end
        local won = roll(case)
        local reward = Cases.Give(Cases.IdOf(player), "item", won)
        sold("item", won)
        -- the strip shown by the roulette: random items of the case, the winner at position 45
        local strip = {}
        for j = 1, 55 do strip[j] = roll(case) end
        strip[45] = won
        rolls[#rolls + 1] = { strip = strip, win = won, uid = reward.u }
        local item = Cases.Data.items[won]
        if announces(item.rarity) then
            Timer.SetTimeout(function()
                pcall(function() Chat.BroadcastMessage("<yellow>" .. player:GetName() .. "</> unboxed <orange>" .. item.name .. "</> (" .. item.rarity .. ")") end)
            end, 7000)
        end
        Events.Call("Admin:Log", Cases.IdOf(player), player:GetName(), "unboxed " .. item.name .. " from " .. case.name)
    end
    if #rolls == 0 then return end
    -- the crate appears in front of the player during the animation, then disappears
    if Cases.Setting("CrateInWorld") then
        local c = player:GetControlledCharacter()
        if c then
            pcall(function()
                local loc, rot = c:GetLocation(), c:GetRotation()
                local yaw = math.rad(rot.Yaw)
                local crate = Prop(loc + Vector(math.cos(yaw) * 160, math.sin(yaw) * 160, 60), Rotator(0, rot.Yaw, 0), case.mesh or Config.CrateMesh)
                Timer.SetTimeout(function() if crate and crate:IsValid() then crate:Destroy() end end, 7500)
            end)
        end
    end
    Events.CallRemote("Cases:Opened", player, Reliability.Reliable, Cases.Encode({ case = entry.r, rolls = rolls }))
    return "nodata"   -- the menu asks for fresh data after the animation
end

-- use { uid } : credits are added, weapons given, models equipped. Perma items stay and are toggled.
function A.use(player, p, a)
    local entry = Cases.FindEntry(p, a.uid)
    if not entry or entry.t ~= "item" then return end
    local item = Cases.Data.items[entry.r]
    if not item then return end
    if item.kind == "credits" then
        if not take(player, p, entry.u) then return end
        p.credits = p.credits + math.max(0, tonumber(item.amount) or 0)
        notify(player, "+" .. (item.amount or 0) .. " " .. Config.Currency, "ok")
    elseif item.kind == "weapon" and item.perma then
        if p.perma[entry.r] then
            p.perma[entry.r] = nil
            notify(player, item.name .. ": no longer given on spawn", "ok")
        else
            p.perma[entry.r] = true
            giveWeapon(player, item.asset)
            notify(player, item.name .. ": given on every spawn", "ok")
        end
    elseif item.kind == "weapon" then
        if Cases.Offered(player, entry.u) then return notify(player, "This item is in your trade offer", "error") end
        if not giveWeapon(player, item.asset) then return notify(player, "You need a character to receive a weapon", "error") end
        take(player, p, entry.u)
        notify(player, item.name .. " given", "ok")
    elseif item.kind == "model" then
        if p.equipped == entry.r then
            p.equipped = nil
            notify(player, item.name .. " unequipped (back to your normal model after respawn)", "ok")
        else
            p.equipped = entry.r
            applyModel(player, item.asset)
            notify(player, item.name .. " equipped", "ok")
        end
    end
    Cases.Save()
end

-- sell { uid } : sells an entry back to the server (items: sell value, cases and keys: half price)
function A.sell(player, p, a)
    local entry = Cases.FindEntry(p, a.uid)
    if not entry then return end
    local def = Cases.CatalogOf(entry.t)[entry.r]
    local value = entry.t == "item" and (def and tonumber(def.sell) or 0) or math.floor((def and tonumber(def.price) or 0) / 2)
    if value <= 0 then return notify(player, "This cannot be sold to the server", "error") end
    if not take(player, p, entry.u) then return end
    p.credits = p.credits + value
    notify(player, "Sold for " .. value .. " " .. Config.Currency, "ok")
end

-- discard { uid } : deletes an entry from the own inventory
function A.discard(player, p, a)
    if take(player, p, a.uid) then notify(player, "Deleted", "ok") end
end

-- gift { uid, to = player id }
function A.gift(player, p, a)
    local target = Cases.ByNetId(a.to)
    if not target or target == player then return notify(player, "Player not found", "error") end
    local entry = take(player, p, a.uid)
    if not entry then return end
    local tp = Cases.PlayerData(Cases.IdOf(target), target:GetName())
    table.insert(tp.inv, entry)
    Cases.Save()
    notify(player, "Gift sent to " .. target:GetName(), "ok")
    notify(target, player:GetName() .. " gave you " .. Cases.NameOf(entry.t, entry.r), "ok")
    Cases.SendData(target)
end

-- list { uid, price } : puts an inventory entry on the market
function A.list(player, p, a)
    if not Cases.Setting("MarketEnabled") then return notify(player, "The market is closed", "error") end
    local price = math.floor(tonumber(a.price) or 0)
    if price < 1 or price > 10000000 then return notify(player, "Invalid price", "error") end
    local id, count, max = Cases.IdOf(player), 0, tonumber(Cases.Setting("MaxListings")) or 10
    for _, l in ipairs(Cases.Data.market) do if l.seller == id then count = count + 1 end end
    if count >= max then return notify(player, "You already have " .. max .. " listings", "error") end
    local entry = take(player, p, a.uid)
    if not entry then return end
    table.insert(Cases.Data.market, { n = Cases.NewId("m"), seller = id, sellerName = player:GetName(), entry = entry, price = price, at = os.time() })
    Cases.Save()
    notify(player, "Listed for " .. price .. " " .. Config.Currency, "ok")
end

local function findListing(n)
    for i, l in ipairs(Cases.Data.market) do if l.n == n then return l, i end end
end

-- buylisting { n }
function A.buylisting(player, p, a)
    if not Cases.Setting("MarketEnabled") then return notify(player, "The market is closed", "error") end
    local l, i = findListing(a.n)
    if not l then return notify(player, "This listing is gone", "error") end
    local id = Cases.IdOf(player)
    if l.seller == id then return end
    if p.credits < l.price then return notify(player, "Not enough " .. Config.Currency, "error") end
    table.remove(Cases.Data.market, i)
    p.credits = p.credits - l.price
    table.insert(p.inv, l.entry)
    local seller = Cases.PlayerData(l.seller)
    local gain = math.floor(l.price * (1 - (tonumber(Cases.Setting("MarketFee")) or 0)))
    seller.credits = seller.credits + gain
    Cases.Save()
    local name = Cases.NameOf(l.entry.t, l.entry.r)
    notify(player, "Bought " .. name, "ok")
    local text = player:GetName() .. " bought your " .. name .. " (+" .. gain .. " " .. Config.Currency .. ")"
    local online = Cases.Online(l.seller)
    if online then notify(online, text, "ok") else table.insert(seller.pending, text) end
end

-- unlist { n } : the seller (or an admin) takes the listing back
function A.unlist(player, p, a)
    local l, i = findListing(a.n)
    if not l then return end
    if l.seller ~= Cases.IdOf(player) and not Cases.IsAdmin(player) then return end
    table.remove(Cases.Data.market, i)
    table.insert(Cases.PlayerData(l.seller).inv, l.entry)
    Cases.Save()
end

-- ── Admin editor ─────────────────────────────────────────────────────────────────────────────
local function str(v, max) return tostring(v or ""):sub(1, max or 60) end
local function color(v, default) v = tostring(v or "") return v:match("^#%x%x%x%x%x%x$") and v or (default or "#3aa9d8") end
local function num(v, min, max) v = tonumber(v) or 0 if v ~= v then v = 0 end return math.max(min or 0, math.min(max or 1e9, v)) end
local function rarityOr(name) return Cases.Rarity(name) and name or Cases.Data.rarities[1].name end
local function mesh(v) v = str(v, 120) return v:match("^[%w%-_]+::SM_[%w%-_]+$") and v or nil end

-- saveitem { id?, name, rarity, kind, asset, amount, sell, shop, price, perma }
function A.saveitem(player, p, a)
    if a.kind ~= "credits" and a.kind ~= "weapon" and a.kind ~= "model" then return end
    local asset = str(a.asset, 120)
    if a.kind ~= "credits" and not asset:match("^[%w%-_]+::[%w%-_]+$") then return notify(player, "Asset must look like pack::SK_Name", "error") end
    local id = (a.id and Cases.Data.items[a.id]) and a.id or Cases.NewId("i")
    Cases.Data.items[id] = { name = str(a.name), rarity = rarityOr(a.rarity), kind = a.kind, asset = a.kind ~= "credits" and asset or nil,
        amount = math.floor(num(a.amount)), sell = math.floor(num(a.sell)), shop = a.shop == true,
        price = math.floor(num(a.price)), perma = a.kind == "weapon" and a.perma == true or nil }
    notify(player, "Item saved", "ok")
end

function A.deleteitem(player, p, a)
    if not Cases.Data.items[a.id] then return end
    Cases.Data.items[a.id] = nil
    for _, c in pairs(Cases.Data.cases) do
        for i = #c.items, 1, -1 do if c.items[i].item == a.id then table.remove(c.items, i) end end
    end
end

-- savecase { id?, name, price, rarity, key, mesh, shop, limit, cooldown, items = { { item, weight, mystery } } }
function A.savecase(player, p, a)
    local list = {}
    for _, e in ipairs(type(a.items) == "table" and a.items or {}) do
        if Cases.Data.items[e.item] and num(e.weight) > 0 and #list < 60 then
            list[#list + 1] = { item = e.item, weight = num(e.weight), mystery = e.mystery == true or nil }
        end
    end
    local key = (a.key and Cases.Data.keys[a.key]) and a.key or nil
    local id = (a.id and Cases.Data.cases[a.id]) and a.id or Cases.NewId("c")
    Cases.Data.cases[id] = { name = str(a.name), price = math.floor(num(a.price)), rarity = rarityOr(a.rarity), key = key, mesh = mesh(a.mesh),
        shop = a.shop == true, limit = math.floor(num(a.limit)), cooldown = math.floor(num(a.cooldown)), items = list }
    notify(player, "Case saved", "ok")
end

function A.deletecase(player, p, a) Cases.Data.cases[a.id] = nil end

-- savekey { id?, name, price, color, shop }
function A.savekey(player, p, a)
    local id = (a.id and Cases.Data.keys[a.id]) and a.id or Cases.NewId("k")
    Cases.Data.keys[id] = { name = str(a.name), price = math.floor(num(a.price)), color = color(a.color, "#e0a030"), shop = a.shop == true, mesh = mesh(a.mesh) }
    notify(player, "Key saved", "ok")
end

function A.deletekey(player, p, a)
    Cases.Data.keys[a.id] = nil
    for _, c in pairs(Cases.Data.cases) do if c.key == a.id then c.key = nil end end
end

-- rarities { list = { { name, color, weight, old } } } : the whole list, from lowest to highest.
-- Renaming a rarity (old = previous name) renames it on every item and case.
function A.rarities(player, p, a)
    local list, seen = {}, {}
    for _, r in ipairs(type(a.list) == "table" and a.list or {}) do
        local name = str(r.name, 24)
        if name ~= "" and not seen[name] and #list < 12 then
            seen[name] = true
            list[#list + 1] = { name = name, color = color(r.color), weight = num(r.weight) }
            if r.old and r.old ~= name then
                for _, cat in ipairs({ Cases.Data.items, Cases.Data.cases }) do
                    for _, def in pairs(cat) do if def.rarity == r.old then def.rarity = name end end
                end
            end
        end
    end
    if #list == 0 then return notify(player, "At least one rarity is needed", "error") end
    Cases.Data.rarities = list
    for _, cat in ipairs({ Cases.Data.items, Cases.Data.cases }) do
        for _, def in pairs(cat) do if not seen[def.rarity] then def.rarity = list[1].name end end
    end
    notify(player, "Rarities saved", "ok")
end

-- settings { ...CasesConfig.Defaults keys }
function A.settings(player, p, a)
    local s = Cases.Data.settings
    s.StartCredits = math.floor(num(a.StartCredits))
    s.PlaytimeReward = math.floor(num(a.PlaytimeReward))
    s.PlaytimeMinutes = math.floor(num(a.PlaytimeMinutes, 1, 1440))
    s.MarketFee = num(a.MarketFee, 0, 0.9)
    s.MaxListings = math.floor(num(a.MaxListings, 1, 100))
    s.AnnounceFrom = Cases.Rarity(a.AnnounceFrom) and a.AnnounceFrom or ""
    s.CrateInWorld, s.TradeEnabled, s.MarketEnabled = a.CrateInWorld == true, a.TradeEnabled == true, a.MarketEnabled == true
    local cmd = str(a.ChatCommand, 20)
    s.ChatCommand = cmd:match("^[!/][%w_]+$") and cmd or "!cases"
    Cases.RestartPlaytime()
    notify(player, "Settings saved", "ok")
end

-- featured { list = { { t, r } } } : the "Special" row of the home page
function A.featured(player, p, a)
    local list = {}
    for _, f in ipairs(type(a.list) == "table" and a.list or {}) do
        if (f.t == "case" or f.t == "key" or f.t == "item") and Cases.CatalogOf(f.t)[f.r] and #list < 12 then list[#list + 1] = { t = f.t, r = f.r } end
    end
    Cases.Data.featured = list
end

-- givecredits { to = player id, amount }   (negative amounts remove credits)
function A.givecredits(player, p, a)
    local o = Cases.ByNetId(a.to)
    if not o then return end
    local amount = math.floor(tonumber(a.amount) or 0)
    local d = Cases.PlayerData(Cases.IdOf(o), o:GetName())
    d.credits = math.max(0, d.credits + amount)
    notify(player, o:GetName() .. ": " .. d.credits .. " " .. Config.Currency, "ok")
    Events.Call("Admin:Log", Cases.IdOf(player), player:GetName(), "gave " .. amount .. " " .. Config.Currency .. " to " .. o:GetName())
    Cases.SendData(o)
end

-- giveentry { to = player id, kind, ref }
function A.giveentry(player, p, a)
    local o = Cases.ByNetId(a.to)
    if not o or not Cases.CatalogOf(a.kind)[a.ref] then return end
    Cases.Give(Cases.IdOf(o), a.kind, a.ref)
    notify(player, "Given to " .. o:GetName(), "ok")
    Cases.SendData(o)
end

-- takeentry { to = player id, uid } : removes an entry from a player's inventory
function A.takeentry(player, p, a)
    local o = Cases.ByNetId(a.to)
    if not o then return end
    local d = Cases.PlayerData(Cases.IdOf(o), o:GetName())
    if take(o, d, a.uid) then
        notify(player, "Removed from " .. o:GetName(), "ok")
        Events.Call("Admin:Log", Cases.IdOf(player), player:GetName(), "removed an item from " .. o:GetName())
        Cases.SendData(o)
    end
end

local ADMIN = { saveitem = true, deleteitem = true, savecase = true, deletecase = true, savekey = true, deletekey = true, rarities = true,
    settings = true, featured = true, givecredits = true, giveentry = true, takeentry = true }

Events.SubscribeRemote("Cases:Do", function(player, action, payload)
    if type(action) ~= "string" or not A[action] then return end
    local now = os.clock()
    if last_action[player] and now - last_action[player] < 0.25 and action ~= "tradeset" then return end
    last_action[player] = now
    if ADMIN[action] and not Cases.IsAdmin(player) then return end
    local a = Cases.Decode(payload) or {}
    local p = Cases.PlayerData(Cases.IdOf(player), player:GetName())
    local ok, result = pcall(A[action], player, p, a)
    if not ok then Console.Warn("[pandora-cases] action " .. action .. " failed: " .. tostring(result)) end
    Cases.Save()
    if result ~= "nodata" and not action:match("^trade") then Cases.SendData(player) end
end)

Events.SubscribeRemote("Cases:Request", function(player) Cases.SendData(player) end)

-- ── Players ──────────────────────────────────────────────────────────────────────────────────
-- The equipped model and the perma weapons come back on every new character.
Player.Subscribe("Possess", function(player, character)
    local p = Cases.Data.players[Cases.IdOf(player)]
    if not p then return end
    Timer.SetTimeout(function()
        if not player:IsValid() then return end
        Cases.CleanOwnership(p)
        local model = p.equipped and Cases.Data.items[p.equipped]
        if model and model.kind == "model" then applyModel(player, model.asset) end
        for id in pairs(p.perma or {}) do
            local item = Cases.Data.items[id]
            if item and item.kind == "weapon" and item.perma then giveWeapon(player, item.asset) end
        end
    end, 300)
end)

Player.Subscribe("Destroy", function(player) last_action[player] = nil end)

local playtime
function Cases.RestartPlaytime()
    if playtime then Timer.ClearInterval(playtime) playtime = nil end
    local reward, minutes = tonumber(Cases.Setting("PlaytimeReward")) or 0, tonumber(Cases.Setting("PlaytimeMinutes")) or 0
    if reward <= 0 or minutes <= 0 then return end
    playtime = Timer.SetInterval(function()
        for _, pl in ipairs(Cases.AllPlayers()) do
            local d = Cases.PlayerData(Cases.IdOf(pl), pl:GetName())
            d.credits = d.credits + reward
            notify(pl, "+" .. reward .. " " .. Config.Currency .. " for playing", "ok")
        end
        Cases.Save()
    end, minutes * 60000)
end
Cases.RestartPlaytime()

-- Chat: the command (default !cases) opens the menu; other text goes through untouched.
Chat.Subscribe("PlayerSubmit", function(text, player)
    local cmd = Cases.Setting("ChatCommand") or "!cases"
    if text == cmd or text == "!cases" or text == "/cases" then
        Events.CallRemote("Cases:Open", player, Reliability.Reliable)
        return false
    end
end)

-- ── Server console: cases <command> ──────────────────────────────────────────────────────────
Console.RegisterCommand("cases", function(cmd, a1, a2)
    if cmd == "addadmin" and a1 then
        Cases.Data.admins[tostring(a1)] = true Cases.SaveNow() Console.Log("[pandora-cases] " .. a1 .. " can now edit cases")
    elseif cmd == "removeadmin" and a1 then
        Cases.Data.admins[tostring(a1)] = nil Cases.SaveNow() Console.Log("[pandora-cases] " .. a1 .. " removed")
    elseif cmd == "credits" and a1 and a2 then
        local d = Cases.PlayerData(tostring(a1))
        d.credits = math.max(0, d.credits + math.floor(tonumber(a2) or 0)) Cases.SaveNow()
        Console.Log("[pandora-cases] " .. a1 .. " now has " .. d.credits)
    else
        Console.Log("cases addadmin <steam id> | cases removeadmin <steam id> | cases credits <steam id> <amount>")
    end
end, "Pandora Cases admin commands", { "command", "arg1", "arg2" })
