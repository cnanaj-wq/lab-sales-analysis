-- Mesures de silver.exploded_products pour les contrôles RC01 et RC02, par devise.
-- Renvoie une ligne par devise : devise, tickets, ca, quantite.
-- total_amount est répété sur chaque article : il est compté une fois par ticket.
-- Paramètre jour : une date, ou null pour toute la table.

with tickets as (
    select
        transaction_id,
        currency as devise,
        max(total_amount) as montant,
        sum(quantity) as quantite
    from silver.exploded_products
    where %(jour)s::date is null
        or purchase_timestamp::date = %(jour)s::date
    group by transaction_id, currency
)
select
    devise,
    count(*) as tickets,
    round(sum(montant::numeric), 2) as ca,
    sum(quantite) as quantite
from tickets
group by devise
order by devise;
