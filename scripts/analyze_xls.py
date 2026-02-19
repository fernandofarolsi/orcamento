import pandas as pd
import os

file_path = '001_2025_1_MON.XLS'

try:
    # Try reading as HTML first (common for "fake" XLS files exported by some systems)
    try:
        dfs = pd.read_html(file_path)
        print("Read as HTML. Found tables:")
        for i, df in enumerate(dfs):
            print(f"Table {i}:")
            print(df.head())
    except:
        # Load the Excel file 
        xls = pd.ExcelFile(file_path)
        sheet_name = '1.2.3'
        print(f"\n--- Sheet: {sheet_name} ---")
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        
        print("Shape:", df.shape)
        
        # Check Row 2 (Header info usually)
        print("\nRow 2 (Headers?):")
        print(df.iloc[2].tolist())

        # Check Row 9 (Table Headers?)
        print("\nRow 9 (Table Headers?):")
        print(df.iloc[9].tolist())
        
        # Check Row 15 (Data?)
        print("\nRow 15 (Data - 05 DOM/SEG?):")
        print(df.iloc[15].tolist())







except Exception as e:
    print(f"Error reading file: {e}")
