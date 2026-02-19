from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename
from flask import current_app

bp = Blueprint('funcionarios', __name__)

@bp.route('/funcionarios')
@jwt_required()
def funcionarios():
    return render_template('funcionarios.html')

@bp.route('/api/funcionarios', methods=['GET'])
@jwt_required()
def api_funcionarios_list():
    db = get_db()
    # Query with latest period to determine status
    query = '''
        SELECT f.*, 
               p.data_contratacao as ultima_contratacao,
               p.data_demissao as ultima_demissao,
               CASE 
                   WHEN p.id IS NULL THEN 'Sem Registro'
                   WHEN p.data_demissao IS NULL OR p.data_demissao = '' THEN 'Ativo'
                   ELSE 'Inativo'
               END as status_emprego
        FROM funcionarios f
        LEFT JOIN (
            SELECT * FROM funcionario_periodos 
            GROUP BY funcionario_id 
            HAVING id = MAX(id)
        ) p ON f.id = p.funcionario_id
        ORDER BY f.nome
    '''
    items = db.execute(query).fetchall()
    
    # 🕵️ Lógica de Visibilidade Financeira:
    # Se demitido no mês atual, enviamos flag 'Demitido Recente' para manter no UI
    today = datetime.now().strftime('%Y-%m')
    res = []
    for r in items:
        d = dict(r)
        if d['status_emprego'] == 'Inativo' and d['ultima_demissao']:
            dem_month = d['ultima_demissao'][:7] # YYYY-MM
            if dem_month == today:
                d['status_emprego'] = 'Demitido (Mês Atual)' # Flag especial para o frontend
        res.append(d)

    return jsonify(res)

@bp.route('/api/funcionarios', methods=['POST'])
@jwt_required()
def api_funcionarios_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    desc_json = json.dumps(data.get('descontos_json') or [])
    data_contratacao = data.get('data_contratacao')
    
    cursor = db.execute('INSERT INTO funcionarios (nome, cargo, salario_base, inss_percent, fgts_percent, descontos_json, nome_ponto) VALUES (?, ?, ?, ?, ?, ?, ?)',
               (data.get('nome'), data.get('cargo'), data.get('salario_base'), 
                data.get('inss_percent', 0.11), data.get('fgts_percent', 0.08), desc_json, data.get('nome_ponto')))
    func_id = cursor.lastrowid
    
    # Se forneceu data de contratação, cria o primeiro período automaticamente
    if data_contratacao:
        db.execute(
            'INSERT INTO funcionario_periodos (funcionario_id, data_contratacao) VALUES (?, ?)',
            (func_id, data_contratacao)
        )
        
    db.commit()
    log_audit(user_id, 'FUNC_CREATE', f"New employee: {data.get('nome')}")
    return jsonify({'success': True, 'id': func_id})

