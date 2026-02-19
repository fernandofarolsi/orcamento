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
