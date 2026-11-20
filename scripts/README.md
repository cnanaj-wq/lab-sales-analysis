# Scripts Python

Ce dossier contient les scripts du pipeline. Les deux premiers travaillent sur le fichier source, sans jamais le modifier.

| Script | Question à laquelle il répond | Résultat |
| --- | --- | --- |
| [`profilage_source.py`](profilage_source.py) | Le fichier source est-il fiable, et quelles règles faut-il en tirer ? | Rapport affiché à l'écran, repris dans le [profilage](../docs/02_profilage_source.md) |
| [`generer_modele_source.py`](generer_modele_source.py) | Quels champs contient le fichier, et avec quel type SQL les stocker ? | Fichier [`config/modele/source.csv`](../config/modele/source.csv) |

Lancement depuis la racine du projet :

```powershell
python scripts/profilage_source.py
```

```powershell
python scripts/generer_modele_source.py
```

## Place des scripts dans le pipeline

```mermaid
flowchart LR
    json[("Fichier source<br/>pos_sales_data_30k.json")]
    prof["profilage_source.py"]
    doc["docs/02_profilage_source.md<br/>anomalies et règles"]
    contrat["docs/03_contrat_donnees.md<br/>contrôles CQ01 à CQ28"]
    gen["generer_modele_source.py"]
    src["config/modele/source.csv<br/>types, vides, longueurs max"]
    tables["config/modele/0X_schema/*.csv<br/>définition des tables"]
    ddl["generer_ddl.py<br/>à venir"]
    base[("Base ventes<br/>PostgreSQL")]

    json --> prof --> doc --> contrat
    json --> gen --> src
    src -. "vérifie les types" .-> tables
    tables --> ddl --> base
```

- `profilage_source.py` sert à **comprendre** le fichier : ses résultats ont servi à rédiger le document de profilage puis le contrat de données.
- `generer_modele_source.py` sert à **construire** : sa fiche des champs sert de référence pour les types des tables décrites dans `config/modele/`.

## `profilage_source.py` : contrôler le fichier source

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

## `generer_modele_source.py` : décrire les champs du fichier source

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
| `decimal`, ou `entier` et `decimal` mélangés | `numeric(12,2)` |
| `horodatage` | `timestamp` |
| `booleen` | `boolean` |
| `liste` ou `objet` | `jsonb` |
| tout autre mélange, ou champ toujours vide | `text`, qui accepte tout |

La longueur max n'est pas utilisée pour fixer la taille des colonnes : les colonnes sont en `text`, comme dans l'énoncé. Elle servira de **contrôle qualité** pour repérer une valeur anormalement longue dans une prochaine livraison.
