-- Live trading between two online players. Trades only live in memory: nothing moves until both
-- players have pressed Ready on the same offers, and every change to an offer clears both Ready.
local trades = {}      -- player -> trade (both players point to the same table)
local requests = {}    -- target player -> requesting player

local T = {}
Cases.TradeActions = T

local function other(trade, player) return trade.a == player and trade.b or trade.a end

local function stateFor(trade, player)
    local them = other(trade, player)
    local mine, theirs = trade.offer[player], trade.offer[them]
    local p2 = Cases.PlayerData(Cases.IdOf(them))
    local entries = {}
    for _, uid in ipairs(theirs.uids) do
        local e = Cases.FindEntry(p2, uid)
        if e then entries[#entries + 1] = e end
    end
    return Cases.Encode({ open = true, with = them:GetName(), mine = { uids = mine.uids, credits = mine.credits, ready = trade.ready[player] == true },
        theirs = { entries = entries, credits = theirs.credits, ready = trade.ready[them] == true }, chat = trade.chat })
end

local function push(trade)
    for _, pl in ipairs({ trade.a, trade.b }) do
        if pl:IsValid() then Events.CallRemote("Cases:Trade", pl, Reliability.Reliable, stateFor(trade, pl)) end
    end
end

local function close(trade, reason)
    for _, pl in ipairs({ trade.a, trade.b }) do
        trades[pl] = nil
        if pl:IsValid() then
            Events.CallRemote("Cases:Trade", pl, Reliability.Reliable, Cases.Encode({ open = false }))
            if reason then Cases.Notify(pl, reason, "info") end
        end
    end
end

function Cases.InTrade(player) return trades[player] ~= nil end

-- traderequest { to = player id }
function T.traderequest(player, p, a)
    if not Cases.Setting("TradeEnabled") then return Cases.Notify(player, "Trading is disabled", "error") end
    local target = Cases.ByNetId(a.to)
    if not target or target == player then return Cases.Notify(player, "Player not found", "error") end
    if trades[player] or trades[target] then return Cases.Notify(player, "One of you is already trading", "error") end
    requests[target] = player
    Events.CallRemote("Cases:TradeRequest", target, Reliability.Reliable, player:GetID(), player:GetName())
    Cases.Tell(target, "<yellow>" .. player:GetName() .. "</> wants to trade with you, open the cases menu (" .. (CasesConfig.MenuKey ~= "" and CasesConfig.MenuKey or "!cases in the chat") .. ")")
    Cases.Notify(player, "Trade request sent to " .. target:GetName(), "ok")
end

-- tradeaccept { from = player id }
function T.tradeaccept(player, p, a)
    local from = requests[player]
    requests[player] = nil
    if not from or not from:IsValid() or from:GetID() ~= tonumber(a.from) then return Cases.Notify(player, "This request expired", "error") end
    if trades[player] or trades[from] then return Cases.Notify(player, "One of you is already trading", "error") end
    local trade = { a = from, b = player, offer = { [from] = { uids = {}, credits = 0 }, [player] = { uids = {}, credits = 0 } }, ready = {}, chat = {} }
    trades[from], trades[player] = trade, trade
    push(trade)
end

function T.tradedecline(player, p, a)
    local from = requests[player]
    requests[player] = nil
    if from and from:IsValid() then Cases.Notify(from, player:GetName() .. " declined the trade", "info") end
end

-- tradeset { uids = { ... }, credits } : replaces what this player offers
function T.tradeset(player, p, a)
    local trade = trades[player]
    if not trade then return end
    local uids, seen = {}, {}
    for _, uid in ipairs(type(a.uids) == "table" and a.uids or {}) do
        uid = tostring(uid)
        if not seen[uid] and Cases.FindEntry(p, uid) and #uids < 24 then seen[uid] = true uids[#uids + 1] = uid end
    end
    local credits = math.max(0, math.min(p.credits, math.floor(tonumber(a.credits) or 0)))
    trade.offer[player] = { uids = uids, credits = credits }
    trade.ready = {}
    push(trade)
end

-- tradeready { ready = true | false }
function T.tradeready(player, p, a)
    local trade = trades[player]
    if not trade then return end
    trade.ready[player] = a.ready ~= false
    local them = other(trade, player)
    if not (trade.ready[player] and trade.ready[them]) then return push(trade) end
    -- both ready: check everything again, then swap
    local pa, pb = Cases.PlayerData(Cases.IdOf(trade.a)), Cases.PlayerData(Cases.IdOf(trade.b))
    local oa, ob = trade.offer[trade.a], trade.offer[trade.b]
    for _, pair in ipairs({ { pa, oa }, { pb, ob } }) do
        if pair[1].credits < pair[2].credits then trade.ready = {} push(trade) return Cases.Notify(player, "Not enough credits anymore", "error") end
        for _, uid in ipairs(pair[2].uids) do
            if not Cases.FindEntry(pair[1], uid) then trade.ready = {} push(trade) return Cases.Notify(player, "An item is no longer available", "error") end
        end
    end
    local function move(from, to, offer)
        for _, uid in ipairs(offer.uids) do table.insert(to.inv, Cases.TakeEntry(from, uid)) end
        from.credits = from.credits - offer.credits
        to.credits = to.credits + offer.credits
        Cases.CleanOwnership(from)
    end
    move(pa, pb, oa)
    move(pb, pa, ob)
    Cases.Save()
    Events.Call("Admin:Log", Cases.IdOf(trade.a), trade.a:GetName(), "traded with " .. trade.b:GetName())
    close(trade, "Trade completed")
    Cases.SendData(trade.a)
    Cases.SendData(trade.b)
end

function T.tradecancel(player, p, a)
    local trade = trades[player]
    if trade then close(trade, player:GetName() .. " cancelled the trade") end
end

-- tradechat { text }
function T.tradechat(player, p, a)
    local trade = trades[player]
    local text = tostring(a.text or ""):sub(1, 140)
    if not trade or text:match("^%s*$") then return end
    table.insert(trade.chat, { from = player:GetName(), text = text })
    while #trade.chat > 30 do table.remove(trade.chat, 1) end
    push(trade)
end

Player.Subscribe("Destroy", function(player)
    requests[player] = nil
    for target, from in pairs(requests) do if from == player then requests[target] = nil end end
    local trade = trades[player]
    if trade then close(trade, player:GetName() .. " left, trade cancelled") end
end)

-- Items offered in a trade must not leave the inventory some other way while it is open.
function Cases.Offered(player, uid)
    local trade = trades[player]
    if not trade then return false end
    for _, u in ipairs(trade.offer[player].uids) do if u == uid then return true end end
    return false
end
