"""Profilage du fichier source des ventes POS (Lab Sales Analysis).

Lecture seule : le fichier source n'est jamais modifié.
Lancement depuis la racine du projet :
    python scripts/01_profilage_source.py

Chaque contrôle porte un identifiant repris dans docs/02_profilage_source.md :
    S = structure, V = volume, F = format (validité), C = complétude,
    U = unicité, K = cohérence, D = distribution.
"""

import json
import sys
from collections import Counter, defaultdict
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

# --- Unicité ------------------------------------------------------------------

# U1 : l'identifiant du ticket est-il unique ? (clé primaire, RG05)
id_counts = Counter(transaction["transaction_id"] for transaction in transactions)
duplicate_ids = [tid for tid, count in id_counts.items() if count > 1]
print("U1 Identifiants en double :", len(duplicate_ids), duplicate_ids[:10])

# U2 : doublon caché, même contenu sous un autre identifiant.
content_counts = Counter(
    json.dumps(
        {key: value for key, value in transaction.items() if key != "transaction_id"},
        sort_keys=True,
    )
    for transaction in transactions
)

hidden_duplicates = sum(count - 1 for count in content_counts.values() if count > 1)
print("U2 Tickets identiques sous un autre identifiant :", hidden_duplicates)

# U3 : un produit répété dans un ticket ?
repeated_products = [
    transaction["transaction_id"]
    for transaction in transactions
    if len(transaction["products"])
    != len({product["product_id"] for product in transaction["products"]})
]

print(
    "U3 Tickets avec un produit répété :",
    len(repeated_products),
    repeated_products[:10],
)

# --- Cohérence ----------------------------------------------------------------

# K1 : le montant du ticket est-il la somme de ses lignes ? (RG02)
# Arrondi au centime des deux côtés : les float sont approchés (0.1 + 0.2).
amount_mismatches = [
    transaction["transaction_id"]
    for transaction in transactions
    if round(transaction["total_amount"], 2)
    != round(
        sum(
            product["quantity"] * product["price"]
            for product in transaction["products"]
        ),
        2,
    )
]

print(
    "K1 Tickets dont le montant ne correspond pas aux lignes :",
    len(amount_mismatches),
    amount_mismatches[:10],
)

# K2 : la quantité du ticket est-elle la somme de ses lignes ? (RG03)
quantity_mismatches = [
    transaction["transaction_id"]
    for transaction in transactions
    if transaction["total_quantity_sold"]
    != sum(product["quantity"] for product in transaction["products"])
]

print(
    "K2 Tickets dont la quantité ne correspond pas aux lignes :",
    len(quantity_mismatches),
    quantity_mismatches[:10],
)

# K3 : chaque pays utilise-t-il une seule devise ? (daily_sales_country_currency)
currencies_by_country = defaultdict(set)
for transaction in transactions:
    country = transaction["store_country"]
    currencies_by_country[country].add(transaction["currency"])

multi_currency_countries = {
    country: sorted(country_currencies)
    for country, country_currencies in currencies_by_country.items()
    if len(country_currencies) > 1
}

print(
    "K3 Pays avec plusieurs devises :",
    len(multi_currency_countries),
    multi_currency_countries,
)

# K4 : un store_id désigne-t-il toujours le même magasin ? (P01)
stores_by_id = defaultdict(set)
for transaction in transactions:
    store = (
        transaction["store_name"],
        transaction["store_city"],
        transaction["store_country"],
        transaction["store_type"],
    )
    stores_by_id[transaction["store_id"]].add(store)

unstable_store_ids = [
    store_id for store_id, stores in stores_by_id.items() if len(stores) > 1
]

print("K4 store_id distincts :", len(stores_by_id))
print(
    "K4 store_id qui désignent plusieurs magasins :",
    len(unstable_store_ids),
    unstable_store_ids[:5],
)

if unstable_store_ids:
    print("    exemple :", sorted(stores_by_id[unstable_store_ids[0]]))

# K5 : promo_code = [indicateur, code]. Les deux parties sont-elles cohérentes ?
promo_combinations = Counter(
    (transaction["promo_code"][0], transaction["promo_code"][1] is not None)
    for transaction in transactions
)

for (flag, has_code), count in sorted(promo_combinations.items()):
    print("K5 promo_code", flag, "| code renseigné :", has_code, "|", count)

# K6 : un magasin (enseigne, ville) a-t-il toujours le même type ? (RP01)
types_by_store = defaultdict(set)
for transaction in transactions:
    store = (transaction["store_name"], transaction["store_city"])
    types_by_store[store].add(transaction["store_type"])

multi_type_stores = [
    store for store, store_types in types_by_store.items() if len(store_types) > 1
]

print("K6 Magasins (enseigne, ville) :", len(types_by_store))
print("K6 Magasins avec plusieurs types :", len(multi_type_stores))

# K7 : la remise est-elle liée à la promotion ? (RG08)
discount_by_promo = Counter(
    (transaction["promo_code"][0], transaction["discount_applied"] > 0)
    for transaction in transactions
)

for (flag, has_discount), count in sorted(discount_by_promo.items()):
    print("K7 promo", flag, "| remise > 0 :", has_discount, "|", count)

# --- Distribution -------------------------------------------------------------

# D1 : répartition des tickets vendus / retournés (traitement des retours dans le CA)
return_counts = Counter(transaction["return_status"] for transaction in transactions)
print("D1 Statut de retour :", dict(return_counts))

# D2 : moyens de paiement (payment_method_analysis)
payment_counts = Counter(transaction["payment_method"] for transaction in transactions)
print("D2 Moyens de paiement :", len(payment_counts), sorted(payment_counts))
for method, count in payment_counts.most_common():
    print("    -", method, ":", count)

# D3 : types de magasin (axe magasin, faute de store_id fiable)
store_type_counts = Counter(transaction["store_type"] for transaction in transactions)
print("D3 Types de magasin :", dict(store_type_counts.most_common()))

# D4 : lignes article par produit (exploded_products)
product_counts = Counter(
    (product["product_id"], product["product_name"])
    for transaction in transactions
    for product in transaction["products"]
)

print("D4 Produits distincts :", len(product_counts))
for (product_id, product_name), count in sorted(product_counts.items()):
    print("    -", product_id, product_name, ":", count)

# D5 : un produit a-t-il un prix unique ? (price dans exploded_products)
prices_by_product = defaultdict(set)
for transaction in transactions:
    for product in transaction["products"]:
        prices_by_product[product["product_id"]].add(product["price"])

print("D5 Prix distincts par produit :")
for product_id, prices in sorted(prices_by_product.items()):
    print(
        "    -",
        product_id,
        ":",
        len(prices),
        "prix, de",
        min(prices),
        "à",
        max(prices),
    )

# D6 : tickets par jour (RG06 : un jour sans vente signale une livraison manquante)
tickets_by_day = Counter(timestamp[:10] for timestamp in timestamps)

print("D6 Jours avec ventes :", len(tickets_by_day))
print("D6 Tickets par jour, minimum :", min(tickets_by_day.values()))
print("D6 Tickets par jour, maximum :", max(tickets_by_day.values()))
