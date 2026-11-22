-- Alimente gold.dim_magasin : un magasin par ligne.
-- Un magasin est identifié par son enseigne et sa ville, car store_id n'est
-- pas fiable (RP01). La devise dépend du pays, une seule par pays.
-- magasin_id est une clé technique, numérotée à chaque recalcul complet.

insert into gold.dim_magasin (
    magasin_id,
    enseigne,
    ville,
    pays,
    devise
)
select
    row_number() over (order by store_country, store_city, store_name),
    store_name,
    store_city,
    store_country,
    currency
from (
    select distinct
        store_name,
        store_city,
        store_country,
        currency
    from silver.exploded_products
) as magasins;
