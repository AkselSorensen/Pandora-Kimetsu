-- In-game store menu: store contents, the player's packages, buying with store credits and the website login code.
local cache, cache_at = nil, 0
local last = {}

local function send(player, name, data) Events.CallRemote(name, player, Reliability.Reliable, JSON.stringify(data)) end

local function withStore(callback)
    if cache and os.time() - cache_at < 60 then return callback(cache) end
    Store.Request(HTTPMethod.GET, "/game/store", nil, function(ok, data)
        if ok then cache, cache_at = data, os.time() end
        callback(ok and data or cache)
    end)
end

-- Opening the menu also creates the 6-digit code to sign in on the website.
function Store.Open(player)
    local steam = Store.IdOf(player)
    if not steam then return Store.Say(player, "<red>Steam ID introuvable.</>") end
    Events.CallRemote("Store:Open", player, Reliability.Reliable)
    withStore(function(store)
        if not player:IsValid() then return end
        if not store then return send(player, "Store:Error", { message = "La boutique ne répond pas, réessaie plus tard." }) end
        send(player, "Store:Catalog", store)
    end)
    Store.Request(HTTPMethod.GET, "/game/players/" .. steam, nil, function(ok, me)
        if ok and player:IsValid() then send(player, "Store:Me", me) end
    end)
    Store.Request(HTTPMethod.POST, "/game/players/" .. steam .. "/login-code", { name = player:GetName() }, function(ok, data)
        if ok and player:IsValid() then
            send(player, "Store:Code", data)
            Store.Say(player, "Ton code pour le site : <yellow>" .. tostring(data.code) .. "</> (" .. tostring(data.url) .. ", 10 min)")
        end
    end)
end

Events.SubscribeRemote("Store:Request", function(player) Store.Open(player) end)

Events.SubscribeRemote("Store:Buy", function(player, package_id)
    local steam = Store.IdOf(player)
    if not steam or (last[player] and os.clock() - last[player] < 2) then return end
    last[player] = os.clock()
    Store.Request(HTTPMethod.POST, "/game/players/" .. steam .. "/buy", { packageId = tonumber(package_id), name = player:GetName() }, function(ok, data)
        if not player:IsValid() then return end
        send(player, "Store:Bought", { ok = ok, message = ok and "Achat réussi !" or tostring(data.message or "Achat impossible") })
        if ok then
            Store.Poll()
            Store.Request(HTTPMethod.GET, "/game/players/" .. steam, nil, function(ok2, me) if ok2 and player:IsValid() then send(player, "Store:Me", me) end end)
        end
    end)
end)

Chat.Subscribe("PlayerSubmit", function(text, player)
    for _, cmd in ipairs(StoreConfig.ChatCommands) do
        if text == cmd then Store.Open(player) return false end
    end
end)

Player.Subscribe("Destroy", function(player) last[player] = nil end)
