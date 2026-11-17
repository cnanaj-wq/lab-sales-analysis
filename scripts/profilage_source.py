"""Profilage du fichier source des ventes POS (Lab Sales Analysis).

Lecture seule : le fichier source n'est jamais modifié.
Lancement depuis la racine du projet :
    python scripts/profilage_source.py

Chaque contrôle porte un identifiant repris dans docs/02_profilage_source.md :
    S = structure, V = volume, F = format (validité).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SOURCE_FILE = Path("data") / "raw" / "pos_sales_data_30k.json"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Chargement ---------------------------------------------------------------

print("Fichier source :", SOURCE_FILE)
print("Fichier trouvé :", SOURCE_FILE.exists())

# RG06 : sans fichier source, on s'arrête avec un message clair.
if not SOURCE_FILE.exists():
    sys.exit(f"Arrêt : fichier source introuvable ({SOURCE_FILE}).")

with SOURCE_FILE.open(encoding="utf-8") as source:
    transactions = json.load(source)

# --- Structure ----------------------------------------------------------------

print("S1 Type de l'objet chargé :", type(transactions))
print("S2 Nombre d'éléments :", len(transactions))

first_transaction = transactions[0]
print("S3 Type du premier élément :", type(first_transaction))
print("S4 Champs :", list(first_transaction.keys()))

for field, value in first_transaction.items():
    if isinstance(value, (list, dict)):
        print("S5 Champ imbriqué :", field, type(value))

# --- Volume et période --------------------------------------------------------

product_lines = sum(len(transaction["products"]) for transaction in transactions)
print("V1 Lignes article :", product_lines)

timestamps = [transaction["purchase_timestamp"] for transaction in transactions]
print("V2 Première vente :", min(timestamps))
print("V3 Dernière vente :", max(timestamps))

countries = {transaction["store_country"] for transaction in transactions}
print("V4 Pays :", len(countries), sorted(countries))

currencies = {transaction["currency"] for transaction in transactions}
print("V5 Devises :", len(currencies), sorted(currencies))

# --- Validité : format des dates ----------------------------------------------

# strptime vérifie la forme ET le calendrier (il refuse 2024-02-30).
invalid_timestamps = []
for timestamp in timestamps:
    try:
        datetime.strptime(timestamp, TIMESTAMP_FORMAT)
    except (ValueError, TypeError):
        invalid_timestamps.append(timestamp)

print("F1 Dates conformes :", len(timestamps) - len(invalid_timestamps))
print("F2 Dates non conformes :", len(invalid_timestamps), invalid_timestamps[:10])
