"""Profilage des champs du fichier JSON pour le modèle de tables (Lab Sales Analysis).

Lit le fichier source et écrit config/modele/source.csv :
un champ par ligne, avec son type détecté, sa longueur max et son taux de vides.
Lancement depuis la racine du projet :
    python scripts/02_generer_modele_source.py
"""

# --- Imports ------------------------------------------------------------------

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# --- Constantes ---------------------------------------------------------------

SOURCE_FILE = Path("data") / "raw" / "pos_sales_data_30k.json"
OUTPUT_FILE = Path("config") / "modele" / "source.csv"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
MISSING_VALUES = (None, "", [])

SQL_TYPES = {
    "texte": "text",
    "entier": "integer",
    "decimal": "float",
    "horodatage": "timestamp",
    "booleen": "boolean",
    "liste": "jsonb",
    "objet": "jsonb",
}


# --- Type d'une valeur --------------------------------------------------------


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


# --- Fiche de statistiques d'un champ -----------------------------------------


def new_stats():
    """Crée la fiche vierge d'un champ : types, vides, longueur max, exemple."""
    return {
        "types": set(),
        "nb_valeurs": 0,
        "nb_vides": 0,
        "longueur_max": 0,
        "exemple": "",
    }


def update_stats(stats, value):
    """Met à jour la fiche d'un champ avec une nouvelle valeur."""
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


# --- Type SQL proposé ---------------------------------------------------------


def propose_sql_type(types):
    """Propose un type PostgreSQL à partir des types détectés d'un champ."""
    if types == {"entier", "decimal"}:
        return "float"
    for detected_type, sql_type in SQL_TYPES.items():
        if types == {detected_type}:
            return sql_type
    return "text"


# --- Lecture du fichier source -----------------------------------------------

if not SOURCE_FILE.exists():
    sys.exit(f"Arrêt : fichier source introuvable ({SOURCE_FILE}).")

with SOURCE_FILE.open(encoding="utf-8") as source:
    transactions = json.load(source)

# --- Statistiques par champ ---------------------------------------------------

fields = {}
for transaction in transactions:
    for name, value in transaction.items():
        if name == "products":
            continue
        stats = fields.setdefault(("ticket", name), new_stats())
        update_stats(stats, value)
    for product in transaction.get("products") or []:
        for name, value in product.items():
            stats = fields.setdefault(("article", name), new_stats())
            update_stats(stats, value)

# --- Écriture du modèle -------------------------------------------------------

HEADER = [
    "niveau",
    "champ",
    "types_detectes",
    "type_sql_propose",
    "nb_valeurs",
    "nb_vides",
    "pct_vides",
    "longueur_max",
    "exemple",
]

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as output:
    writer = csv.writer(output, delimiter=";")
    writer.writerow(HEADER)
    for key, stats in fields.items():
        level = key[0]
        name = key[1]
        types_text = ",".join(sorted(stats["types"]))
        sql_type = propose_sql_type(stats["types"])
        pct_vides = round(100 * stats["nb_vides"] / stats["nb_valeurs"], 2)
        row = [
            level,
            name,
            types_text,
            sql_type,
            stats["nb_valeurs"],
            stats["nb_vides"],
            pct_vides,
            stats["longueur_max"],
            stats["exemple"],
        ]
        writer.writerow(row)

print(f"{len(fields)} champs écrits dans {OUTPUT_FILE}")
