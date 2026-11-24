"""Chargement d'un fichier JSON de ventes dans bronze (Lab Sales Analysis).

Contrôle le fichier, calcule son empreinte pour ne jamais l'intégrer deux fois,
charge les tickets tels quels dans bronze.pos_sales_raw et trace la livraison
dans ops.journal_livraisons. Le chargement se fait en une seule transaction :
tout est chargé, ou rien.
Lancement depuis la racine du projet :
    python scripts/04_charger_bronze.py [chemin_du_fichier.json]
"""

# --- Imports ------------------------------------------------------------------

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from psycopg2.extras import Json, execute_values

from connexion import connect
from messages import log, stop

# --- Constantes ---------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_FILE = PROJECT_DIR / "data" / "raw" / "pos_sales_data_30k.json"
ARCHIVE_DIR = PROJECT_DIR / "data" / "archive"
BATCH_SIZE = 1000

STATUS_PUBLISHED = "publiée"
STATUS_ALREADY_LOADED = "déjà intégrée"
STATUS_REJECTED = "refusée"
CONTROL_CODE = "CQ14"
MAX_EXAMPLES = 10

# --- Empreinte du fichier -----------------------------------------------------


def file_hash(content):
    """Renvoie l'empreinte SHA-256 d'un contenu, en 64 caractères hexadécimaux."""
    return hashlib.sha256(content).hexdigest()


# --- Contrôle CQ14 : ticket déjà chargé et modifié ----------------------------


def modified_tickets(cursor, tickets):
    """Renvoie les tickets déjà présents dans bronze avec un contenu différent."""
    cursor.execute(
        """
        select transaction_id, document
        from bronze.pos_sales_raw
        where transaction_id = any(%s)
        """,
        ([ticket["transaction_id"] for ticket in tickets],),
    )
    loaded = dict(cursor.fetchall())

    modified = []
    for ticket in tickets:
        transaction_id = ticket["transaction_id"]
        if transaction_id in loaded and loaded[transaction_id] != ticket:
            modified.append(transaction_id)
    return modified


def write_control(cursor, delivery_id, modified, run_id, control_day):
    """Écrit le résultat de CQ14 dans ops.journal_controles."""
    cursor.execute(
        """
        insert into ops.journal_controles (
            run_id, date_logique, livraison_id, code_controle, mesure,
            seuil, bloquant, resultat, nb_ecarts, exemples, controle_le
        )
        values (%s, %s, %s, %s, 'tickets', 0, true, %s, %s, %s, now())
        """,
        (
            run_id,
            control_day,
            delivery_id,
            CONTROL_CODE,
            "KO" if modified else "OK",
            len(modified),
            ", ".join(modified[:MAX_EXAMPLES]) or None,
        ),
    )


# --- Chargement d'un fichier --------------------------------------------------


def main(source_file=DEFAULT_SOURCE_FILE, run_id="manuel", control_day=None):
    """Charge un fichier JSON dans bronze et renvoie les compteurs du chargement."""
    source_file = Path(source_file)
    control_day = control_day or date.today()

    # Contrôle du fichier source
    if not source_file.parent.is_dir():
        stop(f"dossier de dépôt introuvable ({source_file.parent}).")
    if not source_file.is_file():
        stop(f"fichier source introuvable ({source_file}).")

    # Lecture du fichier
    content = source_file.read_bytes()
    fingerprint = file_hash(content)

    try:
        tickets = json.loads(content)
    except json.JSONDecodeError as error:
        stop(f"le fichier n'est pas un JSON valide ({error}).")

    if not isinstance(tickets, list) or not tickets:
        stop("le fichier ne contient aucun ticket.")

    log(f"{len(tickets)} tickets lus dans {source_file.name}")

    # Fichier déjà intégré ?
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
        return {
            "livraison_id": previous[0],
            "statut": STATUS_ALREADY_LOADED,
            "tickets_lus": len(tickets),
            "tickets_charges": 0,
        }

    # CQ14 : un ticket déjà chargé ne doit pas revenir avec un autre contenu
    with connection, connection.cursor() as cursor:
        modified = modified_tickets(cursor, tickets)
        if modified:
            cursor.execute(
                """
                insert into ops.journal_livraisons
                    (nom_fichier, empreinte_fichier, recu_le, traite_le, nb_tickets, statut)
                values (%s, %s, now(), now(), %s, %s)
                returning livraison_id
                """,
                (source_file.name, fingerprint, len(tickets), STATUS_REJECTED),
            )
            write_control(cursor, cursor.fetchone()[0], modified, run_id, control_day)

    if modified:
        connection.close()
        stop(
            f"CQ14 : {len(modified)} tickets déjà chargés reviennent modifiés "
            f"({', '.join(modified[:MAX_EXAMPLES])}). Rien n'a été chargé."
        )

    # Chargement dans bronze : tout ou rien
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
            write_control(cursor, delivery_id, [], run_id, control_day)

            rows = []
            for ticket in tickets:
                rows.append((ticket["transaction_id"], delivery_id, Json(ticket)))

            # Après CQ14, un ticket déjà présent est forcément identique : on l'ignore
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
    log(
        f"livraison {delivery_id} publiée : {len(inserted)} tickets chargés dans bronze."
    )
    log(f"{ignored} tickets déjà présents, ignorés.")

    # Archive du fichier
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_file = ARCHIVE_DIR / f"{fingerprint}.json"
    if not archive_file.exists():
        archive_file.write_bytes(content)
    log(f"fichier archivé : {archive_file}")

    return {
        "livraison_id": delivery_id,
        "statut": STATUS_PUBLISHED,
        "tickets_lus": len(tickets),
        "tickets_charges": len(inserted),
    }


# --- Lancement depuis le terminal ---------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
