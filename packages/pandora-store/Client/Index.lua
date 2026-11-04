-- Client side of Pandora Store: the in-game store menu.
local menu = WebUI("Pandora Store", "file://UI/index.html", WidgetVisibility.Hidden)
local is_open = false

local function SetOpen(state)
    is_open = state
    menu:SetVisibility(state and WidgetVisibility.Visible or WidgetVisibility.Hidden)
    Input.SetMouseEnabled(state)
    if state then menu:SetFocus() else menu:RemoveFocus() end
end

Events.SubscribeRemote("Store:Open", function() SetOpen(true) end)
for _, name in ipairs({ "Catalog", "Me", "Code", "Bought", "Error" }) do
    Events.SubscribeRemote("Store:" .. name, function(json) menu:CallEvent(name, json) end)
end

menu:Subscribe("Buy", function(id) Events.CallRemote("Store:Buy", Reliability.Reliable, id) end)
menu:Subscribe("Close", function() SetOpen(false) end)

Input.Subscribe("KeyPress", function(key_name)
    if key_name == StoreShared.MenuKey then
        if is_open then SetOpen(false) else Events.CallRemote("Store:Request", Reliability.Reliable) end
    end
end)
