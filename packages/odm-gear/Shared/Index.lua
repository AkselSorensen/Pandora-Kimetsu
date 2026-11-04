ODM = {
	-- Grappins
	MaxRange = 5000,          -- portée maximale (unités UE)
	MinDistance = 200,        -- sous cette longueur de câble, le grappin se détache
	AutoReel = 250,           -- le câble se raccourcit tout seul (cm/s) : on balance en se rapprochant
	ReelSpeed = 1400,         -- vitesse d'enroulement en maintenant R (cm/s)
	ReelGasPerSecond = 15,    -- gaz consommé par seconde en enroulant vite
	RopeStiffness = 12,       -- raideur du câble quand il est tendu (plus haut = plus sec)
	MaxCorrection = 3000,     -- accélération max de rappel du câble (cm/s²)

	-- Gaz (sert au boost et à l'enroulement rapide, pas aux câbles)
	GasMax = 100,
	GasRegenPerSecond = 6,
	BoostImpulse = 1100,
	BoostGasCost = 12,
	BoostSmokeDuration = 1.0,
	SmokeAsset = "nanos-world::P_Weapon_BarrelSmoke",
	SmokeScale = 3,
	SmokeInterval = 0.05,
	SmokeLifetime = 2,

	-- Lames
	SlashCooldown = 0.45,     -- secondes
	NapeRadius = 350,         -- rayon de la zone de la nuque (multiplié par l'échelle du Titan / 5)
	MinSlashSpeed = 600,      -- vitesse minimale pour trancher une nuque (cm/s)
	BladeDamage = 20,         -- dégâts sur le corps
	NapeDamage = 10000,       -- dégâts à la nuque : mort instantanée
	BladesMax = 4,            -- durabilité d'une paire de lames (nombre de coups qui touchent)
	SpareBlades = 3,          -- paires de rechange
	BladeReloadTime = 1.6,    -- secondes pour changer de lames

	-- Lances-foudre
	Spears = 3,
	SpearCooldown = 1.5,
	SpearThrowForce = 2800,
	SpearFuse = 4,            -- explose seule après ce délai (s) si elle ne touche rien
	SpearDamage = 90,         -- dégâts au centre de l'explosion (un Titan a 100 de vie)

	-- Chute
	FallSafeSpeed = 1200,     -- vitesse de chute (cm/s) en dessous de laquelle on ne se blesse pas
	FallDamagePerSpeed = 0.06,
	FallGasCost = 25,         -- le gaz amortit l'atterrissage s'il en reste assez

	-- Os de la nuque, essayés dans l'ordre (lus côté client)
	NapeMarkerSize = 0.6,     -- taille de la sphère rouge sur la nuque (à ajuster selon l'échelle du modèle)
	NapeBones = { "neck_01", "head" },

	-- Titans
	TitansEnabled = false,    -- false : aucun Titan (ni colossal) n'apparaît sur le serveur
	TitanMax = 3,
	TitanAttackCooldown = 2.0,
	TitanRegenPerTick = 1,    -- vie rendue toutes les 0,5 s aux Titans blessés
	TitanRespawnDelay = 10,   -- secondes avant qu'un Titan remplace un mort
	-- Modèle des Titans (chaque type peut avoir son propre `mesh = "pack::SK_..."`)
	TitanMesh = "aot-titan-souriant-smile-titan::SK_smilemad",

	TitanTypes = {
		{ name = "Normal",   kind = "normal",  scale = 5, speed = 1.0, damage = 35, range = 500, health = 100, weight = 4, attack_cd = 2.0 },
		{ name = "Petit",    kind = "normal",  scale = 3, speed = 1.7, damage = 20, range = 320, health = 80,  weight = 2, attack_cd = 1.5 },
		{ name = "Geant",    kind = "normal",  scale = 8, speed = 0.7, damage = 60, range = 800, health = 140, weight = 2, attack_cd = 2.5 },
		{ name = "Mangeur",  kind = "mangeur", scale = 6, speed = 0.8, damage = 0,  range = 600, health = 110, weight = 2, attack_cd = 3.0 },
		{ name = "Sauteur",  kind = "sauteur", scale = 4, speed = 1.3, damage = 40, range = 420, health = 90,  weight = 2, attack_cd = 2.0 },
		{ name = "Anormal",  kind = "anormal", scale = 5, speed = 3.2, damage = 30, range = 500, health = 120, weight = 1, attack_cd = 1.0, sprint = true },
	},

	-- Titan colossal (boss) : apparaît après quelques morts, dégage de la vapeur brûlante
	BossType = {
		name = "Colossal", kind = "colosse", scale = 8,
		mesh = "aot-armin-colossal-titan-playermodel::SK_armincolossaltitan",
		speed = 0.55, damage = 90, range = 1800,
		health = 1500, weight = 0, attack_cd = 3.0, boss = true, nape_damage = 500,
	},
	BossAfterKills = 5,
	BossSteamRadius = 1100,
	BossSteamDamage = 6,      -- par pulsation de 0,5 s

	-- Mangeur
	EatTime = 4,              -- secondes avant d'être mangé
	EatDamage = 250,
	StruggleNeeded = 4,       -- coups de F pour se libérer
	StruggleStun = 3,         -- le Titan est étourdi autant de secondes

	-- Sauteur
	LeapCooldown = 6,
	LeapForce = 2200,
	LeapUp = 1400,

	-- Animations des Titans (montages du mannequin de base ; remplace par tes propres animations
	-- exportées depuis Unreal si le modèle en a, par ex. "mon-pack::AM_Titan_Eat")
	Animations = {
		attack = "nanos-world::AM_Mannequin_Melee_Slash_Attack",
		grab   = "nanos-world::AM_Mannequin_Melee_Stab_Attack",
		eat    = "nanos-world::AM_Mannequin_Torch_Attack",
	},

	-- Mort
	DeathSteamPulses = 14,    -- bouffées de vapeur à la mort (toutes les 0,4 s)
	BodyLinger = 4,           -- secondes avant que le corps commence à disparaître

	-- Effet de vitesse
	SpeedEffectStart = 600,   -- vitesse (cm/s) où l'effet commence
	SpeedEffectFull = 2400,   -- vitesse où il est à son maximum
	SpeedCameraPullBack = 180,-- recul maximal de la caméra

}
