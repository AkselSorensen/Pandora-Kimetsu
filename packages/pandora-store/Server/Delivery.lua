-- Delivery: asks the website for new purchases and carries out each action.
-- Every action works for offline players too (perma weapons wait for their next spawn).
local function weaponsOf(steam)
    Store.State.weapons[steam] = Store.State.weapons[steam] or {}
    return Store.State.weapons[steam]
end

local function spawnWeapon(player, asset)
    local c = player:GetControlledCharacter()
    if not c then return end
    pcall(function()
        local w = Weapon(c:GetLocation() + Vector(0, 0, 50), Rotator(0, 0, 0), asset)
        c:PickUp(w)
    end)
end

local function fill(text, cmd)
    return (tostring(text):gsub("{name}", cmd.player or "?"):gsub("{package}", cmd.package or ""))
end

local GIVE = {
    role = function(cmd, a)
        -- nanos-admin keeps a higher group (staff) and only raises the player
        Events.Call("Admin:GrantGroup", cmd.steamId, cmd.player, a.group)
        Store.State.groups[cmd.grantId] = { steam = cmd.steamId, group = a.group }
    end,
    credits = function(cmd, a) Events.Call("Cases:GiveCredits", cmd.steamId, a.amount, cmd.player) end,
    caseItem = function(cmd, a) Events.Call("Cases:GiveEntry", cmd.steamId, a.kind, a.ref, a.amount, cmd.player) end,
    weapon = function(cmd, a)
        weaponsOf(cmd.steamId)[cmd.grantId .. ":" .. a.asset] = a.asset
        local p = Store.Online(cmd.steamId)
        if p then spawnWeapon(p, a.asset) end
    end,
    event = function(cmd, a) Events.Call(a.name, cmd.steamId, a.value, true) end,
    chat = function(cmd, a) pcall(function() Chat.BroadcastMessage(StoreConfig.ChatPrefix .. fill(a.message, cmd)) end) end,
}

local REMOVE = {
    role = function(cmd, a)
        Events.Call("Admin:RevokeGroup", cmd.steamId, cmd.player, a.group)
        Store.State.groups[cmd.grantId] = nil
    end,
    weapon = function(cmd, a) weaponsOf(cmd.steamId)[cmd.grantId .. ":" .. a.asset] = nil end,
    event = function(cmd, a) Events.Call(a.name, cmd.steamId, a.value, false) end,
}

local function run(cmd)
    local list = cmd.type == "GIVE" and GIVE or REMOVE
    for _, a in ipairs(cmd.actions or {}) do
        local fn = list[a.type]
        if fn then
            local ok, err = pcall(fn, cmd, a)
            if not ok then Console.Warn("[pandora-store] " .. tostring(a.type) .. " failed for " .. tostring(cmd.steamId) .. ": " .. tostring(err)) end
        end
    end
    local p = Store.Online(cmd.steamId)
    if p and cmd.type == "GIVE" then Store.Say(p, "Merci ! <green>" .. tostring(cmd.package) .. "</> est arrivé.") end
    if p and cmd.type == "REMOVE" then Store.Say(p, "<yellow>" .. tostring(cmd.package) .. "</> est terminé.") end
    Console.Log("[pandora-store] " .. cmd.type .. " " .. tostring(cmd.package) .. " -> " .. tostring(cmd.steamId))
end

-- A command is acknowledged after it ran. If the ack is lost, "done" stops it from running twice.
local busy = false
function Store.Poll()
    if busy then return end
    busy = true
    Store.Request(HTTPMethod.GET, "/game/queue", nil, function(ok, list)
        busy = false
        if not ok or type(list) ~= "table" or #list == 0 then return end
        local ids = {}
        for _, cmd in ipairs(list) do
            local key = tostring(cmd.id)
            if not Store.State.done[key] then
                run(cmd)
                Store.State.done[key] = os.time()
            end
            ids[#ids + 1] = cmd.id
        end
        Store.Save()
        Store.Request(HTTPMethod.POST, "/game/ack", { ids = ids }, function(acked)
            if not acked then return end
            for _, id in ipairs(ids) do Store.State.done[tostring(id)] = nil end
            Store.Save()
        end)
    end)
end

Timer.SetInterval(Store.Poll, math.max(5, StoreConfig.PollSeconds) * 1000)
Timer.SetTimeout(Store.Poll, 3000)

-- Perma weapons come back on every new character while the package lasts.
Player.Subscribe("Possess", function(player)
    local steam = Store.IdOf(player)
    local list = steam and Store.State.weapons[steam]
    if not list or next(list) == nil then return end
    Timer.SetTimeout(function()
        if not player:IsValid() then return end
        for _, asset in pairs(list) do spawnWeapon(player, asset) end
    end, 400)
end)

Console.RegisterCommand("store", function(cmd)
    if cmd == "poll" then Store.Poll() Console.Log("[pandora-store] checking for purchases")
    else Console.Log("[pandora-store] commands: store poll") end
end, "Pandora Store: store poll")
