"""Construction de silver.exploded_products à partir de bronze (Lab Sales Analysis).

Lit les tickets de bronze.pos_sales_raw qui ne sont pas encore dans silver,
les éclate en une ligne par article et les insère dans silver.exploded_products,
en une seule transaction. Les colonnes et l'origine de chaque valeur sont lues
dans le modèle config/modele/03_silver/exploded_products.csv (champ_source).
Lancement depuis la racine du projet :
    python scripts/05_construire_silver.py
"""

# --- Imports ------------------------------------------------------------------

import csv
import sys
from pathlib import Path

from psycopg2.extras import execute_values

from connexion import connect
from messages import log, stop

# --- Constantes ---------------------------------------------------------------

MODEL_FILE = Path("config") / "modele" / "03_silver" / "exploded_products.csv"
TARGET_TABLE = "silver.exploded_products"
BATCH_SIZE = 1000

# --- Lecture des tickets de bronze --------------------------------------------

connection = connect()

with connection, connection.cursor() as cursor:
    cursor.execute(
        """
        select document
        from bronze.pos_sales_raw as raw
        where not exists (
            select 1
            from silver.exploded_products as exploded
            where exploded.transaction_id = raw.transaction_id
        )
        """
    )
    tickets = []
    for row in cursor.fetchall():
        tickets.append(row[0])

if not tickets:
    connection.close()
    log("aucun nouveau ticket dans bronze : rien à construire.")
    sys.exit(0)

log(f"{len(tickets)} tickets lus dans bronze, à éclater en articles.")

# --- Éclatement en une ligne par article --------------------------------------

rows = []
for ticket in tickets:
    for article in ticket.get("products") or []:
        row = (
            ticket["transaction_id"],
            ticket["store_id"],
            article["product_id"],
        )
        rows.append(row)

log(f"{len(rows)} articles prêts à insérer dans silver.")

# --- Insertion dans silver : tout ou rien -------------------------------------

try:
    with connection, connection.cursor() as cursor:
        inserted = execute_values(
            cursor,
            f"""
            insert into {TARGET_TABLE} (transaction_id, store_id, product_id)
            values %s
            on conflict (transaction_id, product_id) do nothing
            returning transaction_id
            """,
            rows,
            page_size=BATCH_SIZE,
            fetch=True,
        )
except Exception as error:  # noqa: BLE001 - toute erreur annule la construction
    connection.close()
    stop(f"construction annulée, rien n'a été écrit dans silver ({error}).")

connection.close()
ignored = len(rows) - len(inserted)
log(f"{len(inserted)} articles insérés dans {TARGET_TABLE}.")
log(f"{ignored} articles déjà présents, ignorés.")
