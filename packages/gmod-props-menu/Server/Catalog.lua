-- Builds the catalog from the Asset Packs installed on whatever server runs this package.
-- Each Assets/<pack>/Assets.toml is read at startup, so nothing is hardcoded.

-- Assets.toml section -> kind used by Server/Index.lua, and the label shown on the card
local SECTION_KINDS = {
    static_meshes = { kind = "prop", label = "Prop" },
    skeletal_meshes = { kind = "model", label = "Modèle" },
}

Package.Require("CreatorModels.lua")

PropCatalog = {}

local function Escape(text)
    return (text:gsub('\\', '\\\\'):gsub('"', '\\"'))
end

local function ReadPack(path)
    local pack = path:match("([^/\\]+)[/\\]Assets%.toml$")
    if not pack then return end

    local content = File(path):Read()
    local section

    for line in content:gmatch("[^\r\n]+") do
        local name = line:match("^%s*%[assets%.([%w_]+)%]%s*$")
        if name then
            section = SECTION_KINDS[name] and name or nil
        elseif line:match("^%s*%[") then
            section = nil
        elseif section then
            local key = line:match('^%s*([%w_]+)%s*=%s*"')
            if key then
                local info = SECTION_KINDS[section]
                PropCatalog[#PropCatalog + 1] = {
                    name = key,
                    pack = pack,
                    kind = info.kind,
                    label = info.label,
                    asset = pack .. "::" .. key,
                    creator = CreatorModels[pack .. "::" .. key] == true,
                }
            end
        end
    end
end

function BuildCatalog()
    PropCatalog = {}

    if not File.Exists("Assets") then
        Console.Warn("[props-menu] Assets folder not found, the menu will be empty")
        return
    end

    for _, path in ipairs(File.GetFiles("Assets", ".toml", -1)) do
        if path:match("Assets%.toml$") then
            ReadPack(path)
        end
    end

    table.sort(PropCatalog, function(a, b)
        if a.creator ~= b.creator then return a.creator end
        if a.pack ~= b.pack then return a.pack < b.pack end
        return a.name < b.name
    end)

    Console.Log("[props-menu] " .. #PropCatalog .. " assets loaded")
end

-- JSON sent to clients: index (used when spawning), name, pack (tab) and kind label
function CatalogJSON()
    local items = {}
    for i, entry in ipairs(PropCatalog) do
        items[#items + 1] = string.format(
            '{"i":%d,"n":"%s","c":"%s","k":"%s","e":%d}',
            i, Escape(entry.name), Escape(entry.pack), Escape(entry.label), entry.creator and 1 or 0
        )
    end
    return "[" .. table.concat(items, ",") .. "]"
end
