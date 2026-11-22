"""Messages horodatés des scripts du pipeline (Lab Sales Analysis).

À importer depuis un autre script :
    from messages import log, stop
"""

# --- Imports ------------------------------------------------------------------

import sys
from datetime import datetime

# --- Constantes ---------------------------------------------------------------

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


# --- Messages horodatés -------------------------------------------------------


def log(message):
    """Affiche un message d'information précédé de l'heure."""
    now = datetime.now().strftime(TIMESTAMP_FORMAT)
    print(f"{now} {message}")


def stop(message):
    """Arrête le script en affichant l'heure et le motif de l'arrêt."""
    now = datetime.now().strftime(TIMESTAMP_FORMAT)
    sys.exit(f"{now} Arrêt : {message}")
