CREATE TABLE IF NOT EXISTS crm_contatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT DEFAULT 'lead', -- 'cliente', 'fornecedor', 'funcionario', 'lead', 'parceiro'
    telefone TEXT,
    email TEXT,
    origem TEXT, -- 'manual', 'google', 'site', 'indicacao'
    observacoes TEXT,
    google_resource_name TEXT, -- ID do contato no Google People API
    last_sync_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster search
CREATE INDEX IF NOT EXISTS idx_crm_nome ON crm_contatos(nome);
CREATE INDEX IF NOT EXISTS idx_crm_tipo ON crm_contatos(tipo);
