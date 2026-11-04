# Pandora Kimetsu

Mode de jeu de rôle **Demon Slayer** pour [nanos world](https://nanos.world) (Unreal Engine 5.7), en français. Deux camps : les **Pourfendeurs**, qui maîtrisent un souffle et une lame Nichirin, et les **Démons**, qui régénèrent, se battent avec leur sang et dévorent les humains pour gagner en puissance.

> **État du projet : prototype.** Tout le code est testé par simulation (le Lua tourne dans un faux moteur), mais le mode de jeu n'a pas encore été vérifié en continu dans une vraie partie. Les rendus des effets, l'orientation des lames en main et les noms de quelques fonctions du moteur restent à confirmer en jeu. La liste précise est dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), section « Jamais vérifié en jeu ».

## Ce que contient le dépôt

```
pandora-kimetsu/
├── packages/            les packages nanos world (à copier dans Packages/ du serveur)
│   ├── wakfu-rp/        le mode de jeu « Kimetsu RP » (l'identifiant historique est gardé, voir plus bas)
│   ├── wakfu-loading/   écran de chargement
│   └── nanos-admin, gmod-props-menu, fx-showcase-menu   addons
├── server/              Config.example.toml (la partie propre) et le lanceur
├── scripts/             sync_packages.py : copie dépôt <-> serveur
├── tests/simulation/    tests sans le jeu (faux moteur Lua)
├── tools/               convertisseur GMod -> nanos, scripts Unreal, tests Python, formes d'effet générées
└── docs/                architecture, système du démon, assets, feuille de route, direction artistique
```

Les **assets** (modèles, animations, effets cuits par Unreal) ne sont **pas** dans le dépôt : ils pèsent des centaines de Mo et certains ont leur propre licence. [docs/ASSETS.md](docs/ASSETS.md) explique comment les produire.

## Démarrer (nouveau développeur)

Prérequis : le serveur nanos world, Python 3.12, et pour la partie contenu Unreal Engine 5.7 avec le plugin NanosWorldForge.

1. **Cloner** le dépôt : `git clone <adresse du dépôt> pandora-kimetsu`.
2. **Installer les packages** dans ton serveur nanos world (le dossier qui contient `NanosWorldServer.exe`) :
   ```
   python scripts/sync_packages.py install --server "C:/chemin/vers/nanos-world-server" --dry-run
   python scripts/sync_packages.py install --server "C:/chemin/vers/nanos-world-server"
   ```
3. **Configurer la partie** : copie `server/Config.example.toml` en `Config.toml` dans le dossier du serveur.
4. **Déposer les assets** cuits dans `Assets/` du serveur, un dossier par pack : voir [docs/ASSETS.md](docs/ASSETS.md). Sans eux, le mode de jeu ne se charge pas.
5. **Lancer** `NanosWorldServer.exe` (ou `server/Lancer-Kimetsu.bat`) et rejoindre la partie.
6. **Modifier le code** dans `packages/`, relancer les tests (ci-dessous), puis réinstaller sur le serveur avec le même script. Pour récupérer des changements faits directement sur un serveur : `python scripts/sync_packages.py pull --server ...`.

## Les touches en jeu

| Touche | Effet |
|---|---|
| 1 à 4 | techniques de la voie |
| E | parler à un PNJ |
| H | dévorer une proie (démon) |
| I | inventaire |
| C | créateur de personnage |
| J | choisir la traînée de l'arme |
| F5, F6 | accepter une quête, entraînement |
| Échap ou F10 | menu |
| F1 à F4, F7 à F9, flèches gauche et droite | **raccourcis de test** : changer de voie, visualiseur d'animations, essais d'effets, changer d'arme. À couper en production (tâche A2) |

## Les tests

```
pip install lupa
python tests/simulation/run_all.py          # logique, serveur et client du Lua
python tests/simulation/run_all.py --ui     # en plus : le HUD dans Microsoft Edge (captures dans tests/simulation/out/)

pip install -r tools/requirements-dev.txt
cd tools && python -m pytest                # convertisseur, scripts Unreal, générateurs
```

Trois tests de `tools/tests/test_characters.py` attendent un fichier de référence qui n'est pas versionné (`tests/data/nanos_mannequin_reference.json`) : ils échouent tant qu'on ne le fournit pas.

## Pour comprendre la suite

| Document | Contenu |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | comment le code est organisé, les événements, l'état d'un joueur, les tests |
| [docs/DEMON-SYSTEM.md](docs/DEMON-SYSTEM.md) | le système du démon : camps, sang, chair, âmes, cadavres, limite de repas |
| [docs/ASSETS.md](docs/ASSETS.md) | les packs d'assets, leur origine, comment les cuire et les déployer |
| [docs/ROADMAP.md](docs/ROADMAP.md) | le fil rouge, ce qui est fait, les prochaines fonctionnalités, les 49 tâches |
| [Issues](https://github.com/AkselSorensen/Pandora-Kimetsu/issues) | tout ce qu'il y a à faire pour deux développeurs, numéroté dans l'ordre de priorité (voir [CONTRIBUTING.md](CONTRIBUTING.md)) |
| [docs/DA-DEMON.md](docs/DA-DEMON.md) | la direction artistique du côté démon, et le prompt Figma |
| [CONTRIBUTING.md](CONTRIBUTING.md) | comment contribuer : branches, commits, conventions, vérifications |

## Conventions à connaître tout de suite

- **L'identifiant `wakfu-rp` et les événements `wakfu:*` sont gardés** : le projet est né d'un mode de jeu Wakfu, converti en Demon Slayer. Le nom affiché est « Kimetsu RP » (`Package.toml`). Les renommer toucherait tous les messages entre client et serveur pour un gain seulement esthétique.
- **Le serveur décide de tout** : le client n'envoie que des intentions (une touche, un clic) et affiche ce que le serveur renvoie.
- **La logique de jeu est pure** (dans `Shared/`, sans appel au moteur) pour être testée sans lancer nanos world ; les valeurs de réglage sont dans `Shared/Config.lua`.
- **Rien d'extrait d'un jeu commercial** ne doit entrer dans le projet, ni dans le dépôt, ni dans les packs d'assets.

## Droits

Le code de ce dépôt est écrit par Aksel Sorensen et ses contributeurs ; la licence reste à choisir (en attendant, tous droits réservés). Les assets ne sont pas fournis et suivent chacun leur licence (packs Fab, addons du Steam Workshop, animations), détaillée dans [docs/ASSETS.md](docs/ASSETS.md). Demon Slayer (Kimetsu no Yaiba) appartient à ses ayants droit ; ce projet est une œuvre de fan sans lien avec eux.
