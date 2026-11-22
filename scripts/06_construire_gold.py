"""Construction des 3 tables gold à partir de silver (Lab Sales Analysis).

Exécute les requêtes du dossier sql/gold/, une par table, dans une seule
transaction : les 3 tables sont recalculées ensemble, ou rien ne change.
Lancement depuis la racine du projet :
    python scripts/06_construire_gold.py
"""

# --- Imports ------------------------------------------------------------------

from pathlib import Path

from connexion import connect
from messages import log, stop

# --- Constantes ---------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_DIR / "sql" / "gold"
SQL_FILES = [
    "store_sales_summary.sql",
    "daily_sales_country_currency.sql",
    "payment_method_analysis.sql",
]

# --- Construction des tables gold ---------------------------------------------


def main():
    """Recalcule les 3 tables gold et renvoie le nombre de lignes de chacune."""
    # Lecture des requêtes SQL
    queries = []
    for name in SQL_FILES:
        sql_file = SQL_DIR / name
        if not sql_file.is_file():
            stop(f"requête SQL introuvable ({sql_file}).")
        queries.append((name, sql_file.read_text(encoding="utf-8")))

    # Construction des tables gold : tout ou rien
    counts = {}
    connection = connect()

    try:
        with connection, connection.cursor() as cursor:
            for name, query in queries:
                cursor.execute(query)
                log(f"{name} : {cursor.rowcount} lignes calculées.")
                if cursor.rowcount >= 0:
                    counts[Path(name).stem] = cursor.rowcount
    except Exception as error:  # noqa: BLE001 - toute erreur annule la construction
        connection.close()
        stop(f"construction annulée, les tables gold sont inchangées ({error}).")

    connection.close()
    log("3 tables gold publiées.")
    return counts


# --- Lancement depuis le terminal ---------------------------------------------

if __name__ == "__main__":
    main()
