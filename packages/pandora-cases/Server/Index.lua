-- Pandora Cases: shop, cases with keys, CS:GO style unboxing, inventory, market, live trading and an in-game editor.
Cases = {}
Package.Require("Util.lua")
Package.Require("Data.lua")
Package.Require("Trade.lua")
Package.Require("Actions.lua")
Package.Require("Bridge.lua")
Console.Log("[pandora-cases] loaded, " .. (CasesConfig.MenuKey ~= "" and ("press " .. CasesConfig.MenuKey .. " in game") or "type !cases in the chat") .. " or type 'cases help' in the console")
