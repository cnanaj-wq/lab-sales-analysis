"""Profilage du fichier source des ventes POS (Lab Sales Analysis).

Lecture seule : le fichier source n'est jamais modifié.
Lancement depuis la racine du projet :
    python scripts/profilage_source.py

Chaque contrôle porte un identifiant repris dans docs/02_profilage_source.md :
    S = structure, V = volume, F = format (validité), C = complétude.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SOURCE_FILE = Path("data") / "raw" / "pos_sales_data_30k.json"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
# Ce qui compte comme « vide ». Le 0 n'y est pas : une remise de 0 est une valeur.
MISSING_VALUES = (None, "", [])

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

# --- Complétude ---------------------------------------------------------------

# Niveau ticket. Référence provisoire : les champs du premier ticket
# (elle viendra du contrat de données).
reference_fields = set(first_transaction.keys())

irregular_transactions = [
    transaction.get("transaction_id")
    for transaction in transactions
    if set(transaction.keys()) != reference_fields
]
print(
    "C1 Tickets aux champs différents :",
    len(irregular_transactions),
    irregular_transactions[:10],
)

# Limite : une valeur vide À L'INTÉRIEUR d'une liste n'est pas vue
# (promo_code = ["no", null] n'est pas vide). Elle relève de la cohérence.
missing_counts = {field: 0 for field in reference_fields}
for transaction in transactions:
    for field in reference_fields:
        if transaction.get(field) in MISSING_VALUES:
            missing_counts[field] += 1

print("C2 Valeurs manquantes (tickets) :", sum(missing_counts.values()))
for field, count in sorted(missing_counts.items()):
    if count > 0:
        print("    -", field, ":", count)

# Niveau article : mêmes contrôles, un niveau plus bas.
reference_product_fields = set(first_transaction["products"][0].keys())

irregular_products = 0
missing_product_values = 0
for transaction in transactions:
    for product in transaction["products"]:
        if set(product.keys()) != reference_product_fields:
            irregular_products += 1
        for value in product.values():
            if value in MISSING_VALUES:
                missing_product_values += 1

print("C3 Articles aux champs différents :", irregular_products)
print("C4 Valeurs manquantes (articles) :", missing_product_values)
