import argparse
import json
import pathlib
import sys
import datetime

# Ajouter le dossier racine du projet au chemin pour pouvoir importer 'app'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from app import calendar_core as cc

def main():
    """
    Script pour pré-calculer et sauvegarder les données liturgiques
    pour une année complète dans un fichier JSON.
    """
    parser = argparse.ArgumentParser(description="Génère un cache annuel des données liturgiques coptes.")
    parser.add_argument("--year", type=int, required=True, help="L'année pour laquelle générer le cache (ex: 2025).")
    parser.add_argument("--lang", default="ar", choices=["ar", "fr"], help="La langue du cache ('ar' ou 'fr').")
    parser.add_argument("--data", default="data/master_data.json", help="Chemin vers le fichier master_data.json.")
    parser.add_argument("--out", default="cache", help="Dossier de sortie pour le fichier de cache.")
    args = parser.parse_args()

    print(f"--- Génération du cache pour l'année {args.year} en langue '{args.lang}' ---")

    try:
        # Charger les données de base
        data = cc.load_master(args.data)
        
        # Construire le cache pour l'année spécifiée
        cache_content = cc.build_year_cache(data, args.year, args.lang)
        
        # Créer le dossier de sortie s'il n'existe pas
        output_dir = pathlib.Path(args.out)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Définir le nom du fichier de sortie
        output_file = output_dir / f"year_{args.year}_{args.lang}.json"
        
        # Écrire le cache dans le fichier JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cache_content, f, ensure_ascii=False, indent=2)
            
        print(f"\nSuccès ! Cache écrit dans : {output_file}")

    except FileNotFoundError:
        print(f"Erreur : Le fichier de données '{args.data}' est introuvable.")
        sys.exit(1)
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()