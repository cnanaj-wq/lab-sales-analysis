-- Q12. Classement des méthodes par volume de transactions.
-- Table : gold.payment_method_analysis. KPI : nombre de transactions.

select
    rank() over (order by total_transactions desc) as rang,
    payment_method,
    total_transactions
from gold.payment_method_analysis
order by rang;
