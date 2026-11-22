-- Mesures de silver.exploded_products pour les contrôles RC01 et RC02.
-- Renvoie une ligne : nombre de tickets, chiffre d'affaires, quantité vendue.
-- total_amount est répété sur chaque article : il est compté une fois par ticket.
-- Paramètre jour : une date, ou null pour toute la table.

with articles as (
    select
        transaction_id,
        total_amount,
        quantity
    from silver.exploded_products
    where %(jour)s::date is null
        or purchase_timestamp::date = %(jour)s::date
),
tickets as (
    select
        transaction_id,
        max(total_amount) as total_amount
    from articles
    group by transaction_id
)
select
    (select count(*) from tickets) as tickets,
    (select coalesce(round(sum(total_amount::numeric), 2), 0) from tickets) as ca,
    (select coalesce(sum(quantity), 0) from articles) as quantite;
