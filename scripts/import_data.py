import json
import psycopg2
import argparse
import pathlib
import sys

def get_upsert_sql(table, cols, conflict_cols):
    """Génère une commande SQL 'INSERT ... ON CONFLICT DO UPDATE'."""
    placeholders = ", ".join(["%s"] * len(cols))
    cols_list = ", ".join(cols)
    conflict_str = ", ".join(conflict_cols)
    updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols if c not in conflict_cols])
    return f"""
        INSERT INTO {table} ({cols_list}) 
        VALUES ({placeholders}) 
        ON CONFLICT ({conflict_str}) 
        DO UPDATE SET {updates};
    """

def main():
    """Script pour importer les données du fichier JSON vers une base de données PostgreSQL."""
    parser = argparse.ArgumentParser(description="Importe les données du calendrier copte dans PostgreSQL.")
    parser.add_argument("--dsn", required=True, help="Chaîne de connexion PostgreSQL (ex: 'postgresql://user:pass@host/db')")
    parser.add_argument("--data", default="data/master_data.json", help="Chemin vers le fichier master_data.json.")
    args = parser.parse_args()

    print("--- Lancement de l'importation vers PostgreSQL ---")
    
    try:
        data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
        conn = psycopg2.connect(args.dsn)
        cur = conn.cursor()
        print("Connexion à la base de données réussie.")

        # Importer feasts_fixed
        sql = get_upsert_sql("feasts_fixed", ["code", "jour_copte", "mois_copte", "rang", "titre_ar", "titre_fr"], ["code"])
        for f in data.get("feasts_fixed", []):
            cur.execute(sql, (f["code"], f["jour_copte"], f["mois_copte"], f.get("rang"), f.get("titre_ar"), f.get("titre_fr")))

        # Importer feasts_movable
        sql = get_upsert_sql("feasts_movable", ["code", "offset_jours", "rang", "titre_ar", "titre_fr"], ["code"])
        for f in data.get("feasts_movable", []):
            cur.execute(sql, (f["code"], f["offset_jours"], f.get("rang"), f.get("titre_ar"), f.get("titre_fr")))

        # Importer saints
        sql = get_upsert_sql("saints", ["id", "nom_ar", "nom_fr", "type", "jour_copte", "mois_copte", "fiabilite"], ["id"])
        for s in data.get("saints", []):
            cur.execute(sql, (s["id"], s["nom_ar"], s.get("nom_fr"), s.get("type"), s["jour_copte"], s["mois_copte"], s.get("fiabilite")))

        # Importer daily_commemorations (supprimer les anciennes pour éviter les doublons)
        cur.execute("TRUNCATE TABLE daily_commemorations RESTART IDENTITY;")
        for d in data.get("daily_commemorations", []):
            cur.execute(
                "INSERT INTO daily_commemorations (jour_copte, mois_copte, liste_saints) VALUES (%s, %s, %s)",
                (d["jour_copte"], d["mois_copte"], json.dumps(d["liste_saints"]))
            )

        # Importer fasting_periods
        sql = get_upsert_sql("fasting_periods", ["code", "debut_type", "debut_ref", "fin_type", "fin_ref", "intensite"], ["code"])
        for fp in data.get("fasting_periods", []):
            cur.execute(sql, (fp["code"], fp["debut_type"], json.dumps(fp.get("debut_ref")), fp["fin_type"], json.dumps(fp.get("fin_ref")), fp.get("intensite")))

        # Importer paramon_rules
        sql = get_upsert_sql("paramon_rules", ["code", "feast_code", "feast_day", "feast_month", "mapping"], ["code"])
        for code, pr in data.get("paramon_rules", {}).items():
            cur.execute(sql, (code, pr["feast_code"], pr["feast_day"], pr["feast_month"], json.dumps(pr["mapping"])))

        conn.commit()
        print(f"\nSuccès ! {len(data.get('saints',[]))} saints et {len(data.get('feasts_fixed',[]))} fêtes fixes importés.")
    
    except Exception as e:
        print(f"\nUne erreur est survenue : {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        print("Connexion à la base de données fermée.")

if __name__ == "__main__":
    main()