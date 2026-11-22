# Analyse des ventes d'un réseau international de magasins de sport

**Procédure de rattrapage (backfill) du pipeline des ventes**

| Champ      | Valeur                                                        |
|------------|---------------------------------------------------------------|
| Référence  | LSA-DOC-04                                                    |
| Version    | 0.1                                                           |
| Statut     | Brouillon                                                     |
| Auteur     | Cédric NANA                                                   |
| Date       | 2026-11-22                                                    |



## Historique des révisions


| Version | Date       | Auteur      | Modification                   |
|---------|------------|-------------|--------------------------------|
| 0.1     | 2026-11-22 | Cédric NANA | Création : sections 1 à 7      |


---

## 1. Objet

Cette procédure explique comment rattraper des journées que le DAG
`lab_sales_analysis_pipeline` n'a pas traitées : panne de la machine, Airflow
arrêté, DAG en pause, ou journée en échec (porte qualité KO).

Une journée est **traitée** quand un run de cette journée est passé jusqu'à la
porte RC02 avec ses 3 mesures OK (tickets, CA, quantité) : la donnée est
arrivée dans gold et elle a été vérifiée.

## 2. Ce que fait un rattrapage dans ce pipeline

Un rattrapage crée **un run par journée** de la période demandée. Chaque run :

1. charge dans bronze les fichiers arrivés et pas encore chargés (chargement
   incrémental par fichier) ;
2. reconstruit silver, puis les 3 tables gold et le modèle en étoile ;
3. contrôle **sa journée** avec les portes RC01 (bronze = silver) et RC02
   (silver = gold), et l'écrit dans `ops.journal_controles` ;
4. envoie un mail à l'astreinte : bilan si tout est OK, alerte sinon.

À savoir :

- Le **premier** run qui suit la panne, planifié ou rattrapé, charge les
  fichiers arrivés pendant la panne. Les runs rattrapés servent surtout à
  **contrôler et tracer chaque journée**.
- Un run planifié ou lancé à la main contrôle toute la table ; un run de
  rattrapage contrôle seulement sa journée (fonction `controlled_day` du DAG).
- Les journées sont celles de Paris : Airflow stocke minuit à Paris en UTC
  (22 h ou 23 h la veille), le DAG remet la date dans le bon fuseau.

## 3. Règles à respecter

| Règle | Pourquoi |
|-------|----------|
| Toujours `--max-active-runs 1` | Un rattrapage ne reprend pas la limite du DAG. Des runs en parallèle reconstruisent gold en même temps : verrou mortel (deadlock) observé lors du test, et risque de faux KO si une porte lit gold pendant qu'un autre run le vide. |
| Toujours un `--dry-run` d'abord | Il liste les runs prévus sans rien lancer. |
| Laisser le paramètre `jour` vide | `jour` passe avant tout : renseigné, tous les runs contrôleraient la même journée. |
| Prévenir l'astreinte | Un mail par run : 30 jours rattrapés = 30 mails de bilan. |

## 4. Étapes

### 4.1 Repérer les journées à rattraper

Dans pgAdmin, base des ventes. Remplacer les deux dates par la période à
vérifier.

**Journées non traitées** (aucun run avec RC02 entièrement OK) :

```sql
select d::date as journee
from generate_series(date '2024-07-01', date '2024-07-31', interval '1 day') d
where not exists (
    select 1
    from ops.journal_controles c
    where c.date_logique = d::date
      and c.code_controle = 'RC02'
    group by c.run_id
    having bool_and(c.resultat = 'OK') and count(distinct c.mesure) = 3
)
order by journee;
```

**Journées en KO jamais corrigées** (avec les contrôles en cause) :

```sql
select date_logique as journee, run_id,
       string_agg(distinct code_controle || ' ' || mesure, ', ') as controles_ko
from ops.journal_controles
where resultat = 'KO'
  and date_logique not in (
      select date_logique
      from ops.journal_controles
      where code_controle = 'RC02'
      group by run_id, date_logique
      having bool_and(resultat = 'OK') and count(distinct mesure) = 3
  )
group by date_logique, run_id
order by journee;
```

