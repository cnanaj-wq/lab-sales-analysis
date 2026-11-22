-- Alimente gold.dim_produit : un produit par ligne, avec sa catégorie.
-- Chaque product_id n'a qu'un nom et qu'une catégorie dans silver.

insert into gold.dim_produit (
    produit_id,
    nom_produit,
    categorie
)
select distinct
    product_id,
    product_name,
    products_category
from silver.exploded_products;
