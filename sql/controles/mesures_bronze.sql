-- Mesures de bronze.pos_sales_raw pour les contrôles RC01 et RC02.
-- Renvoie une ligne : nombre de tickets, chiffre d'affaires, quantité vendue.
-- Paramètre jour : une date pour contrôler une seule journée d'achat,
-- ou null pour contrôler toute la table.

with tickets as (
    select
        document
    from bronze.pos_sales_raw
    where %(jour)s::date is null
        or (document ->> 'purchase_timestamp')::timestamp::date = %(jour)s::date
)
select
    (select count(*) from tickets) as tickets,
    (select coalesce(round(sum((document ->> 'total_amount')::numeric), 2), 0)
        from tickets) as ca,
    (select coalesce(sum((article ->> 'quantity')::integer), 0)
        from tickets, jsonb_array_elements(document -> 'products') as article) as quantite;
