import sqlite3
import os

DATABASE = 'app.db'

def run_migration():
    if not os.path.exists(DATABASE):
        print(f"Database {DATABASE} not found!")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # 1. Create price_groups table
        print("Creating table price_groups...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Add price_group_id to estoque if not exists
        print("Checking entries in estoque table...")
        cursor.execute("PRAGMA table_info(estoque)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'price_group_id' not in columns:
            print("Adding price_group_id column to estoque...")
            cursor.execute('ALTER TABLE estoque ADD COLUMN price_group_id INTEGER REFERENCES price_groups(id)')
        else:
            print("Column price_group_id already exists.")

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
