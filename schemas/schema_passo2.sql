-- Add column to existing table (allow null if not linked)
ALTER TABLE cards_kanban ADD COLUMN orcamento_id INTEGER;

-- Catalog items for estimation
CREATE TABLE itens_catalogo (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    preco_base REAL NOT NULL, -- Price per cubic meter or base unit
    dims_padrao TEXT -- JSON-like string "L:1.0,A:1.0,P:0.5" for auto-fill
);

-- Budgets table
CREATE TABLE orcamentos (
    id INTEGER PRIMARY KEY,
    client TEXT NOT NULL,
    itens_json TEXT NOT NULL, -- JSON array of items in this budget
    total REAL NOT NULL,
    status TEXT DEFAULT 'pendente',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Seed Catalog
INSERT INTO itens_catalogo (nome, preco_base, dims_padrao) VALUES 
('Gaveteiro Simples', 400.0, 'L:0.5,A:0.7,P:0.5'),
('Roupeiro 2 Portas', 850.0, 'L:1.0,A:2.4,P:0.6'),
('Armário Aéreo', 450.0, 'L:1.2,A:0.8,P:0.35'),
('Balcão Cozinha', 600.0, 'L:1.2,A:0.9,P:0.6'),
('Painel TV', 300.0, 'L:1.8,A:1.5,P:0.05');
