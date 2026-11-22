# Analyse des ventes d'un réseau international de magasins de sport

**Cadrage métier**

| Champ      | Valeur                          |
|------------|---------------------------------|
| Référence  | LSA-DOC-01                      |
| Version    | 0.2                             |
| Statut     | Brouillon                       |
| Auteur     | Cédric NANA                     |
| Date       | 2026-11-16                      |
| Validateur | Responsable métier (à désigner) |


## Historique des révisions


| Version | Date       | Auteur      | Modification |
|---------|------------|-------------|--------------|
| 0.1     | 2026-11-16 | Cédric NANA | Création     |
| 0.2     | 2026-11-16 | Cédric NANA | Rédaction complète des sections 1 à 8 et de l'annexe A |


---

## 1. Contexte et problème

L'entreprise internationale spécialisée dans la vente d'articles de sport possède des magasins physiques dans 18 pays d'Europe, d'Amérique du Nord et d'Asie.

Chaque jour, des milliers de transactions sont enregistrées via les systèmes de caisse (POS). Le jeu de données fourni pour le projet est un fichier JSON de 30 000 transactions enregistrées entre 2023 et 2025, avec parfois plusieurs articles par ticket.

Aujourd'hui, la direction souhaite disposer d'une vue à 360° afin de mieux piloter son activité commerciale. Elle ne peut pas identifier quels magasins réalisent les meilleures ventes, comment l'activité se répartit par pays et par devise, ni quels moyens de paiement sont les plus utilisés ou présentent le taux de retour le plus élevé.

Chaque matin, la direction commerciale utilise le chiffre d'affaires (CA) de la veille pour identifier les magasins dont les ventes décrochent et décider lesquels contacter. Un magasin peut sembler en baisse parce que son fichier de ventes est arrivé en retard. À l'inverse, une double livraison peut gonfler le CA et masquer une vraie baisse.

Dans les deux cas, le reporting Power BI se rafraîchit et affiche un CA incomplet ou erroné, sans avertissement visible. La direction commerciale risque alors de demander des explications à un magasin dont les ventes se maintiennent et de passer à côté d'un magasin qui a réellement besoin d'un suivi. Lorsque ces écarts se répètent, les équipes métier perdent confiance dans les chiffres fournis par l'équipe Data et recalculent le CA dans Excel. Ces vérifications retardent les décisions et chaque service finit par communiquer un chiffre différent.


## 2. Utilisateurs et décisions

| Utilisateur            | Fréquence                          | Ce qu'il consulte                                                                                                        | Décision qu'il prend                                                                                      |
|------------------------|------------------------------------|--------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| Direction générale     | Chaque mois                        | Le classement des magasins, la répartition des ventes par pays et par devise, et l'analyse par moyen de paiement (taux de retour, remise moyenne). | Orienter les efforts commerciaux vers les pays ou magasins prioritaires, et revoir les conditions d'un moyen de paiement dont le taux de retour est élevé. |
| Direction commerciale  | Chaque matin                       | Le CA de la veille par magasin, son écart par rapport à une période de référence et le statut de complétude des données. | Prioriser les magasins à contacter lorsqu'une baisse est confirmée sur des données complètes et validées. |
| Responsable de magasin | Après un contact de la direction   | Les ventes par produit et le nombre de transactions marquées comme retournées dans son magasin.                          | Comprendre l'évolution des ventes et décider si une action locale est nécessaire.                         |
| Équipe Data            | Sur alerte ou demande de la direction | Le statut des livraisons : fichiers manquants, en retard ou en double.                                                | Enquêter sur l'anomalie, puis relancer ou corriger la livraison concernée.                                |

**Règle de décision.** Si les données d'un magasin sont incomplètes à l'heure du point commercial, la direction demande à l'équipe Data de vérifier la livraison avant de tirer une conclusion sur les ventes. Power BI signale les données manquantes, pour éviter qu'un retard de livraison soit interprété comme une baisse des ventes et pour éviter les recalculs de contrôle dans Excel.

**Période de référence (proposition à valider).** Le CA de la veille est comparé à celui du même jour de la semaine précédente. La comparaison est simple à expliquer et évite par exemple de comparer directement un dimanche à un samedi. Le seuil à partir duquel une baisse justifie un appel reste à définir (voir section 7).

## 3. Périmètre

**Inclus**

