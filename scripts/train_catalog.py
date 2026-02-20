import os
import zipfile
import re
import sqlite3
import xml.etree.ElementTree as ET

import sys

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(BASE_DIR, 'app', 'app.db')

# Default training dir, but can be overridden via command line
TRAIN_DIR = os.path.join(BASE_DIR, 'treino')
if len(sys.argv) > 1:
    TRAIN_DIR = os.path.abspath(sys.argv[1])

def train():
    if not os.path.exists(TRAIN_DIR):
        print(f"Directory {TRAIN_DIR} not found.")
        return

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"Starting Training from: {TRAIN_DIR}")
    
    # 1. Get already mapped items to exclude them
    mapped_names = {row['promob_name'] for row in cursor.execute("SELECT promob_name FROM promob_mappings WHERE target_id IS NOT NULL").fetchall()}
    
    discovery = {}

    # 2. Walk through files
    matched_files = []
    for root, _, files in os.walk(TRAIN_DIR):
        for f in files:
            if f.endswith(('.promob', '.bak')):
                matched_files.append(os.path.join(root, f))
    
    print(f"Found {len(matched_files)} potential files.")

    for i, filepath in enumerate(matched_files):
        if i % 10 == 0:
            print(f"Processing file {i+1}/{len(matched_files)}...")
            
        try:
            file_entities = 0
            with zipfile.ZipFile(filepath, 'r') as z:
                amb_path = next((n for n in z.namelist() if 'ambient3d' in n.lower()), None)
                if not amb_path:
                    continue
                # Try different encodings
                raw_data = z.read(amb_path)
                data = None
                for enc in ['utf-8-sig', 'utf-16-sig', 'utf-8', 'utf-16']:
                    try:
                        data = raw_data.decode(enc)
                        break
                    except:
                        continue
                
                if data:
                    # HEURISTIC: Is this a budgeted file or legacy?
                    is_budget_file = '<BUDGETINFORMATION' in data
                    found_items = []
                    
                    # Common Furniture Whitelist
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

                    def clean_furniture_name(name):
                        if not name: return None
                        name = re.sub(r'\$[\w]+\$', '', name)
                        name = re.sub(r'#[\w]+#', '', name)
                        return name.replace('  ', ' ').strip()

                    if is_budget_file:
                        # Strategy A: Budget-centric
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
                            
                            name = clean_furniture_name(name)
                            if not name or len(name) < 3: continue
                            
                            lower_name = name.lower()
                            if not any(key in lower_name for key in furniture_keywords): continue
                            if any(part in lower_name for part in parts_blacklist): continue
                            
                            dims = {}
                            for d, alt in [('L', 'WIDTH'), ('A', 'HEIGHT'), ('P', 'DEPTH')]:
                                val_matches = re.findall(rf'\b(?:{d}|{alt})="([\d.]+)"', window)
                                if val_matches: dims[d] = float(val_matches[-1])
                            
                            if len(dims) == 3:
                                found_items.append((name, dims))
                    
                    if not found_items:
                        # Strategy B: Tag-centric fallback (for files without BudgetInfo)
                        blocks = re.split(r'<(?:ENTITY|ITEM|INFORMACOES)\b', data)
                        for block in blocks:
                            if 'TYPE="MODULO"' in block or 'TYPE="WARDROBE"' in block:
                                # Name
                                desc = None
                                attr_desc = re.search(r'ID="DESCRIPTION"\s+VALUE="([^"]+)"', block)
                                if attr_desc:
                                    desc = attr_desc.group(1).strip()
                                else:
                                    dm = re.search(r'DESCRIPTION="([^"]*)"', block)
                                    if dm: desc = dm.group(1).strip()
                                
                                desc = clean_furniture_name(desc)
                                if not desc or len(desc) < 3: continue
                                
                                lower_desc = desc.lower()
                                # EXTREMELY STRICT for fallback: must be a known furniture type
                                if not any(key in lower_desc for key in furniture_keywords): continue
                                if any(part in lower_desc for part in parts_blacklist): continue
                                
                                # Dimensions
                                dims = {}
                                for d, alt in [('L', 'WIDTH'), ('A', 'HEIGHT'), ('P', 'DEPTH')]:
                                    val = re.search(rf'\b(?:{d}|{alt})="([\d.]+)"', block)
                                    if val: dims[d] = float(val.group(1))
                                
                                if len(dims) == 3:
                                    found_items.append((desc, dims))

                    # Strategy C: VIP Sub-components (Gaveteiros, Portas de Correr, Rodapés, Engrossos)
                    # We run this ALWAYS, regardless of Strategy A or B finding the main module
                    vip_keywords = [
                        'gaveta interna', 'gaveteiro', 'porta de correr', 'porta deslizante', 
                        'corpo de gaveta', 'moldura engros', 'rodapé', 'rodape', 'engrosso'
                    ]
                    matches = re.finditer(r'<ATTRIBUTE ID="DESCRIPTION" VALUE="([^"]+)"', data)
                    
                    for m in matches:
                        desc = m.group(1).strip()
                        lower_desc = desc.lower()
                        
                        if not any(k in lower_desc for k in vip_keywords):
                            continue
                            
                        # Pular sub-partes muito granulares
                        if 'fundo de gaveta' in lower_desc or 'lateral de gaveta' in lower_desc or 'frente gaveta' in lower_desc or 'posterior de gaveta' in lower_desc:
                            continue
                            
                        start_pos = m.end()
                        end_pos = min(len(data), start_pos + 3000)
                        window = data[start_pos:end_pos]
                        
                        dim_match = re.search(r'<INSERTDIMENSION WIDTH="([\d.]+)" HEIGHT="([\d.]+)" DEPTH="([\d.]+)"', window)
                        if dim_match:
                            # Filtro de sanidade: ignorar se tamanho for 1x1x1 (placeholder Promob)
                            l, a, p = float(dim_match.group(1)), float(dim_match.group(2)), float(dim_match.group(3))
                            if l > 5 and a > 5 and p > 5:
                                clean_desc = clean_furniture_name(desc)
                                found_items.append((clean_desc, {'L': l, 'A': a, 'P': p}))

                    # Process results

                    for name, dims in found_items:
                        if name not in discovery:
                            discovery[name] = {'occurrences': 0, 'L': [], 'A': [], 'P': []}
                        discovery[name]['occurrences'] += 1
                        discovery[name]['L'].append(dims['L'])
                        discovery[name]['A'].append(dims['A'])
                        discovery[name]['P'].append(dims['P'])
                        file_entities += 1
                
                # if file_entities > 0:
                #    print(f"Found {file_entities} entities in {os.path.basename(filepath)}")
                    
        except Exception as e:
            print(f"Error processing {os.path.basename(filepath)}: {e}")

    # 3. Save to database
    print("\nSaving patterns to database...")
    new_items = 0
    updated_items = 0
    
    for name, data in discovery.items():
        avg_L = round(sum(data['L']) / len(data['L']), 0)
        avg_A = round(sum(data['A']) / len(data['A']), 0)
        avg_P = round(sum(data['P']) / len(data['P']), 0)
        occ = data['occurrences']
        
        try:
            cursor.execute('''
                INSERT INTO discovered_patterns (name, avg_L, avg_A, avg_P, occurrences)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET 
                    avg_L = (avg_L + excluded.avg_L) / 2,
                    avg_A = (avg_A + excluded.avg_A) / 2,
                    avg_P = (avg_P + excluded.avg_P) / 2,
                    occurrences = occurrences + excluded.occurrences,
                    is_reviewed = 0
            ''', (name, avg_L, avg_A, avg_P, occ))
            if cursor.rowcount > 0:
                new_items += 1
            else:
                updated_items += 1
        except Exception as e:
            print(f"DB Error saving {name}: {e}")

    conn.commit()
    conn.close()
    print(f"\nTraining Complete!")
    print(f"New Patterns Found: {new_items}")
    print(f"Patterns Updated: {updated_items}")

if __name__ == "__main__":
    train()
