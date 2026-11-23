"""Vérifie que les tests travaillent sur une base de recette propre."""


def test_base_de_recette_vide(db):
    """La fixture db se connecte à ventes_recette et part de tables vides."""
    with db.cursor() as cursor:
        cursor.execute("select current_database()")
        assert cursor.fetchone()[0] == "ventes_recette"

        cursor.execute("select count(*) from bronze.pos_sales_raw")
        assert cursor.fetchone()[0] == 0
