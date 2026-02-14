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
