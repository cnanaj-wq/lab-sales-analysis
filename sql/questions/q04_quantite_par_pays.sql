-- Q4. Quelle est la quantité totale de produits vendus par pays ?
-- Table : gold.store_sales_summary. KPI : quantités vendues.

select
    store_country,
    sum(total_quantity_sold) as quantite_vendue
from gold.store_sales_summary
group by store_country
order by quantite_vendue desc;
