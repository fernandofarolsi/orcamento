import sqlite3

DATABASE = 'app.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("Migrating database for Payroll System...")

    # 1. Create ponto_registros table
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ponto_registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER,
            data DATE NOT NULL,
            entrada_1 TEXT, 
            saida_1 TEXT,  
            entrada_2 TEXT, 
            saida_2 TEXT,   
            extras_minutos INTEGER DEFAULT 0,
            atrasos_minutos INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Presente',
            FOREIGN KEY(funcionario_id) REFERENCES funcionarios(id)
        )
        ''')
        print("Created table 'ponto_registros'.")
    except Exception as e:
        print(f"Error creating table: {e}")

    # 2. Add nome_ponto column to funcionarios
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(funcionarios)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'nome_ponto' not in columns:
            cursor.execute("ALTER TABLE funcionarios ADD COLUMN nome_ponto TEXT")
            print("Added column 'nome_ponto' to 'funcionarios'.")
        else:
            print("Column 'nome_ponto' already exists.")
    except Exception as e:
        print(f"Error adding column: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
