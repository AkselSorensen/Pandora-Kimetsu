-- Built-in commands. Each one has a minimum group; ranks: user < operator < admin < superadmin.
local function say(caller, text) Admin.Reply(caller, text) end
local function tag(name) return "<cyan>" .. name .. "</>" end

local function character(player) return player:GetControlledCharacter() end

-- Runs fn(player) on every target and reports problems once.
local function forTargets(caller, args, fn, multiple)
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = multiple ~= false })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    for _, p in ipairs(targets) do fn(p) end
    return targets
end

-- ── Everyone ─────────────────────────────────────────────────────────────────────────────────
Admin.RegisterCommand({ name = "help", group = "user", help = "lists the commands you can use", fn = function(caller)
    local names = {}
    for name, cmd in pairs(Admin.Commands) do
        if cmd.name == name and Admin.Can(caller, cmd) then
            names[#names + 1] = cmd
        end
    end
    table.sort(names, function(a, b) return a.name < b.name end)
    say(caller, "<orange>Commands you can use (prefix with !):</>")
    for _, cmd in ipairs(names) do
        say(caller, tag(cmd.name) .. " " .. cmd.usage .. " - " .. (cmd.help or ""))
    end
end })

Admin.RegisterCommand({ name = "who", group = "user", help = "lists the players and their group", fn = function(caller)
    for _, p in ipairs(Admin.AllPlayers()) do
        say(caller, string.format("#%d %s <gray>[%s]</>", p:GetID(), p:GetName(), Admin.GroupOf(p)))
    end
end })

-- ── Operator ─────────────────────────────────────────────────────────────────────────────────
Admin.RegisterCommand({ log = true, name = "kick", group = "operator", usage = "<player> [reason]", help = "removes a player from the server", fn = function(caller, args)
    local reason = table.concat(args, " ", 2)
    forTargets(caller, args, function(p)
        Admin.Broadcast(tag(Admin.NameOf(caller)) .. " kicked " .. tag(p:GetName()) .. (reason ~= "" and (": " .. reason) or ""))
        p:Kick(reason ~= "" and reason or "Kicked by an admin")
    end, false)
end })

Admin.RegisterCommand({ log = true, name = "mute", group = "operator", usage = "<player>", help = "stops a player from chatting", fn = function(caller, args)
    forTargets(caller, args, function(p)
        Admin.Muted[Admin.IdOf(p)] = true
        Admin.Broadcast(tag(Admin.NameOf(caller)) .. " muted " .. tag(p:GetName()))
    end)
end })

Admin.RegisterCommand({ log = true, name = "unmute", group = "operator", usage = "<player>", help = "lets a player chat again", fn = function(caller, args)
    forTargets(caller, args, function(p)
        Admin.Muted[Admin.IdOf(p)] = nil
        Admin.Broadcast(tag(Admin.NameOf(caller)) .. " unmuted " .. tag(p:GetName()))
    end)
end })

local frozen = {}
Admin.Frozen = frozen
local function setFrozen(p, state)
    local c = character(p)
    if not c then return end
    frozen[p] = state or nil
    local ok = pcall(function() c:SetInputEnabled(not state) end)
    if not ok then pcall(function() c:SetMovementEnabled(not state) end) end
end
Admin.RegisterCommand({ log = true, name = "freeze", group = "operator", usage = "<player>", help = "blocks a player's movement", fn = function(caller, args)
    forTargets(caller, args, function(p)
        setFrozen(p, true)
        Admin.Broadcast(tag(Admin.NameOf(caller)) .. " froze " .. tag(p:GetName()))
    end)
end })
Admin.RegisterCommand({ log = true, name = "unfreeze", group = "operator", usage = "<player>", help = "releases a frozen player", fn = function(caller, args)
    forTargets(caller, args, function(p)
        setFrozen(p, false)
        Admin.Broadcast(tag(Admin.NameOf(caller)) .. " unfroze " .. tag(p:GetName()))
    end)
end })

Admin.RegisterCommand({ log = true, name = "goto", group = "operator", usage = "<player>", help = "teleports you to a player", fn = function(caller, args)
    if not caller then say(caller, "<red>Only players can use this command.</>") return end
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = false, ignore_rank = true })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    local me, them = character(caller), character(targets[1])
    if not me or not them then say(caller, "<red>No character to teleport.</>") return end
    me:SetLocation(them:GetLocation() + Vector(100, 0, 50))
end })

