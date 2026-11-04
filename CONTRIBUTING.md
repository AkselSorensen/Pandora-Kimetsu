# Contribuer à Pandora Kimetsu

Merci de travailler sur le projet. Lis d'abord le [README](README.md), puis [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) et [docs/ROADMAP.md](docs/ROADMAP.md) : le fil rouge dit ce qui compte, dans quel ordre.

## Qui fait quoi

Le plan de travail répartit les tâches entre deux développeurs (voir la feuille de route) :

- **Dev A : le jeu et l'interface** (`packages/kimetsu-pandora`, surtout `Server/`, `Client/` et `Client/UI/`) : camps, démon, combat, HUD.
- **Dev B : le serveur, le contenu et les outils** (`tools/`, `scripts/`, `server/`, les packs d'assets, la sauvegarde) : pipeline d'assets, tests, sauvegarde, administration.

Deux personnes ne devraient pas modifier le même fichier en même temps : `Server/Index.lua` et `Client/UI/index.js` sont les points de friction. Annonce-toi avant d'y toucher beaucoup.

## Les issues

Tout ce qu'il y a à faire est dans les [issues du dépôt](https://github.com/AkselSorensen/Pandora-Kimetsu/issues), **numérotées dans l'ordre de priorité** : la plus basse issue ouverte de ton étiquette est la prochaine à prendre. L'issue « Feuille de route » les liste toutes, de haut en bas, avec des cases à cocher.

| Étiquette | Sens |
|---|---|
| `dev-a`, `dev-b` | à qui revient l'issue (voir « Qui fait quoi ») |
| `P0`, `P1`, `P2` | priorité, et jalon du même nom : fondations, jeu complet, finitions |
| `taille: S/M/L` | moins d'une journée, quelques jours, une semaine ou plus |
| `zone: ...` | la partie du jeu concernée |
| `en cours`, `à vérifier en jeu` | déjà commencé, ou écrit mais jamais vu dans une vraie partie |
| `décision` | une décision à prendre avant de coder |
| `dette` | nettoyage d'un travail précédent |

Chaque issue dit **pourquoi**, **ce qu'il faut faire** (cases à cocher), **quand elle est terminée**, de quoi elle **dépend** (avec un lien vers l'issue) et quels fichiers elle touche. Une issue qui dépend d'une autre non terminée peut être préparée, mais pas fermée. Ferme-la depuis la demande de fusion (`Closes #12`).

Les issues viennent de `scripts/issues.json` ; `python scripts/create_issues.py --dry-run` montre ce qui serait créé, et le script, relancé, ne recrée jamais une issue existante.

## Le flux de travail

1. **Choisis une issue** (voir « Les issues » ci-dessous) et vérifie qu'elle sert le parcours du joueur.
2. **Crée une branche** depuis `main` : `feature/<tâche>-<sujet>` (par exemple `feature/a14-pouvoirs-sanguinaires`) ou `fix/<sujet>`.
3. **Code** (conventions ci-dessous), **teste** (`python tests/simulation/run_all.py`), **installe sur ton serveur** (`python scripts/sync_packages.py install --server ...`) et essaie en jeu quand c'est possible.
4. **Mets la documentation à jour** : la section concernée de `docs/`, et le statut de la tâche dans `docs/ROADMAP.md`.
5. **Ouvre une demande de fusion** vers `main` avec : ce qui change, comment tu l'as vérifié (simulation, en jeu, ou pas encore), ce qui reste.

Les messages de commit sont en français, à l'impératif, préfixés par le sujet : `Démon : limite de repas par grade`, `HUD : barre de dévoration`, `Outils : script d'installation`.

## Conventions de code

- **Lua** : indentation par tabulations, fins de ligne LF, commentaires en français qui disent le *pourquoi*. Les noms de variables et de fonctions restent en anglais ou en français selon le voisinage.
- **Logique pure dans `Shared/`** : ce qui se calcule sans le moteur ne doit pas appeler l'API de nanos world. C'est ce qui permet de le tester.
- **Les réglages vont dans `Shared/Config.lua`**, jamais en dur dans la logique. Un chiffre d'équilibrage doit pouvoir changer sans toucher au code.
- **Le serveur est autoritaire** : toute demande du client est validée (distance, coût, camp, limite, type). Le client n'envoie que des intentions.
- **Événements** : préfixe `wakfu:` (préfixe historique conservé). Un nouvel événement est ajouté dans la table de `docs/ARCHITECTURE.md`.
- **Un appel au moteur dont on n'est pas sûr** s'enveloppe dans `pcall` et se note dans « Jamais vérifié en jeu » de `docs/ARCHITECTURE.md`.
- **Le HUD** : HTML, CSS et JavaScript simples, sans bibliothèque. Les valeurs viennent du serveur ; le thème démon passe par la classe `html.demon`.

## Chaque fonctionnalité apporte

1. la logique pure et ses réglages ;
2. le branchement serveur, avec les validations ;
3. l'affichage dans le HUD si le joueur doit le voir ;
4. **un test de simulation** dans `tests/simulation/` (et si possible une vérification du HUD avec `--ui`) ;
5. la documentation.

## Ce qui ne doit jamais entrer dans le dépôt

- des **assets cuits** ou des gros fichiers (`.uasset`, `.uexp`, `.ubulk`, vidéos) : voir `.gitignore` et [docs/ASSETS.md](docs/ASSETS.md) ;
- tout **contenu extrait d'un jeu commercial** ;
- un **vrai `Config.toml`** (token, mot de passe, adresse) : seul `server/Config.example.toml` est versionné ;
- des **secrets** de toute sorte.

## Ajouter un asset

Suis le pipeline de [docs/ASSETS.md](docs/ASSETS.md) : import dans Unreal, cuisson avec Forge, master, régénération des listes, déclaration dans `Package.toml`. Documente l'origine et la licence du pack dans le tableau de ce document.

## En cas de doute

Un comportement du moteur que personne n'a vu en jeu est un risque, pas un fait. Écris-le, ne le cache pas : le premier lancement réel de chaque fonctionnalité est une étape du projet.
