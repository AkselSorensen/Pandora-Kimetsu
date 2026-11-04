FXShowcase = {}

local WHOLE_PACKS = {
    ["breath-fx"] = true,
    ["free-magic"] = true,
    ["free-spells"] = true,
    ["scythe"] = true,
    ["sword-trail-vfx"] = true,
    ["vefects"] = true,
}

local MARKERS = {
    "effect", "vfx", "particle", "trail", "slash", "spark", "magic", "spell",
    "explosion", "impact", "aura", "beam", "fire", "flame", "lightning",
    "thunder", "blood", "shock", "burst", "smoke", "wind", "dust", "web",
    "spl_", "_spl", "ring",
}

function FXShowcase.IsEffectMesh(pack_path, mesh)
    local pack = tostring(pack_path or ""):lower()
    if WHOLE_PACKS[pack] then return true end

    local key = type(mesh) == "table" and tostring(mesh.key or "") or tostring(mesh or "")
    local category = type(mesh) == "table" and tostring(mesh.category or "") or ""
    local path = type(mesh) == "table" and tostring(mesh.path or "") or ""
    local searchable = (pack .. "/" .. key .. "/" .. category .. "/" .. path):lower()

    for _, marker in ipairs(MARKERS) do
        if searchable:find(marker, 1, true) then return true end
    end
    return false
end
