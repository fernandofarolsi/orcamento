from flask import Blueprint, request, jsonify
from app.database import get_db
import traceback

bp = Blueprint('whatsapp_webhook', __name__)

@bp.route('/api/waha/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Waha sends various events, we care about 'message.upsert' or 'message'
    # Structure depends on Waha version/engine
    # Assuming standard Waha payload
    
    event = data.get('event')
    payload = data.get('payload', {})
    
    if event == 'message.upsert' or event == 'message':
        handle_message(payload)
        
    return jsonify({'status': 'ok'})

def handle_message(msg):
    # msg structure: {from: '123@s.whatsapp.net', body: 'text', pushName: 'Name', ...}
    try:
        remote_jid = msg.get('from')
        if not remote_jid or '@g.us' in remote_jid: # Ignore groups for now
            return
            
        # Ignore status updates
        if remote_jid == 'status@broadcast':
            return
            
        # Ignore messages from me (if Waha echoes them, though usually has 'fromMe': true)
        if msg.get('fromMe'):
            return

        db = get_db()
        
        # 1. UPSERT Chat
        chat = db.execute("SELECT * FROM whatsapp_chats WHERE remote_jid = ?", (remote_jid,)).fetchone()
        
        push_name = msg.get('pushName') or msg.get('_data', {}).get('notifyName') or remote_jid.split('@')[0]
        
        if not chat:
            db.execute('''INSERT INTO whatsapp_chats 
                        (remote_jid, name, last_message_at, unread_count, status, camila_active)
                        VALUES (?, ?, datetime('now'), 1, 'open', 1)''', (remote_jid, push_name))
            chat_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        else:
            chat_id = chat['id']
            db.execute('''UPDATE whatsapp_chats 
                          SET last_message_at = datetime('now'), unread_count = unread_count + 1, name = ? 
                          WHERE id = ?''', (push_name, chat_id))
        
        # 2. INSERT Message
        body = msg.get('body')
        if not body and msg.get('type') == 'image':
             body = '[Imagem]'
             
        waha_id = msg.get('id', {}).get('id') if isinstance(msg.get('id'), dict) else msg.get('id')
        
        db.execute('''INSERT OR IGNORE INTO whatsapp_messages 
                      (chat_id, sender, content, status, timestamp, waha_msg_id)
                      VALUES (?, 'user', ?, 'received', datetime('now'), ?)''',
                   (chat_id, body, waha_id))
        
        db.commit()
        
        # 3. Trigger AI (Async ideally, but sync for MVP)
        # Check if AI is active
        # We need to reload chat status in case it was updated
        chat = db.execute("SELECT camila_active FROM whatsapp_chats WHERE id = ?", (chat_id,)).fetchone()
        if chat['camila_active'] and body:
             from app.services import camila_agent
             camila_agent.process_message(chat_id, body)
             
    except Exception as e:
        print(f"Error handling webhook: {e}")
        traceback.print_exc()
