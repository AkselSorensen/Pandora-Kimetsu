-- Server only. Get the key in the website admin panel: Serveurs > Ajouter.
StoreConfig = {
    ApiUrl = "http://localhost:3000",   -- the website address (it forwards /api to the NestJS API)
    ServerKey = "",                      -- psk_...
    PollSeconds = 15,                    -- how often the server asks for new purchases
    ChatCommands = { "!boutique", "!store", "!donate" },
    ChatPrefix = "<cyan>[Boutique]</> ",
}
