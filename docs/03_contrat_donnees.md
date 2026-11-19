# Analyse des ventes d'un réseau international de magasins de sport

**Contrat de données des ventes des systèmes de caisse (POS)**

| Champ      | Valeur                                                        |
|------------|---------------------------------------------------------------|
| Référence  | LSA-DOC-03                                                    |
| Version    | 0.1                                                           |
| Statut     | Brouillon                                                     |
| Auteur     | Cédric NANA                                                   |
| Date       | 2026-11-19                                                    |
| Validateur | Responsable métier et fournisseur des données de caisse (à désigner) |


## Historique des révisions


| Version | Date       | Auteur      | Modification                   |
|---------|------------|-------------|--------------------------------|
| 0.1     | 2026-11-19 | Cédric NANA | Création : sections 1 à 8      |


---

## 1. Objet et parties

### 1.1 Objet

Ce contrat fixe **ce que le fournisseur des données de caisse livre et ce que le pipeline de données de ventes accepte**. Il répond à une question : **à quelles conditions une livraison de ventes peut-elle être chargée et publiée ?**

Il s'appuie sur deux documents :

- la note de cadrage (LSA-DOC-01), pour les règles de gestion RG01 à RG10 et les hypothèses H01 à H08 
- le profilage du fichier source (LSA-DOC-02), pour les règles proposées RP01 à RP09, que ce contrat valide ou ajuste

Il tranche aussi les trois points que la note de cadrage lui a confiés : la clé unique du ticket, le calendrier des livraisons attendues et le signal qui confirme une journée sans ventes.

### 1.2 Parties

| Rôle | Qui | Engagement |
|------|-----|------------|
| Producteur | Fournisseur des données de caisse (systèmes POS des magasins) | Livrer chaque jour un fichier conforme aux sections 2 et 3, à l'heure convenue. |
| Consommateur | Équipe Data (pipeline PostgreSQL et Airflow) | Contrôler chaque livraison, charger celles qui sont conformes, signaler les autres sans les publier. |
| Utilisateurs | Direction commerciale, direction générale, responsables de magasin | Lire les indicateurs publiés, uniquement sur des journées complètes et validées (RG06). |
| Validateur | Responsable métier, avec le fournisseur des données de caisse | Valider ce contrat et chacune de ses évolutions (section 8). |

### 1.3 Périmètre

**Inclus :**

- les livraisons de tickets de caisse : format, nommage, calendrier et relivraison 
- le schéma attendu aux niveaux ticket et ligne article, et la correspondance avec les noms du modèle conceptuel de données 
- les valeurs de référence, l'identification du ticket, du magasin et du produit 
- les contrôles de qualité rejoués à chaque livraison et le traitement des écarts

**Exclus :**

- les données absentes de la source : client, taxe et taux de change (limites L1 à L3 du profilage) 
- le calcul des indicateurs, décrit dans la note de cadrage 
- la structure physique des tables PostgreSQL, décrite dans le modèle physique de données


## 2. Livraison

### 2.1 Livraisons attendues

Le pipeline reçoit deux types de livraison.

| Type | Contenu | Fréquence |
|------|---------|-----------|
| Reprise d'historique | Le fichier `pos_sales_data_30k.json` : 30 000 tickets du 2023-01-01 au 2025-12-31. | Une seule fois, au démarrage. |
| Livraison quotidienne | Les tickets d'**une** journée de vente, rattachés par la date de `purchase_timestamp` (RG01). | Une par jour, pour la veille. |

Pour démontrer l'exploitation quotidienne, les livraisons quotidiennes sont obtenues en découpant le fichier d'historique par date d'achat (H02).

### 2.2 Format

| Élément | Valeur attendue |
|---------|-----------------|
| Format | JSON, encodé en UTF-8 |
| Contenu | Une liste de tickets, chaque ticket contenant la liste de ses lignes article (`products`) |
| Schéma | Celui de la section 3, identique pour tous les tickets |
| Fichier vide | Autorisé : une liste vide `[]` (voir 2.5) |

### 2.3 Nommage et dépôt

