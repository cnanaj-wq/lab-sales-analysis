# Lab Sales Analysis

Réalisation d'un pipeline de données qui analyse les ventes d'un réseau international de magasins de sport : il contrôle les livraisons des systèmes de caisse (POS) avant publication puis alimente un rapport Power BI pour suivre l'activité selon les axes d'analyse suivants :

- magasin
- pays
- devise
- moyen de paiement

## Sommaire

1. [Besoin métier](#besoin-métier)
2. [Structure du projet](#structure-du-projet)
3. [Données](#données)
4. [Modèle de données](#modèle-de-données)
5. [Documentation](#documentation)
6. [État d'avancement](#état-davancement)

## Besoin métier

La direction souhaite obtenir une vue à 360° de son activité commerciale. Le chiffre d'affaires (CA) qu'elle consulte chaque matin peut être faussé par une livraison en retard ou en double, sans que rien ne le signale.

Le projet répond à ces deux problèmes :

- **Analyser l'activité** : trois tables d'analyse qui répondent aux douze questions que se pose le client.
- **Garantir la qualité des données** : aucune donnée incomplète ou en double n'est publiée et le rapport indique jusqu'à quelle date les données sont complètes.

## Structure du projet

```text
Lab_Sales_Analysis/
├── data/
│   └── raw/        fichier source fourni par le client, jamais modifié
├── docs/           documentation du projet
│   └── modeles/    modèles de données (MCD)
├── scripts/        scripts Python
├── .gitattributes  règles de fins de ligne
├── .gitignore      fichiers exclus du dépôt
└── README.md
```

## Données

Le fichier source `data/raw/pos_sales_data_30k.json` contient 30 000 tickets de caisse enregistrés entre 2023 et 2025 dans 18 pays. Chaque ticket peut contenir plusieurs articles.

## Modèle de données

Le modèle conceptuel de données (MCD, notation Merise) décrit les ventes avec le vocabulaire du métier. Il est construit à partir des constats du [profilage](docs/02_profilage_source.md).

![Modèle conceptuel de données](docs/modeles/mcd.excalidraw.svg)

Points clés :

- le **ticket de vente** est au centre : il est payé par un moyen de paiement, enregistré dans un magasin et peut bénéficier d'un code promo ;
- un **magasin** est une enseigne dans une ville (450 magasins), car l'identifiant `store_id` de la source n'est pas fiable ;
- la quantité et le prix appartiennent à la **ligne de vente** (association CONTENIR), car le prix d'un même produit varie d'une vente à l'autre ;
- la **devise** est rattachée au pays : chaque pays utilise une seule devise, et l'euro est partagé par 5 pays.

## Documentation

| Document | Contenu | Version | Mis à jour le |
| --- | --- | --- | --- |
| [Note de cadrage métier](docs/01_Besoin_metier.md) | Besoin, utilisateurs, périmètre, indicateurs, règles de gestion et critères de succès | 0.2 | 2026-11-16 |
| [Profilage du fichier source](docs/02_profilage_source.md) | Résultats des contrôles S1 à D6, anomalies, limites et règles proposées pour le contrat de données | 0.2 | 2026-11-19 |
| [Modèle conceptuel de données](docs/modeles/mcd.excalidraw.svg) | Entités, associations et cardinalités du domaine des ventes (Merise) | 0.1 | 2026-11-19 |
| [Contrat de données](docs/03_contrat_donnees.md) | Livraison, schéma source → MCD, valeurs de référence, identification, contrôles de qualité CQ01 à CQ28 et traitement des écarts | 0.1 | 2026-11-19 |

## État d'avancement

Le détail de la réalisation brique par brique est suivi dans le [tableau Kanban du projet](https://github.com/users/cnanaj-wq/projects/1).

- [x] Cadrage métier
- [x] Profilage du fichier source
- [x] Modèle conceptuel de données
- [x] Contrat de données
- [ ] Socle PostgreSQL et Airflow
- [ ] Extension Snowflake et dbt
- [ ] Rapport Power BI et supervision