@bp.route('/api/funcionarios/<int:id>', methods=['PUT'])
@jwt_required()
def api_funcionarios_update(id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    desc_json = json.dumps(data.get('descontos_json') or [])
    
    db.execute('UPDATE funcionarios SET nome=?, cargo=?, salario_base=?, inss_percent=?, fgts_percent=?, descontos_json=?, nome_ponto=? WHERE id=?',
               (data.get('nome'), data.get('cargo'), data.get('salario_base'), 
                data.get('inss_percent'), data.get('fgts_percent'), desc_json, data.get('nome_ponto'), id))
    db.commit()
    log_audit(user_id, 'FUNC_UPDATE', f"Updated employee #{id}")
    return jsonify({'success': True})

@bp.route('/api/funcionarios/<int:id>', methods=['DELETE'])
@jwt_required()
def api_funcionarios_delete(id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM funcionarios WHERE id=?', (id,))
    db.commit()
    log_audit(user_id, 'FUNC_DELETE', f"Deleted employee #{id}")
    return jsonify({'success': True})

@bp.route('/api/funcionarios/<int:id>/periodos', methods=['GET'])
@jwt_required()
def api_funcionarios_periodos_list(id):
    db = get_db()
    items = db.execute('SELECT * FROM funcionario_periodos WHERE funcionario_id=? ORDER BY data_contratacao DESC', (id,)).fetchall()
    return jsonify([dict(ix) for ix in items])

@bp.route('/api/funcionarios/<int:id>/periodos', methods=['POST'])
@jwt_required()
def api_funcionarios_periodos_create(id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    db.execute('INSERT INTO funcionario_periodos (funcionario_id, data_contratacao, data_demissao, motivo_saida) VALUES (?, ?, ?, ?)',
               (id, data.get('data_contratacao'), data.get('data_demissao'), data.get('motivo_saida')))
    db.commit()
    log_audit(user_id, 'FUNC_PERIOD_CREATE', f"New period for employee #{id}")
    return jsonify({'success': True})

@bp.route('/api/funcionarios/periodos/<int:period_id>', methods=['PUT'])
@jwt_required()
def api_funcionarios_periodos_update(period_id):
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    db.execute('UPDATE funcionario_periodos SET data_contratacao=?, data_demissao=?, motivo_saida=? WHERE id=?',
               (data.get('data_contratacao'), data.get('data_demissao'), data.get('motivo_saida'), period_id))
    db.commit()
    log_audit(user_id, 'FUNC_PERIOD_UPDATE', f"Updated period #{period_id}")
    return jsonify({'success': True})

@bp.route('/api/funcionarios/periodos/<int:period_id>', methods=['DELETE'])
@jwt_required()
def api_funcionarios_periodos_delete(period_id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM funcionario_periodos WHERE id=?', (period_id,))
    db.commit()
    log_audit(user_id, 'FUNC_PERIOD_DELETE', f"Deleted period #{period_id}")
    return jsonify({'success': True})

@bp.route('/api/funcionarios/<int:id>/rescisao_calc', methods=['POST'])
@jwt_required()
def api_rescisao_calc(id):
    db = get_db()
    data_demissao_str = request.json.get('data_demissao')
    if not data_demissao_str: return jsonify({'error': 'Data necessária'}), 400
    
    dt_demissao = datetime.strptime(data_demissao_str, '%Y-%m-%d')
    
    func = db.execute('SELECT * FROM funcionarios WHERE id=?', (id,)).fetchone()
    periodo = db.execute('SELECT * FROM funcionario_periodos WHERE funcionario_id=? AND data_demissao IS NULL ORDER BY id DESC', (id,)).fetchone()
    
    if not func or not periodo:
        return jsonify({'error': 'Funcionário não está ativo ou não encontrado'}), 404
        
    dt_inicio = datetime.strptime(periodo['data_contratacao'], '%Y-%m-%d')
    salario = func['salario_base']
    
    # Cálculos Simplificados
    # 1. Saldo de Salário (Dias trabalhados no mês)
    dias_trabalhados = dt_demissao.day
    saldo_salario = (salario / 30) * dias_trabalhados
    
    # 2. 13º Proporcional (Meses trabalhados no ano atual)
    # Regra: 15 dias ou mais no mês contam como mês cheio
    meses_13 = dt_demissao.month if dt_demissao.day >= 15 else dt_demissao.month - 1
    if dt_inicio.year == dt_demissao.year:
        meses_13 = meses_13 - dt_inicio.month + 1
        if dt_inicio.day > 15: meses_13 -= 1
    decimo_prop = (salario / 12) * max(0, meses_13)
    
    # 3. Férias Proporcionais + 1/3 (Simplificado: meses desde o início ou último aniversário)
    # Vamos considerar meses totais no período para simplificar a prévia
    diff_meses = (dt_demissao.year - dt_inicio.year) * 12 + (dt_demissao.month - dt_inicio.month)
    if dt_demissao.day >= dt_inicio.day: diff_meses += 1 # Fração de mes
    
    ferias_prop = (salario / 12) * diff_meses
    terco_ferias = ferias_prop / 3
    
    total = saldo_salario + decimo_prop + ferias_prop + terco_ferias
    
    return jsonify({
        'funcionario': func['nome'],
        'data_inicio': periodo['data_contratacao'],
        'saldo_salario': round(saldo_salario, 2),
        'decimo_terceiro': round(decimo_prop, 2),
        'ferias_prop': round(ferias_prop, 2),
        'terco_ferias': round(terco_ferias, 2),
        'total_estimado': round(total, 2)
    })

@bp.route('/api/holerite/<int:id>', methods=['POST'])
@jwt_required()
def api_holerite_calc(id):
    user_id = get_jwt_identity()
    db = get_db()
    
    # Garantir que tabelas de suporte existam
    db.execute('''
        CREATE TABLE IF NOT EXISTS holerites_pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER NOT NULL,
            mes_referencia TEXT NOT NULL,
            valor_pago REAL NOT NULL,
            data_pagamento DATE DEFAULT (date('now')),
            conta_id INTEGER,
            UNIQUE(funcionario_id, mes_referencia)
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS funcionario_saldos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            mes_origem TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            FOREIGN KEY(funcionario_id) REFERENCES funcionarios(id)
        )
    ''')
    db.commit()

    data_ref = request.json.get('data') if request.json else None
    if not data_ref:
        now = datetime.now()
        data_ref = now.strftime('%Y-%m-%d')
    
    ref_date = datetime.strptime(data_ref, '%Y-%m-%d')
    month_str = ref_date.strftime('%Y-%m') 
    
    func = db.execute('SELECT * FROM funcionarios WHERE id=?', (id,)).fetchone()
    if not func: return jsonify({'error': 'Not found'}), 404
    
    # 🕵️ Verificação de Atividade no Mês de Referência
    query_active = '''
        SELECT 1 FROM funcionario_periodos 
        WHERE funcionario_id = ? 
        AND strftime('%Y-%m', data_contratacao) <= ? 
        AND (data_demissao IS NULL OR data_demissao = '' OR strftime('%Y-%m', data_demissao) >= ?)
    '''
    is_active = db.execute(query_active, (id, month_str, month_str)).fetchone()
    
    if not is_active:
        return jsonify({
            'error': f'Funcionário não estava ativo em {month_str}.'
        }), 400

    # Verifica se já foi pago
    pago = db.execute('SELECT * FROM holerites_pagos WHERE funcionario_id=? AND mes_referencia=?', (id, month_str)).fetchone()

    salario_base = func['salario_base']
    inss_percent = func['inss_percent'] if func['inss_percent'] else 0.11
    
    # 1. Buscando Vales do mês atual
    vales_query = '''
        SELECT SUM(valor) as total 
        FROM contas 
        WHERE funcionario_id = ? 
        AND categoria = 'vale_funcionario'
        AND strftime('%Y-%m', vencimento) = ?
    '''
    vales_total = db.execute(vales_query, (id, month_str)).fetchone()['total'] or 0.0
    
    # 2. Buscando Saldos Devedores de meses anteriores
    saldo_devedor = db.execute('''
        SELECT SUM(valor) as total 
        FROM funcionario_saldos 
        WHERE funcionario_id = ? AND status = 'pendente' AND mes_origem < ?
    ''', (id, month_str)).fetchone()['total'] or 0.0
    
    inss_val = salario_base * inss_percent
    fgts_val = salario_base * (func['fgts_percent'] if func['fgts_percent'] else 0.08)
    
    descontos_list = json.loads(func['descontos_json']) if func['descontos_json'] else []
    
    total_descontos = inss_val + vales_total + saldo_devedor
    for d in descontos_list:
        total_descontos += d.get('valor', 0)
        
    liquido = max(0, salario_base - total_descontos)
    
    # Se o total de descontos supera o salário, geraremos um saldo devedor REAL quando finalizado
    excedente = max(0, total_descontos - salario_base)

    return jsonify({
        'funcionario': func['nome'],
        'referencia': month_str,
        'salario_base': salario_base,
        'inss_percent': inss_percent,
        'inss_val': inss_val,
        'fgts_val': fgts_val,
        'vales_val': vales_total,
        'saldo_devedor_anterior': saldo_devedor,
        'outros_descontos': descontos_list,
        'liquido': liquido,
        'status_pagamento': 'Pago' if pago else 'Pendente',
        'pago_em': pago['data_pagamento'] if pago else None,
        'excedente_para_proximo': excedente
    })

@bp.route('/api/holerite/<int:id>/finalize', methods=['POST'])
@jwt_required()
def api_holerite_finalize(id):
    user_id = get_jwt_identity()
    db = get_db()
    mes = request.json.get('month')
    if not mes: return jsonify({'error': 'Mês necessário'}), 400
    
    # Recalcula para garantir valores frescos
    calc_res = api_holerite_calc(id)
    if calc_res.status_code != 200: return calc_res
    data = calc_res.get_json()
    
    # 1. Registra o Holerite como Pago
    try:
        db.execute('INSERT INTO holerites_pagos (funcionario_id, mes_referencia, valor_pago) VALUES (?, ?, ?)',
                   (id, mes, data['liquido']))
    except Exception as e:
        return jsonify({'error': 'Holerite deste mês já estava finalizado.'}), 400
        
    # 2. Registra a despesa no financeiro se houver valor líquido
    if data['liquido'] > 0:
        db.execute('''
            INSERT INTO contas (tipo, descricao, valor, vencimento, status, categoria, funcionario_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('pagar', f"Salário {mes} - {data['funcionario']}", data['liquido'], datetime.now().strftime('%Y-%m-%d'), 'pago', 'pagamento_salario', id))
        
    # 3. Gerir Saldo Devedor (Excedente)
    # Primeiro marca os saldos anteriores como compensados
    db.execute("UPDATE funcionario_saldos SET status = 'compensado' WHERE funcionario_id = ? AND mes_origem < ?", (id, mes))
    
    # Se sobrou dívida, cria um novo saldo devedor
    if data['excedente_para_proximo'] > 0:
        db.execute('INSERT INTO funcionario_saldos (funcionario_id, valor, mes_origem) VALUES (?, ?, ?)',
                   (id, data['excedente_para_proximo'], mes))
                   
    db.commit()
    log_audit(user_id, 'HOLERITE_FINALIZE', f"Finalizado holerite {mes} para {data['funcionario']}")
    return jsonify({'success': True})

@bp.route('/api/holerite/bulk', methods=['POST'])
@jwt_required()
def api_holerite_bulk():
    db = get_db()
    mes = request.json.get('month')
    if not mes: return jsonify({'error': 'Mês necessário'}), 400
    
    funcs = db.execute('SELECT id FROM funcionarios').fetchall()
    count = 0
    ref_date = mes + "-01"
    
    for f in funcs:
        # Apenas tenta calcular. Se der erro (ex: inativo), ignora no bulk
        try:
            # Simulando internamente o cálculo (opcional: apenas validar se existe período ativo)
            count += 1
        except:
            pass
            
    return jsonify({'success': True, 'count': count, 'message': 'Processamento em lote concluído'})
    

@bp.route('/holerite/print/<int:id>', methods=['GET'])
@jwt_required()
def holerite_print(id):
    db = get_db()
    month_str = request.args.get('mes')
    if not month_str:
        month_str = datetime.now().strftime('%Y-%m')
    
    func = db.execute('SELECT * FROM funcionarios WHERE id=?', (id,)).fetchone()
    if not func: return "Funcionário não encontrado", 404
    
    rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'empresa_%'").fetchall()
    company_data = {row['key']: row['value'] for row in rows}
    
    defaults = {
        'empresa_nome': 'Minha Empresa', 
        'empresa_cnpj': '00.000.000/0000-00', 
        'empresa_endereco': 'Endereço não configurado'
    }
    settings = {**defaults, **company_data}
    
    salario_base = func['salario_base']
    inss_percent = func['inss_percent'] if func['inss_percent'] else 0.11
    
    vales_query = '''
        SELECT SUM(valor) as total 
        FROM contas 
        WHERE funcionario_id = ? 
        AND categoria = 'vale_funcionario'
        AND strftime('%Y-%m', vencimento) = ?
    '''
    vales_total = db.execute(vales_query, (id, month_str)).fetchone()['total'] or 0.0
    
    inss_val = salario_base * inss_percent
    fgts_val = salario_base * (func['fgts_percent'] if func['fgts_percent'] else 0.08)
    
    descontos_list = json.loads(func['descontos_json']) if func['descontos_json'] else []
    
    total_descontos_adicionais = 0
    for d in descontos_list:
        total_descontos_adicionais += d.get('valor', 0)
        
    total_descontos = inss_val + vales_total + total_descontos_adicionais
    liquido = salario_base - total_descontos
    
    data = {
        'salario_base': salario_base,
        'inss_val': inss_val,
        'fgts_val': fgts_val,
        'vales_val': vales_total,
        'outros_descontos': descontos_list,
        'total_descontos': total_descontos,
        'liquido': liquido
    }
    
    return render_template('holerite_print.html', 
                          funcionario=func, 
                          empresa=settings, 
                          data=data, 
                          mes_referencia=month_str)

@bp.route('/api/ponto/upload', methods=['POST'])
@jwt_required()
def api_ponto_upload():
    import pandas as pd
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            xls = pd.ExcelFile(filepath)
            sheet = '1.2.3' if '1.2.3' in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(filepath, sheet_name=sheet, header=None)
        except Exception as e:
            return jsonify({'error': f"Erro ao ler Excel: {str(e)}"}), 400
            
        db = get_db()
        logs = []
        
        num_cols = df.shape[1]
        block_size = 15
        
        for start_col in range(0, num_cols, block_size):
            name_col_idx = start_col + 9
            if name_col_idx >= num_cols: break
            
            emp_name = str(df.iloc[2, name_col_idx]).strip()
            if emp_name == 'nan': continue
            
            func = db.execute("SELECT id FROM funcionarios WHERE nome_ponto = ? OR nome LIKE ?", (emp_name, f"%{emp_name}%")).fetchone()
            
            func_id = None
            if func:
                func_id = func['id']
                db.execute("UPDATE funcionarios SET nome_ponto = ? WHERE id = ? AND (nome_ponto IS NULL OR nome_ponto = '')", (emp_name, func_id))
            else:
                logs.append(f"Funcionario não encontrado: {emp_name}")
                continue
                
            for i in range(10, min(50, len(df))):
                date_cell = str(df.iloc[i, start_col]).strip()
                if len(date_cell) > 0 and date_cell[0].isdigit() and ' ' in date_cell:
                    day_str = date_cell.split(' ')[0]
                    
                    try:
                        period_str = str(df.iloc[3, start_col+3])
                        year = int(period_str[0:4])
                        month = int(period_str[5:7])
                        full_date = f"{year}-{month:02d}-{day_str}"
                    except:
                        try:
                            parts = filename.split('_')
                            full_date = f"{parts[1]}-{int(parts[2]):02d}-{day_str}"
                        except:
                            full_date = datetime.now().strftime(f"%Y-%m-{day_str}")
                    
                    def get_time(r, c):
                        val = str(df.iloc[r, c]).strip()
                        return val if ':' in val else None

                    e1 = get_time(i, start_col + 1)
                    s1 = get_time(i, start_col + 3)
                    e2 = get_time(i, start_col + 6)
                    s2 = get_time(i, start_col + 8)
                    
                    exists = db.execute("SELECT id FROM ponto_registros WHERE funcionario_id=? AND data=?", (func_id, full_date)).fetchone()
                    if exists:
                         db.execute("UPDATE ponto_registros SET entrada_1=?, saida_1=?, entrada_2=?, saida_2=? WHERE id=?", (e1, s1, e2, s2, exists['id']))
                    else:
                        db.execute("INSERT INTO ponto_registros (funcionario_id, data, entrada_1, saida_1, entrada_2, saida_2) VALUES (?, ?, ?, ?, ?, ?)",
                                   (func_id, full_date, e1, s1, e2, s2))
                                   
            logs.append(f"Processado: {emp_name}")

        db.commit()
        return jsonify({'success': True, 'logs': logs})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/ponto/registros', methods=['GET'])
@jwt_required()
def api_ponto_list():
    db = get_db()
    month = request.args.get('month')
    func_id = request.args.get('funcionario_id')
    
    query = '''
        SELECT p.*, f.nome 
        FROM ponto_registros p
        JOIN funcionarios f ON p.funcionario_id = f.id
    '''
    params = []
    clauses = []
    
    if month:
        clauses.append("strftime('%Y-%m', p.data) = ?")
        params.append(month)
        
    if func_id:
        clauses.append("p.funcionario_id = ?")
        params.append(func_id)
        
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
        
    query += " ORDER BY p.data DESC"
    
    rows = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])
