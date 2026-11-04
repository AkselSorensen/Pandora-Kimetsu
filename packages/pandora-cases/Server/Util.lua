-- Small helpers: player ids, JSON encoding, chat.
function Cases.IdOf(player)
    local ok, id = pcall(function() return player:GetSteamID() end)
    if ok and id and tostring(id) ~= "" and tostring(id) ~= "0" then return tostring(id) end
    ok, id = pcall(function() return player:GetAccountID() end)
    if ok and id then return tostring(id) end
    return "id" .. tostring(player:GetID())
end

function Cases.Encode(v)
    local t = type(v)
    if v == nil then return "null" end
    if t == "boolean" then return v and "true" or "false" end
    if t == "number" then return (v ~= v or v == math.huge or v == -math.huge) and "0" or string.format("%.14g", v) end
    if t == "string" then
        local s = v:gsub('[%c"\\]', function(c)
            local map = { ['"'] = '\\"', ["\\"] = "\\\\", ["\n"] = "\\n", ["\r"] = "\\r", ["\t"] = "\\t" }
            return map[c] or string.format("\\u%04x", c:byte())
        end)
        return '"' .. s .. '"'
    end
    if t == "table" then
        if next(v) == nil or #v > 0 then
            local parts = {}
            for i = 1, #v do parts[i] = Cases.Encode(v[i]) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        local parts = {}
        for k, val in pairs(v) do parts[#parts + 1] = Cases.Encode(tostring(k)) .. ":" .. Cases.Encode(val) end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return "null"
end

function Cases.Decode(text)
    if type(text) ~= "string" or #text > 20000 then return nil end
    local ok, data = pcall(function() return JSON.parse(text) end)
    if ok and type(data) == "table" then return data end
    return nil
end

function Cases.Tell(player, text)
    if player then pcall(function() Chat.SendMessage(player, text) end) else Console.Log((text:gsub("<[^>]*>", ""))) end
end

function Cases.AllPlayers()
    local list = {}
    for _, p in pairs(Player.GetPairs()) do list[#list + 1] = p end
    return list
end

function Cases.IsAdmin(player)
    if not player then return true end
    local id = Cases.IdOf(player)
    for _, admin in ipairs(CasesConfig.Admins) do
        if tostring(admin) == id then return true end
    end
    return Cases.Data ~= nil and Cases.Data.admins[id] == true
end

function Cases.Notify(player, text, kind)
    Events.CallRemote("Cases:Notify", player, Reliability.Reliable, text, kind or "info")
end

function Cases.ByNetId(id)
    for _, p in ipairs(Cases.AllPlayers()) do if p:GetID() == tonumber(id) then return p end end
end

function Cases.Online(steam)
    for _, p in ipairs(Cases.AllPlayers()) do if Cases.IdOf(p) == steam then return p end end
end

function Cases.NameOf(kind, ref)
    local def = Cases.CatalogOf(kind)[ref]
    return def and def.name or "item"
end
