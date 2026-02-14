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
    items = db.execute('SELECT * FROM funcionarios ORDER BY nome').fetchall()
    return jsonify([dict(ix) for ix in items])

@bp.route('/api/funcionarios', methods=['POST'])
@jwt_required()
def api_funcionarios_create():
    user_id = get_jwt_identity()
    data = request.json
    db = get_db()
    
    desc_json = json.dumps(data.get('descontos_json') or [])
    
    db.execute('INSERT INTO funcionarios (nome, cargo, salario_base, inss_percent, fgts_percent, descontos_json, nome_ponto) VALUES (?, ?, ?, ?, ?, ?, ?)',
               (data.get('nome'), data.get('cargo'), data.get('salario_base'), 
                data.get('inss_percent', 0.11), data.get('fgts_percent', 0.08), desc_json, data.get('nome_ponto')))
    db.commit()
    log_audit(user_id, 'FUNC_CREATE', f"New employee: {data.get('nome')}")
    return jsonify({'success': True})

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

@bp.route('/api/holerite/<int:id>', methods=['POST'])
@jwt_required()
def api_holerite_calc(id):
    user_id = get_jwt_identity()
    db = get_db()
    
    data_ref = request.json.get('data') if request.json else None
    if not data_ref:
        now = datetime.now()
        data_ref = now.strftime('%Y-%m-%d')
    
    ref_date = datetime.strptime(data_ref, '%Y-%m-%d')
    month_str = ref_date.strftime('%Y-%m') 
    
    func = db.execute('SELECT * FROM funcionarios WHERE id=?', (id,)).fetchone()
    if not func: return jsonify({'error': 'Not found'}), 404
    
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
    
    total_descontos = inss_val + vales_total
    for d in descontos_list:
        total_descontos += d.get('valor', 0)
        
    liquido = salario_base - total_descontos
    
    res_json = {
        'funcionario': func['nome'],
        'referencia': month_str,
        'salario_base': salario_base,
        'inss_val': inss_val,
        'fgts_val': fgts_val,
        'vales_val': vales_total,
        'outros_descontos': descontos_list,
        'liquido': liquido
    }
    
    log_audit(user_id, 'HOLERITE_GEN', f"Generated holerite for #{id}")
    return jsonify(res_json)

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
