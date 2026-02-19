
import sqlite3
import shutil

DB_PATH = 'app.db'
BACKUP_PATH = 'app.db.bak'

def migrate():
    # 1. Backup
    shutil.copy(DB_PATH, BACKUP_PATH)
    print(f"Backup created at {BACKUP_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 2. Rename old table
        print("Renaming old table...")
        cursor.execute("ALTER TABLE clientes RENAME TO clientes_old")

        # 3. Create new table with nullable fields
        print("Creating new table...")
        cursor.execute("""
            CREATE TABLE clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf_cnpj TEXT,  -- Now Nullable
                data_nascimento DATE,
                tipo_pessoa TEXT DEFAULT 'fisica',
                telefone TEXT,  -- Now Nullable
                whatsapp TEXT,
                email TEXT,     -- Now Nullable
                cep TEXT,
                logradouro TEXT,
                numero TEXT,
                complemento TEXT,
                bairro TEXT,
                cidade TEXT,
                estado TEXT,
                status TEXT DEFAULT 'ativo',
                origem TEXT,
                observacoes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Copy data
        print("Copying data...")
        # Get columns from old table to ensure mapping
        cursor.execute("PRAGMA table_info(clientes_old)")
        columns = [col[1] for col in cursor.fetchall()]
        cols_str = ", ".join(columns)
        
        cursor.execute(f"INSERT INTO clientes ({cols_str}) SELECT {cols_str} FROM clientes_old")

        # 5. Drop old table
        print("Dropping old table...")
        cursor.execute("DROP TABLE clientes_old")

        # 6. Recreate Indices (if any were strictly manual, but basic ones are fine)
        # Re-adding unique constraint on cpf_cnpj ONLY if not null? 
        # SQLite UNIQUE allows multiple NULLs.
        print("Recreating indices...")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_cpf_cnpj ON clientes(cpf_cnpj) WHERE cpf_cnpj IS NOT NULL AND cpf_cnpj != ''")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome)")

        conn.commit()
        print("Migration successful!")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        print("Rolled back.")
        # Restore backup? 
        # For now, just exit.
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
