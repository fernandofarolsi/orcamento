-- Enforce unique names for stock items
CREATE UNIQUE INDEX IF NOT EXISTS idx_estoque_nome ON estoque (nome);
