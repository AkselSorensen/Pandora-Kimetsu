-- Commandes admin propres au mode Kimetsu Pandora : rerolls et changement de camp.
-- Elles envoient un événement au mode de jeu (Server/Index.lua de kimetsu-pandora), qui fait la modification.

local function say(caller, text)
    if caller and caller:IsValid() then
        pcall(function() Chat.SendMessage(caller, text) end)
    else
        print(text)
    end
end

Admin.RegisterCommand({ log = true, name = "rerolls", group = "admin", usage = "<player> <amount>",
    help = "ajoute (ou retire) des rerolls de capacité à un joueur", fn = function(caller, args)
    local amount = math.floor(tonumber(args[2]) or 0)
    if amount == 0 then
        return say(caller, "Usage : !rerolls <joueur> <nombre> (négatif pour retirer)")
    end
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = true })
    if not targets then return say(caller, err or "Joueur introuvable") end
    for _, p in ipairs(targets) do
        Events.Call("Kimetsu:Admin:GiveRerolls", p, amount)
    end
    say(caller, "Rerolls " .. (amount > 0 and "+" or "") .. amount .. " pour " .. #targets .. " joueur(s)")
end })

Admin.RegisterCommand({ log = true, name = "camp", group = "admin", usage = "<player> <slayer|demon>",
    help = "change le camp d'un joueur (pourfendeur ou démon)", fn = function(caller, args)
    local camp = args[2]
    if camp ~= "slayer" and camp ~= "demon" then
        return say(caller, "Usage : !camp <joueur> <slayer|demon>")
    end
    local targets, err = Admin.FindTargets(caller, args[1], { multiple = true })
    if not targets then return say(caller, err or "Joueur introuvable") end
    for _, p in ipairs(targets) do
        Events.Call("Kimetsu:Admin:SetCamp", p, camp)
    end
    say(caller, "Camp " .. camp .. " pour " .. #targets .. " joueur(s)")
end })
