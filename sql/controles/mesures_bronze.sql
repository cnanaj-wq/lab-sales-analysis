-- Mesures de bronze.pos_sales_raw pour le contrôle RC01, par devise.
-- Renvoie une ligne par devise : devise, tickets, ca, quantite.
-- Paramètre jour : une date pour contrôler une seule journée d'achat,
-- ou null pour contrôler toute la table.

with tickets as (
    select
        document ->> 'currency' as devise,
        (document ->> 'total_amount')::numeric as montant,
        (select coalesce(sum((article ->> 'quantity')::integer), 0)
            from jsonb_array_elements(document -> 'products') as article) as quantite
    from bronze.pos_sales_raw
    where %(jour)s::date is null
        or (document ->> 'purchase_timestamp')::timestamp::date = %(jour)s::date
)
select
    devise,
    count(*) as tickets,
    round(sum(montant), 2) as ca,
    sum(quantite) as quantite
from tickets
group by devise
order by devise;
