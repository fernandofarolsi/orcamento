import os
import zipfile
import hashlib
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# Path Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE = os.path.join(BASE_DIR, 'app', 'app.db')
TRAIN_DIR = os.path.join(BASE_DIR, 'treino')

def get_file_hash(filepath):
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

import re

def extract_promob_data(filepath):
    """Extract materials and module names from a Promob file."""
    materials = set()
    modules = set()
    
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            names = z.namelist()
            
            # 1. Materials
            mat_path = next((n for n in names if 'materials.material' in n.lower()), None)
            if mat_path:
                try:
                    data = z.read(mat_path)
                    # Handle UTF-16 with possible BOM
                    try:
                        content = data.decode('utf-16-sig')
                    except:
                        content = data.decode('utf-8', errors='ignore')
                    
                    # Clean up content (sometimes there's junk at the start)
                    content = content.strip()
                    if not content.startswith('<'):
                        idx = content.find('<')
                        if idx != -1:
                            content = content[idx:]
                    
                    if content:
                        root = ET.fromstring(content)
                        for mat in root.findall('.//MATERIAL'):
                            name = mat.get('NAME')
                            finish = mat.get('FINISH')
                            model = mat.get('MODEL')
                            if name:
                                # Create a unique key for mapping
                                full_name = name
                                if finish: full_name += f" | {finish}"
                                if model: full_name += f" | {model}"
                                materials.add(full_name)
                except Exception as e:
                    print(f"Error parsing materials in {filepath}: {e}")

            # 2. Modules (from ambient3d or similar)
            # Ambient3D can be HUGE. Regex is safer and faster for just descriptions.
            amb_path = next((n for n in names if 'ambient3d' in n.lower()), None)
            if amb_path:
                try:
                    data = z.read(amb_path)
                    try:
                        content = data.decode('utf-16-sig')
                    except:
                        content = data.decode('utf-8', errors='ignore')
                    
                    # Regex for <ENTITY DESCRIPTION="Balcão 2p" ...>
                    # We look for DESCRIPTION="Value"
                    matches = re.findall(r'DESCRIPTION="([^"]+)"', content)
                    for match in matches:
                        # Filter out common non-module descriptions if needed
                        # For now, collect everything unique
                        if match and len(match) > 2:
                            modules.add(match)
                except Exception as e:
                    print(f"Error parsing modules in {filepath}: {e}")

    except Exception as e:
        print(f"Error opening {filepath}: {e}")
        
    return materials, modules

def run_miner(limit=1000):
    """Main mining loop."""
    if not os.path.exists(TRAIN_DIR):
        print(f"Directory {TRAIN_DIR} not found.")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Use os.walk for recursive search
    files_to_process = []
    for root, dirs, files in os.walk(TRAIN_DIR):
        for f in files:
            if f.endswith(('.promob', '.bak')):
                files_to_process.append(os.path.join(root, f))
                
    print(f"Found {len(files_to_process)} files in {TRAIN_DIR} (including subdirs)")
    
    processed_count = 0
    skipped_count = 0
    new_materials = 0
    new_modules = 0
    
    # Sort files to ensure stable processing order if limit is used
    files_to_process.sort()

    for filepath in files_to_process:
        if processed_count >= limit:
            break
            
        filename = os.path.basename(filepath)
        file_hash = get_file_hash(filepath)
        
        # Check if already processed
        cursor.execute("SELECT id FROM processed_files WHERE file_hash = ?", (file_hash,))
        if cursor.fetchone():
            skipped_count += 1
            continue
            
        print(f"[{processed_count+1}/{limit}] Processing: {filename}...")
        mats, mods = extract_promob_data(filepath)
        
        # Save Materials
        for m in mats:
            try:
                cursor.execute("INSERT OR IGNORE INTO promob_mappings (promob_name, target_type) VALUES (?, ?)", (m, 'material'))
                if cursor.rowcount > 0:
                    new_materials += 1
            except Exception as e:
                print(f"DB Error (material): {e}")

        # Save Modules
        for m in mods:
            try:
                cursor.execute("INSERT OR IGNORE INTO promob_mappings (promob_name, target_type) VALUES (?, ?)", (m, 'item'))
                if cursor.rowcount > 0:
                    new_modules += 1
            except Exception as e:
                print(f"DB Error (module): {e}")
                
        # Mark as processed
        cursor.execute("INSERT INTO processed_files (file_hash, filename) VALUES (?, ?)", (file_hash, filename))
        conn.commit()
        processed_count += 1
        
    conn.close()
    print(f"\nMining Complete!")
    print(f"Files Processed (New): {processed_count}")
    print(f"Files Already Processed: {skipped_count}")
    print(f"New Materials Mapped: {new_materials}")
    print(f"New Modules Mapped: {new_modules}")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run_miner(limit)
