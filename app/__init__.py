import os
from flask import Flask, send_from_directory, jsonify, redirect, url_for
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

from .database import get_db, close_connection
from .utils import count_json_items, date_format_filter, status_color_filter, from_json_filter, format_currency

load_dotenv()

def create_app(test_config=None):
    # Initialize Flask app
    app = Flask(__name__, instance_relative_config=True)

    # Configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key'),
        JWT_SECRET_KEY=os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret'),
        JWT_TOKEN_LOCATION=['cookies'],
        JWT_COOKIE_CSRF_PROTECT=False, # MVP shortcut
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads'), # Store uploads in static for easier serving or keep separate?
        # Original code used 'uploads' in root. Let's keep it consistent or move to instance.
        # Let's use a dedicated uploads folder in the root for now to avoid losing data if we just moved static.
        # Wait, previous move command moved static/* to app/static.
        # Let's verify where uploads are. They were likely in root/uploads.
        # I did not move root/uploads in the previous step.
    )
    
    # Fix Upload Folder Path
    # If we want to keep using 'uploads' in the root project dir:
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(app.root_path), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    if test_config:
        app.config.update(test_config)

    # Register Extensions
    jwt = JWTManager(app)

    # Register Database Teardown
    app.teardown_appcontext(close_connection)

    # Register Filters
    app.template_filter('count_items')(count_json_items)
    app.template_filter('date_format')(date_format_filter)
    app.template_filter('status_color')(status_color_filter)
    app.template_filter('from_json')(from_json_filter)
    app.template_filter('format_currency')(format_currency)

    # Context Processors
    @app.context_processor
    def inject_company_settings():
        try:
            db = get_db()
            rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'empresa_%'").fetchall()
            company = {row['key']: row['value'] for row in rows}
            
            defaults = {
                'empresa_nome': 'Adore Marcenaria',
                'empresa_logo_url': '/static/logo.jpg',
                'empresa_cnpj': '',
                'empresa_endereco': '',
                'empresa_telefone': '',
                'empresa_email': ''
            }
            return dict(company={**defaults, **company})
        except Exception as e:
            print(f"Error injecting settings: {e}")
            return dict(company={'empresa_nome': 'Adore Marcenaria', 'empresa_logo_url': '/static/logo.jpg'})

    @app.context_processor
    def inject_user():
        from flask_jwt_extended import current_user
        return dict(current_user=current_user)

    # JWT Callbacks
    # JWT Callbacks
    @jwt.unauthorized_loader
    def custom_unauthorized_response(_err):
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify({"msg": "Missing Authorization Header"}), 401
        return redirect(url_for('auth.login'))

    @jwt.expired_token_loader
    def custom_expired_token_response(_hdr, _payload):
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify({"msg": "Token has expired", "error": "token_expired"}), 401
        return redirect(url_for('auth.login'))
    
    @jwt.invalid_token_loader
    def custom_invalid_token_response(_err):
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify({"msg": "Invalid Token"}), 401
        return redirect(url_for('auth.login'))

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        db = get_db()
        return db.execute("SELECT * FROM users WHERE id = ?", (identity,)).fetchone()

    # Register Blueprints (Import here to avoid circular dependencies)
    from .routes import auth, dashboard, kanban, orcamentos, clientes, estoque, financeiro, funcionarios, settings, main, catalogo, relatorios, tiers, crm, whatsapp, whatsapp_webhook
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(kanban.bp)
    app.register_blueprint(orcamentos.bp)
    app.register_blueprint(clientes.bp)
    app.register_blueprint(estoque.bp)
    app.register_blueprint(financeiro.bp)
    app.register_blueprint(funcionarios.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(catalogo.bp)
    app.register_blueprint(relatorios.bp)
    app.register_blueprint(tiers.bp)
    app.register_blueprint(crm.bp)
    app.register_blueprint(whatsapp.bp)
    app.register_blueprint(whatsapp_webhook.bp)

    # Prototype Route (Temporary)
    from .routes import prototype
    app.register_blueprint(prototype.bp)

    # Client Profile Route
    from .routes import client_profile
    app.register_blueprint(client_profile.bp)

    return app
