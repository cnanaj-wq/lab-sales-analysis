# Scripts Python

Ce dossier contient les scripts du projet. Les deux premiers travaillent sur le fichier source, sans jamais le modifier. Les scripts 04 à 06 forment le pipeline : le DAG Airflow les appelle chaque jour, et ils peuvent aussi être lancés à la main.

| Script | Question à laquelle il répond | Résultat |
| --- | --- | --- |
| [`01_profilage_source.py`](01_profilage_source.py) | Le fichier source est-il fiable, et quelles règles faut-il en tirer ? | Rapport affiché à l'écran, repris dans le [profilage](../docs/02_profilage_source.md) |
| [`02_generer_modele_source.py`](02_generer_modele_source.py) | Quels champs contient le fichier, et avec quel type SQL les stocker ? | Fichier [`config/modele/source.csv`](../config/modele/source.csv) |
| [`03_generer_ddl.py`](03_generer_ddl.py) | Comment créer les tables décrites dans `config/modele/` ? | Fichier `sql/ddl_genere.sql`, exécuté dans la base |
| [`04_charger_bronze.py`](04_charger_bronze.py) | Le fichier livré est-il nouveau et conforme ? | Tickets dans `bronze.pos_sales_raw`, livraison tracée dans `ops.journal_livraisons`, copie dans `data/archive/` |
| [`05_construire_silver.py`](05_construire_silver.py) | Quels tickets de bronze ne sont pas encore dans silver ? | Une ligne par article dans `silver.exploded_products` |
| [`06_construire_gold.py`](06_construire_gold.py) | Que répondent les données aux 12 questions métier ? | Les 3 tables gold, recalculées par les requêtes de `sql/gold/` |
| [`06_construire_gold_star_schema.py`](06_construire_gold_star_schema.py) | Comment servir les données à Power BI ? | Les 4 dimensions et les 2 faits de l'étoile, recalculés par les requêtes de `sql/gold_star_schema/` |
| [`07_creer_role_grafana.py`](07_creer_role_grafana.py) | Comment Grafana lit-il les journaux sans pouvoir rien modifier ? | Rôle `grafana_lecture`, en lecture seule sur le schéma `ops` |
| [`08_generer_mpd.py`](08_generer_mpd.py) | Le schéma du modèle physique correspond-il aux tables créées ? | Fichier [`docs/modeles/mpd.dbml`](../docs/modeles/mpd.dbml), à dessiner dans dbdiagram.io |
| [`09_creer_role_powerbi.py`](09_creer_role_powerbi.py) | Comment Power BI lit-il les données sans pouvoir rien modifier ? | Rôle `powerbi_lecture`, en lecture seule sur les schémas `gold` et `ops` |

Deux modules sont partagés par les scripts :

| Module | Rôle |
| --- | --- |
| [`connexion.py`](connexion.py) | Connexion à la base des ventes : connexion Airflow `postgres_ventes` dans Airflow, fichier de `data_connection/` sur le PC |
| [`messages.py`](messages.py) | Messages horodatés (`log`) et arrêt avec un message clair (`stop`) |

Les scripts 04 à 06 travaillent chacun en une seule transaction : tout est écrit, ou rien ne change.

Lancement depuis la racine du projet, par exemple :

```powershell
python scripts/01_profilage_source.py
```

```powershell
python scripts/08_generer_mpd.py
```

## Place des scripts dans le pipeline

```mermaid
flowchart LR
    json[("Fichier source<br/>pos_sales_data_30k.json")]
    prof["01_profilage_source.py"]
    doc["docs/02_profilage_source.md<br/>anomalies et règles"]
    contrat["docs/03_contrat_donnees.md<br/>contrôles CQ01 à CQ28"]
    gen["02_generer_modele_source.py"]
    src["config/modele/source.csv<br/>types, vides, longueurs max"]
    tables["config/modele/0X_schema/*.csv<br/>définition des tables"]
    ddl["03_generer_ddl.py"]
    mpd["08_generer_mpd.py<br/>docs/modeles/mpd.dbml"]
    base[("Base ventes<br/>PostgreSQL")]
    b["04_charger_bronze.py"]
    s["05_construire_silver.py"]
    g["06_construire_gold.py<br/>3 tables gold"]
    st["06_construire_gold_star_schema.py<br/>modèle en étoile"]

    json --> prof --> doc --> contrat
    json --> gen --> src
    src -. "vérifie les types" .-> tables
    tables --> ddl --> base
    tables --> mpd
    json --> b --> s --> g
    s --> st
    g --> base
    st --> base
```

