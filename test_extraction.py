import zipfile, re
filepath = 'treino/Nova pasta/roupeiro 2 portas.promob'
with zipfile.ZipFile(filepath, 'r') as z:
    amb_path = next((n for n in z.namelist() if 'ambient3d' in n.lower()), None)
    data = None
    for enc in ['utf-8-sig', 'utf-16-sig', 'utf-8', 'utf-16']:
        try:
            data = z.read(amb_path).decode(enc)
            break
        except:
            continue
    if data:
        budget_matches = re.finditer(r'<BUDGETINFORMATION\s+([^>]+)BUDGET="Y"', data)
        for m in budget_matches:
            info_attr = m.group(1)
            start_win = max(0, m.start() - 3000)
            end_win = min(len(data), m.end() + 500)
            window = data[start_win:end_win]
            
            name = None
            dn = re.search(r'DESCRIPTION="([^"]+)"', info_attr)
            if dn: name = dn.group(1).strip()
            
            if not name or name.lower() in ['padrão', 'default', 'config felipe']:
                an = re.search(r'ID="DESCRIPTION"\s+VALUE="([^"]+)"', window)
                if an: name = an.group(1).strip()
            
            print(f"Raw Name: {name}")
            
            if name:
                name = re.sub(r'\$[\w]+\$', '', name)
                name = re.sub(r'#[\w]+#', '', name)
                name = name.replace('  ', ' ').strip()
                print(f"Clean Name: {name}")
            
            lower_name = name.lower() if name else ""
            furniture_keywords = [
                'balcão', 'armário', 'torre', 'nicho', 'paneleiro', 'aéreo', 
                'gaveteiro', 'criado', 'cama', 'mesa', 'painel', 'adega',
                'banheiro', 'dormitório', 'guarda-roupa', 'modulo', 'módulo',
                'roupeiro', 'closet', 'escrivaninha', 'estante', 'cristaleira'
            ]
            parts_blacklist = [
                'lateral', 'base', 'sarrafo', 'fundo', 'travessa', 'prateleira', 
                'porta reta', 'frente reta', 'dobradiça', 'corrediça', 'puxador',
                'trilho', 'perfil', 'ponteira', 'suporte', 'batedor'
            ]
            
            has_keyword = any(key in lower_name for key in furniture_keywords)
            has_blacklist = any(part in lower_name for part in parts_blacklist)
            
            print(f"Has Keyword: {has_keyword}, Has Blacklist: {has_blacklist}")
