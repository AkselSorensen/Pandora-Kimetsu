-- Lets other packages (pandora-store) reward a player by Steam ID, online or not.
--   Events.Call("Cases:GiveCredits", steam_id, amount, name)
--   Events.Call("Cases:GiveEntry", steam_id, kind, ref, amount, name)   kind = "case" | "key" | "item"
local function refresh(steam, text)
    local player = Cases.Online(steam)
    if not player then return end
    Cases.Notify(player, text, "ok")
    Cases.SendData(player)
end

Events.Subscribe("Cases:GiveCredits", function(steam, amount, name)
    steam, amount = tostring(steam or ""), math.floor(tonumber(amount) or 0)
    if steam == "" or amount == 0 then return end
    local d = Cases.PlayerData(steam, name)
    d.credits = math.max(0, d.credits + amount)
    Cases.Save()
    refresh(steam, "+" .. amount .. " " .. CasesConfig.Currency)
end)

Events.Subscribe("Cases:GiveEntry", function(steam, kind, ref, amount, name)
    steam, ref = tostring(steam or ""), tostring(ref or "")
    if steam == "" or not Cases.CatalogOf(kind)[ref] or (kind ~= "case" and kind ~= "key" and kind ~= "item") then
        Console.Warn("[pandora-cases] Cases:GiveEntry: unknown " .. tostring(kind) .. " '" .. ref .. "'")
        return
    end
    Cases.PlayerData(steam, name)
    local n = math.max(1, math.min(100, math.floor(tonumber(amount) or 1)))
    for _ = 1, n do Cases.Give(steam, kind, ref) end
    refresh(steam, "+" .. n .. " " .. Cases.NameOf(kind, ref))
end)
