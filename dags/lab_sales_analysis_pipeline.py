"""DAG du pipeline des ventes (Lab Sales Analysis).

Enchaîne les scripts du projet : chargement de bronze, construction de silver,
porte qualité RC01 (bronze = silver), groupe gold (les 3 tables gold et le
modèle en étoile, en parallèle), puis porte qualité RC02 (silver = gold).
Chaque tâche est notée dans ops.journal_taches ; chaque contrôle dans
ops.journal_controles. XCom ne transporte que de petits compteurs.
Un mail part vers l'astreinte (Mailpit en local) : bilan des contrôles si tout
est OK, alerte avec l'erreur et les contrôles si une tâche échoue.
"""

# --- Imports ------------------------------------------------------------------

import importlib
import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from html import escape
from pathlib import Path
from urllib.parse import quote

from airflow.sdk import Param, Variable, dag, get_current_context, task, task_group
from airflow.sdk.exceptions import AirflowFailException

# --- Constantes ---------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
CONTROLS_DIR = PROJECT_DIR / "sql" / "controles"
MEASURES = ["tickets", "ca", "quantite"]
THRESHOLD_VARIABLE = "lab_sales_seuil_ecart"
ALERT_RECIPIENTS = ["astreinte-data@lab.local"]
AIRFLOW_UI_URL = "http://localhost:8090"

log = logging.getLogger(__name__)

# Les scripts du projet (connexion.py, 04_charger_bronze.py...) sont dans scripts/
sys.path.insert(0, str(SCRIPTS_DIR))

# Compteur de chaque tâche recopié dans journal_taches.nb_lignes
ROW_COUNTERS = {
    "charger_bronze": "tickets_charges",
    "construire_silver": "articles_inseres",
    "gold.construire_gold": "lignes_ecrites",
    "gold.construire_star_schema": "lignes_ecrites",
}


# --- Outils communs -----------------------------------------------------------


def logical_day(context):
    """Renvoie la journée traitée par l'exécution (date logique).

    La date est stockée en UTC : minuit à Paris vaut 23 h UTC la veille.
    On la convertit dans le fuseau du DAG avant de garder le jour.
    """
    logical = context.get("logical_date") or context["dag_run"].run_after
    return logical.astimezone(context["dag"].timezone).date()


def controlled_day(context):
    """Renvoie la journée à contrôler, ou None pour toute la table.

    1. le paramètre jour s'il est renseigné ;
    2. sinon pour un rattrapage (backfill), la date logique du run ;
    3. sinon (run planifié ou manuel) None : toute la table.
    """
    if context["params"]["jour"]:
        return context["params"]["jour"]
    if context["dag_run"].run_type == "backfill":
        return logical_day(context)
    return None


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
    mail_failure(context)


# --- Mails à l'astreinte ------------------------------------------------------


def read_controls(run_id):
    """Lit le dernier résultat de chaque contrôle (code, mesure) d'un run."""
    from connexion import connect

    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select distinct on (code_controle, mesure)
                    code_controle, mesure, valeur_bronze, valeur_silver,
                    valeur_gold, ecart, seuil, resultat
                from ops.journal_controles
                where run_id = %(run_id)s
                order by code_controle, mesure, controle_id desc
                """,
                {"run_id": run_id},
            )
            return cursor.fetchall()
    finally:
        connection.close()


def controls_html(rows):
    """Met les contrôles d'un run en tableau HTML."""
    if not rows:
        return "<p>Aucun contrôle enregistré pour ce run.</p>"
    header = "".join(
        f"<th>{title}</th>"
        for title in [
            "Contrôle",
            "Mesure",
            "Bronze",
            "Silver",
            "Gold",
            "Écart",
            "Seuil",
            "Résultat",
        ]
    )
    lines = []
    for row in rows:
        color = "#1d7a3e" if row[-1] == "OK" else "#b42318"
        cells = "".join(
            f"<td>{escape('' if v is None else str(v))}</td>" for v in row[:-1]
        )
        lines.append(f"<tr>{cells}<td style='color:{color}'><b>{row[-1]}</b></td></tr>")
    return (
        "<table border='1' cellpadding='4' cellspacing='0'>"
        f"<tr>{header}</tr>{''.join(lines)}</table>"
    )


def send_mail(subject, html):
    """Envoie un mail par la connexion smtp_default.

    Une panne de messagerie ne doit pas faire échouer le pipeline :
    l'erreur est notée dans le log de la tâche, sans être relancée.
    """
    from airflow.providers.smtp.hooks.smtp import SmtpHook

    try:
        with SmtpHook(smtp_conn_id="smtp_default") as smtp:
            smtp.send_email_smtp(
                to=ALERT_RECIPIENTS, subject=subject, html_content=html
            )
    except Exception:  # le mail ne doit jamais bloquer le pipeline
        log.exception("Mail non envoyé : %s", subject)


