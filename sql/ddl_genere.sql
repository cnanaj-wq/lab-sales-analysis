-- Fichier généré par scripts/03_generer_ddl.py : ne pas modifier à la main.

-- Schéma ops
create schema if not exists ops;
comment on schema ops is 'Journal des livraisons et des contrôles qualité';

create table if not exists ops.journal_controles (
    controle_id serial not null,
    run_id text not null,
    date_logique date not null,
    livraison_id integer,
    code_controle text not null,
    mesure text not null,
    valeur_bronze numeric,
    valeur_silver numeric,
    valeur_gold numeric,
    ecart numeric,
    seuil numeric not null,
    bloquant boolean not null,
    resultat text not null,
    nb_ecarts integer not null,
    exemples text,
    controle_le timestamptz not null,
    primary key (controle_id)
);
comment on column ops.journal_controles.controle_id is 'Numéro de ligne, attribué automatiquement';
comment on column ops.journal_controles.run_id is 'Identifiant de l''exécution Airflow';
comment on column ops.journal_controles.date_logique is 'Journée contrôlée';
comment on column ops.journal_controles.livraison_id is 'Livraison contrôlée, vide pour une réconciliation entre couches';
comment on column ops.journal_controles.code_controle is 'Code du contrôle : CQ01 à CQ28, RC01 bronze-silver, RC02 silver-gold';
comment on column ops.journal_controles.mesure is 'Mesure comparée : tickets, ca ou quantite';
comment on column ops.journal_controles.valeur_bronze is 'Valeur calculée dans bronze';
comment on column ops.journal_controles.valeur_silver is 'Valeur calculée dans silver';
comment on column ops.journal_controles.valeur_gold is 'Valeur calculée dans gold';
comment on column ops.journal_controles.ecart is 'Écart le plus grand entre les couches comparées';
comment on column ops.journal_controles.seuil is 'Écart toléré, lu dans une Variable Airflow';
comment on column ops.journal_controles.bloquant is 'Oui : un échec arrête le DAG et gold n''est pas publié';
comment on column ops.journal_controles.resultat is 'Réussi, avertissement ou échec';
comment on column ops.journal_controles.nb_ecarts is 'Nombre de lignes en écart';
comment on column ops.journal_controles.exemples is 'Au plus 10 exemples d''écarts';
comment on column ops.journal_controles.controle_le is 'Date et heure du contrôle';

create table if not exists ops.journal_livraisons (
    livraison_id serial not null,
    nom_fichier text not null,
    empreinte_fichier char(64) not null,
    journee_vente date,
    recu_le timestamptz not null,
    traite_le timestamptz,
    nb_tickets integer,
    statut text not null,
    primary key (livraison_id)
);
comment on column ops.journal_livraisons.livraison_id is 'Numéro de livraison, attribué automatiquement';
comment on column ops.journal_livraisons.nom_fichier is 'Nom du fichier reçu';
comment on column ops.journal_livraisons.empreinte_fichier is 'Empreinte SHA-256 du fichier, détecte un fichier déjà intégré. Nom de l''archive : data/archive/<empreinte>.json';
comment on column ops.journal_livraisons.journee_vente is 'Journée couverte, vide pour la reprise d''historique';
comment on column ops.journal_livraisons.recu_le is 'Date et heure de réception du fichier';
comment on column ops.journal_livraisons.traite_le is 'Date et heure de fin du traitement';
comment on column ops.journal_livraisons.nb_tickets is 'Nombre de tickets lus dans le fichier';
comment on column ops.journal_livraisons.statut is 'Publiée, publiée avec avertissement, refusée, déjà intégrée ou manquante';

create table if not exists ops.journal_taches (
    tache_id serial not null,
    run_id text not null,
    date_logique date not null,
    tache text not null,
    debut_le timestamptz not null,
    fin_le timestamptz,
    statut text not null,
    essai integer not null,
    nb_lignes integer,
    message text,
    primary key (tache_id)
);
comment on column ops.journal_taches.tache_id is 'Numéro de ligne, attribué automatiquement';
comment on column ops.journal_taches.run_id is 'Identifiant de l''exécution Airflow';
comment on column ops.journal_taches.date_logique is 'Journée traitée par l''exécution, utile au backfill';
comment on column ops.journal_taches.tache is 'Nom de la tâche, par exemple gold.construire_star_schema';
comment on column ops.journal_taches.debut_le is 'Date et heure de début de la tâche';
comment on column ops.journal_taches.fin_le is 'Date et heure de fin de la tâche, vide tant qu''elle tourne';
comment on column ops.journal_taches.statut is 'En cours, succès ou échec';
comment on column ops.journal_taches.essai is 'Numéro de l''essai : 1, puis 2 ou 3 en cas de réessai';
comment on column ops.journal_taches.nb_lignes is 'Nombre de lignes traitées, transmis par XCom';
comment on column ops.journal_taches.message is 'Message principal ou erreur ';

