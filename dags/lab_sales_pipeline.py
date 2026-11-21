"""DAG du pipeline des ventes (Lab Sales Analysis).

Enchaîne les scripts du projet : chargement de bronze, construction de silver,
puis la porte qualité RC01 (bronze = silver). La suite (gold, RC02) viendra
au bloc suivant.
Chaque tâche est notée dans ops.journal_taches ; chaque contrôle dans
ops.journal_controles. XCom ne transporte que de petits compteurs.
"""

# --- Imports ------------------------------------------------------------------

import importlib
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from airflow.sdk import Param, Variable, dag, get_current_context, task
from airflow.sdk.exceptions import AirflowFailException

# --- Constantes ---------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
CONTROLS_DIR = PROJECT_DIR / "sql" / "controles"
MEASURES = ["tickets", "ca", "quantite"]
THRESHOLD_VARIABLE = "lab_sales_seuil_ecart"

# Les scripts du projet (connexion.py, 04_charger_bronze.py...) sont dans scripts/
sys.path.insert(0, str(SCRIPTS_DIR))

# Compteur de chaque tâche recopié dans journal_taches.nb_lignes
ROW_COUNTERS = {
    "charger_bronze": "tickets_charges",
    "construire_silver": "articles_inseres",
}


# --- Outils communs -----------------------------------------------------------


def logical_day(context):
    """Renvoie la journée traitée par l'exécution (date logique)."""
    logical = context.get("logical_date") or context["dag_run"].run_after
    return logical.date()


def run_script(module_name, *args):
    """Lance main() d'un script du projet et renvoie ses compteurs.

    stop() arrête un script avec sys.exit : on le transforme en erreur
    ordinaire pour qu'Airflow note l'échec et puisse réessayer.
    """
    module = importlib.import_module(module_name)
    try:
        return module.main(*args)
    except SystemExit as error:
        raise RuntimeError(str(error)) from None


def read_measures(layer, day):
    """Lit les mesures tickets, ca, quantite d'une couche (None = toute la table)."""
    from connexion import connect

    query = (CONTROLS_DIR / f"mesures_{layer}.sql").read_text(encoding="utf-8")
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, {"jour": day})
            row = cursor.fetchone()
    finally:
        connection.close()
    return dict(zip(MEASURES, row))


# --- Journal des tâches (callbacks) -------------------------------------------


def write_task_journal(context, status, message=None):
    """Crée ou met à jour la ligne de la tâche dans ops.journal_taches."""
    from connexion import connect

    ti = context["ti"]
    key = {"run_id": ti.run_id, "tache": ti.task_id, "essai": ti.try_number}

    connection = connect()
    try:
        with connection, connection.cursor() as cursor:
            if status == "en cours":
                cursor.execute(
                    """
                    insert into ops.journal_taches
                        (run_id, date_logique, tache, debut_le, statut, essai)
                    values (%(run_id)s, %(jour)s, %(tache)s, now(), %(statut)s, %(essai)s)
                    """,
                    {**key, "jour": logical_day(context), "statut": status},
                )
                return

            # Fin de tâche : nombre de lignes lu dans le XCom de la tâche
            nb_rows = None
            counter = ROW_COUNTERS.get(ti.task_id)
            if status == "succès" and counter:
                result = ti.xcom_pull(task_ids=ti.task_id) or {}
                nb_rows = result.get(counter)

            cursor.execute(
                """
                update ops.journal_taches
                set fin_le = now(), statut = %(statut)s,
                    nb_lignes = %(nb_lignes)s, message = %(message)s
                where run_id = %(run_id)s and tache = %(tache)s and essai = %(essai)s
                """,
                {**key, "statut": status, "nb_lignes": nb_rows, "message": message},
            )
    finally:
        connection.close()


def error_message(context):
    """Renvoie le début du message d'erreur, ou None s'il n'y en a pas."""
    error = context.get("exception")
    return str(error)[:500] if error else None


def on_task_start(context):
    write_task_journal(context, "en cours")


def on_task_success(context):
    write_task_journal(context, "succès")


def on_task_retry(context):
    write_task_journal(context, "réessai", error_message(context))


def on_task_failure(context):
    write_task_journal(context, "échec", error_message(context))


# --- Journal des contrôles ----------------------------------------------------


def write_control_journal(code, results, delivery_id):
    """Écrit une ligne par mesure dans ops.journal_controles."""
    from connexion import connect

    context = get_current_context()
    connection = connect()
    try:
        with connection, connection.cursor() as cursor:
            for result in results:
                cursor.execute(
                    """
                    insert into ops.journal_controles (
                        run_id, date_logique, livraison_id, code_controle, mesure,
                        valeur_bronze, valeur_silver, valeur_gold, ecart,
                        seuil, bloquant, resultat, nb_ecarts, controle_le
                    )
                    values (
                        %(run_id)s, %(jour)s, %(livraison_id)s, %(code)s, %(mesure)s,
                        %(bronze)s, %(silver)s, %(gold)s, %(ecart)s,
                        %(seuil)s, true, %(resultat)s, %(nb_ecarts)s, now()
                    )
                    """,
                    {
                        "run_id": context["run_id"],
                        "jour": logical_day(context),
                        "livraison_id": delivery_id,
                        "code": code,
                        **result,
                    },
                )
    finally:
        connection.close()


# --- DAG ----------------------------------------------------------------------

DEFAULT_ARGS = {
    "owner": "lab-sales",
    "retries": 2,
    "retry_delay": timedelta(seconds=30),
    "on_execute_callback": on_task_start,
    "on_success_callback": on_task_success,
    "on_retry_callback": on_task_retry,
    "on_failure_callback": on_task_failure,
}


@dag(
    dag_id="lab_sales_pipeline",
    description="Ventes : bronze → silver → porte RC01 (bronze = silver)",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["lab-sales", "medaillon", "qualite"],
    params={
        "jour": Param(
            None,
            type=["null", "string"],
            format="date",
            description="AAAA-MM-JJ pour contrôler une journée ; vide = toute la table",
        ),
    },
)
def lab_sales_pipeline():
    @task
    def charger_bronze():
        return run_script("04_charger_bronze")

    @task
    def construire_silver(bronze):
        # bronze n'est pas lu ici : le recevoir fait attendre la fin du chargement
        return run_script("05_construire_silver")

    @task(retries=0)
    def quality_gate_rc01(bronze, silver):
        """Porte qualité : bronze et silver doivent avoir les mêmes totaux."""
        day = get_current_context()["params"]["jour"]
        threshold = Decimal(Variable.get(THRESHOLD_VARIABLE, default="0"))

        bronze_values = read_measures("bronze", day)
        silver_values = read_measures("silver", day)

        results = []
        for measure in MEASURES:
            gap = abs(Decimal(silver_values[measure]) - Decimal(bronze_values[measure]))
            results.append(
                {
                    "mesure": measure,
                    "bronze": bronze_values[measure],
                    "silver": silver_values[measure],
                    "gold": None,
                    "ecart": gap,
                    "seuil": threshold,
                    "resultat": "OK" if gap <= threshold else "KO",
                    "nb_ecarts": 0 if gap <= threshold else 1,
                }
            )

        write_control_journal("RC01", results, bronze["livraison_id"])

        failed = [r["mesure"] for r in results if r["resultat"] == "KO"]
        if failed:
            raise AirflowFailException(
                f"RC01 KO : bronze ≠ silver ({', '.join(failed)})"
            )
        return {r["mesure"]: r["resultat"] for r in results}

    bronze = charger_bronze()
    silver = construire_silver(bronze)
    quality_gate_rc01(bronze, silver)


lab_sales_pipeline()
