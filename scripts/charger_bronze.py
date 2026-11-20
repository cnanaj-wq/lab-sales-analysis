"""Chargement d'un fichier JSON de ventes dans bronze (Lab Sales Analysis).

Contrôle le fichier, calcule son empreinte pour ne jamais l'intégrer deux fois,
charge les tickets tels quels dans bronze.pos_sales_raw et trace la livraison
dans ops.journal_livraisons. Le chargement se fait en une seule transaction :
tout est chargé, ou rien.
Lancement depuis la racine du projet :
    python scripts/charger_bronze.py [chemin_du_fichier.json]
"""

# --- Imports ------------------------------------------------------------------

import hashlib
import json
import sys
from pathlib import Path

from psycopg2.extras import Json, execute_values

from connexion import connect
from messages import log, stop

# --- Constantes ---------------------------------------------------------------

DEFAULT_SOURCE_FILE = Path("data") / "raw" / "pos_sales_data_30k.json"
ARCHIVE_DIR = Path("data") / "archive"
BATCH_SIZE = 1000

STATUS_PUBLISHED = "publiée"
STATUS_ALREADY_LOADED = "déjà intégrée"
STATUS_REJECTED = "refusée"


# --- Empreinte du fichier -----------------------------------------------------


def file_hash(content):
    """Renvoie l'empreinte SHA-256 d'un contenu, en 64 caractères hexadécimaux."""
    return hashlib.sha256(content).hexdigest()


# --- Contrôle du fichier source -----------------------------------------------

if len(sys.argv) > 1:
    source_file = Path(sys.argv[1])
else:
    source_file = DEFAULT_SOURCE_FILE

if not source_file.parent.is_dir():
    stop(f"dossier de dépôt introuvable ({source_file.parent}).")
if not source_file.is_file():
    stop(f"fichier source introuvable ({source_file}).")

# --- Lecture du fichier -------------------------------------------------------

content = source_file.read_bytes()
fingerprint = file_hash(content)

try:
    tickets = json.loads(content)
except json.JSONDecodeError as error:
    stop(f"le fichier n'est pas un JSON valide ({error}).")

if not isinstance(tickets, list) or not tickets:
    stop("le fichier ne contient aucun ticket.")

log(f"{len(tickets)} tickets lus dans {source_file.name}")

# --- Fichier déjà intégré ? ---------------------------------------------------

connection = connect()

with connection, connection.cursor() as cursor:
    cursor.execute(
        """
        select livraison_id
        from ops.journal_livraisons
        where empreinte_fichier = %s and statut = %s
        """,
        (fingerprint, STATUS_PUBLISHED),
    )
    previous = cursor.fetchone()
    if previous:
        cursor.execute(
            """
            insert into ops.journal_livraisons
                (nom_fichier, empreinte_fichier, recu_le, traite_le, nb_tickets, statut)
            values (%s, %s, now(), now(), %s, %s)
            """,
            (source_file.name, fingerprint, len(tickets), STATUS_ALREADY_LOADED),
        )

if previous:
    connection.close()
    log(f"fichier déjà intégré (livraison {previous[0]}) : rien à charger.")
    sys.exit(0)

# --- Chargement dans bronze : tout ou rien ------------------------------------

try:
    with connection, connection.cursor() as cursor:
        cursor.execute(
            """
            insert into ops.journal_livraisons
                (nom_fichier, empreinte_fichier, recu_le, statut)
            values (%s, %s, now(), %s)
            returning livraison_id
            """,
            (source_file.name, fingerprint, STATUS_PUBLISHED),
        )
        delivery_id = cursor.fetchone()[0]

        rows = []
        for ticket in tickets:
            rows.append((ticket["transaction_id"], delivery_id, Json(ticket)))

        inserted = execute_values(
            cursor,
            """
            insert into bronze.pos_sales_raw
                (transaction_id, livraison_id, document, charge_le)
            values %s
            on conflict (transaction_id) do nothing
            returning transaction_id
            """,
            rows,
            template="(%s, %s, %s, now())",
            page_size=BATCH_SIZE,
            fetch=True,
        )

        cursor.execute(
            """
            update ops.journal_livraisons
            set traite_le = clock_timestamp(), nb_tickets = %s
            where livraison_id = %s
            """,
            (len(tickets), delivery_id),
        )
except Exception as error:  # noqa: BLE001 - toute erreur refuse la livraison
    with connection, connection.cursor() as cursor:
        cursor.execute(
            """
            insert into ops.journal_livraisons
                (nom_fichier, empreinte_fichier, recu_le, traite_le, nb_tickets, statut)
            values (%s, %s, now(), now(), %s, %s)
            """,
            (source_file.name, fingerprint, len(tickets), STATUS_REJECTED),
        )
    connection.close()
    stop(f"chargement annulé, rien n'a été publié ({error}).")

connection.close()
ignored = len(tickets) - len(inserted)
log(f"livraison {delivery_id} publiée : {len(inserted)} tickets chargés dans bronze.")
log(f"{ignored} tickets déjà présents, ignorés.")

# --- Archive du fichier -------------------------------------------------------

ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
archive_file = ARCHIVE_DIR / f"{fingerprint}.json"
if not archive_file.exists():
    archive_file.write_bytes(content)
log(f"fichier archivé : {archive_file}")
