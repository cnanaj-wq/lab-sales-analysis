-- Alimente gold.store_sales_summary à partir de silver.exploded_products.
-- Une ligne par magasin. Recalcul complet : la table est vidée puis remplie.
-- total_amount est répété sur chaque article d'un ticket : la sous-requête
-- tickets le ramène à une seule valeur par ticket avant de faire la somme.

truncate table gold.store_sales_summary;

insert into gold.store_sales_summary (
    store_id,
    store_name,
    store_country,
    store_city,
    store_type,
    total_sales_amount,
    total_quantity_sold
)
with tickets as (
    select
        transaction_id,
        store_id,
        store_name,
        store_country,
        store_city,
        store_type,
        max(total_amount) as total_amount,
        sum(quantity) as quantity_sold
    from silver.exploded_products
    group by
        transaction_id,
        store_id,
        store_name,
        store_country,
        store_city,
        store_type
)
select
    store_id,
    store_name,
    store_country,
    store_city,
    store_type,
    sum(total_amount),
    sum(quantity_sold)
from tickets
group by
    store_id,
    store_name,
    store_country,
    store_city,
    store_type;
