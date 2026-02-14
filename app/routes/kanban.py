from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
import json
from datetime import datetime, timedelta

bp = Blueprint('kanban', __name__)

@bp.route('/kanban')
@jwt_required()
def kanban():
    db = get_db()
    cards = db.execute('SELECT * FROM cards_kanban').fetchall()
    return render_template('kanban.html', cards=cards)

@bp.route('/api/kanban/update', methods=['POST'])
@jwt_required()
def api_kanban_update():
    data = request.json
    card_id = data.get('id')
    nova_etapa = data.get('etapa')
    db = get_db()
    db.execute('UPDATE cards_kanban SET etapa = ? WHERE id = ?', (nova_etapa, card_id))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/kanban/card', methods=['POST'])
@jwt_required()
def api_kanban_create():
    data = request.json
    titulo = data.get('titulo') # Nome do Lead
    client = data.get('client') 
    
    obs = data.get('obs')
    data_json = json.dumps({'obs': obs})
    
    db = get_db()
    db.execute('INSERT INTO cards_kanban (titulo, etapa, client, orcamento_id, data_json) VALUES (?, ?, ?, ?, ?)',
               (titulo, 'Contato', client, None, data_json))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/kanban/card/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def api_kanban_card_manage(id):
    user_id = get_jwt_identity()
    db = get_db()
    
    if request.method == 'DELETE':
        db.execute('DELETE FROM cards_kanban WHERE id=?', (id,))
        db.commit()
        log_audit(user_id, 'DELETE_CARD', f"Deleted Kanban Card #{id}")
        return jsonify({'success': True})
        
    if request.method == 'PUT':
        data = request.json
        titulo = data.get('titulo')
        client = data.get('client')
        obs = data.get('obs')
        
        data_json = json.dumps({'obs': obs})
        
        db.execute('UPDATE cards_kanban SET titulo=?, client=?, data_json=? WHERE id=?',
                   (titulo, client, data_json, id))
        db.commit()
        log_audit(user_id, 'UPDATE_CARD', f"Updated Kanban Card #{id}")
        return jsonify({'success': True})

@bp.route('/api/kanban/convert/<int:id>', methods=['POST'])
@jwt_required()
def api_kanban_convert(id):
    user_id = get_jwt_identity()
    db = get_db()
    
    card = db.execute('SELECT * FROM cards_kanban WHERE id=?', (id,)).fetchone()
    if not card: return jsonify({'error': 'Card not found'}), 404
    
    if card['orcamento_id']:
        return jsonify({'error': 'Card already has budget'}), 400
        
    # Create Budget
    data_json = json.loads(card['data_json']) if card['data_json'] else {}
    
    client_name = card['titulo']
    
    # Create empty budget
    cur = db.cursor()
    cur.execute('''INSERT INTO orcamentos (client, status, total, itens_json, created_at, prazo_entrega) 
                   VALUES (?, ?, ?, ?, datetime('now'), ?)''',
                (client_name, 'Rascunho', 0.0, '[]', 
                 (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')))
    orcamento_id = cur.lastrowid
    
    # Link Card
    db.execute('UPDATE cards_kanban SET orcamento_id=?, etapa=? WHERE id=?', (orcamento_id, 'Orçamento', id))
    
    log_audit(user_id, 'LEAD_CONVERT', f"Converted Lead #{id} to Budget #{orcamento_id}")
    db.commit()
    
    return jsonify({'success': True, 'orcamento_id': orcamento_id})

@bp.route('/api/calendar/events', methods=['GET'])
@jwt_required()
def api_calendar_events():
    db = get_db()
    events = []
    
    # Internal Events only for now (Google Auth removed/simplified)
    # 1. Orçamentos (Prazos, Instalação, Visitas)
    orcamentos = db.execute('SELECT id, client, prazo_entrega, data_instalacao, created_at, status FROM orcamentos').fetchall()
    for orc in orcamentos:
        if orc['prazo_entrega']:
            events.append({
                'id': f"orc_{orc['id']}",
                'title': f"Prazo: {orc['client']}",
                'start': orc['prazo_entrega'],
                'type': 'project',
                'description': f"Orçamento #{orc['id']} - {orc['status']}"
            })
        if orc['data_instalacao']:
            events.append({
                'id': f"inst_{orc['id']}",
                'title': f"Instalação: {orc['client']}",
                'start': orc['data_instalacao'],
                'type': 'install',
                'description': f"Instalação confirmada - {orc['client']}"
            })
        if orc['created_at']:
            events.append({
                'id': f"visit_{orc['id']}",
                'title': f"Visita/Contato: {orc['client']}",
                'start': orc['created_at'].split(' ')[0], 
                'type': 'visit',
                'description': f"Primeiro contato/Visita técnica"
            })

    # 2. Financeiro (Contas)
    contas = db.execute('SELECT id, descricao, valor, tipo, vencimento, status FROM contas WHERE status="pendente"').fetchall()
    for conta in contas:
        evt_type = 'receber' if conta['tipo'] == 'receber' else 'payable'
        title_prefix = 'Receber' if conta['tipo'] == 'receber' else 'Pagar'
        
        events.append({
            'id': f"fin_{conta['id']}",
            'title': f"{title_prefix}: {conta['descricao']}",
            'start': conta['vencimento'],
            'type': evt_type,
            'description': f"R$ {conta['valor']:.2f} - {conta['status']}"
        })
        
    return jsonify(events)
