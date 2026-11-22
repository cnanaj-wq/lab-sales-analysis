-- Q5. Quel est le chiffre d'affaires total en CAD ?
-- Table : gold.daily_sales_country_currency. KPI : montant des ventes.

select
    sum(daily_total_sales) as chiffre_affaires_cad
from gold.daily_sales_country_currency
where currency = 'CAD';
