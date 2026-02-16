-- Tabela de Funcionários e RH
CREATE TABLE IF NOT EXISTS funcionarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  cargo TEXT,
  salario_base REAL,
  inss_percent REAL DEFAULT 0.11,
  fgts_percent REAL DEFAULT 0.08,
  descontos_json TEXT DEFAULT '[]', -- JSON string [{"tipo":"vale","valor":100}]
  holerite_ultimo TEXT, -- Armazena JSON do último cálculo para facilidade
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Contas (Pagar e Receber)
CREATE TABLE IF NOT EXISTS contas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo TEXT NOT NULL, -- 'receber' ou 'pagar'
  descricao TEXT NOT NULL,
  valor REAL NOT NULL,
  vencimento DATE,
  status TEXT DEFAULT 'pendente', -- 'pendente', 'pago', 'vencido'
  categoria TEXT, -- 'material', 'mao_obra', 'vale_funcionario', 'venda_orcamento', 'fixo'
  funcionario_id INTEGER, -- FK opcional para pagamentos de salário/vale
  orcamento_id INTEGER, -- FK opcional para recebimentos de venda
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Dados Demo Funcionários
INSERT INTO funcionarios (nome, cargo, salario_base) VALUES 
('José Silva', 'Marceneiro Chefe', 3500.00),
('Maria Souza', 'Auxiliar Acabamento', 1800.00);

-- Dados Demo Contas
INSERT INTO contas (tipo, descricao, valor, vencimento, status, categoria) VALUES
('pagar', 'Fornecedor MDF (Chapas)', 1200.00, DATE('now', '+5 days'), 'pendente', 'material'),
('pagar', 'Energia Elétrica', 450.00, DATE('now', '+10 days'), 'pendente', 'fixo'),
('receber', 'Entrada Cozinha Sr. João', 5000.00, DATE('now', '-2 days'), 'pago', 'venda_orcamento');
