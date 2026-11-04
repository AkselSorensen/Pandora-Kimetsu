-- Small helpers shared by the admin modules.
Admin = Admin or {}

function Admin.Escape(text)
    return (tostring(text):gsub('\\', '\\\\'):gsub('"', '\\"'))
end

-- Stable identifier of a player (Steam ID when available).
function Admin.IdOf(player)
    local ok, id = pcall(function() return player:GetSteamID() end)
    if ok and id and tostring(id) ~= "" and tostring(id) ~= "0" then return tostring(id) end
    ok, id = pcall(function() return player:GetAccountID() end)
    if ok and id then return tostring(id) end
    return "id" .. tostring(player:GetID())
end

-- Sends a chat line to one player (nil = server console).
function Admin.Reply(player, text)
    if not player then
        Console.Log((tostring(text):gsub("<[^>]*>", "")))
        return
    end
    local ok = pcall(function() Chat.SendMessage(player, text) end)
    if not ok then pcall(function() Chat.BroadcastMessage(text) end) end
end

function Admin.Broadcast(text)
    Chat.BroadcastMessage(text)
    Console.Log((tostring(text):gsub("<[^>]*>", "")))
end

-- "30m", "2h", "1d", "1w", "90" (minutes) or "0" (permanent) -> seconds, or nil when invalid.
function Admin.ParseDuration(text)
    if text == nil then return nil end
    local n, unit = tostring(text):match("^(%d+)(%a?)$")
    if not n then return nil end
    n = tonumber(n)
    local mult = { s = 1, m = 60, h = 3600, d = 86400, w = 604800 }
    if unit == "" then unit = "m" end
    if not mult[unit] then return nil end
    return n * mult[unit]
end

function Admin.FormatDuration(seconds)
    if not seconds or seconds <= 0 then return "permanent" end
    if seconds >= 86400 then return string.format("%.1f d", seconds / 86400) end
    if seconds >= 3600 then return string.format("%.1f h", seconds / 3600) end
    return string.format("%d min", math.ceil(seconds / 60))
end

-- Splits a command line into words, keeping "quoted text" together.
function Admin.SplitArgs(line)
    local args = {}
    local i, n = 1, #line
    while i <= n do
        local c = line:sub(i, i)
        if c:match("%s") then
            i = i + 1
        elseif c == '"' then
            local j = line:find('"', i + 1, true)
            if not j then j = n + 1 end
            args[#args + 1] = line:sub(i + 1, j - 1)
            i = j + 1
        else
            local j = line:find("%s", i) or (n + 1)
            args[#args + 1] = line:sub(i, j - 1)
            i = j
        end
    end
    return args
end

-- Minimal JSON encoder (strings, numbers, booleans, arrays, objects) used to send data to the menu.
function Admin.Encode(v)
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
            for i = 1, #v do parts[i] = Admin.Encode(v[i]) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        local parts = {}
        for k, val in pairs(v) do parts[#parts + 1] = Admin.Encode(tostring(k)) .. ":" .. Admin.Encode(val) end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return "null"
end
