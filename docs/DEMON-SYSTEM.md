# Le système du démon

Premier ensemble de fonctionnalités du camp démon : tâches A5, A12 et A18 du plan (voir [ROADMAP.md](ROADMAP.md)). Le code est dans `Shared/Demon.lua` (logique pure), `Server/Index.lua` (section « Système du démon ») et `Client/UI/` (HUD). **Tous les réglages sont dans `Shared/Config.lua`**, sections `Config.Demon` et `Config.Corpses`.

## Le camp

À sa première connexion, le joueur voit un écran obligatoire : **Pourfendeur** ou **Démon**. Le choix est **définitif pour le personnage** : le serveur refuse tout changement de voie, de reroll ou de création qui ferait changer de camp. Sans camp choisi, aucune voie ne peut être prise. Un autre package peut remettre le camp à zéro avec l'événement serveur `Wakfu:ResetCamp` (support, boutique). Tant que la sauvegarde (B1) n'existe pas, le choix est perdu à la déconnexion.

Un démon ne tient pas de lame : il se bat avec ses techniques. Son échelle de grades est celle des Lunes (de « Démon errant » à « Lune Supérieure Une »).

## Les ressources

| Ressource | Rôle | Réglage de départ |
|---|---|---|
| **Sang** | paie les techniques ; remonte seul | 100 maximum, +2,5 par seconde ; coûts 8, 12, 25 et 40 |
| **Chair** | nourrit la régénération ; se vide avec le temps | 100 maximum, -0,4 par seconde |
| **Âmes** | puissance durable, par paliers | 120 maximum |

**Régénération passive** : après 6 secondes sans coup donné ni reçu, le démon récupère 1,2 % de ses PV maximum par seconde. La chair l'amplifie (jusqu'à deux fois), la faim l'étouffe (35 % de la valeur). Elle est prévue pour se couper en plein soleil (tâche A21).

**Paliers de puissance** (selon les âmes) :

| Palier | Nom | Âmes | PV | Dégâts | Régénération |
|---|---|---|---|---|---|
| 1 | Errant affamé | 0 | 0 | 0 % | 0 |
| 2 | Chasseur de nuit | 10 | +80 | +6 % | +0,3 %/s |
| 3 | Prédateur | 30 | +180 | +12 % | +0,6 %/s |
| 4 | Seigneur de sang | 60 | +300 | +20 % | +0,9 %/s |
| 5 | Lune de sang | 100 | +450 | +30 % | +1,2 %/s |

La technique 4 est **verrouillée** jusqu'au palier 4. **La faim** : 240 secondes sans repas font retomber la puissance d'un palier (au seuil du palier précédent), puis le délai repart.

## Dévorer

Touche **H** près d'une proie. Le démon s'accroupit et maintient le geste 3,5 secondes ; le HUD montre une barre, le temps restant et le gain attendu. Un **coup reçu, une technique lancée, un pas de trop (plus de 330 cm) ou la mort** interrompent le repas sans rien consommer. Une proie ne se mange qu'une fois.

| Proie | Gain | Remarque |
|---|---|---|
| **Cadavre d'un joueur** | +50 chair, +6 âmes, +20 % PV, +20 XP | le corps reste au sol 180 secondes, puis disparaît ; il disparaît aussi quand on le dévore |
| **Civil** (4 PNJ du Domaine) | +40 chair, +4 âmes, +15 % PV, +15 XP | disparaît 90 secondes puis revient |
| Dépouille de chasse | +15 chair, +2 âmes, +5 % PV, +8 XP | réservé à la tâche A7, pas encore de source |

**Jamais un joueur vivant n'est une proie** : seuls les corps déjà morts le sont, et la victime n'est pas affectée (elle est revenue au Domaine dans un corps neuf). Un démon qui meurt part en cendres, sans cadavre (`Config.Corpses.demonsLeaveBody` pour changer).

**Limite de repas par jour** (cadavres et civils) : 5 au premier grade, 10 au deuxième, 15 au troisième, et ainsi de suite jusqu'à 40 au huitième. Le réglage `Config.Demon.meals` permet une liste explicite par grade. Un jour dure 24 heures réelles par défaut. Le HUD affiche « Repas du jour n/maximum », qui passe en or quand la limite est atteinte.

Pendant le repas, le démon est accroupi. Aucune animation de repas n'existe dans les packs : `Config.Demon.devour.animation` accepte l'identifiant d'une animation jouée en boucle.

## Ce qui reste à faire

Plusieurs pouvoirs sanguinaires tirés au sort (A14, A13, A15), bonus des lames Nichirin contre les démons et équilibrage par des duels (fin de A5), soleil (A21), dépouilles de chasse (A7), zones de glycine (A25), sauvegarde (B1). L'équilibrage actuel n'est pas validé : cinq repas par jour au premier grade donnent au mieux 30 âmes, alors que la faim fait retomber la puissance en quatre minutes sans repas.

## Les tests

`tests/simulation/demon_check.py` couvre la logique (paliers, sang, faim, limite de repas, passage au jour suivant), le serveur (camp, verrouillage, techniques, dévoration, interruptions, cadavres, limite par grade, reset) et le client (écran de camp, touches, événements). `tests/simulation/ui_demon_preview.py` vérifie le HUD dans Edge.
