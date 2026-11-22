-- Q6. Combien de jours ont dépassé 6 000 € de ventes en France ?
-- Table : gold.daily_sales_country_currency. KPI : montant des ventes.
-- Un jour est la date d'achat telle qu'enregistrée par la caisse (H04).
-- « Dépasser » est lu au sens strict : plus de 6 000 €.

select
    count(*) as nombre_jours
from gold.daily_sales_country_currency
where store_country = 'France'
  and currency = 'EUR'
  and daily_total_sales > 6000;
