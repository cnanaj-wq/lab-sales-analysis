"""Écriture du modèle physique de données (MPD) en DBML (Lab Sales Analysis).

Lit les mêmes fichiers que 03_generer_ddl.py : config/modele/schemas.csv,
un dossier par schéma avec un CSV par table, et relations.csv.
Écrit docs/modeles/mpd.dbml, à coller dans https://dbdiagram.io pour le dessin.
Le MPD décrit donc toujours exactement les tables créées dans la base.
Lancement depuis la racine du projet :
    python scripts/08_generer_mpd.py
"""

# --- Imports ------------------------------------------------------------------

import csv
import sys
from datetime import date
from pathlib import Path

# --- Constantes ---------------------------------------------------------------

MODEL_DIR = Path("config") / "modele"
SCHEMAS_FILE = MODEL_DIR / "schemas.csv"
RELATIONS_FILE = MODEL_DIR / "relations.csv"
OUTPUT_FILE = Path("docs") / "modeles" / "mpd.dbml"

# Couleur de chaque couche dans le diagramme
COLORS = {"ops": "#6B7280", "bronze": "#B45309", "silver": "#64748B", "gold": "#CA8A04"}


# --- Outils -------------------------------------------------------------------


def read_csv(path):
    """Lit un fichier CSV du modèle et renvoie une liste de lignes."""
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def note(text):
    """Met un texte entre apostrophes pour le DBML, en protégeant ses apostrophes."""
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


# --- DBML d'une table ---------------------------------------------------------


def table_dbml(schema, table, columns):
    """Renvoie le bloc DBML d'une table."""
    keys = [c["colonne"] for c in columns if c["cle_primaire"] == "oui"]
    lines = []
    for column in columns:
        settings = []
        if len(keys) == 1 and column["colonne"] in keys:
            settings.append("pk")
        elif column["obligatoire"] == "oui":
            settings.append("not null")
        if column["description"]:
            settings.append(f"note: {note(column['description'])}")
        options = f" [{', '.join(settings)}]" if settings else ""
        type_sql = column["type_sql"].replace(" ", "_")
        lines.append(f"  {column['colonne']} {type_sql}{options}")

    # Clé primaire sur plusieurs colonnes
    if len(keys) > 1:
        lines += ["", "  indexes {", f"    ({', '.join(keys)}) [pk]", "  }"]

    return f"Table {schema}.{table} {{\n" + "\n".join(lines) + "\n}\n"


# --- Lecture des schémas ------------------------------------------------------

if not SCHEMAS_FILE.exists():
    sys.exit(f"Arrêt : fichier des schémas introuvable ({SCHEMAS_FILE}).")

descriptions = {}
for row in read_csv(SCHEMAS_FILE):
    descriptions[row["schema"]] = row["description"]

# --- Écriture du DBML ---------------------------------------------------------

dbml = (
    "// Modèle physique de données - Lab Sales Analysis\n"
    f"// Écrit par scripts/08_generer_mpd.py le {date.today()} à partir de config/modele :\n"
    "// ne pas modifier à la main. À coller dans https://dbdiagram.io pour le dessin.\n"
    "\n"
    "Project lab_sales_analysis {\n"
    "  database_type: 'PostgreSQL'\n"
    "  Note: 'Architecture médaillon : bronze, silver, gold, et ops pour le suivi du pipeline.'\n"
    "}\n"
)

nb_tables = 0
for folder in sorted(MODEL_DIR.iterdir()):
    if not folder.is_dir():
        continue
    schema = folder.name.split("_", 1)[1]
    if schema not in descriptions:
        sys.exit(f"Arrêt : le schéma {schema} manque dans {SCHEMAS_FILE}.")

    tables = []
    dbml += f"\n// {'=' * 76}\n// {schema} : {descriptions[schema]}\n// {'=' * 76}\n\n"
    for table_file in sorted(folder.glob("*.csv")):
        dbml += table_dbml(schema, table_file.stem, read_csv(table_file)) + "\n"
        tables.append(f"{schema}.{table_file.stem}")
        nb_tables += 1

    color = COLORS.get(schema, "#64748B")
    dbml += f"TableGroup {schema} [color: {color}] {{\n"
    dbml += "".join(f"  {table}\n" for table in tables) + "}\n"

# --- Relations ----------------------------------------------------------------

nb_relations = 0
if RELATIONS_FILE.exists():
    dbml += f"\n// {'=' * 76}\n// Relations (clés étrangères)\n// {'=' * 76}\n\n"
    for relation in read_csv(RELATIONS_FILE):
        dbml += (
            f"Ref: {relation['table']}.{relation['colonne']}"
            f" > {relation['table_reference']}.{relation['colonne_reference']}\n"
        )
        nb_relations += 1

# --- Écriture du fichier ------------------------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.write_text(dbml, encoding="utf-8")
print(f"{nb_tables} tables et {nb_relations} relations écrites dans {OUTPUT_FILE}")
