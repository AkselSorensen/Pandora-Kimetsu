-- Data and actions for the admin menu (!menu). The menu only sends command lines,
-- and Admin.Run checks the rank exactly like for a chat command.

local ACTIONS = { "kick", "mute", "unmute", "freeze", "unfreeze", "goto", "bring", "send", "slay", "hp", "god", "ungod", "ban", "unban", "announce", "setgroup", "role", "warn", "unwarn", "closereport", "log", "reports", "rerolls", "camp" }

local function menuData(player)
    local players = {}
    for _, p in ipairs(Admin.AllPlayers()) do
        local id = Admin.IdOf(p)
        local hp
        local c = p:GetControlledCharacter()
        if c then pcall(function() hp = math.floor(c:GetHealth()) end) end
        players[#players + 1] = {
            id = p:GetID(), steam = id, name = p:GetName(), group = Admin.GroupOf(p), hp = hp,
            warns = #(Admin.Data.warns[id] or {}), muted = Admin.Muted[id] == true, frozen = Admin.Frozen[p] == true, god = Admin.Gods[p] == true,
            me = (p == player),
        }
    end
    local bans = {}
    for id, ban in pairs(Admin.Data.bans) do
        if Admin.GetBan(id) then
            bans[#bans + 1] = { id = id, name = ban.name, by = ban.by, reason = ban.reason,
                left = (ban.expires > 0) and (ban.expires - os.time()) or 0 }
        end
    end
    -- what this player may do (buttons) and, for role managers, the roles with their permissions
    local can = {}
    for _, name in ipairs(ACTIONS) do
        local cmd = Admin.Commands[name]
        if cmd then can[name] = Admin.Can(player, cmd) end
    end
    local groups = {}
    for _, g in ipairs(Admin.GroupList()) do groups[#groups + 1] = { name = g.name, rank = g.rank } end
    local roles, commands = {}, {}
    if can.role then
        local list = {}
        for name, cmd in pairs(Admin.Commands) do
            if cmd.name == name then list[#list + 1] = cmd end
        end
        table.sort(list, function(x, y) return x.name < y.name end)
        for _, cmd in ipairs(list) do commands[#commands + 1] = { name = cmd.name, help = cmd.help or "", usage = cmd.usage, default = cmd.group } end
        for _, g in ipairs(Admin.GroupList()) do
            local perms = {}
            for _, cmd in ipairs(list) do perms[cmd.name] = Admin.GroupCan(g, cmd) end
            roles[#roles + 1] = { name = g.name, rank = g.rank, color = g.color, builtin = g.builtin, perms = perms, limit = g.limit or -1 }
        end
    end
    -- journal (newest first) and reports (open first), only for the players allowed to use them
    local journal, reports = {}, {}
    if can.log then
        for i = #Admin.LogList, math.max(1, #Admin.LogList - 299), -1 do
            local e = Admin.LogList[i]
            journal[#journal + 1] = { t = e.t, who = e.who, id = e.id, msg = e.msg }
        end
    end
    if can.reports then
        for i = #Admin.Data.reports, 1, -1 do
            local r = Admin.Data.reports[i]
            reports[#reports + 1] = { n = r.n, from = r.from, target = r.target, reason = r.reason, at = r.at, open = r.open }
        end
    end
    return Admin.Encode({ players = players, bans = bans, log = journal, reports = reports, can = can, groups = groups, roles = roles, commands = commands,
        rank = Admin.RankOf(player), group = Admin.GroupOf(player) })
end

local function send(player)
    Events.CallRemote("Admin:Data", player, Reliability.Reliable, menuData(player))
end

Events.SubscribeRemote("Admin:Request", function(player)
    if not Admin.Can(player, Admin.Commands.menu) then return end
    send(player)
end)

Events.SubscribeRemote("Admin:Do", function(player, line)
    if type(line) ~= "string" or #line > 300 then return end
    local name = line:match("^%s*(%S+)")
    local allowed = false
    for _, a in ipairs(ACTIONS) do if a == name then allowed = true end end
    if not allowed then return end
    Admin.Run(player, line)
    send(player)
end)

Admin.RegisterCommand({ name = "menu", group = "operator", help = "opens the admin menu", fn = function(caller)
    if not caller then Admin.Reply(caller, "The menu is only available in game.") return end
    Events.CallRemote("Admin:Open", caller, Reliability.Reliable)
    send(caller)
end })
