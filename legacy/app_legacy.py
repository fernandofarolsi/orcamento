import json
import time
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, g, make_response, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from asgiref.wsgi import WsgiToAsgi
import os
from datetime import datetime, timedelta
import threading
import random

import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env

# Initialize Flask app as 'flask_app' so we can expose the ASGI wrapper as 'app'
flask_app = Flask(__name__)

# Context Processor to inject company settings into all templates
@flask_app.context_processor
def inject_company_settings():
    try:
        db = get_db()
        # Fetch all settings starting with 'empresa_'
        rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'empresa_%'").fetchall()
        company = {row['key']: row['value'] for row in rows}
        
        # Ensure defaults if DB is empty or missing keys
        defaults = {
            'empresa_nome': 'Adore Marcenaria',
            'empresa_logo_url': '/static/logo.jpg',
            'empresa_cnpj': '',
            'empresa_endereco': '',
            'empresa_telefone': '',
            'empresa_email': ''
        }
        # Merge defaults with DB values
        final_company = {**defaults, **company}
        return dict(company=final_company)
    except Exception as e:
        # Fallback in case of DB error (e.g. during init)
        print(f"Error injecting company settings: {e}")
        return dict(company={
            'empresa_nome': 'Adore Marcenaria',
            'empresa_logo_url': '/static/logo.jpg'
        })

flask_app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-do-not-use-in-prod')
flask_app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-do-not-use-in-prod')
flask_app.config['JWT_TOKEN_LOCATION'] = ['cookies']
flask_app.config['JWT_TOKEN_LOCATION'] = ['cookies']
flask_app.config['JWT_COOKIE_CSRF_PROTECT'] = False # MVP shortcut
flask_app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)

@flask_app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(flask_app.config['UPLOAD_FOLDER'], filename)

@flask_app.route('/api/upload', methods=['POST'])
@jwt_required()
def api_upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    client_name = request.form.get('client_name', 'cliente_desconhecido')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        # Create a safe filename based on client name and timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_client = secure_filename(client_name).lower()
        if not safe_client:
            safe_client = 'upload'
            
        # Extract extension (keep original or default to png if blob)
        ext = 'png'
        if '.' in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            
        filename = f"{safe_client}_{timestamp}.{ext}"
        filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Return the URL
        url = url_for('uploaded_file', filename=filename)
        return jsonify({'url': url})

jwt = JWTManager(flask_app)

@flask_app.template_filter('count_items')
def count_json_items(json_str):
    if not json_str: return 0
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            # New format: List of Groups [{'name': 'Sala', 'items': [...]}]
            if len(data) > 0 and isinstance(data[0], dict) and 'items' in data[0]:
                count = 0
                for group in data:
                    count += len(group.get('items', []))
                return count
            # Old format: List of Items directly
            return len(data)
        return 0
    except:
        return 0

@flask_app.template_filter('date_format')
def date_format_filter(value, include_time=False):
    if not value: return ''
    # Assume standard SQLite format: YYYY-MM-DD HH:MM:SS
    # Return DD/MM/YYYY [HH:MM]
    try:
        if isinstance(value, str):
            # Split date and time
            parts = value.split(' ')
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else ''
            
            y, m, d = date_part.split('-')
            formatted_date = f"{d}/{m}/{y}"
            
            if include_time and time_part:
                # Take only HH:MM
                return f"{formatted_date} {time_part[:5]}"
            return formatted_date
        return value
    except:
        return value

STATUS_COLORS = {
    'Rascunho': '#6c757d',
    'Enviado': '#17a2b8',
    'Negociação': '#ffc107',
    'Aprovado': '#28a745',
    'Faturado': '#155724',
    'Perdido': '#dc3545'
}

@flask_app.template_filter('status_color')
def status_color_filter(status):
    return STATUS_COLORS.get(status, '#007bff')

@flask_app.template_filter('from_json')
def from_json_filter(value):
    if not value: return {}
    try:
        return json.loads(value)
    except:
        return {}

@jwt.unauthorized_loader
def custom_unauthorized_response(_err):
    return redirect(url_for('login'))

@jwt.expired_token_loader
def custom_expired_token_response(_hdr, _payload):
    return redirect(url_for('login'))

@jwt.invalid_token_loader
def custom_invalid_token_response(_err):
    return redirect(url_for('login'))

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (identity,)).fetchone()
    return user # Returns Row object or None

@flask_app.context_processor
def inject_user():
    from flask_jwt_extended import current_user
    return dict(current_user=current_user)

DATABASE = 'app.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@flask_app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with flask_app.app_context():
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin', 'admin')")
            db.commit()
            print("Admin user created.")
        except sqlite3.IntegrityError:
            pass
            
        # Default Settings
        db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        defaults = [
            ('capacidade_horas_mes', '160'),
            ('valor_hora_fabrica', '70.00'),
            ('raspagem_ativa', 'false'),
            ('raspagem_hora', '02:00'),
            ('empresa_nome', 'Adore Marcenaria'),
            ('empresa_cnpj', '00.000.000/0001-00'),
            ('empresa_endereco', 'Endereço da Empresa, Cidade - UF'),
            ('empresa_telefone', '(00) 0000-0000'),
            ('empresa_email', 'contato@empresa.com'),
            ('empresa_site', 'www.empresa.com'),
            ('empresa_logo_url', '/static/logo.jpg'),
            ('contrato_template', '''<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Contrato - [CLIENTE]</title>
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 40px; color: #333; line-height: 1.6; }
        .header { text-align: center; margin-bottom: 40px; border-bottom: 2px solid #333; padding-bottom: 20px; }
        .header img { max-width: 200px; }
        .contract-title { font-size: 24px; font-weight: bold; text-transform: uppercase; margin: 20px 0; }
        .section-title { font-size: 16px; font-weight: bold; text-transform: uppercase; margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
        .content { font-size: 14px; text-align: justify; }
        .clause { margin-bottom: 15px; }
        .clause-title { font-weight: bold; text-decoration: underline; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #f4f4f4; text-transform: uppercase; }
        .signatures { margin-top: 80px; display: flex; justify-content: space-between; page-break-inside: avoid; }
        .sig-block { width: 45%; text-align: center; border-top: 1px solid #333; padding-top: 10px; }
        @media print {
            body { margin: 0; }
            .no-print { display: none; }
        }
    </style>
</head>
<body>

    <div class="header">
        <img src="[EMPRESA_LOGO]" alt="Logo" style="max-height: 100px;">
        <div class="contract-title">Contrato de Prestação de Serviços</div>
        <div style="font-size: 12px;">[EMPRESA_NOME] | [EMPRESA_CNPJ]</div>
    </div>

    <div class="content">
        <p>
            Pelo presente instrumento particular, de um lado <strong>[EMPRESA_NOME]</strong>, inscrita no CNPJ <strong>[EMPRESA_CNPJ]</strong>, 
            estabelecida em [EMPRESA_ENDERECO], doravante denominada VENDEDORA, e de outro lado 
            <strong>[CLIENTE]</strong>, portador do CPF/CNPJ <strong>[CPF_CNPJ]</strong>, doravante denominado COMPRADOR, 
            têm entre si justo e contratado o seguinte:
        </p>

        <div class="section-title">1. DO OBJETO</div>
        <p>O presente contrato tem como objeto a fabricação e instalação dos móveis planejados abaixo descritos:</p>
        
        [TABELA_ITENS]

        <div class="section-title">2. DO VALOR E PAGAMENTO</div>
        <p>
            O valor total deste contrato é de <strong>[TOTAL]</strong>.
            Forma de pagamento: [FORMA_PAGAM].
            Entrada de [ENTRADA] e [QTD_PARCELAS] parcelas de [VALOR_PARCELA].
        </p>

        <div class="section-title">3. DAS CLÁUSULAS GERAIS</div>
        
        <div class="clause">
            <span class="clause-title">DA ENTREGA:</span> 30 dias úteis após medição final.
        </div>
        <div class="clause">
            <span class="clause-title">DA GARANTIA:</span> 1 ano para defeitos de fabricação.
        </div>
        
        [ASSINATURAS]

        <br><br>
        <p style="text-align: center; font-size: 10px;">Gerado em [DATA] - Orçamento #[ID]</p>
    </div>

</body>
</html>'''),
            ('contrato_base', '''<div class="clause">
        <span class="clause-title">CLÁUSULA 1ª - DA ENTREGA E PRAZO</span><br>
        A VENDEDORA se compromete a entregar e instalar os móveis no prazo estipulado de 30 (trinta) dias úteis, a
        contar da data de assinatura deste contrato e liberação do local (medição final).
    </div>

    <div class="clause">
        <span class="clause-title">CLÁUSULA 2ª - DA GARANTIA</span><br>
        Os móveis possuem garantia de 01 (um) ano (3 meses legal + 9 meses contratual) contra defeitos de fabricação e
        montagem. A garantia não cobre danos por mau uso, umidade excessiva (infiltrações), ou manuseio por terceiros.
    </div>

    <div class="clause">
        <span class="clause-title">CLÁUSULA 3ª - DAS OBRIGAÇÕES</span><br>
        O COMPRADOR deve disponibilizar o local livre para montagem. Alterações no projeto após a assinatura gerarão
        custos adicionais e novo prazo.
    </div>

    <div class="clause">
        <span class="clause-title">CLÁUSULA 4ª - DO FORO</span><br>
        As partes elegem o foro da Comarca de Sinop - MT para dirimir quaisquer dúvidas.
    </div>''')
        ]
        for key, val in defaults:
            try:
                db.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))
            except:
                pass
        db.commit()

        db.execute('''CREATE TABLE IF NOT EXISTS config_fabrica (
            id INTEGER PRIMARY KEY,
            margem_lucro REAL DEFAULT 0.35,
            margem_negociacao REAL DEFAULT 0.10,
            margem_impostos REAL DEFAULT 0.05
        )''')
        
        # Seed default config if empty
        row = db.execute('SELECT * FROM config_fabrica').fetchone()
        if not row:
            db.execute('INSERT INTO config_fabrica (margem_lucro, margem_negociacao, margem_impostos) VALUES (0.35, 0.10, 0.05)')
        db.commit()

def log_audit(user_id, action, details=''):
    db = get_db()
    db.execute('INSERT INTO audits (user_id, action, details) VALUES (?, ?, ?)',
               (user_id, action, details))
    db.commit()

@flask_app.route('/')
def index():
    return redirect(url_for('login'))

    return render_template('login.html')

@flask_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and user['password'] == password:
            # Check active status
            if 'is_active' in user.keys() and user['is_active'] == 0:
                flash('Usuário desativado pelo administrador.', 'error')
                log_audit(user['id'], 'LOGIN_FAILED', 'Inactive user tried to login')
                return render_template('login.html')

            access_token = create_access_token(identity=str(user['id']))
            resp = make_response(redirect(url_for('dashboard')))
            set_access_cookies(resp, access_token)
            
            log_audit(user['id'], 'LOGIN_SUCCESS', 'User logged in')
            return resp
        
        flash('Usuário ou senha inválidos', 'error')
        
    return render_template('login.html')

@flask_app.route('/kanban')
@jwt_required()
def kanban():
    current_user_id = get_jwt_identity()
    db = get_db()
    
    # Get Kanban cards
    cards = db.execute('SELECT * FROM cards_kanban').fetchall()
    return render_template('kanban.html', cards=cards)

@flask_app.route('/dashboard')
@jwt_required()
def dashboard():
    return render_template('dashboard_kpi.html')

@flask_app.route('/relatorios')
@jwt_required()
def relatorios():
    return render_template('relatorios.html')

