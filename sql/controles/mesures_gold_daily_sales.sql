-- Mesures de gold.daily_sales_country_currency pour le contrôle RC02, par devise.
-- Renvoie une ligne par devise : devise, tickets, ca (la table n'a pas de quantité).
-- Paramètre jour : une date, ou null pour toute la table.

select
    currency as devise,
    sum(number_of_transactions) as tickets,
    round(sum(daily_total_sales::numeric), 2) as ca
from gold.daily_sales_country_currency
where %(jour)s::date is null or purchase_date = %(jour)s::date
group by currency
order by currency;
