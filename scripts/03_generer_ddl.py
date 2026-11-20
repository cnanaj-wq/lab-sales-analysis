"""Génération du SQL de création des tables à partir du modèle (Lab Sales Analysis).

Lit config/modele/ : schemas.csv, puis un dossier par schéma (01_ops, 02_bronze...)
avec un fichier CSV par table. Écrit sql/ddl_genere.sql, puis l'exécute dans la base.
Option --vider : vide toutes les tables après la création (tests uniquement).
Lancement depuis la racine du projet :
    python scripts/03_generer_ddl.py [--vider]
"""

# --- Imports ------------------------------------------------------------------

import csv
import sys
from pathlib import Path

import psycopg2

# --- Constantes ---------------------------------------------------------------

MODEL_DIR = Path("config") / "modele"
SCHEMAS_FILE = MODEL_DIR / "schemas.csv"
RELATIONS_FILE = MODEL_DIR / "relations.csv"
OUTPUT_FILE = Path("sql") / "ddl_genere.sql"
ENV_FILE = Path("..") / "data_connection" / "lab_sales_postgres_ventes.env"
DB_HOST = "127.0.0.1"
DB_PORT = 5440
RESET_OPTION = "--vider"


# --- Outils -------------------------------------------------------------------


def read_csv(path):
    """Lit un fichier CSV du modèle et renvoie une liste de lignes."""
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def sql_text(text):
    """Met un texte entre apostrophes pour le SQL, en doublant ses apostrophes."""
    return "'" + text.replace("'", "''") + "'"


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


# --- SQL d'une table ----------------------------------------------------------


def table_sql(schema, table, columns):
    """Renvoie le SQL qui crée une table et commente ses colonnes."""
    full_name = f"{schema}.{table}"
    column_lines = []
    primary_key = []
    for column in columns:
        line = f"    {column['colonne']} {column['type_sql']}"
        if column["obligatoire"] == "oui":
            line += " not null"
        column_lines.append(line)
        if column["cle_primaire"] == "oui":
            primary_key.append(column["colonne"])
    if primary_key:
        column_lines.append(f"    primary key ({', '.join(primary_key)})")

    sql = f"create table if not exists {full_name} (\n"
    sql += ",\n".join(column_lines)
    sql += "\n);\n"
    for column in columns:
        name = f"{full_name}.{column['colonne']}"
        description = sql_text(column["description"])
        sql += f"comment on column {name} is {description};\n"
    return sql


# --- SQL d'une clé étrangère --------------------------------------------------


def relation_sql(relation):
    """Renvoie le SQL qui ajoute une clé étrangère, en la recréant si elle existe."""
    table = relation["table"]
    column = relation["colonne"]
    constraint = "fk_" + table.split(".")[1] + "_" + column
    reference = f"{relation['table_reference']} ({relation['colonne_reference']})"
    sql = f"alter table {table} drop constraint if exists {constraint};\n"
    sql += f"alter table {table} add constraint {constraint} "
    sql += f"foreign key ({column}) references {reference};\n"
    return sql


# --- Lecture des schémas ------------------------------------------------------

if not SCHEMAS_FILE.exists():
    sys.exit(f"Arrêt : fichier des schémas introuvable ({SCHEMAS_FILE}).")

descriptions = {}
for row in read_csv(SCHEMAS_FILE):
    descriptions[row["schema"]] = row["description"]

# --- Génération du SQL --------------------------------------------------------

sql = "-- Fichier généré par scripts/03_generer_ddl.py : ne pas modifier à la main.\n"
nb_tables = 0
tables = []
for folder in sorted(MODEL_DIR.iterdir()):
    if not folder.is_dir():
        continue
    schema = folder.name.split("_", 1)[1]
    if schema not in descriptions:
        sys.exit(f"Arrêt : le schéma {schema} manque dans {SCHEMAS_FILE}.")
    sql += f"\n-- Schéma {schema}\n"
    sql += f"create schema if not exists {schema};\n"
    sql += f"comment on schema {schema} is {sql_text(descriptions[schema])};\n"
    for table_file in sorted(folder.glob("*.csv")):
        columns = read_csv(table_file)
        sql += "\n" + table_sql(schema, table_file.stem, columns)
        nb_tables += 1
        tables.append(f"{schema}.{table_file.stem}")

# --- Clés étrangères ----------------------------------------------------------

if RELATIONS_FILE.exists():
    sql += "\n-- Clés étrangères\n"
    for relation in read_csv(RELATIONS_FILE):
        sql += relation_sql(relation)

# --- Écriture du fichier SQL --------------------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.write_text(sql, encoding="utf-8")
print(f"{nb_tables} tables écrites dans {OUTPUT_FILE}")

# --- Exécution dans PostgreSQL ------------------------------------------------

if not ENV_FILE.exists():
    sys.exit(f"Arrêt : fichier de connexion introuvable ({ENV_FILE}).")

settings = read_env(ENV_FILE)
connection = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=settings["POSTGRES_DB"],
    user=settings["POSTGRES_USER"],
    password=settings["POSTGRES_PASSWORD"],
)

with connection, connection.cursor() as cursor:
    cursor.execute(sql)
    print("Tables créées ou déjà présentes.")
    if RESET_OPTION in sys.argv:
        cursor.execute("truncate table " + ", ".join(tables) + " restart identity;")
        print(f"{len(tables)} tables vidées.")

connection.close()
