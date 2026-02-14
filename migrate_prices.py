import sqlite3

DATABASE = 'app.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Add columns for individual prices
        cursor.execute("ALTER TABLE estoque ADD COLUMN preco_madeiranit REAL")
        cursor.execute("ALTER TABLE estoque ADD COLUMN preco_leomadeiras REAL")
        cursor.execute("ALTER TABLE estoque ADD COLUMN preco_madeverde REAL")
        
        # Add column for price strategy
        # Values: 'auto_max', 'manual', 'madeiranit', 'leomadeiras', 'madeverde'
        cursor.execute("ALTER TABLE estoque ADD COLUMN price_strategy TEXT DEFAULT 'auto_max'")
        
        conn.commit()
        print("Migration successful: Added price columns and strategy to 'estoque' table.")
        
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print(f"Migration skipped or partial: {e}")
        else:
            print(f"Migration failed: {e}")
            
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
