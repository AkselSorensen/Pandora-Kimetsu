# gmod2nanos — Garry's Mod Workshop → nanos world

Site web qui récupère des addons du **Steam Workshop de Garry's Mod** et les convertit en **Asset Pack nanos world**.

## Ce qui est converti

| Garry's Mod | → | nanos world |
|---|---|---|
| Modèles compilés `.mdl` + `.vvd` + `.vtx` | → | glTF (`.gltf` + `.bin`) avec matériaux, à importer dans Unreal |
| Modèles décompilés `.smd` (+ `.qc`, ex. via Crowbar) | → | glTF, idem |
| Matériaux `.vmt` / textures `.vtf` | → | matériaux glTF + textures `.png` (couleur, normal map, transparence, double face) |
| Sons `.wav` / `.mp3` / `.ogg` | → | `.ogg` utilisables **directement** (`assets://pack/Sounds/...`) |
| Playermodels (squelette `ValveBiped`) | → | Skeletal Mesh reciblé sur `SKEL_Mannequin` + `PHYS_Mannequin`, utilisable avec `Character` |
| Armes blanches tenues en main (world models liés à l'os `Bip01_R_Hand`) | → | glTF déjà orienté pour nanos world (poignée à l'origine, pointe vers +X, dos vers +Z) + `weapons.json` |
| Collections du Workshop | → | tous les addons de la collection dans un seul pack |

Non convertis : le Lua GMod (API incompatible), les maps `.bsp`, les animations GMod (les personnages utilisent celles de
nanos world). Les autres modèles riggés (bras de vue, NPC non humains) sont exportés en mesh statique.

### Armes

Un world model GMod est lié à l'os de la main droite : sa géométrie est décrite dans le repère de cet os. nanos world tient
un `Melee` dans `hand_r_socket` avec le repère du Katana_sword de référence (lame vers +Z, tranchant vers +X, plats vers ±Y,
origine à la poignée), mesuré avec `unreal_tools/measure_weapon_frames.py`.
`gmod2nanos/grip.py` calcule la transformation entre les deux et la fixe dans le mesh à la conversion : l'arme est tenue
correctement sans aucun réglage d'os ni de socket, ni par arme.

- la pointe est le bout le plus éloigné de la main, le tranchant est du côté +X de l'os (mesuré sur 176 armes : les 17
  katanas se courbent toutes vers -X, côté du dos), l'origine est le centre de la poignée à hauteur de la main ;
- l'importeur glTF d'Unreal 5.7 convertit les axes avec `UE = (glTF.x, glTF.z, glTF.y)` (mesuré sur un `.uexp` cuit) : le
  mesh est précompensé, sinon l'avant de l'arme arrive sur +Y d'Unreal et l'arme est tenue de travers ;
- `unreal_tools/measure_weapon_frames.py` (à lancer dans Unreal) mesure le repère d'un mesh d'arme : à utiliser pour
  comparer à une arme de référence bien tenue ;
- le test en jeu (`3-package-test`) donne l'arme au personnage du joueur : flèches gauche / droite pour changer d'arme ;
- si toutes les armes sont décalées de la même façon, un seul réglage commun suffit (`WEAPON_GRIP`, appliqué avec
  `Melee:SetAttachmentSettings`) ;
- non géré pour l'instant : les armes à feu (point `muzzle`), dont le repère de main est différent.

### Personnages

nanos world n'accepte que des personnages sur le squelette du Mannequin UE4. Le site exporte le playermodel avec son
squelette ValveBiped (`Characters/SK_*_source.gltf`) ; le script d'import Unreal lit ensuite `SKEL_Mannequin` dans l'ADK,
et `gmod2nanos/retarget.py` :

1. tourne le modèle pour qu'il regarde dans la même direction que le Mannequin ;
2. plie bras, mains, doigts, jambes et pieds pour reproduire la pose de référence du Mannequin (A-pose) ;
3. lie le maillage à des os portant les noms, la hiérarchie et l'orientation du Mannequin, placés aux articulations du
   modèle GMod (ses proportions sont conservées) ;
