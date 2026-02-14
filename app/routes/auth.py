from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
from app.database import get_db, log_audit

bp = Blueprint('auth', __name__)

@bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@bp.route('/login', methods=['GET', 'POST'])
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
            resp = make_response(redirect(url_for('dashboard.dashboard'))) # Assuming dashboard blueprint
            set_access_cookies(resp, access_token)
            
            log_audit(user['id'], 'LOGIN_SUCCESS', 'User logged in')
            return resp
        
        flash('Usuário ou senha inválidos', 'error')
        
    return render_template('login.html')

@bp.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    resp = jsonify({'success': True})
    unset_jwt_cookies(resp)
    return resp
