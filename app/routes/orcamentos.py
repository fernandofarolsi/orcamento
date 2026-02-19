from flask import Blueprint, render_template, request, jsonify, flash
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
from datetime import datetime
import json

bp = Blueprint('orcamentos', __name__)

@bp.route('/orcamentos')
@jwt_required()
def orcamentos():
    db = get_db()
    show_all = request.args.get('show_all')
    if show_all:
        orcamentos = db.execute('SELECT * FROM orcamentos ORDER BY created_at DESC').fetchall()
    else:
        orcamentos = db.execute("SELECT * FROM orcamentos WHERE status != 'Faturado' ORDER BY created_at DESC").fetchall()
    return render_template('orcamentos.html', orcamentos=orcamentos, showing_all=show_all)

@bp.route('/api/orcamentos', methods=['GET'])
@jwt_required()
def api_orcamentos_list():
    db = get_db()
    orcamentos = db.execute('''
        SELECT id, client, client_id, status, created_at, 
               prazo_entrega, data_instalacao
        FROM orcamentos 
        ORDER BY created_at DESC
    ''').fetchall()
    return jsonify([dict(o) for o in orcamentos])

@bp.route('/api/orcamentos', methods=['POST'])
@jwt_required()
def api_orcamentos_create():
    user_id = get_jwt_identity()
    data = request.json
    
    client_id = data.get('client_id')
    client = data.get('client')
    itens = json.dumps(data.get('itens'))
    total = data.get('total')
    total_horas_mo = data.get('total_horas_mo', 0)
    
    db = get_db()
    cur = db.cursor()
    
    cur.execute('INSERT INTO orcamentos (client_id, client, itens_json, total, status, total_horas_mo, created_at) VALUES (?, ?, ?, ?, ?, ?, datetime("now"))',
                (client_id, client, itens, total, data.get('status', 'Rascunho'), total_horas_mo))
    orcamento_id = cur.lastrowid
    
    # Auto-create Kanban Card
    cur.execute('INSERT INTO cards_kanban (titulo, etapa, client, orcamento_id) VALUES (?, ?, ?, ?)',
                (f"Orç. #{orcamento_id} - {client}", "Contato", client, orcamento_id))
    
    log_audit(user_id, 'CREATE_ORCAMENTO', f'Created budget #{orcamento_id} for {client}')
    
    db.commit()
    return jsonify({'success': True, 'id': orcamento_id})

@bp.route('/api/orcamentos/<int:id>', methods=['GET'])
@jwt_required()
def get_orcamento(id):
    db = get_db()
    orc = db.execute('SELECT * FROM orcamentos WHERE id = ?', (id,)).fetchone()
    if not orc:
        return jsonify({'success': False, 'error': 'Orçamento não encontrado'}), 404
    
    return jsonify({'success': True, 'orcamento': dict(orc)})

@bp.route('/api/orcamentos/<int:id>', methods=['PUT'])
@jwt_required()
def update_orcamento(id):
    user_id = get_jwt_identity()
    data = request.json
    
    client_id = data.get('client_id')
    client = data.get('client')
    
    db = get_db()
    db.execute('''UPDATE orcamentos SET client_id=?, client=?, itens_json=?, total=?, total_horas_mo=?, status=? WHERE id=?''',
                (client_id, client, json.dumps(data.get('itens')), data.get('total'), data.get('total_horas_mo', 0), data.get('status'), id))
    
    log_audit(user_id, 'UPDATE_ORCAMENTO', f'Updated budget #{id}')
    db.commit()
    return jsonify({'success': True})

@bp.route('/api/orcamentos/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_orcamento(id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM orcamentos WHERE id = ?', (id,))
    db.execute('DELETE FROM cards_kanban WHERE orcamento_id = ?', (id,))
    db.commit()
    log_audit(user_id, 'DELETE_ORCAMENTO', f'Deleted budget #{id}')
    return jsonify({'success': True})

