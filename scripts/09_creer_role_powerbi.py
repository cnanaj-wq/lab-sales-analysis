"""Crée le rôle PostgreSQL powerbi_lecture (Lab Sales Analysis).

Power BI lit le modèle en étoile (schéma gold) et le journal des contrôles
(schéma ops) avec ce rôle, en lecture seule : il ne voit ni bronze ni silver,
et ne peut rien modifier.
Le mot de passe est lu dans data_connection/lab_sales_powerbi.env, hors du dépôt.
Le script peut être relancé : il met seulement le mot de passe à jour.

Lancement : python scripts/09_creer_role_powerbi.py
"""

# --- Imports ------------------------------------------------------------------

from connexion import ENV_FILE, connect, read_env
from messages import log, stop

# --- Constantes ---------------------------------------------------------------

POWERBI_ENV_FILE = ENV_FILE.parent / "lab_sales_powerbi.env"
ROLE = "powerbi_lecture"
SCHEMAS = ["gold", "ops"]

# --- Création du rôle ---------------------------------------------------------


def main():
    """Crée ou met à jour le rôle de lecture de Power BI."""
    if not POWERBI_ENV_FILE.exists():
        stop(f"fichier de secrets introuvable ({POWERBI_ENV_FILE.name}).")
    password = read_env(POWERBI_ENV_FILE).get("POWERBI_LECTURE_PASSWORD")
    if not password:
        stop("POWERBI_LECTURE_PASSWORD absent du fichier de secrets.")

    connection = connect()
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute("select 1 from pg_roles where rolname = %s", (ROLE,))
            action = "alter" if cursor.fetchone() else "create"
            cursor.execute(f"{action} role {ROLE} login password %s", (password,))

            # Lecture seule sur gold et ops, y compris les tables créées plus tard
            for schema in SCHEMAS:
                cursor.execute(f"grant usage on schema {schema} to {ROLE}")
                cursor.execute(
                    f"grant select on all tables in schema {schema} to {ROLE}"
                )
                cursor.execute(
                    f"alter default privileges in schema {schema} grant select on tables to {ROLE}"
                )
    finally:
        connection.close()

    log(f"rôle {ROLE} prêt : lecture seule sur les schémas {', '.join(SCHEMAS)}.")


# --- Lancement depuis le terminal ---------------------------------------------

if __name__ == "__main__":
    main()
