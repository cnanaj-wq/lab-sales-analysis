"""Construction du modèle en étoile de gold à partir de silver (Lab Sales Analysis).

Exécute les requêtes du dossier sql/gold_star_schema/ dans l'ordre : vidage
des 6 tables, puis les 4 dimensions, puis les 2 faits. Le tout en une seule
transaction : l'étoile est recalculée entièrement, ou rien ne change.
Lancement depuis la racine du projet :
    python scripts/06_construire_gold_star_schema.py
"""

# --- Imports ------------------------------------------------------------------

from pathlib import Path

from connexion import connect
from messages import log, stop

# --- Constantes ---------------------------------------------------------------

SQL_DIR = Path("sql") / "gold_star_schema"
SQL_FILES = [
    "00_vider_star_schema.sql",
    "01_dim_date.sql",
    "02_dim_magasin.sql",
    "03_dim_produit.sql",
    "04_dim_moyen_paiement.sql",
    "05_fait_ticket.sql",
    "06_fait_ligne_vente.sql",
]

# --- Lecture des requêtes SQL -------------------------------------------------

queries = []
for name in SQL_FILES:
    sql_file = SQL_DIR / name
    if not sql_file.is_file():
        stop(f"requête SQL introuvable ({sql_file}).")
    queries.append((name, sql_file.read_text(encoding="utf-8")))

# --- Construction de l'étoile : tout ou rien ----------------------------------

connection = connect()

try:
    with connection, connection.cursor() as cursor:
        for name, query in queries:
            cursor.execute(query)
            log(f"{name} : {cursor.rowcount} lignes traitées.")
except Exception as error:  # noqa: BLE001 - toute erreur annule la construction
    connection.close()
    stop(f"construction annulée, l'étoile est inchangée ({error}).")

connection.close()
log("modèle en étoile publié.")
