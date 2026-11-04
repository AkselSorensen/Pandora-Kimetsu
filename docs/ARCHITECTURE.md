# Architecture

## Vue d'ensemble

```
Unreal Engine 5.7 (plugin Forge)         nanos world (serveur et clients)
  modèles, animations, effets   ──cuisson──►  Assets/<pack>/            (un dossier par pack, jamais dans le dépôt)
                                              Packages/kimetsu-pandora/        le mode de jeu (ce dépôt)
                                              Packages/<addons>/        facultatifs (ce dépôt)
```

- Le **mode de jeu** `kimetsu-pandora` fait tout le jeu de rôle : classes, grades, quêtes, PNJ, inventaire, forge, effets, système du démon.
- Les **addons** sont des packages indépendants que la partie peut charger en plus (administration, menu de props, boutique, caisses, équipement ODM, vitrine d'effets). La partie propre n'en charge aucun.
- Les **packs d'assets** contiennent les modèles et effets cuits. Le mode de jeu les exige dans son `Package.toml` (`assets_requirements`) : il ne démarre pas s'il en manque un.

## Le mode de jeu `kimetsu-pandora`

```
packages/kimetsu-pandora/
├── Package.toml            nom affiché, packs d'assets exigés
├── Shared/                 chargé par le serveur ET le client : données et logique pure
│   ├── Config.lua          tous les réglages (armes, effets, démon, cadavres, apparences)
│   ├── Classes.lua         8 voies (7 souffles + démon), camps, techniques
│   ├── Ranks.lua           échelles de grades (pourfendeur, démon) et XP
│   ├── Demon.lua           sang, chair, âmes, paliers, faim, repas par jour (logique pure)
│   ├── Combat.lua          portée, dégâts, soins, délais de recharge
│   ├── Items.lua           objets, inventaire, équipement, 176 lames
│   ├── Quests.lua, Npcs.lua, Economy.lua
│   ├── VfxPlan.lua         quels effets pour quelle technique, trajectoires (logique pure)
│   ├── YufuWeapons.lua     liste des lames (GÉNÉRÉ par tools/unreal_tools/gen_yufu_weapons.py)
│   ├── VfxAssets.lua       effets Niagara réellement cuits (GÉNÉRÉ par tools/unreal_tools/gen_vfx_assets.py)
│   ├── FxMeshAssets.lua    formes lumineuses réellement cuites (GÉNÉRÉ par le même script)
│   └── Animations.lua      liste des animations pour le visualiseur
├── Server/
│   ├── Index.lua           serveur autoritaire : état des joueurs, techniques, camp, démon, cadavres, forge...
│   └── AnimViewer.lua      outil de mise au point (visualiseur d'animations)
└── Client/
    ├── Index.lua           touches, écrans, relais des événements vers le HUD
    ├── VfxPlayer.lua       joue les effets chez le joueur (Niagara et formes lumineuses)
    ├── AnimViewer.lua, Zoom.lua
    └── UI/                 le HUD en HTML : index.html, index.js, style.css, img/
```

Règle de découpage : tout ce qui se calcule sans le moteur va dans `Shared/` et se teste ; `Server/` branche cette logique sur le moteur (personnages, minuteurs, événements) ; `Client/` ne décide jamais.

### L'état d'un joueur (serveur)

Un tableau par joueur dans `Server/Index.lua` : voie (`class`), camp (`camp`, nul avant le choix), état du démon (`demon`, seulement pour un démon), apparence (`gender`, `color`, `skin`, `nick`), `cooldowns`, yens (`kamas`), `xp`, `quests`, `stats` (bonus de l'entraînement), `inventory`, choix de traînée (`trail`, `trailSize`), arme choisie (`cycledWeapon`). Il est en mémoire seulement : **rien n'est sauvegardé** tant que la tâche B1 n'est pas faite.

### Les événements

Tous préfixés `wakfu:`.

| Sens | Événements |
|---|---|
| client → serveur | `castIndex`, `interact`, `acceptQuest`, `reroll`, `chooseCamp`, `chooseClass`, `classReroll`, `create`, `devour`, `forgeBuy`, `invUse` / `invUnequip` / `invMove` / `invDrop` / `invDelete` / `invGive`, `trailChoose`, `trailSize`, `weaponCycle`, `creatorEnter` / `creatorAim` / `creatorExit` |
| serveur → client | `state` (tout ce que le HUD affiche), `inventory`, `notice`, `cast`, `fx`, `dialog`, `demon` (jauges du démon, chaque seconde), `devourStart` / `devourStop`, `openCamp` / `openCreator` / `openClassReroll` / `openForge`, `questAccepted` / `questDone`, `rerolled` / `rerollFailed` |
| entre packages (côté serveur) | `Wakfu:EquipWeapon` (équiper une arme depuis le menu de props), `Wakfu:ResetCamp` (remettre le camp d'un joueur à zéro) |

Le serveur **valide chaque demande** (distance, coût, camp, limite) : un client modifié ne doit rien pouvoir obtenir en plus.

### Les effets visuels

`VfxPlan.lua` choisit, pour chaque technique, des systèmes Niagara (traînées, impacts) et des formes lumineuses (croissants, anneaux, spirales...) d'après deux listes **générées** : `VfxAssets.lua` et `FxMeshAssets.lua`. Sans pack cuit, les listes sont vides et le jeu tourne sans effet, sans erreur. Le serveur envoie seulement `fx` (identifiant de la technique, position, direction) aux joueurs proches ; `VfxPlayer.lua` crée les entités locales chez chacun. Les traînées d'arme sont des particules attachées à la lame (allumées pendant un coup), au choix du joueur (touche J).

### Le HUD

Une page HTML (`Client/UI/`) pilotée par des événements Lua. Le thème démoniaque s'active par une classe `demon` sur `<html>` quand le camp est démon. Les polices (Shippori Mincho, Rajdhani) sont nommées dans le CSS mais **aucun fichier de police n'est livré** : le jeu retombe sur une police japonaise du système puis sur Georgia.

## Les tests

- **Simulation** (`tests/simulation/`) : le Lua du serveur et du client tourne dans un faux moteur (module `lupa`). On y vérifie l'arrivée d'un joueur, les techniques, la forge, les traînées, le camp, le démon, les cadavres, la limite de repas, et les écrans du HUD (avec `--ui`, dans Microsoft Edge).
- **Python** (`tools/tests/`) : convertisseur GMod, scripts Unreal, générateurs de listes et de formes.

Un test de simulation vérifie le **raisonnement** du code, pas le moteur : si un nom de fonction nanos world est faux, la simulation ne le voit pas.

## Jamais vérifié en jeu

À contrôler au premier lancement réel, dans cet ordre :

1. Les noms `SetStanceMode` et `StopAnimation` (posture accroupie du démon qui mange), enveloppés dans `pcall`. Le site de documentation de nanos était inaccessible au moment de l'écriture.
2. Le rendu des effets : le matériau lumineux, les formes (taille et orientation), le sens des traînées. Les noms de l'API `StaticMesh` ont été déduits du code du package `sandbox`.
3. La taille de la traînée : la largeur du ruban est une constante dans les systèmes Niagara du pack, l'échelle du composant peut n'avoir aucun effet.
4. L'orientation et la taille des lames en main (mesurées sur un katana de référence, jamais vues en partie).
5. Les touches F1 à F10, J et H, qui pourraient être prises par le moteur.
6. Les polices du HUD.

## Le pipeline de contenu

Détaillé dans [ASSETS.md](ASSETS.md) : addons GMod ou modèles → glTF (`tools/gmod2nanos`) → import et cuisson dans Unreal (`tools/unreal_tools`, plugin Forge) → master cumulatif (`python -m gmod2nanos.master`) → serveur → régénération des listes (`gen_vfx_assets.py`, `gen_yufu_weapons.py`).
