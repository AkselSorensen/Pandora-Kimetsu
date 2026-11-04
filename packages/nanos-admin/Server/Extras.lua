-- Action journal, warnings, reports, votes and the link with the props menu.
local Config = AdminConfig
local function tag(name) return "<cyan>" .. name .. "</>" end
local function say(caller, text) Admin.Reply(caller, text) end

-- ── Action journal ───────────────────────────────────────────────────────────────────────────
Admin.LogList = {}   -- oldest first: { t, who, id, msg }
local log_dirty = false

local function loadLog()
    if not File.Exists(Config.LogFile) then return end
    local ok, data = pcall(function() return JSON.parse(File(Config.LogFile):Read()) end)
    if ok and type(data) == "table" then Admin.LogList = data end
end

local function saveLog()
    log_dirty = false
    local ok, err = pcall(function()
        local file = File(Config.LogFile, true)
        file:Write(JSON.stringify(Admin.LogList))
        file:Close()
    end)
    if not ok then Console.Warn("[nanos-admin] could not save the journal: " .. tostring(err)) end
end

-- Posts a line to the Discord webhook (if configured). Never breaks the server when the request fails.
function Admin.Discord(text)
    local url = Config.DiscordWebhook
    if not url or url == "" then return end
    local host, path = url:match("^(https?://[^/]+)(/.*)$")
    if not host then return end
    local body = Admin.Encode({ content = tostring(text):sub(1, 1800), username = "Nanos Admin" })
    local ok, err = pcall(function()
        HTTP.RequestAsync(host, path, HTTPMethod.POST, body, "application/json")
    end)
    if not ok then Console.Warn("[nanos-admin] Discord webhook failed: " .. tostring(err)) end
end

-- who: a player, or nil for the console. Written to disk a few seconds later (not on every entry).
function Admin.Log(who, msg, name, id, quiet)
    local entry = { t = os.time(), who = name or (who and who:GetName()) or "Console", id = id or (who and Admin.IdOf(who)) or "console", msg = tostring(msg) }
    table.insert(Admin.LogList, entry)
    while #Admin.LogList > (Config.LogSize or 500) do table.remove(Admin.LogList, 1) end
    if not quiet then Admin.Discord("**" .. entry.who .. "**: " .. entry.msg) end
    if not log_dirty then
        log_dirty = true
        Timer.SetTimeout(saveLog, 5000)
    end
end

loadLog()

-- Other packages (the props menu) report what players do: Events.Call("Admin:Log", steam_id, name, text)
Events.Subscribe("Admin:Log", function(id, name, text)
    Admin.Log(nil, text, tostring(name), tostring(id), true)
end)

Admin.RegisterCommand({ name = "log", group = "admin", usage = "[player]", help = "shows the latest journal entries (the menu has the full journal)", fn = function(caller, args)
    local filter = args[1] and args[1]:lower()
    local shown = 0
    for i = #Admin.LogList, 1, -1 do
        local e = Admin.LogList[i]
        if not filter or e.who:lower():find(filter, 1, true) or e.msg:lower():find(filter, 1, true) then
            say(caller, "<gray>" .. os.date("%H:%M", e.t) .. "</> " .. tag(e.who) .. " " .. e.msg)
            shown = shown + 1
            if shown >= 10 then break end
        end
    end
    if shown == 0 then say(caller, "Nothing in the journal.") end
end })

Package.Subscribe("Unload", function() if log_dirty then saveLog() end end)

-- ── Link with the props menu: roles decide who may spawn objects / equip models ────────────────
Admin.RegisterCommand({ name = "props", group = "user", help = "role permission: spawn objects and weapons from the props menu (Q)", fn = function(caller)
    say(caller, "Open the props menu with the key set in its config (Q by default).")
end })
Admin.RegisterCommand({ name = "models", group = "user", help = "role permission: equip models from the props menu", fn = function(caller)
    say(caller, "Open the props menu and pick a model in the Models tab.")
end })

