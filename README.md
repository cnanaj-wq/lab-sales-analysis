# Lab Sales Analysis

Réalisation d'un pipeline de données qui analyse les ventes d'un réseau international de magasins de sport : il contrôle les livraisons des systèmes de caisse (POS) avant publication puis alimente un rapport Power BI pour suivre l'activité selon les axes d'analyse suivants :

- magasin
- pays
- devise
- moyen de paiement

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
├── scripts/        scripts Python
├── .gitattributes  règles de fins de ligne
├── .gitignore      fichiers exclus du dépôt
└── README.md
```

## Données

Le fichier source `data/raw/pos_sales_data_30k.json` contient 30 000 tickets de caisse enregistrés entre 2023 et 2025 dans 18 pays. Chaque ticket peut contenir plusieurs articles.

## Documentation

| Document | Contenu | Version | Mis à jour le |
| --- | --- | --- | --- |
| [Note de cadrage métier](docs/01_Besoin_metier.md) | Besoin, utilisateurs, périmètre, indicateurs, règles de gestion et critères de succès | 0.2 | 2026-11-16 |
| [Profilage du fichier source](docs/02_profilage_source.md) | Résultats des contrôles S1 à D6, anomalies, limites et règles proposées pour le contrat de données | 0.1 | 2026-11-18 |

## État d'avancement

- [x] Cadrage métier
- [x] Profilage du fichier source
- [ ] Contrat de données
- [ ] Socle PostgreSQL et Airflow
- [ ] Extension Snowflake et dbt
- [ ] Rapport Power BI et supervision
