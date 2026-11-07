"""API HTTP de Kimetsu Pandora : seul composant qui parle à PostgreSQL.

Le serveur nanos l'appelle (HTTP, côté serveur uniquement). Chaque requête doit
porter l'en-tête `X-API-Key` égal à la variable d'environnement `KIMETSU_API_KEY`.

Lancement (depuis server/api) :
    set DATABASE_URL=postgresql://user:motdepasse@localhost:5432/kimetsu
    set KIMETSU_API_KEY=une-cle-longue-et-secrete
    uvicorn app:app --host 127.0.0.1 --port 8080
"""

import os
import secrets

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel

DATABASE_URL = os.environ["DATABASE_URL"]
API_KEY = os.environ["KIMETSU_API_KEY"]

app = FastAPI(title="Kimetsu Pandora API", version="0.1.0")


def require_key(x_api_key: str = Header(default="")) -> None:
    # Comparaison à temps constant pour éviter les attaques par chronométrage.
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="clé API invalide")


def db():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/players/{steam_id}", dependencies=[Depends(require_key)])
def get_player(steam_id: str, conn=Depends(db)):
    """Renvoie le joueur et ses personnages, à partir de son SteamID."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT player_id, steam_id, display_name, is_banned, last_login, playtime_seconds "
            "FROM player WHERE steam_id = %s",
            (steam_id,),
        )
        player = cur.fetchone()
        if player is None:
            raise HTTPException(status_code=404, detail="joueur inconnu")

        cur.execute(
            "SELECT c.character_id, c.name, c.faction_id, c.job, c.hp, c.max_hp, c.level, c.xp, "
            "c.reroll_count, c.skill_points_unspent, c.is_active, c.game_state, ca.appearance "
            "FROM characters c LEFT JOIN character_appearance ca ON ca.character_id = c.character_id "
            "WHERE c.player_id = %s ORDER BY c.created_at",
            (player["player_id"],),
        )
        characters = cur.fetchall()

    player["player_id"] = str(player["player_id"])
    for character in characters:
        character["character_id"] = str(character["character_id"])
    return {"player": player, "characters": characters}


class LoginIn(BaseModel):
    display_name: str | None = None


@app.post("/players/{steam_id}/login", dependencies=[Depends(require_key)])
def login(steam_id: str, body: LoginIn, conn=Depends(db)):
    """Crée le joueur s'il n'existe pas, met à jour sa dernière connexion, et crée son inventaire."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO player (steam_id, display_name, last_login) VALUES (%s, %s, now()) "
            "ON CONFLICT (steam_id) DO UPDATE SET last_login = now() "
            "RETURNING player_id",
            (steam_id, body.display_name),
        )
        player_id = cur.fetchone()["player_id"]
        cur.execute(
            "INSERT INTO inventory (player_id) VALUES (%s) ON CONFLICT (player_id) DO NOTHING",
            (player_id,),
        )
    return {"player_id": str(player_id)}


class CharacterIn(BaseModel):
    name: str
    faction_id: int
    job: str | None = None
    hp: int | None = None
    max_hp: int | None = None


@app.post("/players/{steam_id}/characters", dependencies=[Depends(require_key)])
def create_character(steam_id: str, body: CharacterIn, conn=Depends(db)):
    """Crée un personnage pour le joueur, avec sa ligne de statistiques de combat."""
    with conn.cursor() as cur:
        cur.execute("SELECT player_id FROM player WHERE steam_id = %s", (steam_id,))
        player = cur.fetchone()
        if player is None:
            raise HTTPException(status_code=404, detail="joueur inconnu : appeler /login d'abord")
        cur.execute(
            "INSERT INTO characters (player_id, faction_id, name, job, hp, max_hp) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING character_id",
            (player["player_id"], body.faction_id, body.name, body.job, body.hp, body.max_hp),
        )
        character_id = cur.fetchone()["character_id"]
        cur.execute("INSERT INTO combat_stats (character_id) VALUES (%s)", (character_id,))
    return {"character_id": str(character_id)}


class StateIn(BaseModel):
    name: str | None = None
    faction_id: int | None = None
    game: dict | None = None
    job: str | None = None
    hp: int | None = None
    max_hp: int | None = None
    level: int | None = None
    xp: int | None = None


