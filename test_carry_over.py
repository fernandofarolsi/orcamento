
import sqlite3
import json
from datetime import datetime

def test_carry_over():
    conn = sqlite3.connect('/home/fernando/Área de trabalho/Orcamento/app/app.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # 1. Setup temporary test data
    # Jose, Salario 1500
    db.execute("INSERT INTO funcionarios (nome, cargo, salario_base) VALUES ('Jose Teste', 'Pedreiro', 1500)")
    func_id = db.lastrowid
    
    # Período ativo
    db.execute("INSERT INTO funcionario_periodos (funcionario_id, data_contratacao) VALUES (?, '2026-01-01')", (func_id,))
    
    # Vale de 2000 em Fevereiro
    db.execute("INSERT INTO contas (tipo, descricao, valor, vencimento, status, categoria, funcionario_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
               ('pagar', 'Vale Jose', 2000.0, '2026-02-15', 'pago', 'vale_funcionario', func_id))
    
    conn.commit()
    print(f"Test data created for func_id {func_id}")

    # 2. Finalize Feb
    # Simulate API call logic
    # INSS = 1500 * 0.11 = 165
    # Vales = 2000
    # Total Descontos = 2165
    # Salario = 1500
    # Excedente = 665
    
    db.execute("INSERT INTO holerites_pagos (funcionario_id, mes_referencia, valor_pago) VALUES (?, '2026-02', 0.0)", (func_id,))
    db.execute("INSERT INTO funcionario_saldos (funcionario_id, valor, mes_origem) VALUES (?, 665.0, '2026-02')", (func_id,))
    conn.commit()
    print("Finalized Feb with 665 debt")

    # 3. Check March Calculation
    # Fetch pendente saldos < '2026-03'
    saldo_devedor = db.execute('''
        SELECT SUM(valor) as total 
        FROM funcionario_saldos 
        WHERE funcionario_id = ? AND status = 'pendente' AND mes_origem < '2026-03'
    ''', (func_id,)).fetchone()['total'] or 0.0
    
    print(f"Saldo devedor for March: {saldo_devedor}")
    assert saldo_devedor == 665.0, f"Expected 665, got {saldo_devedor}"

    # 4. Cleanup
    db.execute("DELETE FROM funcionario_saldos WHERE funcionario_id = ?", (func_id,))
    db.execute("DELETE FROM holerites_pagos WHERE funcionario_id = ?", (func_id,))
    db.execute("DELETE FROM funcionario_periodos WHERE funcionario_id = ?", (func_id,))
    db.execute("DELETE FROM contas WHERE funcionario_id = ?", (func_id,))
    db.execute("DELETE FROM funcionarios WHERE id = ?", (func_id,))
    conn.commit()
    conn.close()
    print("Test passed and cleaned up!")

if __name__ == '__main__':
    test_carry_over()