-- Schéma bronze
create schema if not exists bronze;
comment on schema bronze is 'Tickets tels que livrés, sans correction';

create table if not exists bronze.pos_sales_raw (
    transaction_id text not null,
    livraison_id integer not null,
    document jsonb not null,
    charge_le timestamptz not null,
    primary key (transaction_id)
);
comment on column bronze.pos_sales_raw.transaction_id is 'Identifiant du ticket, extrait du document';
comment on column bronze.pos_sales_raw.livraison_id is 'Livraison qui a apporté le ticket';
comment on column bronze.pos_sales_raw.document is 'Ticket complet tel que livré, promo_code compris';
comment on column bronze.pos_sales_raw.charge_le is 'Date et heure de chargement';

-- Schéma silver
create schema if not exists silver;
comment on schema silver is 'Données contrôlées : table intermédiaire et modèle métier';

create table if not exists silver.exploded_products (
    transaction_id text not null,
    store_id text,
    store_name text,
    store_country text,
    store_city text,
    store_type text,
    purchase_timestamp timestamp,
    payment_method text,
    currency text,
    total_amount float,
    total_quantity_sold integer,
    discount_applied float,
    return_status text,
    product_id text not null,
    product_name text,
    products_category text,
    quantity integer,
    price float,
    primary key (transaction_id, product_id)
);
comment on column silver.exploded_products.transaction_id is 'Identifiant du ticket de caisse';
comment on column silver.exploded_products.store_id is 'Identifiant du magasin dans la source, non fiable (RP01)';
comment on column silver.exploded_products.store_name is 'Enseigne du magasin';
comment on column silver.exploded_products.store_country is 'Pays du magasin, tel que livré';
comment on column silver.exploded_products.store_city is 'Ville du magasin';
comment on column silver.exploded_products.store_type is 'Type de magasin';
comment on column silver.exploded_products.purchase_timestamp is 'Date et heure de l''achat';
comment on column silver.exploded_products.payment_method is 'Moyen de paiement';
comment on column silver.exploded_products.currency is 'Devise du ticket (ISO 4217)';
comment on column silver.exploded_products.total_amount is 'Montant total du ticket, en devise locale';
comment on column silver.exploded_products.total_quantity_sold is 'Nombre total d''articles du ticket';
comment on column silver.exploded_products.discount_applied is 'Remise appliquée au ticket';
comment on column silver.exploded_products.return_status is 'Statut de retour du ticket';
comment on column silver.exploded_products.product_id is 'Code du produit';
comment on column silver.exploded_products.product_name is 'Nom du produit';
comment on column silver.exploded_products.products_category is 'Catégorie du produit';
comment on column silver.exploded_products.quantity is 'Quantité vendue sur la ligne';
comment on column silver.exploded_products.price is 'Prix unitaire sur la ligne';

-- Schéma gold
create schema if not exists gold;
comment on schema gold is 'Tables d''analyse qui répondent aux 12 questions';

create table if not exists gold.daily_sales_country_currency (
    purchase_date date not null,
    store_country text not null,
    currency text not null,
    daily_total_sales float,
    number_of_transactions integer,
    average_transaction_value float,
    primary key (purchase_date, store_country, currency)
);
comment on column gold.daily_sales_country_currency.purchase_date is 'Date de la transaction, sans l''heure';
comment on column gold.daily_sales_country_currency.store_country is 'Pays du magasin';
comment on column gold.daily_sales_country_currency.currency is 'Devise locale utilisée';
comment on column gold.daily_sales_country_currency.daily_total_sales is 'Total des ventes de la journée, une fois par ticket';
comment on column gold.daily_sales_country_currency.number_of_transactions is 'Nombre de tickets distincts';
comment on column gold.daily_sales_country_currency.average_transaction_value is 'Valeur moyenne d''un ticket';

