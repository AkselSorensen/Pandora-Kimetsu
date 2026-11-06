# Feuille de route

Ce document est le fil rouge du projet. Il vient du plan de travail à deux développeurs (49 tâches) et de l'état réel du code.
Les priorités vont de P0 (à faire d'abord) à P2 (plus tard) ; les tailles sont S, M et L.

## Le parcours du joueur, du début à la fin

Chaque fonctionnalité sert une étape de ce parcours. Si une idée n'y trouve pas sa place, elle attend.

1. **Arrivée** : écran de choix du camp, Pourfendeur ou Démon, une seule fois par personnage (A12).
2. **Premier tirage** : un souffle ou un pouvoir sanguinaire tiré au sort, avec des raretés et une pitié (A13, A14, A15).
3. **Progression** : grades, quêtes, chasse aux démons, arbre de compétences (A6, A7, A17).
4. **Combat** : techniques de respiration et pouvoirs sanguinaires, sabre, parade, dash, soleil, glycine (A4, A22, A21, A25).
5. **Puissance du démon** : sang, chair, âmes, repas par jour, cadavres (A5, A18).
6. **Économie** : yens, forge de lames, craft, équipement par paliers, boutique (A26, A28, B7, B14).
7. **Monde** : maisons instanciées, coffres, récolte, carte et ambiance (A19, A20, B19, B6).

## Ce qui est fait

- Conversion complète du mode de jeu en Demon Slayer : 8 voies (7 souffles et le démon), grades, 176 lames, quêtes, PNJ, forge.
- Effets : 63 systèmes Niagara cuits, 12 formes lumineuses originales, traînées d'arme avec menu (touche J), tailles réglables.
- Système du démon (première tranche) : camp, sang, chair, âmes à 5 paliers, faim, régénération, dévoration, HUD démoniaque.
- Cadavres : le corps d'un joueur mort reste au sol, un démon peut le dévorer, limite de repas par jour selon le grade.
- Outils : convertisseur GMod, scripts Unreal, master des assets cuits, tests de simulation sans le jeu.
- Partie propre et dépôt Pandora Kimetsu (ce dépôt).

Rien de cela n'a été vérifié dans une vraie partie : tout est testé par simulation (voir `docs/ARCHITECTURE.md`, section Tests).

## Prochaines fonctionnalités, dans l'ordre

1. **Pouvoirs sanguinaires (A14)** : plusieurs pouvoirs de quatre techniques avec une rareté. Il faut d'abord valider la liste (décision 8).
2. **Tirage et pitié (A13, A15)** : le premier tirage après le choix du camp, taux publiés et pitié par paliers.
3. **Sauvegarde des joueurs (B1)** : camp, âmes, repas, pitié et grade gardés entre deux connexions.
4. **Combat (A22) et fin de A5** : parade, dash, bonus des lames Nichirin contre les démons, équilibrage par des duels.
5. **Soleil (A21)** : durée du jour et temps de survie à décider (décision 17). La régénération du démon sait déjà se couper au soleil.
6. **Chasse (A7)** : des démons mineurs à tuer, source de puissance prête côté démon.
7. **Glycine (A25), menu de touches (A16), maisons et coffres (A19, A20)**.

## Décisions ouvertes

- **Décision 8** : la liste des pouvoirs sanguinaires et la rareté de chaque voie. Proposition du plan : Sang explosif, Fils, Tambours, Glace, Rubans, Faucilles de sang.
- **Décision 14 (révisée)** : jamais un joueur vivant n'est une proie. Les cadavres de joueurs le sont, la victime n'est pas touchée. Une option de refus par joueur reste à décider.
- **Décision 17** : durée d'une journée du jeu, part de nuit, secondes de survie d'un démon au soleil, exceptions et abris.

## Toutes les tâches

| Tâche | Qui | Priorité | Taille | État |
|---|---|---|---|---|
| A1 Recette en jeu et retouches visuelles | A | P0 | S | À faire |
| A2 Couper les raccourcis de test en production | A | P0 | S | À faire |
| A3 Orientation et taille des lames en main | A | P0 | S | À vérifier en jeu : orientation mesurée, jamais vue en partie |
| A4 Techniques de respiration jouables | A | P1 | L | En cours : effets et traînées en place, pas encore de techniques à projectile |
| A5 Le Démon, de bout en bout | A | P1 | M | En cours : régénération et sang faits, reste le bonus des lames et l'équilibrage |
| A6 Grades et progression | A | P1 | M | À faire |
| A7 Chasse aux démons et missions | A | P1 | L | À faire |
| A8 PNJ avec de vrais skins | A | P1 | S | À faire |
| A9 Couleur Nichirin par voie | A | P2 | M | À faire |
| A10 Illustrations et icônes | A | P2 | M | À faire |
| A11 Relecture des textes | A | P2 | S | À faire |
| A12 Choix du camp à l'arrivée | A | P0 | M | En cours : écran et verrouillage faits, la sauvegarde attend B1 |
| A13 Tirage au sort des souffles et des pouvoirs sanguinaires | A | P0 | L | À faire |
| A14 Pouvoirs sanguinaires du Démon | A | P0 | L | À faire |
| A15 Modèle de probabilités et pitié | A | P0 | M | À faire |
| A16 Menu de touches dans l'inventaire | A | P1 | M | À faire |
| A17 Arbre de compétences | A | P1 | L | À faire |
| A18 Chair et âmes humaines : la puissance du Démon | A | P1 | L | En cours : chair, âmes, paliers, faim, civils et cadavres faits, reste la chasse et l'équilibrage |
| A19 Maisons instanciées | A | P1 | L | À faire |
| A20 Coffres liés à l'inventaire | A | P1 | L | À faire |
| A21 Soleil qui brûle les démons | A | P1 | M | À faire |
| A22 Combat au sabre et aux pouvoirs démoniaques | A | P1 | L | À faire |
| A23 Créateur de personnage | A | P1 | L | En cours : le créateur s'ouvre après le choix du camp, nom de 3 caractères minimum ; reste la fiche RP et l'apparence par camp |
| A24 Emplacements supplémentaires pour les VIP | A | P2 | M | À faire |
| A25 Zones de glycine pour les démons | A | P1 | M | À faire |
| A26 Équipement par paliers T1 à T4 | A | P1 | L | À faire |
| A27 Reroll cosmétique du sabre et du démon | A | P1 | L | À faire |
| A28 Craft de sabres avec des plans | A | P1 | L | À faire |
| A29 Communication entre joueurs | A | P1 | M | À faire |
| B1 Sauvegarde des joueurs | B | P0 | L | À faire |
| B2 Une seule source pour les deux serveurs | B | P0 | M | Fait avec ce dépôt (une seule source pour les deux serveurs) |
| B3 Outils d'administration sur le serveur dédié | B | P0 | M | À faire |
| B4 Contrôle des assets avant chaque lancement | B | P0 | S | À faire |
| B5 Trier les addons selon le thème | B | P1 | M | En cours : la partie propre ne charge aucun addon |
| B6 Carte et ambiance Demon Slayer | B | P1 | L | À faire |
| B7 Boutique et caisses | B | P1 | M | À faire |
| B8 Tests automatiques | B | P1 | M | En cours : simulation sans le jeu et tests Python |
| B9 Robustesse du serveur | B | P1 | M | À faire |
| B10 Pipeline de contenu documenté | B | P1 | S | Fait : voir docs/ASSETS.md |
| B11 Armes à feu et autres addons GMod | B | P2 | L | À faire |
| B12 Identité publique du serveur | B | P2 | S | À faire |
| B13 Sauvegardes et lancement fiable | B | P2 | M | À faire |
| B14 Boutique : resets et changements de classe | B | P1 | M | À faire |
| B15 Journal d'audit des tirages | B | P1 | M | À faire |
| B16 Modèle de maison | B | P1 | M | À faire |
| B17 Assets de glycine, de récolte et cosmétiques | B | P1 | M | À faire |
| B18 Modération et voix de proximité | B | P1 | M | À faire |
| B19 Récolte : minage, bois et autres ressources | B | P1 | L | À faire |
| B20 Launcher du jeu | B | P2 | L | À faire |

A = Dev A (jeu et interface), B = Dev B (serveur, contenu, outils).

## Calendrier prévu

| Période | Dev A | Dev B |
|---|---|---|
| Semaine 1 | A12 choix du camp, A14 pouvoirs sanguinaires (données), A15 modèle de probabilités et pitié | B3 admin sur le dédié, B4 contrôle des assets, B1 sauvegarde (camp, jetons et pitié compris) |
| Semaine 2 | A13 tirage au sort, A3 lames en main, A2 raccourcis de test (après B3), A6 grades | B1 fin, B15 journal d'audit, B14 boutique des resets (après A13), B8 tests, B9 robustesse, B10 pipeline |
| Semaine 3 | A22 combat (parade, combos, dash), A8 PNJ | B5 tri des addons (après décision), B7 boutique et caisses, B6 carte et ambiance |
| Semaine 4 | A4 techniques jouables, A16 menu de touches, A29 chat | B6 fin, B12 identité du serveur, B18 modération et voix |
| Semaine 5 | A5 Démon, A21 soleil | B16 modèle de maison, B17 assets de glycine et cosmétiques, B13 sauvegardes et lancement fiable |
| Semaine 6 | A18 chair et âmes, A7 chasse et missions | B19 récolte, B11 armes à feu et autres addons GMod |
| Semaine 7 | A20 coffres (avec A24 emplacements VIP), puis A19 maisons instanciées | B8 : tests des maisons et des coffres |
| Semaine 8 | A17 arbre de compétences, A23 créateur de personnage | B20 launcher |
| Semaine 9 | A25 zones de glycine, A26 équipement par paliers | aucune tâche prévue |
| Semaine 10 | A27 reroll cosmétique du sabre et du démon | aucune tâche prévue |
| Semaine 11 | A28 craft de sabres avec des plans | aucune tâche prévue |
| Ensuite | A9, A10, A11 | aucune tâche prévue |

Le calendrier suppose deux développeurs à plein temps ; il se décale si un seul avance. Les tâches du dev B se transfèrent au dev A sans toucher à l'interface, qui reste au dev A.
