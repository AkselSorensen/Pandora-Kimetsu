# Les assets

Les modèles, animations et effets du jeu sont des **packs d'assets nanos world** : des dossiers `Assets/<pack>/` avec un `Assets.toml` et des fichiers Unreal cuits (`.uasset`, `.uexp`, `.ubulk`). Ils ne sont **jamais dans le dépôt** : trop lourds (des centaines de Mo) et soumis chacun à sa licence. Ce document dit ce qu'ils sont, d'où ils viennent et comment les produire.

## Règle du projet

**Aucun asset extrait d'un jeu commercial** (modèles, effets, animations, textures) ne doit entrer dans le projet. Les assets viennent de trois sources seulement : des packs achetés ou gratuits avec licence claire (Fab), des addons publiés sur le Steam Workshop de Garry's Mod convertis par `tools/gmod2nanos`, et des créations originales du projet.

## Les packs de la partie propre

| Pack nanos | Dossier Unreal | Contenu | Origine et droits |
|---|---|---|---|
| `pandora-demonslayer` | `YufuPmVaasContent` (republié sous ce nom par l'alias du master) | les personnages Demon Slayer (environ 83 apparences) | convertis d'addons du Steam Workshop de Garry's Mod ; droits de tiers à vérifier avant toute diffusion publique |
| `aksel-animations` | `Katana_Animations` | animations du katana et mesh `Katana_sword` | origine à documenter par le projet |
| `scythe` | `Scythe` | animations de faux et mesh de faux | Scythe Animation Pack (UE5), retargeté sur le mannequin nanos par `import_scythe_pack.py` |
| `yufu-arme-test` | `YufuArmeTest` | 176 lames | addon GMod « [YUFU] Arme Test » converti par `gmod2nanos` (orientation de la main fixée à la conversion) |
| `vefects` | `Vefects` | 10 traînées Niagara | Vefects Essential Trails |
| `free-magic`, `free-spells`, `sword-trail-vfx` | `Free_Magic`, `Free_Spells`, `SwordTrailVFX` | 17, 18 et 18 systèmes Niagara | packs Fab, licences Fab |
| `breath-fx` | `BreathFx` | 12 formes lumineuses et 10 matériaux (une couleur par voie) | **original** : généré par `tools/unreal_tools/gen_fx_meshes.py` puis importé par `import_fx_meshes.py` |

Le nom d'un pack nanos vient du dossier de plus haut niveau de `Content/` dans Unreal, passé en minuscules avec des tirets (`Free_Magic` donne `free-magic`).

## Ce qui n'est volontairement pas dans le dépôt

- `packages/kimetsu-pandora-loading/bg.webm` : la vidéo de fond de l'écran de chargement (16 Mo). Dépose la tienne à cet endroit pour activer l'écran.
- `packages/kimetsu-pandora/Client/UI/img/reroll/` et `img/logo.png` : des images de l'ancien projet Wakfu, plus utilisées par le code. Elles sont ignorées par `.gitignore` et peuvent être supprimées.
- Le dossier `askel` (un lot d'effets et de modèles extrait d'un jeu commercial) : il **ne doit pas** être utilisé, voir la règle du projet.
- `tools/data/` : le cache de téléchargement du convertisseur GMod.

## Produire un pack : le pipeline

1. **Source** : un addon GMod (converti en glTF par `tools/gmod2nanos`), un pack Fab, ou une création originale (les formes d'effet sont dessinées par le code).
2. **Import dans Unreal 5.7** avec les scripts de `tools/unreal_tools/` (à lancer avec `py "<chemin>"` dans le champ Cmd d'Unreal ; le résultat apparaît dans le journal, filtré par le préfixe du script).
3. **Liste de cuisson** : le dossier doit figurer dans `Config/DefaultGame.ini` du projet Unreal (`+DirectoriesToAlwaysCook=(Path="/Game/<Dossier>")`, fichier en CRLF). Les dossiers de démonstration (`Demo`) vont dans `DirectoriesToNeverCook`. Redémarrer Unreal après un changement.
4. **Cuisson** avec le plugin **Forge** : elle écrit dans `Assets/<pack>` du serveur de test.
5. **Master cumulatif** : Forge réécrit `Assets.toml` à chaque cuisson et efface ce qui n'est plus dans le projet. Le master garde tout :
   ```
   python -m gmod2nanos.master sync <pack> --deploy <pack>     # une fois
   nanos-master-watch.bat                                      # en continu pendant qu'on cuit
   ```
   (à lancer depuis `tools/`).
6. **Régénérer les listes** du mode de jeu, serveur par serveur :
   ```
   python tools/unreal_tools/gen_vfx_assets.py      # VfxAssets.lua et FxMeshAssets.lua
   python tools/unreal_tools/gen_yufu_weapons.py    # YufuWeapons.lua
   ```
   Les chemins des serveurs sont en tête de chaque script.
7. **Déclarer le pack** : l'ajouter à `assets_requirements` dans `packages/kimetsu-pandora/Package.toml` (seulement une fois cuit : sinon le mode de jeu ne se charge plus) et à `assets` dans `Config.toml`.

## Les scripts Unreal (`tools/unreal_tools/`)

| Script | Rôle |
|---|---|
| `prepare_vfx.py` | vérifie que les systèmes Niagara se chargent et prépare leur cuisson |
| `import_fx_meshes.py`, `check_fx_meshes.py` | importe les formes d'effet, crée le matériau lumineux et ses couleurs ; vérifie le résultat |
| `import_katana_pack.py`, `import_scythe_pack.py`, `lock_root_motion.py` | animations du katana et de la faux, mouvement de racine |
| `gen_fx_meshes.py` | dessine les 12 formes d'effet en glTF (dans `tools/fx_meshes/`) |
| `gen_vfx_assets.py`, `gen_yufu_weapons.py`, `gen_anim_list.py` | génèrent les listes Lua à partir des packs cuits |
| `measure_weapon_frames.py` | mesure le repère d'une arme de référence |

L'import glTF d'Unreal 5.7 envoie `(x, y, z)` du glTF sur `(x, z, y)` d'Unreal et multiplie les mètres par 100 ; les générateurs en tiennent compte.
