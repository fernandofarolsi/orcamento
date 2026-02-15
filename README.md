# Móveis Planejados MVP

MVP ultra-básico de gestão para fábrica de móveis.

## Instalação

1. Crie e ative um ambiente virtual (opcional mas recomendado):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Inicialize o Banco de Dados:
   ```bash
   sqlite3 app.db < schema.sql
   # Inserir usuário admin padrão
   sqlite3 app.db "INSERT INTO users (username, password, role) VALUES ('admin', 'admin', 'admin');"
   ```

## Execução

Rode com Uvicorn (reload ativo):
```bash
uvicorn app:app_asgi --reload --host 0.0.0.0 --port 5000
```
> Nota: usamos `app:app_asgi` para rodar com Uvicorn, pois o Flask é WSGI.

Acesse: [http://localhost:5000](http://localhost:5000)
Login: `admin` / `admin`

## Funcionalidades
- Login com JWT (Cookies)
- Dashboard com Kanban (Drag & Drop visual)
- Tabela de Auditoria (Logs de login)
# orcamento
