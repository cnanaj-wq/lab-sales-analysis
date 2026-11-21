-- Alimente gold.dim_date : un jour par ligne, sans trou, de la première
-- à la dernière date d'achat de silver.exploded_products.
-- Les noms de mois et de jours sont en français ; les numéros (mois,
-- jour_semaine) servent de codes stables pour les traductions.

insert into gold.dim_date (
    date_id,
    annee,
    trimestre,
    mois,
    nom_mois,
    semaine_iso,
    jour,
    jour_semaine,
    nom_jour
)
select
    jour::date,
    extract(year from jour)::integer,
    extract(quarter from jour)::integer,
    extract(month from jour)::integer,
    (array[
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
        'août', 'septembre', 'octobre', 'novembre', 'décembre'
    ])[extract(month from jour)::integer],
    extract(week from jour)::integer,
    extract(day from jour)::integer,
    extract(isodow from jour)::integer,
    (array[
        'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'
    ])[extract(isodow from jour)::integer]
from generate_series(
    (select min(purchase_timestamp)::date from silver.exploded_products),
    (select max(purchase_timestamp)::date from silver.exploded_products),
    interval '1 day'
) as jour;
