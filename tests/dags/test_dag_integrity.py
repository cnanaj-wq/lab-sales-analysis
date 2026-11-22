"""Test d'intégrité du DAG lab_sales_analysis_pipeline.

Vérifie, sans base de données ni exécution, que le DAG se charge et que sa
structure n'a pas changé par erreur : tâches, ordre, portes qualité, réglages.

À lancer dans l'image Airflow (conteneur jetable, depuis la racine du projet) :
    docker run --rm -v "${PWD}:/lab" -w /lab apache/airflow:3.4.0 bash -c "pip install -q pytest==8.3.5 && python -m pytest -q -p no:cacheprovider tests/dags"
"""

# --- Imports ------------------------------------------------------------------

import time
from pathlib import Path

import pytest

pytest.importorskip("airflow")
from airflow.models import DagBag

# --- Constantes ---------------------------------------------------------------

DAGS_DIR = Path(__file__).resolve().parents[2] / "dags"
DAG_ID = "lab_sales_analysis_pipeline"

# Chaque tâche et les tâches qu'elle attend directement
EXPECTED_UPSTREAM = {
    "charger_bronze": set(),
    "construire_silver": {"charger_bronze"},
    "quality_gate_rc01": {"charger_bronze", "construire_silver"},
    "gold.construire_gold": {"quality_gate_rc01"},
    "gold.construire_star_schema": {"quality_gate_rc01"},
    "quality_gate_rc02": {
        "charger_bronze",
        "gold.construire_gold",
        "gold.construire_star_schema",
    },
    "envoyer_bilan": {"quality_gate_rc02"},
}
QUALITY_GATES = ["quality_gate_rc01", "quality_gate_rc02"]


# --- Chargement du DAG --------------------------------------------------------


@pytest.fixture(scope="module")
def dagbag():
    """Charge le dossier dags/ une seule fois et mesure le temps de chargement."""
    start = time.monotonic()
    bag = DagBag(dag_folder=str(DAGS_DIR))
    bag.load_seconds = time.monotonic() - start
    return bag


@pytest.fixture(scope="module")
def dag(dagbag):
    return dagbag.dags[DAG_ID]


# --- Tests --------------------------------------------------------------------


def test_aucune_erreur_import(dagbag):
    assert dagbag.import_errors == {}


def test_chargement_rapide(dagbag):
    """Airflow relit le dossier toutes les 30 s : aucun accès base ou réseau à l'import."""
    assert dagbag.load_seconds < 10


def test_dag_present(dagbag):
    assert DAG_ID in dagbag.dag_ids


def test_taches_attendues(dag):
    assert set(dag.task_ids) == set(EXPECTED_UPSTREAM)


def test_ordre_des_taches(dag):
    for task_id, upstream in EXPECTED_UPSTREAM.items():
        assert dag.get_task(task_id).upstream_task_ids == upstream, task_id


def test_gold_protege_par_rc01(dag):
    """Aucune table gold n'est construite avant la porte RC01."""
    for task_id in ["gold.construire_gold", "gold.construire_star_schema"]:
        ancestors = {
            t.task_id for t in dag.get_task(task_id).get_flat_relatives(upstream=True)
        }
        assert "quality_gate_rc01" in ancestors, task_id


def test_portes_sans_reessai(dag):
    """Une porte qualité rouge ne se réessaie pas : réessayer ne corrige pas les données."""
    for task_id in QUALITY_GATES:
        assert dag.get_task(task_id).retries == 0, task_id


def test_reessais_des_autres_taches(dag):
    for task in dag.tasks:
        if task.task_id not in QUALITY_GATES:
            assert task.retries == 2, task.task_id


def test_journal_et_alertes_sur_chaque_tache(dag):
    """Chaque tâche écrit dans ops.journal_taches et alerte l'astreinte si elle échoue."""
    for task in dag.tasks:
        assert task.on_execute_callback, task.task_id
        assert task.on_success_callback, task.task_id
        assert task.on_failure_callback, task.task_id


def test_reglages_du_dag(dag):
    assert dag.max_active_runs == 1
    assert not dag.catchup
    assert "jour" in dag.params
    assert {"lab-sales", "qualite"} <= set(dag.tags)
