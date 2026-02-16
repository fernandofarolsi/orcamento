-- Adicionar coluna de área por unidade (m2 da chapa) no estoque
ALTER TABLE estoque ADD COLUMN area_unidade REAL DEFAULT 0;

-- Adicionar link com material principal no catálogo
ALTER TABLE itens_catalogo ADD COLUMN estoque_id INTEGER;
ALTER TABLE itens_catalogo ADD COLUMN categoria TEXT; -- 'Armarios', 'Cozinhas', etc
