from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from app.database import get_db
from app.services import waha

bp = Blueprint('whatsapp', __name__)

@bp.route('/whatsapp')
@jwt_required()
def index():
    return render_template('whatsapp.html')

@bp.route('/api/whatsapp/status')
@jwt_required()
def api_status():
    return jsonify(waha.get_status())

@bp.route('/api/whatsapp/qr')
@jwt_required()
def api_qr():
    qr = waha.get_qr_code()
    return jsonify({'qrcode': qr})

@bp.route('/api/whatsapp/chats')
@jwt_required()
def api_chats():
    db = get_db()
    rows = db.execute("SELECT * FROM whatsapp_chats ORDER BY last_message_at DESC").fetchall()
    return jsonify([dict(row) for row in rows])

@bp.route('/api/whatsapp/chats/<int:chat_id>/messages')
@jwt_required()
def api_messages(chat_id):
    db = get_db()
    rows = db.execute("SELECT * FROM whatsapp_messages WHERE chat_id = ? ORDER BY timestamp ASC", (chat_id,)).fetchall()
    # Mark as read
    db.execute("UPDATE whatsapp_chats SET unread_count = 0 WHERE id = ?", (chat_id,))
    db.commit()
    return jsonify([dict(row) for row in rows])

@bp.route('/api/whatsapp/chats/<int:chat_id>/toggle-ai', methods=['POST'])
@jwt_required()
def api_toggle_ai(chat_id):
    data = request.json
    active = data.get('active', True)
    db = get_db()
    db.execute("UPDATE whatsapp_chats SET camila_active = ? WHERE id = ?", (active, chat_id))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/whatsapp/chats/<int:chat_id>/send', methods=['POST'])
@jwt_required()
def api_send(chat_id):
    data = request.json
    text = data.get('text')
    if not text: return jsonify({'error': 'No text'}), 400
    
    db = get_db()
    chat = db.execute("SELECT * FROM whatsapp_chats WHERE id = ?", (chat_id,)).fetchone()
    if not chat: return jsonify({'error': 'Chat not found'}), 404
    
    # Check if Simulation
    is_sim = dict(chat).get('is_simulation', 0)
    
    if not is_sim:
        # Send via Waha (Real)
        try:
            res = waha.send_message(chat['remote_jid'], text)
            if 'error' in res: return jsonify(res), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Save to DB (Me/Agent)
    db.execute("INSERT INTO whatsapp_messages (chat_id, sender, content, status, timestamp) VALUES (?, 'agent', ?, 'sent', datetime('now'))",
               (chat_id, text))
    db.execute("UPDATE whatsapp_chats SET last_message_at = datetime('now') WHERE id = ?", (chat_id,))
    db.commit()
    
    # Trigger AI Response if Active
    if chat['camila_active']:
        try:
            from app.services import camila_agent
            # Async processing ideally, but sync for now for simplicity/simulator
            camila_agent.process_message(chat_id, text, is_simulation=is_sim)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f"AI Error: {str(e)}"}), 500
    
    return jsonify({'success': True})

@bp.route('/api/whatsapp/simulate/create', methods=['POST'])
@jwt_required()
def api_simulate_create():
    db = get_db()
    
    # Create a fake chat
    import random
    fake_id = random.randint(1000, 9999)
    remote_jid = f"55119{fake_id}@s.whatsapp.net"
    name = f"Simulação {fake_id}"
    
    cur = db.cursor()
    cur.execute('''INSERT INTO whatsapp_chats (remote_jid, name, unread_count, camila_active, is_simulation, last_message_at) 
                   VALUES (?, ?, 0, 1, 1, datetime('now'))''', (remote_jid, name))
    chat_id = cur.lastrowid
    
    # Initial Message from "User"
    db.execute("INSERT INTO whatsapp_messages (chat_id, sender, content, status, timestamp) VALUES (?, 'user', 'Olá, gostaria de um orçamento.', 'received', datetime('now'))",
               (chat_id,))
               
    db.commit()
    return jsonify({'success': True, 'chat_id': chat_id})