| Élément | Valeur attendue |
|---------|-----------------|
| Nom du fichier quotidien | `pos_sales_AAAA-MM-JJ.json`, où la date est la **journée de vente** couverte, et non la date d'envoi |
| Exemple | `pos_sales_2024-07-16.json` contient uniquement les tickets achetés le 2024-07-16 |
| Dossier de dépôt | `data/incoming/` |
| Après traitement | Le fichier est conservé tel quel en lecture seule : il n'est jamais modifié |

Un ticket dont la date d'achat ne correspond pas à la date du nom du fichier rend la livraison non conforme.

### 2.4 Calendrier

Les heures sont exprimées en heure de Paris (section 6 de la note de cadrage).

| Étape | Échéance | Origine |
|-------|----------|---------|
| Dépôt du fichier de la veille | Au plus tard à 06:00 | H06, à valider |
| Alerte de retard | À 06:15, si le fichier attendu n'est pas arrivé | H06, à valider |
| Publication des ventes de la veille | À 07:00 | H06, à valider |

Une livraison en retard est traitée dès son arrivée, par une relance à la demande, sans attendre l'exécution du lendemain.

### 2.5 Journée sans ventes

Le fournisseur livre **un fichier chaque jour, même lorsqu'aucune vente n'a eu lieu**. La distinction suivante applique la règle RG06.

| Situation | Signification | Affichage |
|-----------|---------------|-----------|
| Fichier reçu et conforme, avec des tickets | Journée complète | Ventes publiées |
| Fichier reçu et conforme, liste vide `[]` | Journée sans ventes **confirmée** | Ventes affichées à zéro |
| Aucun fichier reçu à l'échéance | Livraison manquante | Statut « Données manquantes », jamais zéro |

Le fichier vide est donc le signal qui confirme une journée sans ventes. Ce choix est **proposé, à valider** avec le fournisseur des données de caisse.

### 2.6 Relivraison

Une journée peut être livrée à nouveau, par exemple après une correction. La règle RG05 s'applique.

| Cas | Traitement |
|-----|------------|
| Même fichier ou mêmes tickets avec un contenu identique | Chargement sans effet : les indicateurs ne changent pas |
| Un ticket déjà chargé revient avec un contenu différent | Livraison bloquée et alerte à l'équipe Data : l'écart est résolu avant toute publication |
| Nouveaux tickets pour une journée déjà publiée | Livraison bloquée et alerte : un complément de journée doit être confirmé par le fournisseur |

Un ticket est reconnu par son identifiant `transaction_id` (section 5).


## 3. Schéma

Le schéma décrit chaque champ livré et le relie au **modèle conceptuel de données** (`docs/modeles/mcd.excalidraw.svg`) : le MCD emploie le vocabulaire métier, la source emploie ses propres noms, et ce tableau fait la correspondance.

Un champ **obligatoire** doit être présent dans chaque ticket et ne jamais être vide (`null`, chaîne vide ou liste vide). Les valeurs autorisées des listes fermées sont données en section 4. Les contrôles correspondants sont numérotés en section 6.

### 3.1 Niveau ticket

Un élément de la liste livrée correspond à un ticket de vente : 15 champs, décrits sur 16 lignes car `promo_code` contient deux valeurs.

