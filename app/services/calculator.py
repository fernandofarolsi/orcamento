from app.database import get_db

def get_tier_rules(db, tier_id):
    """
    Returns a dict: { category: { 'item_id': id, 'price_modifier': float } }
    """
    rows = db.execute("SELECT category, item_id, price_modifier FROM tier_rules WHERE tier_id = ?", (tier_id,)).fetchall()
    rules = {}
    for r in rows:
        rules[r['category']] = {
            'item_id': r['item_id'],
            'price_modifier': r['price_modifier']
        }
    return rules

def calculate_item_tier_cost(db, item_data, tier_id):
    """
    Calculates cost for a single item usage under a specific tier.
    item_data: { 'catalogo_id': int, 'L': float, 'A': float, 'P': float, 'complex': float, 'acessorios': [] }
    """
    cat_id = item_data.get('catalogo_id')
    L = float(item_data.get('L', 0)) / 1000.0 # mm to m
    A = float(item_data.get('A', 0)) / 1000.0 # mm to m
    P = float(item_data.get('P', 0)) / 1000.0 # mm to m
    complex_factor = float(item_data.get('complex', 1.0))
    
    # 1. Fetch Catalog Item & Insumos
    # We fetch fresh from DB to avoid frontend tampering with internal logic
    cat_item = db.execute("SELECT * FROM itens_catalogo WHERE id = ?", (cat_id,)).fetchone()
    if not cat_item:
        return 0.0, ["Item não encontrado"]

    insumos = db.execute('''
        SELECT ci.*, e.custo_unitario, e.categoria, e.nome, e.id as original_estoque_id
        FROM catalogo_insumos ci
        JOIN estoque e ON ci.estoque_id = e.id
        WHERE ci.catalogo_id = ?
    ''', (cat_id,)).fetchall()

    rules = get_tier_rules(db, tier_id)

    total_mat_cost = 0.0
    breakdown = []

    # 3. Calculate Material Cost
    if insumos:
        for ins in insumos:
            # Consumption Calculation
            qty = 0.0
            type_calc = ins['tipo_calculo']
            base_qty = float(ins['quantidade'])
            
            if type_calc == 'fixo':
                qty = base_qty
            elif type_calc == 'area':
                qty = (L * A) * base_qty
            elif type_calc == 'volume':
                depth = P if P > 0 else 0.001
                qty = (L * A * depth) * base_qty
            elif type_calc == 'perimetro':
                qty = 2 * (L + A) * base_qty
                
            # Tier Substitution Logic
            category = ins['categoria']
            cost_unit = float(ins['custo_unitario'])
            used_name = ins['nome']
            rule = rules.get(category)
            
            if rule:
                # Apply replacement if item_id is defined
                if rule['item_id']:
                    replacement = db.execute("SELECT nome, custo_unitario FROM estoque WHERE id = ?", (rule['item_id'],)).fetchone()
                    if replacement:
                        cost_unit = float(replacement['custo_unitario'])
                        used_name = replacement['nome'] # + " (Subst.)"
                
                # Apply modifier
                if rule['price_modifier'] != 1.0:
                    cost_unit *= rule['price_modifier']

            item_cost = qty * cost_unit
            total_mat_cost += item_cost
            breakdown.append(f"{used_name}: {qty:.2f} x {cost_unit:.2f} = {item_cost:.2f}")

    else:
        # Fallback for simple items without insumos
        vol = L * A * (P if P > 0 else 0.001)
        base_price = float(cat_item['preco_base'] or 0)
        total_mat_cost = vol * base_price
        breakdown.append(f"Volume Fallback: {vol:.3f}m³ * {base_price}")

    # 4. Labor Cost
    labor_rate_row = db.execute("SELECT value FROM settings WHERE key='valor_hora_fabrica'").fetchone()
    labor_rate = float(labor_rate_row['value']) if labor_rate_row else 70.0
    
    labor_cost = float(cat_item['horas_mo'] or 0) * labor_rate * complex_factor
    breakdown.append(f"Mão de Obra: {float(cat_item['horas_mo'] or 0):.1f}h x {labor_rate} x {complex_factor} = {labor_cost:.2f}")
    
    # 5. Accessories
    acc_cost = 0.0
    if item_data.get('acessorios'):
        for acc in item_data.get('acessorios'):
            acc_id = acc.get('id')
            acc_qty = float(acc.get('qtd', 0))
            
            acc_db = db.execute("SELECT categoria, custo_unitario, nome FROM estoque WHERE id = ?", (acc_id,)).fetchone()
            if acc_db:
                a_cost = float(acc_db['custo_unitario'])
                a_name = acc_db['nome']
                a_cat = acc_db['categoria']
                
                # Check rule
                rule = rules.get(a_cat)
                if rule:
                     if rule['item_id']:
                        rep = db.execute("SELECT nome, custo_unitario FROM estoque WHERE id = ?", (rule['item_id'],)).fetchone()
                        if rep:
                            a_cost = float(rep['custo_unitario'])
                            a_name = rep['nome']
                     if rule.get('price_modifier', 1.0) != 1.0:
                            a_cost *= rule['price_modifier']
                
                item_acc_cost = acc_qty * a_cost
                acc_cost += item_acc_cost
                breakdown.append(f"Acessório {a_name}: {acc_qty} x {a_cost:.2f}")

    return total_mat_cost + labor_cost + acc_cost, breakdown