- Ventes des magasins physiques, issues des tickets de caisse fournis dans le fichier JSON.
- Performance par magasin : montant cumulé des ventes et quantités vendues.
- Ventes quotidiennes par pays et par devise : montant, nombre de transactions et valeur moyenne d'une transaction.
- Analyse par moyen de paiement : nombre de transactions, montant des ventes, remise moyenne, taux de retour et nombre moyen d'articles par transaction.
- Suivi dans Power BI du montant quotidien des ventes par magasin, en devise locale, et des quantités vendues par produit.
- Nombre de transactions marquées comme retournées, calculé au niveau du ticket à partir du champ `return_status`.
- Contrôle des livraisons manquantes, tardives ou en double avant publication avec distinction entre données manquantes et journée sans ventes confirmée.

**Exclu**

- Ventes en ligne, stocks et marges.
- Montant des remboursements : la source fournit le statut du retour au niveau du ticket, le montant effectivement remboursé est indisponible.
- Calcul du CA net HT : la remise est suivie en moyenne, sans être déduite du montant des ventes.
- Conversion des devises et consolidation des ventes dans une devise commune.
- Analyses clients (fidélisation, rétention, inactivité) : la source ne contient pas d'identifiant client.


## 4. KPI retenus

### Indicateurs de vente

| KPI | Définition en une phrase | Grain | Source |
| --- | --- | --- | --- |
| **Montant des ventes** | Somme des montants enregistrés en caisse, en comptant chaque ticket une seule fois et en conservant sa devise. | Magasin (cumul) · Jour × pays × devise · Moyen de paiement · Jour × magasin × devise | JSON POS · `transaction_id`, `total_amount`, `currency`, `store_id`, `store_country`, `payment_method`, `purchase_timestamp` |
| **Quantités vendues** | Somme des quantités enregistrées sur les lignes de ticket pour chaque produit. | Magasin (cumul) · Jour × magasin × produit | JSON POS · `products[].product_id`, `products[].quantity`, `store_id`, `purchase_timestamp` |
| **Nombre de transactions** | Nombre de tickets distincts. | Jour × pays × devise · Moyen de paiement | JSON POS · `transaction_id`, `store_country`, `currency`, `payment_method`, `purchase_timestamp` |
| **Valeur moyenne d'une transaction** | Montant des ventes divisé par le nombre de transactions de la même journée, du même pays et de la même devise. | Jour × pays × devise | Calculé à partir du montant des ventes et du nombre de transactions |
| **Remise moyenne** | Moyenne par ticket de la remise appliquée, tous tickets compris, y compris ceux sans remise. | Moyen de paiement | JSON POS · `transaction_id`, `discount_applied`, `payment_method` |
| **Nombre de transactions retournées** | Nombre de tickets distincts marqués `Returned`, rattachés à leur date d'achat. | Jour d'achat × magasin | JSON POS · `transaction_id`, `return_status`, `store_id`, `purchase_timestamp` |
| **Taux de retour** | Nombre de transactions retournées divisé par le nombre de transactions, exprimé en pourcentage. | Moyen de paiement | JSON POS · `transaction_id`, `return_status`, `payment_method` |
| **Nombre moyen d'articles par transaction** | Moyenne par ticket du nombre total d'articles achetés. | Moyen de paiement | JSON POS · `transaction_id`, `total_quantity_sold`, `payment_method` |
| **Nombre de magasins** | Nombre de magasins distincts ayant enregistré au moins une vente. | Pays | JSON POS · `store_id`, `store_country` (définition du magasin à valider, voir section 7) |

### Indicateur de qualité des données

| KPI | Définition en une phrase | Grain | Source |
| --- | --- | --- | --- |
| **Statut de complétude des données** | La journée est complète lorsque toutes les livraisons attendues sont reçues et validées, y compris une déclaration explicite de zéro vente le cas échéant. | Jour × livraison attendue (grain à fixer dans le contrat de données) | Calendrier des livraisons attendues et journal de réception et de validation, à mettre en place. |

**Lecture des grains.** Un même indicateur peut être restitué à plusieurs grains, séparés par « · ». Les trois premiers grains du montant des ventes correspondent aux trois tables d'analyse demandées ; le quatrième sert au suivi quotidien de la direction commerciale.

**Moyennes.** Toutes les moyennes se calculent par ticket, jamais par ligne de produit : un ticket de trois produits pèse autant qu'un ticket d'un seul produit.

**Limite connue.** Au grain du moyen de paiement, le montant des ventes et la remise moyenne mélangent plusieurs devises. Ces deux valeurs sont fournies comme demandé, mais ne permettent pas de comparer les moyens de paiement entre eux (voir section 7).

## 5. Règles de gestion

Les exemples s'appuient sur le ticket `TXN000001` : 3 produits (quantités 4, 2 et 2), `total_amount` 845,50 CAD, remise 15,52, statut `Returned`, acheté le 2024-07-16 à 15:39:37 à Montréal.