- `01_profilage_source.py` sert à **comprendre** le fichier : ses résultats ont servi à rédiger le document de profilage puis le contrat de données.
- `02_generer_modele_source.py` sert à **construire** : sa fiche des champs sert de référence pour les types des tables décrites dans `config/modele/`.
- `03_generer_ddl.py` et `08_generer_mpd.py` lisent les mêmes fichiers de `config/modele/` : les tables de la base et le MPD restent identiques.
- Dans Airflow, les portes qualité RC01 (après silver) et RC02 (après gold) s'intercalent entre ces scripts : voir le [README du projet](../README.md#pipeline-airflow).

## `01_profilage_source.py` : contrôler le fichier source

Le script lit le fichier une fois, puis réalise sept familles de contrôles, l'une après l'autre. Chaque contrôle porte un code repris dans le document de profilage.

```mermaid
flowchart TD
    start(["Lancement"]) --> exists{"Fichier source<br/>présent ?"}
    exists -- "non" --> stop(["Arrêt avec message clair<br/>RG06"])
    exists -- "oui" --> load["Lecture du JSON<br/>30 000 tickets"]

    load --> S["S : structure<br/>type, nombre d'éléments, champs, champs imbriqués"]
    S --> V["V : volume et période<br/>lignes article, dates min et max, pays, devises"]
    V --> F["F : validité<br/>format des dates"]
    F --> C["C : complétude<br/>champs manquants, valeurs vides, ticket puis article"]
    C --> U["U : unicité<br/>identifiants en double, doublons cachés, produit répété"]
    U --> K["K : cohérence<br/>montant et quantité = somme des lignes,<br/>une devise par pays, store_id stable,<br/>promo_code, type de magasin, remise et promo"]
    K --> D["D : distribution<br/>retours, paiements, types de magasin,<br/>produits, prix par produit, tickets par jour"]
    D --> report(["Rapport affiché à l'écran<br/>→ docs/02_profilage_source.md"])
```

## `02_generer_modele_source.py` : décrire les champs du fichier source

Le script remplit une fiche par champ, en lisant chaque valeur une seule fois, puis écrit une ligne par fiche dans un CSV.

```mermaid
flowchart TD
    start(["Lancement"]) --> exists{"Fichier source<br/>présent ?"}
    exists -- "non" --> stop(["Arrêt avec message clair"])
    exists -- "oui" --> load["Lecture du JSON<br/>30 000 tickets"]

    load --> ticket["Pour chaque ticket"]
    ticket --> tfield["Pour chaque champ du ticket<br/>sauf products"]
    tfield --> update["update_stats<br/>met à jour la fiche du champ"]
    ticket --> article["Pour chaque article de products"]
    article --> afield["Pour chaque champ de l'article"]
    afield --> update

    update --> detect["detect_type<br/>vide, booleen, entier, decimal,<br/>liste, objet, horodatage, texte"]
    detect --> fiche["Fiche du champ<br/>types vus, nb valeurs, nb vides,<br/>longueur max, exemple"]

    fiche --> sql["propose_sql_type<br/>type détecté → type PostgreSQL"]
    sql --> write["Écriture d'une ligne par champ<br/>séparateur ;"]
    write --> out(["config/modele/source.csv<br/>19 champs : 14 ticket + 5 article"])
```

Règles appliquées par `propose_sql_type` :

| Types détectés | Type PostgreSQL proposé |
| --- | --- |
| `texte` | `text` |
| `entier` | `integer` |
| `decimal`, ou `entier` et `decimal` mélangés | `float`, comme dans l'énoncé |
| `horodatage` | `timestamp` |
| `booleen` | `boolean` |
| `liste` ou `objet` | `jsonb` |
| tout autre mélange, ou champ toujours vide | `text`, qui accepte tout |

La longueur max n'est pas utilisée pour fixer la taille des colonnes : les colonnes sont en `text`, comme dans l'énoncé. Elle servira de **contrôle qualité** pour repérer une valeur anormalement longue dans une prochaine livraison.
