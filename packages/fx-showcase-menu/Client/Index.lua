local TOGGLE_KEY = "F6"
local menu = WebUI("FX Showcase", "file://UI/index.html", WidgetVisibility.Hidden)
local is_open = false
local catalog_json

local function JsonString(value)
    return '"' .. tostring(value):gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('[\r\n]', ' ') .. '"'
end

local function AddAsset(items, seen, path, asset, kind, pack_title)
    if type(asset) ~= "table" or type(asset.key) ~= "string" then return end
    local id = path .. "::" .. asset.key
    if seen[id] then return end
    seen[id] = true
    items[#items + 1] = string.format(
        '{"id":%s,"name":%s,"pack":%s,"type":%s,"category":%s}',
        JsonString(id), JsonString(asset.key), JsonString(pack_title or path),
        JsonString(kind), JsonString(asset.category or "")
    )
end

local function BuildCatalog()
    local items, seen = {}, {}
    for _, pack in pairs(Assets.GetAssetPacks()) do
        local path = pack.Path
        if type(path) == "string" then
            local title = pack.Title or pack.title or path

            local ok_particles, particles = pcall(Assets.GetParticles, path)
            if ok_particles and type(particles) == "table" then
                for _, asset in pairs(particles) do
                    AddAsset(items, seen, path, asset, "particle", title)
                end
            end

            local ok_meshes, meshes = pcall(Assets.GetStaticMeshes, path)
            if ok_meshes and type(meshes) == "table" then
                for _, asset in pairs(meshes) do
                    if FXShowcase.IsEffectMesh(path, asset) then
                        AddAsset(items, seen, path, asset, "mesh", title)
                    end
                end
            end
        end
    end

    table.sort(items, function(a, b) return a:lower() < b:lower() end)
    return "[" .. table.concat(items, ",") .. "]", #items
end

local function SetOpen(state)
    is_open = state
    menu:SetVisibility(state and WidgetVisibility.Visible or WidgetVisibility.Hidden)
    Input.SetMouseEnabled(state)
    if state then
        if not catalog_json then
            local ok, json, count = pcall(BuildCatalog)
            if not ok then
                Console.Warn("[fx-showcase] could not build the effects catalog: " .. tostring(json))
                return
            end
            catalog_json = json
            menu:CallEvent("Catalog", catalog_json)
            Console.Log("[fx-showcase] catalog ready (" .. tostring(count) .. " entries)")
        end
        menu:SetFocus()
    else
        menu:RemoveFocus()
    end
end

menu:Subscribe("Spawn", function(asset)
    Events.CallRemote("FXShowcase:Spawn", Reliability.Reliable, asset)
end)

menu:Subscribe("Clear", function()
    Events.CallRemote("FXShowcase:Clear", Reliability.Reliable)
end)

menu:Subscribe("Close", function()
    SetOpen(false)
end)

Events.SubscribeRemote("FXShowcase:Notice", function(text)
    menu:CallEvent("Notice", JsonString(text))
end)

Input.Subscribe("KeyPress", function(key_name)
    if key_name == TOGGLE_KEY then SetOpen(not is_open) end
end)
