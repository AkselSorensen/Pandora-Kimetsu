-- Réglages du serveur RP. Tout ce qui se règle sans toucher au code vit ici.

local Config = {}

Config.Zone = "Domaine Ubuyashiki"

-- Points d'apparition au Domaine (x, y, z en centimètres).
Config.SpawnPoints = {
	{ x = -29540, y = 340, z = 502 }, -- PlayerStart de snktest1 (Unreal)
}

Config.RespawnDelay = 5 -- secondes avant réapparition après la mort

-- Les modèles .glb d'Assets/Models ne se chargent pas tels quels : Nanos World n'utilise que des
-- assets Unreal cuits, livrés dans un pack d'assets. Passer à true une fois le pack `kimetsu-pandora-assets`
-- installé dans le dossier Assets/ du serveur et ajouté à assets_requirements dans Package.toml.
Config.UseCustomModels = false

-- Expérience (XP) qui fait monter en grade (Ranks.lua) : un duel gagné contre un autre joueur ; les quêtes donnent la leur.
Config.Xp = { kill = 40 }

-- Forge des lames Nichirin (PNJ forgeron) : prix en yens d'une lame, et yens donnés à un joueur qui arrive.
Config.Forge = { cost = 100 }
Config.StartingYens = 200

-- Créateur de personnage : genres et couleurs proposés (r, g, b entre 0 et 1).
Config.Genders = { "Homme", "Femme" }
Config.FemaleModel = "nanos-world::SK_Female"
Config.Colors = {
	{ 0.88, 0.38, 0.16 },
	{ 0.09, 0.72, 0.93 },
	{ 0.31, 0.62, 0.23 },
	{ 0.42, 0.29, 0.56 },
	{ 0.99, 0.69, 0.05 },
	{ 0.78, 0.20, 0.24 },
}
Config.MaxNameLength = 16

-- Galerie du pack pandora-demonslayer : un PNJ par personnage, alignés sur l'axe X autour de x (centimètres).
-- yaw -90 : ils regardent vers -Y, donc vers les points d'apparition (y <= 800).
Config.Showcase = { x = 0, y = 1500, z = 100, spacing = 150, yaw = -90 }

-- Armes tenues en main (classe Melee), indexées par id d'objet de Items.lua : équiper l'objet dans l'emplacement
-- arme met l'arme en main. enabled = false les retire toutes (les objets restent de simples équipements).
Config.Weapons = {
	enabled = true,
	players = "katana", -- arme tenue à l'apparition tant que le joueur n'a pas équipé une autre arme ; false = aucune
	showcase = false, -- id d'arme tenue par les figurants de la galerie ; false = aucune
	npcs = { kakushi = "katana" }, -- id de PNJ (Npcs.lua) -> id d'arme
	-- Réglage commun de la prise de TOUTES les armes, à ne toucher que si elles sont toutes décalées pareil (jamais arme par arme) :
	-- { x = 0, y = 0, z = 0, pitch = 0, yaw = 0, roll = 0 }, en cm et degrés, relatif à hand_r_socket. false = aucun réglage.
	grip = false,
	list = {
		-- Pack aksel-animations (Unreal). Avec plusieurs animations, nanos world en tire une au hasard à chaque coup.
		-- A_* = séquences : nanos choisit le slot (UpperBody par défaut). AM_* = montages : le slot est celui du montage,
		-- DefaultSlot ici, alors que le squelette nanos liste UpperBody, FullBody... Essayer l'autre jeu si rien ne joue.
		katana = {
			mesh = "aksel-animations::Katana_sword",
			slot = "FullBody", -- UpperBody (défaut) n'anime que le haut du corps ; FullBody anime tout le corps
			animations = {
				"aksel-animations::A_Combo_Attack_01",
				"aksel-animations::A_Combo_Attack_02",
				"aksel-animations::A_Combo_Attack_03",
				"aksel-animations::A_Combo_Attack_04",
			},
			damage = 40,
			cooldown = 0.8, -- secondes entre deux coups
			damageStart = 0.3, -- début des dégâts après le lancement de l'animation (secondes)
			damageDuration = 0.5,
			tip = 105, -- distance poignée-pointe de la lame (cm) : là où s'accroche la traînée (Config.Vfx)
		},
		-- Arme de référence de nanos world (exemple de la doc de Melee) : marche sans nos assets.
		pied_de_biche = {
			mesh = "nanos-world::SM_Crowbar_01",
			animations = { "nanos-world::AM_Mannequin_Melee_Slash_Attack" },
			damage = 25,
			cooldown = 1.0,
			damageStart = 0.3,
			damageDuration = 0.5,
			tip = 70,
		},
	},
}

