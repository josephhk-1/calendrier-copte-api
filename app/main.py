from fastapi import FastAPI, Query, HTTPException
import datetime, json, os
from . import calendar_core as cc
from . import search_index

# Chemin vers le fichier de données, configurable via une variable d'environnement
DATA_PATH = os.environ.get("MASTER_DATA_PATH", "data/master_data.json")

# Chargement des données au démarrage de l'application
with open(DATA_PATH, "r", encoding="utf-8") as f:
    MASTER_DATA = json.load(f)

# Construction de l'index de recherche au démarrage
SEARCH_INDEX = search_index.build_indices(MASTER_DATA)

# Initialisation de l'application FastAPI
app = FastAPI(title="Coptic Calendar API", version=MASTER_DATA.get("version", "0.0.0"))

@app.get("/health")
def health():
    """Endpoint pour vérifier que l'API est en ligne."""
    return {"status": "ok", "version": MASTER_DATA.get("version")}

@app.get("/day")
def get_day_info(date: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"), lang: str = "ar"):
    """Retourne les informations liturgiques pour une date spécifique."""
    try:
        d = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD.")
    return cc.build_day(MASTER_DATA, d, lang)

@app.get("/week")
def get_week_info(start: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"), lang: str = "ar"):
    """Retourne les informations pour une semaine à partir d'une date de début."""
    try:
        d = datetime.date.fromisoformat(start)
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD.")
    return cc.build_week(MASTER_DATA, d, lang)

@app.get("/year")
def get_year_info(year: int, lang: str = "ar"):
    """Retourne les informations pour une année complète."""
    cache = cc.build_year_cache(MASTER_DATA, year, lang)
    return {"year": year, "lang": lang, "days": cache}

@app.get("/search")
def search_data(q: str, lang: str = "ar", type: str = "all", limit: int = 20, offset: int = 0):
    """Endpoint de recherche dans les données (saints et fêtes)."""
    if lang not in ("ar", "fr"):
        raise HTTPException(status_code=400, detail="Langue non supportée. Utilisez 'ar' ou 'fr'.")
    if type not in ("all", "saint", "feast"):
        raise HTTPException(status_code=400, detail="Type de recherche non supporté. Utilisez 'all', 'saint', ou 'feast'.")
    return search_index.search(q, lang, SEARCH_INDEX, type_filter=type, limit=limit, offset=offset)