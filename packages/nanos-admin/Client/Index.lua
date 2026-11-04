-- Client side of the admin menu: shows the WebUI and relays its actions to the server.
local Config = AdminConfig

local menu = WebUI("Admin Menu", "file://UI/index.html", WidgetVisibility.Hidden)
local is_open = false

local function SetOpen(state)
    is_open = state
    menu:SetVisibility(state and WidgetVisibility.Visible or WidgetVisibility.Hidden)
    Input.SetMouseEnabled(state)
    if state then
        local ok, language = pcall(function() return Client.GetLocalization() end)
        menu:CallEvent("Language", ok and tostring(language) or "en")
        menu:SetFocus()
        Events.CallRemote("Admin:Request", Reliability.Reliable)
    else
        menu:RemoveFocus()
    end
end

Events.SubscribeRemote("Admin:Open", function() SetOpen(true) end)

Events.SubscribeRemote("Admin:Data", function(json)
    menu:CallEvent("Data", json)
end)

menu:Subscribe("Do", function(line)
    Events.CallRemote("Admin:Do", Reliability.Reliable, line)
end)

menu:Subscribe("Refresh", function()
    Events.CallRemote("Admin:Request", Reliability.Reliable)
end)

menu:Subscribe("Close", function() SetOpen(false) end)

if Config.MenuKey then
    Input.Subscribe("KeyPress", function(key_name)
        if key_name == Config.MenuKey then SetOpen(not is_open) end
    end)
end

-- On-screen announcement banner: only visible while an announcement is shown, so it never blocks the menu's clicks.
-- Hold Alt to get the mouse and click the cross to close it.
local banner = WebUI("Admin Banner", "file://UI/banner.html", WidgetVisibility.Hidden)
local banner_token = 0
local banner_shown = false

local function HideBanner()
    banner_shown = false
    banner_token = banner_token + 1
    banner:SetVisibility(WidgetVisibility.Hidden)
end

Events.SubscribeRemote("Admin:Announce", function(text, author)
    local seconds = AdminConfig.AnnounceSeconds or 8
    banner_token = banner_token + 1
    local mine = banner_token
    banner_shown = true
    banner:SetVisibility(WidgetVisibility.Visible)
    banner:CallEvent("Announce", text, author, seconds)
    Timer.SetTimeout(function()
        if mine == banner_token then HideBanner() end
    end, (seconds + 1) * 1000)
end)

banner:Subscribe("Close", HideBanner)

Input.Subscribe("KeyPress", function(key_name)
    if key_name == "LeftAlt" and banner_shown then Input.SetMouseEnabled(true) end
end)
Input.Subscribe("KeyRelease", function(key_name)
    if key_name == "LeftAlt" and not is_open then Input.SetMouseEnabled(false) end
end)
