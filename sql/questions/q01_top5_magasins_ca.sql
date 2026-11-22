-- Q1. Quels sont les 5 magasins ayant réalisé le plus de chiffre d'affaires ?
-- Table : gold.store_sales_summary. KPI : montant des ventes.
-- Un magasin est une enseigne dans une ville (450 magasins), car store_id
-- n'identifie pas un magasin unique (P01). La devise est celle du pays :
-- les montants de devises différentes ne sont pas comparables (P02).

select
    store_name,
    store_city,
    store_country,
    sum(total_sales_amount) as chiffre_affaires
from gold.store_sales_summary
group by
    store_name,
    store_city,
    store_country
order by chiffre_affaires desc
limit 5;
