from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
import json

bp = Blueprint('catalogo', __name__)

@bp.route('/catalogo')
@jwt_required()
def catalogo():
    return render_template('catalogo.html')

@bp.route('/api/catalogo', methods=['GET'])
@jwt_required()
def api_catalogo_list():
    db = get_db()
    items = db.execute('''
        SELECT c.*, 
               (SELECT json_group_array(json_object(
                   'id', ci.id, 
                   'estoque_id', ci.estoque_id, 
                   'quantidade', ci.quantidade, 
                   'tipo_calculo', ci.tipo_calculo,
                   'nome', e.nome,
                   'custo_unitario', e.custo_unitario
               ))
               FROM catalogo_insumos ci
               JOIN estoque e ON ci.estoque_id = e.id
               WHERE ci.catalogo_id = c.id) as insumos
        FROM itens_catalogo c
        ORDER BY c.nome
    ''').fetchall()
    
    result = []
    for item in items:
        d = dict(item)
        if d['insumos']:
            try:
                d['insumos'] = json.loads(d['insumos'])
            except:
                d['insumos'] = []
        else:
            d['insumos'] = []
        result.append(d)
        
    return jsonify(result)

@bp.route('/api/catalogo', methods=['POST'])
@jwt_required()
def api_catalogo_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    cur = db.cursor()
    cur.execute('INSERT INTO itens_catalogo (nome, preco_base, fator_consumo, dims_padrao, estoque_id, categoria, horas_mo, imagem_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
               (data.get('nome'), data.get('preco_base'), data.get('fator_consumo'), data.get('dims_padrao'), 
                data.get('estoque_id'), data.get('categoria'), data.get('horas_mo', 0), data.get('imagem_url')))
    cat_id = cur.lastrowid
    
    if data.get('insumos'):
        for ins in data.get('insumos'):
            db.execute('INSERT INTO catalogo_insumos (catalogo_id, estoque_id, quantidade, tipo_calculo) VALUES (?, ?, ?, ?)',
                       (cat_id, ins['estoque_id'], ins['quantidade'], ins['tipo_calculo']))
    
    db.commit()
    log_audit(user_id, 'CAT_CREATE', f"Created item: {data.get('nome')}")
    return jsonify({'success': True, 'id': cat_id})

@bp.route('/api/catalogo/<int:id>', methods=['PUT'])
@jwt_required()
def api_catalogo_update(id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    db.execute('UPDATE itens_catalogo SET nome=?, preco_base=?, fator_consumo=?, dims_padrao=?, estoque_id=?, categoria=?, horas_mo=?, imagem_url=? WHERE id=?',
               (data.get('nome'), data.get('preco_base'), data.get('fator_consumo'), data.get('dims_padrao'), 
                data.get('estoque_id'), data.get('categoria'), data.get('horas_mo', 0), data.get('imagem_url'), id))
    
    db.execute('DELETE FROM catalogo_insumos WHERE catalogo_id=?', (id,))
    
    if data.get('insumos'):
        for ins in data.get('insumos'):
            db.execute('INSERT INTO catalogo_insumos (catalogo_id, estoque_id, quantidade, tipo_calculo) VALUES (?, ?, ?, ?)',
                       (id, ins['estoque_id'], ins['quantidade'], ins['tipo_calculo']))
            
    db.commit()
    log_audit(user_id, 'CAT_UPDATE', f"Updated item #{id}")
    return jsonify({'success': True})

@bp.route('/api/catalogo/<int:id>', methods=['DELETE'])
@jwt_required()
def api_catalogo_delete(id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM itens_catalogo WHERE id=?', (id,))
    db.execute('DELETE FROM catalogo_insumos WHERE catalogo_id=?', (id,))
    db.commit()
    log_audit(user_id, 'CAT_DELETE', f"Deleted item #{id}")
    return jsonify({'success': True})
