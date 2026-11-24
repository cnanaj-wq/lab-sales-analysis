"""DAG du pipeline des ventes (Lab Sales Analysis).

Enchaîne les scripts du projet : chargement de bronze, construction de silver,
porte qualité RC01 (bronze = silver), groupe gold (les 3 tables gold et le
modèle en étoile, en parallèle), puis porte qualité RC02 (silver = l'étoile
et les 3 tables gold). Les portes comparent les mesures devise par devise.
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

# Tables rapprochées par chaque porte qualité. requete : fichier
# sql/controles/mesures_<requete>.sql ; mesures : ce que la table sait calculer.
# toute_la_table : la table n'a pas de date, elle se contrôle toujours en entier.
# toutes_devises : la table n'a pas de devise, elle est rapprochée sur son total.
RC01_TABLES = [
    {
        "table": "silver.exploded_products",
        "requete": "silver",
        "mesures": ["tickets", "ca", "quantite"],
    },
]
RC02_TABLES = [
    {
        "table": "gold.etoile",
        "requete": "gold_etoile",
        "mesures": ["tickets", "ca", "quantite"],
    },
    {
        "table": "gold.daily_sales_country_currency",
        "requete": "gold_daily_sales",
        "mesures": ["tickets", "ca"],
    },
    {
        "table": "gold.store_sales_summary",
        "requete": "gold_store_sales",
        "mesures": ["ca", "quantite"],
        "toute_la_table": True,
    },
    {
        "table": "gold.payment_method_analysis",
        "requete": "gold_payment_method",
        "mesures": ["tickets", "ca"],
        "toute_la_table": True,
        "toutes_devises": True,
    },
]
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


def run_script(module_name, *args, **kwargs):
    """Lance main() d'un script du projet et renvoie ses compteurs.

    stop() arrête un script avec sys.exit : on le transforme en erreur
    ordinaire pour qu'Airflow note l'échec et puisse réessayer.
    """
    module = importlib.import_module(module_name)
    try:
        return module.main(*args, **kwargs)
    except SystemExit as error:
        raise RuntimeError(str(error)) from None


def read_measures(query_name, day):
    """Lit les mesures d'une requête de contrôle : {(devise, mesure): valeur}.

    La requête renvoie une ligne par devise : la devise, puis une colonne
    par mesure. day = None : toute la table.
    """
    from connexion import connect

    query = (CONTROLS_DIR / f"mesures_{query_name}.sql").read_text(encoding="utf-8")
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, {"jour": day})
            columns = [column.name for column in cursor.description]
            rows = cursor.fetchall()
    finally:
        connection.close()

    measures = {}
    for row in rows:
        for column, value in zip(columns[1:], row[1:]):
            measures[(row[0], column)] = value
    return measures


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
    """Lit le dernier résultat de chaque contrôle d'un run, KO en tête.

    Un contrôle est identifié par son code, sa table, sa devise et sa mesure.
    """
    from connexion import connect

    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select * from (
                    select distinct on (code_controle, table_controlee, devise, mesure)
                        code_controle, table_controlee, devise, mesure,
                        valeur_bronze, valeur_silver, valeur_gold,
                        ecart, seuil, resultat
                    from ops.journal_controles
                    where run_id = %(run_id)s
                    order by code_controle, table_controlee, devise, mesure,
                        controle_id desc
                ) as dernier
                order by resultat, code_controle, table_controlee, devise, mesure
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
            "Table",
            "Devise",
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
                        run_id, date_logique, livraison_id, code_controle,
                        table_controlee, devise, mesure,
                        valeur_bronze, valeur_silver, valeur_gold, ecart,
                        seuil, bloquant, resultat, nb_ecarts, controle_le
                    )
                    values (
                        %(run_id)s, %(jour)s, %(livraison_id)s, %(code)s,
                        %(table_controlee)s, %(devise)s, %(mesure)s,
                        %(bronze)s, %(silver)s, %(gold)s, %(ecart)s,
                        %(seuil)s, true, %(resultat)s, %(nb_ecarts)s, now()
                    )
                    """,
                    {
                        "run_id": context["run_id"],
                        "jour": logical_day(context),
                        "livraison_id": delivery_id,
                        "code": code,
                        "bronze": None,
                        "silver": None,
                        "gold": None,
                        **result,
                    },
                )
    finally:
        connection.close()


def run_quality_gate(code, upstream_layer, tables, delivery_id):
    """Rapproche une couche amont de chaque table aval, devise par devise.

    Écrit une ligne par table, devise et mesure dans ops.journal_controles,
    puis arrête le DAG si une seule ligne est KO.
    """
    from rapprochement import compare_measures, select_upstream

    day = controlled_day(get_current_context())
    threshold = Decimal(Variable.get(THRESHOLD_VARIABLE, default="0"))

    results = []
    for target in tables:
        # Une table sans date se contrôle toujours en entier
        target_day = None if target.get("toute_la_table") else day
        upstream = select_upstream(
            read_measures(upstream_layer, target_day),
            target["mesures"],
            all_currencies=target.get("toutes_devises", False),
        )
        downstream = read_measures(target["requete"], target_day)
        downstream_layer = target["table"].split(".")[0]
        for result in compare_measures(upstream, downstream, threshold):
            result["table_controlee"] = target["table"]
            result[upstream_layer] = result["amont"]
            result[downstream_layer] = result["aval"]
            results.append(result)

    write_control_journal(code, results, delivery_id)

    failed = [
        f"{r['table_controlee']} {r['devise'] or 'toutes devises'} {r['mesure']}"
        for r in results
        if r["resultat"] == "KO"
    ]
    if failed:
        raise AirflowFailException(
            f"{code} KO : {len(failed)} écart(s) avec {upstream_layer} : "
            + ", ".join(failed[:10])
        )
    return {"mesures_controlees": len(results), "ko": 0}


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
        context = get_current_context()
        return run_script(
            "04_charger_bronze",
            run_id=context["run_id"],
            control_day=logical_day(context),
        )

    @task
    def construire_silver(bronze):
        # bronze n'est pas lu ici : le recevoir fait attendre la fin du chargement
        return run_script("05_construire_silver")

    @task(retries=0)
    def quality_gate_rc01(bronze, silver):
        """Porte qualité : bronze et silver, mêmes totaux devise par devise."""
        return run_quality_gate("RC01", "bronze", RC01_TABLES, bronze["livraison_id"])

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
        """Porte qualité : silver, l'étoile et les 3 tables gold, devise par devise."""
        return run_quality_gate("RC02", "silver", RC02_TABLES, bronze["livraison_id"])

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
