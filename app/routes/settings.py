from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity, current_user
from app.database import get_db

bp = Blueprint('settings', __name__)

@bp.route('/settings')
@jwt_required()
def settings():
    # Role logic should be handled by decorators or within logic. 
    # db logic for user role check is complex without loading user from DB.
    # But current_user is available via JWT callback if configured? 
    # In __init__.py we set user_lookup_callback.
    # So current_user should work.
    
    if current_user and current_user['role'] != 'admin':
        flash('Acesso restrito a administradores.', 'error')
        return redirect(url_for('dashboard.dashboard'))
    return render_template('settings.html')

@bp.route('/api/settings', methods=['GET'])
@jwt_required()
def api_settings_list():
    db = get_db()
    rows = db.execute('SELECT * FROM settings').fetchall()
    return jsonify({r['key']: r['value'] for r in rows})

@bp.route('/api/settings', methods=['POST'])
@jwt_required()
def api_settings_update():
    data = request.json
    db = get_db()
    for key, value in data.items():
        db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/config-fabrica', methods=['GET'])
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

@bp.route('/api/config-fabrica', methods=['POST'])
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

@bp.route('/api/users', methods=['GET'])
@jwt_required()
def api_users_list():
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    db = get_db()
    users = db.execute('SELECT id, username, role, is_active, whatsapp FROM users').fetchall()
    return jsonify([dict(u) for u in users])

@bp.route('/api/users', methods=['POST'])
@jwt_required()
def api_users_create():
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    db = get_db()
    
    # Check existing
    exists = db.execute('SELECT id FROM users WHERE username = ?', (data.get('username'),)).fetchone()
    if exists:
        return jsonify({'error': 'Usuário já existe'}), 400
        
    db.execute('INSERT INTO users (username, password, role, is_active, whatsapp) VALUES (?, ?, ?, 1, ?)',
               (data.get('username'), data.get('password'), data.get('role', 'user'), data.get('whatsapp')))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/users/<int:id>', methods=['PUT'])
@jwt_required()
def api_users_update(id):
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    db = get_db()
    
    fields = []
    values = []
    
    if 'role' in data:
        fields.append('role=?')
        values.append(data['role'])
    
    if 'password' in data and data['password']:
        fields.append('password=?')
        values.append(data['password'])
        
    if 'is_active' in data:
        fields.append('is_active=?')
        values.append(int(data['is_active']))
        
    if 'whatsapp' in data:
        fields.append('whatsapp=?')
        values.append(data['whatsapp'])
        
    if not fields:
        return jsonify({'success': True}) # Nothing to update
        
    values.append(id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id=?"
    db.execute(query, tuple(values))
    db.commit()
    
    return jsonify({'success': True})

@bp.route('/api/users/<int:id>', methods=['DELETE'])
@jwt_required()
def api_users_delete(id):
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Soft delete
    db = get_db()
    db.execute('UPDATE users SET is_active = 0 WHERE id = ?', (id,))
    db.commit()
    
    return jsonify({'success': True})
