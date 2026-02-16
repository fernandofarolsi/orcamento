-- Schema para tabelas financeiras do calendário
-- Execute: sqlite3 app.db < schema_calendario.sql

-- Tabela de contas a receber (geradas por faturamento)
CREATE TABLE IF NOT EXISTS contas_receber (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    data_vencimento DATE,
    data_pagamento DATE,
    status TEXT DEFAULT 'pendente', -- 'pendente', 'pago', 'vencido'
    orcamento_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de contas a pagar (salários, fornecedores, etc)
CREATE TABLE IF NOT EXISTS contas_pagar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    data_vencimento DATE,
    data_pagamento DATE,
    status TEXT DEFAULT 'pendente', -- 'pendente', 'pago', 'vencido'
    categoria TEXT, -- 'salario', 'fornecedor', 'aluguel', etc
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Adicionar colunas de datas na tabela orcamentos se não existirem
ALTER TABLE orcamentos ADD COLUMN prazo_entrega DATE;
ALTER TABLE orcamentos ADD COLUMN data_instalacao DATE;

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_contas_receber_vencimento ON contas_receber(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_contas_pagar_vencimento ON contas_pagar(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_orcamentos_prazo ON orcamentos(prazo_entrega);
CREATE INDEX IF NOT EXISTS idx_orcamentos_instalacao ON orcamentos(data_instalacao);
