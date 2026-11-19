# Analyse des ventes d'un réseau international de magasins de sport

**Profilage du fichier source**

| Champ      | Valeur                          |
|------------|---------------------------------|
| Référence  | LSA-DOC-02                      |
| Version    | 0.2                             |
| Statut     | Brouillon                       |
| Auteur     | Cédric NANA                     |
| Date       | 2026-11-19                      |
| Validateur | Responsable métier (à désigner) |


## Historique des révisions


| Version | Date       | Auteur      | Modification                         |
|---------|------------|-------------|--------------------------------------|
| 0.1     | 2026-11-18 | Cédric NANA | Création : sections 1 à 6 |
| 0.2     | 2026-11-19 | Cédric NANA | Ajout des contrôles K6 et K7, des anomalies A4 et A5, des règles RP08 et RP09 , mise à jour de RP01 après le MCD |


---

## 1. Objet et périmètre

### 1.1 Objet

Ce document présente le profilage du fichier source des ventes avant toute construction du pipeline. Il répond à une question : **les données livrées par les systèmes de caisse (POS) sont-elles assez fiables pour calculer les indicateurs de la note de cadrage (LSA-DOC-01) ?**

Pour chaque contrôle, il indique le résultat obtenu et sa conséquence pour la suite du projet : contrat de données, modèle de données, chargement dans PostgreSQL et tables d'analyse.

### 1.2 Fichier profilé

| Élément          | Valeur                                   |
|------------------|------------------------------------------|
| Fichier          | `data/raw/pos_sales_data_30k.json`       |
| Format           | JSON, une liste de tickets de caisse     |
| Taille           | 31,6 Mo (31 588 992 octets)              |
| Contenu          | 30 000 tickets, 59 928 lignes article    |
| Période de couverture | du 2023-01-01 au 2025-12-31              |
| Fourni par       | Bootcamp - Data Engineering et Analytics           |
| Livraison        | Un seul fichier, livré en une fois       |

Le fichier est en **lecture seule** : il n'est jamais modifié, ni par le script ni à la main.

### 1.3 Script utilisé

| Élément          | Valeur                                              |
|------------------|-----------------------------------------------------|
| Script           | `scripts/profilage_source.py`                       |
| Version          | commit `981a26e` de la branche `docs/modele-donnees` |
| Langage          | Python 3.12.10, bibliothèque standard uniquement    |
| Date d'exécution | 2026-11-19                                          |
| Commande         | `python scripts/profilage_source.py`, depuis la racine du projet |

Chaque contrôle porte un identifiant, repris dans ce document et dans les messages du script :

| Préfixe | Famille     | Question posée                                       |
|---------|-------------|------------------------------------------------------|
| S       | Structure   | Comment le fichier est-il organisé ?                 |
| V       | Volume      | Combien de données, sur quelle période ?             |
| F       | Format      | Les valeurs respectent-elles le format attendu ?     |
| C       | Complétude  | Manque-t-il des champs ou des valeurs ?              |
| U       | Unicité     | Y a-t-il des doublons ?                              |
| K       | Cohérence   | Les champs sont-ils cohérents entre eux ?            |
| D       | Distribution| Comment les valeurs se répartissent-elles ?          |

### 1.4 Périmètre

**Inclus :**

- les 15 champs de niveau ticket et les 5 champs de niveau article (`products`) 
- les contrôles de structure, volume, format, complétude, unicité, cohérence et distribution 
- les limites du fichier qui empêchent de calculer certains indicateurs

**Exclus :**

- la correction des données : le profilage constate, il ne modifie rien 
- les livraisons futures : seul ce fichier est profilé. Les contrôles à rejouer à chaque livraison seront définis dans le contrat de données 
- la comparaison avec une source externe (catalogue produits, référentiel magasins, taux de change) : aucune n'est fournie


## 2. Synthèse

