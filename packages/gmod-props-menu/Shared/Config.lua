-- Settings of the props menu. Edit these values, no other file needs to change.
local yufu = Package.Require("YufuWeapons.lua")
local melee_weapons, melee_groups = {}, {}
for _, weapon in ipairs(yufu.weapons) do
    local asset = yufu.pack .. "::SM_" .. weapon[1]
    melee_weapons[asset] = "yufu_" .. weapon[1]
    melee_groups[asset] = weapon[2]
end

PropsMenuConfig = {
    ToggleKey = "Q",              -- opens / closes the menu
    RemoveKey = "X",              -- removes the prop you are aiming at (your own props)
    MaxPropsPerPlayer = 50,       -- props a player can have in the world at the same time
    Cooldown = 0.25,              -- seconds between two spawns from the same player
    SpawnDistance = 300,          -- centimeters in front of the player
    SpawnHeight = 100,            -- lifts the prop so it does not spawn inside the ground
    HistorySize = 30,             -- entries kept per player
    SaveHistory = true,           -- remember each player's history between sessions (history.json)
    AllowRemoveOthers = false,    -- true: anyone can remove anyone's props with the remove key
    -- Melee weapons (static meshes) listed under Weapons: a click puts them in the player's hand through the game mode
    -- (local event Wakfu:EquipWeapon) instead of dropping them on the ground. asset -> weapon id of the game mode, and
    -- asset -> category shown in the menu. Built from Shared/YufuWeapons.lua (unreal_tools/gen_yufu_weapons.py).
    MeleeWeapons = melee_weapons,
    MeleeGroups = melee_groups,
}
