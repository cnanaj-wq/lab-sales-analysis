-- Fichier généré par scripts/generer_ddl.py : ne pas modifier à la main.

-- Schéma ops
create schema if not exists ops;
comment on schema ops is 'Journal des livraisons et des contrôles qualité';

create table if not exists ops.journal_controles (
    livraison_id integer not null,
    code_controle text not null,
    resultat text not null,
    nb_ecarts integer not null,
    exemples text,
    primary key (livraison_id, code_controle)
);
comment on column ops.journal_controles.livraison_id is 'Livraison contrôlée';
comment on column ops.journal_controles.code_controle is 'Code du contrôle, de CQ01 à CQ28';
comment on column ops.journal_controles.resultat is 'Réussi, avertissement ou échec';
comment on column ops.journal_controles.nb_ecarts is 'Nombre de lignes en écart';
comment on column ops.journal_controles.exemples is 'Au plus 10 exemples d''écarts';

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