- **Le fichier est techniquement sain.** La structure est identique sur les 30 000 tickets, aucune valeur ne manque, toutes les dates sont conformes et il n'y a aucun doublon.
- **Les totaux des tickets sont fiables.** Le montant et la quantité de chaque ticket sont égaux à la somme de ses lignes. Le montant est **brut** (remise non déduite) et exprimé en **devise locale**.
- **`store_id` ne peut pas servir de clé magasin.** 87,5 % des identifiants désignent plusieurs magasins, parfois dans plusieurs pays. C'est le seul point **bloquant**. Le modèle de données propose d'identifier un magasin par son enseigne et sa ville : 450 magasins, chacun pouvant apparaître sous deux types (`Mall` ou `Standalone Store`) selon le ticket.
- **Deux règles de gestion sont à fixer** : 2 980 tickets retournés (9,9 %) et 2 442 tickets « promo : oui » sans code (8,1 %).
- **La remise ne dépend pas de la promotion** : la quasi-totalité des tickets ont une remise, avec ou sans promotion. La remise moyenne porte donc sur tous les tickets.
- **Certains indicateurs ne sont pas calculables** : le fichier ne contient ni client, ni taxe, ni taux de change. Il n'y a donc ni fidélisation, ni distinction TTC / HT, ni CA consolidé dans une seule devise.
- **La livraison est complète** : les 1 096 jours de la période ont des ventes entre 12 et 49 tickets par jour. Ces bornes serviront de seuils au contrôle quotidien. 


## 3. Résultats par famille

Statuts : **Conforme** (aucune action), **À surveiller** (une règle ou une limite à documenter), **Bloquant** (une décision est nécessaire avant de construire le pipeline).

### 3.1 Structure (S)

