-- Settings of Nanos Admin. Edit these values, no other file needs to change.
AdminConfig = {
    Prefixes = { "!", "/" },      -- chat prefixes that trigger a command
    Owners = {                    -- Steam IDs that are always superadmin (strings)
        -- "76561198000000000",
    },
    MenuKey = "F10",              -- key that opens the admin menu (also: !menu). nil = chat command only
    DefaultGroup = "user",
    DataFile = "Packages/nanos-admin/admin-data.json",   -- groups of players and bans
    MaxBanSeconds = 0,            -- 0 = no limit on ban length for admins
    AnnounceSeconds = 8,          -- how long an !announce stays on screen
    LogSize = 500,                -- entries kept in the action journal
    LogFile = "Packages/nanos-admin/admin-log.json",
    WarnLimit = 3,                -- warnings before the automatic action
    WarnAction = "kick",          -- "kick" or "ban"
    WarnBanSeconds = 3600,        -- length of the automatic ban
    ReportCooldown = 30,          -- seconds between two reports from the same player
    VoteSeconds = 30,             -- how long a vote stays open
    ChatPrefixes = true,          -- show [Role] before the name of players who have a role
    DiscordWebhook = "",          -- Discord webhook URL: admin actions, warns, reports and votes are posted there ("" = off)
    LocalChat = false,            -- true: normal chat is only heard within ChatRange (RP proximity chat)
    ChatRange = 1500,             -- normal voice range, in Unreal units (100 = 1 m)
    WhisperRange = 300,           -- /w
    ShoutRange = 4000,            -- /s
    ShowDefaultRolePrefix = false,-- also show a prefix for the default role
}