| Règle | Application | Exemple |
| --- | --- | --- |
| **RG01 — Journée de vente** | Les ventes et les quantités sont rattachées au magasin et à la date d'achat issue de `purchase_timestamp`. Le fuseau horaire de référence reste à confirmer (voir section 7). | Le ticket est rattaché à la journée du 2024-07-16. |
| **RG02 — Montant des ventes** | Le montant `total_amount` est compté une seule fois par ticket, quel que soit le nombre de lignes produit. Les totaux et les comparaisons sont calculés par devise. | Le ticket compte pour 845,50 CAD, et non 2 536,50 CAD (3 lignes × 845,50). |
| **RG03 — Quantités vendues** | Les quantités par produit sont calculées à partir de `products[].quantity`. Le total du ticket, `total_quantity_sold`, sert au rapprochement avec la somme des quantités de ses lignes. | 4 + 2 + 2 = 8, égal à `total_quantity_sold`. |
| **RG04 — Transactions retournées** | Un ticket dont le statut `return_status` vaut `Returned` est compté une seule fois, à sa date d'achat. Ce statut alimente le compteur de retours. Le montant de vente enregistré est conservé. | Un retour compté au 2024-07-16 ; les 845,50 CAD restent dans le montant des ventes. |
| **RG05 — Livraison en double** | La relivraison d'un lot identique, même sous un autre nom, laisse les KPI inchangés. Si deux versions d'un même ticket diffèrent, l'écart doit être résolu avant publication. | Le ticket reçu deux fois compte toujours pour 845,50 CAD et 8 articles. |
| **RG06 — Complétude et publication** | Une journée est complète lorsque toutes les livraisons attendues sont reçues et validées. À l'échéance, une livraison absente déclenche une alerte à l'équipe Data et le statut « Données manquantes » dans Power BI. Une journée sans ventes confirmée est affichée à zéro. | Sans livraison reçue pour le 2024-07-16, la journée est affichée « Données manquantes », et non à zéro. |
| **RG07 — Comparaison des ventes** | Une baisse est exploitable lorsque les données des deux périodes sont complètes et validées pour le même magasin et la même devise. La période de référence et le seuil d'alerte restent à valider (voir section 7). | Le 2024-07-16 (mardi) est comparé au 2024-07-09, si les deux journées sont complètes. |
| **RG08 — Remise** | La remise `discount_applied` n'est pas déduite du montant des ventes. Elle est suivie séparément, en moyenne par ticket. | Le montant reste 845,50 CAD, et non 829,98 CAD ; la remise de 15,52 entre dans la remise moyenne. |
| **RG09 — Moyennes et taux** | Les moyennes et les taux se calculent par ticket, jamais par ligne de produit. Sur une période, une moyenne se recalcule à partir des totaux, et non comme moyenne de moyennes quotidiennes. | Le ticket pèse pour 1 dans le taux de retour et la remise moyenne, et non pour 3. |
| **RG10 — Magasin** | L'identifiant `store_id` seul ne désigne pas un magasin unique : un même identifiant apparaît dans plusieurs pays. La définition d'un magasin reste à valider (voir section 7). | — |

**À valider dans le contrat de données.** La clé unique du ticket, le calendrier des livraisons attendues et le signal qui confirme une journée sans ventes.

## 6. Actualisation des données

Le traitement fonctionne en mode batch : les données sont traitées une fois par jour, et non en temps réel. Les heures sont exprimées en heure de Paris.

| Élément | Valeur | Origine |
| --- | --- | --- |
| Fréquence du traitement | Une exécution par jour, relançable à la demande. | Demande du client |
| Données visibles | Ventes jusqu'à la veille incluse. | Conséquence du traitement quotidien |
| Arrivée du fichier de ventes quotidien | Au plus tard à 06:00. | Hypothèse à valider (voir section 7) |
| Alerte de retard | À 06:15, si le fichier attendu n'est pas arrivé. | Hypothèse à valider (voir section 7) |
| Heure limite de publication | Ventes de la veille visibles dans Power BI à 07:00. | Hypothèse à valider (voir section 7) |

**Ce que voit l'utilisateur.** Le rapport affiche la date de la dernière journée complète et l'heure de la dernière publication. Une heure de rafraîchissement récente ne suffit pas : elle ne prouve pas que les données couvrent bien la veille.

**En cas de dépassement.** Si les données de la veille ne sont pas publiées à 07:00, le rapport conserve la dernière version validée et affiche le statut « Données manquantes » pour la journée concernée (règle RG06). Aucun chiffre incomplet n'est publié.

