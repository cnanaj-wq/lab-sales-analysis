-- Q7. Quel est le total des ventes par devise ?
-- Table : gold.daily_sales_country_currency. KPI : montant des ventes.
-- Un total par devise, sans addition entre devises. EUR regroupe 5 pays.

select
    currency,
    sum(daily_total_sales) as total_ventes
from gold.daily_sales_country_currency
group by currency
order by currency;
