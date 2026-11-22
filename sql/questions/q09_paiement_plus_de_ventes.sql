-- Q9. Quelle méthode de paiement apporte le plus de ventes ?
-- Table : gold.payment_method_analysis. KPI : montant des ventes.
-- Le montant additionne plusieurs devises (P02) : le résultat est donné tel
-- que demandé, avec cette réserve.

select
    payment_method,
    total_sales_amount
from gold.payment_method_analysis
order by total_sales_amount desc
limit 1;