| Identifiant | Contrôle | Résultat | Statut |
|-------------|----------|----------|--------|
| S1 | Type de l'objet chargé | Une liste | Conforme |
| S2 | Nombre d'éléments | 30 000 tickets | Conforme |
| S3 | Type d'un élément | Un dictionnaire (un ticket) | Conforme |
| S4 | Champs d'un ticket | 15 champs : `transaction_id`, `store_id`, `store_name`, `store_country`, `store_city`, `products`, `total_quantity_sold`, `total_amount`, `promo_code`, `payment_method`, `discount_applied`, `store_type`, `purchase_timestamp`, `return_status`, `currency` | Conforme |
| S5 | Champs imbriqués | `products` (liste d'articles, 5 champs : `product_id`, `product_name`, `products_category`, `quantity`, `price`) et `promo_code` (paire `[indicateur, code]`) | À surveiller : à aplatir au chargement |

### 3.2 Volume et période (V)

| Identifiant | Contrôle | Résultat | Statut |
|-------------|----------|----------|--------|
| V1 | Lignes article | 59 928 soit 2 articles par ticket en moyenne | Conforme : volume attendu de la table `exploded_products` |
| V2 | Première vente | 2023-01-01 01:30:24 | Conforme |
| V3 | Dernière vente | 2025-12-31 23:03:40 | Conforme |
| V4 | Pays | 18 pays | Conforme |
| V5 | Devises | 14 devises | Conforme |

### 3.3 Format (F)

| Identifiant | Contrôle | Résultat | Statut |
|-------------|----------|----------|--------|
| F1 | Dates au format `YYYY-MM-DD hh:mm:ss` | 30 000 sur 30 000 | Conforme |
| F2 | Dates non conformes ou manquantes | 0 | Conforme |

### 3.4 Complétude (C)

| Identifiant | Contrôle | Résultat | Statut |
|-------------|----------|----------|--------|
| C1 | Tickets aux champs différents | 0 | Conforme |
| C2 | Valeurs manquantes, niveau ticket | 0 | Conforme. Limite : un `null` à l'intérieur de `promo_code` n'est pas détecté ici, voir K5 |
| C3 | Articles aux champs différents | 0 | Conforme |
| C4 | Valeurs manquantes, niveau article | 0 | Conforme |

### 3.5 Unicité (U)

| Identifiant | Contrôle | Résultat | Statut |
|-------------|----------|----------|--------|
| U1 | `transaction_id` en double | 0 | Conforme : clé primaire des tickets |
| U2 | Même contenu sous un autre identifiant | 0 | Conforme |
| U3 | Produit répété dans un même ticket | 0 | Conforme : (`transaction_id`, `product_id`) est unique |

### 3.6 Cohérence (K)

| Identifiant | Contrôle | Résultat | Statut |
|-------------|----------|----------|--------|
| K1 | `total_amount` = somme(quantité × prix) | 0 écart | Conforme : montant brut, remise non déduite |
| K2 | `total_quantity_sold` = somme des quantités | 0 écart | Conforme |
| K3 | Une seule devise par pays | 0 pays multidevise ; l'EUR couvre 5 pays | Conforme |
| K4 | Un `store_id` = un seul magasin | 7 598 identifiants sur 8 681 (87,5 %) désignent plusieurs magasins. Exemple : `STR1483` à Montréal, Mumbai et Medan | **Bloquant** : `store_id` n'est pas une clé (P01) |
| K5 | Cohérence de `promo_code` | `no` sans code : 14 916 ; `yes` avec code : 12 642 ; `yes` sans code : **2 442** (8,1 %) | À surveiller : règle pour le code manquant |
| K6 | Un magasin (enseigne, ville) a toujours le même type | 450 magasins ; les **450** apparaissent sous plusieurs types | À surveiller : le type décrit le ticket, pas le magasin |
| K7 | Lien entre la remise et la promotion | Sans promo et remise > 0 : **14 914** ; avec promo et remise > 0 : 15 079 ; remise nulle : 7 tickets (2 sans promo, 5 avec promo) | À surveiller : la remise est indépendante de la promotion |

### 3.7 Distribution (D)

| Identifiant | Contrôle | Résultat | Statut |
|-------------|----------|----------|--------|
| D1 | Statut de retour | Not Returned : 27 020 ; Returned : 2 980 (9,9 %) | À surveiller : inclure ou exclure les retours du CA |
| D2 | Moyens de paiement | 7 moyens, de 4 125 (Visa) à 4 389 (Mastercard) tickets | Conforme |
| D3 | Types de magasin | Standalone Store : 15 062 ; Mall : 14 938 | Conforme |
| D4 | Lignes par produit | 10 produits, un nom par identifiant, de 5 869 à 6 149 lignes ; total 59 928 = V1 | Conforme |
| D5 | Prix par produit | 12 prix différents par produit, le maximum valant 2,5 fois le minimum. Ni la devise ni l'année n'expliquent l'écart | À surveiller : le prix appartient à la ligne de vente, pas au produit |
| D6 | Tickets par jour | 1 096 jours sur 1 096 ; de 12 à 49 tickets par jour | Conforme : seuils pour le contrôle quotidien (RG06) |


## 4. Anomalies et limites

### 4.1 Anomalies

Une anomalie est une donnée présente dans le fichier mais qui ne peut pas être utilisée telle quelle.

| Identifiant | Constat | Contrôle | Impact | Décision à prendre |
|-------------|---------|----------|--------|--------------------|
| A1 | `store_id` ne désigne pas un magasin unique : 7 598 identifiants sur 8 681 (87,5 %) renvoient à plusieurs magasins, parfois dans plusieurs pays (P01) | K4 | Grouper par `store_id` mélange des magasins, des pays et des devises. La table `store_sales_summary` serait fausse | Proposé dans le modèle de données : un magasin = une enseigne dans une ville, soit 450 magasins (K6). À valider dans le contrat de données |
| A2 | 2 442 tickets (8,1 %) indiquent une promotion (`yes`) sans code (`null`) | K5 | Le nombre de tickets en promotion vaut 15 084 si l'on suit l'indicateur, 12 642 si l'on suit le code | Choisir la référence : l'indicateur ou le code, et la valeur qui remplace le code manquant |
| A3 | 2 980 tickets (9,9 %) sont retournés. Le statut porte sur le ticket entier sans date, sans montant et sans détail par article | D1 | Le CA varie d'environ 10 % selon que les retours sont inclus ou exclus. Un retour partiel ne peut pas être distingué | Déjà tranché par RG04 : le montant est conservé et le retour est compté à part. Reste une limite : un retour partiel ne peut pas être identifié |
| A4 | La remise n'est pas liée à la promotion : 14 914 tickets sans promotion ont une remise supérieure à 0 | K7 | Comparer la remise des tickets avec et sans promotion ne montre aucun effet de la promotion. La remise moyenne porte sur la quasi-totalité des tickets | Confirmer avec le métier l'origine de la remise et la définition de la remise moyenne (RG08) |
| A5 | Le type de magasin (`store_type`) change d'un ticket à l'autre pour un même magasin : les 450 magasins apparaissent sous les deux types | K6 | Classer les magasins par type est impossible. Une analyse par type se calcule au niveau du ticket, et un même magasin compte dans les deux types | Confirmer avec le métier la signification de `store_type` |

### 4.2 Limites

Une limite est une information absente du fichier : les indicateurs qui en dépendent ne peuvent pas être calculés sans une autre source.

| Identifiant | Information absente | Impact |
|-------------|---------------------|--------|
| L1 | Champ taxe | On ne sait pas si `total_amount` et `price` sont TTC ou HT. Les montants sont publiés tels quels, sans mention de taxe |
| L2 | Taux de change | Les montants restent dans leur devise locale (14 devises). Aucun CA consolidé dans une seule devise, et aucune comparaison de montants entre pays de devises différentes |
| L3 | Identifiant client | Aucun indicateur client : fidélisation, rétention, fréquence d'achat ou panier par client |


## 5. Règles proposées pour le contrat de données

Ces règles sont des **propositions** issues du profilage. Elles seront validées dans le contrat de données puis appliquées par le pipeline. Elles complètent les règles de gestion de la note de cadrage (RG01 à RG10) sans les modifier.

| Identifiant | Origine | Règle proposée |
|-------------|---------|----------------|
| RP01 | A1, K4, K6, RG10 | Un magasin est identifié par le couple (`store_name`, `store_city`) et non par `store_id`, soit 450 magasins. Le pays se déduit de la ville. `store_type` n'est pas un attribut du magasin (voir RP09). |
| RP02 | A2, K5 | L'indicateur de `promo_code` fait foi pour compter les tickets en promotion. Un code manquant est remplacé par la valeur `UNKNOWN`. |
| RP03 | A3, D1, RG04 | Un ticket retourné reste dans le montant des ventes. Le retour est compté à part, à partir de `return_status`. Le retour s'applique au ticket entier. |
| RP04 | L1, L2, RG02 | Les montants sont publiés tels que livrés, toujours accompagnés de leur devise. Aucun montant n'est additionné entre devises différentes. |
| RP05 | S5, V1, D5, RG02, RG03 | `exploded_products` contient une ligne par article soit 59 928 lignes pour ce fichier. Le prix est lu sur la ligne de vente. Le montant d'une ligne vaut quantité × prix. `total_amount` n'est jamais additionné sur les lignes d'un même ticket. |
| RP06 | S, F, C, U, K1, K2, RG05, RG06 | À chaque livraison, les contrôles de structure, de format, de complétude, d'unicité et de rapprochement des totaux sont rejoués. Un seul échec bloque la publication de la livraison. |
| RP07 | D6, RG06 | Une journée sans aucun ticket déclenche une alerte. Un volume en dehors de 12 à 49 tickets par jour déclenche un avertissement. Ces seuils sont à recalibrer sur le volume de production. |
| RP08 | A4, K7, RG08 | La remise est un attribut du ticket, analysée indépendamment de la promotion. La remise moyenne se calcule sur tous les tickets, conformément à H07. |
| RP09 | A5, K6 | `store_type` est conservé au niveau du ticket. Toute analyse par type de magasin se calcule sur les tickets, jamais sur une liste de magasins. |


## 6. Reproduire le profilage

### 6.1 Prérequis

- Python 3.12, sans bibliothèque externe : le script n'utilise que la bibliothèque standard.
- Le fichier source est présent dans `data/raw/pos_sales_data_30k.json`.

### 6.2 Commande

Depuis la racine du projet :

```bash
python scripts/profilage_source.py
```

### 6.3 Résultat attendu

- Le script affiche une ligne par contrôle, préfixée par son identifiant (S1 à D6, dont K1 à K7). Les valeurs doivent être identiques à celles de la section 3.
- Le script s'exécute en 2 secondes environ et se termine avec le code 0.
- Si le fichier source est absent, le script s'arrête avec le message « Arrêt : fichier source introuvable » et revnoie le code 1.

Sortie complète :

```text
Fichier source : data\raw\pos_sales_data_30k.json
Fichier trouvé : True
S1 Type de l'objet chargé : <class 'list'>
S2 Nombre d'éléments : 30000
S3 Type du premier élément : <class 'dict'>
S4 Champs : ['transaction_id', 'store_id', 'store_name', 'store_country', 'store_city', 'products', 'total_quantity_sold', 'total_amount', 'promo_code', 'payment_method', 'discount_applied', 'store_type', 'purchase_timestamp', 'return_status', 'currency']
S5 Champ imbriqué : products <class 'list'>
S5 Champ imbriqué : promo_code <class 'list'>
V1 Lignes article : 59928
V2 Première vente : 2023-01-01 01:30:24
V3 Dernière vente : 2025-12-31 23:03:40
V4 Pays : 18 ['Canada', 'China', 'France', 'Germany', 'India', 'Indonesia', 'Italy', 'Japan', 'Mexico', 'Netherlands', 'Saudi Arabia', 'South Korea', 'Spain', 'Thailand', 'United Arab Emirates', 'United Kingdom', 'United States', 'Vietnam']
V5 Devises : 14 ['AED', 'CAD', 'CNY', 'EUR', 'GBP', 'IDR', 'INR', 'JPY', 'KRW', 'MXN', 'SAR', 'THB', 'USD', 'VND']
F1 Dates conformes : 30000
F2 Dates non conformes : 0 []
C1 Tickets aux champs différents : 0 []
C2 Valeurs manquantes (tickets) : 0
C3 Articles aux champs différents : 0
C4 Valeurs manquantes (articles) : 0
U1 Identifiants en double : 0 []
U2 Tickets identiques sous un autre identifiant : 0
U3 Tickets avec un produit répété : 0 []
K1 Tickets dont le montant ne correspond pas aux lignes : 0 []
K2 Tickets dont la quantité ne correspond pas aux lignes : 0 []
K3 Pays avec plusieurs devises : 0 {}
K4 store_id distincts : 8681
K4 store_id qui désignent plusieurs magasins : 7598 ['STR1483', 'STR1805', 'STR5221', 'STR5723', 'STR2796']
    exemple : [('Active Life', 'Montreal', 'Canada', 'Mall'), ("Athlete's Corner", 'Mumbai', 'India', 'Standalone Store'), ('Sports Hub', 'Medan', 'Indonesia', 'Standalone Store')]
K5 promo_code no | code renseigné : False | 14916
K5 promo_code yes | code renseigné : False | 2442
K5 promo_code yes | code renseigné : True | 12642
K6 Magasins (enseigne, ville) : 450
K6 Magasins avec plusieurs types : 450
K7 promo no | remise > 0 : False | 2
K7 promo no | remise > 0 : True | 14914
K7 promo yes | remise > 0 : False | 5
K7 promo yes | remise > 0 : True | 15079
D1 Statut de retour : {'Returned': 2980, 'Not Returned': 27020}
D2 Moyens de paiement : 7 ['Apple Pay (Mastercard)', 'Apple Pay (Visa)', 'Cash', 'Google Pay (Mastercard)', 'Google Pay (Visa)', 'Mastercard', 'Visa']
    - Mastercard : 4389
    - Apple Pay (Mastercard) : 4335
    - Cash : 4312
    - Google Pay (Visa) : 4301
    - Apple Pay (Visa) : 4288
    - Google Pay (Mastercard) : 4250
    - Visa : 4125
D3 Types de magasin : {'Standalone Store': 15062, 'Mall': 14938}
D4 Produits distincts : 10
    - P001 Running Shoes : 5976
    - P002 Football Jersey : 5982
    - P003 Tennis Racket : 5894
    - P004 Basketball : 5985
    - P005 Weightlifting Gloves : 5869
    - P006 Cycling Helmet : 6000
    - P007 Yoga Mat : 6061
    - P008 Hiking Backpack : 6001
    - P009 Swimming Goggles : 6011
    - P010 Golf Club Set : 6149
D5 Prix distincts par produit :
    - P001 : 12 prix, de 48.0 à 120.0
    - P002 : 12 prix, de 30.0 à 75.0
    - P003 : 12 prix, de 80.0 à 200.0
    - P004 : 12 prix, de 24.0 à 60.0
    - P005 : 12 prix, de 10.0 à 25.0
    - P006 : 12 prix, de 60.0 à 150.0
    - P007 : 12 prix, de 20.0 à 50.0
    - P008 : 12 prix, de 72.0 à 180.0
    - P009 : 12 prix, de 16.0 à 40.0
    - P010 : 12 prix, de 200.0 à 500.0
D6 Jours avec ventes : 1096
D6 Tickets par jour, minimum : 12
D6 Tickets par jour, maximum : 49
```
