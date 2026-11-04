-- Client side of Pandora Cases: shows the menu, relays its actions to the server and plays the sounds.
local menu = WebUI("Pandora Cases", "file://UI/index.html", WidgetVisibility.Hidden)
local is_open = false

local function SetOpen(state)
    is_open = state
    menu:SetVisibility(state and WidgetVisibility.Visible or WidgetVisibility.Hidden)
    Input.SetMouseEnabled(state)
    if state then
        local ok, language = pcall(function() return Client.GetLocalization() end)
        menu:CallEvent("Language", ok and tostring(language) or "en")
        menu:CallEvent("SoundPack", CasesConfig.SoundPack ~= nil and CasesConfig.SoundPack ~= "")
        menu:SetFocus()
        Events.CallRemote("Cases:Request", Reliability.Reliable)
    else
        menu:RemoveFocus()
    end
end

Events.SubscribeRemote("Cases:Open", function() SetOpen(true) end)
Events.SubscribeRemote("Cases:Data", function(json) menu:CallEvent("Data", json) end)
Events.SubscribeRemote("Cases:Opened", function(json) menu:CallEvent("Opened", json) end)
Events.SubscribeRemote("Cases:Notify", function(text, kind) menu:CallEvent("Notify", text, kind) end)
Events.SubscribeRemote("Cases:Trade", function(json) menu:CallEvent("Trade", json) end)
Events.SubscribeRemote("Cases:TradeRequest", function(id, name) menu:CallEvent("TradeRequest", id, name) end)

menu:Subscribe("Do", function(action, payload)
    Events.CallRemote("Cases:Do", Reliability.Reliable, action, payload or "{}")
end)
menu:Subscribe("Request", function() Events.CallRemote("Cases:Request", Reliability.Reliable) end)
menu:Subscribe("Close", function() SetOpen(false) end)

-- Sounds of an optional asset pack (CasesConfig.SoundPack), e.g. "assets://voidcases-content/Sounds/voidcases/".
-- Without it the menu uses its own small synthesized sounds.
menu:Subscribe("Sound", function(file)
    if not CasesConfig.SoundPack or CasesConfig.SoundPack == "" then return end
    pcall(function() Sound(Vector(), CasesConfig.SoundPack .. tostring(file):gsub("[^%w_%.]", ""), true, true, SoundType.UI, 0.8) end)
end)

Input.Subscribe("KeyPress", function(key_name)
    if key_name == CasesConfig.MenuKey then SetOpen(not is_open) end
end)
