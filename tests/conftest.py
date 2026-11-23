"""Configuration commune des tests (Lab Sales Analysis).

Les tests écrivent dans la base de recette ventes_recette, jamais dans ventes.
Avant chaque test, les schémas sont recréés vides à partir de sql/ddl_genere.sql.
"""

# --- Imports ------------------------------------------------------------------

import os
from pathlib import Path

import pytest

from connexion import connect

# --- Constantes ---------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
DDL_FILE = PROJECT_DIR / "sql" / "ddl_genere.sql"
TEST_DB = "ventes_recette"
SCHEMAS = ["ops", "bronze", "silver", "gold"]

# Toutes les connexions ouvertes pendant les tests visent la base de recette
os.environ["LAB_SALES_DB"] = TEST_DB

# --- Base de recette ----------------------------------------------------------


@pytest.fixture
def db():
    """Remet la base de recette à zéro et renvoie une connexion ouverte."""
    connection = connect()
    with connection, connection.cursor() as cursor:
        # Garde-fou : on ne vide jamais une autre base que la base de recette
        cursor.execute("select current_database()")
        current_db = cursor.fetchone()[0]
        if current_db != TEST_DB:
            pytest.exit(f"garde-fou : connecté à {current_db}, pas à {TEST_DB}.")

        # Schémas supprimés puis recréés vides
        cursor.execute("drop schema if exists " + ", ".join(SCHEMAS) + " cascade")
        cursor.execute(DDL_FILE.read_text(encoding="utf-8"))

    yield connection
    connection.close()
