local MAX_ACTIVE = 12
local EFFECT_LIFETIME = 8
local COOLDOWN = 0.35

local allowed_particles = {}
local allowed_meshes = {}
local active_by_player = {}
local last_spawn = {}
local can_use = {}

local function BuildAllowlist()
    for _, pack in pairs(Assets.GetAssetPacks()) do
        local path = pack.Path
        if type(path) == "string" then
            local ok_particles, particles = pcall(Assets.GetParticles, path)
            if ok_particles and type(particles) == "table" then
                for _, asset in pairs(particles) do
                    if type(asset) == "table" and type(asset.key) == "string" then
                        allowed_particles[path .. "::" .. asset.key] = true
                    end
                end
            end

            local ok_meshes, meshes = pcall(Assets.GetStaticMeshes, path)
            if ok_meshes and type(meshes) == "table" then
                for _, asset in pairs(meshes) do
                    if type(asset) == "table" and type(asset.key) == "string"
                        and FXShowcase.IsEffectMesh(path, asset) then
                        allowed_meshes[path .. "::" .. asset.key] = true
                    end
                end
            end
        end
    end

    local particle_count, mesh_count = 0, 0
    for _ in pairs(allowed_particles) do particle_count = particle_count + 1 end
    for _ in pairs(allowed_meshes) do mesh_count = mesh_count + 1 end
    Console.Log("[fx-showcase] allowlist ready: " .. particle_count .. " particles, " .. mesh_count .. " effect meshes")
end

local function PlayerKey(player)
    local ok, id = pcall(function() return player:GetSteamID() end)
    if ok and id and tostring(id) ~= "" and tostring(id) ~= "0" then return tostring(id) end
    ok, id = pcall(function() return player:GetAccountID() end)
    if ok and id then return tostring(id) end
    return "id" .. tostring(player:GetID())
end

local function Deny(player, message)
    pcall(function()
        Events.CallRemote("FXShowcase:Notice", player, Reliability.Reliable, message)
    end)
end

local function Track(player, entity)
    if not entity then return false end
    local list = active_by_player[player] or {}
    active_by_player[player] = list
    while #list >= MAX_ACTIVE do
        local old = table.remove(list, 1)
        pcall(function() if old and old:IsValid() then old:Destroy() end end)
    end
    table.insert(list, entity)
    entity:SetLifeSpan(EFFECT_LIFETIME)
    return true
end

local function ForwardFromRotation(rotation)
    local yaw = math.rad(rotation.Yaw)
    return Vector(math.cos(yaw), math.sin(yaw), 0)
end

BuildAllowlist()

-- Reuse the server's existing props permission. If nanos-admin is installed,
-- only players allowed to use the props menu can trigger showcase effects.
Events.Subscribe("Admin:Perms", function(id, props_allowed)
    can_use[tostring(id)] = props_allowed == true
end)
Events.Call("PropsMenu:Ready")

Events.SubscribeRemote("FXShowcase:Spawn", function(player, asset)
    if not can_use[PlayerKey(player)] then
        Deny(player, "You do not have permission to use the FX showcase.")
        return
    end

    local pawn = player:GetControlledCharacter()
    if not pawn then return end
    local now = os.clock()
    if last_spawn[player] and now - last_spawn[player] < COOLDOWN then return end
    last_spawn[player] = now

    local kind
    if allowed_particles[asset] then
        kind = "particle"
    elseif allowed_meshes[asset] then
        kind = "mesh"
    else
        return
    end

    local origin = pawn:GetLocation()
    local forward = ForwardFromRotation(pawn:GetRotation())
    local location = Vector(origin.X + forward.X * 300, origin.Y + forward.Y * 300, origin.Z + 80)

    local ok, entity = pcall(function()
        if kind == "particle" then
            return Particle(location, pawn:GetRotation(), asset, false, true)
        end
        return StaticMesh(location, pawn:GetRotation(), asset, CollisionType.NoCollision)
    end)
    if not ok or not entity then
        Console.Warn("[fx-showcase] failed to spawn " .. tostring(asset) .. ": " .. tostring(entity))
        Deny(player, "This effect could not be spawned.")
        return
    end

    Track(player, entity)
end)

Events.SubscribeRemote("FXShowcase:Clear", function(player)
    local list = active_by_player[player]
    if not list then return end
    for _, entity in ipairs(list) do
        pcall(function() if entity and entity:IsValid() then entity:Destroy() end end)
    end
    active_by_player[player] = nil
end)

Player.Subscribe("Destroy", function(player)
    local list = active_by_player[player]
    if list then
        for _, entity in ipairs(list) do
            pcall(function() if entity and entity:IsValid() then entity:Destroy() end end)
        end
    end
    active_by_player[player] = nil
    last_spawn[player] = nil
    can_use[PlayerKey(player)] = nil
end)
