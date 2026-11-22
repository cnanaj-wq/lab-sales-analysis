# Analyse des ventes d'un réseau international de magasins de sport

**Résultats des 12 questions métier**

| Champ      | Valeur                                                        |
|------------|---------------------------------------------------------------|
| Référence  | LSA-DOC-05                                                    |
| Version    | 0.1                                                           |
| Auteur     | Cédric NANA                                                   |
| Date       | 2026-11-22                                                    |



## Historique des révisions


| Version | Date       | Auteur      | Modification                   |
|---------|------------|-------------|--------------------------------|
| 0.1     | 2026-11-22 | Cédric NANA | Création : Q1 à Q12            |


---

## 1. Objet

Ce document donne la réponse chiffrée à chacune des douze questions de
l'annexe A du [besoin métier](01_Besoin_metier.md#annexe-a-questions-métier),
avec sa réserve lorsqu'il y en a une (critère CS02).

Chaque question a sa requête dans [`sql/questions/`](../sql/questions/), qui
lit seulement les 3 tables gold. Les résultats ont été obtenus le 2026-11-22
sur les 30 000 tickets chargés (19 450 000,75 de CA, 180 091 articles, contrôlés
par les portes RC01 et RC02).

## 2. Conventions

- **Magasin** : une enseigne dans une ville, soit 450 magasins. `store_id`
  n'identifie pas un magasin unique (P01) et `store_type` change d'un ticket à
  l'autre : ni l'un ni l'autre n'entre dans la définition. C'est la même
  définition que `gold.dim_magasin`.
- **Montants** : en devise locale. Chaque pays a une seule devise, l'EUR est
  partagé par 5 pays. La source ne contient aucun taux de change (P02) : un
  classement entre pays de devises différentes est donné tel que demandé, avec
  cette réserve.
- **Arrondis** : montants à 2 décimales, moyennes et taux à 2 décimales.

## 3. Table `store_sales_summary`

### Q1. Quels sont les 5 magasins ayant réalisé le plus de chiffre d'affaires ?

Requête : [`q01_top5_magasins_ca.sql`](../sql/questions/q01_top5_magasins_ca.sql)

| Rang | Enseigne         | Ville     | Pays           | Devise | Chiffre d'affaires |
|------|------------------|-----------|----------------|--------|--------------------|
| 1    | Athlete's Corner | London    | United Kingdom | GBP    | 75 985,75          |
| 2    | Pro Fitness      | Houston   | United States  | USD    | 75 390,00          |
| 3    | Active Life      | The Hague | Netherlands    | EUR    | 75 377,75          |
| 4    | Active Life      | Eindhoven | Netherlands    | EUR    | 73 596,50          |
| 5    | Active Life      | Toronto   | Canada         | CAD    | 73 169,00          |

**Réserve** : le classement compare 4 devises différentes (P02). Il dépend
aussi de la définition d'un magasin (P01).

### Q2. Quelle est la ville avec le chiffre d'affaires cumulé le plus élevé ?

Requête : [`q02_ville_ca_max.sql`](../sql/questions/q02_ville_ca_max.sql)

**Eindhoven** (Netherlands) : **308 493,50 EUR**.



### Q3. Combien de magasins se trouvent dans chaque pays ?

Requête : [`q03_magasins_par_pays.sql`](../sql/questions/q03_magasins_par_pays.sql)

**25 magasins dans chacun des 18 pays**, soit 450 magasins : Canada, China,
France, Germany, India, Indonesia, Italy, Japan, Mexico, Netherlands,
Saudi Arabia, South Korea, Spain, Thailand, United Arab Emirates,
United Kingdom, United States, Vietnam.

En comptant les `store_id`, on obtiendrait 8 681 identifiants, dont 7 493 présents dans
plusieurs pays.

### Q4. Quelle est la quantité totale de produits vendus par pays ?

Requête : [`q04_quantite_par_pays.sql`](../sql/questions/q04_quantite_par_pays.sql)

| Pays                 | Quantité vendue |
|----------------------|-----------------|
| South Korea          | 10 440          |
| Mexico               | 10 315          |
| United Arab Emirates | 10 246          |
| France               | 10 174          |
| Netherlands          | 10 162          |
| Saudi Arabia         | 10 162          |
| Vietnam              | 10 134          |
| Japan                | 10 117          |
| China                | 10 087          |
| India                | 10 038          |
| Spain                | 9 978           |
| United States        | 9 865           |
| Germany              | 9 841           |
| Canada               | 9 766           |
| Thailand             | 9 750           |
| Italy                | 9 733           |
| United Kingdom       | 9 706           |
| Indonesia            | 9 577           |
| **Total**            | **180 091**     |



## 4. Table `daily_sales_country_currency`

### Q5. Quel est le chiffre d'affaires total en CAD ?

Requête : [`q05_ca_total_cad.sql`](../sql/questions/q05_ca_total_cad.sql)

**CA TOTAL : 1 294 261,00 CAD** (Canada, seul pays en CAD).

### Q6. Combien de jours ont dépassé 6 000 € de ventes en France ?

Requête : [`q06_jours_france_plus_6000.sql`](../sql/questions/q06_jours_france_plus_6000.sql)