**Reprise.** Lorsque le fichier manquant ou corrigé arrive, le traitement est relancé à la demande, sans attendre l'exécution du lendemain.

**Limite.** La notion de « veille » dépend du fuseau horaire de rattachement des ventes, qui reste à confirmer (règle RG01) : à 07:00 à Paris, la journée précédente vient à peine de se terminer pour les magasins d'Amérique du Nord.

## 7. Solutions techniques, hypothèses et points ouverts

Une solution technique est un choix d'outillage déjà arrêté. Une hypothèse est un choix retenu pour avancer, à confirmer. Un point ouvert est une question sans réponse à ce jour. Chacun est attribué au rôle qui doit trancher.

### Solutions techniques

| N°  | Solution retenue | Origine |
| --- | --- | --- |
| D01 | Le socle demandé par le client (PostgreSQL, Airflow, Docker, Python) est réalisé en premier. Il est étendu à Snowflake, dbt, Power BI et Grafana brique par brique en vérifiant à chaque étape que les deux chaînes donnent les mêmes chiffres. | Extension acceptée le 2026-11-16 par l'équipe Projet |

### Hypothèses retenues, à valider

| N°  | Hypothèse | Qui valide | Impact si elle change |
| --- | --- | --- | --- |
| H01 | Le fichier source est un échantillon : 30 000 tickets sur 3 ans, soit environ 27 par jour, alors que le client annonce des milliers de transactions par jour. Le suivi quotidien par magasin est conçu pour le volume de production et sera démontré au grain jour × pays. | Responsable métier | Grain de démonstration du suivi quotidien, tests de performance. |
| H02 | Le fichier source est un historique complet et figé : l'absence de ticket y signifie l'absence de vente. Pour démontrer l'exploitation quotidienne, les livraisons sont simulées en découpant le fichier par date d'achat, et les retards et doublons sont provoqués volontairement. | Équipe Data | Calendrier des livraisons, scénarios de retard et de double livraison. |
| H03 | `transaction_id` identifie un ticket de façon unique. C'est le cas dans le fichier source (30 000 valeurs distinctes). | Fournisseur des données de caisse | RG02, RG05 : détection des doublons. |
| H04 | Un ticket est rattaché à la date de `purchase_timestamp` telle qu'enregistrée, supposée être l'heure locale du magasin. La source n'indique aucun fuseau horaire. | Fournisseur des données de caisse | RG01, définition de « la veille », Q6. |
| H05 | La période de référence d'une comparaison est le même jour de la semaine précédente. | Direction commerciale | RG07, lecture des baisses. |
| H06 | Le fichier de ventes quotidien arrive au plus tard à 06:00, l'alerte de retard part à 06:15 et les ventes de la veille sont visibles à 07:00, heure de Paris. | Direction commerciale et équipe Data | Section 6, planification du traitement. |
| H07 | La remise moyenne se calcule sur tous les tickets, y compris ceux sans remise. | Responsable métier | Valeur de la remise moyenne (RG08). |
| H08 | La vue à 360° de l'activité est consultée chaque mois par la direction générale. | Responsable métier | Section 2, contenu et rythme du rapport. |

### Points ouverts

| N°  | Question | Constat | Qui décide | Impact |
| --- | --- | --- | --- | --- |
| P01 | Qu'est-ce qui identifie un magasin ? | Sur 8 681 `store_id`, 7 493 apparaissent dans plusieurs pays. La combinaison nom × ville × type donne 900 magasins. | Responsable métier | RG10, table `store_sales_summary`, Q1 et Q3. |
| P02 | Comment comparer des montants de devises différentes ? | La source ne contient aucun taux de change. Les classements de Q1, Q2 et Q9 additionnent ou comparent plusieurs devises. | Responsable métier | Q1, Q2, Q9, analyse par moyen de paiement. En attendant, les valeurs sont fournies telles que demandées, avec la réserve signalée. |
| P03 | De combien le montant des ventes de la veille d'un magasin doit-il baisser, par rapport au même jour de la semaine précédente, pour justifier un appel ? | Aucun seuil n'est défini. | Direction commerciale | RG07, alertes du suivi quotidien. |

## 8. Critères de succès

Le projet est réussi lorsque chaque critère ci-dessous est vérifié, preuve à l'appui. Les preuves sont consignées dans le PV de recette.

### Conformité à la demande du client

