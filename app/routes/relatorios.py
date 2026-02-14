from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db
from datetime import datetime, timedelta

bp = Blueprint('relatorios', __name__)

@bp.route('/relatorios')
@jwt_required()
def relatorios():
    return render_template('relatorios.html')

@bp.route('/api/relatorios/dashboard')
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
    faturamento_row = db.execute(query_fat, (first_day.strftime('%Y-%m-%d'),)).fetchone()
    faturamento = faturamento_row['total'] if faturamento_row and faturamento_row['total'] else 0.0
    
    # 2. Contas Pendentes (Pagar) - Geral
    query_contas = "SELECT SUM(valor) as total FROM contas WHERE tipo='pagar' AND status='pendente'"
    pendente_row = db.execute(query_contas).fetchone()
    pendente = pendente_row['total'] if pendente_row and pendente_row['total'] else 0.0
    
    # 3. Lucro Estimado do Mês (Entradas Reais - Saídas Reais do Mês)
    # Entradas: Contas Receber (Pagas no mês) | Saídas: Contas Pagar (Pagas no mês)
    query_in = "SELECT SUM(valor) as t FROM contas WHERE tipo='receber' AND status='pago' AND strftime('%Y-%m', vencimento) = ?"
    query_out = "SELECT SUM(valor) as t FROM contas WHERE tipo='pagar' AND status='pago' AND strftime('%Y-%m', vencimento) = ?"
    
    mes_str = today.strftime('%Y-%m')
    entradas_row = db.execute(query_in, (mes_str,)).fetchone()
    entradas = entradas_row['t'] if entradas_row and entradas_row['t'] else 0.0
    
    saidas_row = db.execute(query_out, (mes_str,)).fetchone()
    saidas = saidas_row['t'] if saidas_row and saidas_row['t'] else 0.0
    
    lucro = entradas - saidas
    
    # 4. Fluxo de Caixa (Últimos 6 meses)
    # Agrupado por Mês: Receitas vs Despesas
    fluxo = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        m_str = d.strftime('%Y-%m')
        
        rec_row = db.execute("SELECT SUM(valor) as t FROM contas WHERE tipo='receber' AND strftime('%Y-%m', vencimento) = ?", (m_str,)).fetchone()
        rec = rec_row['t'] if rec_row and rec_row['t'] else 0.0
        
        pag_row = db.execute("SELECT SUM(valor) as t FROM contas WHERE tipo='pagar' AND strftime('%Y-%m', vencimento) = ?", (m_str,)).fetchone()
        pag = pag_row['t'] if pag_row and pag_row['t'] else 0.0
        
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

@bp.route('/api/relatorios/data')
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

@bp.route('/api/relatorios/comercial')
@jwt_required()
def api_relatorios_comercial():
    db = get_db()
    
    # Top 5 Clientes por Valor Total de Orçamentos Aprovados
    # Note: Using client name directly from orcamentos as we don't have a clients table linked by ID in this query context from reporting usually
    # But let's check legacy query: JOIN orcamentos o ON c.id = o.client_id
    # Wait, the legacy query used JOIN clientes c.
    # Let's assume clientes table exists (it should, from previous tasks).
    
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

@bp.route('/api/relatorios/melhor_compra')
@jwt_required()
def api_relatorios_melhor_compra():
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
        # Find who has the min price
        best = db.execute('SELECT site_origem FROM estoque WHERE nome = ? AND custo_unitario = ?', 
                          (d['nome'], d['preco_oportunidade'])).fetchone()
        d['site_barato'] = best['site_origem'] if best else 'Manual'
        
        if d['preco_orcamento'] > 0:
            d['economia_percent'] = round(((d['preco_orcamento'] - d['preco_oportunidade']) / d['preco_orcamento']) * 100, 1)
        else:
            d['economia_percent'] = 0
            
        result.append(d)
        
    return jsonify(result)
