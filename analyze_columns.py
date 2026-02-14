import pandas as pd
import glob

files = glob.glob('*.XLS')
found_any = False

for file_path in files:
    print(f"\n--- Checking {file_path} ---")
    try:
        # Check sheet '1.2.3' first, or fallback to first sheet if not exists
        xls = pd.ExcelFile(file_path)
        sheet = '1.2.3' if '1.2.3' in xls.sheet_names else xls.sheet_names[0]
        
        df = pd.read_excel(file_path, sheet_name=sheet, header=None)
        print(f"Scanning sheet '{sheet}'...")
        
        for i in range(10, min(60, len(df))):
            row_list = df.iloc[i].tolist()
            for j, val in enumerate(row_list):
                s_val = str(val)
                # Look for time pattern like '08:00'
                if ':' in s_val and len(s_val) <= 5 and s_val[0].isdigit():
                     print(f"FOUND Time at Row {i}, Col {j}: {s_val}")
                     # Print context (surrounding columns) to identify In/Out positions
                     context = [str(x) for x in row_list[max(0, j-2): j+3]]
                     print(f"Context (cols {max(0, j-2)} to {j+2}): {context}")
                     found_any = True
                     
            if found_any: break
        if found_any: break

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

if not found_any:
    print("No time data found in any file.")

