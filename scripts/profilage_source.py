"""Profilage du fichier source des ventes POS (Lab Sales Analysis)."""

import json
import sys
from pathlib import Path

SOURCE_FILE = Path("data") / "raw" / "pos_sales_data_30k.json"

print("Fichier source :", SOURCE_FILE)
print("Fichier trouvé :", SOURCE_FILE.exists())

# RG06 : sans fichier source, on s'arrête avec un message clair.
if not SOURCE_FILE.exists():
    sys.exit(f"Arrêt : fichier source introuvable ({SOURCE_FILE}).")

with SOURCE_FILE.open(encoding="utf-8") as source:
    transactions = json.load(source)

print("S1 Type de l'objet chargé :", type(transactions))
print("S2 Nombre d'éléments :", len(transactions))

first_transaction = transactions[0]
print("S3 Type du premier élément :", type(first_transaction))
print("S4 Champs :", list(first_transaction.keys()))

for field, value in first_transaction.items():
    if isinstance(value, (list, dict)):
        print("S5 Champ imbriqué :", field, type(value))
