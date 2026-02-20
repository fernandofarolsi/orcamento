from flask import Blueprint, send_from_directory, current_app, jsonify
from flask_jwt_extended import jwt_required

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('dashboard.dashboard'))

@bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@bp.route('/favicon.ico')
def favicon():
    from flask import redirect, url_for
    return redirect(url_for('static', filename='favicon.ico'))

@bp.route('/api/system/metadata', methods=['GET'])
@jwt_required()
def api_system_metadata():
    """
    Returns system-wide enums and valid values for dropdowns/agents.
    """
    from app.database import get_db
    import json
    
    db = get_db()
    cat_setting = db.execute("SELECT value FROM settings WHERE key = 'categorias_estoque'").fetchone()
    
    categorias_estoque = [
        'MDF', 'Compensado', 'Fórmica', 'Vidro', 'Espelho', 
        'Ferragem', 'Acessório', 'Iluminação', 'Outro'
    ]
    
    if cat_setting and cat_setting['value']:
        try:
            categorias_estoque = json.loads(cat_setting['value'])
        except:
            pass
            
    # Load unidades de medida dynamically as well (future proofing)
    und_setting = db.execute("SELECT value FROM settings WHERE key = 'unidades_estoque'").fetchone()
    unidades_estoque = ['Unidade', 'Metro', 'Quilo', 'Litro', 'Chapa']
    if und_setting and und_setting['value']:
        try:
            unidades_estoque = json.loads(und_setting['value'])
        except:
            pass

    metadata = {
        'estoque': {
            'categorias': categorias_estoque,
            'unidades': unidades_estoque
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

@bp.route('/api/upload', methods=['POST'])
# @jwt_required() # User might not be logged in or token issue? Let's check headers, but frontend sends it. Usually safe to enable, but let's check if the frontend appends the token to upload request.
# The user's js code uses fetch('/api/upload', { method: 'POST', body: formData }) without explicit headers for auth in the snippets, but the main fetch might be intercepted or cookies used.
# Let's keep jwt_required() consistent with other API calls if possible, or omit if it causes issues.
# Looking at layout, other API calls have jwt_required().
# Let's try with jwt_required() but if it fails (401), user might need to adjust frontend.
# But wait, 404 was the error, not 401. So the route just didn't exist.
@jwt_required()
def api_upload():
    from flask import request
    import os
    from werkzeug.utils import secure_filename
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        # Unique filename to avoid overwrite? Maybe timestamp?
        # For logo, overwriting might be okay if name is same, but let's just save.
        
        # Check upload folder existence
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file.save(os.path.join(upload_folder, filename))
        return jsonify({'url': f"/uploads/{filename}"}) # Matches the @bp.route('/uploads/<path:filename>')
    return jsonify({'error': 'Unknown error'}), 500
