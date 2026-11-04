# Pandora Cases

An unboxing system for nanos world: a shop with cases and keys, a CS:GO style opening animation, an inventory, a player market, gifts and an in-game editor for cases and items.

Inspired by the unboxing addons of other games. Written from scratch for nanos world: no code, models, sounds or images from any other addon.

## Features

- **Home**: popular cases, best sellers and special items picked by the admins.
- **Shop**: cases, keys and items sold directly (perma weapons too), with search, type and rarity filters; preview every case with the exact chance of each item.
- **Case limits**: purchase cooldown (daily free case...), purchase limit per player, key requirement, mystery items shown as "?".
- **Unboxing**: CS:GO style roulette (open 1, 3 or 5 cases at once with several reels), rarity colors, a 3D crate in front of the player, drops from a chosen rarity announced in the chat. The result is decided by the server.
- **Inventory**: stacked, searchable. Use credits, receive weapons, equip models (kept after respawn), perma weapons given on every spawn, sell back to the server, gift, delete.
- **Market**: sell anything to other players at your price (fee configurable). Sellers are paid and told even when offline.
- **Live trading**: send a request, both players put items and credits, chat, and the swap happens only when both are ready (any change clears ready).
- **Settings tab** (admins): edit items, cases (details, limitations, items and drop chances) and keys with a live preview; options (chat command, credits, playtime reward, crate, announces, trading, market); rarities (create, rename, recolor, delete); players' inventories (give credits or items, remove items); featured items.
- English and French.

## Sounds

The menu makes its own small sounds. To use a sound pack instead (for example your own VoidCases content converted for nanos), put the asset pack in `Assets`, add its name to `assets_requirements` in `Package.toml` and set `SoundPack` in `Shared/Config.lua` (e.g. `"assets://voidcases-content/Sounds/voidcases/"`). Files used: `case_drop.ogg` and `item_drop1_common.ogg` to `item_drop5_legendary.ogg`.

## Setup

1. Put `pandora-cases` in your server's `Packages` folder and add it to the `packages` list of `Config.toml`.
2. Add your Steam ID to `Admins` in `Shared/Config.lua`, or run `cases addadmin <steam id>` in the server console.
3. In game press **J** (or type `!cases`). The Settings tab appears for admins.

The first start creates three example cases with base nanos-world weapons and models. Data is saved in `PandoraCases/data.json` next to the server executable.

Console: `cases addadmin <steam id>`, `cases removeadmin <steam id>`, `cases credits <steam id> <amount>`.