@flask_app.route('/api/kpis')
@jwt_required()
def api_kpis():
    db = get_db()
    
    # 1. Faturamento Mês (Sum orcamentos aprovados/contas receber)
    # Simple: Sum total of 'orcamentos' this month
    # Better: Sum 'contas' type='receber' this month
    faturamento = db.execute("SELECT SUM(valor) as total FROM contas WHERE tipo='receber' AND strftime('%Y-%m', vencimento) = strftime('%Y-%m', 'now')").fetchone()['total'] or 0
    
    # 2. Orçamentos (Total vs Approved)
    total_orc = db.execute("SELECT COUNT(*) as c FROM orcamentos").fetchone()['c']
    # Logic: if exists in contas or status 'aprovado' (we don't have status col in orcamentos yet, looking at schema). 
    # Let's count cards in 'Concluído' or similar? 
    # For now, let's just count total.
    
    # 3. Estoque Crítico (< 10)
    estoque_crit = db.execute("SELECT COUNT(*) as c FROM estoque WHERE quantidade < 10 AND quantidade > 0").fetchone()['c']
    
    # 4. Clientes Novos (This Month)
    # We don't have a clients table, we use distinct client names from orcamentos
    clientes = db.execute("SELECT COUNT(DISTINCT client) as c FROM orcamentos WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')").fetchone()['c']
    
    # 5. Contas Vencidas
    vencidas = db.execute("SELECT SUM(valor) as total FROM contas WHERE tipo='pagar' AND status='pendente' AND vencimento < date('now')").fetchone()['total'] or 0
    # 6. Margem Média Projetos (Target from Config)
    config = db.execute('SELECT margem_lucro FROM config_fabrica LIMIT 1').fetchone()
    margem = (config['margem_lucro'] * 100) if config else 35.0

    # 7. Charts Data
    # A. Faturamento (Last 30 days)
    # Group by vencimento (or created_at if paid?) - let's use vencimento for projection/history
    fat_query = '''
        SELECT strftime('%d/%m', vencimento) as day, SUM(valor) as total
        FROM contas
        WHERE tipo='receber' 
        AND vencimento >= date('now', '-30 days')
        GROUP BY day
        ORDER BY vencimento ASC
    '''
    fat_rows = db.execute(fat_query).fetchall()
    fat_labels = [r['day'] for r in fat_rows]
    fat_data = [r['total'] for r in fat_rows]
    
    # Fill gaps? (Optional, skipping for MVP)
    
    # B. Estoque por Categoria
    est_query = '''
        SELECT categoria, COUNT(*) as qtd
        FROM estoque
        WHERE categoria IS NOT NULL AND categoria != ''
        GROUP BY categoria
        ORDER BY qtd DESC
        LIMIT 5
    '''
    est_rows = db.execute(est_query).fetchall()
    est_labels = [r['categoria'] for r in est_rows]
    est_data = [r['qtd'] for r in est_rows]
    
    # If empty labels (no categories yet), fallback
    if not est_labels:
        est_labels = ['Sem Categoria']
        est_data = [db.execute("SELECT COUNT(*) FROM estoque").fetchone()[0]]

    return jsonify({
        'faturamento_mes': faturamento,
        'orcamentos_total': total_orc,
        'estoque_critico': estoque_crit,
        'clientes_novos': clientes,
        'contas_vencidas': vencidas,
        'margem_projetos': margem,
        'charts': {
            'fat_labels': fat_labels,
            'fat_data': fat_data,
            'est_labels': est_labels,
            'est_data': est_data
        }
    })

@flask_app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    resp = jsonify({'success': True})
    unset_jwt_cookies(resp)
    return resp

# --- API LOGS DO SISTEMA ---

@flask_app.route('/api/logs', methods=['GET'])
@jwt_required()
def api_logs_list():
    db = get_db()
    
    # Auto-cleanup older than 1 year
    try:
        db.execute("DELETE FROM audits WHERE ts < date('now', '-1 year')")
        db.commit()
    except:
        pass # Fail silently if table locked or error
        
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    action = request.args.get('action')
    user = request.args.get('user')
    limit = request.args.get('limit', 50)
    
    # Select * and alias ts to created_at for frontend compatibility if needed, 
    # but let's just use ts in the query logic.
    query = "SELECT *, ts as created_at FROM audits WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND ts >= ?"
        params.append(start_date + ' 00:00:00')
    if end_date:
        query += " AND ts <= ?"
        params.append(end_date + ' 23:59:59')
    if action:
        query += " AND action LIKE ?"
        params.append(f"%{action}%")
    if user:
        query += " AND user_id LIKE ?"
        params.append(f"%{user}%")
        
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    
    rows = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])

# --- API USUÁRIOS ---

@flask_app.route('/api/users', methods=['GET'])
@jwt_required()
def api_users_list():
    db = get_db()
    # List all users, default to showing active first
    users = db.execute('SELECT id, username, role, is_active FROM users ORDER BY is_active DESC, username ASC').fetchall()
    return jsonify([dict(u) for u in users])

@flask_app.route('/api/users', methods=['POST'])
@jwt_required()
def api_users_create():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username e Password obrigatórios'}), 400
        
    db = get_db()
    try:
        db.execute('INSERT INTO users (username, password, role, is_active) VALUES (?, ?, ?, 1)', 
                   (username, password, role))
        db.commit()
        log_audit(get_jwt_identity(), 'USER_CREATE', f'Created user {username}')
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Usuário já existe'}), 400

