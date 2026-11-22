"""Crée le rôle PostgreSQL grafana_lecture (Lab Sales Analysis).

Grafana lit les journaux du pipeline (schéma ops) avec ce rôle, en lecture
seule : il ne voit ni bronze, ni silver, ni gold, et ne peut rien modifier.
Le mot de passe est lu dans data_connection/lab_sales_grafana.env, hors du dépôt.
Le script peut être relancé : il met seulement le mot de passe à jour.

Lancement : python scripts/07_creer_role_grafana.py
"""

# --- Imports ------------------------------------------------------------------

from connexion import ENV_FILE, connect, read_env
from messages import log, stop

# --- Constantes ---------------------------------------------------------------

GRAFANA_ENV_FILE = ENV_FILE.parent / "lab_sales_grafana.env"
ROLE = "grafana_lecture"

# --- Création du rôle ---------------------------------------------------------


def main():
    """Crée ou met à jour le rôle de lecture de Grafana."""
    if not GRAFANA_ENV_FILE.exists():
        stop(f"fichier de secrets introuvable ({GRAFANA_ENV_FILE.name}).")
    password = read_env(GRAFANA_ENV_FILE).get("GRAFANA_LECTURE_PASSWORD")
    if not password:
        stop("GRAFANA_LECTURE_PASSWORD absent du fichier de secrets.")

    connection = connect()
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute("select 1 from pg_roles where rolname = %s", (ROLE,))
            action = "alter" if cursor.fetchone() else "create"
            cursor.execute(f"{action} role {ROLE} login password %s", (password,))

            # Lecture seule sur les journaux, y compris les tables créées plus tard
            cursor.execute(f"grant usage on schema ops to {ROLE}")
            cursor.execute(f"grant select on all tables in schema ops to {ROLE}")
            cursor.execute(
                f"alter default privileges in schema ops grant select on tables to {ROLE}"
            )
    finally:
        connection.close()

    log(f"rôle {ROLE} prêt : lecture seule sur le schéma ops.")


# --- Lancement depuis le terminal ---------------------------------------------

if __name__ == "__main__":
    main()