Le panneau **« Historique des portes qualité par run »** de Grafana
(http://localhost:3002) donne la même information en couleur.

Pour une journée en KO, **corriger la cause d'abord** (fichier source, script,
données), sinon le rattrapage échouera de nouveau.

### 4.2 Simuler le rattrapage

```powershell
docker exec lab-sales-analysis-airflow-scheduler-1 airflow backfill create --dag-id lab_sales_analysis_pipeline --from-date 2024-07-01 --to-date 2024-07-31 --max-active-runs 1 --reprocess-behavior none --dry-run
```

- `--from-date` et `--to-date` : première et dernière journée, incluses.
- `--reprocess-behavior` :
  - `none` : seulement les journées sans run (défaut) ;
  - `failed` : aussi les journées dont le run a échoué ;
  - `completed` : toutes les journées, même celles déjà réussies.

Comparer la liste affichée avec le résultat de l'étape 4.1.

### 4.3 Lancer le rattrapage

Même commande, **sans** `--dry-run`.

Autre possibilité : dans Airflow (http://localhost:8090), page du DAG, onglet
**Rattrapages**, avec les mêmes choix (dates, comportement de retraitement,
nombre de runs actifs à 1).

### 4.4 Suivre l'avancement

- Airflow, onglet **Rattrapages** : le rattrapage et ses runs, un à la fois.
- Grafana : le panneau « Dernier run » passe à EN COURS puis OK, run après run.
- Mailpit (http://localhost:8027) : un mail par run.

### 4.5 Vérifier le résultat

1. Relancer la première requête de l'étape 4.1 : elle doit revenir **vide**.
2. Contrôler le détail des journées rattrapées :

```sql
select date_logique as journee, code_controle, mesure,
       coalesce(valeur_bronze, valeur_silver) as amont,
       coalesce(valeur_gold, valeur_silver) as aval,
       ecart, resultat
from ops.journal_controles
where run_id like 'backfill%'
  and date_logique between '2024-07-01' and '2024-07-31'
order by journee, code_controle, mesure;
```

## 5. En cas d'échec d'un run rattrapé

1. L'astreinte reçoit le mail « ÉCHEC » ou « QUALITÉ KO » avec l'erreur, les
   contrôles du run et le lien vers la tâche dans Airflow.
2. Lire le message dans le mail ou dans `ops.journal_taches` (colonne
   `message`), corriger la cause.
3. Relancer seulement les journées en échec :

```powershell
docker exec lab-sales-analysis-airflow-scheduler-1 airflow backfill create --dag-id lab_sales_analysis_pipeline --from-date 2024-07-01 --to-date 2024-07-31 --max-active-runs 1 --reprocess-behavior failed
```

Pour une seule journée, on peut aussi ouvrir son run dans Airflow et
**effacer** la tâche en échec (avec ses tâches en aval).

## 6. Exemple réel : rattrapage du 15 au 17 juillet 2024

Commande lancée (sans `--max-active-runs 1` à ce moment-là) :

```powershell
docker exec lab-sales-analysis-airflow-scheduler-1 airflow backfill create --dag-id lab_sales_analysis_pipeline --from-date 2024-07-15 --to-date 2024-07-17
```

Résultat dans `ops.journal_controles` :

| Journée    | Tickets | CA        | Quantité | RC01 | RC02 |
|------------|---------|-----------|----------|------|------|
| 2024-07-15 | 32      | 23 155,00 | 191      | OK   | OK   |
| 2024-07-16 | 32      | 20 156,25 | 168      | OK   | OK   |
| 2024-07-17 | 28      | 14 630,50 | 161      | OK   | OK   |

Les 3 runs ont démarré en même temps. Deux reconstructions de l'étoile se sont
bloquées mutuellement : PostgreSQL a annulé l'une d'elles (deadlock), le script
a tout annulé proprement et le réessai a réussi. C'est l'origine de la règle
`--max-active-runs 1`.