function Admin.PushPerms(player)
    local info = Admin.GroupInfo(Admin.GroupOf(player))
    if not info then return end
    Events.Call("Admin:Perms", Admin.IdOf(player), Admin.GroupCan(info, Admin.Commands.props),
        Admin.GroupCan(info, Admin.Commands.models), info.limit or -1)
end

function Admin.PushAllPerms()
    for _, p in ipairs(Admin.AllPlayers()) do Admin.PushPerms(p) end
end

-- Any change to groups, roles or permissions is saved, so push the new permissions at the same time.
local baseSave = Admin.Save
function Admin.Save()
    baseSave()
    Admin.PushAllPerms()
end

Events.Subscribe("PropsMenu:Ready", Admin.PushAllPerms)
Player.Subscribe("Spawn", function(player) Admin.PushPerms(player) end)
Admin.PushAllPerms()

-- ── Warnings ─────────────────────────────────────────────────────────────────────────────────
local function warnsOf(id)
    local list = Admin.Data.warns[id]
    if not list then list = {} Admin.Data.warns[id] = list end
    return list
end

Admin.RegisterCommand({ log = true, name = "warn", group = "operator", usage = "<player> [reason]", help = "gives a warning; after " .. tostring(Config.WarnLimit) .. " the player is kicked or banned automatically", fn = function(caller, args)
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = false })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    local p = targets[1]
    local reason = table.concat(args, " ", 2)
    local id = Admin.IdOf(p)
    local list = warnsOf(id)
    table.insert(list, { by = Admin.NameOf(caller), reason = reason, at = os.time(), name = p:GetName() })
    Admin.Save()
    local limit = Config.WarnLimit or 3
    Admin.Broadcast(tag(Admin.NameOf(caller)) .. " warned " .. tag(p:GetName()) .. " (" .. #list .. "/" .. limit .. ")" .. (reason ~= "" and (": " .. reason) or ""))
    if #list >= limit then
        Admin.Data.warns[id] = nil
        Admin.Save()
        local why = "Too many warnings (" .. limit .. ")"
        Admin.Log(nil, "automatic " .. Config.WarnAction .. " of " .. p:GetName() .. " after " .. limit .. " warnings", "Warn system", "system")
        if Config.WarnAction == "ban" then
            Admin.AddBan(id, p:GetName(), Config.WarnBanSeconds or 3600, why, "warn system")
        end
        Admin.Broadcast(tag(p:GetName()) .. " " .. (Config.WarnAction == "ban" and "banned" or "kicked") .. " after " .. limit .. " warnings")
        p:Kick(why)
    end
end })

Admin.RegisterCommand({ name = "warns", group = "operator", usage = "<player>", help = "lists the warnings of a player", fn = function(caller, args)
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = false, ignore_rank = true })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    local list = Admin.Data.warns[Admin.IdOf(targets[1])] or {}
    say(caller, tag(targets[1]:GetName()) .. ": " .. #list .. "/" .. (Config.WarnLimit or 3) .. " warnings")
    for i, w in ipairs(list) do say(caller, i .. ". " .. (w.reason ~= "" and w.reason or "-") .. " <gray>(" .. w.by .. ")</>") end
end })

Admin.RegisterCommand({ log = true, name = "unwarn", aliases = { "clearwarns" }, group = "admin", usage = "<player>", help = "removes all the warnings of a player", fn = function(caller, args)
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = false, ignore_rank = true })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    Admin.Data.warns[Admin.IdOf(targets[1])] = nil
    Admin.Save()
    say(caller, "Warnings of " .. targets[1]:GetName() .. " removed")
end })

-- ── Reports ──────────────────────────────────────────────────────────────────────────────────
local last_report = {}

