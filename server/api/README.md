# API Kimetsu Pandora

Le serveur nanos ne parle pas directement à PostgreSQL. Cette API est le seul composant qui lit et écrit dans la base. Le serveur nanos l'appelle en HTTP, côté serveur uniquement.

## Fichiers
- `schema.sql` : schéma PostgreSQL, tiré de `docs/DATABASE-SCHEMA.mmd`.
- `app.py` : API FastAPI. Une seule route pour l'instant : `GET /players/{steam_id}`.
- `requirements.txt` : dépendances Python.

## Mise en place (test local)
1. Installer PostgreSQL, puis créer la base :
   ```
   createdb kimetsu
   psql -d kimetsu -f schema.sql
   ```
2. Installer les dépendances :
   ```
   pip install -r requirements.txt
   ```
3. Lancer l'API :
   ```
   set DATABASE_URL=postgresql://user:motdepasse@localhost:5432/kimetsu
   set KIMETSU_API_KEY=une-cle-longue-et-secrete
   uvicorn app:app --host 127.0.0.1 --port 8080
   ```
4. Tester : `curl -H "X-API-Key: une-cle-longue-et-secrete" http://127.0.0.1:8080/players/76561198000000000`

## Points à savoir
- Le schéma et l'API n'ont pas encore été testés contre une vraie base PostgreSQL.
- `character` est renommée `characters` dans la base, pour éviter le mot réservé.
- `transaction` est renommée `transactions` pour la même raison.
- La clé API ne doit jamais être commitée. Elle se met dans les variables d'environnement, ou plus tard dans `custom_settings` de `Config.toml` côté serveur nanos.
- L'API ne doit pas être exposée sur Internet sans protection.
