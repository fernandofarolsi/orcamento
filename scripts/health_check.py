import sys
import os
import sqlite3

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import get_db

def check_schema():
    print("[-] Verifying Database Schema...")
    app = create_app()
    with app.app_context():
        db = get_db()
        
        # 1. Check CRM Tables
        try:
            db.execute("SELECT 1 FROM crm_contatos LIMIT 1")
            print("  [OK] Table 'crm_contatos' exists.")
        except sqlite3.OperationalError:
            print("  [FAIL] Table 'crm_contatos' MISSING.")

        # 2. Check Inventory Columns
        expected_columns = ['margem_lucro', 'preco_venda', 'minimo', 'localizacao', 'price_strategy', 'price_group_id']
        cursor = db.execute("PRAGMA table_info(estoque)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        for col in expected_columns:
            if col in columns:
                print(f"  [OK] Column 'estoque.{col}' exists.")
            else:
                print(f"  [FAIL] Column 'estoque.{col}' MISSING.")

        # 3. Check Price Groups
        try:
            db.execute("SELECT 1 FROM price_groups LIMIT 1")
            print("  [OK] Table 'price_groups' exists.")
        except sqlite3.OperationalError:
            print("  [FAIL] Table 'price_groups' MISSING.")

def check_routes():
    print("\n[-] Verifying Route Registration...")
    app = create_app()
    with app.app_context():
        # List specific critical blueprints
        blueprints = app.blueprints.keys()
        required_bps = ['crm', 'estoque', 'kanban', 'orcamentos', 'clientes']
        
        for bp in required_bps:
            if bp in blueprints:
                print(f"  [OK] Blueprint '{bp}' registered.")
            else:
                print(f"  [FAIL] Blueprint '{bp}' NOT registered.")

if __name__ == "__main__":
    print("=== SYSTEM HEALTH CHECK ===")
    try:
        check_schema()
        check_routes()
        print("\n=== CHECK COMPLETED ===")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
