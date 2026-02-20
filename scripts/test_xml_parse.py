import zipfile
import re

filepath = 'treino/Nova pasta/roupeiro 2 portas com gaveterio.promob'

with zipfile.ZipFile(filepath, 'r') as z:
    amb_path = next((n for n in z.namelist() if 'ambient3d' in n.lower()), None)
    data = None
    for enc in ['utf-8-sig', 'utf-16-sig', 'utf-8', 'utf-16']:
        try:
            data = z.read(amb_path).decode(enc)
            break
        except: continue
        
    print("--- Extração de Sub-Componentes por Regex Direcional ---")
    
    internal_keywords = ['gaveta interna', 'gaveta', 'porta reta', 'porta de correr', 'corpo de gaveta']
    
    # Encontrar todas as descrições
    matches = re.finditer(r'<ATTRIBUTE ID="DESCRIPTION" VALUE="([^"]+)"', data)
    found_internals = []
    
    for m in matches:
        desc = m.group(1).strip()
        lower_desc = desc.lower()
        
        # Check if it's an internal component we care about
        if not any(k in lower_desc for k in internal_keywords):
            continue
            
        # Pular coisas indesejadas
        if 'fundo de gaveta' in lower_desc or 'lateral de gaveta' in lower_desc or 'frente gaveta' in lower_desc or 'posterior de gaveta' in lower_desc:
            continue
            
        start_pos = m.end()
        end_pos = min(len(data), start_pos + 1000)
        window = data[start_pos:end_pos]
        
        dim_match = re.search(r'<INSERTDIMENSION WIDTH="([\d.]+)" HEIGHT="([\d.]+)" DEPTH="([\d.]+)"', window)
        if dim_match:
            dims = {'L': float(dim_match.group(1)), 'A': float(dim_match.group(2)), 'P': float(dim_match.group(3))}
            found_internals.append((desc, dims))
            
    print(f"Sub-componentes encontrados ({len(found_internals)}):")
    for name, d in found_internals:
        print(f" - {name}: L={d['L']}, A={d['A']}, P={d['P']}")
