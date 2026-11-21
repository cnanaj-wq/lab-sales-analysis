-- Mesures du modèle en étoile de gold pour le contrôle RC02.
-- Renvoie une ligne : nombre de tickets, chiffre d'affaires, quantité vendue.
-- Tickets et chiffre d'affaires viennent de fait_ticket, la quantité de
-- fait_ligne_vente (une ligne par article).
-- Paramètre jour : une date, ou null pour toute la table.

select
    (select count(*)
        from gold.fait_ticket
        where %(jour)s::date is null or date_id = %(jour)s::date) as tickets,
    (select coalesce(round(sum(montant_total::numeric), 2), 0)
        from gold.fait_ticket
        where %(jour)s::date is null or date_id = %(jour)s::date) as ca,
    (select coalesce(sum(quantite), 0)
        from gold.fait_ligne_vente
        where %(jour)s::date is null or date_id = %(jour)s::date) as quantite;
