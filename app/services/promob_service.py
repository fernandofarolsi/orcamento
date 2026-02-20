import zipfile
import xml.etree.ElementTree as ET
import re
import os
from app.database import get_db

class PromobService:
    @staticmethod
    def extract_data(filepath):
        """
        Parses a Promob file and returns structured data for budgeting.
        """
        results = {
            'client': None,
            'items': [],
            'materials': [],
            'unknowns': [] # Items/Materials that need manual mapping
        }

        try:
            with zipfile.ZipFile(filepath, 'r') as z:
                names = z.namelist()

                # 1. Client Info
                client_path = next((n for n in names if 'dataclient' in n.lower()), None)
                if client_path:
                    try:
                        data = z.read(client_path).decode('utf-16-sig', errors='ignore')
                        root = ET.fromstring(data)
                        client_node = root.find('.//CLIENT')
                        if client_node is not None:
                            results['client'] = {
                                'nome': client_node.get('NAME'),
                                'email': client_node.get('EMAIL'),
                                'fone': client_node.get('PHONE')
                            }
                        else:
                            # Fallback if XML structure is slightly different
                            name_match = re.search(r'NAME="([^"]+)"', data)
                            if name_match:
                                results['client'] = {'nome': name_match.group(1)}
                    except:
                        pass

                # 2. Materials (MDFs, Hardwares, etc)
                mat_path = next((n for n in names if 'materials.material' in n.lower()), None)
                if mat_path:
                    try:
                        data = z.read(mat_path).decode('utf-16-sig', errors='ignore')
                        # Extraction of materials and their finishes
                        root = ET.fromstring(data)
                        for mat in root.findall('.//MATERIAL'):
                            name = mat.get('NAME')
                            finish = mat.get('FINISH')
                            model = mat.get('MODEL')
                            if name:
                                materials_key = name
                                if finish: materials_key += f" | {finish}"
                                if model: materials_key += f" | {model}"
                                results['materials'].append({
                                    'raw_name': materials_key,
                                    'name': name,
                                    'finish': finish,
                                    'model': model
                                })
                    except:
                        pass

                # 3. Modules (Robust Extraction)
                amb_path = next((n for n in names if 'ambient3d' in n.lower()), None)
                if amb_path:
                    try:
                        raw_data = z.read(amb_path)
                        data = None
                        # Try multiple encodings
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
                            
                            # Whitelist and Blacklist for consistency
                            furniture_keywords = ['balcão', 'armário', 'torre', 'nicho', 'paneleiro', 'aéreo', 'gaveteiro', 'criado', 'cama', 'mesa', 'painel', 'adega', 'banheiro', 'dormitório', 'guarda-roupa', 'modulo', 'módulo']
                            parts_blacklist = ['lateral', 'base', 'sarrafo', 'fundo', 'travessa', 'prateleira', 'porta reta', 'frente reta', 'dobradiça', 'corrediça', 'puxador']

                            def clean_name(name):
                                if not name: return None
                                name = re.sub(r'\$[\w]+\$', '', name)
                                name = re.sub(r'#[\w]+#', '', name)
                                return name.replace('  ', ' ').strip()

                            if is_budget_file:
                                # A: Budget-centric
                                budget_matches = re.finditer(r'<BUDGETINFORMATION\s+([^>]+)BUDGET="Y"', data)
                                for m in budget_matches:
                                    info_attr = m.group(1)
                                    window = data[max(0, m.start()-3000) : min(len(data), m.end()+500)]
                                    
                                    name = None
                                    dn = re.search(r'DESCRIPTION="([^"]+)"', info_attr)
                                    if dn: name = dn.group(1).strip()
                                    if not name or name.lower() in ['padrão', 'default']:
                                        an = re.search(r'ID="DESCRIPTION"\s+VALUE="([^"]+)"', window)
                                        if an: name = an.group(1).strip()
                                    
                                    name = clean_name(name)
                                    if not name or len(name) < 3: continue
                                    lower_name = name.lower()
                                    if not any(k in lower_name for k in furniture_keywords): continue
                                    if any(p in lower_name for p in parts_blacklist): continue
                                    
                                    dims = {}
                                    for d, alt in [('L', 'WIDTH'), ('A', 'HEIGHT'), ('P', 'DEPTH')]:
                                        val_matches = re.findall(rf'\b(?:{d}|{alt})="([\d.]+)"', window)
                                        if val_matches: dims[d] = float(val_matches[-1])
                                    
                                    if len(dims) == 3:
                                        found_items.append({'raw_name': name, 'L': dims['L'], 'A': dims['A'], 'P': dims['P']})
                            
                            if not found_items:
                                # B: Tag-centric fallback
                                blocks = re.split(r'<(?:ENTITY|ITEM|INFORMACOES)\b', data)
                                for block in blocks:
                                    if 'TYPE="MODULO"' in block or 'TYPE="WARDROBE"' in block:
                                        desc = None
                                        ad = re.search(r'ID="DESCRIPTION"\s+VALUE="([^"]+)"', block)
                                        if ad: desc = ad.group(1).strip()
                                        else:
                                            dm = re.search(r'DESCRIPTION="([^"]*)"', block)
                                            if dm: desc = dm.group(1).strip()
                                        
                                        desc = clean_name(desc)
                                        if not desc or len(desc) < 3: continue
                                        lower_desc = desc.lower()
                                        if not any(k in lower_desc for k in furniture_keywords): continue
                                        if any(p in lower_desc for p in parts_blacklist): continue
                                        
                                        dims = {}
                                        for d, alt in [('L', 'WIDTH'), ('A', 'HEIGHT'), ('P', 'DEPTH')]:
                                            v = re.search(rf'\b(?:{d}|{alt})="([\d.]+)"', block)
                                            if v: dims[d] = float(v.group(1))
                                        
                                        if len(dims) == 3:
                                            found_items.append({'raw_name': desc, 'L': dims['L'], 'A': dims['A'], 'P': dims['P']})
                            
                            results['items'].extend(found_items)
                    except Exception as e:
                        print(f"Error extracting modules from {amb_path}: {e}")

        except Exception as e:
            print(f"Error parsing Promob file {filepath}: {e}")
            return None

        return results

    @staticmethod
    def map_data(db, raw_data):
        """
        Maps raw Promob names to internal Catalog/Stock IDs using the mappings table.
        """
        mapped_results = {
            'client': raw_data['client'],
            'items': [],
            'materials': [],
            'unknowns': []
        }

        # Handle Items (Modules)
        for item in raw_data['items']:
            mapping = db.execute("SELECT target_type, target_id FROM promob_mappings WHERE promob_name = ?", 
                                 (item['raw_name'],)).fetchone()
            
            if mapping and mapping['target_id']:
                item['catalogo_id'] = mapping['target_id']
                mapped_results['items'].append(item)
            else:
                if item['raw_name'] not in [u['name'] for u in mapped_results['unknowns']]:
                    mapped_results['unknowns'].append({'type': 'item', 'name': item['raw_name']})
                mapped_results['items'].append(item) # Still include but it will be flagged

        # Handle Materials
        for mat in raw_data['materials']:
            mapping = db.execute("SELECT target_type, target_id FROM promob_mappings WHERE promob_name = ?", 
                                 (mat['raw_name'],)).fetchone()
            
            if mapping and mapping['target_id']:
                mat['estoque_id'] = mapping['target_id']
                mapped_results['materials'].append(mat)
            else:
                if mat['raw_name'] not in [u['name'] for u in mapped_results['unknowns']]:
                    mapped_results['unknowns'].append({'type': 'material', 'name': mat['raw_name']})
                mapped_results['materials'].append(mat)

        return mapped_results
