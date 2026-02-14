from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
import sqlite3

bp = Blueprint('clientes', __name__)

@bp.route('/clientes')
@jwt_required()
def clientes():
    return render_template('clientes.html')

@bp.route('/api/clientes', methods=['GET'])
@jwt_required()
def api_clientes_list():
    db = get_db()
    
    # Check for query params (search)
    search_term = request.args.get('q')
    
    query = "SELECT * FROM clientes"
    params = []
    
    if search_term:
        query += " WHERE nome LIKE ? OR cpf_cnpj LIKE ? OR email LIKE ?"
        term = f"%{search_term}%"
        params = [term, term, term]
        
    query += " ORDER BY nome"
    
    clientes = db.execute(query, params).fetchall()
    return jsonify([dict(c) for c in clientes])

@bp.route('/api/clientes', methods=['POST'])
@jwt_required()
def api_clientes_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
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

@bp.route('/api/clientes/<int:id>', methods=['GET'])
@jwt_required()
def api_clientes_get(id):
    db = get_db()
    cliente = db.execute('SELECT * FROM clientes WHERE id = ?', (id,)).fetchone()
    if not cliente:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify(dict(cliente))

@bp.route('/api/clientes/<int:id>', methods=['PUT'])
@jwt_required()
def api_clientes_update(id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    try:
        db.execute('''
        UPDATE clientes SET nome=?, cpf_cnpj=?, data_nascimento=?, tipo_pessoa=?, telefone=?, whatsapp=?, 
                             email=?, cep=?, logradouro=?, numero=?, complemento=?, bairro=?, cidade=?, estado=?, 
                             status=?, origem=?, observacoes=?, updated_at=datetime('now')
        WHERE id = ?
        ''', (
            data.get('nome'), 
            data.get('cpf_cnpj'), 
            data.get('data_nascimento'), 
            data.get('tipo_pessoa'),
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
            data.get('status'), 
            data.get('origem'),
            data.get('observacoes'),
            id
        ))
        db.commit()
        log_audit(user_id, 'CLIENTE_UPDATE', f"Updated client #{id}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/clientes/<int:id>', methods=['DELETE'])
@jwt_required()
def api_clientes_delete(id):
    user_id = get_jwt_identity()
    db = get_db()
    try:
        db.execute('DELETE FROM clientes WHERE id = ?', (id,))
        db.commit()
        log_audit(user_id, 'CLIENTE_DELETE', f"Deleted client #{id}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
