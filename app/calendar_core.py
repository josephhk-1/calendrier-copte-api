# -*- coding: utf-8 -*-
import datetime, json, math, pathlib
from typing import Dict, Any, List

# --- Constantes ---
COPTIC_MONTHS_AR = ["توت","بابه","هاتور","كيهك","طوبه","أمشير","برمهات","برموده","بشنس","بؤونه","أبيب","مسرى","النسئ"]
MAJOR_FEAST_CODES = {"ANNUNCIATION", "NATIVITY", "THEOPHANY", "PASCHA", "ASCENSION", "PENTECOST", "TRANSFIGURATION"}
PARAMON_CODES = {"NATIVITY_PARAMON", "THEOPHANY_PARAMON"}
WEEKDAY_MAP = {"MON": "MON", "TUE": "TUE", "WED": "WED", "THU": "THU", "FRI": "FRI", "SAT": "SAT", "SUN": "SUN"}


# --- Fonctions de base du calendrier ---

def is_gregorian_leap(year: int) -> bool:
    """Vérifie si une année grégorienne est bissextile."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def gregorian_to_coptic(gdate: datetime.date) -> Dict[str, Any]:
    """Convertit une date grégorienne en date copte."""
    y = gdate.year
    new_year_day = 12 if is_gregorian_leap(y - 1) else 11
    cny = datetime.date(y, 9, new_year_day)
    
    if gdate >= cny:
        delta = (gdate - cny).days
        coptic_year = y - 284
    else:
        y_prev = y - 1
        cny_prev = datetime.date(y_prev, 9, 12 if is_gregorian_leap(y_prev - 1) else 11)
        delta = (gdate - cny_prev).days
        coptic_year = y_prev - 284
        
    day_abs = delta + 1
    is_coptic_leap = (coptic_year + 1) % 4 == 0
    
    if day_abs <= 360:
        month = (day_abs - 1) // 30 + 1
        day = (day_abs - 1) % 30 + 1
    else: # Mois de Nasi
        month = 13
        day = day_abs - 360
        
    return {"jour": day, "mois": COPTIC_MONTHS_AR[month - 1], "mois_num": month, "annee_copte": coptic_year}

def julian_easter(year: int) -> datetime.date:
    """Calcule la date de Pâques dans le calendrier Julien."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = 3 + (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    return datetime.date(year, month, day)

def julian_to_gregorian(julian_date: datetime.date) -> datetime.date:
    """Convertit une date julienne en date grégorienne."""
    y = julian_date.year
    delta = y // 100 - y // 400 - 2
    return julian_date + datetime.timedelta(days=delta)

def coptic_pascha_date(year: int) -> datetime.date:
    """Calcule la date de Pâques copte pour une année civile grégorienne donnée."""
    jd = julian_easter(year)
    return julian_to_gregorian(jd)

def locate_fixed_coptic(day: int, month: int, year_guess: int) -> datetime.date:
    """Trouve la date grégorienne pour un jour/mois copte donné, autour d'une année pivot."""
    pivot = datetime.date(year_guess, 6, 1) # Pivot au milieu de l'année pour plus de stabilité
    for d in range(-400, 401):
        g = pivot + datetime.timedelta(days=d)
        c = gregorian_to_coptic(g)
        if c["mois_num"] == month and c["jour"] == day:
            return g
    raise ValueError(f"Date coptique introuvable : {day}/{month} autour de {year_guess}")

# --- Fonctions de logique métier ---

def load_master(path: str) -> Dict[str, Any]:
    """Charge le fichier de données maître."""
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))

def compute_paramon_days(data: Dict[str, Any], year: int) -> List[Dict[str, Any]]:
    """Calcule les dates du Paramon pour une année donnée à partir des règles."""
    paramon_defs = data.get("paramon_rules", {})
    results = []
    for code, cfg in paramon_defs.items():
        feast_g = locate_fixed_coptic(cfg["feast_day"], cfg["feast_month"], year)
        wd_key = feast_g.strftime("%a").upper()
        offsets = cfg["mapping"].get(wd_key, [-1])
        for off in offsets:
            d = feast_g + datetime.timedelta(days=off)
            results.append({
                "code": code,
                "feast_code": cfg["feast_code"],
                "gregorian_date": d,
                "offset": off
            })
    return results

def get_movable_feasts(data: Dict[str, Any], year: int) -> List[Dict[str, Any]]:
    """Retourne toutes les fêtes mobiles (Pâques, Paramon) pour une année."""
    pascha = coptic_pascha_date(year)
    out = []
    for f in data["feasts_movable"]:
        d = pascha + datetime.timedelta(days=f["offset_jours"])
        nf = f.copy()
        nf["gregorian_date"] = d
        out.append(nf)
    
    for p in compute_paramon_days(data, year):
        out.append({
            "code": p["code"],
            "gregorian_date": p["gregorian_date"],
            "rang": "paramon",
            "titre_ar": "برامون " + ("الميلاد" if p["feast_code"] == "NATIVITY" else "الغطاس"),
            "titre_fr": "Paramon de la " + ("Nativité" if p["feast_code"] == "NATIVITY" else "Théophanie"),
            "resume_ar": "يوم إعداد وصوم ترقّبي قبل العيد."
        })
    return out

