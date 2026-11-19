"""Profilage des champs du fichier JSON pour le modèle de tables (Lab Sales Analysis).

Lit le fichier source et écrit config/modele/source.csv :
un champ par ligne, avec son type détecté, sa longueur max et son taux de vides.
Lancement depuis la racine du projet :
    python scripts/generer_modele_source.py
"""
# Imports et constantes
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

SOURCE_FILE = Path("data") / "raw" / "pos_sales_data_30k.json"
OUTPUT_FILE = Path("config") / "modele" / "source.csv"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
MISSING_VALUES = (None, "", [])


# Reconnaître le type d’une valeur
def detect_type(value):
    """Renvoie le type d'une valeur JSON, avec les mots du modèle."""
    if value in MISSING_VALUES:
        return "vide"
    if isinstance(value, bool):
        return "booleen"
    if isinstance(value, int):
        return "entier"
    if isinstance(value, float):
        return "decimal"
    if isinstance(value, list):
        return "liste"
    if isinstance(value, dict):
        return "objet"
    try:
        datetime.strptime(value, TIMESTAMP_FORMAT)
        return "horodatage"
    except ValueError:
        return "texte"


# récupérer les statistiques d’un champ (types, vides, longueur max, exemple)
def new_stats():
    """Crée les compteurs vides d'un champ."""
    return {"types": set(), "nb_valeurs": 0, "nb_vides": 0,
            "longueur_max": 0, "exemple": ""}


def update_stats(stats, value):
    """Ajoute une valeur aux compteurs de son champ."""
    stats["nb_valeurs"] += 1
    value_type = detect_type(value)
    if value_type == "vide":
        stats["nb_vides"] += 1
        return
    stats["types"].add(value_type)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    stats["longueur_max"] = max(stats["longueur_max"], len(text))
    if not stats["exemple"]:
        stats["exemple"] = text