| Champ source | Nom métier (MCD) | Entité ou association | Type | Obligatoire | Règle de validité |
|--------------|------------------|-----------------------|------|-------------|-------------------|
| `transaction_id` | `num_ticket` | TICKET_VENTE | Texte | Oui | Format `TXN` suivi de 6 chiffres. Unique dans toutes les livraisons (section 5). |
| `purchase_timestamp` | `date_heure_achat` | TICKET_VENTE | Texte | Oui | Format `AAAA-MM-JJ HH:MM:SS`, date réelle du calendrier. Heure locale du magasin (H04). Sa date est celle du nom du fichier (2.3). |
| `total_amount` | `montant_total` | TICKET_VENTE | Décimal | Oui | Strictement positif, 2 décimales au plus. Montant brut, remise non déduite (RG08), en devise locale. Égal à la somme quantité × prix des lignes (RG02). |
| `discount_applied` | `montant_remise` | TICKET_VENTE | Décimal | Oui | Positif ou nul, 2 décimales au plus, inférieur ou égal à `total_amount`. |
| `promo_code` [0] | `indicateur_promo` | TICKET_VENTE | Texte | Oui | Première valeur de la liste `promo_code` : `yes` ou `no`. |
| `promo_code` [1] | `code_promo` | CODE_PROMO, par BENEFICIER | Texte | Non | Deuxième valeur de la liste : un code de la section 4, ou `null`. Doit être `null` si l'indicateur vaut `no`. |
| `return_status` | `statut_retour` | TICKET_VENTE | Texte | Oui | `Returned` ou `Not Returned`. Le retour porte sur le ticket entier (RG04). |
| `store_type` | `type_magasin` | TICKET_VENTE | Texte | Oui | `Mall` ou `Standalone Store`. Attribut du ticket et non du magasin (RP09). |
| `payment_method` | `libelle_moyen` | MOYEN_PAIEMENT, par PAYER | Texte | Oui | Un des 7 moyens de paiement de la section 4. |
| `store_name` | `nom_enseigne` | MAGASIN, par ENREGISTRER | Texte | Oui | Une des enseignes de la section 4. Avec la ville, identifie le magasin (RP01). |
| `store_city` | `nom_ville` | VILLE, par SITUER | Texte | Oui | Une des villes de la section 4 rattachée à un seul pays. |
| `store_country` | `nom_pays` | PAYS, par APPARTENIR | Texte | Oui | Un des 18 pays de la section 4, en anglais. Doit être le pays de la ville. |
| `currency` | `code_devise` | DEVISE, par UTILISER | Texte | Oui | Code ISO 4217 sur 3 lettres. Doit être la devise du pays (section 4). |
| `products` | — | CONTENIR | Liste | Oui | Au moins une ligne article (3.2). |
| `total_quantity_sold` | — | Non repris | Entier | Oui | Strictement positif. Égal à la somme des quantités des lignes (RG03). |
| `store_id` | — | Non repris | Texte | Oui | Format `STR` suivi de 4 chiffres. Ne sert pas à identifier le magasin (RP01). |

Deux champs sont livrés mais **non repris dans le MCD** :

- `total_quantity_sold` se déduit des lignes article. Il sert uniquement au contrôle de rapprochement (RG03).
- `store_id` ne désigne pas un magasin unique (RG10, RP01). Il est conservé dans les données chargées pour la traçabilité, mais aucun indicateur ne l'utilise.

### 3.2 Niveau ligne article

Chaque élément de la liste `products` correspond à une ligne de vente : 5 champs. Une ligne relie un ticket à un produit par l'association CONTENIR.

| Champ source | Nom métier (MCD) | Entité ou association | Type | Obligatoire | Règle de validité |
|--------------|------------------|-----------------------|------|-------------|-------------------|
| `product_id` | `code_produit` | PRODUIT | Texte | Oui | Format `P` suivi de 3 chiffres. Un des 10 produits de la section 4. Une seule ligne par produit dans un ticket. |
| `product_name` | `nom_produit` | PRODUIT | Texte | Oui | Toujours le même nom pour un même `product_id` (section 4). |
| `products_category` | `nom_categorie` | CATEGORIE, par REGROUPER | Texte | Oui | Une des 4 catégories de la section 4. Toujours la même pour un même produit. |
| `quantity` | `quantite` | CONTENIR | Entier | Oui | Strictement positif. |
| `price` | `prix_unitaire` | CONTENIR | Décimal | Oui | Strictement positif, 2 décimales au plus. Prix de la ligne, en devise du ticket : il varie d'un ticket à l'autre pour un même produit (RP05). |

Le champ catégorie s'appelle bien **`products_category`** dans la source, avec un « s », et non `category`.

### 3.3 Identifiants calculés

Le MCD utilise des identifiants qui ne sont pas livrés. Le pipeline les calcule à partir des champs source, selon les règles de la section 5.

| Identifiant (MCD) | Entité | Calculé à partir de |
|-------------------|--------|---------------------|
| `code_magasin` | MAGASIN | `store_name` et `store_city` |
| `code_ville` | VILLE | `store_city` et `store_country` |
| `code_pays` | PAYS | `store_country` par la table de correspondance de la section 4 |
| `code_categorie` | CATEGORIE | `products_category` |


