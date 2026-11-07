-- Classes Demon Slayer : un style de respiration pour les pourfendeurs, le sang pour les démons.
-- Distances en centimètres (unité de Nanos World), temps en secondes.
-- `glyph` : le kanji du style, affiché à la place d'un portrait dans l'écran de reroll et dans le HUD.
-- `ladder` : l'échelle de grades de la classe (voir Ranks.lua).
-- `fallbackModel` : mesh fourni par Nanos World ; `model` (facultatif) sert si Config.UseCustomModels est vrai.
-- Un sort peut aussi soigner son lanceur (`heal`, en PV) ; sans `damage` il ne blesse personne.
-- `glyph` (facultatif) : le kanji affiché dans l'emplacement de la technique à la place de son icône (thème du démon).

local Classes = {}

Classes.Default = "Eau"

Classes.List = {
	Eau = {
		name = "Souffle de l'Eau",
		glyph = "水",
		color = "#2f8fd0",
		ladder = "slayer",
		role = "Polyvalent",
		title = "Le souffle fluide",
		short = "Polyvalent, corps à corps",
		blurb = "Le Souffle de l'Eau s'adapte à tout adversaire : des coupes fluides, un rythme constant et une garde qui ne cède pas. C'est la respiration la plus enseignée du Corps, idéale pour débuter.",
		tags = { "Polyvalent", "Corps à corps", "Facile à prendre en main" },
		gameplay = { damage = 65, survival = 65, support = 25, control = 35 },
		fallbackModel = "nanos-world::SK_Male",
		hp = 1200,
		spells = {
			{ id = "eau_surface", name = "Coupe de la surface", damage = 150, range = 260, cooldown = 2 },
			{ id = "eau_maree", name = "Marée frappante", damage = 180, range = 320, cooldown = 4 },
			{ id = "eau_tourbillon", name = "Tourbillon", damage = 140, range = 450, cooldown = 6 },
			{ id = "eau_flux", name = "Flux constant", damage = 260, range = 380, cooldown = 10 },
		},
	},
	Foudre = {
		name = "Souffle de la Foudre",
		glyph = "雷",
		color = "#f2c20f",
		ladder = "slayer",
		role = "Dégâts",
		title = "L'éclair divin",
		short = "Fulgurant, grande portée",
		blurb = "Le Souffle de la Foudre n'a qu'une idée : frapper avant que l'ennemi ait vu venir le coup. Une charge fulgurante, puis le silence. Fragile, mais redoutable à distance.",
		tags = { "Dégâts", "Vitesse", "Fulgurant" },
		gameplay = { damage = 85, survival = 35, support = 15, control = 25 },
		fallbackModel = "nanos-world::SK_ClassicMale",
		hp = 950,
		spells = {
			{ id = "foudre_eclair", name = "Éclair et tonnerre", damage = 190, range = 900, cooldown = 3 },
			{ id = "foudre_roulement", name = "Roulement de tonnerre", damage = 120, range = 500, cooldown = 5 },
			{ id = "foudre_chaleur", name = "Chaleur de l'éclair", damage = 160, range = 700, cooldown = 6 },
			{ id = "foudre_six", name = "Six éclairs", damage = 300, range = 1100, cooldown = 12 },
		},
	},
	Flamme = {
		name = "Souffle des Flammes",
		glyph = "炎",
		color = "#e0602a",
		ladder = "slayer",
		role = "Dégâts",
		title = "Le brasier inébranlable",
		short = "Puissant, corps à corps",
		blurb = "Le Souffle des Flammes brûle tout sur son passage. Des coups larges et lourds, portés avec un courage qui ne recule jamais : il faut le voir pour croire qu'un homme peut tenir ainsi face à la nuit.",
		tags = { "Dégâts", "Corps à corps", "Puissance" },
		gameplay = { damage = 90, survival = 55, support = 20, control = 15 },
		fallbackModel = "nanos-world::SK_Male",
		hp = 1250,
		spells = {
			{ id = "flamme_inconscient", name = "Feu inconscient", damage = 180, range = 280, cooldown = 3 },
			{ id = "flamme_soleil", name = "Soleil levant", damage = 150, range = 350, cooldown = 4 },
			{ id = "flamme_tigre", name = "Tigre de flammes", damage = 230, range = 600, cooldown = 7 },
			{ id = "flamme_purgatoire", name = "Purgatoire", damage = 320, range = 400, cooldown = 11 },
		},
	},
	Vent = {
		name = "Souffle du Vent",
		glyph = "風",
		color = "#5fc9a8",
		ladder = "slayer",
		role = "Dégâts",
		title = "La tempête incisive",
		short = "Zone, coups multiples",
		blurb = "Le Souffle du Vent déchire l'air en lames tournoyantes : chaque geste lance une rafale qui frappe tout autour de lui. Sauvage, instinctif, sans aucune retenue.",
		tags = { "Dégâts", "Zone", "Sauvage" },
		gameplay = { damage = 85, survival = 40, support = 15, control = 40 },
		fallbackModel = "nanos-world::SK_Mannequin",
		hp = 1000,
		spells = {
			{ id = "vent_poussiere", name = "Tourbillon de poussière", damage = 140, range = 400, cooldown = 2 },
			{ id = "vent_griffes", name = "Griffes purificatrices", damage = 170, range = 500, cooldown = 4 },
			{ id = "vent_tempete", name = "Tempête ascendante", damage = 210, range = 450, cooldown = 7 },
			{ id = "vent_brume", name = "Brume de montagne", damage = 280, range = 700, cooldown = 11 },
		},
	},
	Pierre = {
		name = "Souffle de la Pierre",
		glyph = "岩",
		color = "#a8a29a",
		ladder = "slayer",
		role = "Tank",
		title = "Le roc impassible",
		short = "Tank, encaisse tout",
		blurb = "Le Souffle de la Pierre fait de son porteur une muraille. Lent, patient, il encaisse ce qui briserait les autres et rend chaque coup au centuple d'un seul revers de hache et de chaîne.",
		tags = { "Tank", "Défense", "Endurance" },
		gameplay = { damage = 55, survival = 95, support = 30, control = 30 },
		fallbackModel = "nanos-world::SK_Male",
		hp = 1600,
		spells = {
			{ id = "pierre_serpentine", name = "Serpentine bipède", damage = 130, range = 280, cooldown = 3 },
			{ id = "pierre_peau", name = "Peau de pierre", heal = 200, range = 0, cooldown = 9 },
			{ id = "pierre_eclat", name = "Éclat supérieur", damage = 200, range = 300, cooldown = 5 },
			{ id = "pierre_arcs", name = "Arcs de justice", damage = 250, range = 450, cooldown = 10 },
		},
	},
	Brume = {
		name = "Souffle de la Brume",
		glyph = "霞",
		color = "#9fb4c8",
		ladder = "slayer",
		role = "Contrôle",
		title = "Le voile mouvant",
		short = "Contrôle, esquive",
		blurb = "Le Souffle de la Brume trompe le regard de l'ennemi : on croit le toucher, il n'est déjà plus là. Il gêne, esquive et frappe de côté, quand l'adversaire ne s'y attend plus.",
		tags = { "Contrôle", "Esquive", "Discrétion" },
		gameplay = { damage = 55, survival = 45, support = 30, control = 90 },
		fallbackModel = "nanos-world::SK_ClassicMale",
		hp = 1000,
		spells = {
			{ id = "brume_lune", name = "Lune déclinante", damage = 120, range = 350, cooldown = 2 },
			{ id = "brume_huit", name = "Brume à huit couches", damage = 150, range = 500, cooldown = 5 },
			{ id = "brume_eclaboussure", name = "Éclaboussure de brume", damage = 100, range = 800, cooldown = 6 },
			{ id = "brume_nuages", name = "Nuages obscurcissants", damage = 220, range = 600, cooldown = 9 },
		},
	},
	Insecte = {
		name = "Souffle de l'Insecte",
		glyph = "蟲",
		color = "#b06fe0",
		ladder = "slayer",
		role = "Soutien",
		title = "Le venin guérisseur",
		short = "Soutien, poison, soins",
		blurb = "Le Souffle de l'Insecte ne tranche pas : il pique. Des coups fins qui injectent un venin de glycine mortel pour les démons, et des remèdes qui remettent les alliés sur pied.",
		tags = { "Soutien", "Poison", "Soins" },
		gameplay = { damage = 40, survival = 40, support = 90, control = 50 },
		fallbackModel = "nanos-world::SK_Female",
		hp = 900,
		spells = {
			{ id = "insecte_papillon", name = "Piqûre du papillon", damage = 110, range = 260, cooldown = 2 },
			{ id = "insecte_glycine", name = "Venin de glycine", damage = 130, range = 900, cooldown = 5 },
			{ id = "insecte_remede", name = "Remède de glycine", heal = 250, range = 0, cooldown = 8 },
			{ id = "insecte_abeille", name = "Piqûre d'abeille", damage = 240, range = 500, cooldown = 10 },
		},
	},
	Demon = {
		name = "Démon",
		glyph = "鬼",
		color = "#c8323c",
		ladder = "demon",
		role = "Dégâts",
		title = "Le prédateur de la nuit",
		short = "Sang, régénération",
		blurb = "Les démons ne craignent ni la fatigue ni les blessures : leur chair se recoud d'elle-même. Griffes, lames de sang et techniques sanguinaires, jusqu'à ce que l'aube se lève.",
		tags = { "Dégâts", "Régénération", "Technique de sang" },
		gameplay = { damage = 80, survival = 70, support = 20, control = 30 },
		fallbackModel = "nanos-world::SK_Mannequin",
		hp = 1300,
		spells = {
			{ id = "demon_griffes", name = "Griffes de sang", glyph = "爪", damage = 160, range = 260, cooldown = 2 },
			{ id = "demon_lames", name = "Lames de sang", glyph = "刃", damage = 130, range = 700, cooldown = 4 },
			{ id = "demon_regeneration", name = "Régénération", glyph = "癒", heal = 300, range = 0, cooldown = 9 },
			{ id = "demon_dechainement", name = "Déchaînement sanguinaire", glyph = "狂", damage = 280, range = 500, cooldown = 12 },
		},
	},
}

