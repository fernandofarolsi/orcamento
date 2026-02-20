import zipfile
import sys

def analyze_promob(filepath):
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            print("--- FILES IN ZIP ---")
            names = z.namelist()
            for name in names:
                print(f"  {name}")
            
            # Look for materials and ambient3d regardless of separator
            mat_path = next((n for n in names if 'materials.material' in n.lower()), None)
            amb_path = next((n for n in names if 'ambient3d' in n.lower()), None)
            client_path = next((n for n in names if 'dataclient' in n.lower()), None)

            if mat_path:
                print(f"\n--- {mat_path} ---")
                try:
                    data = z.read(mat_path).decode('utf-16', errors='ignore')
                    print(data[:2000])
                except Exception as e:
                    print(f"Error reading {mat_path}: {e}")

            if amb_path:
                print(f"\n--- {amb_path} ---")
                try:
                    data = z.read(amb_path).decode('utf-16', errors='ignore')
                    print(data[:2000])
                except Exception as e:
                    print(f"Error reading {amb_path}: {e}")
            
            if client_path:
                print(f"\n--- {client_path} ---")
                try:
                    data = z.read(client_path).decode('utf-16', errors='ignore')
                    # Look for client or color info
                    print(data[:1000])
                except Exception as e:
                    print(f"Error reading {client_path}: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_promob(sys.argv[1])
    else:
        print("Usage: python3 analyze_promob.py <path_to_promob>")
