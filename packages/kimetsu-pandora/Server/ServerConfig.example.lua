-- Copie ce fichier en ServerConfig.lua (dans le même dossier) et remplis la clé.
-- ServerConfig.lua n'est jamais commité : il contient la clé secrète de l'API.
-- La clé doit être la même que KIMETSU_API_KEY côté server/api.
KimetsuApi = {
    ApiUrl = "http://127.0.0.1:8080",   -- adresse de l'API (server/api)
    ServerKey = "",                      -- la clé secrète, ex. une-cle-longue-et-secrete
}
