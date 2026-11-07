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
from psycopg.rows import dict_row
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
            "SELECT player_id, steam_id, display_name, is_banned, last_login "
            "FROM player WHERE steam_id = %s",
            (steam_id,),
        )
        player = cur.fetchone()
        if player is None:
            raise HTTPException(status_code=404, detail="joueur inconnu")

        cur.execute(
            "SELECT character_id, name, faction_id, job, hp, max_hp, level, xp, "
            "reroll_count, skill_points_unspent, is_active "
            "FROM characters WHERE player_id = %s ORDER BY created_at",
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
    job: str | None = None
    hp: int | None = None
    max_hp: int | None = None
    level: int | None = None
    xp: int | None = None


@app.put("/characters/{character_id}/state", dependencies=[Depends(require_key)])
def save_state(character_id: str, body: StateIn, conn=Depends(db)):
    """Sauvegarde l'état d'un personnage : job, points de vie, niveau, expérience.
    Seuls les champs envoyés sont modifiés."""
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="aucun champ à sauvegarder")
    assignments = ", ".join(f"{name} = %s" for name in fields)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE characters SET {assignments} WHERE character_id = %s RETURNING character_id",
            (*fields.values(), character_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="personnage inconnu")
    return {"saved": list(fields.keys())}
