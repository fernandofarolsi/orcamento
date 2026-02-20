import zipfile, re, glob
files = glob.glob('treino/Nova pasta/roup*.promob')
for filepath in files:
    print(f"\n--- Analisando: {filepath} ---")
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
            found = False
            for m in budget_matches:
                info_attr = m.group(1)
                name = None
                dn = re.search(r'DESCRIPTION="([^"]+)"', info_attr)
                if dn: name = dn.group(1).strip()
                
                if not name or name.lower() in ['padrão', 'default', 'config felipe']:
                    start_win = max(0, m.start() - 3000)
                    end_win = min(len(data), m.end() + 500)
                    window = data[start_win:end_win]
                    an = re.search(r'ID="DESCRIPTION"\s+VALUE="([^"]+)"', window)
                    if an: name = an.group(1).strip()
                print(f"Encontrou entidade orçada: '{name}'")
                found = True
            if not found:
                print("Nenhuma entidade BUDGET='Y' encontrada.")
