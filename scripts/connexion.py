"""Connexion à la base des ventes (Lab Sales Analysis).

Dans Airflow : utilise la connexion Airflow « postgres_ventes ».
Sur le PC : lit les paramètres dans data_connection, hors du dépôt.
À importer depuis un autre script :
    from connexion import connect
"""

# --- Imports ------------------------------------------------------------------

import os
import sys
from pathlib import Path

import psycopg2

# --- Constantes ---------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR.parent / "data_connection" / "lab_sales_postgres_ventes.env"
AIRFLOW_CONN_ID = "postgres_ventes"
DB_OVERRIDE_VAR = "LAB_SALES_DB"


# --- Lecture des secrets ------------------------------------------------------


def read_env(path):
    """Lit un fichier .env (CLE=valeur) et renvoie un dictionnaire."""
    settings = {}
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
    return settings


# --- Connexion à la base ------------------------------------------------------


def connect():
    """Ouvre une connexion à la base des ventes et la renvoie."""
    # Dans le conteneur Airflow : paramètres lus dans la connexion Airflow
    # (on ouvre la connexion avec psycopg2, car les scripts utilisent execute_values)
    if "AIRFLOW_CONN_POSTGRES_VENTES" in os.environ:
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        airflow_conn = PostgresHook.get_connection(AIRFLOW_CONN_ID)
        return psycopg2.connect(
            host=airflow_conn.host,
            port=airflow_conn.port,
            dbname=airflow_conn.schema,
            user=airflow_conn.login,
            password=airflow_conn.password,
        )

    # Sur le PC : fichier .env rangé hors du dépôt
    if not ENV_FILE.exists():
        sys.exit(f"Arrêt : fichier de connexion introuvable ({ENV_FILE}).")
    settings = read_env(ENV_FILE)
    # Base visée : LAB_SALES_DB si elle existe (les tests visent ventes_recette),
    # sinon la base du fichier .env
    dbname = os.environ.get(DB_OVERRIDE_VAR, settings["POSTGRES_DB"])
    return psycopg2.connect(
        host=settings["POSTGRES_HOST"],
        port=settings["POSTGRES_PORT"],
        dbname=dbname,
        user=settings["POSTGRES_USER"],
        password=settings["POSTGRES_PASSWORD"],
    )
