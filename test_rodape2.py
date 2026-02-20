import zipfile, re
filepath = 'treino/Nova pasta/rodape.promob'
with zipfile.ZipFile(filepath, 'r') as z:
    amb_path = next((n for n in z.namelist() if 'ambient3d' in n.lower()), None)
    data = None
    for enc in ['utf-8-sig', 'utf-8', 'latin1']:
        try:
            data = z.read(amb_path).decode(enc)
            break
        except: continue
    
    if data:
        # Pega 300 caracteres antes e depois da primeira ocorrencia
        match = re.search(r'(.{300}Moldura Engros.{300})', data, re.DOTALL)
        if match:
            print("--- RAW BLOCK MOLDURA ENGROS ---")
            print(match.group(1))
        else:
            print("Nenhuma moldura encontrada com essa string exata.")
