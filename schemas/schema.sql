CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audits (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action TEXT NOT NULL,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, 
    value TEXT
);

CREATE TABLE IF NOT EXISTS config_fabrica (
    id INTEGER PRIMARY KEY,
    margem_lucro REAL DEFAULT 0.35,
    margem_negociacao REAL DEFAULT 0.10,
    margem_impostos REAL DEFAULT 0.05
);

CREATE TABLE IF NOT EXISTS price_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS estoque (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    categoria TEXT,
    unidade TEXT,
    quantidade REAL DEFAULT 0,
    custo_unitario REAL DEFAULT 0,
    site_origem TEXT,
    is_acessorio INTEGER DEFAULT 0,
    area_unidade REAL DEFAULT 0,
    url_madeiranit TEXT,
    url_leomadeiras TEXT,
    url_madeverde TEXT,
    price_group_id INTEGER,
    last_update DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(price_group_id) REFERENCES price_groups(id)
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf_cnpj TEXT UNIQUE,
    data_nascimento DATE,
    tipo_pessoa TEXT DEFAULT 'fisica', -- 'fisica' ou 'juridica'
    telefone TEXT,
    whatsapp TEXT,
    email TEXT,
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

CREATE TABLE IF NOT EXISTS orcamentos (
    id INTEGER PRIMARY KEY,
    client TEXT, -- Keeping for compatibility, but client_id is preferred
    client_id INTEGER,
    itens_json TEXT NOT NULL, -- JSON array of items in this budget
    total REAL NOT NULL,
    status TEXT DEFAULT 'pendente',
    prazo_entrega DATE,
    data_instalacao DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(client_id) REFERENCES clientes(id)
);

CREATE TABLE IF NOT EXISTS cards_kanban (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,
    etapa TEXT NOT NULL,
    client TEXT,
    orcamento_id INTEGER
);

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

CREATE TABLE IF NOT EXISTS itens_catalogo (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    preco_base REAL,
    fator_consumo REAL,
    dims_padrao TEXT,
    estoque_id INTEGER,
    categoria TEXT,
    horas_mo REAL,
    imagem_url TEXT
);

CREATE TABLE IF NOT EXISTS catalogo_insumos (
    id INTEGER PRIMARY KEY,
    catalogo_id INTEGER,
    estoque_id INTEGER,
    quantidade REAL,
    tipo_calculo TEXT,
    FOREIGN KEY(catalogo_id) REFERENCES itens_catalogo(id) ON DELETE CASCADE
);

-- Seed Initial Data if tables are empty
INSERT OR IGNORE INTO config_fabrica (id, margem_lucro, margem_negociacao, margem_impostos) VALUES (1, 0.35, 0.10, 0.05);

INSERT OR IGNORE INTO estoque (nome, categoria, unidade, quantidade, custo_unitario) VALUES
('MDF Branco Tx 15mm', 'MDF', 'Chapa', 10, 250.00),
('MDF Amadeirado 15mm', 'MDF', 'Chapa', 5, 320.00),
('Corrediça Telescópica 45cm', 'Ferragem', 'Par', 50, 15.00),
('Dobradiça Curva 35mm', 'Ferragem', 'Unidade', 100, 3.50);
