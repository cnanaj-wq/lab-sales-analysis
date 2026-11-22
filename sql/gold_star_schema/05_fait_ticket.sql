-- Alimente gold.fait_ticket : un ticket par ligne.
-- Les champs du ticket sont répétés sur chacun de ses articles dans silver :
-- select distinct les ramène à une seule ligne par ticket.
-- magasin_id est retrouvé dans dim_magasin par l'enseigne et la ville.

insert into gold.fait_ticket (
    ticket_id,
    date_id,
    magasin_id,
    moyen_paiement,
    horodatage_achat,
    type_magasin,
    montant_total,
    remise,
    quantite_totale,
    est_retourne
)
select
    tickets.transaction_id,
    tickets.purchase_timestamp::date,
    magasin.magasin_id,
    tickets.payment_method,
    tickets.purchase_timestamp,
    tickets.store_type,
    tickets.total_amount,
    tickets.discount_applied,
    tickets.total_quantity_sold,
    tickets.return_status = 'Returned'
from (
    select distinct
        transaction_id,
        purchase_timestamp,
        store_name,
        store_city,
        payment_method,
        store_type,
        total_amount,
        discount_applied,
        total_quantity_sold,
        return_status
    from silver.exploded_products
) as tickets
join gold.dim_magasin as magasin
    on magasin.enseigne = tickets.store_name
    and magasin.ville = tickets.store_city;
