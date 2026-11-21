-- Alimente gold.fait_ligne_vente : un article vendu par ligne.
-- montant_ligne = quantité x prix unitaire ; la somme des lignes d'un ticket
-- est égale à son total_amount. magasin_id est retrouvé dans dim_magasin.

insert into gold.fait_ligne_vente (
    ticket_id,
    produit_id,
    date_id,
    magasin_id,
    moyen_paiement,
    quantite,
    prix_unitaire,
    montant_ligne,
    est_retourne
)
select
    lignes.transaction_id,
    lignes.product_id,
    lignes.purchase_timestamp::date,
    magasin.magasin_id,
    lignes.payment_method,
    lignes.quantity,
    lignes.price,
    lignes.quantity * lignes.price,
    lignes.return_status = 'Returned'
from silver.exploded_products as lignes
join gold.dim_magasin as magasin
    on magasin.enseigne = lignes.store_name
    and magasin.ville = lignes.store_city;
