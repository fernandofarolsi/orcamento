import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app import create_app
from app.database import get_db
from app.services.calculator import calculate_item_tier_cost

app = create_app()

with app.app_context():
    db = get_db()
    
    # 1. Setup Test Data
    print("Setting up test data...")
    # Create Item
    cur = db.cursor()
    cur.execute("INSERT INTO estoque (nome, categoria, custo_unitario) VALUES ('Dobradiça Comum', 'Ferragem', 5.00)")
    item_id_eco = cur.lastrowid
    
    cur.execute("INSERT INTO estoque (nome, categoria, custo_unitario) VALUES ('Dobradiça Blum', 'Ferragem', 25.00)")
    item_id_prem = cur.lastrowid
    
    cur.execute("INSERT INTO itens_catalogo (nome, preco_base) VALUES ('Armário Teste', 100)")
    cat_id = cur.lastrowid
    
    # Add Insumo to Catalog (Uses Comum by default)
    cur.execute("INSERT INTO catalogo_insumos (catalogo_id, estoque_id, quantidade, tipo_calculo) VALUES (?, ?, 10, 'fixo')", (cat_id, item_id_eco))
    
    # Create Rule for Premium (Tier 3)
    # Rule: Replace 'Ferragem' with 'Dobradiça Blum'
    cur.execute("INSERT INTO tier_rules (tier_id, category, item_id) VALUES (3, 'Ferragem', ?)", (item_id_prem,))
    db.commit()
    
    # 2. Test Calculation
    # Item Data from Frontend
    item_data = {
        'catalogo_id': cat_id,
        'L': 1000, 'A': 1000, 'P': 500, # mm
        'complex': 1.0,
        'acessorios': []
    }
    
    print("\n--- Testing Calculation ---")
    
    # Eco (Tier 1) - Should use default (Comum) -> 10 * 5.00 = 50.00
    cost_eco, details_eco = calculate_item_tier_cost(db, item_data, 1)
    print(f"Eco Cost: {cost_eco} (Expected ~50 + labor)")
    print("Details:", details_eco)
    
    # Premium (Tier 3) - Should use Rule (Blum) -> 10 * 25.00 = 250.00
    cost_prem, details_prem = calculate_item_tier_cost(db, item_data, 3)
    print(f"Premium Cost: {cost_prem} (Expected ~250 + labor)")
    print("Details:", details_prem)
    
    # Cleanup
    print("\nCleaning up...")
    cur.execute("DELETE FROM tier_rules WHERE tier_id=3 AND category='Ferragem'")
    cur.execute("DELETE FROM catalogo_insumos WHERE catalogo_id=?", (cat_id,))
    cur.execute("DELETE FROM itens_catalogo WHERE id=?", (cat_id,))
    cur.execute("DELETE FROM estoque WHERE id IN (?, ?)", (item_id_eco, item_id_prem))
    db.commit()