def fasting_state(date: datetime.date, data: Dict[str, Any], todays_feasts_codes: set) -> Dict[str, Any]:
    """Détermine le statut de jeûne pour une date donnée."""
    # Règle 1: Le jeûne du Paramon a une haute priorité.
    if PARAMON_CODES & todays_feasts_codes:
        return {"est_jeune": True, "type": "PARAMON", "intensite": "strict", "source_rule": "PARAMON"}

    # Règle 2: Les fêtes seigneuriales majeures annulent tout jeûne.
    if MAJOR_FEAST_CODES & todays_feasts_codes:
        return {"est_jeune": False, "type": None, "intensite": "none", "source_rule": "MAJOR_FEAST_OVERRIDE"}

    # Règle 3: Pas de jeûne durant les 50 jours saints (Khamasin).
    pascha = coptic_pascha_date(date.year)
    if pascha <= date <= pascha + datetime.timedelta(days=49):
        return {"est_jeune": False, "type": None, "intensite": "none", "source_rule": "FIFTY_DAYS"}

    # Règle 4: Scanner les périodes de jeûne définies.
    for fp in data.get("fasting_periods", []):
        if fp["code"] == "FIFTY_DAYS": continue
        try:
            start_date = pascha + datetime.timedelta(days=fp["debut_ref"]["offset"]) if fp["debut_type"] == "relative_to_pascha" else locate_fixed_coptic(fp["debut_ref"]["jour"], fp["debut_ref"]["mois"], date.year)
            end_date = pascha + datetime.timedelta(days=fp["fin_ref"]["offset"]) if fp["fin_type"] == "relative_to_pascha" else locate_fixed_coptic(fp["fin_ref"]["jour"], fp["fin_ref"]["mois"], date.year)
            if start_date <= date <= end_date:
                return {"est_jeune": True, "type": fp["code"], "intensite": fp.get("intensite", "normal"), "source_rule": fp["code"]}
        except (ValueError, KeyError):
            continue

    # Règle 5: Jeûne du Mercredi et Vendredi.
    if date.weekday() in (2, 4):
        return {"est_jeune": True, "type": "WED_FRI", "intensite": "normal", "source_rule": "WED_FRI"}

    return {"est_jeune": False, "type": None, "intensite": "none", "source_rule": "NONE"}

# --- Fonctions de construction de la réponse ---

def build_day(data: Dict[str, Any], date: datetime.date, lang: str = "ar") -> Dict[str, Any]:
    """Construit l'objet de réponse complet pour un jour."""
    cinfo = gregorian_to_coptic(date)
    
    # Pré-calcul des fêtes du jour
    fixed = [f for f in data["feasts_fixed"] if (f.get("jour_copte") == cinfo["jour"] and f.get("mois_copte") == cinfo["mois_num"]) or (f["code"] == "ARCHANGEL_MICHAEL_MONTHLY" and cinfo["jour"] == 12)]
    
    all_movable = get_movable_feasts(data, date.year)
    movable = [f for f in all_movable if f["gregorian_date"] == date]
    
    todays_feasts_codes = {f["code"] for f in fixed} | {f["code"] for f in movable}
    
    # Logique principale
    saints = [s for s in data["saints"] if any(comm["jour_copte"] == s["jour_copte"] and comm["mois_copte"] == s["mois_copte"] for comm in data["daily_commemorations"] if s["id"] in comm["liste_saints"])]
    fast = fasting_state(date, data, todays_feasts_codes)
    
    pascha = coptic_pascha_date(date.year)
    period = "الخماسين المقدسة" if pascha <= date <= pascha + datetime.timedelta(days=49) else "عادي"

    def get_lang_field(obj, field_prefix):
        return obj.get(f"{field_prefix}_{lang}", obj.get(f"{field_prefix}_ar", ""))

    feasts_res = [{
        "code": f["code"], "titre": get_lang_field(f, "titre"), "resume": get_lang_field(f, "resume"), "rang": f.get("rang")
    } for f in fixed + movable]
    
    commems_res = [{
        "id": s["id"], "type": s.get("type"), "nom": get_lang_field(s, "nom"), "resume": get_lang_field(s, "resume"), "fiabilite": s.get("fiabilite", "moyenne")
    } for s in saints if s["jour_copte"] == cinfo["jour"] and s["mois_copte"] == cinfo["mois_num"]]

    return {
        "date_gregorienne": date.isoformat(), "date_copte": cinfo, "periode_liturgique": period,
        "jeune": fast, "fetes": feasts_res, "commemorations": commems_res,
    }
