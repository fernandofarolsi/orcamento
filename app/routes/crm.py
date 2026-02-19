from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
import datetime

bp = Blueprint('crm', __name__)

@bp.route('/contatos')
@jwt_required()
def contatos_index():
    return render_template('contatos.html')

@bp.route('/api/contatos', methods=['GET'])
@jwt_required()
def api_contatos_list():
    db = get_db()
    query = "SELECT * FROM crm_contatos ORDER BY nome"
    rows = db.execute(query).fetchall()
    return jsonify([dict(row) for row in rows])

@bp.route('/api/contatos', methods=['POST'])
@jwt_required()
def api_contatos_create():
    data = request.json
    db = get_db()
    try:
        db.execute('''INSERT INTO crm_contatos (nome, tipo, telefone, email, origem, observacoes, google_resource_name) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (data.get('nome'), data.get('tipo', 'lead'), data.get('telefone'), 
                    data.get('email'), data.get('origem', 'manual'), data.get('observacoes'), 
                    data.get('google_resource_name')))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/contatos/<int:id>', methods=['PUT'])
@jwt_required()
def api_contatos_update(id):
    data = request.json
    db = get_db()
    try:
        db.execute('''UPDATE crm_contatos SET nome=?, tipo=?, telefone=?, email=?, 
                      origem=?, observacoes=?, google_resource_name=?, updated_at=CURRENT_TIMESTAMP 
                      WHERE id=?''',
                   (data.get('nome'), data.get('tipo'), data.get('telefone'), 
                    data.get('email'), data.get('origem'), data.get('observacoes'), 
                    data.get('google_resource_name'), id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/contatos/<int:id>', methods=['DELETE'])
@jwt_required()
def api_contatos_delete(id):
    db = get_db()
    db.execute('DELETE FROM crm_contatos WHERE id=?', (id,))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/contatos/sync', methods=['POST'])
@jwt_required()
def api_contatos_sync():
    # Placeholder for Google Sync Logic
    # 1. Fetch from Google
    # 2. Update local DB
    # 3. Push local changes to Google
    
    # Simulating sync for now
    import time
    time.sleep(1)
    
    return jsonify({'success': True, 'message': 'Sincronização simulada com sucesso (Lógica pendente)'})

@bp.route('/api/contatos/import', methods=['POST'])
@jwt_required()
def api_contatos_import():
    # Import from existing Clientes/Funcionarios tables
    db = get_db()
    count = 0
    
    # Import Clientes
    clientes = db.execute("SELECT * FROM clientes").fetchall()
    for c in clientes:
        exists = db.execute("SELECT id FROM crm_contatos WHERE nome = ?", (c['nome'],)).fetchone()
        if not exists:
            db.execute('''INSERT INTO crm_contatos (nome, tipo, telefone, email, origem, observacoes) 
                          VALUES (?, 'cliente', ?, ?, ?, ?)''',
                       (c['nome'], c['telefone'] or c['whatsapp'], c['email'], 'sistema_antigo', f"Importado de Clientes ID {c['id']}"))
            count += 1
            
    # Import Funcionarios
    funcionarios = db.execute("SELECT * FROM funcionarios").fetchall()
    for f in funcionarios:
        exists = db.execute("SELECT id FROM crm_contatos WHERE nome = ?", (f['nome'],)).fetchone()
        if not exists:
            db.execute('''INSERT INTO crm_contatos (nome, tipo, telefone, email, origem, observacoes) 
                          VALUES (?, 'funcionario', '', '', 'sistema_antigo', f"Importado de Funcionarios ID {f['id']}")''',
                       (f['nome'],))
            count += 1
            
    db.commit()
    return jsonify({'success': True, 'imported': count})
