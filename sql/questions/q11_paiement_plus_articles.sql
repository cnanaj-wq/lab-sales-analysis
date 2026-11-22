-- Q11. Quelle méthode est associée au plus grand nombre d'articles en moyenne ?
-- Table : gold.payment_method_analysis. KPI : nombre moyen d'articles par transaction.

select
    payment_method,
    average_items_per_transaction
from gold.payment_method_analysis
order by average_items_per_transaction desc
limit 1;
