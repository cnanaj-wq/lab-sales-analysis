-- Q10. Quelles méthodes ont un taux de retour supérieur à 10 % ?
-- Table : gold.payment_method_analysis. KPI : taux de retour.
-- return_rate est un pourcentage de 0 à 100 ; « supérieur » au sens strict.

select
    payment_method,
    return_rate
from gold.payment_method_analysis
where return_rate > 10
order by return_rate desc;
