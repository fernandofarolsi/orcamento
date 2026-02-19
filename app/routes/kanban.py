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
    try:
        data = request.json
        titulo = data.get('titulo') # Nome do Lead
        client = data.get('client') 
        
        obs = data.get('obs')
        data_json = json.dumps({'obs': obs})
        
        db = get_db()
        db.execute('INSERT INTO cards_kanban (titulo, etapa, client, orcamento_id, data_json) VALUES (?, ?, ?, ?, ?)',
                (titulo, 'Contato', client, None, data_json))
                
        # Auto-create in CRM if not exists
        try:
            crm_exists = db.execute('SELECT id FROM crm_contatos WHERE nome = ?', (titulo,)).fetchone()
            if not crm_exists:
                db.execute('''INSERT INTO crm_contatos (nome, tipo, telefone, origem, observacoes) 
                            VALUES (?, 'lead', ?, 'kanban', ?)''',
                        (titulo, client, obs))
        except Exception as e:
            print(f"Error creating CRM contact from Kanban: {e}")
            # Non-critical, continue

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

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
    
    # 1. Update CRM Contact to 'cliente'
    try:
        db.execute("UPDATE crm_contatos SET tipo = 'cliente' WHERE nome = ?", (client_name,))
    except Exception as e:
        print(f"Error updating CRM contact: {e}")

    # 2. Ensure Client exists in 'clientes' table (legacy compatibility)
    client_id = None
    existing_client = db.execute("SELECT id FROM clientes WHERE nome = ?", (client_name,)).fetchone()
    
    if existing_client:
        client_id = existing_client['id']
    else:
        # Create new client from CRM data or Card data
        try:
            # Try to get phone from CRM
            crm_data = db.execute("SELECT telefone, email FROM crm_contatos WHERE nome = ?", (client_name,)).fetchone()
            phone = crm_data['telefone'] if crm_data else ''
            email = crm_data['email'] if crm_data else ''
            
            cur = db.cursor()
            cur.execute("INSERT INTO clientes (nome, telefone, email, origem) VALUES (?, ?, ?, 'kanban_convert')", 
                        (client_name, phone, email))
            client_id = cur.lastrowid
        except Exception as e:
            print(f"Error enforcing client creation: {e}")

    # 3. Create empty budget
    cur = db.cursor()
    cur.execute('''INSERT INTO orcamentos (client, client_id, status, total, itens_json, created_at, prazo_entrega) 
                   VALUES (?, ?, ?, ?, ?, datetime('now'), ?)''',
                (client_name, client_id, 'Rascunho', 0.0, '[]', 
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
    orcamentos = db.execute('SELECT id, client, client_id, prazo_entrega, data_instalacao, created_at, status FROM orcamentos').fetchall()
    for orc in orcamentos:
        if orc['prazo_entrega']:
            events.append({
                'id': f"orc_{orc['id']}",
                'title': f"Prazo: {orc['client']}",
                'start': orc['prazo_entrega'],
                'type': 'project',
                'description': f"Orçamento #{orc['id']} - {orc['status']}",
                'cli_id': orc['client_id']
            })
        if orc['data_instalacao']:
            events.append({
                'id': f"inst_{orc['id']}",
                'title': f"Instalação: {orc['client']}",
                'start': orc['data_instalacao'],
                'type': 'install',
                'description': f"Instalação confirmada - {orc['client']}",
                'cli_id': orc['client_id']
            })
        if orc['created_at']:
            # Maybe restrict simple 'created_at' to only recent or vital ones to avoid clutter?
            # Keeping it for now as "Visita/Contato" marker
            events.append({
                'id': f"visit_{orc['id']}",
                'title': f"Visita/Contato: {orc['client']}",
                'start': orc['created_at'].split(' ')[0], 
                'type': 'visit',
                'description': f"Primeiro contato/Visita técnica",
                'cli_id': orc['client_id']
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
        
    # 3. CRM Activities (NEW)
    activities = db.execute("SELECT * FROM crm_activities").fetchall()
    for act in activities:
        # Determine color/type mapping
        # types: note, visit, meeting, call
        etype = 'visit' # default purple for unknown
        if act['activity_type'] == 'note': etype = 'note'
        elif act['activity_type'] == 'visit': etype = 'visit'
        elif act['activity_type'] == 'meeting': etype = 'visit'
        
        # If pending or future? 
        # Show all for history? Or only future? 
        # Calendar usually shows everything.
        
        # Check if date exists (some notes might not have scheduled date, only created_at)
        # We use scheduled_at if available, else created_at
        date_str = act['scheduled_at'] if act['scheduled_at'] else act['created_at']
        if date_str:
            events.append({
                'id': f"act_{act['id']}",
                'title': act['title'],
                'start': date_str, # Return full DATETIME for frontend sorting
                'type': etype,
                'description': act['description'],
                'cli_id': act['client_id']
            })

    # Final Sort by Start Date
    events.sort(key=lambda x: x['start'])
    return jsonify(events)

@bp.route('/api/kanban/activity', methods=['POST'])
@jwt_required()
def add_kanban_activity():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    title = data.get('title')
    act_type = data.get('type', 'note')
    date_iso = data.get('date') # YYYY-MM-DD
    client_name = data.get('client_name')
    
    # Try to find client_id by text if provided
    client_id = None
    if client_name:
        # Simple lookup
        cli = db.execute("SELECT id FROM clientes WHERE nome LIKE ?", (f"%{client_name}%",)).fetchone()
        if cli:
            client_id = cli['id']
            
    # Insert
    # We use 'scheduled_at' for the calendar date
    # Format date_iso to datetime str if needed
    time_str = data.get('time', '09:00')
    scheduled_at = f"{date_iso} {time_str}:00" if date_iso else None
    
    db.execute('''INSERT INTO crm_activities (client_id, title, description, activity_type, scheduled_at, created_by, created_at) 
                  VALUES (?, ?, ?, ?, ?, ?, datetime('now'))''', 
               (client_id, title, f"Agendado via Calendário. Cliente: {client_name or 'N/A'}", act_type, scheduled_at, user_id))
    db.commit()
    
    # Log
    log_audit(user_id, 'CREATE_ACTIVITY', f"Created activity '{title}' for date {date_iso}")
    
    return jsonify({'success': True})
