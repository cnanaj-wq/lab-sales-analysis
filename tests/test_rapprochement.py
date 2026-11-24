"""Tests du rapprochement des mesures entre deux couches, devise par devise (#36)."""

# --- Imports ------------------------------------------------------------------

from decimal import Decimal

from rapprochement import compare_measures

# --- Tests --------------------------------------------------------------------


def ko_keys(results):
    """Renvoie les couples (devise, mesure) en échec."""
    return {(r["devise"], r["mesure"]) for r in results if r["resultat"] == "KO"}


def test_ecart_dans_une_seule_devise_detecte():
    """EUR est faux, USD est juste : seul EUR est KO."""
    silver = {("EUR", "ca"): Decimal("100.00"), ("USD", "ca"): Decimal("200.00")}
    gold = {("EUR", "ca"): Decimal("110.00"), ("USD", "ca"): Decimal("200.00")}

    results = compare_measures(silver, gold, threshold=Decimal(0))

    assert ko_keys(results) == {("EUR", "ca")}


def test_ecarts_qui_se_compensent_detectes():
    """+10 en EUR et -10 en USD : le total est égal, mais les deux devises sont KO."""
    silver = {("EUR", "ca"): Decimal("100.00"), ("USD", "ca"): Decimal("200.00")}
    gold = {("EUR", "ca"): Decimal("110.00"), ("USD", "ca"): Decimal("190.00")}

    results = compare_measures(silver, gold, threshold=Decimal(0))

    # L'ancien contrôle, sur le total, aurait laissé passer ces écarts
    assert sum(silver.values()) == sum(gold.values())
    assert ko_keys(results) == {("EUR", "ca"), ("USD", "ca")}


def test_devise_absente_d_un_cote_detectee():
    """Une devise présente en silver mais absente de gold est KO."""
    silver = {("EUR", "tickets"): 5, ("JPY", "tickets"): 2}
    gold = {("EUR", "tickets"): 5}

    results = compare_measures(silver, gold, threshold=Decimal(0))

    assert ko_keys(results) == {("JPY", "tickets")}