@bp.route('/api/orcamento-calcular', methods=['POST'])
@jwt_required()
def api_orcamento_calcular():
    data = request.json
    material = float(data.get('material', 0))
    horas = float(data.get('horas', 0))
    
    db = get_db()
    cf = data.get('config')
    if not cf:
        cf = dict(db.execute('SELECT * FROM config_fabrica LIMIT 1').fetchone())
    
    rate_row = db.execute("SELECT value FROM settings WHERE key='valor_hora_fabrica'").fetchone()
    custo_hora = float(rate_row['value']) if rate_row else 70.0
    
    margem_lucro = float(cf['margem_lucro'])
    margem_negociacao = float(cf['margem_negociacao'])
    margem_impostos = float(cf['margem_impostos'])
    
    custo_fabricacao = custo_hora * horas
    custo_total = material + custo_fabricacao
    
    preco_venda = custo_total * (1 + margem_lucro) * (1 + margem_negociacao) * (1 + margem_impostos)
    
    breakdown = [
        f"Material: R$ {material:,.2f}",
        f"Mão de Obra ({horas}h @ R$ {custo_hora:,.2f}/h): R$ {custo_fabricacao:,.2f}",
        f"Custo Base Total: R$ {custo_total:,.2f}",
        f"+ Margem Lucro ({margem_lucro*100}%): R$ {custo_total * margem_lucro:,.2f}",
        f"+ Reserva Negoc. ({margem_negociacao*100}%): R$ {custo_total * (1+margem_lucro) * margem_negociacao:,.2f}",
        f"+ Impostos ({margem_impostos*100}%): R$ {custo_total * (1+margem_lucro) * (1+margem_negociacao) * margem_impostos:,.2f}",
        f"--- PREÇO FINAL SUGERIDO: R$ {preco_venda:,.2f} ---"
    ]
    
    return jsonify({
        'custo_fabricacao': round(custo_fabricacao, 2),
        'custo_total': round(custo_total, 2),
        'preco_venda': round(preco_venda, 2),
        'breakdown': breakdown
    })

@bp.route('/api/orcamentos/calculate-tiers', methods=['POST'])
@jwt_required()
def api_orcamento_calculate_tiers():
    from app.services.calculator import calculate_item_tier_cost
    
    data = request.json
    items = data.get('items', [])
    config = data.get('config', {})
    
    db = get_db()
    
    # 1. Get Tiers
    tiers = db.execute("SELECT * FROM budget_tiers ORDER BY order_index").fetchall()
    
    results = {}
    
    # Global Config (or per tier?)
    if not config:
        cf = db.execute('SELECT * FROM config_fabrica LIMIT 1').fetchone()
        config = dict(cf) if cf else {'margem_lucro': 0.35, 'margem_negociacao': 0.10, 'margem_impostos': 0.05}

    margem_lucro = float(config.get('margem_lucro', 0.35))
    margem_negociacao = float(config.get('margem_negociacao', 0.10))
    margem_impostos = float(config.get('margem_impostos', 0.05))

    for tier in tiers:
        tier_id = tier['id']
        tier_name = tier['name']
        
        tier_total_cost = 0.0
        tier_breakdown = []
        
        for item in items:
            # Calculate cost for this item in this tier
            cost, details = calculate_item_tier_cost(db, item, tier_id)
            tier_total_cost += cost
            tier_breakdown.extend(details)
            
        # Final Price Calculation
        preco_venda = tier_total_cost * (1 + margem_lucro) * (1 + margem_negociacao) * (1 + margem_impostos)
        
        results[tier_name] = {
            'custo_total': round(tier_total_cost, 2),
            'preco_venda': round(preco_venda, 2),
            'breakdown': tier_breakdown,
            'description': tier['description']
        }
        
    return jsonify(results)

# --- Generating Contracts & Proposals ---

