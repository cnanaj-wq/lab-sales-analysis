-- Mesures de gold.store_sales_summary pour le contrôle RC02, par devise.
-- Renvoie une ligne par devise : devise, ca, quantite (la table n'a pas de tickets).
-- La table n'a ni devise ni date : la devise est retrouvée par le pays, avec
-- la correspondance pays-devise de silver (en attendant ref.pays_devise, #41).
-- Un pays inconnu de silver donne une devise vide, donc un KO.
-- Paramètre jour : non utilisé, la table se contrôle toujours en entier.

with pays_devise as (
    select distinct
        store_country,
        currency as devise
    from silver.exploded_products
)
select
    pays_devise.devise,
    round(sum(magasin.total_sales_amount::numeric), 2) as ca,
    sum(magasin.total_quantity_sold) as quantite
from gold.store_sales_summary as magasin
left join pays_devise on pays_devise.store_country = magasin.store_country
group by pays_devise.devise
order by pays_devise.devise;