def mail_failure(context):
    """Alerte l'astreinte quand une tâche échoue définitivement."""
    ti = context["ti"]
    day = logical_day(context)
    kind = "QUALITÉ KO" if ti.task_id.startswith("quality_gate") else "ÉCHEC"
    link = (
        f"{AIRFLOW_UI_URL}/dags/{ti.dag_id}/runs/{quote(ti.run_id, safe='')}"
        f"/tasks/{ti.task_id}"
    )
    html = (
        f"<h2>{kind} : {escape(ti.task_id)}</h2>"
        f"<p>DAG <b>{ti.dag_id}</b>, run <b>{escape(ti.run_id)}</b>, "
        f"journée {day}, essai {ti.try_number}.</p>"
        f"<p><b>Erreur :</b> {escape(error_message(context) or 'non transmise')}</p>"
        "<p>La suite du pipeline n'a pas été exécutée.</p>"
        f"<h3>Contrôles du run</h3>{controls_html(read_controls(ti.run_id))}"
        f"<p><a href='{link}'>Ouvrir la tâche dans Airflow</a></p>"
    )
    send_mail(f"[Lab Sales] {kind} {ti.task_id} - {day}", html)


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


def run_quality_gate(code, upstream, downstream, delivery_id):
    """Compare les mesures de deux couches, note le résultat et bloque si KO.

    upstream et downstream sont des noms de couche : bronze, silver ou gold.
    """
    day = controlled_day(get_current_context())
    threshold = Decimal(Variable.get(THRESHOLD_VARIABLE, default="0"))

    upstream_values = read_measures(upstream, day)
    downstream_values = read_measures(downstream, day)

    results = []
    for measure in MEASURES:
        gap = abs(
            Decimal(downstream_values[measure]) - Decimal(upstream_values[measure])
        )
        result = {
            "mesure": measure,
            "bronze": None,
            "silver": None,
            "gold": None,
            "ecart": gap,
            "seuil": threshold,
            "resultat": "OK" if gap <= threshold else "KO",
            "nb_ecarts": 0 if gap <= threshold else 1,
        }
        result[upstream] = upstream_values[measure]
        result[downstream] = downstream_values[measure]
        results.append(result)

    write_control_journal(code, results, delivery_id)

    failed = [r["mesure"] for r in results if r["resultat"] == "KO"]
    if failed:
        raise AirflowFailException(
            f"{code} KO : {upstream} ≠ {downstream} ({', '.join(failed)})"
        )
    return {r["mesure"]: r["resultat"] for r in results}


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
    dag_id="lab_sales_analysis_pipeline",
    description="Ventes : bronze → silver → RC01 → gold (tables + étoile) → RC02",
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
            description=(
                "AAAA-MM-JJ pour contrôler une journée ; vide = toute la table "
                "(ou la date logique pour un rattrapage)"
            ),
        ),
    },
)
def lab_sales_analysis_pipeline():
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
        return run_quality_gate("RC01", "bronze", "silver", bronze["livraison_id"])

    @task_group
    def gold(rc01):
        """Les 3 tables gold et le modèle en étoile, construits en parallèle."""

        @task
        def construire_gold(rc01):
            # rc01 n'est pas lu : le recevoir fait attendre la porte RC01
            counts = run_script("06_construire_gold")
            return {**counts, "lignes_ecrites": sum(counts.values())}

        @task
        def construire_star_schema(rc01):
            counts = run_script("06_construire_gold_star_schema")
            return {**counts, "lignes_ecrites": sum(counts.values())}

        return [construire_gold(rc01), construire_star_schema(rc01)]

    @task(retries=0)
    def quality_gate_rc02(bronze, gold_tables):
        """Porte qualité : silver et l'étoile de gold doivent avoir les mêmes totaux."""
        return run_quality_gate("RC02", "silver", "gold", bronze["livraison_id"])

    @task
    def envoyer_bilan(rc02):
        """Envoie le bilan des contrôles à l'astreinte quand tout est OK."""
        context = get_current_context()
        day = logical_day(context)
        html = (
            f"<h2>Pipeline OK : journée {day}</h2>"
            f"<p>Run <b>{escape(context['run_id'])}</b> : bronze, silver et gold "
            "construits, portes RC01 et RC02 validées.</p>"
            f"<h3>Contrôles du run</h3>{controls_html(read_controls(context['run_id']))}"
        )
        send_mail(f"[Lab Sales] OK - {day}", html)

    bronze = charger_bronze()
    silver = construire_silver(bronze)
    rc01 = quality_gate_rc01(bronze, silver)
    rc02 = quality_gate_rc02(bronze, gold(rc01))
    envoyer_bilan(rc02)


lab_sales_analysis_pipeline()
