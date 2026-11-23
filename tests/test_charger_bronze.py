"""Tests du chargement dans bronze (scripts/04_charger_bronze.py)."""

# --- Imports ------------------------------------------------------------------

import importlib
from pathlib import Path

import pytest

# --- Constantes ---------------------------------------------------------------

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"
LOT_NOMINAL = SAMPLE_DIR / "lot_nominal.json"

# Le nom du script commence par un chiffre : import par importlib
bronze = importlib.import_module("04_charger_bronze")

# --- Fixtures -----------------------------------------------------------------


@pytest.fixture
def archive_dir(tmp_path, monkeypatch):
    """Redirige l'archive vers un dossier temporaire, pour ne pas toucher data/archive."""
    monkeypatch.setattr(bronze, "ARCHIVE_DIR", tmp_path)
    return tmp_path


# --- Tests --------------------------------------------------------------------


def test_lot_nominal_charge_3_tickets(db, archive_dir):
    """Une livraison correcte est publiée, chargée en entier et archivée."""
    result = bronze.main(LOT_NOMINAL)

    assert result["statut"] == "publiée"
    assert result["tickets_lus"] == 3
    assert result["tickets_charges"] == 3
    with db.cursor() as cursor:
        cursor.execute("select count(*) from bronze.pos_sales_raw")
        assert cursor.fetchone()[0] == 3
    assert len(list(archive_dir.glob("*.json"))) == 1


def test_meme_fichier_livre_deux_fois_n_est_pas_recharge(db, archive_dir):
    """Un fichier déjà intégré est reconnu à son empreinte et n'est pas rechargé."""
    first = bronze.main(LOT_NOMINAL)
    second = bronze.main(LOT_NOMINAL)

    assert second["statut"] == "déjà intégrée"
    assert second["tickets_charges"] == 0
    assert second["livraison_id"] == first["livraison_id"]
    with db.cursor() as cursor:
        cursor.execute("select count(*) from bronze.pos_sales_raw")
        assert cursor.fetchone()[0] == 3
        cursor.execute(
            "select statut from ops.journal_livraisons order by livraison_id"
        )
        assert [row[0] for row in cursor.fetchall()] == ["publiée", "déjà intégrée"]
