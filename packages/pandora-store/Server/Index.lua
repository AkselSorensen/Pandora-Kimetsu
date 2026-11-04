-- Pandora Store: delivers what players buy on the website, and runs the in-game store menu.
Package.Require("ServerConfig.lua")
Store = { State = { weapons = {}, groups = {}, done = {} } }

local FILE = "PandoraStore/state.json"
local host, base = StoreConfig.ApiUrl:match("^(https?://[^/]+)(.*)$")
base = (base or ""):gsub("/$", "") .. "/api"

-- ── Helpers ──────────────────────────────────────────────────────────────────────────────────
function Store.IdOf(player)
    local ok, id = pcall(function() return player:GetSteamID() end)
    if ok and id and tostring(id) ~= "" and tostring(id) ~= "0" then return tostring(id) end
    return nil
end

function Store.Online(steam)
    for _, p in pairs(Player.GetAll()) do if Store.IdOf(p) == steam then return p end end
end

function Store.Say(player, text)
    pcall(function() Chat.SendMessage(player, StoreConfig.ChatPrefix .. text) end)
end

local function decode(text)
    if type(text) ~= "string" or text == "" then return nil end
    local ok, data = pcall(function() return JSON.parse(text) end)
    return ok and data or nil
end

-- callback(ok, data, status). Never throws, so a down website never breaks the server.
function Store.Request(method, path, body, callback)
    if not host or StoreConfig.ServerKey == "" then
        if callback then callback(false, { message = "Pandora Store is not configured (Server/ServerConfig.lua)" }, 0) end
        return
    end
    local ok, err = pcall(function()
        HTTP.RequestAsync(host, base .. path, method, body and JSON.stringify(body) or "", "application/json", false,
            { ["X-Server-Key"] = StoreConfig.ServerKey },
            function(status, data)
                if callback then callback(status >= 200 and status < 300, decode(data) or {}, status) end
            end)
    end)
    if not ok then
        Console.Warn("[pandora-store] request failed: " .. tostring(err))
        if callback then callback(false, { message = "request failed" }, 0) end
    end
end

-- ── Saved state (perma weapons and store groups, so they come back after a restart) ──────────
function Store.Load()
    if not File.Exists(FILE) then return end
    local data = decode(File(FILE):Read())
    if type(data) == "table" then
        Store.State.weapons = data.weapons or {}
        Store.State.groups = data.groups or {}
        Store.State.done = data.done or {}
    end
end

function Store.Save()
    local ok, err = pcall(function()
        local file = File(FILE, true)
        file:Write(JSON.stringify(Store.State))
        file:Close()
    end)
    if not ok then Console.Warn("[pandora-store] could not save " .. FILE .. ": " .. tostring(err)) end
end

Package.Require("Delivery.lua")
Package.Require("Menu.lua")

Store.Load()
if StoreConfig.ServerKey == "" then
    Console.Warn("[pandora-store] no server key: set StoreConfig.ServerKey in Packages/pandora-store/Server/ServerConfig.lua")
else
    Console.Log("[pandora-store] connected to " .. host .. base)
end
