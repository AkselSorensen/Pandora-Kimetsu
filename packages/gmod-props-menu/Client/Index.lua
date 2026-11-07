-- Client-side menu: opens the WebUI with a key, builds the catalog from the engine's Assets API
-- (base nanos-world pack included, like the Sandbox spawn menu) and forwards choices to the server.
local Config = PropsMenuConfig

local menu = WebUI("Props Menu", "file://UI/index.html", WidgetVisibility.Hidden)
local is_open = false
local catalog_json = nil

local function JsonString(text)
    return '"' .. tostring(text):gsub('\\', '\\\\'):gsub('"', '\\"') .. '"'
end

local function IsWeaponCategory(category)
    return category ~= nil and tostring(category):lower():find("weapon") ~= nil
end

local function BuildCatalog()
    local items = {}
    local melee_weapons = Config.MeleeWeapons or {}
    local melee_groups = Config.MeleeGroups or {}
    for _, pack in pairs(Assets.GetAssetPacks()) do
        local path = pack.Path

        for _, mesh in pairs(Assets.GetStaticMeshes(path)) do
            local id = path .. "::" .. mesh.key
            local melee = melee_weapons[id] ~= nil   -- listed under Weapons, not Props
            local thumb = "assets://" .. path .. "/" .. (mesh.thumbnail or ("Thumbnails/" .. mesh.key .. ".jpg"))
            items[#items + 1] = string.format('{"id":%s,"n":%s,"c":%s,"g":%s,"k":%s,"t":%s,"e":0}',
                JsonString(id), JsonString(mesh.key), JsonString(path),
                JsonString(melee and (melee_groups[id] or "Sabres") or mesh.category or ""), melee and '"Arme"' or '"Prop"', JsonString(thumb))
        end

        -- Skeletal meshes: characters (equippable) and weapons
        local ok, skeletals = pcall(Assets.GetSkeletalMeshes, path)
        if ok and skeletals then
            for _, mesh in pairs(skeletals) do
                local id = path .. "::" .. mesh.key
                local weapon = IsWeaponCategory(mesh.category)
                local thumb = "assets://" .. path .. "/" .. (mesh.thumbnail or ("Thumbnails/" .. mesh.key .. ".jpg"))
                items[#items + 1] = string.format('{"id":%s,"n":%s,"c":%s,"g":%s,"k":%s,"t":%s,"e":%d}',
                    JsonString(id), JsonString(mesh.key), JsonString(path), JsonString(mesh.category or ""),
                    weapon and '"Arme"' or '"Modèle"', JsonString(thumb),
                    (not weapon and CreatorModels and CreatorModels[id]) and 1 or 0)
            end
        end
    end
    -- Équipement tridimensionnel (package odm-gear) : équipé depuis l'onglet Arme
    items[#items + 1] = '{"id":"odm-gear::ODM","n":"ODM Gear - Equipement tridimensionnel","c":"odm-gear","g":"Equipement","k":"Arme","t":"","e":0}'
    -- Entités spéciales du mode Kimetsu RP, placées manuellement par l'administrateur.
    items[#items + 1] = '{"id":"kimetsu-pandora::selection_reroll","n":"Sélection re-roll (Yushiro)","c":"kimetsu-pandora","g":"Entités","k":"Entité","t":"","e":0}'
    return "[" .. table.concat(items, ",") .. "]"
end

-- Game language (e.g. "fr", "en-US"); the menu falls back to English when it has no translation.
local function SendSettings()
    local ok, language = pcall(function() return Client.GetLocalization() end)
    menu:CallEvent("Settings", string.format('{"toggleKey":%s,"removeKey":%s,"language":%s}',
        JsonString(Config.ToggleKey), JsonString(Config.RemoveKey), JsonString(ok and language or "en")))
end

local function SetOpen(state)
    is_open = state
    menu:SetVisibility(state and WidgetVisibility.Visible or WidgetVisibility.Hidden)
    Input.SetMouseEnabled(state)
    if state then
        if not catalog_json then
            catalog_json = BuildCatalog()
            SendSettings()
            Console.Log("[props-menu] catalog built (" .. #catalog_json .. " characters)")
            menu:CallEvent("Catalog", catalog_json)
        end
        menu:SetFocus()
    else
        menu:RemoveFocus()
    end
end

-- Removes the prop under the crosshair (the server checks who owns it).
local function RemoveAimed()
    local viewport = Viewport.DeprojectScreenToWorld(Viewport.GetViewportSize() / 2)
    local start_location = viewport.Position + viewport.Direction * 50
    local end_location = viewport.Position + viewport.Direction * 5000
    local channels = CollisionChannel.WorldStatic | CollisionChannel.WorldDynamic | CollisionChannel.PhysicsBody | CollisionChannel.Vehicle
    local ignored = { Client.GetLocalPlayer():GetControlledCharacter() }
    local result = Trace.LineSingle(start_location, end_location, channels, TraceMode.ReturnEntity | TraceMode.TraceOnlyVisibility, ignored)
    if result.Success and result.Entity then
        Events.CallRemote("PropsMenu:RemoveAimed", Reliability.Reliable, result.Entity)
    end
end

menu:Subscribe("Spawn", function(kind, asset)
    Events.CallRemote("PropsMenu:Spawn", Reliability.Reliable, kind, asset)
end)

menu:Subscribe("Undo", function()
    Events.CallRemote("PropsMenu:Undo", Reliability.Reliable)
end)

menu:Subscribe("Clear", function()
    Events.CallRemote("PropsMenu:Clear", Reliability.Reliable)
end)

menu:Subscribe("RequestHistory", function()
    Events.CallRemote("PropsMenu:RequestHistory", Reliability.Reliable)
end)

menu:Subscribe("ClearHistory", function()
    Events.CallRemote("PropsMenu:ClearHistory", Reliability.Reliable)
end)

menu:Subscribe("Close", function()
    SetOpen(false)
end)

Events.SubscribeRemote("PropsMenu:History", function(json)
    menu:CallEvent("History", json)
end)

Input.Subscribe("KeyPress", function(key_name)
    if key_name == Config.ToggleKey then
        SetOpen(not is_open)
    elseif key_name == Config.RemoveKey and not is_open then
        RemoveAimed()
    end
end)
