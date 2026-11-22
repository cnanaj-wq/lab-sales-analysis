-- Q2. Quelle est la ville avec le chiffre d'affaires cumulé le plus élevé ?
-- Table : gold.store_sales_summary. KPI : montant des ventes.
-- Chaque ville appartient à un seul pays, donc à une seule devise : le
-- classement compare des devises différentes (P02).

select
    store_city,
    store_country,
    sum(total_sales_amount) as chiffre_affaires
from gold.store_sales_summary
group by
    store_city,
    store_country
order by chiffre_affaires desc
limit 1;
