from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
from datetime import datetime

bp = Blueprint('client_profile', __name__)

@bp.route('/cliente/<int:id>')
@jwt_required()
def client_profile(id):
    db = get_db()
    
    # 1. Client Info
    client = db.execute('SELECT * FROM clientes WHERE id = ?', (id,)).fetchone()
    if not client:
        return "Cliente não encontrado", 404
    
    client = dict(client)
    # Mocking Tags for now (later can be a real table)
    client['tags'] = ['Cliente'] 
    if client.get('origem'): client['tags'].append(client['origem'])
    
    # Mocking Total Spent (later sum from orcamentos)
    total_spent = db.execute("SELECT SUM(total) as total FROM orcamentos WHERE client_id = ? AND status IN ('Aprovado', 'Faturado', 'Concluído')", (id,)).fetchone()
    client['total_spent'] = f"R$ {total_spent['total'] or 0:.2f}"
    
    # Avatar (Gravatar or UI Avatars)
    client_name = client.get('name') or client.get('nome', 'Cliente')
    client['avatar'] = f"https://ui-avatars.com/api/?name={client_name}&background=random"

    # 2. Timeline (Activities + System Events)
    timeline = []
    
    # A. CRM Activities
    activities = db.execute("SELECT * FROM crm_activities WHERE client_id = ? ORDER BY created_at DESC", (id,)).fetchall()
    for act in activities:
        timeline.append({
            'source': 'activity',
            'type': act['activity_type'] or 'note',
            'title': act['title'],
            'desc': act['description'],
            'date': act['created_at'],
            'user': 'Sistema' # TODO: Join with users table
        })
        
    # B. Orçamentos Events
    orcamentos = db.execute("SELECT * FROM orcamentos WHERE client_id = ? ORDER BY created_at DESC", (id,)).fetchall()
    budgets = []
    for orc in orcamentos:
        budgets.append(dict(orc))
        timeline.append({
            'source': 'system',
            'type': 'budget',
            'title': f"Orçamento #{orc['id']} Criado",
            'desc': f"Status: {orc['status']} - Total: R$ {orc['total']:.2f}",
            'date': orc['created_at'],
            'user': 'Sistema'
        })
        
    # Sort Timeline
    timeline.sort(key=lambda x: x['date'], reverse=True)
        
    return render_template('client_profile.html', client=client, timeline=timeline, budgets=budgets)

@bp.route('/api/cliente/<int:id>/activity', methods=['POST'])
@jwt_required()
def add_activity(id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    title = data.get('title')
    desc = data.get('desc')
    act_type = data.get('type', 'note')
    
    db.execute('''INSERT INTO crm_activities (client_id, title, description, activity_type, created_by, created_at) 
                  VALUES (?, ?, ?, ?, ?, datetime('now'))''', 
               (id, title, desc, act_type, user_id))
    db.commit()
    return jsonify({'success': True})
@bp.route('/api/cliente/<int:id>/ai-summary', methods=['GET'])
@jwt_required()
def get_ai_summary(id):
    import sqlite3
    import os
    import json
    
    db = get_db()
    client = db.execute('SELECT whatsapp FROM clientes WHERE id = ?', (id,)).fetchone()
    if not client or not client['whatsapp']:
        return jsonify({'summary': None})
    
    # Try to find a chat for this client
    # Clean the number to search
    whatsapp_clean = ''.join(filter(str.isdigit, client['whatsapp']))
    if not whatsapp_clean:
        return jsonify({'summary': None})
        
    chat = db.execute("SELECT id FROM whatsapp_chats WHERE remote_jid LIKE ? OR name LIKE ?", 
                      (f'%{whatsapp_clean}%', f'%{whatsapp_clean}%')).fetchone()
    
    if not chat:
        return jsonify({'summary': None})
    
    chat_id = str(chat['id'])
    
    # Query Agno Memory
    db_path = os.path.join(os.path.dirname(__file__), '../camila_agent.db')
    if not os.path.exists(db_path):
        return jsonify({'summary': None})
        
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT summary FROM agent_sessions WHERE session_id = ?", (chat_id,)).fetchone()
        conn.close()
        
        if row and row['summary']:
            summary_data = json.loads(row['summary'])
            # summary_data format from Agno: {"content": "...", "created_at": ...} or similar
            # Based on Agno source, SessionSummary has a 'summary' or 'content' field?
            # Let's check AgentSession.from_dict which calls SessionSummary.from_dict
            
            # Usually Agno summary JSON has the text in "content" or "summary"
            summary_text = summary_data.get('content') or summary_data.get('summary') or str(summary_data)
            return jsonify({'summary': summary_text})
    except Exception as e:
        print(f"Error AI Summary: {e}")
        
    return jsonify({'summary': None})