## 4. Valeurs de référence

Les champs à liste fermée n'acceptent que les valeurs ci-dessous, écrites exactement ainsi : même orthographe, mêmes majuscules, mêmes espaces. Elles sont relevées dans le fichier d'historique (profilage, LSA-DOC-02).

### 4.1 Listes simples

| Champ source | Nombre | Valeurs autorisées |
|--------------|--------|--------------------|
| `return_status` | 2 | `Returned`, `Not Returned` |
| `store_type` | 2 | `Mall`, `Standalone Store` |
| `promo_code` [0] | 2 | `yes`, `no` |
| `promo_code` [1] | 5 | `FREESHIP`, `NEWYEAR25`, `SPRING10`, `SUMMER15`, `WINTER20`, ou `null` |
| `payment_method` | 7 | `Cash`, `Visa`, `Mastercard`, `Apple Pay (Visa)`, `Apple Pay (Mastercard)`, `Google Pay (Visa)`, `Google Pay (Mastercard)` |
| `store_name` | 5 | `Active Life`, `Athlete's Corner`, `Champion Gear`, `Pro Fitness`, `Sports Hub` |

Les portefeuilles mobiles (Apple Pay, Google Pay) sont distingués selon la carte utilisée : ils comptent comme 7 moyens de paiement distincts dans les indicateurs.

Un ticket « promo : oui » sans code reçoit le code `UNKNOWN` au chargement (RP02). Ce code n'est jamais livré par la source.

### 4.2 Produits et catégories

| `product_id` | `product_name` | `products_category` |
|--------------|----------------|---------------------|
| P001 | Running Shoes | Shoes |
| P002 | Football Jersey | Clothing |
| P003 | Tennis Racket | Equipment |
| P004 | Basketball | Equipment |
| P005 | Weightlifting Gloves | Accessories |
| P006 | Cycling Helmet | Equipment |
| P007 | Yoga Mat | Accessories |
| P008 | Hiking Backpack | Equipment |
| P009 | Swimming Goggles | Accessories |
| P010 | Golf Club Set | Equipment |

4 catégories : `Accessories`, `Clothing`, `Equipment`, `Shoes`.

### 4.3 Pays, devises et villes

Les pays sont livrés en anglais. Le code pays suit la norme ISO 3166-1 alpha-2, le code devise la norme ISO 4217. Chaque pays a une seule devise, chaque ville un seul pays.

| `store_country` | Pays | Code pays | `currency` | Villes (`store_city`) |
|-----------------|------|-----------|------------|-----------------------|
| Canada | Canada | CA | CAD | Calgary, Montreal, Ottawa, Toronto, Vancouver |
| China | Chine | CN | CNY | Beijing, Chengdu, Guangzhou, Shanghai, Shenzhen |
| France | France | FR | EUR | Lyon, Marseille, Nice, Paris, Toulouse |
| Germany | Allemagne | DE | EUR | Berlin, Cologne, Frankfurt, Hamburg, Munich |
| India | Inde | IN | INR | Bangalore, Chennai, Delhi, Hyderabad, Mumbai |
| Indonesia | Indonésie | ID | IDR | Bali, Bandung, Jakarta, Medan, Surabaya |
| Italy | Italie | IT | EUR | Florence, Milan, Naples, Rome, Turin |
| Japan | Japon | JP | JPY | Kyoto, Nagoya, Osaka, Tokyo, Yokohama |
| Mexico | Mexique | MX | MXN | Cancun, Guadalajara, Mexico City, Monterrey, Tijuana |
| Netherlands | Pays-Bas | NL | EUR | Amsterdam, Eindhoven, Rotterdam, The Hague, Utrecht |
| Saudi Arabia | Arabie saoudite | SA | SAR | Dammam, Jeddah, Mecca, Medina, Riyadh |
| South Korea | Corée du Sud | KR | KRW | Busan, Daegu, Daejeon, Incheon, Seoul |
| Spain | Espagne | ES | EUR | Barcelona, Bilbao, Madrid, Seville, Valencia |
| Thailand | Thaïlande | TH | THB | Bangkok, Chiang Mai, Krabi, Pattaya, Phuket |
| United Arab Emirates | Émirats arabes unis | AE | AED | Abu Dhabi, Ajman, Dubai, Ras Al Khaimah, Sharjah |
| United Kingdom | Royaume-Uni | GB | GBP | Birmingham, Edinburgh, Liverpool, London, Manchester |
| United States | États-Unis | US | USD | Chicago, Houston, Los Angeles, Miami, New York |
| Vietnam | Viêt Nam | VN | VND | Da Nang, Hai Phong, Hanoi, Ho Chi Minh City, Nha Trang |

