"""Connexion à la base des ventes (Lab Sales Analysis).

Lit les paramètres de connexion hors du dépôt et ouvre la connexion
à la base des ventes. À importer depuis un autre script :
    from connexion import connect
"""

# --- Imports ------------------------------------------------------------------

import sys
from pathlib import Path

import psycopg2

# --- Constantes ---------------------------------------------------------------

ENV_FILE = Path("..") / "data_connection" / "lab_sales_postgres_ventes.env"


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
    if not ENV_FILE.exists():
        sys.exit(f"Arrêt : fichier de connexion introuvable ({ENV_FILE}).")
    settings = read_env(ENV_FILE)
    return psycopg2.connect(
        host=settings["POSTGRES_HOST"],
        port=settings["POSTGRES_PORT"],
        dbname=settings["POSTGRES_DB"],
        user=settings["POSTGRES_USER"],
        password=settings["POSTGRES_PASSWORD"],
    )
