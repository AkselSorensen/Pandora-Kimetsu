-- Command registry, target resolution and dispatch (chat "!command" and server console).
local Config = AdminConfig

Admin.Commands = {}   -- [name] = { name, group, help, usage, fn }

-- Other packages can add commands too:
--   Admin.RegisterCommand({ name = "hello", group = "user", help = "says hello", usage = "", fn = function(caller, args) ... end })
function Admin.RegisterCommand(def)
    def.group = def.group or "admin"
    def.usage = def.usage or ""
    Admin.Commands[def.name] = def
    for _, alias in ipairs(def.aliases or {}) do Admin.Commands[alias] = def end
end

local function allPlayers()
    local list = {}
    for _, p in pairs(Player.GetPairs()) do list[#list + 1] = p end
    return list
end
Admin.AllPlayers = allPlayers

-- Finds players from "*" (everyone), "^" (me), "#12" / "12" (id) or a part of a name.
-- Returns a list, or nil + error message. Players above the caller's rank are rejected.
function Admin.FindTargets(caller, token, opts)
    opts = opts or {}
    if not token or token == "" then return nil, "no player given" end
    local found = {}
    if token == "*" or token == "@all" then
        if not opts.multiple then return nil, "this command takes one player" end
        found = allPlayers()
    elseif token == "^" then
        if not caller then return nil, "the console has no player" end
        found = { caller }
    else
        local id = tonumber((token:gsub("^#", "")))
        local lower = token:lower()
        for _, p in ipairs(allPlayers()) do
            if id and p:GetID() == id then found = { p } break end
            if p:GetName():lower() == lower then found = { p } break end
            if p:GetName():lower():find(lower, 1, true) then found[#found + 1] = p end
        end
    end
    if #found == 0 then return nil, "no player matches '" .. token .. "'" end
    if #found > 1 and not opts.multiple then return nil, "several players match '" .. token .. "', be more precise" end

    local allowed = {}
    for _, p in ipairs(found) do
        -- immunity: you cannot target a player of a higher rank (yourself is always fine)
        if p == caller or opts.ignore_rank or Admin.RankOf(caller) >= Admin.RankOf(p) then
            allowed[#allowed + 1] = p
        end
    end
    if #allowed == 0 then return nil, "you cannot target that player (higher rank)" end
    return allowed
end

function Admin.NameOf(caller) return caller and caller:GetName() or "Console" end

-- Runs "command arg1 arg2 ..." as `caller` (nil = console). Returns true when the command exists.
function Admin.Run(caller, line)
    local args = Admin.SplitArgs(line)
    local name = table.remove(args, 1)
    if not name then return false end
    local cmd = Admin.Commands[name:lower()]
    if not cmd then return false end

    if not Admin.Can(caller, cmd) then
        Admin.Reply(caller, "<red>You are not allowed to use</> <cyan>" .. cmd.name .. "</>")
        return true
    end
    local ok, err = pcall(cmd.fn, caller, args)
    if ok and cmd.log then Admin.Log(caller, cmd.name .. " " .. table.concat(args, " ")) end
    if not ok then
        Admin.Reply(caller, "<red>Error:</> " .. tostring(err))
        Console.Error("[nanos-admin] command '%s' failed: %s", cmd.name, tostring(err))
    end
    return true
end

-- Chat tag colors the engine understands; anything else falls back to white.
local CHAT_COLORS = { white = true, gray = true, green = true, orange = true, red = true, yellow = true, cyan = true, blue = true }
function Admin.ChatColor(name)
    if name and CHAT_COLORS[name] then return name end
    if name == "purple" then return "blue" end
    return "white"
end

-- ── Chat ─────────────────────────────────────────────────────────────────────────────────────
Admin.Muted = {}   -- [id] = true

Chat.Subscribe("PlayerSubmit", function(text, player)
    for _, prefix in ipairs(Config.Prefixes) do
        if text:sub(1, #prefix) == prefix and #text > #prefix then
            if Admin.Run(player, text:sub(#prefix + 1)) then return false end
        end
    end
    if Admin.Muted[Admin.IdOf(player)] then
        Admin.Reply(player, "<red>You are muted.</>")
        return false
    end
    -- "[Role] Name: text" in the role's color (default role only if ShowDefaultRolePrefix), and/or proximity chat
    local group = Admin.GroupOf(player)
    local prefixed = Config.ChatPrefixes and (group ~= Config.DefaultGroup or Config.ShowDefaultRolePrefix)
    if prefixed or Config.LocalChat then
        local function clean(t) return (tostring(t):gsub("<", "‹")) end
        local line = clean(player:GetName()) .. ": " .. clean(text)
        if prefixed then
            local info = Admin.GroupInfo(group)
            line = string.format("<%s>[%s]</> ", Admin.ChatColor(info and info.color), clean(group)) .. line
        end
        if Config.LocalChat and Admin.SayNear then
            Admin.SayNear(player, Config.ChatRange, line)
        else
            Chat.BroadcastMessage(line)
        end
        return false
    end
end)

-- ── Server console: admin <command> [args] ───────────────────────────────────────────────────
Console.RegisterCommand("admin", function(...)
    local parts = { ... }
    if not Admin.Run(nil, table.concat(parts, " ")) then
        Console.Error("Unknown admin command. Type: admin help")
    end
end, "runs a Nanos Admin command as the server console", { "command", "arguments" })