Soit 18 pays, 14 devises (l'euro est partagé par 5 pays) et 90 villes.

### 4.4 Nouvelle valeur

Une valeur absente de ces listes n'est pas forcément une erreur : un nouveau magasin peut ouvrir, un nouveau moyen de paiement peut apparaître. Le traitement dépend du champ.

| Champ | Nouvelle valeur | Traitement |
|-------|-----------------|------------|
| `store_country`, `currency` | Nouveau pays ou nouvelle devise | Bloquant : le code ISO et la devise du pays doivent être ajoutés au contrat avant chargement. |
| `return_status`, `store_type`, `promo_code` [0] | Valeur inconnue | Bloquant : la signification de la valeur est inconnue. |
| `product_id`, `products_category` | Nouveau produit ou nouvelle catégorie | Bloquant : le produit et sa catégorie doivent être ajoutés au contrat avant chargement. |
| `store_name`, `store_city` | Nouvelle enseigne ou nouvelle ville dans un pays connu | Avertissement : la livraison est chargée, le magasin est créé et la liste est mise à jour dans la version suivante du contrat. |
| `payment_method`, `promo_code` [1] | Nouveau moyen de paiement ou nouveau code promo | Avertissement : la livraison est chargée et la liste est mise à jour dans la version suivante du contrat. |


## 5. Identification

Chaque entité du MCD est reconnue par une **clé naturelle**, c'est-à-dire par un ou plusieurs champs livrés. Le pipeline en déduit les identifiants du MCD (section 3.3). Les clés techniques des tables sont définies dans le modèle physique de données.

| Entité (MCD) | Identifiant (MCD) | Clé naturelle (champs source) | Nombre dans l'historique | Origine |
|--------------|-------------------|-------------------------------|--------------------------|---------|
| TICKET_VENTE | `num_ticket` | `transaction_id` | 30 000 | H03, U1 |
| MAGASIN | `code_magasin` | `store_name` + `store_city` + `store_country` | 450 | RP01, K4, K6 |
| VILLE | `code_ville` | `store_city` + `store_country` | 90 | Section 4.3 |
| PAYS | `code_pays` | `store_country` | 18 | Section 4.3 |
| DEVISE | `code_devise` | `currency` | 14 | V5, K3 |
| PRODUIT | `code_produit` | `product_id` | 10 | D4 |
| CATEGORIE | `code_categorie` | `products_category` | 4 | Section 4.2 |
| MOYEN_PAIEMENT | `libelle_moyen` | `payment_method` | 7 | D2 |
| CODE_PROMO | `code_promo` | `promo_code` [1] | 5, plus `UNKNOWN` | K5, RP02 |

### 5.1 Ticket

`transaction_id` est la **clé unique du ticket**. Elle est unique dans toutes les livraisons, pas seulement dans un fichier : un identifiant déjà chargé qui revient est traité comme une relivraison (section 2.6). Ceci tranche la question de la clé unique du ticket posée par la note de cadrage (RG05, H03).

### 5.2 Magasin

Un magasin est **une enseigne dans une ville** (RP01). `store_id` ne l'identifie pas : 87,5 % des identifiants désignent plusieurs magasins, parfois dans plusieurs pays (RG10, K4).

Le pays fait partie de la clé de la ville, et donc de celle du magasin. Aujourd'hui, aucun nom de ville n'est partagé par deux pays, mais rien ne l'interdit à l'avenir (par exemple Valencia en Espagne et au Venezuela). La clé reste ainsi valable si le réseau s'étend.

`store_type` ne fait pas partie de la clé : un même magasin apparaît sous les deux types selon le ticket (RP09).

### 5.3 Produit

`product_id` identifie le produit. Son nom et sa catégorie doivent rester les mêmes d'une livraison à l'autre. Un même `product_id` livré avec un autre nom ou une autre catégorie rend la livraison non conforme.


## 6. Règles de qualité

Les contrôles ci-dessous sont **rejoués à chaque livraison**, reprise d'historique comprise (RP06). Ils reprennent les contrôles du profilage (LSA-DOC-02), cités dans la colonne « Origine ».

Chaque contrôle a un niveau :

- **Bloquant** : la livraison entière est refusée. Rien n'est chargé ni publié pour la journée (section 7).
- **Avertissement** : la livraison est chargée et publiée. L'écart est signalé à l'équipe Data.

Le moment indique quand le contrôle s'exécute : **avant chargement**, sur le fichier reçu, ou **après chargement**, sur les tables PostgreSQL.

### 6.1 Liste des contrôles

**Livraison**

| N° | Contrôle | Niveau | Moment | Origine |
|----|----------|--------|--------|---------|
| CQ01 | Le fichier de la journée est présent à l'échéance (2.4). Sinon, alerte et statut « Données manquantes ». | Bloquant | Avant chargement | RG06, H06 |
| CQ02 | Le fichier est un JSON valide, encodé en UTF-8, qui contient une liste. | Bloquant | Avant chargement | S1 |
| CQ03 | Le nom du fichier respecte le format `pos_sales_AAAA-MM-JJ.json`. | Bloquant | Avant chargement | 2.3 |
| CQ04 | Tous les tickets ont la date d'achat du nom du fichier. | Bloquant | Avant chargement | 2.3, RG01 |

**Structure**

| N° | Contrôle | Niveau | Moment | Origine |
|----|----------|--------|--------|---------|
| CQ05 | Chaque ticket contient exactement les 15 champs de la section 3.1, ni plus ni moins. | Bloquant | Avant chargement | S4, C1 |
| CQ06 | Chaque ligne article contient exactement les 5 champs de la section 3.2. | Bloquant | Avant chargement | C3 |
| CQ07 | `promo_code` est une liste de 2 valeurs. `products` est une liste d'au moins une ligne. | Bloquant | Avant chargement | S5 |

**Format et complétude**

| N° | Contrôle | Niveau | Moment | Origine |
|----|----------|--------|--------|---------|
| CQ08 | Aucun champ obligatoire n'est vide (`null`, chaîne vide ou liste vide). | Bloquant | Avant chargement | C2, C4 |
| CQ09 | Chaque champ a le type attendu : texte, entier ou décimal. | Bloquant | Avant chargement | 3.1, 3.2 |
| CQ10 | Les identifiants respectent leur format : `TXN` + 6 chiffres, `STR` + 4 chiffres, `P` + 3 chiffres. | Bloquant | Avant chargement | 3.1, 3.2 |
| CQ11 | `purchase_timestamp` respecte le format `AAAA-MM-JJ HH:MM:SS` et désigne une date réelle du calendrier. | Bloquant | Avant chargement | F1, F2 |
| CQ12 | Montant, quantités et prix sont strictement positifs. La remise est positive ou nulle et ne dépasse pas le montant. Les décimaux ont 2 décimales au plus. | Bloquant | Avant chargement | 3.1, 3.2 |

**Unicité**

| N° | Contrôle | Niveau | Moment | Origine |
|----|----------|--------|--------|---------|
| CQ13 | Chaque `transaction_id` apparaît une seule fois dans le fichier. | Bloquant | Avant chargement | U1, RG05 |
| CQ14 | Un `transaction_id` déjà chargé revient avec un contenu différent (2.6). S'il revient à l'identique, il est ignoré sans erreur. | Bloquant | Avant chargement | RG05, 5.1 |
| CQ15 | Deux tickets ont le même contenu sous des identifiants différents. | Avertissement | Avant chargement | U2 |
| CQ16 | Un produit apparaît au plus une fois dans un ticket. | Bloquant | Avant chargement | U3 |

**Cohérence**

| N° | Contrôle | Niveau | Moment | Origine |
|----|----------|--------|--------|---------|
| CQ17 | `total_amount` est égal à la somme quantité × prix des lignes, arrondie au centime. | Bloquant | Avant chargement | K1, RG02 |
| CQ18 | `total_quantity_sold` est égal à la somme des quantités des lignes. | Bloquant | Avant chargement | K2, RG03 |
| CQ19 | `currency` est la devise du pays du ticket (4.3). | Bloquant | Avant chargement | K3 |
| CQ20 | `store_city` est une ville du pays `store_country` (4.3). | Bloquant | Avant chargement | 5.2 |
| CQ21 | Si l'indicateur promo vaut `no`, le code promo est `null`. | Bloquant | Avant chargement | K5 |
| CQ22 | Un ticket « promo : oui » sans code reçoit le code `UNKNOWN`. Le nombre de tickets concernés est signalé. | Avertissement | Avant chargement | K5, RP02 |
| CQ23 | Un `product_id` a toujours le même nom et la même catégorie (4.2). | Bloquant | Avant chargement | D4, 5.3 |

**Valeurs de référence**

| N° | Contrôle | Niveau | Moment | Origine |
|----|----------|--------|--------|---------|
| CQ24 | Chaque champ à liste fermée prend une valeur de la section 4. Une nouvelle valeur est traitée selon la section 4.4. | Selon 4.4 | Avant chargement | Section 4 |

**Volume et rapprochement**

| N° | Contrôle | Niveau | Moment | Origine |
|----|----------|--------|--------|---------|
| CQ25 | Le nombre de tickets de la journée est compris entre 12 et 49. Un fichier vide `[]` est accepté comme journée sans ventes (2.5) mais signalé. | Avertissement | Avant chargement | D6, RP07 |
| CQ26 | Le nombre de tickets chargés est égal au nombre de tickets livrés, hors tickets ignorés par CQ14. | Bloquant | Après chargement | CS04 |
| CQ27 | La table `exploded_products` contient une ligne par ligne article livrée. | Bloquant | Après chargement | RP05, V1 |
| CQ28 | Le montant des ventes par devise et la quantité totale des tables d'analyse sont égaux à ceux du fichier livré. | Bloquant | Après chargement | CS04, RG02, RG03 |

Les seuils de CQ25 viennent de l'historique (12 à 49 tickets par jour). Ils sont à recalibrer sur le volume de production (H01).

### 6.2 Décision sur les règles proposées par le profilage

| Règle | Décision | Où elle s'applique |
|-------|----------|--------------------|
| RP01 | Validée, avec le pays ajouté à la clé de la ville | Section 5.2, CQ20 |
| RP02 | Validée | Section 4.1, CQ22 |
| RP03 | Validée | Règle de calcul (RG04) : aucun contrôle de livraison |
| RP04 | Validée | Règle de calcul : aucun total entre devises. CQ19 garantit la devise de chaque ticket |
| RP05 | Validée | CQ17, CQ27 |
| RP06 | Validée | Section 6 dans son ensemble |
| RP07 | Ajustée : un fichier absent est bloquant (CQ01), un fichier vide est accepté avec avertissement (CQ25) | CQ01, CQ25, section 2.5 |
| RP08 | Validée | Règle de calcul (RG08, H07) : aucun contrôle de livraison |
| RP09 | Validée | Sections 3.1 et 5.2 |


## 7. Traitement des écarts

### 7.1 Statut d'une livraison

Après les contrôles, chaque livraison reçoit un seul statut.

| Statut | Condition | Conséquence |
|--------|-----------|-------------|
| Publiée | Aucun contrôle en échec | La journée est chargée et publiée. |
| Publiée avec avertissement | Au moins un avertissement, aucun contrôle bloquant en échec | La journée est chargée et publiée. Les avertissements sont signalés à l'équipe Data. |
| Refusée | Au moins un contrôle bloquant en échec | Rien n'est chargé pour la journée. Le rapport conserve la dernière version validée et affiche « Données manquantes » (RG06). |
| Manquante | Aucun fichier reçu à l'échéance (CQ01) | Alerte à 06:15 et statut « Données manquantes » (RG06). |

Une livraison refusée l'est **en entier** : aucun ticket n'est chargé, même ceux qui sont conformes. Une journée n'est jamais publiée à moitié.

Si un contrôle **après chargement** échoue (CQ26 à CQ28), les données de la journée sont retirées des tables, et la livraison passe au statut « Refusée ».

### 7.2 Rôles en cas d'écart

| Étape | Qui | Action |
|-------|-----|--------|
| Détection | Pipeline | Exécute les contrôles et attribue le statut. |
| Alerte | Pipeline | Prévient l'équipe Data dès qu'une livraison est refusée ou manquante. |
| Analyse | Équipe Data | Lit le rapport de contrôle et identifie l'origine de l'écart. |
| Correction | Fournisseur des données de caisse | Corrige les données à la source et relivre la journée. Le pipeline ne corrige jamais un fichier reçu. |
| Reprise | Équipe Data | Relance le traitement à la demande (7.3). |

### 7.3 Reprise

1. Le fournisseur dépose le fichier corrigé, sous le **même nom** que le fichier refusé.
2. L'équipe Data relance le traitement pour cette journée, sans attendre l'exécution du lendemain.
3. Tous les contrôles sont rejoués sur le nouveau fichier.
4. Les tickets déjà chargés et identiques sont ignorés (CQ14) : la reprise ne crée aucun doublon (CS09).

### 7.4 Journal des contrôles

Chaque livraison laisse une trace dans un journal, conservé par le pipeline.

| Information | Exemple |
|-------------|---------|
| Fichier | `pos_sales_2024-07-16.json` |
| Journée de vente | 2024-07-16 |
| Heure de réception | 2024-07-17 05:42 |
| Heure de traitement | 2024-07-17 06:00 |
| Résultat de chaque contrôle | CQ01 à CQ28 : réussi, avertissement ou échec avec au plus 10 exemples par échec |
| Statut final | Publiée, publiée avec avertissement, refusée ou manquante |

Ce journal sert à afficher dans le rapport la **date de la dernière journée complète** et l'**heure de la dernière publication** (CS10). Sa structure physique est définie dans le modèle physique de données.


## 8. Points ouverts et évolution du contrat

### 8.1 Points ouverts

| N° | Question | Qui décide | Impact |
|----|----------|------------|--------|
| H04 | Les heures de `purchase_timestamp` sont-elles bien l'heure locale du magasin ? | Fournisseur des données de caisse | Journée de rattachement des ventes (RG01), CQ04. |
| H06 | Les échéances 06:00, 06:15 et 07:00 sont-elles tenables ? | Direction commerciale et équipe Data | Calendrier (2.4), CQ01. |
| H01 | Quels seuils de volume quotidien retenir en production ? | Équipe Data | CQ25, à recalibrer sur le volume réel. |
| P02 | Comment comparer des montants de devises différentes ? | Responsable métier | Hors contrat tant qu'aucun taux de change n'est livré. RP04 s'applique. |
| PC01 | Le fournisseur peut-il livrer un fichier vide `[]` les jours sans ventes ? | Fournisseur des données de caisse | Signal de journée sans ventes (2.5). |

Les identifiants H et P renvoient à la note de cadrage (LSA-DOC-01). PC01 est propre à ce contrat.

### 8.2 Évolution du contrat

Toute évolution est validée par le responsable métier et le fournisseur des données de caisse, puis enregistrée dans l'historique des révisions.

| Type d'évolution | Exemples | Version |
|------------------|----------|---------|
| Mineure | Ajout d'une valeur à une liste de la section 4, ajustement d'un seuil d'avertissement | 1.0 → 1.1 |
| Majeure | Champ ajouté, supprimé ou renommé, changement de type, nouveau contrôle bloquant, changement du format de livraison | 1.0 → 2.0 |

Une évolution majeure est annoncée **avant** la première livraison concernée. Sans annonce, la livraison est refusée par les contrôles de structure (CQ05, CQ06).

La version **1.0** sera la première version validée. Jusque-là, le contrat reste en brouillon (versions 0.x).
