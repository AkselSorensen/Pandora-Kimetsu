-- Settings of Pandora Cases. Most options are edited in game (Settings tab, admins only) and saved on the
-- server in PandoraCases/data.json; the values below are only the defaults of the first start.
CasesConfig = {
    MenuKey = "",                -- key that opens the cases menu (empty = no key, use !cases in the chat; J belongs to the wakfu-rp trail menu)
    Currency = "Credits",        -- name of the money used in the shop
    CrateMesh = "nanos-world::SM_Crate_07",  -- default 3D crate of a case (each case can have its own)
    -- Optional sound pack (folder of .ogg). With the VoidCases content pack: "assets://voidcases-content/Sounds/voidcases/"
    -- (add "voidcases-content" to assets_requirements in Package.toml). Empty = built-in synthesized sounds.
    SoundPack = "assets://voidcases-content/Sounds/voidcases/",
    Admins = {                   -- Steam IDs allowed to edit everything (strings).
        "76561198904305680",
    },
    Defaults = {                 -- first-start values of the in-game settings
        StartCredits = 500, PlaytimeReward = 50, PlaytimeMinutes = 10, MarketFee = 0.05, MaxListings = 10,
        AnnounceFrom = "Epic", CrateInWorld = true, TradeEnabled = true, MarketEnabled = true, ChatCommand = "!cases",
    },
}

-- Rarities of the first start (edited in game afterwards). Weight = default chance when an item is added to a case.
CasesRarities = {
    { name = "Common",    color = "#9aa3b5", weight = 60 },
    { name = "Uncommon",  color = "#3fbf4f", weight = 25 },
    { name = "Rare",      color = "#3aa9d8", weight = 10 },
    { name = "Epic",      color = "#c040d8", weight = 4 },
    { name = "Legendary", color = "#e0a030", weight = 1 },
}
