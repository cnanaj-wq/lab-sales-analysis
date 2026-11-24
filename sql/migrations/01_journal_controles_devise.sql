-- Ticket #36 : ajoute table_controlee et devise au journal des contrôles.
-- À lancer une fois sur une base déjà créée. Une base neuve reçoit ces
-- colonnes par sql/ddl_genere.sql. Rejouable sans erreur (if not exists).

alter table ops.journal_controles add column if not exists table_controlee text;
alter table ops.journal_controles add column if not exists devise text;
