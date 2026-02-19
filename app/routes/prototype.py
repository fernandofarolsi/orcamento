from flask import Blueprint, render_template

bp = Blueprint('prototype', __name__)

@bp.route('/prototype/cliente')
def prototype_cliente():
    # Mock Data for "Maria Silva"
    client = {
        "id": 1,
        "name": "Maria Silva",
        "company": "Escritório Silva & Associados",
        "email": "maria@silva.com",
        "phone": "(11) 99999-8888",
        "address": "Av. Paulista, 1000 - São Paulo, SP",
        "avatar": "https://ui-avatars.com/api/?name=Maria+Silva&background=random",
        "status": "Ativo",
        "total_spent": "R$ 45.200,00",
        "last_interaction": "2 horas atrás",
        "tags": ["Vip", "Indicação", "Corporativo"]
    }
    
    timeline = [
        {"type": "visit", "date": "Hoje, 14:00", "title": "Visita Técnica Realizada", "user": "Fernando", "desc": "Medição confirmada. Cliente quer acabamento em Freijó."},
        {"type": "budget", "date": "Ontem, 10:30", "title": "Orçamento #1023 Criado", "user": "Fernando", "desc": "Valor: R$ 12.500,00 - Status: Enviado"},
        {"type": "whatsapp", "date": "15/02/2026", "title": "Mensagem Recebida", "user": "Maria", "desc": "Oi, gostaria de agendar uma visita para medir a sala de reuniões."},
        {"type": "file", "date": "10/02/2026", "title": "Nota Fiscal #5544 Anexada", "user": "Admin", "desc": "Referente à compra de puxadores Zen."}
    ]
    
    budgets = [
        {"id": 1023, "status": "Enviado", "value": "12.500,00", "date": "16/02/2026", "items": "Armário Cozinha"},
        {"id": 980, "status": "Aprovado", "value": "32.700,00", "date": "10/01/2026", "items": "Móveis Escritório Completo"}
    ]
    
    return render_template('prototype_cliente.html', client=client, timeline=timeline, budgets=budgets)
