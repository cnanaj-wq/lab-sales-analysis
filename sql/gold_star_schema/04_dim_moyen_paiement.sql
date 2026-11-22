-- Alimente gold.dim_moyen_paiement : un moyen de paiement par ligne.
-- famille et reseau sont déduits du libellé. Un libellé inconnu est classé
-- « À classer » plutôt que rangé par défaut dans une famille au hasard.

insert into gold.dim_moyen_paiement (
    moyen_paiement,
    famille,
    reseau
)
select
    payment_method,
    case
        when payment_method = 'Cash' then 'Espèces'
        when payment_method in ('Visa', 'Mastercard') then 'Carte'
        when payment_method like 'Apple Pay%'
            or payment_method like 'Google Pay%' then 'Portefeuille mobile'
        else 'À classer'
    end,
    case
        when payment_method = 'Cash' then 'Aucun'
        when payment_method like '%Visa%' then 'Visa'
        when payment_method like '%Mastercard%' then 'Mastercard'
        else 'À classer'
    end
from (
    select distinct payment_method
    from silver.exploded_products
) as moyens;
