import os
import requests
import base64
from app.database import get_db

def get_config():
    # Prioritiza variáveis de ambiente (.env) por segurança
    env_url = os.getenv('WAHA_API_URL')
    env_key = os.getenv('WAHA_API_KEY')
    
    if env_url:
        return {'url': env_url, 'key': env_key or ''}

    # Fallback para o Banco de Dados (Legado/UI)
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'waha_%'").fetchall()
    config = {row['key']: row['value'] for row in rows}
    return {
        'url': config.get('waha_api_url', 'http://localhost:3000'),
        'key': config.get('waha_api_key', '')
    }

def get_status():
    conf = get_config()
    try:
        url = f"{conf['url']}/api/sessions/default"
        headers = {'X-Api-Key': conf['key']} if conf['key'] else {}
        r = requests.get(url, headers=headers, timeout=2)
        if r.status_code == 200:
            return r.json()
        return {'status': 'ERROR', 'details': r.text}
    except Exception as e:
        return {'status': 'OFFLINE', 'details': str(e)}

def get_qr_code():
    conf = get_config()
    try:
        url = f"{conf['url']}/api/default/auth/qr"
        headers = {'X-Api-Key': conf['key']} if conf['key'] else {}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if 'qrcode' in data:
                return data['qrcode'] # Base64
        return None
    except:
        return None

def send_message(chat_id, text):
    conf = get_config()
    try:
        url = f"{conf['url']}/api/sendText"
        headers = {'Content-Type': 'application/json'}
        if conf['key']: headers['X-Api-Key'] = conf['key']
        
        payload = {
            "session": "default",
            "chatId": chat_id,
            "text": text
        }
        
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        return r.json()
    except Exception as e:
        return {'error': str(e)}