create table if not exists gold.dim_date (
    date_id date not null,
    annee integer not null,
    trimestre integer not null,
    mois integer not null,
    nom_mois text not null,
    semaine_iso integer not null,
    jour integer not null,
    jour_semaine integer not null,
    nom_jour text not null,
    primary key (date_id)
);
comment on column gold.dim_date.date_id is 'Jour du calendrier, de la première à la dernière date d''achat, sans trou';
comment on column gold.dim_date.annee is 'Année';
comment on column gold.dim_date.trimestre is 'Trimestre, de 1 à 4';
comment on column gold.dim_date.mois is 'Mois, de 1 à 12';
comment on column gold.dim_date.nom_mois is 'Nom du mois en français';
comment on column gold.dim_date.semaine_iso is 'Numéro de semaine ISO';
comment on column gold.dim_date.jour is 'Jour du mois';
comment on column gold.dim_date.jour_semaine is 'Jour de la semaine ISO, de 1 (lundi) à 7 (dimanche)';
comment on column gold.dim_date.nom_jour is 'Nom du jour en français';

create table if not exists gold.dim_magasin (
    magasin_id integer not null,
    enseigne text not null,
    ville text not null,
    pays text not null,
    devise text not null,
    primary key (magasin_id)
);
comment on column gold.dim_magasin.magasin_id is 'Clé technique du magasin, numérotée à la construction';
comment on column gold.dim_magasin.enseigne is 'Enseigne du magasin (store_name)';
comment on column gold.dim_magasin.ville is 'Ville du magasin (store_city) ';
comment on column gold.dim_magasin.pays is 'Pays du magasin (store_country)';
comment on column gold.dim_magasin.devise is 'Devise du pays (currency), une seule par pays';

create table if not exists gold.dim_moyen_paiement (
    moyen_paiement text not null,
    famille text not null,
    reseau text not null,
    primary key (moyen_paiement)
);
comment on column gold.dim_moyen_paiement.moyen_paiement is 'Moyen de paiement (payment_method)';
comment on column gold.dim_moyen_paiement.famille is 'Carte, Portefeuille mobile ou Espèces';
comment on column gold.dim_moyen_paiement.reseau is 'Visa, Mastercard ou Aucun';

create table if not exists gold.dim_produit (
    produit_id text not null,
    nom_produit text not null,
    categorie text not null,
    primary key (produit_id)
);
comment on column gold.dim_produit.produit_id is 'Code du produit (product_id)';
comment on column gold.dim_produit.nom_produit is 'Nom du produit (product_name)';
comment on column gold.dim_produit.categorie is 'Catégorie du produit (products_category)';

create table if not exists gold.fait_ligne_vente (
    ticket_id text not null,
    produit_id text not null,
    date_id date not null,
    magasin_id integer not null,
    moyen_paiement text not null,
    quantite integer not null,
    prix_unitaire float not null,
    montant_ligne float not null,
    est_retourne boolean not null,
    primary key (ticket_id, produit_id)
);
comment on column gold.fait_ligne_vente.ticket_id is 'Identifiant du ticket (transaction_id)';
comment on column gold.fait_ligne_vente.produit_id is 'Produit, lien vers dim_produit';
comment on column gold.fait_ligne_vente.date_id is 'Jour de l''achat, lien vers dim_date';
comment on column gold.fait_ligne_vente.magasin_id is 'Magasin, lien vers dim_magasin';
comment on column gold.fait_ligne_vente.moyen_paiement is 'Moyen de paiement, lien vers dim_moyen_paiement';
comment on column gold.fait_ligne_vente.quantite is 'Quantité vendue sur la ligne (quantity)';
comment on column gold.fait_ligne_vente.prix_unitaire is 'Prix unitaire en devise locale (price)';
comment on column gold.fait_ligne_vente.montant_ligne is 'Quantité multipliée par le prix unitaire, en devise locale';
comment on column gold.fait_ligne_vente.est_retourne is 'Vrai si le ticket de la ligne est retourné';

create table if not exists gold.fait_ticket (
    ticket_id text not null,
    date_id date not null,
    magasin_id integer not null,
    moyen_paiement text not null,
    horodatage_achat timestamp not null,
    type_magasin text not null,
    montant_total float not null,
    remise float not null,
    quantite_totale integer not null,
    est_retourne boolean not null,
    primary key (ticket_id)
);
comment on column gold.fait_ticket.ticket_id is 'Identifiant du ticket (transaction_id)';
comment on column gold.fait_ticket.date_id is 'Jour de l''achat, lien vers dim_date';
comment on column gold.fait_ticket.magasin_id is 'Magasin, lien vers dim_magasin';
comment on column gold.fait_ticket.moyen_paiement is 'Moyen de paiement, lien vers dim_moyen_paiement';
comment on column gold.fait_ticket.horodatage_achat is 'Date et heure de l''achat (purchase_timestamp)';
comment on column gold.fait_ticket.type_magasin is 'Type de magasin (store_type), propre au ticket : il varie pour un même magasin';
comment on column gold.fait_ticket.montant_total is 'Montant du ticket en devise locale (total_amount), égal à la somme des montant_ligne';
comment on column gold.fait_ticket.remise is 'Remise appliquée au ticket, en devise locale (discount_applied)';
comment on column gold.fait_ticket.quantite_totale is 'Nombre d''articles du ticket (total_quantity_sold)';
comment on column gold.fait_ticket.est_retourne is 'Vrai si le ticket est retourné (return_status = Returned)';