4. importe le résultat et lui assigne `SKEL_Mannequin` et `PHYS_Mannequin`.

### Pourquoi passer par Unreal ?

nanos world ne charge que des assets **cuisinés par Unreal Engine** (`.uasset`). Le site prépare donc tout
(`Assets.toml` déjà rempli, modèles, textures, script d'import Unreal, package Lua de test). Il ne reste qu'à lancer
le script dans le projet Unreal de nanos world (ADK), cuisiner, puis copier le résultat. Les étapes sont détaillées dans le
`LISEZMOI.md` du zip généré.

## Lancer le site

```bash
pip install -r requirements.txt
uvicorn gmod2nanos.app:app --host 0.0.0.0 --port 8000
```

Puis ouvre http://localhost:8000. `ffmpeg` doit être installé pour convertir les sons.

Ou avec Docker :

```bash
docker build -t gmod2nanos .
docker run -p 8000:8000 gmod2nanos
```

### Téléchargement depuis le Workshop

Les anciens addons ont un lien de téléchargement direct. Les plus récents passent par **SteamCMD** (connexion anonyme).
Si SteamCMD n'est pas trouvé (`STEAMCMD` ou `PATH`), le site le télécharge automatiquement dans `~/.gmod2nanos/steamcmd`
la première fois (Windows, Linux, macOS). Les addons téléchargés sont gardés en cache : reconvertir le même addon
ne le retélécharge pas (sauf s'il a été mis à jour sur le Workshop).

### Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `GMOD2NANOS_DATA` | `./data` | dossier de travail des conversions |
| `GMOD2NANOS_MAX_BYTES` | 2 Go | taille max d'un addon ou d'un envoi |
| `GMOD2NANOS_MAX_COLLECTION` | 50 | nombre max d'addons par collection |
| `GMOD2NANOS_WORKERS` | 2 | conversions en parallèle |
| `GMOD2NANOS_JOB_TTL` | 6 h | durée de conservation des résultats |
| `STEAMCMD` | — | chemin de SteamCMD (sinon installé automatiquement) |
| `GMOD2NANOS_TOOLS` | `~/.gmod2nanos` | dossier de SteamCMD et du cache des addons téléchargés |
| `GMOD2NANOS_CACHE_BYTES` | 10 Go | taille max du cache d'addons (`0` pour le désactiver) |
| `GMOD2NANOS_THREADS` | nb de cœurs (max 8) | conversions de textures/sons en parallèle |

## API

- `GET /api/workshop/{lien ou id}` : infos sur un addon ou une collection
- `POST /api/jobs` `{"workshop": "...", "title": "", "author": "", "pack_name": "", "scale": 0.0254}` : lance une conversion
- `POST /api/jobs/upload` (multipart `file` + mêmes options) : convertit un `.gma`, un `.zip` ou un `.smd` envoyé
- `GET /api/jobs/{id}` : état et journal
- `GET /api/jobs/{id}/download` : zip du résultat

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests fabriquent de vrais fichiers Source (`.gma`, `.mdl`/`.vvd`/`.vtx`, `.vtf`, `.vmt`, `.smd`, `.qc`) et vérifient la
conversion de bout en bout.

## Structure

```
gmod2nanos/
  app.py          API FastAPI + service de l'interface
  jobs.py         file de conversions en arrière-plan
  workshop.py     API Steam + SteamCMD
  gma.py          archives .gma (y compris compressées LZMA)
  mdl.py          lecture .mdl / .vvd / .vtx (os de la main, points d'attache)
  grip.py         prise en main des armes blanches (repère de nanos world)
  smd.py          lecture .smd / .qc
  materials.py    .vmt / .vtf → PNG
  gltf.py         écriture glTF 2.0
  audio.py        conversion en .ogg (ffmpeg)
  converter.py    orchestration et génération du pack
  templates/      Assets.toml, Package.toml, Lua, LISEZMOI, script d'import Unreal
web/              interface (HTML/CSS/JS)
tests/
```

Respecte les licences : demande l'accord des créateurs avant de republier leurs assets.
