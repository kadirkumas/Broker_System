import os

backup_root = r'C:\Users\kadir.kumas\Desktop\Broker_Backups'

print(f"--- {backup_root} ICERIGI ---")
if not os.path.exists(backup_root):
    print("HATA: Broker_Backups klasoru bulunamadi!")
else:
    for root, dirs, files in os.walk(backup_root):
        level = root.replace(backup_root, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        if level < 3: # Cok derine inip ekrani doldurmasin
            for f in files:
                if f.endswith('.py') or f.endswith('.db') or f.endswith('.json'):
                    print(f"{indent}  {f}")
