-- Groups, ranks and persistence (players' groups and bans are saved to a JSON file).
local Config = AdminConfig

-- Built-in groups (their permissions can be edited, they cannot be deleted). Custom roles are added by the owner.
local BUILTIN = {
    user       = { rank = 1,   color = "white"  },
    operator   = { rank = 2,   color = "green"  },
    admin      = { rank = 3,   color = "orange" },
    superadmin = { rank = 100, color = "red"    },
}
local BUILTIN_ORDER = { "user", "operator", "admin", "superadmin" }

-- users[id] = { group = "admin", name = "..." }; bans[id] = {...}
-- groups[name] = { rank = n, color = "red", perms = { command = true/false } }  (custom roles and edits of built-in ones)
Admin.Data = { users = {}, bans = {}, groups = {}, warns = {}, reports = {} }

function Admin.Load()
    if not File.Exists(Config.DataFile) then return end
    local ok, data = pcall(function() return JSON.parse(File(Config.DataFile):Read()) end)
    if ok and type(data) == "table" then
        Admin.Data.users = data.users or {}
        Admin.Data.bans = data.bans or {}
        Admin.Data.groups = data.groups or {}
        Admin.Data.warns = data.warns or {}
        Admin.Data.reports = data.reports or {}
    end
end

function Admin.Save()
    local ok, err = pcall(function()
        local file = File(Config.DataFile, true)
        file:Write(JSON.stringify(Admin.Data))
        file:Close()
    end)
    if not ok then Console.Warn("[nanos-admin] could not save data: " .. tostring(err)) end
end

-- Info of a group: { name, rank, color, builtin, perms }. Returns nil for an unknown group.
function Admin.GroupInfo(name)
    local base, stored = BUILTIN[name], Admin.Data.groups[name]
    if not base and not stored then return nil end
    stored = stored or {}
    return {
        name = name,
        rank = base and base.rank or stored.rank or 1,
        color = stored.color or (base and base.color) or "white",
        builtin = base ~= nil,
        perms = stored.perms or {},
        limit = stored.limit,        -- max props for this role (nil = props menu default)
    }
end

-- All groups sorted by rank.
function Admin.GroupList()
    local names, seen = {}, {}
    for _, n in ipairs(BUILTIN_ORDER) do names[#names + 1] = n seen[n] = true end
    for n in pairs(Admin.Data.groups) do if not seen[n] then names[#names + 1] = n end end
    local list = {}
    for _, n in ipairs(names) do list[#list + 1] = Admin.GroupInfo(n) end
    table.sort(list, function(x, y) if x.rank ~= y.rank then return x.rank < y.rank end return x.name < y.name end)
    return list
end

-- Creates or updates the stored part of a group.
local function stored(name)
    local g = Admin.Data.groups[name]
    if not g then g = { perms = {} } Admin.Data.groups[name] = g end
    g.perms = g.perms or {}
    return g
end

function Admin.CreateGroup(name, rank, color)
    local g = stored(name)
    g.rank, g.color = rank, color or "white"
    Admin.Save()
end

function Admin.DeleteGroup(name)
    Admin.Data.groups[name] = nil
    Admin.Save()
end

function Admin.SetGroupField(name, field, value)
    stored(name)[field] = value
    Admin.Save()
end

-- value: true / false, or nil to go back to the default rule
function Admin.SetPermission(name, command, value)
    stored(name).perms[command] = value
    Admin.Save()
end

-- Can this group use this command? An explicit true/false wins, otherwise the command's default minimum group applies.
function Admin.GroupCan(info, cmd)
    if info.name == "superadmin" then return true end
    local explicit = info.perms[cmd.name]
    if explicit ~= nil then return explicit end
    local need = Admin.GroupInfo(cmd.group)
    return need ~= nil and info.rank >= need.rank
end

function Admin.Can(player, cmd)
    if not player then return true end
    local info = Admin.GroupInfo(Admin.GroupOf(player))
    return info ~= nil and Admin.GroupCan(info, cmd)
end

local function isOwner(id)
    for _, owner in ipairs(Config.Owners) do
        if tostring(owner) == id then return true end
    end
    return false
end

-- Group name of a player (nil caller = server console = superadmin).
function Admin.GroupOf(player)
    if not player then return "superadmin" end
    local id = Admin.IdOf(player)
    if isOwner(id) then return "superadmin" end
    local entry = Admin.Data.users[id]
    return entry and Admin.GroupInfo(entry.group) and entry.group or Config.DefaultGroup
end

function Admin.RankOf(player)
    return Admin.GroupInfo(Admin.GroupOf(player)).rank
end

function Admin.SetGroup(id, name, group)
    if group == Config.DefaultGroup then
        Admin.Data.users[id] = nil
    else
        Admin.Data.users[id] = { group = group, name = name }
    end
    Admin.Save()
end

-- ── Bans ─────────────────────────────────────────────────────────────────────────────────────
function Admin.AddBan(id, name, seconds, reason, by)
    Admin.Data.bans[id] = {
        name = name, reason = reason or "", by = by or "console",
        at = os.time(), expires = (seconds and seconds > 0) and (os.time() + seconds) or 0,
    }
    Admin.Save()
end

function Admin.RemoveBan(id)
    local existed = Admin.Data.bans[id] ~= nil
    Admin.Data.bans[id] = nil
    if existed then Admin.Save() end
    return existed
end

-- Returns the active ban of an id (expired bans are removed).
function Admin.GetBan(id)
    local ban = Admin.Data.bans[id]
    if not ban then return nil end
    if ban.expires and ban.expires > 0 and ban.expires <= os.time() then
        Admin.RemoveBan(id)
        return nil
    end
    return ban
end

Admin.Load()