-- Sabres du pack yufu-arme-test (addon GMod [YUFU]Arme Test converti par gmod2nanos). Leur mesh est déjà orienté pour la main :
-- poignée à l'origine, lame vers +Z comme le Katana_sword de nanos (voir gmod2nanos/grip.py), donc aucune prise à régler par
-- arme. La liste vient de Shared/YufuWeapons.lua (unreal_tools/gen_yufu_weapons.py). Mêmes animations et mêmes dégâts que le
-- katana : seul le mesh change.
local yufu = Package.Require("YufuWeapons.lua")
local yufuIds = {}
for _, weapon in ipairs(yufu.weapons) do
	local def = {}
	for key, value in pairs(Config.Weapons.list.katana) do
		def[key] = value
	end
	def.mesh = yufu.pack .. "::SM_" .. weapon[1]
	def.tip = weapon[3] or def.tip -- distance poignée-pointe de la lame (cm), lue dans les glTF de la conversion
	def.handling = "SingleHandedMelee" -- pose de la main (HandlingMode) : une main, deux mains...
	local id = "yufu_" .. weapon[1]
	Config.Weapons.list[id] = def
	yufuIds[#yufuIds + 1] = id
end

-- Essai des armes : flèche droite / gauche = arme suivante / précédente de la liste (elle prime sur l'arme équipée).
-- enabled = false retire la fonction.
local cycle = { "katana" }
for _, id in ipairs(yufuIds) do
	cycle[#cycle + 1] = id
end
cycle[#cycle + 1] = "pied_de_biche"
Config.WeaponCycle = { enabled = true, previous = "Left", next = "Right", list = cycle }

-- Effets visuels des techniques (systèmes Niagara cuits depuis les packs de VFX, liste dans Shared/VfxAssets.lua, voir VfxPlan.lua).
-- enabled = false les retire ; radius = distance (cm) à laquelle un joueur voit l'effet d'une technique.
-- test : touches d'essai, nextEffect joue l'effet suivant de la banque, nextPattern change la trajectoire des traînées. À couper en production.
Config.Vfx = {
	enabled = true,
	radius = 6000,
	test = { enabled = true, nextEffect = "F9", nextPattern = "F8" },
	-- Traînée accrochée à la pointe de l'arme tenue (une Particle attachée au Melee, comme la flamme de la torche de sandbox). Chaque joueur la
	-- choisit dans un menu (touche menuKey ou bouton de l'inventaire) : « auto » = celle de sa voie (Vfx.Style), « none » = aucune, ou une
	-- traînée de la banque. defaultTip = distance poignée-pointe (cm) d'une arme sans mesure.
	weaponTrail = true,
	menuKey = "J", -- la touche J a été retirée à pandora-cases (son menu reste ouvert par !cases) ; déjà prises : K (eric...-test), F4 (pandora-store et voies), F1 à F10 (kimetsu-pandora, nanos-admin)
	-- La traînée n'est allumée que pendant un coup (événement Attack du Melee) ; alwaysOn = true la garde allumée en permanence.
	-- sizes : réglages de taille du menu (defaultSize au départ). scale = échelle du composant Niagara (la largeur du ruban est une constante
	-- des systèmes du pack : l'échelle peut ne rien y changer) ; tip = part de la distance poignée-pointe où la traînée s'accroche (plus près de
	-- la main, l'arc balayé est plus court) ; seconds = durée allumée par coup (nil = fenêtre de dégâts de l'arme : damageStart + damageDuration).
	trail = {
		defaultTip = 100,
		alwaysOn = false,
		defaultSize = "fine",
		sizes = {
			{ id = "fine", label = "Fine", scale = 0.3, tip = 0.7, seconds = 0.5 },
			{ id = "moyenne", label = "Moyenne", scale = 0.6, tip = 0.85, seconds = 0.65 },
			{ id = "normale", label = "Normale", scale = 1, tip = 0.95 },
		},
	},
}

-- Système du démon (Shared/Demon.lua, Server/Index.lua). Tous les calculs sont côté serveur ; ces valeurs sont des points de départ à équilibrer
-- par des duels de test (plan A5, A18).
Config.Demon = {
	enabled = true,
	devourKey = "H", -- touche pour dévorer une proie proche (libre dans tous les packages chargés)
	-- portée (cm), durée du geste (s), retour d'un civil dévoré (s). Pendant le geste le démon est accroupi ; animation = identifiant d'une animation
	-- jouée en boucle pendant le repas (par exemple "pack::A_..."), nil = seulement accroupi (aucune animation de repas n'existe dans les packs).
	devour = { range = 220, seconds = 3.5, civilRespawn = 90, animation = nil },
	combatSeconds = 6, -- sans coup donné ni reçu pendant ce délai, la régénération passive démarre
	-- Régénération passive : fraction des PV max par seconde. La chair l'amplifie jusqu'à (1 + fleshBoost) ; sans chair (affamé) elle tombe à hungryFactor.
	regen = { base = 0.012, fleshBoost = 1.0, hungryFactor = 0.35 },
	-- Sang : ressource des techniques. costs = coût de la technique 1 à 4 ; il remonte de perSecond.
	blood = { max = 100, perSecond = 2.5, costs = { 8, 12, 25, 40 } },
	-- Chair : jauge qui nourrit la régénération et se vide avec le temps.
	flesh = { max = 100, decayPerSecond = 0.4 },
	-- Âmes : puissance durable, par paliers. Sans repas pendant hungerSeconds, la puissance retombe d'un palier.
	-- Âmes : départ à `start` (× le facteur de la rareté du pouvoir), plafond `max`. Elles ne baissent plus avec la faim.
	souls = { start = 300, max = 5000, rarityFactor = { common = 1, rare = 1.5, epic = 2, mythic = 3, pandorium = 4 } },
	-- Paliers de puissance : seuil d'âmes, bonus de PV max, de dégâts (%) et de régénération (fraction des PV max par seconde).
	tiers = {
		{ name = "Errant affamé", souls = 0, hp = 0, damagePct = 0, regen = 0 },
		{ name = "Chasseur de nuit", souls = 500, hp = 80, damagePct = 6, regen = 0.003 },
		{ name = "Prédateur", souls = 1000, hp = 180, damagePct = 12, regen = 0.006 },
		{ name = "Seigneur de sang", souls = 1800, hp = 300, damagePct = 20, regen = 0.009 },
		{ name = "Lune de sang", souls = 2800, hp = 450, damagePct = 30, regen = 0.012 },
	},
	-- Techniques verrouillées : numéro de la technique -> palier requis.
	unlock = { [4] = 4 },
	-- Repas par jour : un démon ne dévore qu'un nombre limité de proies humaines (cadavres et civils : les sources listées dans kinds) par jour.
	-- Le maximum monte avec le grade : perRank × numéro du grade (5 au premier grade, 10 au deuxième...), ou la liste caps (numéro du grade ->
	-- maximum) pour fixer des valeurs à la main. dayLength = durée d'un jour en secondes réelles (86400 = 24 h).
	-- Repas par heure selon le grade démon : 3 au premier rang, +1 à chaque rang (rang 13 : 15).
	meals = { dayLength = 3600, perRank = 5, caps = { [1] = 3, [2] = 4, [3] = 5, [4] = 6, [5] = 7, [6] = 8, [7] = 9, [8] = 10, [9] = 11, [10] = 12, [11] = 13, [12] = 14, [13] = 15 }, kinds = { corpse = true, civil = true } },
	-- Sources de puissance. heal = fraction des PV max rendue sur le coup. corpse = le corps d'un joueur mort (voir Config.Corpses) : il reste
	-- au sol et ne coûte rien à la victime, qui est déjà revenue au Domaine ; un civil disparaît le temps de son retour ; la chasse (A7)
	-- ajoutera ses dépouilles.
	sources = {
		corpse = { flesh = 50, souls = { 8, 15 }, heal = 0.2, xp = 20 }, -- âmes : un tirage entre les deux bornes
		civil = { flesh = 40, souls = { 5, 10 }, heal = 0.15, xp = 15 },
		hunt = { flesh = 15, souls = { 2, 4 }, heal = 0.05, xp = 8 },
	},
}

-- Cadavres : un joueur qui meurt laisse son corps au sol pendant lifetime secondes et revient au Domaine dans un nouveau corps. Un démon
-- peut dévorer le corps (Config.Demon.sources.corpse). Un démon qui meurt part en cendres : son corps ne reste que si demonsLeaveBody.
Config.Corpses = {
	enabled = true,
	lifetime = 180,
	demonsLeaveBody = false,
	label = true, -- nom flottant « † nom » au-dessus du corps
}

-- Visualiseur d'animations (Client/AnimViewer.lua) : key ouvre et ferme le panneau ; enabled = false le retire.
Config.AnimViewer = { enabled = true, key = "F7" }

-- Apparences spéciales choisissables dans le créateur (nom affiché -> mesh d'un pack d'assets).
-- Le pack doit être installé dans Assets/ du serveur et compilé pour une version d'Unreal acceptée (5.7.1 à 5.7.4).
Config.Skins = {
	["Father Demon Spider"] = "pandora-demonslayer::SK_father_demon_spider",
	["Sick Male"] = "pandora-demonslayer::SK_sick_male",
	["Tengen"] = "pandora-demonslayer::SK_tengen",
	["Urami"] = "pandora-demonslayer::SK_urami",
	["Water Slayer Male"] = "pandora-demonslayer::SK_water_slayer_male",
	["Yahaba"] = "pandora-demonslayer::SK_yahaba",
	["Neponchik"] = "pandora-demonslayer::SK_neponchik",
	["Nestell"] = "pandora-demonslayer::SK_nestell",
	["Nezuko Kamado"] = "pandora-demonslayer::SK_nezuko_kamado",
	["Nier Takamori"] = "pandora-demonslayer::SK_nier_takamori",
	["Obanai"] = "pandora-demonslayer::SK_obanai",
	["Obanai Iguro"] = "pandora-demonslayer::SK_obanai_iguro",
	["Orochimaru Mikam"] = "pandora-demonslayer::SK_orochimaru_mikam",
	["Redzo Goku"] = "pandora-demonslayer::SK_redzo_goku",
	["Rock Slayer Male"] = "pandora-demonslayer::SK_rock_slayer_male",
	["Rui"] = "pandora-demonslayer::SK_rui",
	["Sabito"] = "pandora-demonslayer::SK_sabito",
	["Daki"] = "pandora-demonslayer::SK_daki",
	["Dark Slayer Female"] = "pandora-demonslayer::SK_dark_slayer_female",
	["Koinatsu"] = "pandora-demonslayer::SK_koinatsu",
	["Kokushiba"] = "pandora-demonslayer::SK_kokushiba",
	["Kotegawa"] = "pandora-demonslayer::SK_kotegawa",
	["Kyojuro Rengoku"] = "pandora-demonslayer::SK_kyojuro_rengoku",
	["Makio"] = "pandora-demonslayer::SK_makio",
	["Makomo"] = "pandora-demonslayer::SK_makomo",
	["Male Demonslayer"] = "pandora-demonslayer::SK_male_demonslayer",
	["Male Demonslayer1"] = "pandora-demonslayer::SK_male_demonslayer1",
	["Mitsuri"] = "pandora-demonslayer::SK_mitsuri",
	["Muichiro"] = "pandora-demonslayer::SK_muichiro",
	["Mukago"] = "pandora-demonslayer::SK_mukago",
	["Naho Takada"] = "pandora-demonslayer::SK_naho_takada",
	["Nakime"] = "pandora-demonslayer::SK_nakime",
	["Sister Spider"] = "pandora-demonslayer::SK_sister_spider",
	["Suma"] = "pandora-demonslayer::SK_suma",
	["Susamaru"] = "pandora-demonslayer::SK_susamaru",
	["Tamae"] = "pandora-demonslayer::SK_tamae",
	["Xaloin"] = "pandora-demonslayer::SK_xaloin",
	["Xes"] = "pandora-demonslayer::SK_xes",
	["Yasu Normokentro"] = "pandora-demonslayer::SK_yasu_normokentro",
	["Yushiro"] = "pandora-demonslayer::SK_yushiro",
	["Akaza"] = "pandora-demonslayer::SK_akaza",
	["Aoi Kanzaki"] = "pandora-demonslayer::SK_aoi_kanzaki",
	["Demon Female"] = "pandora-demonslayer::SK_demon_female",
	["Demon M"] = "pandora-demonslayer::SK_demon_m",
	["Demon M1"] = "pandora-demonslayer::SK_demon_m1",
	["Demon M2"] = "pandora-demonslayer::SK_demon_m2",
	["Demon M3"] = "pandora-demonslayer::SK_demon_m3",
	["Demon M4"] = "pandora-demonslayer::SK_demon_m4",
	["Demon M5"] = "pandora-demonslayer::SK_demon_m5",
	["Demon Male14"] = "pandora-demonslayer::SK_demon_male14",
	["Demon Male16"] = "pandora-demonslayer::SK_demon_male16",
	["Demon Male6"] = "pandora-demonslayer::SK_demon_male6",
	["Demon Male9"] = "pandora-demonslayer::SK_demon_male9",
	["Douma"] = "pandora-demonslayer::SK_douma",
	["Enmu"] = "pandora-demonslayer::SK_enmu",
	["Father"] = "pandora-demonslayer::SK_father",
	["Female Demonslayer"] = "pandora-demonslayer::SK_female_demonslayer",
	["Female Demonslayer1"] = "pandora-demonslayer::SK_female_demonslayer1",
	["Funny"] = "pandora-demonslayer::SK_funny",
	["Gekko"] = "pandora-demonslayer::SK_gekko",
	["Giyu Tomioka"] = "pandora-demonslayer::SK_giyu_tomioka",
	["Gyomei"] = "pandora-demonslayer::SK_gyomei",
	["Hantengu"] = "pandora-demonslayer::SK_hantengu",
	["Highligh"] = "pandora-demonslayer::SK_highligh",
	["Hinatsuru"] = "pandora-demonslayer::SK_hinatsuru",
	["Inflated Mice"] = "pandora-demonslayer::SK_inflated_mice",
	["Inosuke Hashibira"] = "pandora-demonslayer::SK_inosuke_hashibira",
	["Jigoro Kuwajima"] = "pandora-demonslayer::SK_jigoro_kuwajima",
	["Jigoro Student Female"] = "pandora-demonslayer::SK_jigoro_student_female",
	["Jigoro Student Male"] = "pandora-demonslayer::SK_jigoro_student_male",
	["Juststopme"] = "pandora-demonslayer::SK_juststopme",
	["Kagaya"] = "pandora-demonslayer::SK_kagaya",
	["Kaigaku"] = "pandora-demonslayer::SK_kaigaku",
	["Kamanue"] = "pandora-demonslayer::SK_kamanue",
	["Kanao"] = "pandora-demonslayer::SK_kanao",
	["Kanata Kabuyashiki"] = "pandora-demonslayer::SK_kanata_kabuyashiki",
	["Kiriya Kabuyashiki"] = "pandora-demonslayer::SK_kiriya_kabuyashiki",
	["Kisatsutai Female"] = "pandora-demonslayer::SK_kisatsutai_female",
	["Kisatsutai Male"] = "pandora-demonslayer::SK_kisatsutai_male",
	["Kiyo Terauchi"] = "pandora-demonslayer::SK_kiyo_terauchi",
	["Sakonji Urokodaki"] = "pandora-demonslayer::SK_sakonji_urokodaki",
	["Sanemi Shinazugawa"] = "pandora-demonslayer::SK_sanemi_shinazugawa",
	["Shinjuro Rengoku"] = "pandora-demonslayer::SK_shinjuro_rengoku",
}

return Config