| N°   | Critère | Preuve attendue | Référence |
| ---- | --- | --- | --- |
| CS01 | La table intermédiaire et les trois tables d'analyse existent avec les colonnes demandées par le client. | Comparaison de la structure des tables avec la demande : aucun écart. | Section 3 |
| CS02 | Les douze questions métier ont chacune une réponse chiffrée, accompagnée de sa réserve lorsqu'il y en a une. | Douze résultats de requête, numérotés Q1 à Q12. | Annexe A |
| CS03 | Le traitement s'exécute automatiquement chaque jour et peut être relancé à la demande. | Historique d'exécution montrant une exécution planifiée et une exécution manuelle réussies. | Section 6 |

### Exactitude des chiffres

| N°   | Critère | Preuve attendue | Référence |
| ---- | --- | --- | --- |
| CS04 | Les chiffres publiés se rapprochent du fichier source : 30 000 tickets, et un montant des ventes par devise et une quantité totale identiques à ceux du fichier. | Tableau de rapprochement : écart nul sur le nombre de tickets, le montant par devise et les quantités. | RG02, RG03 |
| CS05 | Les dix règles de gestion sont vérifiées par un contrôle automatique. | Un contrôle par règle, tous réussis, dont l'exemple du ticket `TXN000001`. | Section 5 |
| CS06 | Les deux chaînes de traitement donnent des chiffres identiques pour tous les indicateurs. | Comparaison des trois tables d'analyse entre les deux chaînes : écart nul. | D01 |

### Fiabilité de la publication

| N°   | Critère | Preuve attendue | Référence |
| ---- | --- | --- | --- |
| CS07 | Une livraison reçue en double ne modifie aucun indicateur. | Valeurs des indicateurs avant et après une double livraison provoquée : identiques. | RG05, H02 |
| CS08 | Une livraison absente à l'échéance déclenche une alerte et le statut « Données manquantes ». Aucune journée incomplète n'est affichée à zéro. | Alerte reçue et capture du rapport lors d'un retard provoqué. | RG06, H02 |
| CS09 | Après l'arrivée du fichier manquant, une relance à la demande rétablit les chiffres, sans doublon. | Rapprochement réussi après la reprise. | Section 6 |
| CS10 | Le rapport affiche la date de la dernière journée complète et l'heure de la dernière publication. | Capture du rapport Power BI. | Section 6 |
| CS11 | Les ventes de la veille sont visibles à 07:00, heure de Paris, sur les journées simulées sans incident. | Heures de publication relevées sur les journées simulées. | H06 |

---

## Annexe A. Questions métier

Les douze questions ci-dessous sont posées par le client. Chacune est reliée à la table d'analyse qui y répond et à l'indicateur de la section 4 qu'elle utilise.

### Table `store_sales_summary`

| N°  | Question | KPI utilisé | Remarque |
| --- | --- | --- | --- |
| Q1  | Quels sont les 5 magasins ayant généré le plus de chiffre d'affaires ? | Montant des ventes | Dépend de la définition d'un magasin. Les magasins comparés n'ont pas tous la même devise (voir section 7). |
| Q2  | Quelle est la ville avec le chiffre d'affaires cumulé le plus élevé ? | Montant des ventes | Les villes comparées n'ont pas toutes la même devise (voir section 7). |
| Q3  | Combien de magasins se trouvent dans chaque pays ? | Nombre de magasins | Dépend de la définition d'un magasin (voir section 7). |
| Q4  | Quelle est la quantité totale de produits vendus par pays ? | Quantités vendues | Aucune : une quantité ne dépend pas de la devise. |

### Table `daily_sales_country_currency`

| N°  | Question | KPI utilisé | Remarque |
| --- | --- | --- | --- |
| Q5  | Quel est le chiffre d'affaires total en CAD ? | Montant des ventes | Aucune. |
| Q6  | Combien de jours ont dépassé 6 000 € de ventes en France ? | Montant des ventes | Aucune. |
| Q7  | Quel est le total des ventes par devise ? | Montant des ventes | Un total par devise, sans addition entre devises. |
| Q8  | Quelle est la valeur moyenne d'une transaction par pays ? | Valeur moyenne d'une transaction | À recalculer sur la période : montant des ventes divisé par le nombre de transactions, et non moyenne des moyennes quotidiennes. |

### Table `payment_method_analysis`

| N°  | Question | KPI utilisé | Remarque |
| --- | --- | --- | --- |
| Q9  | Quelle méthode de paiement génère le plus de ventes ? | Montant des ventes | Le montant additionne plusieurs devises (voir section 7). |
| Q10 | Quelles méthodes ont un taux de retour supérieur à 10 % ? | Taux de retour | Aucune. |
| Q11 | Quelle méthode est associée au plus grand nombre d'articles en moyenne ? | Nombre moyen d'articles par transaction | Aucune. |
| Q12 | Classement des méthodes par volume de transactions. | Nombre de transactions | Aucune. |
