-- Mesures du modèle en étoile de gold pour le contrôle RC02, par devise.
-- Renvoie une ligne par devise : devise, tickets, ca, quantite.
-- Tickets et chiffre d'affaires viennent de fait_ticket, la quantité de
-- fait_ligne_vente : les deux tables de faits sont contrôlées.
-- La devise vient de dim_magasin. Un ticket sans magasin disparaît de la
-- jointure : l'écart de tickets le fait alors passer en KO.
-- Paramètre jour : une date, ou null pour toute la table.

with tickets as (
    select
        magasin.devise,
        count(*) as tickets,
        round(sum(ticket.montant_total::numeric), 2) as ca
    from gold.fait_ticket as ticket
    join gold.dim_magasin as magasin on magasin.magasin_id = ticket.magasin_id
    where %(jour)s::date is null or ticket.date_id = %(jour)s::date
    group by magasin.devise
),
lignes as (
    select
        magasin.devise,
        sum(ligne.quantite) as quantite
    from gold.fait_ligne_vente as ligne
    join gold.dim_magasin as magasin on magasin.magasin_id = ligne.magasin_id
    where %(jour)s::date is null or ligne.date_id = %(jour)s::date
    group by magasin.devise
)
select
    coalesce(tickets.devise, lignes.devise) as devise,
    coalesce(tickets.tickets, 0) as tickets,
    coalesce(tickets.ca, 0) as ca,
    coalesce(lignes.quantite, 0) as quantite
from tickets
full join lignes on lignes.devise = tickets.devise
order by devise;