@app.put("/characters/{character_id}/state", dependencies=[Depends(require_key)])
def save_state(character_id: str, body: StateIn, conn=Depends(db)):
    """Sauvegarde l'état d'un personnage : job, points de vie, niveau, expérience.
    Seuls les champs envoyés sont modifiés."""
    fields = {k: v for k, v in body.model_dump().items() if v is not None and k != "game"}
    game = body.game
    if not fields and game is None:
        raise HTTPException(status_code=400, detail="aucun champ à sauvegarder")
    assignments = [f"{name} = %s" for name in fields]
    values = list(fields.values())
    if game is not None:
        assignments.append("game_state = %s")
        values.append(Jsonb(game))
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE characters SET " + ", ".join(assignments) + " WHERE character_id = %s RETURNING character_id",
            (*values, character_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="personnage inconnu")
    return {"saved": list(fields.keys()) + (["game"] if game is not None else [])}


class AppearanceIn(BaseModel):
    appearance: dict


@app.put("/characters/{character_id}/appearance", dependencies=[Depends(require_key)])
def save_appearance(character_id: str, body: AppearanceIn, conn=Depends(db)):
    """Sauvegarde l'apparence du personnage (sexe, couleur, peau, pseudo... au format du jeu)."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM characters WHERE character_id = %s", (character_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="personnage inconnu")
        cur.execute(
            "INSERT INTO character_appearance (character_id, appearance, updated_at) "
            "VALUES (%s, %s, now()) "
            "ON CONFLICT (character_id) DO UPDATE SET appearance = EXCLUDED.appearance, "
            "version = character_appearance.version + 1, updated_at = now()",
            (character_id, Jsonb(body.appearance)),
        )
    return {"saved": True}


class PlaytimeIn(BaseModel):
    seconds: int = Field(ge=0, le=86400)  # temps écoulé depuis la dernière sauvegarde


@app.put("/players/{steam_id}/playtime", dependencies=[Depends(require_key)])
def add_playtime(steam_id: str, body: PlaytimeIn, conn=Depends(db)):
    """Ajoute du temps de jeu au total du joueur."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE player SET playtime_seconds = playtime_seconds + %s WHERE steam_id = %s "
            "RETURNING playtime_seconds",
            (body.seconds, steam_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="joueur inconnu : appeler /login d'abord")
    return {"playtime_seconds": row["playtime_seconds"]}


class InvItem(BaseModel):
    code: str
    count: int = 1
    slot: int | None = None        # position dans le sac (NULL si équipé)
    equip_slot: str | None = None  # emplacement d'équipement (NULL si dans le sac)


class InventoryIn(BaseModel):
    items: list[InvItem]


@app.get("/players/{steam_id}/inventory", dependencies=[Depends(require_key)])
def get_inventory(steam_id: str, conn=Depends(db)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT it.code, ii.quantity AS count, ii.slot, ii.equip_slot "
            "FROM item_instance ii "
            "JOIN inventory inv ON inv.inventory_id = ii.inventory_id "
            "JOIN player p ON p.player_id = inv.player_id "
            "JOIN item it ON it.item_id = ii.item_id "
            "WHERE p.steam_id = %s ORDER BY ii.instance_id",
            (steam_id,),
        )
        return {"items": cur.fetchall()}


@app.put("/players/{steam_id}/inventory", dependencies=[Depends(require_key)])
def save_inventory(steam_id: str, body: InventoryIn, conn=Depends(db)):
    """Remplace tout l'inventaire du joueur par celui envoyé (sac et équipement)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT inv.inventory_id FROM inventory inv "
            "JOIN player p ON p.player_id = inv.player_id WHERE p.steam_id = %s",
            (steam_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="joueur inconnu : appeler /login d'abord")
        inventory_id = row["inventory_id"]
        cur.execute("DELETE FROM item_instance WHERE inventory_id = %s", (inventory_id,))
        for entry in body.items:
            cur.execute(
                "INSERT INTO item (code, name, category) VALUES (%s, %s, 'unknown') "
                "ON CONFLICT (code) DO NOTHING",
                (entry.code, entry.code),
            )
            cur.execute("SELECT item_id FROM item WHERE code = %s", (entry.code,))
            item_id = cur.fetchone()["item_id"]
            cur.execute(
                "INSERT INTO item_instance (item_id, inventory_id, quantity, slot, equip_slot, is_equipped) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (item_id, inventory_id, entry.count, entry.slot, entry.equip_slot,
                 entry.equip_slot is not None),
            )
    return {"saved": len(body.items)}
