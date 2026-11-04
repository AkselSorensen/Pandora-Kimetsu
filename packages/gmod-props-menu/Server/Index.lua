-- Server-side spawning: validates every request before creating a prop, weapon or equipping a model.
-- The catalog itself is built on the client from the engine's Assets API (see Client/Index.lua).
local Config = PropsMenuConfig

local HISTORY_FILE = "Packages/gmod-props-menu/history.json"

local owned = {}                  -- [player] = { entity, entity, ... }
local owner_of = {}               -- [entity] = player
local last_spawn = {}             -- [player] = os.clock() of the last spawn
local history = {}                -- [account_id] = { { k = kind, a = asset, t = os.time() }, ... }
local last_save = 0

local function AccountKey(player)
    local ok, id = pcall(function() return tostring(player:GetAccountID()) end)
    return ok and id or tostring(player:GetID())
end

-- ── History (kept per account, optionally saved to disk) ─────────────────────────────────────
-- ── Link with Nanos Admin (optional) ─────────────────────────────────────────────────────────
-- When the nanos-admin package is loaded it sends each player's permissions (role "props" / "models"
-- permissions and the role's prop limit). Without it nothing changes: everybody may spawn.
local Perms = {}   -- [steam id] = { props = bool, models = bool, limit = n (-1 = default) }

local function SteamKey(player)
    local ok, id = pcall(function() return player:GetSteamID() end)
    if ok and id and tostring(id) ~= "" and tostring(id) ~= "0" then return tostring(id) end
    ok, id = pcall(function() return player:GetAccountID() end)
    if ok and id then return tostring(id) end
    return "id" .. tostring(player:GetID())
end

Events.Subscribe("Admin:Perms", function(id, props, models, limit)
    Perms[tostring(id)] = { props = props, models = models, limit = tonumber(limit) or -1 }
end)

local function AdminLog(player, text)
    Events.Call("Admin:Log", SteamKey(player), player:GetName(), text)
end

local function Deny(player, text)
    pcall(function() Chat.SendMessage(player, "<red>[Props]</> " .. text) end)
end

local function LoadHistory()
    if not Config.SaveHistory or not File.Exists(HISTORY_FILE) then return end
    local ok, data = pcall(function() return JSON.parse(File(HISTORY_FILE):Read()) end)
    if ok and type(data) == "table" then history = data end
end

local function SaveHistory(force)
    if not Config.SaveHistory then return end
    local now = os.clock()
    if not force and now - last_save < 5 then return end
    last_save = now
    pcall(function()
        local file = File(HISTORY_FILE, true)
        file:Write(JSON.stringify(history))
        file:Close()
    end)
end

local function Escape(text)
    return (tostring(text):gsub('\\', '\\\\'):gsub('"', '\\"'))
end