-- ── Admin ────────────────────────────────────────────────────────────────────────────────────
Admin.RegisterCommand({ log = true, name = "bring", group = "admin", usage = "<player>", help = "teleports a player to you", fn = function(caller, args)
    if not caller then say(caller, "<red>Only players can use this command.</>") return end
    local me = character(caller)
    if not me then return end
    forTargets(caller, args, function(p)
        local c = character(p)
        if c then c:SetLocation(me:GetLocation() + Vector(100, 0, 50)) end
    end)
end })

Admin.RegisterCommand({ log = true, name = "send", group = "admin", usage = "<player> <to>", help = "teleports a player to another", fn = function(caller, args)
    local who = Admin.FindTargets(caller, args[1], { multiple = true })
    local to = Admin.FindTargets(caller, args[2], { multiple = false, ignore_rank = true })
    if not who or not to then say(caller, "<red>Usage: !send <player> <to></>") return end
    local dest = character(to[1])
    if not dest then return end
    for _, p in ipairs(who) do
        local c = character(p)
        if c then c:SetLocation(dest:GetLocation() + Vector(100, 0, 50)) end
    end
end })

Admin.RegisterCommand({ log = true, name = "slay", group = "admin", usage = "<player>", help = "kills a player", fn = function(caller, args)
    forTargets(caller, args, function(p)
        local c = character(p)
        if c then c:SetHealth(0) end
        Admin.Broadcast(tag(Admin.NameOf(caller)) .. " slayed " .. tag(p:GetName()))
    end)
end })

Admin.RegisterCommand({ log = true, name = "hp", group = "admin", usage = "<player> <amount>", help = "sets a player's health", fn = function(caller, args)
    local amount = tonumber(args[2])
    if not amount then say(caller, "<red>Usage: !hp <player> <amount></>") return end
    forTargets(caller, args, function(p)
        local c = character(p)
        if c then c:SetHealth(amount) end
    end)
end })

local gods = {}
Admin.Gods = gods
Character.Subscribe("TakeDamage", function(self)
    local player = self:GetPlayer()
    if player and gods[player] then return false end
end)
Admin.RegisterCommand({ log = true, name = "god", group = "admin", usage = "<player>", help = "makes a player invulnerable", fn = function(caller, args)
    forTargets(caller, args, function(p)
        gods[p] = true
        Admin.Broadcast(tag(Admin.NameOf(caller)) .. " gave god mode to " .. tag(p:GetName()))
    end)
end })
Admin.RegisterCommand({ log = true, name = "ungod", group = "admin", usage = "<player>", help = "removes god mode", fn = function(caller, args)
    forTargets(caller, args, function(p) gods[p] = nil end)
end })

Admin.RegisterCommand({ log = true, name = "ban", group = "admin", usage = "<player> [time] [reason]", help = "bans a player (time like 30m, 2h, 1d, 0 = permanent)", fn = function(caller, args)
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = false })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    local seconds = Admin.ParseDuration(args[2])
    local reasonFrom = seconds and 3 or 2
    seconds = seconds or 0
    local max = AdminConfig.MaxBanSeconds
    if max > 0 and (seconds == 0 or seconds > max) and caller and Admin.RankOf(caller) < 4 then seconds = max end
    local reason = table.concat(args, " ", reasonFrom)
    local p = targets[1]
    Admin.AddBan(Admin.IdOf(p), p:GetName(), seconds, reason, Admin.NameOf(caller))
    Admin.Broadcast(tag(Admin.NameOf(caller)) .. " banned " .. tag(p:GetName()) .. " (" .. Admin.FormatDuration(seconds) .. ")" .. (reason ~= "" and (": " .. reason) or ""))
    p:Kick("Banned (" .. Admin.FormatDuration(seconds) .. ")" .. (reason ~= "" and (": " .. reason) or ""))
