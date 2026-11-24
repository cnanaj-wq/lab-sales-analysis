-- Mesures de gold.payment_method_analysis pour le contrôle RC02.
-- Renvoie une seule ligne : devise vide, tickets, ca.
-- La table n'a ni devise ni date : elle ne peut être rapprochée que sur son
-- total, toutes devises confondues. Limite connue, à revoir avec #41.
-- Paramètre jour : non utilisé, la table se contrôle toujours en entier.

select
    null::text as devise,
    sum(total_transactions) as tickets,
    round(sum(total_sales_amount::numeric), 2) as ca
from gold.payment_method_analysis;
