# app/search_index.py
import re, unicodedata

def normalize_ar(s:str)->str:
    """Nettoie une chaîne de caractères en arabe pour la recherche."""
    if not s: return ""
    # Supprimer les diacritiques arabes
    diac = "".join(chr(c) for c in range(0x0610,0x061B)) + "".join(chr(c) for c in range(0x064B,0x065F))
    table = str.maketrans("", "", diac)
    s = s.translate(table)
    # Normaliser les caractères (أإآ -> ا, ة -> ه, ى -> ي)
    s = s.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ة","ه").replace("ى","ي")
    return s

def normalize_fr(s:str)->str:
    """Nettoie une chaîne de caractères en français pour la recherche."""
    if not s: return ""
    # Enlever les accents
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch)!="Mn")
    return s.lower()

def build_indices(data:dict):
    """Construit un index de recherche en mémoire à partir des données principales."""
    saints_index=[]
    for s in data.get("saints",[]):
        saints_index.append({
            "type":"saint",
            "id":s["id"],
            "nom_ar":s.get("nom_ar"),
            "nom_fr":s.get("nom_fr"),
            "search_ar":normalize_ar(" ".join(filter(None,[s.get("nom_ar"), s.get("resume_ar","")[:80]]))),
            "search_fr":normalize_fr(" ".join(filter(None,[s.get("nom_fr"), s.get("resume_fr","") or s.get("resume_ar","")[:80]]))),
            "fiabilite":s.get("fiabilite")
        })
    
    feasts_index=[]
    all_feasts = data.get("feasts_fixed", []) + data.get("feasts_movable", [])
    for f in all_feasts:
        feasts_index.append({
            "type":"feast",
            "code":f["code"],
            "titre_ar":f.get("titre_ar"),
            "titre_fr":f.get("titre_fr"),
            "search_ar":normalize_ar(" ".join(filter(None,[f.get("code"),f.get("titre_ar"),f.get("resume_ar","")[:80]]))),
            "search_fr":normalize_fr(" ".join(filter(None,[f.get("code"),f.get("titre_fr") or f.get("titre_ar"),f.get("resume_ar","")[:80]])))
        })
        
    return {"saints":saints_index,"feasts":feasts_index}

def search(q:str, lang:str, data_idx:dict, type_filter:str="all", limit:int=20, offset:int=0):
    """Effectue une recherche dans l'index."""
    nq = (normalize_ar(q) if lang=="ar" else normalize_fr(q))
    res=[]
    
    if type_filter in ("all","saint"):
        for s in data_idx["saints"]:
            if nq in s[f"search_{lang}"]:
                res.append({
                    "resource_type":"saint",
                    "id":s["id"],
                    "nom_ar":s["nom_ar"],
                    "nom_fr":s["nom_fr"],
                    "fiabilite":s["fiabilite"]
                })

    if type_filter in ("all","feast"):
        for f in data_idx["feasts"]:
            if nq in f[f"search_{lang}"]:
                res.append({
                    "resource_type":"feast",
                    "code":f["code"],
                    "titre_ar":f["titre_ar"],
                    "titre_fr":f["titre_fr"]
                })
                
    total=len(res)
    return {"total":total,"results":res[offset:offset+limit]}