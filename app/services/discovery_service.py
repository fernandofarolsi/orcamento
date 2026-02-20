import os
import zipfile
import re
import xml.etree.ElementTree as ET
from app.database import get_db

class DiscoveryService:
    @staticmethod
    def get_suggested_items(db, train_dir=None, limit=50):
        """
        Fetches suggested items from the discovered_patterns table.
        Filters out items already reviewed or already mapped.
        """
        # Get already mapped names to be safe (double check)
        mapped_names = {row['promob_name'] for row in db.execute("SELECT promob_name FROM promob_mappings WHERE target_id IS NOT NULL").fetchall()}

        # Fetch from discovered_patterns
        rows = db.execute('''
            SELECT name, avg_L, avg_A, avg_P, occurrences 
            FROM discovered_patterns 
            WHERE is_reviewed = 0 
            ORDER BY occurrences DESC 
            LIMIT ?
        ''', (limit,)).fetchall()

        results = []
        for row in rows:
            if row['name'] in mapped_names:
                continue
            results.append({
                'name': row['name'],
                'occurrences': row['occurrences'],
                'avg_L': row['avg_L'],
                'avg_A': row['avg_A'],
                'avg_P': row['avg_P']
            })
        
        return results

    @staticmethod
    def calculate_edge_banding_4_sides(L, A, P):
        """
        Estimates total edge banding (meters) for a module fit on 4 sides of all pieces.
        Assumes standard structure: 2 sides, 1 base, 1 top, 2 shelves (average), 2 doors (average).
        Dimensions in mm.
        """
        L_m = L / 1000.0
        A_m = A / 1000.0
        P_m = P / 1000.0
        
        # Perimeter of one piece L x A = 2*(L+A)
        # 1. Externals (2 Laterais, 1 Base, 1 Teto)
        laterais = 2 * (2 * (A_m + P_m))
        base_teto = 2 * (2 * (L_m + P_m))
        
        # 2. Internals (Est. 2 Prateleiras)
        prateleiras = 2 * (2 * (L_m + P_m))
        
        # 3. Front (Est. 2 Portas)
        portas = 2 * (2 * (L_m/2 + A_m))
        
        total = laterais + base_teto + prateleiras + portas
        # Add 10% safety margin
        return round(total * 1.1, 2)
