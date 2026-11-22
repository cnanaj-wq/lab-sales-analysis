-- Q8. Quelle est la valeur moyenne d'une transaction par pays ?
-- Table : gold.daily_sales_country_currency. KPI : valeur moyenne d'une transaction.
-- Recalculée sur toute la période : montant des ventes divisé par le nombre
-- de transactions, et non moyenne des moyennes quotidiennes.
-- Chaque valeur est dans la devise de son pays.

select
    store_country,
    currency,
    sum(daily_total_sales) / sum(number_of_transactions) as valeur_moyenne_transaction
from gold.daily_sales_country_currency
group by
    store_country,
    currency
order by store_country;
