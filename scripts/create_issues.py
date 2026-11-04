"""Crée sur GitHub les étiquettes, les jalons et toutes les issues du projet, dans l'ordre de priorité.

    python scripts/create_issues.py --dry-run          # montre ce qui serait créé, sans rien envoyer
    python scripts/create_issues.py                    # crée ce qui manque (peut être relancé sans doublon)
    python scripts/create_issues.py --assign-a PSEUDO_A --assign-b PSEUDO_B

Les données sont dans scripts/issues.json : étiquettes, jalons et issues déjà triées (P0, puis P1, puis P2 ; à priorité égale,
dans l'ordre du calendrier). Les issues sont créées dans cet ordre : leur numéro GitHub suit donc la priorité.

Le jeton GitHub est lu dans la variable d'environnement GITHUB_TOKEN (ou GH_TOKEN), sinon demandé à `gh auth token`
si GitHub CLI est installé et connecté. Il n'est jamais affiché ni écrit. Droit nécessaire : « Issues : lecture et écriture ».

Le script est idempotent : une issue dont le titre commence déjà par « [A12] » n'est pas recréée. Une fois toutes les issues
créées, il remplace les références de la section « Dépend de » (A12, B1...) par des liens vers les numéros GitHub, et crée
ou met à jour l'issue « Feuille de route » qui liste tout dans l'ordre, avec des cases à cocher.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "issues.json"
API = "https://api.github.com"
TRACKING_TITLE = "Feuille de route : toutes les issues dans l'ordre de priorité"


def find_token():
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(name):
            return os.environ[name].strip()
    try:
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


class GitHub:
    def __init__(self, repo, token, dry_run, delay):
        self.repo, self.token, self.dry_run, self.delay = repo, token, dry_run, delay

    def request(self, method, path, payload=None, query=None):
        url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        for attempt in range(6):
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("X-GitHub-Api-Version", "2022-11-28")
            req.add_header("User-Agent", "pandora-kimetsu-issues")
            if self.token:
                req.add_header("Authorization", "Bearer " + self.token)
            if body is not None:
                req.add_header("Content-Type", "application/json; charset=utf-8")
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    text = response.read().decode("utf-8")
                    return json.loads(text) if text else None
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", "replace")
                limited = error.code in (403, 429) and ("rate limit" in detail.lower() or error.headers.get("Retry-After"))
                if limited and attempt < 5:
                    wait = int(error.headers.get("Retry-After") or 60)
                    print(f"  limite de débit atteinte : attente de {wait} s")
                    time.sleep(wait + 1)
                    continue
                sys.exit(f"Erreur GitHub {error.code} sur {method} {path} : {detail[:300]}")
        sys.exit(f"Trop de tentatives sur {method} {path}")

    def pages(self, path, query=None):
        out, page = [], 1
        while True:
            chunk = self.request("GET", path, query={**(query or {}), "per_page": 100, "page": page})
            out += chunk
            if len(chunk) < 100:
                return out
            page += 1

    def write(self, method, path, payload):
        """Une écriture : en simulation, on l'annonce sans l'envoyer ; sinon on l'envoie puis on attend un peu."""
        if self.dry_run:
            return None
        result = self.request(method, path, payload)
        time.sleep(self.delay)
        return result


def sync_labels(gh, labels):
    existing = {item["name"].lower(): item for item in gh.pages(f"/repos/{gh.repo}/labels")}
    for label in labels:
        current = existing.get(label["name"].lower())
        if current is None:
            print("  étiquette à créer :", label["name"])
            gh.write("POST", f"/repos/{gh.repo}/labels", label)
        elif current["color"].lower() != label["color"].lower() or (current["description"] or "") != label["description"]:
            print("  étiquette à mettre à jour :", label["name"])
            gh.write("PATCH", f"/repos/{gh.repo}/labels/{urllib.parse.quote(current['name'])}", label)


def sync_milestones(gh, milestones):
    existing = {item["title"]: item["number"] for item in gh.pages(f"/repos/{gh.repo}/milestones", {"state": "all"})}
    for milestone in milestones:
        if milestone["title"] not in existing:
            print("  jalon à créer :", milestone["title"])
            created = gh.write("POST", f"/repos/{gh.repo}/milestones", milestone)
            existing[milestone["title"]] = created["number"] if created else 0
    return existing


def key_of(title):
    found = re.match(r"\[([A-Z]+\d+)\]", title)
    return found.group(1) if found else None


def link_dependencies(body, numbers):
    """Dans la section « Dépend de », remplace chaque identifiant de tâche par un lien vers l'issue GitHub."""
    marker = "**Dépend de**"
    if marker not in body:
        return body
    head, tail = body.split(marker, 1)
    section, rest = (tail.split("\n\n**", 1) + [""])[:2] if "\n\n**" in tail else (tail, "")
    section = re.sub(r"(?<![#\w])([ABX]\d+)\b", lambda m: f"#{numbers[m.group(1)]} ({m.group(1)})" if m.group(1) in numbers else m.group(0), section)
    return head + marker + section + ("\n\n**" + rest if rest else "")


