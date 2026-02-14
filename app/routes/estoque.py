from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
from app.scraper import run_scraping_job, raspador_site

bp = Blueprint('estoque', __name__)

@bp.route('/estoque')
@jwt_required()
def estoque():
    db = get_db()
    
    # Check if price_groups table exists
    try:
        db.execute('SELECT 1 FROM price_groups LIMIT 1')
        has_price_groups = True
    except:
        has_price_groups = False
        
    items = db.execute('SELECT * FROM estoque').fetchall()
    
    price_groups = []
    if has_price_groups:
        price_groups = db.execute('SELECT * FROM price_groups').fetchall()
        
    return render_template('estoque.html', items=items, price_groups=price_groups)

@bp.route('/catalogo')
@jwt_required()
def catalogo():
    return render_template('catalogo.html')

@bp.route('/api/estoque', methods=['GET'])
@jwt_required()
def api_estoque_list():
    db = get_db()
    items = db.execute('SELECT * FROM estoque').fetchall()
    return jsonify([dict(item) for item in items])

@bp.route('/api/estoque', methods=['POST'])
@jwt_required()
def api_estoque_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    try:
        db.execute('''
            INSERT INTO estoque (nome, categoria, unidade, quantidade, custo_unitario, margem_lucro, preco_venda, 
                                 minimo, localizacao, url_madeiranit, url_leomadeiras, url_madeverde)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['nome'], data.get('categoria'), data.get('unidade'), 
            data.get('quantidade', 0), data.get('custo_unitario', 0), 
            data.get('margem_lucro', 0.35), data.get('preco_venda', 0),
            data.get('minimo', 5), data.get('localizacao'),
            data.get('url_madeiranit'), data.get('url_leomadeiras'), data.get('url_madeverde')
        ))
        db.commit()
        log_audit(user_id, 'ESTOQUE_CREATE', f"Created item: {data['nome']}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/estoque/<int:id>', methods=['DELETE'])
@jwt_required()
def api_estoque_delete(id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM estoque WHERE id = ?', (id,))
    db.commit()
    log_audit(user_id, 'ESTOQUE_DELETE', f"Deleted item {id}")
    return jsonify({'success': True})

@bp.route('/api/estoque/<int:id>', methods=['PUT'])
@jwt_required()
def api_estoque_update(id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    # Basic Update logic (simplified for brevity, assume all fields or selective)
    # The original app likely checked for specific fields.
    # We will assume data contains fields to update.
    
    fields = ['nome', 'categoria', 'unidade', 'quantidade', 'custo_unitario', 'margem_lucro', 'preco_venda', 'minimo', 'localizacao', 'url_madeiranit', 'url_leomadeiras', 'url_madeverde', 'price_strategy', 'price_group_id']
    
    updates = []
    params = []
    
    for field in fields:
        if field in data:
            updates.append(f"{field} = ?")
            params.append(data[field])
            
    if not updates:
        return jsonify({'success': True})
        
    params.append(id)
    
    try:
        db.execute(f'UPDATE estoque SET {", ".join(updates)} WHERE id = ?', params)
        db.commit()
        log_audit(user_id, 'ESTOQUE_UPDATE', f"Updated item {id}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/estoque/raspar-individual', methods=['POST'])
@jwt_required()
def api_estoque_raspar_individual():
    user_id = get_jwt_identity()
    data = request.json
    item_id = data.get('item_id')
    
    if not item_id:
        return jsonify({'success': False, 'error': 'ID do item não fornecido'}), 400
    
    db = get_db()
    item = db.execute('SELECT * FROM estoque WHERE id = ?', (item_id,)).fetchone()
    
    if not item:
        return jsonify({'success': False, 'error': 'Item não encontrado'}), 404
    
    try:
        urls = {
            'madeiranit': item['url_madeiranit'],
            'leomadeiras': item['url_leomadeiras'],
            'madeverde': item['url_madeverde']
        }
        
        precos_encontrados = {}
        updates = []
        params = []
        
        for source, url in urls.items():
            if url:
                novos_items = raspador_site(source, url_override=url) 
                if novos_items:
                    novo_preco = novos_items[0]['preco']
                    precos_encontrados[source] = novo_preco
                    updates.append(f"preco_{source} = ?")
                    params.append(novo_preco)

        if not precos_encontrados:
             return jsonify({'success': False, 'error': 'Nenhuma URL válida ou falha na raspagem de todas as fontes'}), 500

        strategy = item['price_strategy'] if item.get('price_strategy') else 'auto_max'
        novo_custo = item['custo_unitario'] 
        site_escolhido = item['site_origem']

        if strategy == 'auto_max':
            if precos_encontrados:
                max_source = max(precos_encontrados, key=precos_encontrados.get)
                novo_custo = precos_encontrados[max_source]
                site_escolhido = max_source
        elif strategy in precos_encontrados:
            novo_custo = precos_encontrados[strategy]
            site_escolhido = strategy
        
        updates.append("custo_unitario = ?")
        params.append(novo_custo)
        updates.append("site_origem = ?")
        params.append(site_escolhido)
        updates.append("last_update = datetime('now')")
        params.append(item_id)
        
        query = f"UPDATE estoque SET {', '.join(updates)} WHERE id = ?"
        db.execute(query, params)
        db.commit()
        
        log_audit(user_id, 'ESTOQUE_RASPAGEM_SMART', 
                f"Item {item['nome']} (ID {item_id}) atualizado. Strat: {strategy}, Novo Custo: {novo_custo}, Detalhes: {precos_encontrados}")
        
        return jsonify({
            'success': True,
            'preco': novo_custo,
            'site': site_escolhido,
            'detalhes': precos_encontrados,
            'strategy': strategy
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/estoque/ids-para-raspar', methods=['GET'])
@jwt_required()
def api_estoque_ids_para_raspar():
    db = get_db()
    query = '''
        SELECT id FROM estoque 
        WHERE (url_madeiranit IS NOT NULL AND url_madeiranit != '')
           OR (url_leomadeiras IS NOT NULL AND url_leomadeiras != '')
           OR (url_madeverde IS NOT NULL AND url_madeverde != '')
    '''
    rows = db.execute(query).fetchall()
    ids = [row[0] for row in rows]
    return jsonify({'ids': ids, 'count': len(ids)})

@bp.route('/api/estoque/raspar', methods=['POST'])
@jwt_required()
def api_estoque_raspar():
    user_id = get_jwt_identity()
    data = request.json
    target = data.get('site', 'all')
    stats = run_scraping_job(target)
    log_audit(user_id, 'ESTOQUE_RASPAGEM', f"Scraped {target}. U:{stats['updated']} C:{stats['created']}")
    return jsonify({'success': True, 'stats': stats})

@bp.route('/api/price-groups', methods=['GET'])
@jwt_required()
def api_price_groups_list():
    db = get_db()
    groups = db.execute("SELECT * FROM price_groups ORDER BY name").fetchall()
    return jsonify([dict(g) for g in groups])

@bp.route('/api/price-groups', methods=['POST'])
@jwt_required()
def api_price_groups_create():
    data = request.json
    name = data.get('name')
    color = data.get('color', '#333333')
    
    if not name: return jsonify({'error': 'Name required'}), 400
    
    db = get_db()
    try:
        db.execute("INSERT INTO price_groups (name, color) VALUES (?, ?)", (name, color))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/price-groups/<int:id>', methods=['PUT'])
@jwt_required()
def api_price_groups_update(id):
    data = request.json
    name = data.get('name')
    color = data.get('color')
    
    db = get_db()
    db.execute("UPDATE price_groups SET name=?, color=? WHERE id=?", (name, color, id))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/price-groups/<int:id>', methods=['DELETE'])
@jwt_required()
def api_price_groups_delete(id):
    db = get_db()
    # Untag items
    db.execute("UPDATE estoque SET price_group_id = NULL WHERE price_group_id = ?", (id,))
    db.execute("DELETE FROM price_groups WHERE id = ?", (id,))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/estoque/acessorios', methods=['GET'])
@jwt_required()
def api_estoque_acessorios():
    db = get_db()
    items = db.execute('SELECT * FROM estoque WHERE is_acessorio = 1 ORDER BY nome').fetchall()
    return jsonify([dict(ix) for ix in items])