@flask_app.route('/api/users/<int:id>', methods=['PUT'])
@jwt_required()
def api_users_update(id):
    data = request.json
    db = get_db()
    
    # Optional fields
    password = data.get('password')
    role = data.get('role')
    is_active = data.get('is_active')
    
    fields = []
    params = []
    
    if password:
        fields.append("password = ?")
        params.append(password)
    if role:
        fields.append("role = ?")
        params.append(role)
    if is_active is not None:
        fields.append("is_active = ?")
        params.append(is_active)
        
    if not fields:
        return jsonify({'success': True}) # Nothing to update
        
    params.append(id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
    
    db.execute(query, params)
    db.commit()
    log_audit(get_jwt_identity(), 'USER_UPDATE', f'Updated user {id}. Fields: {fields}')
    return jsonify({'success': True})

@flask_app.route('/api/users/<int:id>', methods=['DELETE'])
@jwt_required()
def api_users_delete(id):
    # Soft delete (disable)
    db = get_db()
    db.execute('UPDATE users SET is_active = 0 WHERE id = ?', (id,))
    db.commit()
    log_audit(get_jwt_identity(), 'USER_DISABLE', f'Disabled user {id}')
    return jsonify({'success': True})

@flask_app.route('/orcamentos')
@jwt_required()
def orcamentos():
    db = get_db()
    show_all = request.args.get('show_all')
    if show_all:
        orcamentos = db.execute('SELECT * FROM orcamentos ORDER BY created_at DESC').fetchall()
    else:
        orcamentos = db.execute("SELECT * FROM orcamentos WHERE status != 'Faturado' ORDER BY created_at DESC").fetchall()
    return render_template('orcamentos.html', orcamentos=orcamentos, showing_all=show_all)

@flask_app.route('/estoque')
@jwt_required()
def estoque():
    return render_template('estoque.html')

@flask_app.route('/settings')
@jwt_required()
def settings():
    from flask_jwt_extended import current_user
    if current_user and current_user['role'] != 'admin':
        flash('Acesso restrito a administradores.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('settings.html')

@flask_app.route('/api/estoque/check/<path:nome>')
@jwt_required()
def api_estoque_check(nome):
    db = get_db()
    # Partial search for AI flexibility
    items = db.execute('SELECT nome, quantidade FROM estoque WHERE LOWER(nome) LIKE ?', (f'%{nome.lower()}%',)).fetchall()
    
    if not items:
         return jsonify({'found': False, 'matches': []})
         
    # Return all matches so AI can decide or ask for clarification
    return jsonify({
        'found': True, 
        'count': len(items),
        'matches': [{'nome': i['nome'], 'qtd': i['quantidade']} for i in items]
    })

@flask_app.route('/api/estoque', methods=['GET'])
@jwt_required()
def api_estoque_list():
    db = get_db()
    # Return items with group price
    query = '''
        SELECT e.*, pg.name as group_name, pg.price as group_price 
        FROM estoque e
        LEFT JOIN price_groups pg ON e.price_group_id = pg.id
        ORDER BY e.nome
    '''
    items = db.execute(query).fetchall()
    return jsonify([dict(ix) for ix in items])

@flask_app.route('/api/estoque/acessorios', methods=['GET'])
@jwt_required()
def api_estoque_acessorios():
    db = get_db()
    items = db.execute('SELECT * FROM estoque WHERE is_acessorio = 1 ORDER BY nome').fetchall()
    return jsonify([dict(ix) for ix in items])

@flask_app.route('/api/estoque', methods=['POST'])
@jwt_required()
def api_estoque_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    is_acessorio = 1 if data.get('is_acessorio') else 0
    area = float(data.get('area_unidade') or 0)
    db.execute('INSERT INTO estoque (nome, categoria, unidade, quantidade, custo_unitario, site_origem, is_acessorio, area_unidade, url_madeiranit, url_leomadeiras, url_madeverde, price_group_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
               (data.get('nome'), data.get('categoria'), data.get('unidade'), data.get('quantidade'), data.get('custo_unitario'), data.get('site_origem'), is_acessorio, area, data.get('url_madeiranit'), data.get('url_leomadeiras'), data.get('url_madeverde'), data.get('price_group_id')))
    db.commit()
    log_audit(user_id, 'ESTOQUE_CREATE', f"Created item: {data.get('nome')}")
    return jsonify({'success': True})

@flask_app.route('/api/estoque/<int:id>', methods=['PUT'])
@jwt_required()
def api_estoque_update(id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    is_acessorio = 1 if data.get('is_acessorio') else 0
    area = float(data.get('area_unidade') or 0)
    db.execute('''UPDATE estoque SET nome=?, categoria=?, unidade=?, quantidade=?, custo_unitario=?, site_origem=?, is_acessorio=?, area_unidade=?, url_madeiranit=?, url_leomadeiras=?, url_madeverde=?, price_group_id=?, last_update=CURRENT_TIMESTAMP 
                  WHERE id=?''',
               (data.get('nome'), data.get('categoria'), data.get('unidade'), data.get('quantidade'), data.get('custo_unitario'), data.get('site_origem'), is_acessorio, area, data.get('url_madeiranit'), data.get('url_leomadeiras'), data.get('url_madeverde'), data.get('price_group_id'), id))
    db.commit()
    log_audit(user_id, 'ESTOQUE_UPDATE', f"Updated item #{id}: {data.get('nome')}")
    return jsonify({'success': True})

@flask_app.route('/api/estoque/<int:id>', methods=['DELETE'])
@jwt_required()
def api_estoque_delete(id):
    user_id = get_jwt_identity()
    db = get_db()
    # Check if admin logic here if needed, for now just allow logged user
    db.execute('DELETE FROM estoque WHERE id=?', (id,))
    db.commit()
    log_audit(user_id, 'ESTOQUE_DELETE', f"Deleted item #{id}")
    return jsonify({'success': True})

@flask_app.route('/catalogo')
@jwt_required()
def catalogo():
    return render_template('catalogo.html')

@flask_app.route('/api/catalogo', methods=['GET'])
@jwt_required()
def api_catalogo_list():
    db = get_db()
    # Join with estoque to get material name/price details if needed
    query = '''
        SELECT c.*, e.nome as material_nome, e.custo_unitario as material_custo, e.area_unidade as material_area
        FROM itens_catalogo c
        LEFT JOIN estoque e ON c.estoque_id = e.id
        ORDER BY c.nome
    '''
    items = db.execute(query).fetchall()
    
    result = []
    for item in items:
        d = dict(item)
        # Fetch insumos - Usando Margem de Segurança (Maior Preço por Nome)
        insumos = db.execute('''
            SELECT ci.*, e.nome, 
                   CASE 
                       WHEN pg.id IS NOT NULL THEN pg.price
                       ELSE (SELECT MAX(custo_unitario) FROM estoque WHERE nome = e.nome) 
                   END as custo_unitario,
                   (SELECT MIN(custo_unitario) FROM estoque WHERE nome = e.nome) as custo_minimo,
                   e.unidade, e.area_unidade, e.price_group_id, pg.name as group_name
            FROM catalogo_insumos ci
            JOIN estoque e ON ci.estoque_id = e.id
            LEFT JOIN price_groups pg ON e.price_group_id = pg.id
            WHERE ci.catalogo_id = ?
        ''', (d['id'],)).fetchall()
        d['insumos'] = [dict(ix) for ix in insumos]
        result.append(d)
        
    return jsonify(result)

@flask_app.route('/api/catalogo', methods=['POST'])
@jwt_required()
def api_catalogo_create():
    data = request.json
    db = get_db()
    cursor = db.execute('INSERT INTO itens_catalogo (nome, preco_base, fator_consumo, dims_padrao, estoque_id, categoria, horas_mo, imagem_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
               (data.get('nome'), data.get('preco_base'), data.get('fator_consumo'), data.get('dims_padrao'), data.get('estoque_id'), data.get('categoria'), data.get('horas_mo'), data.get('imagem_url')))
    new_id = cursor.lastrowid
    
    # Save Insumos
    insumos = data.get('insumos', [])
    for ins in insumos:
        db.execute('INSERT INTO catalogo_insumos (catalogo_id, estoque_id, quantidade, tipo_calculo) VALUES (?, ?, ?, ?)',
                   (new_id, ins.get('estoque_id'), ins.get('quantidade'), ins.get('tipo_calculo')))
    
    db.commit()
    return jsonify({'success': True})

@flask_app.route('/api/catalogo/<int:id>', methods=['PUT'])
@jwt_required()
def api_catalogo_update(id):
    data = request.json
    db = get_db()
    db.execute('UPDATE itens_catalogo SET nome=?, preco_base=?, fator_consumo=?, dims_padrao=?, estoque_id=?, categoria=?, horas_mo=?, imagem_url=? WHERE id=?',
               (data.get('nome'), data.get('preco_base'), data.get('fator_consumo'), data.get('dims_padrao'), data.get('estoque_id'), data.get('categoria'), data.get('horas_mo'), data.get('imagem_url'), id))
    
    # Clear and Update Insumos
    db.execute('DELETE FROM catalogo_insumos WHERE catalogo_id=?', (id,))
    insumos = data.get('insumos', [])
    for ins in insumos:
        db.execute('INSERT INTO catalogo_insumos (catalogo_id, estoque_id, quantidade, tipo_calculo) VALUES (?, ?, ?, ?)',
                   (id, ins.get('estoque_id'), ins.get('quantidade'), ins.get('tipo_calculo')))
                   
    db.commit()
    return jsonify({'success': True})

@flask_app.route('/api/catalogo/<int:id>', methods=['DELETE'])
@jwt_required()
def api_catalogo_delete(id):
    db = get_db()
    db.execute('DELETE FROM itens_catalogo WHERE id=?', (id,))
    db.commit()
    return jsonify({'success': True})





@flask_app.route('/financeiro')
@jwt_required()
def financeiro():
    return render_template('financeiro.html')

# --- API FINANCEIRO ---

@flask_app.route('/api/contas', methods=['GET'])
@jwt_required()
def api_contas_list():
    tipo = request.args.get('tipo')
    db = get_db()
    query = 'SELECT * FROM contas'
    args = []
    if tipo:
        query += ' WHERE tipo = ?'
        args.append(tipo)
    query += ' ORDER BY vencimento'
    items = db.execute(query, args).fetchall()
    return jsonify([dict(ix) for ix in items])

@flask_app.route('/api/contas', methods=['POST'])
@jwt_required()
def api_contas_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    # Defaults
    status = data.get('status', 'pendente')
    
    db.execute('INSERT INTO contas (tipo, descricao, valor, vencimento, status, categoria, funcionario_id, orcamento_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
               (data.get('tipo'), data.get('descricao'), data.get('valor'), data.get('vencimento'), status, data.get('categoria'), data.get('funcionario_id'), data.get('orcamento_id')))
    db.commit()
    
    log_audit(user_id, f"CONTA_CREATE_{data.get('tipo').upper()}", f"Created conta: {data.get('descricao')} R${data.get('valor')}")
    return jsonify({'success': True})

# --- API CUSTOS FIXOS ---

@flask_app.route('/api/custos_fixos', methods=['GET'])
@jwt_required()
def api_custos_fixos_list():
    db = get_db()
    items = db.execute('SELECT * FROM custos_fixos ORDER BY descricao').fetchall()
    return jsonify([dict(ix) for ix in items])

@flask_app.route('/api/custos_fixos', methods=['POST'])
@jwt_required()
def api_custos_fixos_create():
    data = request.json
    db = get_db()
    db.execute('INSERT INTO custos_fixos (descricao, valor, categoria) VALUES (?, ?, ?)',
               (data.get('descricao'), data.get('valor'), data.get('categoria')))
    db.commit()
    return jsonify({'success': True})

@flask_app.route('/api/custos_fixos/<int:id>', methods=['DELETE'])
@jwt_required()
def api_custos_fixos_delete(id):
    db = get_db()
    db.execute('DELETE FROM custos_fixos WHERE id=?', (id,))
    db.commit()
    return jsonify({'success': True})

# --- SETTINGS ---
@flask_app.route('/api/settings', methods=['GET'])
@jwt_required()
def api_settings_list():
    db = get_db()
    rows = db.execute('SELECT * FROM settings').fetchall()
    return jsonify({r['key']: r['value'] for r in rows})

@flask_app.route('/api/settings', methods=['POST'])
@jwt_required()
def api_settings_update():
    data = request.json
    db = get_db()
    for key, value in data.items():
        db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
    db.commit()
    return jsonify({'success': True})

# --- API CONFIG FABRICA (VALCI) ---
@flask_app.route('/api/config-fabrica', methods=['GET'])
@jwt_required()
def api_config_list():
    db = get_db()
    row = db.execute('SELECT * FROM config_fabrica LIMIT 1').fetchone()
    config = dict(row)
    # Converter para valores inteiros para interface (35% em vez de 0.35)
    config['margem_lucro'] = float(config['margem_lucro']) * 100
    config['margem_negociacao'] = float(config['margem_negociacao']) * 100
    config['margem_impostos'] = float(config['margem_impostos']) * 100
    return jsonify(config)

@flask_app.route('/api/config-fabrica', methods=['POST'])
@jwt_required()
def api_config_update():
    data = request.json
    db = get_db()
    db.execute('''UPDATE config_fabrica SET 
                  margem_lucro=?, margem_negociacao=?, 
                  margem_impostos=?''',
               (float(data.get('margem_lucro')) / 100, 
                float(data.get('margem_negociacao')) / 100, 
                float(data.get('margem_impostos')) / 100))
    db.commit()
    return jsonify({'success': True})

@flask_app.route('/api/system/metadata', methods=['GET'])
@jwt_required()
def api_system_metadata():
    """
    Returns system-wide enums and valid values for dropdowns/agents.
    """
    metadata = {
        'estoque': {
            'categorias': [
                'MDF', 'Compensado', 'Fórmica', 'Vidro', 'Espelho', 
                'Ferragem', 'Acessório', 'Iluminação', 'Outro'
            ],
            'unidades': ['Unidade', 'Metro', 'Quilo', 'Litro', 'Chapa']
        },
        'orcamentos': {
            'status': ['proposta', 'aprovado', 'producao', 'concluido', 'entregue']
        },
        'clientes': {
            'tipos': ['fisica', 'juridica'],
            'origens': ['indicacao', 'google', 'facebook', 'instagram', 'site', 'outdoor', 'outro']
        }
    }
    return jsonify(metadata)

@flask_app.route('/api/orcamento-calcular', methods=['POST'])
@jwt_required()
def api_orcamento_calcular():
    data = request.json
    material = float(data.get('material', 0))
    horas = float(data.get('horas', 0))
    
    db = get_db()
    # Configuration (provided by client or fetched)
    cf = data.get('config')
    if not cf:
        cf = dict(db.execute('SELECT * FROM config_fabrica LIMIT 1').fetchone())
    
    # Get valor_hora_fabrica from settings
    rate_row = db.execute("SELECT value FROM settings WHERE key='valor_hora_fabrica'").fetchone()
    custo_hora = float(rate_row['value']) if rate_row else 70.0
    
    margem_lucro = float(cf['margem_lucro'])
    margem_negociacao = float(cf['margem_negociacao'])
    margem_impostos = float(cf['margem_impostos'])
    
    custo_fabricacao = custo_hora * horas
    custo_total = material + custo_fabricacao
    
    # Cascade Formula: Preço = CustoTotal * (1+L) * (1+N) * (1+I)
    preco_venda = custo_total * (1 + margem_lucro) * (1 + margem_negociacao) * (1 + margem_impostos)
    
    breakdown = [
        f"Material: R$ {material:,.2f}",
        f"Mão de Obra ({horas}h @ R$ {custo_hora:,.2f}/h): R$ {custo_fabricacao:,.2f}",
        f"Custo Base Total: R$ {custo_total:,.2f}",
        f"+ Margem Lucro ({margem_lucro*100}%): R$ {custo_total * margem_lucro:,.2f}",
        f"+ Reserva Negoc. ({margem_negociacao*100}%): R$ {custo_total * (1+margem_lucro) * margem_negociacao:,.2f}",
        f"+ Impostos ({margem_impostos*100}%): R$ {custo_total * (1+margem_lucro) * (1+margem_negociacao) * margem_impostos:,.2f}",
        f"--- PREÇO FINAL SUGERIDO: R$ {preco_venda:,.2f} ---"
    ]
    
    return jsonify({
        'custo_fabricacao': round(custo_fabricacao, 2),
        'custo_total': round(custo_total, 2),
        'preco_venda': round(preco_venda, 2),
        'breakdown': breakdown
    })

@flask_app.route('/api/contas/<int:id>', methods=['DELETE'])
@jwt_required()
def api_contas_delete(id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM contas WHERE id=?', (id,))
    db.commit()
    log_audit(user_id, 'CONTA_DELETE', f"Deleted conta #{id}")
    return jsonify({'success': True})

@flask_app.route('/api/contas/orcamento/<int:orc_id>', methods=['POST'])
@jwt_required()
def api_contas_from_orcamento(orc_id):
    user_id = get_jwt_identity()
    db = get_db()
    data = request.json
    orc = db.execute('SELECT * FROM orcamentos WHERE id = ?', (orc_id,)).fetchone()
    if not orc:
        return jsonify({'error': 'Orcamento not found'}), 404
        
    # Get Payment Details
    metodo = data.get('metodo', 'outro')
    entrada = float(data.get('entrada') or 0)
    parcelas = int(data.get('parcelas') or 1)
    
    total = orc['total']
    saldo = total - entrada
    
    # 1. Register Down Payment (if any)
    if entrada > 0:
        db.execute('INSERT INTO contas (tipo, descricao, valor, vencimento, status, categoria, orcamento_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   ('receber', f"Entrada Orç. #{orc_id} - {orc['client']}", entrada, datetime.now().strftime('%Y-%m-%d'), 'pago', 'venda_entrada', orc_id))

    # 2. Register Installments (if any saldo left)
    if saldo > 0:
        valor_parcela = saldo / parcelas
        # Create receivable for remaining amount (simplified as one entry or multiple?)
        # Let's create one entry per installment for better tracking? For now simplified: 1 entry representing the deal, or multiple future entries.
        # User wants "Contas a Receber". Let's create multiple if > 1.
        
        from datetime import timedelta
        hoje = datetime.now()
        
        for i in range(parcelas):
            venc = hoje + timedelta(days=30 * (i+1))
            desc = f"Parc. {i+1}/{parcelas} Orç. #{orc_id} ({metodo})"
            db.execute('INSERT INTO contas (tipo, descricao, valor, vencimento, status, categoria, orcamento_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       ('receber', desc, valor_parcela, venc.strftime('%Y-%m-%d'), 'pendente', 'venda_parcela', orc_id))

    # 3. Save Payment Info in Orcamento (for Contract)
    # Storing in a new JSON column or overloading existing? 
    # Let's add a `pagamento_info` column or just strict contract generation to these inputs.
    # To persist for re-printing, we should store it.
    # We'll use a new table `orcamento_pagamento` or just save in `itens_json` appended?
    # Simple approach: Store as JSON in a comment or separate table.
    # We will assume re-printing uses stored Accounts or re-input?
    # Better: Update orcamentos table to have `pagamento_json`.
    
    pag_info = {
        'metodo': metodo,
        'entrada': entrada,
        'parcelas': parcelas,
        'valor_parcela': saldo/parcelas if parcelas > 0 else 0
    }
    
    try:
        db.execute("ALTER TABLE orcamentos ADD COLUMN pagamento_json TEXT")
    except:
        pass # Already exists
        
    db.execute("UPDATE orcamentos SET status = 'Faturado', pagamento_json = ? WHERE id = ?", (json.dumps(pag_info), orc_id))
    db.commit()
    
    log_audit(user_id, 'CONTA_FROM_ORCAMENTO', f"Faturado Orc #{orc_id}. Entrada: {entrada}")
    return jsonify({'success': True})

@flask_app.route('/contrato/<int:orc_id>')
@jwt_required()
def gerar_contrato(orc_id):
    db = get_db()
    # Fetch Orcamento
    orc = db.execute('SELECT * FROM orcamentos WHERE id = ?', (orc_id,)).fetchone()
    if not orc: return "Orçamento não encontrado"
    
    # Fetch Cliente
    cliente = None
    if orc['client_id']:
        cliente = db.execute('SELECT * FROM clientes WHERE id = ?', (orc['client_id'],)).fetchone()
    
    # Fetch Template
    settings_row = db.execute("SELECT value FROM settings WHERE key='contrato_template'").fetchone()
    template_str = settings_row['value'] if settings_row else ""
    
    # Fallback if empty (should fetch from init_db defaults ideally, or hardcode generic)
    if not template_str:
        # Tenta pegar o contrato_base antigo se o novo template não existir
        base_row = db.execute("SELECT value FROM settings WHERE key='contrato_base'").fetchone()
        if base_row:
             # Se tiver o base antigo, encapsula num HTML simples
             template_str = f"<html><body>{base_row['value']}</body></html>"
        else:
             template_str = "<h1>Erro: Template de contrato não encontrado.</h1>"

    # Render Template
    final_html = render_contract_template(template_str, orc, cliente, db)
    
    return render_template('contrato_print.html', contract_html=final_html)

def render_contract_template(template_str, orc, cliente, db):
    # Prepare Data
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        pass # Fallback

    def fmt_moeda(val):
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    pag_info = json.loads(orc['pagamento_json']) if orc['pagamento_json'] else {}
    total = fmt_moeda(orc['total'])
    total = fmt_moeda(orc['total'])
    data_hoje = datetime.now().strftime('%d/%m/%Y')

    # Fetch Company Settings
    try:
        rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'empresa_%'").fetchall()
        company = {row['key']: row['value'] for row in rows}
    except:
        company = {}

    c_nome = company.get('empresa_nome', 'Adore Marcenaria')
    c_cnpj = company.get('empresa_cnpj', '00.000.000/0001-00')
    c_end = company.get('empresa_endereco', '')
    c_logo = company.get('empresa_logo_url', '/static/logo.jpg')
    
    # Items Table Generation
    itens_html = "<table><thead><tr><th>Ambiente</th><th>Descrição</th><th>Dimensões/Detalhes</th><th>Valor</th></tr></thead><tbody>"
    
    itens_data = []
    if orc['itens_json']:
        try:
            raw = json.loads(orc['itens_json'])
            if isinstance(raw, list) and len(raw) > 0 and 'items' in raw[0]:
                for group in raw:
                    for item in group['items']:
                        itens_data.append({'ambiente': group['name'], 'item': item})
            else:
                 for item in raw:
                    itens_data.append({'ambiente': 'Geral', 'item': item})
        except:
            pass

    for row in itens_data:
        it = row['item']
        desc = f"<strong>{it.get('nome', 'Item')}</strong><br>{it.get('descricao', '')}"
        dim = f"{it.get('largura',0)}x{it.get('altura',0)}x{it.get('profundidade',0)}"
        valor = fmt_moeda(it.get('preco_final', 0))
        itens_html += f"<tr><td>{row['ambiente']}</td><td>{desc}</td><td>{dim}</td><td>{valor}</td></tr>"
    
    itens_html += "</tbody></table>"

    # Signatures Block
    signatures_html = f'''
    <div class="signatures">
        <div class="sig-block">
            __________________________<br>
            <strong>{c_nome}</strong><br>
            CNPJ: {c_cnpj}
        </div>
        <div class="sig-block">
            __________________________<br>
            <strong>{cliente['nome'] if cliente else 'CLIENTE'}</strong><br>
            CPF/CNPJ: {cliente['cpf_cnpj'] if cliente else ''}
        </div>
    </div>
    '''

    # Replacements
    html = template_str
    
    # Basic info
    html = html.replace('[ID]', str(orc['id']))
    html = html.replace('[DATA]', data_hoje)
    html = html.replace('[TOTAL]', total)

    # Company info
    html = html.replace('[EMPRESA_NOME]', c_nome)
    html = html.replace('[EMPRESA_CNPJ]', c_cnpj)
    html = html.replace('[EMPRESA_ENDERECO]', c_end)
    html = html.replace('[EMPRESA_LOGO]', c_logo)

    
    # Client info
    html = html.replace('[CLIENTE]', cliente['nome'] if cliente else "N/A")
    html = html.replace('[CPF_CNPJ]', cliente['cpf_cnpj'] if cliente else "N/A")
    
    # Payment info
    html = html.replace('[FORMA_PAGAM]', pag_info.get('metodo', 'À combinar'))
    html = html.replace('[ENTRADA]', fmt_moeda(float(pag_info.get('entrada', 0))))
    html = html.replace('[QTD_PARCELAS]', str(pag_info.get('parcelas', 1)))
    html = html.replace('[VALOR_PARCELA]', fmt_moeda(float(pag_info.get('valor_parcela', 0))))
    
    # Complex Blocks
    html = html.replace('[TABELA_ITENS]', itens_html)
    html = html.replace('[ASSINATURAS]', signatures_html)

    return html

@flask_app.route('/proposta/<int:orc_id>')
@jwt_required()
def gerar_proposta(orc_id):
    db = get_db()
    orc = db.execute('SELECT * FROM orcamentos WHERE id = ?', (orc_id,)).fetchone()
    if not orc: return "Orçamento não encontrado"
    
    # Proposal number is DDMM (today) according to image reference
    from datetime import datetime
    prop_numero = datetime.now().strftime('%d%m')
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    
    # Parse Items and fetch image URLs from catalog
    groups = []
    if orc['itens_json']:
        try:
            raw = json.loads(orc['itens_json'])
            if isinstance(raw, list) and len(raw) > 0 and 'items' in raw[0]:
                # Converter 'items' para 'itens' para compatibilidade com templates
                groups = []
                for group in raw:
                    new_group = dict(group)
                    if 'items' in new_group:
                        new_group['itens'] = new_group.pop('items')
                    groups.append(new_group)
            else:
                groups = [{'name': 'Geral', 'itens': raw}]
        except Exception as e:
            print(f"Error parsing items for proposal: {e}")
            groups = []

    return render_template('proposta_print.html', orcamento=orc, data_hoje=data_hoje, prop_numero=prop_numero, groups=groups)



@flask_app.route('/funcionarios')
@jwt_required()
def funcionarios():
    return render_template('funcionarios.html')

# --- API RH / FUNCIONARIOS ---

@flask_app.route('/api/funcionarios', methods=['GET'])
@jwt_required()
def api_funcionarios_list():
    db = get_db()
    items = db.execute('SELECT * FROM funcionarios ORDER BY nome').fetchall()
    return jsonify([dict(ix) for ix in items])

@flask_app.route('/api/funcionarios', methods=['POST'])
@jwt_required()
def api_funcionarios_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    # Defaults
    desc_json = json.dumps(data.get('descontos_json') or [])
    
    db.execute('INSERT INTO funcionarios (nome, cargo, salario_base, inss_percent, fgts_percent, descontos_json, nome_ponto) VALUES (?, ?, ?, ?, ?, ?, ?)',
               (data.get('nome'), data.get('cargo'), data.get('salario_base'), 
                data.get('inss_percent', 0.11), data.get('fgts_percent', 0.08), desc_json, data.get('nome_ponto')))
    db.commit()
    log_audit(user_id, 'FUNC_CREATE', f"New employee: {data.get('nome')}")
    return jsonify({'success': True})

@flask_app.route('/api/funcionarios/<int:id>', methods=['PUT'])
@jwt_required()
def api_funcionarios_update(id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    desc_json = json.dumps(data.get('descontos_json') or [])
    
    db.execute('UPDATE funcionarios SET nome=?, cargo=?, salario_base=?, inss_percent=?, fgts_percent=?, descontos_json=?, nome_ponto=? WHERE id=?',
               (data.get('nome'), data.get('cargo'), data.get('salario_base'), 
                data.get('inss_percent'), data.get('fgts_percent'), desc_json, data.get('nome_ponto'), id))
    db.commit()
    log_audit(user_id, 'FUNC_UPDATE', f"Updated employee #{id}")
    return jsonify({'success': True})

@flask_app.route('/api/funcionarios/<int:id>', methods=['DELETE'])
@jwt_required()
def api_funcionarios_delete(id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM funcionarios WHERE id=?', (id,))
    db.commit()
    log_audit(user_id, 'FUNC_DELETE', f"Deleted employee #{id}")
    return jsonify({'success': True})

@flask_app.route('/api/holerite/<int:id>', methods=['POST'])
@jwt_required()
def api_holerite_calc(id):
    user_id = get_jwt_identity()
    db = get_db()
    
    # Get Date Range
    data_ref = request.json.get('data') if request.json else None
    if not data_ref:
        now = datetime.now()
        data_ref = now.strftime('%Y-%m-%d')
    
    ref_date = datetime.strptime(data_ref, '%Y-%m-%d')
    month_str = ref_date.strftime('%Y-%m') # "2025-02"
    
    func = db.execute('SELECT * FROM funcionarios WHERE id=?', (id,)).fetchone()
    if not func: return jsonify({'error': 'Not found'}), 404
    
    # Base Values
    salario_base = func['salario_base']
    inss_percent = func['inss_percent'] if func['inss_percent'] else 0.11
    
    # 1. Vales (Adiantamentos)
    # Fetch from financeiro (contas)
    vales_query = '''
        SELECT SUM(valor) as total 
        FROM contas 
        WHERE funcionario_id = ? 
        AND categoria = 'vale_funcionario'
        AND strftime('%Y-%m', vencimento) = ?
    '''
    vales_total = db.execute(vales_query, (id, month_str)).fetchone()['total'] or 0.0
    
    # 2. Ponto (Horas Extras / Atrasos) - MVP Estimates
    # TODO: Implement complex hour calculation. For now, we list days with potential issues.
    # We can just sum up columns if we parsed them as minutes? 
    # Current import logic saves raw strings "08:00". Parsing diffs is complex without a helper.
    # Let's skip auto-calc of hours for this step and just focus on Vales + Base + Taxes.
    # Future: Add Ponto Calc.
    
    # INSS Deduction
    inss_val = salario_base * inss_percent
    
    # FGTS
    fgts_val = salario_base * (func['fgts_percent'] if func['fgts_percent'] else 0.08)
    
    # Other Fixed Discounts
    descontos_list = json.loads(func['descontos_json']) if func['descontos_json'] else []
    
    # Calculate Net
    total_descontos = inss_val + vales_total
    
    for d in descontos_list:
        total_descontos += d.get('valor', 0)
        
    liquido = salario_base - total_descontos
    
    res_json = {
        'funcionario': func['nome'],
        'referencia': month_str,
        'salario_base': salario_base,
        'inss_val': inss_val,
        'fgts_val': fgts_val,
        'vales_val': vales_total,
        'outros_descontos': descontos_list,
        'liquido': liquido
    }
    
    log_audit(user_id, 'HOLERITE_GEN', f"Generated holerite for #{id}")
    return jsonify(res_json)

@flask_app.route('/holerite/print/<int:id>', methods=['GET'])
@jwt_required()
def holerite_print(id):
    user_id = get_jwt_identity()
    db = get_db()
    
    # Get Date Range (Query param: ?mes=YYYY-MM)
    month_str = request.args.get('mes')
    if not month_str:
        month_str = datetime.now().strftime('%Y-%m')
    
    # Fetch Employee
    func = db.execute('SELECT * FROM funcionarios WHERE id=?', (id,)).fetchone()
    if not func: return "Funcionário não encontrado", 404
    
    # Fetch Settings (for Company Header)
    # Settings is a Key-Value table, so we fetch all relevant keys
    rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'empresa_%'").fetchall()
    company_data = {row['key']: row['value'] for row in rows}
    
    defaults = {
        'empresa_nome': 'Minha Empresa', 
        'empresa_cnpj': '00.000.000/0000-00', 
        'empresa_endereco': 'Endereço não configurado'
    }
    settings = {**defaults, **company_data}
    
    # Logic (Replicated from api_holerite_calc for now)
    salario_base = func['salario_base']
    inss_percent = func['inss_percent'] if func['inss_percent'] else 0.11
    
    # Vales
    vales_query = '''
        SELECT SUM(valor) as total 
        FROM contas 
        WHERE funcionario_id = ? 
        AND categoria = 'vale_funcionario'
        AND strftime('%Y-%m', vencimento) = ?
    '''
    vales_total = db.execute(vales_query, (id, month_str)).fetchone()['total'] or 0.0
    
    inss_val = salario_base * inss_percent
    fgts_val = salario_base * (func['fgts_percent'] if func['fgts_percent'] else 0.08)
    
    descontos_list = json.loads(func['descontos_json']) if func['descontos_json'] else []
    
    total_descontos_adicionais = 0
    for d in descontos_list:
        total_descontos_adicionais += d.get('valor', 0)
        
    total_descontos = inss_val + vales_total + total_descontos_adicionais
    liquido = salario_base - total_descontos
    
    data = {
        'salario_base': salario_base,
        'inss_val': inss_val,
        'fgts_val': fgts_val,
        'vales_val': vales_total,
        'outros_descontos': descontos_list,
        'total_descontos': total_descontos,
        'liquido': liquido
    }
    
    return render_template('holerite_print.html', 
                          funcionario=func, 
                          empresa=settings, 
                          data=data, 
                          mes_referencia=month_str)

# --- API PONTO / FOLHA ---

@flask_app.route('/api/ponto/upload', methods=['POST'])
@jwt_required()
def api_ponto_upload():
    import pandas as pd
    user_id = get_jwt_identity()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    try:
        # Save temp file
        filename = secure_filename(file.filename)
        filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parse XLS
        try:
            xls = pd.ExcelFile(filepath)
            # Try to find sheet with data (usually '1.2.3' or similar, or just first one)
            sheet = '1.2.3' if '1.2.3' in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(filepath, sheet_name=sheet, header=None)
        except Exception as e:
            return jsonify({'error': f"Erro ao ler Excel: {str(e)}"}), 400
            
        db = get_db()
        logs = []
        
        # Process Blocks of 15 columns
        # Each employee block is 15 columns wide. 
        # Col 0 (of block): Date/Day (e.g. "01 QUA")
        # Col 1: Entrada 1
        # Col 3: Saída 1
        # Col 6: Entrada 2
        # Col 8: Saída 2
        # Col 8: Nome (Row 2 usually)
        
        num_cols = df.shape[1]
        block_size = 15
        
        for start_col in range(0, num_cols, block_size):
            # Check if block has data (Name at Row 2, Col index 8 relative to block start?? Let's check logic)
            # From analysis: Row 2, Col 9 (index 9) was 'lucas m'. 9 is relative to 0? matches.
            # Block 1 starts at 0. Name at 9.
            # Block 2 starts at 15. Name at 15+9 = 24. 'edivaldo'. matches analysis.
            
            name_col_idx = start_col + 9
            if name_col_idx >= num_cols: break
            
            emp_name = str(df.iloc[2, name_col_idx]).strip()
            if emp_name == 'nan': continue
            
            # Find or Create Mapping
            # Try to match with funcionarios table
            func = db.execute("SELECT id FROM funcionarios WHERE nome_ponto = ? OR nome LIKE ?", (emp_name, f"%{emp_name}%")).fetchone()
            
            func_id = None
            if func:
                func_id = func['id']
                # Auto-update nome_ponto if empty
                db.execute("UPDATE funcionarios SET nome_ponto = ? WHERE id = ? AND (nome_ponto IS NULL OR nome_ponto = '')", (emp_name, func_id))
            else:
                logs.append(f"Funcionario não encontrado: {emp_name}")
                continue
                
            # Parse Rows (Data starts around row 16 for first day? Need to be dynamic)
            # Analysis showed dates start around row 16 for 2025-01.
            # Let's scan for date pattern "DD DDD" (e.g. "01 QUA") in the first column of the block
            
            for i in range(10, min(50, len(df))):
                date_cell = str(df.iloc[i, start_col]).strip()
                # Pattern check: "01 QUA" or similar
                if len(date_cell) > 0 and date_cell[0].isdigit() and ' ' in date_cell:
                    # Found a date row
                    day_str = date_cell.split(' ')[0] # "01"
                    
                    # Construct date (Need Month/Year from file or input? tricky. File has it in row 3: "2025/01/01 ~ 01/31")
                    # For MVP, let's try to extract month/year from Row 3, or use current month if fails
                    try:
                        period_str = str(df.iloc[3, start_col+3]) # "2025/01/01 ~ 01/31"
                        year = int(period_str[0:4])
                        month = int(period_str[5:7])
                        full_date = f"{year}-{month:02d}-{day_str}"
                    except:
                        # Fallback: User should confirm, but for now use current year/month logical guess?
                        # Better: Parse filename "001_2025_1_MON.XLS" -> 2025, 1
                        try:
                            parts = filename.split('_')
                            full_date = f"{parts[1]}-{int(parts[2]):02d}-{day_str}"
                        except:
                            full_date = datetime.now().strftime(f"%Y-%m-{day_str}")
                    
                    # Extract Times
                    def get_time(r, c):
                        val = str(df.iloc[r, c]).strip()
                        return val if ':' in val else None

                    e1 = get_time(i, start_col + 1)
                    s1 = get_time(i, start_col + 3) # Saida 1 (Lunch Start)
                    e2 = get_time(i, start_col + 6) # Entrada 2 (Lunch End)
                    s2 = get_time(i, start_col + 8) # Saida 2 (End Day)
                    
                    # Calculate Extras/Delays (Simplified Logic for MVP)
                    # Real logic needs work shift config. For now just save raw times.
                    
                    # Upsert record
                    exists = db.execute("SELECT id FROM ponto_registros WHERE funcionario_id=? AND data=?", (func_id, full_date)).fetchone()
                    if exists:
                         db.execute("UPDATE ponto_registros SET entrada_1=?, saida_1=?, entrada_2=?, saida_2=? WHERE id=?", (e1, s1, e2, s2, exists['id']))
                    else:
                        db.execute("INSERT INTO ponto_registros (funcionario_id, data, entrada_1, saida_1, entrada_2, saida_2) VALUES (?, ?, ?, ?, ?, ?)",
                                   (func_id, full_date, e1, s1, e2, s2))
                                   
            logs.append(f"Processado: {emp_name}")

        db.commit()
        return jsonify({'success': True, 'logs': logs})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@flask_app.route('/api/ponto/registros', methods=['GET'])
@jwt_required()
def api_ponto_list():
    db = get_db()
    month = request.args.get('month') # YYYY-MM
    func_id = request.args.get('funcionario_id')
    
    query = '''
        SELECT p.*, f.nome 
        FROM ponto_registros p
        JOIN funcionarios f ON p.funcionario_id = f.id
    '''
    params = []
    clauses = []
    
    if month:
        clauses.append("strftime('%Y-%m', p.data) = ?")
        params.append(month)
        
    if func_id:
        clauses.append("p.funcionario_id = ?")
        params.append(func_id)
        
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
        
    query += " ORDER BY p.data DESC"
    
    rows = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])


# --- API CONTAS FINANCEIRAS PARA CALENDÁRIO ---

@flask_app.route('/api/financeiro/contas', methods=['GET'])
@jwt_required()
def api_financeiro_contas_list():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    
    # Buscar contas a receber (geradas por faturamento)
    contas_receber = db.execute('''
        SELECT id, 'receber' as tipo, descricao, valor, data_vencimento, status 
        FROM contas_receber 
        WHERE data_vencimento IS NOT NULL
    ''').fetchall()
    
    # Buscar contas a pagar (salários, etc)
    contas_pagar = db.execute('''
        SELECT id, 'pagar' as tipo, descricao, valor, data_vencimento, status 
        FROM contas_pagar 
        WHERE data_vencimento IS NOT NULL
    ''').fetchall()
    
    # Combinar resultados
    contas = list(contas_receber) + list(contas_pagar)
    db.close()
    
    return jsonify([dict(c) for c in contas])

@flask_app.route('/api/financeiro/contas', methods=['POST'])
@jwt_required()
def api_financeiro_contas_create():
    user_id = get_jwt_identity()
    data = request.json
    
    tipo = data.get('tipo', 'pagar')
    descricao = data.get('descricao')
    valor = data.get('valor')
    vencimento = data.get('vencimento')
    status = data.get('status', 'pendente') # pendente, pago
    categoria = data.get('categoria')
    funcionario_id = data.get('funcionario_id')
    
    if not descricao or not valor:
        return jsonify({'error': 'Dados incompletos'}), 400
        
    db = get_db()
    
    # Determine table based on existing schema separate tables or unified?
    # Schema passo 4 shows UNIFIED table 'contas'.
    # But get_contas_list uses 'contas_receber' and 'contas_pagar'.
    # WAIT. Schema Passo 4 created 'contas' unified.
    # But 'api_financeiro_contas_list' queries 'contas_receber' and 'contas_pagar'.
    # This implies the system might be in a hybrid state or I misread the schema usage.
    # Let's check if 'contas' table exists and is used.
    # Analyzing 'api_financeiro_contas_list' (lines 1260+):
    # It queries `contas_receber` and `contas_pagar`.
    # Schema Passo 4 (lines 15+) defines `contas`.
    # Did schema_passo4 run? The migration script for payroll used 'app.db'.
    # If the system uses separate tables, I should write to them.
    # BUT, 'vales' fits better in a unified 'contas' or 'contas_pagar'.
    # If I write to 'contas', but the list reads 'contas_pagar', the vale won't show up in the calendar if the calendar reads 'contas_pagar'.
    # LET'S CHECK if 'contas' table is actually used in 'api_relatorios_dashboard' (Line 1251+).
    # Line 1271: "SELECT ... FROM contas ..."
    # So Dashboard uses 'contas'. Calendar uses 'contas_pagar'/'contas_receber'.
    # This is INCONSISTENT. I should probably write to 'contas' AND maybe 'contas_pagar' if needed, or fix the read.
    # The prompt said "Refactoring Settings Page". I shouldn't refactor the whole Finance module if not asked, but I need Vales to work.
    # "Gestão de Vales e Folha" task says "Usar a tabela contas ...".
    # So I will write to 'contas' table. 
    # If Calendar needs to see it, Calendar should read 'contas' too.
    # Let's check api_calendar_events (Line 1339+).
    # Line 1435: "SELECT ... FROM contas ..."
    # So Calendar READS 'contas'.
    # The 'api_financeiro_contas_list' (Line 1103 in original, 1260 in current) reads 'contas_receber'/'contas_pagar'. This might be legacy or specific to a view.
    # I will write to 'contas'.
    
    db.execute('INSERT INTO contas (tipo, descricao, valor, vencimento, status, categoria, funcionario_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
               (tipo, descricao, valor, vencimento, status, categoria, funcionario_id))
    db.commit()
    
    log_audit(user_id, 'FIN_CREATE', f"Created transaction {tipo}: {descricao}")
    return jsonify({'success': True})


@flask_app.route('/api/orcamentos', methods=['GET'])
@jwt_required()
def api_orcamentos_list():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    orcamentos = db.execute('''
        SELECT id, client, client_id, status, created_at, 
               prazo_entrega, data_instalacao
        FROM orcamentos 
        ORDER BY created_at DESC
    ''').fetchall()
    db.close()
    return jsonify([dict(o) for o in orcamentos])

@flask_app.route('/api/orcamentos', methods=['POST'])
@jwt_required()
def api_orcamentos_create(): # Renamed from create_orcamento
    user_id = get_jwt_identity()
    data = request.json
    
    client_id = data.get('client_id')
    client = data.get('client')
    itens = json.dumps(data.get('itens'))
    total = data.get('total')
    total_horas_mo = data.get('total_horas_mo', 0) # New field
    
    db = get_db()
    cur = db.cursor()
    
    # Create Budget
    cur.execute('INSERT INTO orcamentos (client_id, client, itens_json, total, status, total_horas_mo) VALUES (?, ?, ?, ?, ?, ?)',
                (client_id, client, itens, total, data.get('status', 'Rascunho'), total_horas_mo)) # Added client_id
    orcamento_id = cur.lastrowid
    
    # Auto-create Kanban Card
    cur.execute('INSERT INTO cards_kanban (titulo, etapa, client, orcamento_id) VALUES (?, ?, ?, ?)',
                (f"Orç. #{orcamento_id} - {client}", "Contato", client, orcamento_id))
    
    log_audit(user_id, 'CREATE_ORCAMENTO', f'Created budget #{orcamento_id} for {client}')
    
    db.commit()
    return jsonify({'success': True, 'id': orcamento_id})

@flask_app.route('/api/orcamentos/<int:id>', methods=['GET'])
@jwt_required()
def get_orcamento(id):
    db = get_db()
    orc = db.execute('SELECT * FROM orcamentos WHERE id = ?', (id,)).fetchone()
    if not orc:
        return jsonify({'success': False, 'error': 'Orçamento não encontrado'}), 404
    
    return jsonify({'success': True, 'orcamento': dict(orc)})

@flask_app.route('/api/orcamentos/<int:id>', methods=['PUT'])
@jwt_required()
def update_orcamento(id):
    user_id = get_jwt_identity()
    data = request.json
    
    client_id = data.get('client_id')
    client = data.get('client')
    
    db = get_db()
    db.execute('''UPDATE orcamentos SET client_id=?, client=?, itens_json=?, total=?, total_horas_mo=?, status=? WHERE id=?''',
                (client_id, client, json.dumps(data.get('itens')), data.get('total'), data.get('total_horas_mo', 0), data.get('status'), id))
    
    log_audit(user_id, 'UPDATE_ORCAMENTO', f'Updated budget #{id}')
    db.commit()
    return jsonify({'success': True})

@flask_app.route('/api/orcamentos/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_orcamento(id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM orcamentos WHERE id = ?', (id,))
    db.execute('DELETE FROM cards_kanban WHERE orcamento_id = ?', (id,))
    db.commit()
    log_audit(user_id, 'DELETE_ORCAMENTO', f'Deleted budget #{id}')
    return jsonify({'success': True})

@flask_app.route('/api/kanban/update', methods=['POST'])
@jwt_required()
def api_kanban_update():
    data = request.json
    card_id = data.get('id')
    nova_etapa = data.get('etapa')
    db = get_db()
    db.execute('UPDATE cards_kanban SET etapa = ? WHERE id = ?', (nova_etapa, card_id))
    db.commit()
    return jsonify({'success': True})

@flask_app.route('/api/kanban/card', methods=['POST'])
@jwt_required()
def api_kanban_create():
    data = request.json
    titulo = data.get('titulo') # Nome do Lead
    client = data.get('client') # Telefone? Ou usar client como telefone e titulo como nome
    # Plan says: Titulo=Nome, Client=Telefone/Contato coverage
    
    obs = data.get('obs')
    data_json = json.dumps({'obs': obs})
    
    db = get_db()
    db.execute('INSERT INTO cards_kanban (titulo, etapa, client, orcamento_id, data_json) VALUES (?, ?, ?, ?, ?)',
               (titulo, 'Contato', client, None, data_json))
    db.commit()
    return jsonify({'success': True})

@flask_app.route('/api/kanban/convert/<int:id>', methods=['POST'])
@jwt_required()
def api_kanban_convert(id):
    user_id = get_jwt_identity()
    db = get_db()
    
    card = db.execute('SELECT * FROM cards_kanban WHERE id=?', (id,)).fetchone()
    if not card: return jsonify({'error': 'Card not found'}), 404
    
    if card['orcamento_id']:
        return jsonify({'error': 'Card already has budget'}), 400
        
    # Create Budget
    # Use card title as Client Name? Or Client field?
    # Logic: Titulo=Nome, Client=Telefone. 
    # Budget needs Client Name.
    data_json = json.loads(card['data_json']) if card['data_json'] else {}
    
    client_name = card['titulo']
    telefone = card['client']
    obs = data_json.get('obs', '')
    
    # Create empty budget
    cur = db.cursor()
    # Schema requires: client, itens_json, total (NOT NULL)
    # create_at is auto or provided.
    # We should provide empty itens_json '[]'
    
    cur.execute('''INSERT INTO orcamentos (client, status, total, itens_json, created_at, prazo_entrega) 
                   VALUES (?, ?, ?, ?, datetime('now'), ?)''',
                (client_name, 'Rascunho', 0.0, '[]', 
                 (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')))
    orcamento_id = cur.lastrowid
    
    # Link Card
    db.execute('UPDATE cards_kanban SET orcamento_id=?, etapa=? WHERE id=?', (orcamento_id, 'Orçamento', id))
    
    # Add initial description/obs to budget? Maybe as an item or internal note?
    # For now, just link.
    
    # Log
    log_audit(user_id, 'LEAD_CONVERT', f"Converted Lead #{id} to Budget #{orcamento_id}")
    db.commit()
    
    return jsonify({'success': True, 'orcamento_id': orcamento_id})

@flask_app.route('/api/kanban/card/<int:id>', methods=['PUT', 'DELETE'])
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
        
        # Preserve existing json if needed, or just overwrite obs
        # For simplicity, we rewrite data_json with obs
        data_json = json.dumps({'obs': obs})
        
        db.execute('UPDATE cards_kanban SET titulo=?, client=?, data_json=? WHERE id=?',
                   (titulo, client, data_json, id))
        db.commit()
        log_audit(user_id, 'UPDATE_CARD', f"Updated Kanban Card #{id}")
        return jsonify({'success': True})

@flask_app.route('/api/relatorios/melhor_compra')
@jwt_required()
def api_melhor_compra():
    db = get_db()
    query = '''
        SELECT nome, 
               MAX(custo_unitario) as preco_orcamento,
               MIN(custo_unitario) as preco_oportunidade,
               COUNT(*) as qtd_ofertas,
               unidade
        FROM estoque
        GROUP BY nome
        HAVING qtd_ofertas >= 1
        ORDER BY (MAX(custo_unitario) - MIN(custo_unitario)) DESC
    '''
    rows = db.execute(query).fetchall()
    
    result = []
    for r in rows:
        d = dict(r)
        best = db.execute('SELECT site_origem FROM estoque WHERE nome = ? AND custo_unitario = ?', 
                          (d['nome'], d['preco_oportunidade'])).fetchone()
        d['site_barato'] = best['site_origem'] if best else 'Manual'
        if d['preco_orcamento'] > 0:
            d['economia_percent'] = round(((d['preco_orcamento'] - d['preco_oportunidade']) / d['preco_orcamento']) * 100, 1)
        else:
            d['economia_percent'] = 0
        result.append(d)
    return jsonify(result)

@flask_app.route('/api/relatorios/dashboard')
@jwt_required()
def api_relatorios_dashboard():
    db = get_db()
    
    # Dates
    today = datetime.now()
    first_day = today.replace(day=1)
    
    # 1. Faturamento Mês (Orçamentos Aprovados/Concluídos neste mês)
    # Consideramos status que indicam venda fechada
    query_fat = '''
        SELECT SUM(total) as total 
        FROM orcamentos 
        WHERE status IN ('aprovado', 'producao', 'concluido', 'entregue')
        AND date(created_at) >= date(?)
    '''
    faturamento = db.execute(query_fat, (first_day.strftime('%Y-%m-%d'),)).fetchone()['total'] or 0.0
    
    # 2. Contas Pendentes (Pagar) - Geral
    query_contas = "SELECT SUM(valor) as total FROM contas WHERE tipo='pagar' AND status='pendente'"
    pendente = db.execute(query_contas).fetchone()['total'] or 0.0
    
    # 3. Lucro Estimado do Mês (Entradas Reais - Saídas Reais do Mês)
    # Entradas: Contas Receber (Pagas no mês) | Saídas: Contas Pagar (Pagas no mês)
    query_in = "SELECT SUM(valor) as t FROM contas WHERE tipo='receber' AND status='pago' AND strftime('%Y-%m', vencimento) = ?"
    query_out = "SELECT SUM(valor) as t FROM contas WHERE tipo='pagar' AND status='pago' AND strftime('%Y-%m', vencimento) = ?"
    
    mes_str = today.strftime('%Y-%m')
    entradas = db.execute(query_in, (mes_str,)).fetchone()['t'] or 0.0
    saidas = db.execute(query_out, (mes_str,)).fetchone()['t'] or 0.0
    lucro = entradas - saidas
    
    # 4. Fluxo de Caixa (Últimos 6 meses)
    # Agrupado por Mês: Receitas vs Despesas
    fluxo = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        m_str = d.strftime('%Y-%m')
        
        rec = db.execute("SELECT SUM(valor) as t FROM contas WHERE tipo='receber' AND strftime('%Y-%m', vencimento) = ?", (m_str,)).fetchone()['t'] or 0.0
        pag = db.execute("SELECT SUM(valor) as t FROM contas WHERE tipo='pagar' AND strftime('%Y-%m', vencimento) = ?", (m_str,)).fetchone()['t'] or 0.0
        
        fluxo.append({
            'label': d.strftime('%b/%Y'),
            'receita': rec,
            'despesa': pag
        })
        
    return jsonify({
        'faturamento_mes': faturamento,
        'contas_pendentes': pendente,
        'lucro_estimado': lucro,
        'fluxo_caixa': fluxo
    })

@flask_app.route('/api/relatorios/data')
@jwt_required()
def api_relatorios_data():
    db = get_db()
    # Get all transactions (receivables and payables) ordered by date
    query = '''
        SELECT descricao, valor, vencimento, tipo, status 
        FROM contas 
        ORDER BY vencimento DESC
        LIMIT 100
    '''
    rows = db.execute(query).fetchall()
    return jsonify([dict(r) for r in rows])

@flask_app.route('/api/relatorios/comercial')
@jwt_required()
def api_relatorios_comercial():
    db = get_db()
    
    # Top 5 Clientes por Valor Total de Orçamentos Aprovados
    query = '''
        SELECT c.nome, COUNT(o.id) as qtd_orcamentos, SUM(o.total) as valor_total
        FROM clientes c
        JOIN orcamentos o ON c.id = o.client_id
        WHERE o.status IN ('aprovado', 'producao', 'concluido', 'entregue')
        GROUP BY c.id
        ORDER BY valor_total DESC
        LIMIT 5
    '''
    rows = db.execute(query).fetchall()
    return jsonify([dict(r) for r in rows])

@flask_app.route('/api/calendar/events')
@jwt_required()
def api_calendar_events():
    import traceback
    import datetime
    
    try:
        db = get_db()
        events = []
        
        # --- GOOGLE CALENDAR FETCH ---
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            # Service Account Config
            SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
            SERVICE_ACCOUNT_FILE = 'gen-lang-client-0788488939-1a564ee56e26.json'
            
            # User provided Calendar ID
            CALENDAR_ID = 'ffdffc49c4127e4c3abffb421202eab6ff3f392866e60b532ad5bea2dc5232e4@group.calendar.google.com'

            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)

            service = build('calendar', 'v3', credentials=creds)

            # Calculate timeMin (e.g., from start of current month or similar)
            # For now, let's fetch events for the last 30 days and next 90 days
            now = datetime.datetime.utcnow()
            timeMin = (now - datetime.timedelta(days=30)).isoformat() + 'Z'
            
            events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=timeMin,
                                                maxResults=50, singleEvents=True,
                                                orderBy='startTime').execute()
            g_events = events_result.get('items', [])

            for ge in g_events:
                start = ge.get('start', {}).get('date') or ge.get('start', {}).get('dateTime')
                if start and 'T' in start:
                    start = start.split('T')[0] # Normalize to YYYY-MM-DD for now
                
                events.append({
                    'id': ge['id'],
                    'title': ge.get('summary', 'Evento Google'),
                    'start': start,
                    'type': 'google',
                    'description': ge.get('description', '')
                })
            
        except Exception as e:
            # Detailed logging for debugging
            with open("debug_api.txt", "a") as f:
                f.write(f"\n[{datetime.datetime.now()}] Google Calendar Error:\n")
                f.write(str(e) + "\n")
                if "Not Found" in str(e):
                    f.write("HINT: Verify if the Service Account is added to the Calendar settings (Share with specific people).\n")
                traceback.print_exc(file=f)
            print(f"Erro ao buscar Google Calendar: {e}")
            # Continue execution

        # --- INTERNAL EVENTS ---
        # 1. Orçamentos (Prazos, Instalação, Visitas)
        orcamentos = db.execute('SELECT id, client, prazo_entrega, data_instalacao, created_at, status FROM orcamentos').fetchall()
        for orc in orcamentos:
            # Prazo de Projeto
            if orc['prazo_entrega']:
                events.append({
                    'id': f"orc_{orc['id']}",
                    'title': f"Prazo: {orc['client']}",
                    'start': orc['prazo_entrega'],
                    'type': 'project',
                    'description': f"Orçamento #{orc['id']} - {orc['status']}"
                })
                
            # Instalação
            if orc['data_instalacao']:
                events.append({
                    'id': f"inst_{orc['id']}",
                    'title': f"Instalação: {orc['client']}",
                    'start': orc['data_instalacao'],
                    'type': 'install',
                    'description': f"Instalação confirmada - {orc['client']}"
                })

            # Visita (Simulada: Data de Criação do Orçamento = Contato/Visita)
            if orc['created_at']:
                events.append({
                    'id': f"visit_{orc['id']}",
                    'title': f"Visita/Contato: {orc['client']}",
                    'start': orc['created_at'].split(' ')[0], # YYYY-MM-DD
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

    except Exception as GlobalEx:
        # Catch-all for any other error causing 500
        with open("debug_api.txt", "a") as f:
            f.write(f"\n[{datetime.datetime.now()}] CRITICAL API ERROR:\n")
            f.write(str(GlobalEx) + "\n")
            traceback.print_exc(file=f)
        return jsonify({'error': str(GlobalEx)}), 500

# --- SCRAPER (MOCK) ---
import requests
from bs4 import BeautifulSoup
import time
import random


# --- REAL WEB SCRAPER ---
import requests
from bs4 import BeautifulSoup

def fetch_price_leomadeiras(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Selector: .price-template or .product-price
            price_elem = soup.select_one('.price-template .best-price') or soup.find(class_='product-price')
            if price_elem:
                price_text = price_elem.get_text().strip().replace('R$', '').replace('.', '').replace(',', '.')
                return float(price_text)
    except Exception as e:
        print(f"Erro LeoMadeiras: {e}")
    return 0.0

def fetch_price_madeverde(url):
    try:
        # Madeverde often requires CEP in cookie or session. 
        # Trying public page first.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cookie': 'cep=01310-100' # Tentar forçar CEP via cookie
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Selectors seen: .preco-venda, .preco-promocional
            price_elem = soup.select_one('.preco-promocional') or soup.select_one('.preco-venda')
            if price_elem:
                price_text = price_elem.get_text().strip().replace('R$', '').replace('.', '').replace(',', '.')
                return float(price_text)
    except Exception as e:
        print(f"Erro Madeverde: {e}")
    return 0.0

def fetch_price_madeiranit(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Selector: .product-info-main .price
            price_elem = soup.select_one('.product-info-main .price')
            if price_elem:
                price_text = price_elem.get_text().strip().replace('R$', '').replace('.', '').replace(',', '.')
                return float(price_text)
    except Exception as e:
        print(f"Erro Madeiranit: {e}")
    return 0.0

def raspador_site(site_name, url_override=None):
    """
    Raspador REAL que busca preços nos URLs definidos.
    Aceita url_override para raspar itens específicos do banco de dados.
    """
    items = []
    
    # URLs hardcoded (fallback)
    urls = {
        'leomadeiras': 'https://www.leomadeiras.com.br/p/10288987/mdf-branco-texturizado-fsc-15mm-2750x1850mm-2-faces-duratex',
        'madeverde': 'https://www.madeverde.com.br/mdf-naval-branco-tx-15mm-02-faces-duratex',
        'madeiranit': 'https://www.madeiranit.com.br/mdf-branco-texturizado-15mm-2-faces-185-x-275cm-duratex'
    }

    url = url_override if url_override else urls.get(site_name)
    
    if not url: return []

    price = 0.0
    # Se for override, não temos nome padrão fácil sem passar.
    # Mas o chamador já tem o nome. O raspador retorna items encontrados.
    # Vamos manter nome genérico se for override, o chamador atualiza o DB.
    nome_padrao = 'MDF Branco TX 15mm (Real Time)' if not url_override else 'Item Raspado'

    try:
        if site_name == 'leomadeiras':
            price = fetch_price_leomadeiras(url)
        elif site_name == 'madeverde':
            price = fetch_price_madeverde(url)
        elif site_name == 'madeiranit':
            price = fetch_price_madeiranit(url)
    except Exception as e:
        print(f"Erro raspando {site_name} ({url}): {e}")
        return []
    
    if price > 0:
        items.append({
            'nome': nome_padrao,
            'preco': price,
            'site': site_name
        })
    
    return items


def run_scraping_job(site_target='all'):
    """
    Executa a raspagem independente de contexto Flask para uso em threads.
    """
    sites = ['madeiranit', 'madeverde', 'leomadeiras']
    if site_target != 'all' and site_target in sites:
        sites = [site_target]
        
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    stats = {'updated': 0, 'created': 0, 'errors': 0, 'details': {}}
    
    for site in sites:
        try:
            items = raspador_site(site)
            site_stats = {'u': 0, 'c': 0}
            
            for item in items:
                existing = db.execute('SELECT id, custo_unitario FROM estoque WHERE nome = ? AND site_origem = ?', 
                                      (item['nome'], item['site'])).fetchone()
                
                if existing:
                    if existing['custo_unitario'] != item['preco']:
                        db.execute('UPDATE estoque SET custo_unitario=?, last_update=CURRENT_TIMESTAMP WHERE id=?',
                                   (item['preco'], existing['id']))
                        site_stats['u'] += 1
                else:
                    db.execute('INSERT INTO estoque (nome, categoria, unidade, quantidade, custo_unitario, site_origem) VALUES (?, ?, ?, ?, ?, ?)',
                               (item['nome'], 'Material Raspado', 'Unidade', 0, item['preco'], item['site']))
                    site_stats['c'] += 1
            
            stats['details'][site] = site_stats
            stats['updated'] += site_stats['u']
            stats['created'] += site_stats['c']
            
        except Exception as e:
            print(f"Erro raspando {site}: {e}")
            stats['errors'] += 1
            
    db.commit()
    db.close()
    return stats

def scraper_worker():
    """
    Verifica o horário para raspagem automática em background.
    """
    print("Scraper Worker iniciado.")
    while True:
        try:
            # Nova conexão por ciclo para evitar problemas de thread
            db = sqlite3.connect(DATABASE)
            db.row_factory = sqlite3.Row
            rows = db.execute('SELECT * FROM settings').fetchall()
            db.close()
            settings = {r['key']: r['value'] for r in rows}
            
            ativa = settings.get('raspagem_ativa') == 'true'
            hora = settings.get('raspagem_hora', '02:00')
            
            if ativa:
                agora = datetime.now().strftime('%H:%M')
                if agora == hora:
                    print(f"[{datetime.now()}] Iniciando raspagem agendada...")
                    run_scraping_job('all')
                    time.sleep(61) # Evita rodar no mesmo minuto
                    continue
        except Exception as e:
            print(f"Erro no Scraper Worker: {e}")
            
        time.sleep(30)

@flask_app.route('/api/estoque/raspar-individual', methods=['POST'])
@jwt_required()
def api_estoque_raspar_individual():
    user_id = get_jwt_identity()
    data = request.json
    item_id = data.get('item_id')
    
    if not item_id:
        return jsonify({'success': False, 'error': 'ID do item não fornecido'}), 400
    
    db = get_db()
    
    # Buscar item no estoque com todas as colunas
    item = db.execute('SELECT * FROM estoque WHERE id = ?', (item_id,)).fetchone()
    
    if not item:
        return jsonify({'success': False, 'error': 'Item não encontrado'}), 404
    
    try:
        # 1. Identificar URLs disponíveis
        urls = {
            'madeiranit': item['url_madeiranit'],
            'leomadeiras': item['url_leomadeiras'],
            'madeverde': item['url_madeverde']
        }
        
        # 2. Raspar cada fonte disponível
        precos_encontrados = {}
        updates = []
        params = []
        
        for source, url in urls.items():
            if url:
                # Chama o raspador para esta URL específica
                # NOTA: O raspador atual pode precisar de ajuste para aceitar URL direta
                # ou inferir o site pela URL. Assumindo que raspador_site(site, url) funcione
                # Se raspador_site espera apenas o NOME do site e busca internamente no DB, 
                # precisamos passar a URL se ela não estiver salva no 'site_origem'.
                # A implementação original do raspador parece ser genérica. 
                # Vamos simplificar e chamar o raspador passando a URL como argumento se possível, 
                # ou confiando que ele sabe lidar.
                
                # Para garantir, vamos simular a chamada correta ou ajustar o raspador.
                # Assumindo que raspador_site aceita (site_name, url_override=None)
                
                # Mockup temporário da lógica de raspagem real para múltiplas fontes
                # Na prática, você deve importar e usar a função real de scrap.
                # Aqui vamos manter a lógica original de chamada, mas adaptada.
                novos_items = raspador_site(source, url_override=url) 
                
                if novos_items:
                    # Pega o primeiro preço encontrado
                    novo_preco = novos_items[0]['preco']
                    precos_encontrados[source] = novo_preco
                    
                    # Adiciona ao update do banco
                    updates.append(f"preco_{source} = ?")
                    params.append(novo_preco)

        if not precos_encontrados:
             return jsonify({'success': False, 'error': 'Nenhuma URL válida ou falha na raspagem de todas as fontes'}), 500

        # 3. Determinar o Novo Custo Unitário com base na Estratégia
        strategy = item['price_strategy'] if item['price_strategy'] else 'auto_max'
        novo_custo = item['custo_unitario'] # Default: mantém o atual (manual)
        site_escolhido = item['site_origem']

        if strategy == 'auto_max':
            # Pega o maior preço encontrado
            if precos_encontrados:
                max_source = max(precos_encontrados, key=precos_encontrados.get)
                novo_custo = precos_encontrados[max_source]
                site_escolhido = max_source
        
        elif strategy in precos_encontrados:
            # Se a estratégia for um site específico e ele foi raspado
            novo_custo = precos_encontrados[strategy]
            site_escolhido = strategy
        
        # Se strategy for 'manual', não mudamos o novo_custo, mas atualizamos os precos_<source>

        # 4. Atualizar Banco de Dados
        updates.append("custo_unitario = ?")
        params.append(novo_custo)
        
        updates.append("site_origem = ?")
        params.append(site_escolhido)
        
        updates.append("last_update = datetime('now')")
        
        # Adiciona ID ao final
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

@flask_app.route('/api/estoque/ids-para-raspar', methods=['GET'])
@jwt_required()
def api_estoque_ids_para_raspar():
    db = get_db()
    # Select items that have at least one URL configured
    query = '''
        SELECT id FROM estoque 
        WHERE (url_madeiranit IS NOT NULL AND url_madeiranit != '')
           OR (url_leomadeiras IS NOT NULL AND url_leomadeiras != '')
           OR (url_madeverde IS NOT NULL AND url_madeverde != '')
    '''
    rows = db.execute(query).fetchall()
    ids = [row[0] for row in rows]
    
    return jsonify({'ids': ids, 'count': len(ids)})

@flask_app.route('/api/estoque/raspar', methods=['POST'])
@jwt_required()
def api_estoque_raspar():
    user_id = get_jwt_identity()
    data = request.json
    target = data.get('site', 'all')
    
    stats = run_scraping_job(target)
    
    log_audit(user_id, 'ESTOQUE_RASPAGEM', f"Scraped {target}. U:{stats['updated']} C:{stats['created']}")
    return jsonify({'success': True, 'stats': stats})

# Expose the ASGI app as 'app' to match the command: uvicorn app:app
init_db()

# Iniciar scraper em background (evita duplicar no reloader do Flask)
# TEMPORARIAMENTE DESATIVADO
# if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not flask_app.debug:
#     if not any(t.name == "ScraperThread" for t in threading.enumerate()):
#         threading.Thread(target=scraper_worker, daemon=True, name="ScraperThread").start()

app = WsgiToAsgi(flask_app)


# --- API CLIENTES ---

@flask_app.route('/api/clientes', methods=['GET'])
@jwt_required()
def api_clientes_list():
    db = get_db()
    clientes = db.execute('''
        SELECT c.*, 
               (SELECT MAX(o.created_at) FROM orcamentos o WHERE o.client_id = c.id) as ultimo_orcamento
        FROM clientes c 
        ORDER BY c.nome
    ''').fetchall()
    return jsonify([dict(c) for c in clientes])

@flask_app.route('/api/clientes', methods=['POST'])
@jwt_required()
def api_clientes_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    # Validation for minimal required fields (Name and Phone/WhatsApp)
    if not data.get('nome'):
        return jsonify({'success': False, 'error': 'Nome é obrigatório'}), 400
        
    try:
        cursor = db.execute('''
        INSERT INTO clientes (nome, cpf_cnpj, data_nascimento, tipo_pessoa, telefone, whatsapp, 
                             email, cep, logradouro, numero, complemento, bairro, cidade, estado, 
                             status, origem, observacoes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (
            data.get('nome'), 
            data.get('cpf_cnpj'), 
            data.get('data_nascimento'), 
            data.get('tipo_pessoa', 'fisica'),
            data.get('telefone'), 
            data.get('whatsapp'), 
            data.get('email'), 
            data.get('cep'),
            data.get('logradouro'), 
            data.get('numero'), 
            data.get('complemento'), 
            data.get('bairro'),
            data.get('cidade'), 
            data.get('estado'), 
            data.get('status', 'ativo'), 
            data.get('origem'),
            data.get('observacoes')
        ))
        db.commit()
        
        log_audit(user_id, 'CLIENTE_CREATE', f"Created client: {data.get('nome')}")
        return jsonify({'success': True, 'id': cursor.lastrowid})
    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@flask_app.route('/api/clientes/<int:cliente_id>', methods=['GET'])
@jwt_required()
def api_clientes_get(cliente_id):
    db = get_db()
    cliente = db.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
    
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente não encontrado'}), 404
    
    return jsonify({'success': True, 'cliente': dict(cliente)})

@flask_app.route('/api/clientes/<int:cliente_id>', methods=['PUT'])
@jwt_required()
def api_clientes_update(cliente_id):
    user_id = get_jwt_identity()
    data = request.json
    
    db = get_db()
    db.execute('''
        UPDATE clientes SET 
            nome = ?, cpf_cnpj = ?, data_nascimento = ?, tipo_pessoa = ?, telefone = ?, 
            whatsapp = ?, email = ?, cep = ?, logradouro = ?, numero = ?, complemento = ?, 
            bairro = ?, cidade = ?, estado = ?, status = ?, origem = ?, observacoes = ?,
            updated_at = datetime('now')
        WHERE id = ?
    ''', (
        data.get('nome'), data.get('cpf_cnpj'), data.get('data_nascimento'), data.get('tipo_pessoa'),
        data.get('telefone'), data.get('whatsapp'), data.get('email'), data.get('cep'),
        data.get('logradouro'), data.get('numero'), data.get('complemento'), data.get('bairro'),
        data.get('cidade'), data.get('estado'), data.get('status'), data.get('origem'),
        data.get('observacoes'), cliente_id
    ))
    db.commit()
    
    log_audit(user_id, 'CLIENTE_UPDATE', f"Updated client: {data.get('nome')}")
    return jsonify({'success': True})

@flask_app.route('/api/clientes/<int:cliente_id>', methods=['DELETE'])
@jwt_required()
def api_clientes_delete(cliente_id):
    user_id = get_jwt_identity()
    
    db = get_db()
    
    # Verificar se cliente tem orçamentos
    has_orcamentos = db.execute('SELECT COUNT(*) FROM orcamentos WHERE client_id = ?', (cliente_id,)).fetchone()[0]
    if has_orcamentos > 0:
        return jsonify({'success': False, 'error': 'Cliente possui orçamentos vinculados'}), 400
    
    db.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
    db.commit()
    
    log_audit(user_id, 'CLIENTE_DELETE', f"Deleted client ID: {cliente_id}")
    return jsonify({'success': True})

@flask_app.route('/clientes')
@jwt_required()
def clientes_page():
    return render_template('clientes.html')



# --- API PRICE GROUPS ---

@flask_app.route('/api/price-groups', methods=['GET'])
@jwt_required()
def api_price_groups_list():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    groups = db.execute('SELECT * FROM price_groups ORDER BY name').fetchall()
    db.close()
    return jsonify([dict(g) for g in groups])

@flask_app.route('/api/price-groups', methods=['POST'])
@jwt_required()
def api_price_groups_create():
    user_id = get_jwt_identity()
    data = request.json
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO price_groups (name, price, description) VALUES (?, ?, ?)
    ''', (data.get('name'), data.get('price'), data.get('description')))
    db.commit()
    db.close()
    log_audit(user_id, 'PRICE_GROUP_CREATE', f"Created group {data.get('name')}")
    return jsonify({'success': True})

@flask_app.route('/api/price-groups/<int:id>', methods=['PUT'])
@jwt_required()
def api_price_groups_update(id):
    user_id = get_jwt_identity()
    data = request.json
    db = sqlite3.connect(DATABASE)
    db.execute('UPDATE price_groups SET name=?, price=?, description=? WHERE id=?',
               (data.get('name'), data.get('price'), data.get('description'), id))
    db.commit()
    db.close()
    log_audit(user_id, 'PRICE_GROUP_UPDATE', f"Updated group ID {id}")
    return jsonify({'success': True})

@flask_app.route('/api/price-groups/<int:id>', methods=['DELETE'])
@jwt_required()
def api_price_groups_delete(id):
    user_id = get_jwt_identity()
    db = sqlite3.connect(DATABASE)
    # Check usage
    count = db.execute('SELECT COUNT(*) FROM estoque WHERE price_group_id = ?', (id,)).fetchone()[0]
    if count > 0:
        db.close()
        return jsonify({'success': False, 'error': 'Grupo em uso por itens de estoque'}), 400
    
    db.execute('DELETE FROM price_groups WHERE id=?', (id,))
    db.commit()
    db.close()
    log_audit(user_id, 'PRICE_GROUP_DELETE', f"Deleted group ID {id}")
    return jsonify({'success': True})

# --- END API PRICE GROUPS ---

if __name__ == '__main__':
    # Initialize DB (Seed defaults)
    init_db()
    # Use 'uvicorn app:app --reload' instead of running directly
    flask_app.run(debug=True)