def sync_issues(gh, issues, milestones, assignees):
    existing = {}
    for item in gh.pages(f"/repos/{gh.repo}/issues", {"state": "all"}):
        if "pull_request" not in item and key_of(item["title"]):
            existing[key_of(item["title"])] = item
    numbers = {key: item["number"] for key, item in existing.items()}
    created = []
    for issue in issues:
        key = issue["key"]
        if key in existing:
            print(f"  #{existing[key]['number']:<3} {key:4s} existe déjà")
            continue
        assigned = assignees.get("dev-a" if "dev-a" in issue["labels"] else "dev-b")
        payload = {"title": issue["title"], "body": issue["body"], "labels": issue["labels"], "milestone": milestones[issue["milestone"]] or None}
        if assigned:
            payload["assignees"] = [assigned]
        print(f"  créer {key:4s} {issue['milestone'][:2]} {', '.join(issue['labels'][:3])} : {issue['title']}" + ("  (puis fermer : déjà fait)" if issue["state"] == "closed" else ""))
        result = gh.write("POST", f"/repos/{gh.repo}/issues", payload)
        if result:
            numbers[key] = result["number"]
            existing[key] = result
            created.append(key)
            if issue["state"] == "closed":
                gh.write("PATCH", f"/repos/{gh.repo}/issues/{result['number']}", {"state": "closed", "state_reason": "completed"})
    return existing, numbers, created


def refresh_links(gh, issues, existing, numbers, created):
    """Deuxième passage : les références de dépendance deviennent des liens (seulement pour les issues qu'on vient de créer)."""
    for issue in issues:
        key = issue["key"]
        if key not in created:
            continue
        linked = link_dependencies(issue["body"], numbers)
        if linked != issue["body"]:
            print(f"  liens de dépendance : #{numbers[key]} {key}")
            gh.write("PATCH", f"/repos/{gh.repo}/issues/{numbers[key]}", {"body": linked})


def tracking_body(issues, numbers, milestones):
    lines = [
        "Toutes les issues du projet, **dans l'ordre de priorité** : à faire de haut en bas. Les numéros suivent cet ordre.",
        "",
        "- **Dev A** (`dev-a`) : le jeu et l'interface, surtout `packages/kimetsu-pandora`.",
        "- **Dev B** (`dev-b`) : le serveur, le contenu et les outils.",
        "- Les deux développeurs peuvent avancer en parallèle : une issue de Dev A n'attend Dev B que si elle l'écrit dans « Dépend de ».",
        "- Cases cochées = fait (GitHub les coche aussi quand l'issue est fermée).",
        "",
    ]
    for title, description in milestones:
        lines += [f"## {title}", description, ""]
        for issue in issues:
            if issue["milestone"] == title:
                who = "A" if "dev-a" in issue["labels"] else "B"
                box = "x" if issue["state"] == "closed" else " "
                lines.append(f"- [{box}] #{numbers.get(issue['key'], '?')} · Dev {who} · {issue['title'].split('] ', 1)[1]}")
        lines.append("")
    lines.append("*Documents : `README.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md`. Cette issue est générée par `scripts/create_issues.py`.*")
    return "\n".join(lines)


def sync_tracking(gh, issues, numbers, milestones_info):
    body = tracking_body(issues, numbers, milestones_info)
    found = [item for item in gh.pages(f"/repos/{gh.repo}/issues", {"state": "all"}) if item["title"] == TRACKING_TITLE and "pull_request" not in item]
    if found:
        print(f"  mise à jour de la feuille de route (#{found[0]['number']})")
        gh.write("PATCH", f"/repos/{gh.repo}/issues/{found[0]['number']}", {"body": body})
    else:
        print("  création de la feuille de route")
        gh.write("POST", f"/repos/{gh.repo}/issues", {"title": TRACKING_TITLE, "body": body, "labels": ["suivi"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="n'écrit rien sur GitHub : liste seulement ce qui serait fait")
    parser.add_argument("--assign-a", metavar="PSEUDO", help="pseudo GitHub du développeur A (assigné aux issues dev-a)")
    parser.add_argument("--assign-b", metavar="PSEUDO", help="pseudo GitHub du développeur B (assigné aux issues dev-b)")
    parser.add_argument("--delay", type=float, default=2.0, help="secondes d'attente entre deux créations (défaut 2, pour la limite anti-abus de GitHub)")
    args = parser.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    token = find_token()
    if not token and not args.dry_run:
        sys.exit("Aucun jeton GitHub : définis GITHUB_TOKEN, ou installe GitHub CLI et lance `gh auth login`.")
    gh = GitHub(data["repo"], token, args.dry_run, args.delay)
    print(("SIMULATION : rien ne sera écrit. " if args.dry_run else "") + f"Dépôt : {data['repo']} · {len(data['issues'])} issues")
    if args.dry_run and not token:
        for issue in data["issues"]:
            print(f"  {issue['rank']:2d}. {issue['key']:4s} {issue['milestone'][:2]} {', '.join(issue['labels'][:3])} : {issue['title']}")
        print("(Pas de jeton : la simulation n'a pas interrogé GitHub, elle liste seulement le contenu du fichier.)")
        return

    print("Étiquettes")
    sync_labels(gh, data["labels"])
    print("Jalons")
    milestones = sync_milestones(gh, data["milestones"])
    print("Issues, dans l'ordre de priorité")
    assignees = {"dev-a": args.assign_a, "dev-b": args.assign_b}
    existing, numbers, created = sync_issues(gh, data["issues"], milestones, assignees)
    if not args.dry_run:
        print("Liens entre issues")
        refresh_links(gh, data["issues"], existing, numbers, created)
        print("Feuille de route")
        sync_tracking(gh, data["issues"], numbers, [(m["title"], m["description"]) for m in data["milestones"]])
    print(f"Terminé : {len(created)} issues créées." if not args.dry_run else "Simulation terminée.")


if __name__ == "__main__":
    main()
