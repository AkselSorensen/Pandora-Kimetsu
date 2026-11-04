# GMod-style Props Menu (nanos world)

Menu de props façon Garry's Mod pour nanos world. Appuie sur **Q** pour ouvrir la liste,
clique sur un élément pour le faire apparaître devant toi.

Le catalogue n'est pas écrit en dur : au démarrage, le serveur lit les `Assets.toml` de son
dossier `Assets/` et propose tout ce qu'il contient (pack de base nanos world, packs ajoutés, etc.).
Le package fonctionne donc sur n'importe quel serveur, sans configuration.

## Installation

1. Copie le dossier `gmod-props-menu` dans `Packages/` du serveur.
2. Dans `Config.toml`, ajoute-le à la liste des packages :

```toml
[game]
packages = ["gmod-props-menu"]
```

3. Lance le serveur. Le log affiche `[props-menu] N assets loaded`.

Pour ajouter des éléments, installe simplement un Asset Pack dans `Assets/` et redémarre le serveur.

## Ce qui est proposé

| Section d'Assets.toml | Dans le menu | Spawn |
|---|---|---|
| `static_meshes` | Prop | `Prop` |
| `skeletal_meshes` | Arme | `Weapon` |
| `characters`, autres sections | — | pas encore |

Les véhicules et entités ne sont pas encore proposés : leur API de spawn n'a pas été vérifiée
dans la doc officielle. Les onglets du menu correspondent aux packs.

## Sécurité

Le client n'envoie que l'index d'un élément. Le serveur retrouve l'asset dans son catalogue,
applique un cooldown (0,25 s) et limite chaque joueur à 50 éléments. Les éléments d'un joueur
sont supprimés quand il quitte.

## Contrôles

| Touche | Action |
|---|---|
| Q | Ouvrir / fermer le menu |
| Échap | Fermer le menu |

## Réglages

Constantes en haut de `Server/Index.lua` : `MAX_PROPS_PER_PLAYER`, `SPAWN_DISTANCE`,
`SPAWN_HEIGHT`, `COOLDOWN`. La touche d'ouverture est dans `Client/Index.lua` (`TOGGLE_KEY`).

## Statut

Version 0.1.0, non testée en jeu. À vérifier au premier lancement :

- `Rotator.Yaw` dans `ForwardFromRotation` (la page Rotator de la doc renvoyait une 404) ;
- `File.GetFiles("Assets", ".toml", -1)` renvoie bien les chemins des `Assets.toml` ;
- les armes spawnées au sol sont bien ramassables ;
- la liste se charge sur un serveur avec beaucoup de packs (taille du message JSON).

Le parseur de `Assets.toml` est volontairement simple : il lit les sections `[assets.<nom>]`
et les lignes `Clé = "chemin"`, ce que génèrent les outils nanos world et gmod2nanos.
