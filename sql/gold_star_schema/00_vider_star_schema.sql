-- Vide les 6 tables de l'étoile avant leur recalcul complet.
-- Un seul truncate pour toutes les tables : PostgreSQL refuse de vider une
-- dimension tant qu'un fait y fait référence par une clé étrangère.

truncate table
    gold.fait_ligne_vente,
    gold.fait_ticket,
    gold.dim_date,
    gold.dim_magasin,
    gold.dim_produit,
    gold.dim_moyen_paiement;
