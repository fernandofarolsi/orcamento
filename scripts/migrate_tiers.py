import sqlite3
import os

DB_PATH = 'app.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Migrating database for Budget Tiers...")

    # 1. Create budget_tiers
    cur.execute("""
    CREATE TABLE IF NOT EXISTS budget_tiers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        order_index INTEGER DEFAULT 0
    )
    """)

    # 2. Create tier_rules
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tier_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tier_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        item_id INTEGER,
        price_modifier REAL DEFAULT 1.0,
        FOREIGN KEY(tier_id) REFERENCES budget_tiers(id),
        FOREIGN KEY(item_id) REFERENCES estoque(id)
    )
    """)
    
    # 3. Add seed data for tiers
    tiers = [
        (1, 'Econômico', 'Opção mais acessível com materiais padrão.', 1),
        (2, 'Intermediário', 'Melhor custo-benefício com acabamentos superiores.', 2),
        (3, 'Premium', 'Acabamento de alto padrão e ferragens de ponta.', 3)
    ]
    
    for t_id, name, desc, order in tiers:
        try:
            cur.execute("INSERT INTO budget_tiers (id, name, description, order_index) VALUES (?, ?, ?, ?)", 
                        (t_id, name, desc, order))
            print(f"Inserted tier: {name}")
        except sqlite3.IntegrityError:
            print(f"Tier {name} already exists.")

    # 4. Add selected_tier_id to orcamentos
    try:
        cur.execute("ALTER TABLE orcamentos ADD COLUMN selected_tier_id INTEGER REFERENCES budget_tiers(id)")
        print("Added selected_tier_id to orcamentos.")
    except sqlite3.OperationalError:
        print("Column selected_tier_id likely already exists or is not needed yet.")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
