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
            "SELECT character_id, name, faction_id, level, xp, reroll_count, "
            "skill_points_unspent, is_active "
            "FROM characters WHERE player_id = %s ORDER BY created_at",
            (player["player_id"],),
        )
        characters = cur.fetchall()

    player["player_id"] = str(player["player_id"])
    for character in characters:
        character["character_id"] = str(character["character_id"])
    return {"player": player, "characters": characters}