local function SendHistory(player)
    local rows = {}
    for _, h in ipairs(history[AccountKey(player)] or {}) do
        rows[#rows + 1] = string.format('{"k":"%s","a":"%s","t":%d}', Escape(h.k), Escape(h.a), h.t)
    end
    Events.CallRemote("PropsMenu:History", player, Reliability.Reliable, "[" .. table.concat(rows, ",") .. "]")
end

local function RecordHistory(player, kind, asset)
    local key = AccountKey(player)
    local list = history[key] or {}
    history[key] = list
    list[#list + 1] = { k = kind, a = asset, t = os.time() }
    while #list > Config.HistorySize do table.remove(list, 1) end
    SaveHistory(false)
    SendHistory(player)
end

LoadHistory()

-- ── Spawning ─────────────────────────────────────────────────────────────────────────────────
-- Horizontal forward vector from a rotator's yaw (degrees).
local function ForwardFromRotation(rotation)
    local yaw = math.rad(rotation.Yaw)
    return Vector(math.cos(yaw), math.sin(yaw), 0)
end

-- "pack::SM_name" (prop) / "pack::SK_name" (model or weapon)
local function IsValidAsset(asset, prefix)
    return type(asset) == "string" and #asset < 200 and asset:match("^[%w%-_]+::" .. prefix .. "[%w_%-%.]+$") ~= nil
end

local function Forget(entity)
    local player = owner_of[entity]
    owner_of[entity] = nil
    local list = player and owned[player]
    if not list then return end
    for i = #list, 1, -1 do
        if list[i] == entity then table.remove(list, i) end
    end
end

Events.SubscribeRemote("PropsMenu:Spawn", function(player, kind, asset)
    local pawn = player:GetControlledCharacter()
    if not pawn then return end

    local now = os.clock()
    if last_spawn[player] and now - last_spawn[player] < Config.Cooldown then return end
    last_spawn[player] = now

    local perm = Perms[SteamKey(player)]

    -- ODM Gear (package odm-gear) : on l'équipe au lieu de faire apparaître une arme
    if kind == "weapon" and asset == "odm-gear::ODM" then
        Events.Call("ODM:Equip", player)
        return
    end

    -- Melee weapon (static mesh): the game mode puts it in the player's hand instead of dropping it on the ground
    local melee = kind == "weapon" and type(asset) == "string" and (Config.MeleeWeapons or {})[asset]
    if melee then
        if perm and not perm.props then Deny(player, "your role cannot spawn objects.") return end
        Events.Call("Wakfu:EquipWeapon", player, melee)
        AdminLog(player, "equipped weapon " .. asset)
        RecordHistory(player, kind, asset)
        return
    end

    -- a model is equipped directly on the player's character
    if kind == "model" then
        if not IsValidAsset(asset, "SK_") then return end
        if perm and not perm.models then Deny(player, "your role cannot equip models.") return end
        local ok = pcall(function() pawn:SetMesh(asset) end)
        if ok then
            RecordHistory(player, kind, asset)
            AdminLog(player, "equipped model " .. asset)
        else
            Console.Warn("[props-menu] could not equip " .. asset)
        end
        return
    end

    if kind ~= "prop" and kind ~= "weapon" then return end
    if not IsValidAsset(asset, kind == "prop" and "SM_" or "SK_") then return end

    if perm and not perm.props then Deny(player, "your role cannot spawn objects.") return end

    local list = owned[player] or {}
    owned[player] = list
    local limit = (perm and perm.limit >= 0) and perm.limit or Config.MaxPropsPerPlayer
    if #list >= limit then Deny(player, "limit reached (" .. limit .. " objects).") return end

    local origin = pawn:GetLocation()
    local forward = ForwardFromRotation(pawn:GetRotation())
    local location = Vector(
        origin.X + forward.X * Config.SpawnDistance,
        origin.Y + forward.Y * Config.SpawnDistance,
        origin.Z + Config.SpawnHeight
    )

    local entity
    if kind == "prop" then
        entity = Prop(location, Rotator(0, 0, 0), asset)
    else
        entity = Weapon(location, Rotator(0, 0, 0), asset)
    end
    if entity then
        AdminLog(player, "spawned " .. kind .. " " .. asset)
        table.insert(list, entity)
        owner_of[entity] = player
        RecordHistory(player, kind, asset)
    end
end)

Events.SubscribeRemote("PropsMenu:Undo", function(player)
    local list = owned[player]
    if not list or #list == 0 then return end
    local entity = table.remove(list)
    owner_of[entity] = nil
    entity:Destroy()
end)

Events.SubscribeRemote("PropsMenu:Clear", function(player)
    local list = owned[player]
    if not list then return end
    for _, entity in ipairs(list) do
        owner_of[entity] = nil
        entity:Destroy()
    end
    owned[player] = nil
end)

-- Removes the prop the player is aiming at (the client sends the entity it traced).
Events.SubscribeRemote("PropsMenu:RemoveAimed", function(player, entity)
    if entity == nil or not entity:IsValid() then return end
    local owner = owner_of[entity]
    if not owner then return end                          -- only props spawned from this menu
    if owner ~= player and not Config.AllowRemoveOthers then return end
    Forget(entity)
    entity:Destroy()
end)

Events.SubscribeRemote("PropsMenu:RequestHistory", function(player)
    SendHistory(player)
end)

Events.SubscribeRemote("PropsMenu:ClearHistory", function(player)
    history[AccountKey(player)] = nil
    SaveHistory(true)
    SendHistory(player)
end)

-- Clean up when a player leaves so their props do not stay in the world.
Player.Subscribe("Destroy", function(player)
    local list = owned[player]
    if list then
        for _, entity in ipairs(list) do
            owner_of[entity] = nil
            entity:Destroy()
        end
    end
    owned[player] = nil
    last_spawn[player] = nil
    SaveHistory(true)
end)

-- Ask nanos-admin (if it is loaded) to send the permissions of everybody.
Events.Call("PropsMenu:Ready")

Package.Subscribe("Unload", function()
    SaveHistory(true)
end)