-- Camps : le joueur choisit Pourfendeur ou Démon une seule fois par personnage. Chaque voie appartient à un camp (champ camp, déduit de son
-- échelle de grades), et le camp fixe l'échelle de grades, la voie de départ et ce que l'écran de choix affiche.
Classes.Camps = {
	slayer = {
		name = "Pourfendeur",
		kanji = "鬼殺",
		color = "#2f8fd0",
		ladder = "slayer",
		defaultClass = "Eau",
		cardTitle = "POURFENDEURS", -- textes exacts de la carte de l'écran de choix de faction (planche Figma)
		cardText = "Les pourfendeurs sont des chasseurs de démons membre de l'Armée des pourfendeurs de démons.",
		blurb = "Tu rejoins le Corps des Pourfendeurs de démons : une lame Nichirin, un souffle à maîtriser et la nuit à tenir jusqu'à l'aube.",
		points = {
			"Techniques de respiration (souffles)",
			"Lame Nichirin à forger et à porter",
			"Grades du Mizunoto au Hashira",
			"Soin, soutien et esprit de corps",
		},
	},
	demon = {
		name = "Démon",
		kanji = "鬼",
		color = "#c8323c",
		ladder = "demon",
		defaultClass = "Demon",
		cardTitle = "DEMON",
		cardText = "Les Démons sont des êtres nés des ténèbres, dotés d'une force surnaturelle et d'une longévité quasi immortelle.",
		blurb = "La nuit t'appartient. Ta chair se recoud d'elle-même, tes griffes et ton sang frappent, et chaque humain dévoré te rend plus fort, jusqu'aux Lunes.",
		points = {
			"Régénération passive hors combat",
			"Le sang alimente tes techniques",
			"Dévorer des humains pour gagner en puissance",
			"Grades des démons errants aux Lunes",
			"La faim fait retomber ta puissance",
		},
	},
}

Classes.CampOrder = { "slayer", "demon" }

for _, class in pairs(Classes.List) do
	class.camp = class.ladder == "demon" and "demon" or "slayer"
end

-- Camp d'une voie ("slayer" ou "demon"), ou nil si elle n'existe pas.
function Classes.CampOf(className)
	local class = Classes.List[className]
	return class and class.camp or nil
end

-- Ordre d'affichage dans l'écran de reroll de classe (les huit cartes de la maquette) ; F1 à F4 prennent les quatre premières.
Classes.RerollOrder = { "Eau", "Foudre", "Flamme", "Vent", "Pierre", "Brume", "Insecte", "Demon" }

-- Renvoie la définition d'une classe, ou nil si elle n'existe pas.
function Classes.Get(className)
	return Classes.List[className]
end

-- Renvoie le sort à la position donnée (1 = touche 1), ou nil.
function Classes.GetSpell(className, index)
	local class = Classes.List[className]
	if not class then
		return nil
	end
	return class.spells[index]
end

return Classes
