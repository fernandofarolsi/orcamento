from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required
from app.database import get_db

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@jwt_required()
def dashboard():
    return render_template('dashboard_kpi.html')

@bp.route('/relatorios')
@jwt_required()
def relatorios():
    return render_template('relatorios.html')

@bp.route('/api/kpis')
@jwt_required()
def api_kpis():
    db = get_db()
    
    # 1. Faturamento Mês (Sum orcamentos aprovados/contas receber)
    faturamento = db.execute("SELECT SUM(valor) as total FROM contas WHERE tipo='receber' AND strftime('%Y-%m', vencimento) = strftime('%Y-%m', 'now')").fetchone()['total'] or 0
    
    # 2. Orçamentos (Total vs Approved)
    total_orc = db.execute("SELECT COUNT(*) as c FROM orcamentos").fetchone()['c']
    
    # 3. Estoque Crítico (< 10)
    estoque_crit = db.execute("SELECT COUNT(*) as c FROM estoque WHERE quantidade < 10 AND quantidade > 0").fetchone()['c']
    
    # 4. Clientes Novos (This Month)
    clientes = db.execute("SELECT COUNT(DISTINCT client) as c FROM orcamentos WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')").fetchone()['c']
    
    # 5. Contas Vencidas
    vencidas = db.execute("SELECT SUM(valor) as total FROM contas WHERE tipo='pagar' AND status='pendente' AND vencimento < date('now')").fetchone()['total'] or 0
    
    # 6. Margem Média Projetos (Target from Config)
    config = db.execute('SELECT margem_lucro FROM config_fabrica LIMIT 1').fetchone()
    margem = (config['margem_lucro'] * 100) if config else 35.0

    # 7. Charts Data
    # A. Faturamento (Last 30 days)
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

@bp.route('/api/logs', methods=['GET'])
@jwt_required()
def api_logs_list():
    db = get_db()
    
    # Auto-cleanup older than 1 year
    try:
        db.execute("DELETE FROM audits WHERE ts < date('now', '-1 year')")
        db.commit()
    except:
        pass 
        
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    action = request.args.get('action')
    user = request.args.get('user')
    limit = request.args.get('limit', 50)
    
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