Admin.RegisterCommand({ log = true, name = "report", group = "user", usage = "<player> <reason>", help = "reports a player to the admins", fn = function(caller, args)
    if not caller then say(caller, "Only players can send reports.") return end
    local reason = table.concat(args, " ", 2)
    if reason == "" then say(caller, "<red>Usage: !report <player> <reason></>") return end
    local now = os.time()
    if last_report[caller] and now - last_report[caller] < (Config.ReportCooldown or 30) then
        say(caller, "<red>Wait a few seconds before sending another report.</>") return
    end
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = false, ignore_rank = true })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    last_report[caller] = now
    local reports = Admin.Data.reports
    local number = (reports[#reports] and reports[#reports].n or 0) + 1
    table.insert(reports, { n = number, from = caller:GetName(), fromId = Admin.IdOf(caller), target = targets[1]:GetName(),
        targetId = Admin.IdOf(targets[1]), reason = reason:sub(1, 200), at = now, open = true })
    while #reports > 200 do table.remove(reports, 1) end
    Admin.Save()
    say(caller, "<green>Report #" .. number .. " sent to the admins.</>")
    for _, p in ipairs(Admin.AllPlayers()) do
        if p ~= caller and Admin.Can(p, Admin.Commands.reports) then
            say(p, "<orange>[Report #" .. number .. "]</> " .. tag(caller:GetName()) .. " → " .. tag(targets[1]:GetName()) .. ": " .. reason:sub(1, 200))
        end
    end
end })

Admin.RegisterCommand({ name = "reports", group = "operator", help = "lists the open reports", fn = function(caller)
    local count = 0
    for _, r in ipairs(Admin.Data.reports) do
        if r.open then
            count = count + 1
            say(caller, "<orange>#" .. r.n .. "</> " .. r.from .. " → " .. r.target .. ": " .. r.reason)
        end
    end
    if count == 0 then say(caller, "No open reports.") end
end })

Admin.RegisterCommand({ log = true, name = "closereport", group = "operator", usage = "<number>", help = "closes a report", fn = function(caller, args)
    local n = tonumber(args[1])
    for _, r in ipairs(Admin.Data.reports) do
        if r.n == n then r.open = false Admin.Save() say(caller, "Report #" .. n .. " closed") return end
    end
    say(caller, "<red>Unknown report number.</>")
end })

-- ── Votes ────────────────────────────────────────────────────────────────────────────────────
-- !vote <question> | <option 1> | <option 2> ...   (no options = yes / no)   !votemap <map>   !votekick <player>
-- Players answer with !yes, !no or !v <number>.
local vote = nil
local vote_id = 0

