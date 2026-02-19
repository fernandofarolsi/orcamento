from app.database import get_db
from app.services import waha
import json
import re
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.models.ollama import Ollama
from agno.db.sqlite import SqliteDb

# Persistence for Agno
agent_storage = SqliteDb(
    table_name="agent_sessions",
    db_url="sqlite:///app/camila_agent.db"
)

import os
from app.database import get_db

def get_agent_config():
    # Prioritiza variáveis de ambiente (.env) por segurança
    env_config = {
        'ai_provider': os.getenv('AI_PROVIDER'),
        'ai_model': os.getenv('AI_MODEL'),
        'ai_api_key': os.getenv('AI_API_KEY')
    }
    
    # Se as chaves principais estiverem no .env, usamos elas
    if env_config['ai_api_key']:
        # Ainda pegamos as instruções do banco para flexibilidade na UI
        db = get_db()
        rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'camila_instructions%'").fetchall()
        db_config = {row['key']: row['value'] for row in rows}
        return {**db_config, **env_config}

    # Fallback para o Banco de Dados (Legado/UI)
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'ai_%' OR key LIKE 'camila_instructions%'").fetchall()
    config = {row['key']: row['value'] for row in rows}
    return config

def identify_user(whatsapp_number):
    """
    Identifica se o número pertence a um Admin ou Cliente.
    """
    db = get_db()
    # Limpa o número (remove @c.us se houver)
    clean_number = whatsapp_number.split('@')[0]
    
    # Busca em users (Admin/Interno)
    user = db.execute("SELECT id, username, role FROM users WHERE whatsapp = ? OR whatsapp LIKE ?", 
                      (clean_number, f'%{clean_number}%')).fetchone()
    if user:
        return {'role': 'admin', 'name': user['username'], 'id': user['id']}
    
    # Busca em clientes (Externo) - Supondo que cadastramos o whatsapp lá também futuramente
    # Por enquanto, se não for user, tratamos como cliente/lead
    return {'role': 'client', 'name': 'Visitante', 'id': None}

# --- TOOLS ---
def consultar_estoque(termo: str) -> str:
    """Consulta o estoque por nome do item."""
    db = get_db()
    items = db.execute("SELECT id, nome, preco_venda, quantidade FROM estoque WHERE nome LIKE ? LIMIT 5", 
                       (f'%{termo}%',)).fetchall()
    if not items:
        return "Nenhum item encontrado."
    
    res = "Itens encontrados:\n"
    for item in items:
        res += f"- {item['nome']} (ID: {item['id']}): R$ {item['preco_venda']:.2f} (Qtd: {item['quantidade']})\n"
    return res

def ver_status_orcamento(cliente_nome: str) -> str:
    """Verifica o status do orçamento de um cliente."""
    db = get_db()
    # Find client first
    cliente = db.execute("SELECT id, nome FROM clientes WHERE nome LIKE ? LIMIT 1", (f'%{cliente_nome}%',)).fetchone()
    if not cliente:
        return "Cliente não encontrado."
        
    orcs = db.execute("SELECT id, total, status, created_at FROM orcamentos WHERE cliente_id = ? ORDER BY created_at DESC LIMIT 3", 
                      (cliente['id'],)).fetchall()
    
    if not orcs:
        return "Nenhum orçamento encontrado para este cliente."
        
    res = f"Orçamentos de {cliente['nome']}:\n"
    for o in orcs:
        res += f"- #{o['id']}: R$ {o['total']:.2f} ({o['status']}) em {o['created_at']}\n"
    return res

