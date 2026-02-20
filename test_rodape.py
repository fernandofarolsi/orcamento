import zipfile, re
filepath = 'treino/Nova pasta/rodape.promob'
with zipfile.ZipFile(filepath, 'r') as z:
    amb_path = next((n for n in z.namelist() if 'ambient3d' in n.lower()), None)
    data = None
    for enc in ['utf-8-sig', 'utf-16-sig', 'utf-8', 'utf-16']:
        try:
            data = z.read(amb_path).decode(enc)
            break
        except: continue
        
    print("Testando EXTRAÇÃO VIP para rodape:")
    vip_keywords = ['moldura engros', 'rodapé', 'rodape', 'engrosso']
    matches = re.finditer(r'<ATTRIBUTE ID="DESCRIPTION" VALUE="([^"]+)"', data)
    for m in matches:
        desc = m.group(1).strip()
        lower_desc = desc.lower()
        if any(k in lower_desc for k in vip_keywords):
            start_pos = m.end()
            end_pos = min(len(data), start_pos + 1000)
            window = data[start_pos:end_pos]
            dim_match = re.search(r'<INSERTDIMENSION WIDTH="([\d.]+)" HEIGHT="([\d.]+)" DEPTH="([\d.]+)"', window)
            if dim_match:
                print(f"Encontrou: {desc} -> L:{dim_match.group(1)} A:{dim_match.group(2)} P:{dim_match.group(3)}")
            else:
                print(f"Sem tag de dimensão para: {desc}")
