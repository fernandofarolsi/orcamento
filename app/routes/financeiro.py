from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
from datetime import datetime
import json

bp = Blueprint('financeiro', __name__)

@bp.route('/financeiro')
@jwt_required()
def financeiro():
    return render_template('financeiro.html')

# --- API FINANCEIRO (CONTAS) ---

@bp.route('/api/contas', methods=['GET'])
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

@bp.route('/api/contas', methods=['POST'])
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

@bp.route('/api/contas/<int:id>', methods=['DELETE'])
@jwt_required()
def api_contas_delete(id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM contas WHERE id=?', (id,))
    db.commit()
    log_audit(user_id, 'CONTA_DELETE', f"Deleted conta #{id}")
    return jsonify({'success': True})

@bp.route('/api/contas/orcamento/<int:orc_id>', methods=['POST'])
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
        from datetime import timedelta
        hoje = datetime.now()
        
        for i in range(parcelas):
            venc = hoje + timedelta(days=30 * (i+1))
            desc = f"Parc. {i+1}/{parcelas} Orç. #{orc_id} ({metodo})"
            db.execute('INSERT INTO contas (tipo, descricao, valor, vencimento, status, categoria, orcamento_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       ('receber', desc, valor_parcela, venc.strftime('%Y-%m-%d'), 'pendente', 'venda_parcela', orc_id))

    # 3. Save Payment Info in Orcamento
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


# --- API CUSTOS FIXOS ---

@bp.route('/api/custos_fixos', methods=['GET'])
@jwt_required()
def api_custos_fixos_list():
    db = get_db()
    items = db.execute('SELECT * FROM custos_fixos ORDER BY descricao').fetchall()
    return jsonify([dict(ix) for ix in items])

@bp.route('/api/custos_fixos', methods=['POST'])
@jwt_required()
def api_custos_fixos_create():
    data = request.json
    db = get_db()
    db.execute('INSERT INTO custos_fixos (descricao, valor, categoria) VALUES (?, ?, ?)',
               (data.get('descricao'), data.get('valor'), data.get('categoria')))
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/custos_fixos/<int:id>', methods=['DELETE'])
@jwt_required()
def api_custos_fixos_delete(id):
    db = get_db()
    db.execute('DELETE FROM custos_fixos WHERE id=?', (id,))
    db.commit()
    return jsonify({'success': True})
