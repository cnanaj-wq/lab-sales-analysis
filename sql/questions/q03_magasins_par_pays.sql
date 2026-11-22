-- Q3. Combien de magasins se trouvent dans chaque pays ?
-- Table : gold.store_sales_summary. KPI : nombre de magasins.
-- Un magasin est une enseigne dans une ville (P01), comme dans gold.dim_magasin.
-- store_type n'entre pas dans la définition : il change d'un ticket à l'autre.

select
    store_country,
    count(distinct (store_name, store_city)) as nombre_magasins
from gold.store_sales_summary
group by store_country
order by
    nombre_magasins desc,
    store_country;
