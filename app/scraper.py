import requests
from bs4 import BeautifulSoup
import time
import sqlite3
from datetime import datetime
from app.database import DATABASE

def fetch_price_leomadeiras(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Selector: .price-template or .product-price
            price_elem = soup.select_one('.price-template .best-price') or soup.find(class_='product-price')
            if price_elem:
                price_text = price_elem.get_text().strip().replace('R$', '').replace('.', '').replace(',', '.')
                return float(price_text)
    except Exception as e:
        print(f"Erro LeoMadeiras: {e}")
    return 0.0

def fetch_price_madeverde(url):
    try:
        # Madeverde often requires CEP in cookie or session. 
        # Trying public page first.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cookie': 'cep=01310-100' # Tentar forçar CEP via cookie
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Selectors seen: .preco-venda, .preco-promocional
            price_elem = soup.select_one('.preco-promocional') or soup.select_one('.preco-venda')
            if price_elem:
                price_text = price_elem.get_text().strip().replace('R$', '').replace('.', '').replace(',', '.')
                return float(price_text)
    except Exception as e:
        print(f"Erro Madeverde: {e}")
    return 0.0

def fetch_price_madeiranit(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Selector: .product-info-main .price
            price_elem = soup.select_one('.product-info-main .price')
            if price_elem:
                price_text = price_elem.get_text().strip().replace('R$', '').replace('.', '').replace(',', '.')
                return float(price_text)
    except Exception as e:
        print(f"Erro Madeiranit: {e}")
    return 0.0

def raspador_site(site_name, url_override=None):
    """
    Raspador REAL que busca preços nos URLs definidos.
    Aceita url_override para raspar itens específicos do banco de dados.
    """
    items = []
    
    # URLs hardcoded (fallback)
    urls = {
        'leomadeiras': 'https://www.leomadeiras.com.br/p/10288987/mdf-branco-texturizado-fsc-15mm-2750x1850mm-2-faces-duratex',
        'madeverde': 'https://www.madeverde.com.br/mdf-naval-branco-tx-15mm-02-faces-duratex',
        'madeiranit': 'https://www.madeiranit.com.br/mdf-branco-texturizado-15mm-2-faces-185-x-275cm-duratex'
    }

    url = url_override if url_override else urls.get(site_name)
    
    if not url: return []

    price = 0.0
    # Se for override, não temos nome padrão fácil sem passar.
    # Mas o chamador já tem o nome. O raspador retorna items encontrados.
    # Vamos manter nome genérico se for override, o chamador atualiza o DB.
    nome_padrao = 'MDF Branco TX 15mm (Real Time)' if not url_override else 'Item Raspado'

    try:
        if site_name == 'leomadeiras':
            price = fetch_price_leomadeiras(url)
        elif site_name == 'madeverde':
            price = fetch_price_madeverde(url)
        elif site_name == 'madeiranit':
            price = fetch_price_madeiranit(url)
    except Exception as e:
        print(f"Erro raspando {site_name} ({url}): {e}")
        return []
    
    if price > 0:
        items.append({
            'nome': nome_padrao,
            'preco': price,
            'site': site_name
        })
    
    return items


def run_scraping_job(site_target='all'):
    """
    Executa a raspagem independente de contexto Flask para uso em threads.
    """
    sites = ['madeiranit', 'madeverde', 'leomadeiras']
    if site_target != 'all' and site_target in sites:
        sites = [site_target]
        
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    stats = {'updated': 0, 'created': 0, 'errors': 0, 'details': {}}
    
    for site in sites:
        try:
            items = raspador_site(site)
            site_stats = {'u': 0, 'c': 0}
            
            for item in items:
                existing = db.execute('SELECT id, custo_unitario FROM estoque WHERE nome = ? AND site_origem = ?', 
                                      (item['nome'], item['site'])).fetchone()
                
                if existing:
                    if existing['custo_unitario'] != item['preco']:
                        db.execute('UPDATE estoque SET custo_unitario=?, last_update=CURRENT_TIMESTAMP WHERE id=?',
                                   (item['preco'], existing['id']))
                        site_stats['u'] += 1
                else:
                    db.execute('INSERT INTO estoque (nome, categoria, unidade, quantidade, custo_unitario, site_origem) VALUES (?, ?, ?, ?, ?, ?)',
                               (item['nome'], 'Material Raspado', 'Unidade', 0, item['preco'], item['site']))
                    site_stats['c'] += 1
            
            stats['details'][site] = site_stats
            stats['updated'] += site_stats['u']
            stats['created'] += site_stats['c']
            
        except Exception as e:
            print(f"Erro raspando {site}: {e}")
            stats['errors'] += 1
            
    db.commit()
    db.close()
    return stats

def scraper_worker():
    """
    Verifica o horário para raspagem automática em background.
    """
    print("Scraper Worker iniciado.")
    while True:
        try:
            # Nova conexão por ciclo para evitar problemas de thread
            db = sqlite3.connect(DATABASE)
            db.row_factory = sqlite3.Row
            rows = db.execute('SELECT * FROM settings').fetchall()
            db.close()
            settings = {r['key']: r['value'] for r in rows}
            
            ativa = settings.get('raspagem_ativa') == 'true'
            hora = settings.get('raspagem_hora', '02:00')
            
            if ativa:
                agora = datetime.now().strftime('%H:%M')
                if agora == hora:
                    print(f"[{datetime.now()}] Iniciando raspagem agendada...")
                    run_scraping_job('all')
                    time.sleep(61) # Evita rodar no mesmo minuto
                    continue
        except Exception as e:
            print(f"Erro no Scraper Worker: {e}")
            
        time.sleep(30)
