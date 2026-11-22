-- Alimente gold.daily_sales_country_currency à partir de silver.exploded_products.
-- Une ligne par jour, pays et devise. Recalcul complet : la table est vidée
-- puis remplie. Comme pour store_sales_summary, la sous-requête tickets ramène
-- total_amount à une seule valeur par ticket avant les calculs.

truncate table gold.daily_sales_country_currency;

insert into gold.daily_sales_country_currency (
    purchase_date,
    store_country,
    currency,
    daily_total_sales,
    number_of_transactions,
    average_transaction_value
)
with tickets as (
    select
        transaction_id,
        purchase_timestamp::date as purchase_date,
        store_country,
        currency,
        max(total_amount) as total_amount
    from silver.exploded_products
    group by
        transaction_id,
        purchase_timestamp,
        store_country,
        currency
)
select
    purchase_date,
    store_country,
    currency,
    sum(total_amount),
    count(*),
    avg(total_amount)
from tickets
group by
    purchase_date,
    store_country,
    currency;