# --- AGENT LOGIC ---
def process_message(chat_id, text, is_simulation=False):
    conf = get_agent_config()
    
    # Identifying user & role
    user_info = identify_user(chat_id)
    role = user_info['role']
    
    # Pick instructions
    if role == 'admin':
        instructions = conf.get('camila_instructions_admin', conf.get('camila_instructions', 'Você é a Camila (Interna).'))
    else:
        instructions = conf.get('camila_instructions_client', conf.get('camila_instructions', 'Você é a Camila (Clientes).'))

    provider = conf.get('ai_provider', 'groq')
    model_name = conf.get('ai_model', 'llama-3.3-70b-versatile')
    api_key = conf.get('ai_api_key', '')
    
    response_text = ""
    
    try:
        if not api_key and not provider == 'ollama':
             response_text = f"[SIMULAÇÃO] ({role.upper()}) Recebi: '{text}'. (API Key ausente)"
        else:
             model = None
             if provider == 'groq':
                 model = Groq(id=model_name, api_key=api_key)
             elif provider == 'openai':
                 model = OpenAIChat(id=model_name, api_key=api_key)
             elif provider == 'ollama':
                 model = Ollama(id=model_name)
                 
             if model:
                 # MANUAL TOOL HANDLING INSTRUCTIONS
                 manual_tool_instr = "\\n\\nPARA USAR FERRAMENTAS, RESPONDA COM ESTE JSON:\\n{ \"tool\": \"consultar_estoque\", \"args\": { \"termo\": \"...\" } }\\nOU\\n{ \"tool\": \"ver_status_orcamento\", \"args\": { \"cliente_nome\": \"...\" } }"
                 
                 agent = Agent(
                     model=model,
                     description=f"Você é a Camila, assistente virtual. Falando com um {role}.",
                     instructions=[instructions + manual_tool_instr],
                     storage=agent_storage,
                     session_id=chat_id, # Link session to WhatsApp number
                     add_history_to_context=True,
                     num_history_responses=5,
                     enable_session_summaries=True,
                     # Agno automatically handles Short-term, Long-term, Summaries if enabled in storage/agent
                     markdown=True
                 )
                 
                 try:
                     # 1. Run Agent (history managed by Agno Storage)
                     response = agent.run(text)
                     content = response.content
                     
                     # 2. Check for Manual Tool Call
                     tool_result = None
                     json_match = re.search(r'\{.*"tool":.*\}', content, re.DOTALL)
                     
                     if json_match:
                         try:
                             json_str = json_match.group(0)
                             if "```json" in json_str:
                                 json_str = json_str.replace("```json", "").replace("```", "").strip()
                             elif "```" in json_str:
                                 json_str = json_str.replace("```", "").strip()
                                 
                             data = json.loads(json_str)
                             tool_name = data.get('tool')
                             args = data.get('args', {})
                             
                             # Access Control for Tools
                             if role == 'client' and tool_name == 'consultar_estoque':
                                 tool_result = "ERRO: Cliente não tem permissão para consultar estoque interno diretamente."
                             elif tool_name == 'consultar_estoque':
                                 tool_result = consultar_estoque(args.get('termo', ''))
                             elif tool_name == 'ver_status_orcamento':
                                 # TODO: Filter by client name if role == client
                                 tool_result = ver_status_orcamento(args.get('cliente_nome', ''))
                                 
                             if tool_result:
                                 final_prompt = f"Assistant: {content}\\n\\nSystem: Resultado da ferramenta: {tool_result}\\n\\nAgora responda ao usuário (sem JSON)."
                                 response = agent.run(final_prompt)
                                 content = response.content
                         except Exception as e:
                             print(f"Manual tool error: {e}")
                             
                     response_text = content
                 except Exception as e:
                    response_text = f"[ERRO IA] Falha: {str(e)}"
             else:
                 response_text = "[ERRO CONFIG] Modelo não configurado."

    except Exception as e:
        response_text = f"[ERRO GERAL] {str(e)}"
        
    # Send via Waha ONLY if NOT simulation
    if not is_simulation:
        try:
            db = get_db()
            chat = db.execute("SELECT remote_jid FROM whatsapp_chats WHERE id = ?", (chat_id,)).fetchone()
            if chat:
                waha.send_message(chat['remote_jid'], response_text)
        except Exception as e:
            print(f"Waha Error: {e}")

    # Save to local table for UI visibility
    db = get_db()
    db.execute("INSERT INTO whatsapp_messages (chat_id, sender, content, status, timestamp) VALUES (?, 'camila', ?, 'sent', datetime('now'))",
               (chat_id, response_text))
    db.execute("UPDATE whatsapp_chats SET last_message_at = datetime('now') WHERE id = ?", (chat_id,))
    db.commit()
