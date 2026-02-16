CREATE TABLE IF NOT EXISTS estoque (
  id INTEGER PRIMARY KEY,
  nome TEXT NOT NULL,
  categoria TEXT,
  unidade TEXT,
  quantidade REAL DEFAULT 0,
  custo_unitario REAL DEFAULT 0,
  site_origem TEXT,
  last_update DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Seed some stock items
INSERT INTO estoque (nome, categoria, unidade, quantidade, custo_unitario) VALUES
('MDF Branco Tx 15mm', 'MDF', 'Chapa', 10, 250.00),
('MDF Amadeirado 15mm', 'MDF', 'Chapa', 5, 320.00),
('Corrediça Telescópica 45cm', 'Ferragem', 'Par', 50, 15.00),
('Dobradiça Curva 35mm', 'Ferragem', 'Unidade', 100, 3.50),
('Fita de LED 12V', 'Iluminação', 'Metro', 20, 12.00);
