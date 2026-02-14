CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audits (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action TEXT NOT NULL,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

CREATE TABLE IF NOT EXISTS cards_kanban (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,
    etapa TEXT NOT NULL,
    client TEXT
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