def render_contract_template(template_str, orc, cliente, db):
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        pass 

    def fmt_moeda(val):
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    pag_info = json.loads(orc['pagamento_json']) if 'pagamento_json' in orc.keys() and orc['pagamento_json'] else {}
    total = fmt_moeda(orc['total'])
    data_hoje = datetime.now().strftime('%d/%m/%Y')

    try:
        rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'empresa_%'").fetchall()
        company = {row['key']: row['value'] for row in rows}
    except:
        company = {}

    c_nome = company.get('empresa_nome', 'Adore Marcenaria')
    c_cnpj = company.get('empresa_cnpj', '00.000.000/0001-00')
    c_end = company.get('empresa_endereco', '')
    c_logo = company.get('empresa_logo_url', '/static/logo.jpg')
    
    itens_html = "<table><thead><tr><th>Ambiente</th><th>Descrição</th><th>Dimensões/Detalhes</th><th>Valor</th></tr></thead><tbody>"
    
    itens_data = []
    if orc['itens_json']:
        try:
            raw = json.loads(orc['itens_json'])
            if isinstance(raw, list) and len(raw) > 0 and 'items' in raw[0]:
                for group in raw:
                    for item in group['items']:
                        itens_data.append({'ambiente': group['name'], 'item': item})
            else:
                 for item in raw:
                    itens_data.append({'ambiente': 'Geral', 'item': item})
        except:
            pass

    for row in itens_data:
        it = row['item']
        desc = f"<strong>{it.get('nome', 'Item')}</strong><br>{it.get('descricao', '')}"
        dim = f"{it.get('largura',0)}x{it.get('altura',0)}x{it.get('profundidade',0)}"
        valor = fmt_moeda(it.get('preco_final', 0))
        itens_html += f"<tr><td>{row['ambiente']}</td><td>{desc}</td><td>{dim}</td><td>{valor}</td></tr>"
    
    itens_html += "</tbody></table>"

    signatures_html = f'''
    <div class="signatures">
        <div class="sig-block">
            __________________________<br>
            <strong>{c_nome}</strong><br>
            CNPJ: {c_cnpj}
        </div>
        <div class="sig-block">
            __________________________<br>
            <strong>{cliente['nome'] if cliente else 'CLIENTE'}</strong><br>
            CPF/CNPJ: {cliente['cpf_cnpj'] if cliente else ''}
        </div>
    </div>
    '''

    html = template_str
    html = html.replace('[ID]', str(orc['id']))
    html = html.replace('[DATA]', data_hoje)
    html = html.replace('[TOTAL]', total)
    html = html.replace('[EMPRESA_NOME]', c_nome)
    html = html.replace('[EMPRESA_CNPJ]', c_cnpj)
    html = html.replace('[EMPRESA_ENDERECO]', c_end)
    html = html.replace('[EMPRESA_LOGO]', c_logo)
    html = html.replace('[CLIENTE]', (cliente['nome'] or "N/A") if cliente else "N/A")
    html = html.replace('[CPF_CNPJ]', (cliente['cpf_cnpj'] or "N/A") if cliente else "N/A")
    html = html.replace('[FORMA_PAGAM]', pag_info.get('metodo', 'À combinar'))
    html = html.replace('[ENTRADA]', fmt_moeda(float(pag_info.get('entrada', 0))))
    html = html.replace('[QTD_PARCELAS]', str(pag_info.get('parcelas', 1)))
    html = html.replace('[VALOR_PARCELA]', fmt_moeda(float(pag_info.get('valor_parcela', 0))))
    html = html.replace('[TABELA_ITENS]', itens_html)
    html = html.replace('[ASSINATURAS]', signatures_html)

    return html

@bp.route('/contrato/<int:orc_id>')
@jwt_required()
def gerar_contrato(orc_id):
    db = get_db()
    orc = db.execute('SELECT * FROM orcamentos WHERE id = ?', (orc_id,)).fetchone()
    if not orc: return "Orçamento não encontrado"
    
    cliente = None
    if orc['client_id']:
        cliente = db.execute('SELECT * FROM clientes WHERE id = ?', (orc['client_id'],)).fetchone()
    
    settings_row = db.execute("SELECT value FROM settings WHERE key='contrato_template'").fetchone()
    template_str = settings_row['value'] if settings_row else ""
    
    if not template_str:
        base_row = db.execute("SELECT value FROM settings WHERE key='contrato_base'").fetchone()
        if base_row:
             template_str = f"<html><body>{base_row['value']}</body></html>"
        else:
             template_str = "<h1>Erro: Template de contrato não encontrado.</h1>"

    final_html = render_contract_template(template_str, orc, cliente, db)
    return render_template('contrato_print.html', contract_html=final_html)

@bp.route('/proposta/<int:orc_id>')
@jwt_required()
def gerar_proposta(orc_id):
    db = get_db()
    orc = db.execute('SELECT * FROM orcamentos WHERE id = ?', (orc_id,)).fetchone()
    if not orc: return "Orçamento não encontrado"
    
    prop_numero = datetime.now().strftime('%d%m')
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    
    groups = []
    if orc['itens_json']:
        try:
            raw = json.loads(orc['itens_json'])
            if isinstance(raw, list) and len(raw) > 0 and 'items' in raw[0]:
                groups = []
                for group in raw:
                    new_group = dict(group)
                    if 'items' in new_group:
                        new_group['itens'] = new_group.pop('items')
                    groups.append(new_group)
            else:
                groups = [{'name': 'Geral', 'itens': raw}]
        except Exception as e:
            print(f"Error parsing items for proposal: {e}")
            groups = []

    return render_template('proposta_print.html', orcamento=orc, data_hoje=data_hoje, prop_numero=prop_numero, groups=groups)
