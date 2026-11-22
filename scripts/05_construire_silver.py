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
from pathlib import Path

from psycopg2.extras import execute_values

from connexion import connect
from messages import log, stop

# --- Constantes ---------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = PROJECT_DIR / "config" / "modele" / "03_silver" / "exploded_products.csv"
TARGET_TABLE = "silver.exploded_products"
BATCH_SIZE = 1000

# --- Construction de silver ---------------------------------------------------


def main():
    """Éclate les nouveaux tickets de bronze dans silver et renvoie les compteurs."""
    # Lecture du modèle de la table
    if not MODEL_FILE.is_file():
        stop(f"modèle de la table introuvable ({MODEL_FILE}).")

    with MODEL_FILE.open(encoding="utf-8", newline="") as file:
        model = list(csv.DictReader(file, delimiter=";"))

    columns = []
    sources = []
    primary_key = []
    for line in model:
        level, field = line["champ_source"].split(".", 1)
        if level not in ("ticket", "article"):
            stop(
                f"champ_source inconnu pour {line['colonne']} : {line['champ_source']}."
            )
        columns.append(line["colonne"])
        sources.append((level, field))
        if line["cle_primaire"] == "oui":
            primary_key.append(line["colonne"])

    # Lecture des tickets de bronze
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
        return {"tickets_lus": 0, "articles_inseres": 0, "articles_ignores": 0}

    log(f"{len(tickets)} tickets lus dans bronze, à éclater en articles.")

    # Éclatement en une ligne par article
    rows = []
    for ticket in tickets:
        for article in ticket.get("products") or []:
            row = []
            for level, field in sources:
                if level == "ticket":
                    row.append(ticket.get(field))
                else:
                    row.append(article.get(field))
            rows.append(row)

    log(f"{len(rows)} articles prêts à insérer dans silver.")

    # Insertion dans silver : tout ou rien
    column_list = ", ".join(columns)
    key_list = ", ".join(primary_key)

    try:
        with connection, connection.cursor() as cursor:
            inserted = execute_values(
                cursor,
                f"""
                insert into {TARGET_TABLE} ({column_list})
                values %s
                on conflict ({key_list}) do nothing
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

    return {
        "tickets_lus": len(tickets),
        "articles_inseres": len(inserted),
        "articles_ignores": ignored,
    }


# --- Lancement depuis le terminal ---------------------------------------------

if __name__ == "__main__":
    main()
