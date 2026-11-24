"""Rapprochement des mesures entre deux couches, devise par devise.

Utilisé par les portes qualité RC01 et RC02 du DAG. Le module ne lit pas
la base : il compare deux dictionnaires {(devise, mesure): valeur}.
"""

# --- Imports ------------------------------------------------------------------

from decimal import Decimal

# --- Comparaison --------------------------------------------------------------


def compare_measures(upstream, downstream, threshold):
    """Compare deux couches devise par devise et renvoie une ligne par mesure.

    Une devise présente d'un seul côté vaut 0 de l'autre côté : elle est KO
    dès que sa valeur dépasse le seuil.
    """
    results = []
    # Union des clés des deux côtés, triée pour un journal toujours dans le même
    # ordre. La devise peut être vide (None) : elle est triée comme "".
    keys = sorted(upstream.keys() | downstream.keys(), key=lambda k: (k[0] or "", k[1]))
    for key in keys:
        devise, mesure = key
        upstream_value = Decimal(upstream.get(key, 0))
        downstream_value = Decimal(downstream.get(key, 0))
        gap = abs(downstream_value - upstream_value)
        ok = gap <= threshold
        results.append(
            {
                "devise": devise,
                "mesure": mesure,
                "amont": upstream_value,
                "aval": downstream_value,
                "ecart": gap,
                "seuil": threshold,
                "resultat": "OK" if ok else "KO",
                "nb_ecarts": 0 if ok else 1,
            }
        )
    return results


def select_upstream(upstream, measures, all_currencies=False):
    """Garde les mesures amont que la table aval sait calculer.

    all_currencies : la table aval n'a pas de devise. L'amont est alors
    totalisé toutes devises confondues, sous la devise vide (None).
    """
    selected = {}
    for (devise, mesure), value in upstream.items():
        if mesure not in measures:
            continue
        key = (None, mesure) if all_currencies else (devise, mesure)
        selected[key] = selected.get(key, 0) + value
    return selected
