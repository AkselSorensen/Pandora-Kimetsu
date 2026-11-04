# Nanos Admin

A complete admin mod for nanos world: roles and permissions, a visual admin menu, moderation commands, a journal, warnings, reports, votes, role prefixes in chat and roleplay chat commands.

Inspired by the admin mods of other games (GMod's ULib and ULX in particular). It is written from scratch for nanos world and shares no code with them.

## Features

- **Admin menu** (`!menu` or F10): players with one-click actions, bans, announcements, journal, reports and the role editor. English and French, picked from the game language.
- **Roles and permissions**: built-in `user` < `operator` < `admin` < `superadmin`, plus as many custom roles as you want. Each role has a level (nobody can target a player of a higher level), a color and a checkbox per command. Create and edit them in the menu (Roles tab) or with `!role`.
- **Moderation**: `kick`, `ban` (with duration and reason), `unban`, `mute`, `freeze`, `god`, `slay`, `hp`, `goto`, `bring`, `send`, `setgroup`, `announce` (shown on screen, hold Alt to get the mouse and close it).
- **Journal**: who banned, kicked or spawned what, filterable by player in the menu (`!log` in chat).
- **Warnings**: `!warn <player> [reason]`; after 3 warnings (configurable) the player is kicked or banned automatically.
- **Reports**: players use `!report <player> <reason>`; admins are notified and handle them in the menu.
- **Votes**: `!vote <question> | option | option`, `!votemap <map>`, `!votekick <player>`; players answer with `!yes`, `!no` or `!v <number>`.
- **Chat**: `[Role] Name: text` in the role color, and roleplay commands `/me`, `/do`, `/ooc`, `/w` (whisper), `/s` (shout), `/pm`. Optional proximity chat.
- **Discord webhook** (optional) for admin actions, warns, reports and votes.
- **Works with Modern Props Menu** (optional): roles decide who may spawn objects or equip models, with a per-role limit.

## Setup

1. Put the `nanos-admin` folder in your server's `Packages` folder and add `nanos-admin` to the `packages` list of `Config.toml`.
2. Make yourself owner: add your Steam ID to `Owners` in `Shared/Config.lua` (owners are always superadmin), or run `admin setid <steam id> superadmin` in the server console.
3. In game, press F10 or type `!menu`.

Everyone else starts as `user` and can only use the basic commands (`!help`, `!who`, `!report`, chat commands, voting). Give roles from the menu (Group button) or with `!setgroup <player> <role>`.

All settings are in `Shared/Config.lua`: command prefixes, menu key, default role, warning limit and action, vote duration, chat prefixes, proximity chat and ranges, Discord webhook.

## Commands

Type `!help` in game to list the commands you are allowed to use, or `admin help` in the server console (the console has full rights). Commands start with `!` or `/`. Players can be targeted by part of their name, `#id`, `^` (yourself) or `*` (everyone, for commands that allow it).

Roles: `!role create <name> [level]`, `!role delete <name>`, `!role set <name> <command> on|off|default`, `!role rank`, `!role color`, `!role limit <name> <number|default>`.

## For developers

Add your own commands in a new file of the package (for example `Server/MyCommands.lua`, loaded with `Package.Require("MyCommands.lua")` from `Server/Index.lua`):

```lua
Admin.RegisterCommand({
    name = "hello", group = "user", usage = "", help = "says hello",
    fn = function(caller, args) Admin.Reply(caller, "Hello!") end,
})
```

Roles can then allow or deny it like any other command (set `log = true` to write it to the journal). Other packages can write to the journal with `Events.Call("Admin:Log", steam_id, name, text)`.

## Data

Roles, player groups, bans, warnings and reports are saved in `admin-data.json`, the journal in `admin-log.json` (both inside the package folder). Delete them to reset.

## License

MIT, see `LICENSE`.