local function finishVote(id)
    if not vote or vote.id ~= id then return end
    local current = vote
    vote = nil
    local counts = {}
    for i = 1, #current.options do counts[i] = 0 end
    for _, choice in pairs(current.votes) do counts[choice] = counts[choice] + 1 end
    local best, bestCount, tie = 1, -1, false
    for i, c in ipairs(counts) do
        if c > bestCount then best, bestCount, tie = i, c, false elseif c == bestCount then tie = true end
    end
    local summary = {}
    for i, o in ipairs(current.options) do summary[#summary + 1] = o .. ": " .. counts[i] end
    if bestCount <= 0 then
        Admin.Broadcast("<orange>[Vote]</> nobody voted, '" .. current.question .. "' is cancelled.")
        return
    end
    Admin.Broadcast("<orange>[Vote]</> " .. current.question .. " → " .. table.concat(summary, " | "))
    if tie then Admin.Broadcast("<orange>[Vote]</> tie, nothing happens.") return end
    if current.onResult then current.onResult(best, counts) end
end

local function startVote(caller, question, options, onResult)
    if vote then say(caller, "<red>A vote is already running (!cancelvote to stop it).</>") return end
    vote_id = vote_id + 1
    vote = { id = vote_id, question = question, options = options, votes = {}, onResult = onResult }
    local labels = {}
    for i, o in ipairs(options) do labels[#labels + 1] = "<cyan>" .. i .. "</> " .. o end
    local seconds = Config.VoteSeconds or 30
    Admin.Broadcast("<orange>[Vote]</> " .. question .. "  " .. table.concat(labels, "   ") .. "   <gray>(!yes / !no or !v <number>, " .. seconds .. "s)</>")
    Events.BroadcastRemote("Admin:Announce", Reliability.Reliable, question .. "  —  " .. table.concat(options, " / "), "Vote")
    local id = vote_id
    Timer.SetTimeout(function() finishVote(id) end, seconds * 1000)
end

local function castVote(caller, choice)
    if not caller then say(caller, "Only players can vote.") return end
    if not vote then say(caller, "<red>No vote is running.</>") return end
    if not choice or not vote.options[choice] then say(caller, "<red>Choose a number between 1 and " .. #vote.options .. ".</>") return end
    vote.votes[Admin.IdOf(caller)] = choice
    say(caller, "You voted <cyan>" .. vote.options[choice] .. "</>")
end

Admin.RegisterCommand({ log = true, name = "vote", group = "admin", usage = "<question> [| option | option ...]", help = "starts a vote (yes/no, or custom options separated by |)", fn = function(caller, args)
    local parts = {}
    for piece in (table.concat(args, " ") .. "|"):gmatch("([^|]*)|") do
        local trimmed = piece:match("^%s*(.-)%s*$")
        if trimmed ~= "" then parts[#parts + 1] = trimmed end
    end
    if #parts == 0 then say(caller, "<red>Usage: !vote <question> | <option 1> | <option 2></>") return end
    local question = table.remove(parts, 1)
    if #parts == 0 then parts = { "Yes", "No" } end
    if #parts > 6 then say(caller, "<red>6 options at most.</>") return end
    startVote(caller, question, parts, nil)
end })

Admin.RegisterCommand({ log = true, name = "votemap", group = "admin", usage = "<map>", help = "starts a yes/no vote to change the map", fn = function(caller, args)
    local map = args[1]
    if not map then say(caller, "<red>Usage: !votemap <map></>") return end
    startVote(caller, "Change the map to " .. map .. "?", { "Yes", "No" }, function(best)
        if best ~= 1 then Admin.Broadcast("<orange>[Vote]</> the map stays the same.") return end
        local ok, err = pcall(function() Server.ChangeMap(map) end)
        if not ok then
            Admin.Broadcast("<red>[Vote]</> the vote passed but the map could not be changed automatically.")
            Console.Warn("[nanos-admin] map change failed: " .. tostring(err))
        end
    end)
end })

Admin.RegisterCommand({ log = true, name = "votekick", group = "operator", usage = "<player>", help = "starts a yes/no vote to kick a player", fn = function(caller, args)
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = false })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    local p = targets[1]
    startVote(caller, "Kick " .. p:GetName() .. "?", { "Yes", "No" }, function(best)
        if best == 1 then
            Admin.Broadcast(tag(p:GetName()) .. " was kicked by vote")
            pcall(function() p:Kick("Kicked by vote") end)
        else
            Admin.Broadcast("<orange>[Vote]</> " .. p:GetName() .. " stays.")
        end
    end)
end })

Admin.RegisterCommand({ log = true, name = "cancelvote", group = "operator", help = "cancels the running vote", fn = function(caller)
    if not vote then say(caller, "No vote is running.") return end
    vote = nil
    Admin.Broadcast("<orange>[Vote]</> cancelled by " .. Admin.NameOf(caller))
end })

Admin.RegisterCommand({ name = "v", group = "user", usage = "<number>", help = "votes in the running vote", fn = function(caller, args) castVote(caller, tonumber(args[1])) end })
Admin.RegisterCommand({ name = "yes", group = "user", help = "votes yes (option 1)", fn = function(caller) castVote(caller, 1) end })
Admin.RegisterCommand({ name = "no", group = "user", help = "votes no (option 2)", fn = function(caller) castVote(caller, 2) end })

-- ── Roleplay chat ────────────────────────────────────────────────────────────────────────────
-- /me /do /ooc /w (whisper) /s (shout) /pm. With Config.LocalChat the normal chat is also limited to ChatRange.
local function clean(t) return (tostring(t):gsub("<", "‹")) end

local function distance(a, b)
    local ca, cb = a:GetControlledCharacter(), b:GetControlledCharacter()
    if not ca or not cb then return math.huge end
    local la, lb = ca:GetLocation(), cb:GetLocation()
    local dx, dy, dz = la.X - lb.X, la.Y - lb.Y, la.Z - lb.Z
    return math.sqrt(dx * dx + dy * dy + dz * dz)
end

-- Sends `text` to everyone within `range` of `speaker` (range nil = everyone).
function Admin.SayNear(speaker, range, text)
    for _, p in ipairs(Admin.AllPlayers()) do
        if not range or p == speaker or distance(speaker, p) <= range then
            Chat.SendMessage(p, text)
        end
    end
end
Admin.Distance = distance

local function needText(caller, args, usage)
    if not caller then say(caller, "Only players can use this.") return nil end
    local text = table.concat(args, " ")
    if text == "" then say(caller, "<red>Usage: " .. usage .. "</>") return nil end
    return clean(text)
end

Admin.RegisterCommand({ name = "me", group = "user", usage = "<action>", help = "describes what your character does", fn = function(caller, args)
    local text = needText(caller, args, "/me <action>")
    if text then Admin.SayNear(caller, Config.ChatRange, "<orange>* " .. clean(caller:GetName()) .. " " .. text .. "</>") end
end })

Admin.RegisterCommand({ name = "do", group = "user", usage = "<description>", help = "describes the scene or the result of an action", fn = function(caller, args)
    local text = needText(caller, args, "/do <description>")
    if text then Admin.SayNear(caller, Config.ChatRange, "<cyan>* " .. text .. " (" .. clean(caller:GetName()) .. ")</>") end
end })

Admin.RegisterCommand({ name = "ooc", group = "user", usage = "<message>", help = "out-of-character message heard by everyone", fn = function(caller, args)
    local text = needText(caller, args, "/ooc <message>")
    if text then Admin.SayNear(caller, nil, "<gray>[OOC] " .. clean(caller:GetName()) .. ": " .. text .. "</>") end
end })

Admin.RegisterCommand({ name = "w", aliases = { "whisper" }, group = "user", usage = "<message>", help = "whispers to the players very close to you", fn = function(caller, args)
    local text = needText(caller, args, "/w <message>")
    if text then Admin.SayNear(caller, Config.WhisperRange, "<gray>" .. clean(caller:GetName()) .. " whispers: " .. text .. "</>") end
end })

Admin.RegisterCommand({ name = "s", aliases = { "shout" }, group = "user", usage = "<message>", help = "shouts, heard from far away", fn = function(caller, args)
    local text = needText(caller, args, "/s <message>")
    if text then Admin.SayNear(caller, Config.ShoutRange, "<red>" .. clean(caller:GetName()) .. " shouts: " .. text .. "</>") end
end })

Admin.RegisterCommand({ name = "pm", aliases = { "msg" }, group = "user", usage = "<player> <message>", help = "private message", fn = function(caller, args)
    if not caller then say(caller, "Only players can use this.") return end
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = false, ignore_rank = true })
    if not targets then say(caller, "<red>" .. err .. "</>") return end
    local text = clean(table.concat(args, " ", 2))
    if text == "" then say(caller, "<red>Usage: /pm <player> <message></>") return end
    Chat.SendMessage(targets[1], "<green>[PM from " .. clean(caller:GetName()) .. "]</> " .. text)
    say(caller, "<green>[PM to " .. clean(targets[1]:GetName()) .. "]</> " .. text)
end })