**5 jours**. Un jour correspond à la date d'achat enregistrée par la caisse (H04).

### Q7. Quel est le total des ventes par devise ?

Requête : [`q07_ventes_par_devise.sql`](../sql/questions/q07_ventes_par_devise.sql)

| Devise | Pays                                             | Total des ventes |
|--------|--------------------------------------------------|------------------|
| AED    | United Arab Emirates                             | 1 219 554,50     |
| CAD    | Canada                                           | 1 294 261,00     |
| CNY    | China                                            | 914 433,00       |
| EUR    | France, Germany, Italy, Netherlands, Spain       | 6 183 077,00     |
| GBP    | United Kingdom                                   | 1 318 277,00     |
| IDR    | Indonesia                                        | 621 681,75       |
| INR    | India                                            | 560 282,00       |
| JPY    | Japan                                            | 1 270 093,50     |
| KRW    | South Korea                                      | 1 245 951,25     |
| MXN    | Mexico                                           | 862 893,00       |
| SAR    | Saudi Arabia                                     | 1 086 060,00     |
| THB    | Thailand                                         | 765 729,25       |
| USD    | United States                                    | 1 389 310,00     |
| VND    | Vietnam                                          | 718 397,50       |



### Q8. Quelle est la valeur moyenne d'une transaction par pays ?

Requête : [`q08_panier_moyen_par_pays.sql`](../sql/questions/q08_panier_moyen_par_pays.sql)

| Pays                 | Devise | Valeur moyenne d'une transaction |
|----------------------|--------|----------------------------------|
| Canada               | CAD    | 799,42                           |
| China                | CNY    | 543,66                           |
| France               | EUR    | 793,19                           |
| Germany              | EUR    | 747,68                           |
| India                | INR    | 329,97                           |
| Indonesia            | IDR    | 389,04                           |
| Italy                | EUR    | 685,67                           |
| Japan                | JPY    | 762,82                           |
| Mexico               | MXN    | 503,44                           |
| Netherlands          | EUR    | 812,68                           |
| Saudi Arabia         | SAR    | 655,44                           |
| South Korea          | KRW    | 733,34                           |
| Spain                | EUR    | 652,04                           |
| Thailand             | THB    | 469,20                           |
| United Arab Emirates | AED    | 727,66                           |
| United Kingdom       | GBP    | 798,47                           |
| United States        | USD    | 834,42                           |
| Vietnam              | VND    | 428,89                           |

La valeur est recalculée sur la période : montant des ventes divisé par le nombre de transactions.

## 5. Table `payment_method_analysis`

### Q9. Quelle méthode de paiement apporte le plus de ventes ?

Requête : [`q09_paiement_plus_de_ventes.sql`](../sql/questions/q09_paiement_plus_de_ventes.sql)

**Cash** : **2 901 724,75**.

**Réserve** : ce montant additionne les 14 devises (P02). Il est donné tel que
demandé, mais n'est pas un montant dans une devise réelle.

### Q10. Quelles méthodes ont un taux de retour supérieur à 10 % ?

Requête : [`q10_paiements_retour_plus_10.sql`](../sql/questions/q10_paiements_retour_plus_10.sql)

| Méthode de paiement     | Taux de retour |
|-------------------------|----------------|
| Google Pay (Mastercard) | 10,75 %        |
| Apple Pay (Visa)        | 10,70 %        |
| Cash                    | 10,32 %        |

Le taux est la part des tickets au statut `Returned`.

### Q11. Quelle méthode est associée au plus grand nombre d'articles en moyenne ?

Requête : [`q11_paiement_plus_articles.sql`](../sql/questions/q11_paiement_plus_articles.sql)

**Cash** : **6,07 articles** par transaction en moyenne.

### Q12. Classement des méthodes par volume de transactions

Requête : [`q12_classement_paiements_volume.sql`](../sql/questions/q12_classement_paiements_volume.sql)

| Rang | Méthode de paiement     | Transactions |
|------|-------------------------|--------------|
| 1    | Mastercard              | 4 389        |
| 2    | Apple Pay (Mastercard)  | 4 335        |
| 3    | Cash                    | 4 312        |
| 4    | Google Pay (Visa)       | 4 301        |
| 5    | Apple Pay (Visa)        | 4 288        |
| 6    | Google Pay (Mastercard) | 4 250        |
| 7    | Visa                    | 4 125        |
|      | **Total**               | **30 000**   |

## 6. Vérifications

| Vérification | Résultat |
|--------------|----------|
| Q1 recalculée sur le modèle en étoile (`fait_ticket` et `dim_magasin`) | Mêmes 5 magasins, mêmes montants |
| Q3 recalculée sur `gold.dim_magasin` | 25 magasins par pays |
| Q4 : somme des quantités comparée à silver | 180 091 des deux côtés |
| Q5 et Q7 recalculées sur silver, un montant par ticket | Totaux identiques |
| Q6 recalculée sur silver, seuil strict et seuil large | 5 jours dans les deux cas |
| Q8 France recalculée sur silver | 793,19 |
| Q12 : somme des transactions | 30 000, le nombre de tickets chargés |