end })

Admin.RegisterCommand({ log = true, name = "unban", group = "admin", usage = "<steam id or name>", help = "removes a ban", fn = function(caller, args)
    local key = args[1]
    if not key then say(caller, "<red>Usage: !unban <steam id or name></>") return end
    for id, ban in pairs(Admin.Data.bans) do
        if id == key or (ban.name or ""):lower() == key:lower() then
            Admin.RemoveBan(id)
            Admin.Broadcast(tag(Admin.NameOf(caller)) .. " unbanned " .. tag(ban.name or id))
            return
        end
    end
    say(caller, "<red>No ban found for '" .. key .. "'.</>")
end })

Admin.RegisterCommand({ name = "bans", group = "admin", help = "lists the active bans", fn = function(caller)
    local n = 0
    for id, ban in pairs(Admin.Data.bans) do
        if Admin.GetBan(id) then
            n = n + 1
            local left = ban.expires > 0 and Admin.FormatDuration(ban.expires - os.time()) or "permanent"
            say(caller, string.format("%s (%s) - %s - by %s %s", ban.name or "?", id, left, ban.by or "?", ban.reason ~= "" and ("- " .. ban.reason) or ""))
        end
    end
    if n == 0 then say(caller, "No active bans.") end
end })

Admin.RegisterCommand({ log = true, name = "announce", aliases = { "say" }, group = "admin", usage = "<message>", help = "sends a highlighted message to everyone", fn = function(caller, args)
    local text = table.concat(args, " ")
    Admin.Broadcast("<orange>[Announcement]</> " .. text)
    Events.BroadcastRemote("Admin:Announce", Reliability.Reliable, text, Admin.NameOf(caller))
end })

-- ── Superadmin ───────────────────────────────────────────────────────────────────────────────
Admin.RegisterCommand({ log = true, name = "setgroup", group = "superadmin", usage = "<player> <group>", help = "changes a player's group (user, operator, admin, superadmin)", fn = function(caller, args)
    local group = args[2] and args[2]:lower()
    local info = group and Admin.GroupInfo(group)
    if not info then say(caller, "<red>Unknown group. Use !roles to list them.</>") return end
    if caller and info.rank >= Admin.RankOf(caller) and Admin.GroupOf(caller) ~= "superadmin" then
        say(caller, "<red>You cannot give a group at or above your own.</>") return
    end
    forTargets(caller, args, function(p)
        Admin.SetGroup(Admin.IdOf(p), p:GetName(), group)
        Admin.Broadcast(tag(Admin.NameOf(caller)) .. " set " .. tag(p:GetName()) .. " to " .. tag(group))
    end, false)
end })

Admin.RegisterCommand({ log = true, name = "setid", group = "superadmin", usage = "<steam id> <group>", help = "sets the group of an offline player by Steam ID", fn = function(caller, args)
    local id, group = args[1], args[2] and args[2]:lower()
    if not id or not group or not Admin.GroupInfo(group) then say(caller, "<red>Usage: !setid <steam id> <group> (see !roles)</>") return end
    Admin.SetGroup(id, id, group)
    say(caller, "Group of " .. id .. " set to " .. group)
end })

-- ── Roles (create roles and choose what each one may do) ────────────────────────────────────
local function roleLine(info)
    return string.format("<%s>%s</> (level %d)%s", info.color, info.name, info.rank, info.builtin and " [built-in]" or "")
end

Admin.RegisterCommand({ name = "roles", group = "user", help = "lists the roles", fn = function(caller)
    for _, info in ipairs(Admin.GroupList()) do say(caller, roleLine(info)) end
end })

