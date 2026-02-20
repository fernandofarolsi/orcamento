import zipfile, re
filepath = 'treino/Nova pasta/roupeiro 2 portas.promob'
with zipfile.ZipFile(filepath, 'r') as z:
    amb_path = next((n for n in z.namelist() if 'ambient3d' in n.lower()), None)
    print("Path:", amb_path)
    data = None
    for enc in ['utf-8-sig', 'utf-16-sig', 'utf-8', 'utf-16']:
        try:
            data = z.read(amb_path).decode(enc)
            print("Encoding:", enc)
            break
        except:
            continue
    if data:
        print("BUDGET:", '<BUDGETINFORMATION' in data)
        print("Descriptions:", len(re.findall(r'DESCRIPTION="([^"]+)"', data)))
        print("BUDGETINFO BUDGET='Y':", len(re.findall(r'<BUDGETINFORMATION\s+([^>]+)BUDGET="Y"', data)))
