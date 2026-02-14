-- Schema para tabela de clientes
-- Execute: sqlite3 app.db < schema_clientes.sql

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf_cnpj TEXT UNIQUE NOT NULL,
    data_nascimento DATE,
    tipo_pessoa TEXT DEFAULT 'fisica', -- 'fisica' ou 'juridica'
    telefone TEXT NOT NULL,
    whatsapp TEXT,
    email TEXT NOT NULL,
    cep TEXT,
    logradouro TEXT,
    numero TEXT,
    complemento TEXT,
    bairro TEXT,
    cidade TEXT,
    estado TEXT,
    status TEXT DEFAULT 'ativo', -- 'ativo' ou 'inativo'
    origem TEXT, -- Como conheceu a empresa
    observacoes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Adicionar coluna client_id na tabela orcamentos se não existir
ALTER TABLE orcamentos ADD COLUMN client_id INTEGER;

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome);
CREATE INDEX IF NOT EXISTS idx_clientes_cpf_cnpj ON clientes(cpf_cnpj);
CREATE INDEX IF NOT EXISTS idx_clientes_status ON clientes(status);
CREATE INDEX IF NOT EXISTS idx_orcamentos_client_id ON orcamentos(client_id);

-- Adicionar chave estrangeira
-- Note: SQLite não suporta ADD CONSTRAINT com FOREIGN KEY em tabelas existentes
-- A relação será mantida em nível de aplicação
