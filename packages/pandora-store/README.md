# pandora-store (nanos world package)

In-game side of [Pandora Store](../../Web/pandora-store/README.md): delivers website purchases and
opens the store menu (`F4`, `!boutique`, `!store`, `!donate`).

Set `ApiUrl` and `ServerKey` in `Server/ServerConfig.lua`. The key comes from the admin panel
(Serveurs). Purchases are applied even for offline players; perma weapons and groups are saved in
`PandoraStore/state.json` and come back after a restart.