Admin.RegisterCommand({ log = true, name = "role", group = "superadmin", usage = "create|delete|set|rank|color|limit ...", help = "manages roles: create <name> [level], delete <name>, set <name> <command> <on|off|default>, rank <name> <level>, color <name> <color>, limit <name> <props|default>", fn = function(caller, args)
    local sub, name = args[1], args[2] and args[2]:lower()
    local info = name and Admin.GroupInfo(name)
    local function fail(msg) say(caller, "<red>" .. msg .. "</>") end

    if sub == "create" then
        if not name or not name:match("^[a-z0-9_%-]+$") or #name > 24 then return fail("Role name: letters, digits, - or _ (max 24)") end
        if info then return fail("That role already exists") end
        local rank = tonumber(args[3]) or 1
        if rank < 1 or rank >= 100 then return fail("Level must be between 1 and 99") end
        Admin.CreateGroup(name, math.floor(rank), "white")
        say(caller, "Role " .. name .. " created (level " .. math.floor(rank) .. ")")
    elseif sub == "delete" then
        if not info then return fail("Unknown role") end
        if info.builtin then return fail("Built-in roles cannot be deleted") end
        Admin.DeleteGroup(name)
        say(caller, "Role " .. name .. " deleted (its members become " .. AdminConfig.DefaultGroup .. ")")
    elseif sub == "set" then
        local cmdName, value = args[3] and args[3]:lower(), args[4] and args[4]:lower()
        if not info then return fail("Unknown role") end
        if info.name == "superadmin" then return fail("Superadmin always has every permission") end
        local cmd = cmdName and Admin.Commands[cmdName]
        if not cmd then return fail("Unknown command") end
        if value ~= "on" and value ~= "off" and value ~= "default" then return fail("Use on, off or default") end
        local setting = nil           -- "default" removes the override ("x and false or nil" would lose the false)
        if value == "on" then setting = true elseif value == "off" then setting = false end
        Admin.SetPermission(name, cmd.name, setting)
        say(caller, cmd.name .. " is now " .. value .. " for " .. name)
    elseif sub == "rank" then
        if not info or info.builtin then return fail("Only custom roles have an editable level") end
        local rank = tonumber(args[3])
        if not rank or rank < 1 or rank >= 100 then return fail("Level must be between 1 and 99") end
        Admin.SetGroupField(name, "rank", math.floor(rank))
        say(caller, "Level of " .. name .. " set to " .. math.floor(rank))
    elseif sub == "limit" then
        local value = args[3] and args[3]:lower()
        if not info then return fail("Unknown role") end
        local n = tonumber(value)
        if value == "default" then
            Admin.SetGroupField(name, "limit", nil)
            say(caller, "Prop limit of " .. name .. " back to the props menu default")
        elseif n and n >= 0 then
            Admin.SetGroupField(name, "limit", math.floor(n))
            say(caller, "Prop limit of " .. name .. " set to " .. math.floor(n))
        else
            return fail("Usage: role limit <name> <number|default>")
        end
    elseif sub == "color" then
        local color = args[3] and args[3]:lower()
        if not info or not color or not color:match("^%a+$") then return fail("Usage: role color <name> <color>") end
        Admin.SetGroupField(name, "color", color)
        say(caller, "Color of " .. name .. " set to " .. color)
    else
        fail("Usage: !role create|delete|set|rank|color|limit ...")
    end
end })

-- ── Housekeeping ─────────────────────────────────────────────────────────────────────────────
-- Banned players are removed as soon as they connect.
Player.Subscribe("Spawn", function(player)
    local ban = Admin.GetBan(Admin.IdOf(player))
    if ban then
        local left = ban.expires > 0 and Admin.FormatDuration(ban.expires - os.time()) or "permanent"
        player:Kick("You are banned (" .. left .. ")" .. (ban.reason ~= "" and (": " .. ban.reason) or ""))
    end
end)

Player.Subscribe("Destroy", function(player)
    frozen[player] = nil
    gods[player] = nil
end)
