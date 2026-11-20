-- Alimente gold.payment_method_analysis à partir de silver.exploded_products.
-- Une ligne par moyen de paiement. Recalcul complet : la table est vidée puis
-- remplie. La sous-requête tickets ramène silver à une ligne par ticket :
-- montant, remise et statut de retour appartiennent au ticket, pas à l'article.

truncate table gold.payment_method_analysis;

insert into gold.payment_method_analysis (
    payment_method,
    total_transactions,
    total_sales_amount,
    average_discount,
    return_rate,
    average_items_per_transaction
)
with tickets as (
    select
        transaction_id,
        payment_method,
        return_status,
        max(total_amount) as total_amount,
        max(discount_applied) as discount_applied,
        sum(quantity) as items
    from silver.exploded_products
    group by
        transaction_id,
        payment_method,
        return_status
)
select
    payment_method,
    count(*),
    sum(total_amount),
    avg(discount_applied),
    100 * avg(case when return_status = 'Returned' then 1.0 else 0.0 end),
    avg(items)
from tickets
group by payment_method;
