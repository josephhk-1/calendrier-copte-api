import json, pathlib, sys, collections, itertools, datetime

# On importe les fonctions de l'application pour les utiliser dans le script
# Pour que cela fonctionne, vous devrez lancer le script depuis le dossier racine du projet.
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from app import calendar_core as cc

# Compteurs pour les erreurs
CRITICAL = 0
WARNINGS = 0

def fail(msg):
    """Affiche une erreur critique et incrémente le compteur."""
    global CRITICAL
    print(f"CRITICAL: {msg}")
    CRITICAL += 1

def warn(msg):
    """Affiche un avertissement."""
    global WARNINGS
    print(f"WARNING:  {msg}")
    WARNINGS += 1

def main():
    """Fonction principale du script d'audit."""
    print("--- Lancement de l'audit des données ---")
    data = json.loads(pathlib.Path("data/master_data.json").read_text(encoding="utf-8"))

    # 1. Vérifier les IDs de saints dupliqués
    ids = [s["id"] for s in data.get("saints", [])]
    dup_ids = [k for k, v in collections.Counter(ids).items() if v > 1]
    if dup_ids:
        fail(f"IDs de saints dupliqués trouvés : {dup_ids}")

    # 2. Vérifier les codes de fêtes dupliqués
    feast_codes = [f["code"] for f in data.get("feasts_fixed", [])] + [f["code"] for f in data.get("feasts_movable", [])]
    dup_codes = [k for k, v in collections.Counter(feast_codes).items() if v > 1]
    if dup_codes:
        fail(f"Codes de fêtes dupliqués trouvés : {dup_codes}")

    # 3. Vérifier les saints qui n'apparaissent dans aucune commémoration
    commemorated_ids = set(itertools.chain.from_iterable(
        [r["liste_saints"] for r in data.get("daily_commemorations", [])]
    ))
    uncommemorated_saints = [s["id"] for s in data.get("saints", []) if s["id"] not in commemorated_ids]
    if uncommemorated_saints:
        warn(f"{len(uncommemorated_saints)} saints n'ont pas de commémoration journalière (ex: {uncommemorated_saints[:5]})")

    # 4. Vérifier les saints listés dans les commémorations mais qui n'existent pas
    all_saint_ids = set(ids)
    non_existent_saints = commemorated