create table if not exists gold.payment_method_analysis (
    payment_method text not null,
    total_transactions integer,
    total_sales_amount float,
    average_discount float,
    return_rate float,
    average_items_per_transaction float,
    primary key (payment_method)
);
comment on column gold.payment_method_analysis.payment_method is 'Méthode de paiement utilisée';
comment on column gold.payment_method_analysis.total_transactions is 'Nombre de tickets distincts';
comment on column gold.payment_method_analysis.total_sales_amount is 'Montant total des ventes, une fois par ticket';
comment on column gold.payment_method_analysis.average_discount is 'Remise moyenne par ticket';
comment on column gold.payment_method_analysis.return_rate is 'Pourcentage de tickets retournés, de 0 à 100';
comment on column gold.payment_method_analysis.average_items_per_transaction is 'Nombre moyen d''articles par ticket';

create table if not exists gold.store_sales_summary (
    store_id text not null,
    store_name text not null,
    store_country text not null,
    store_city text not null,
    store_type text not null,
    total_sales_amount float,
    total_quantity_sold integer,
    primary key (store_id, store_name, store_country, store_city, store_type)
);
comment on column gold.store_sales_summary.store_id is 'Identifiant du magasin, granularité imposée par l''énoncé';
comment on column gold.store_sales_summary.store_name is 'Nom du magasin';
comment on column gold.store_sales_summary.store_country is 'Pays du magasin';
comment on column gold.store_sales_summary.store_city is 'Ville du magasin';
comment on column gold.store_sales_summary.store_type is 'Type de magasin';
comment on column gold.store_sales_summary.total_sales_amount is 'Somme de total_amount, comptée une fois par ticket';
comment on column gold.store_sales_summary.total_quantity_sold is 'Somme des quantités vendues';

-- Clés étrangères
alter table ops.journal_controles drop constraint if exists fk_journal_controles_livraison_id;
alter table ops.journal_controles add constraint fk_journal_controles_livraison_id foreign key (livraison_id) references ops.journal_livraisons (livraison_id);
alter table bronze.pos_sales_raw drop constraint if exists fk_pos_sales_raw_livraison_id;
alter table bronze.pos_sales_raw add constraint fk_pos_sales_raw_livraison_id foreign key (livraison_id) references ops.journal_livraisons (livraison_id);
alter table gold.fait_ticket drop constraint if exists fk_fait_ticket_date_id;
alter table gold.fait_ticket add constraint fk_fait_ticket_date_id foreign key (date_id) references gold.dim_date (date_id);
alter table gold.fait_ticket drop constraint if exists fk_fait_ticket_magasin_id;
alter table gold.fait_ticket add constraint fk_fait_ticket_magasin_id foreign key (magasin_id) references gold.dim_magasin (magasin_id);
alter table gold.fait_ticket drop constraint if exists fk_fait_ticket_moyen_paiement;
alter table gold.fait_ticket add constraint fk_fait_ticket_moyen_paiement foreign key (moyen_paiement) references gold.dim_moyen_paiement (moyen_paiement);
alter table gold.fait_ligne_vente drop constraint if exists fk_fait_ligne_vente_date_id;
alter table gold.fait_ligne_vente add constraint fk_fait_ligne_vente_date_id foreign key (date_id) references gold.dim_date (date_id);
alter table gold.fait_ligne_vente drop constraint if exists fk_fait_ligne_vente_magasin_id;
alter table gold.fait_ligne_vente add constraint fk_fait_ligne_vente_magasin_id foreign key (magasin_id) references gold.dim_magasin (magasin_id);
alter table gold.fait_ligne_vente drop constraint if exists fk_fait_ligne_vente_moyen_paiement;
alter table gold.fait_ligne_vente add constraint fk_fait_ligne_vente_moyen_paiement foreign key (moyen_paiement) references gold.dim_moyen_paiement (moyen_paiement);
alter table gold.fait_ligne_vente drop constraint if exists fk_fait_ligne_vente_produit_id;
alter table gold.fait_ligne_vente add constraint fk_fait_ligne_vente_produit_id foreign key (produit_id) references gold.dim_produit (produit_id);
