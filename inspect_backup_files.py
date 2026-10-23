import os

backup_root = r'C:\Users\kadir.kumas\Desktop\Broker_Backups'

for sub in ['local', 'cloud']:
    target = os.path.join(backup_root, sub)
    print(f"\n--- {target} ICERIGI ---")
    if not os.path.exists(target):
        print("Klasor yok.")
        continue
    
    for root, dirs, files in os.walk(target):
        # Sadece ilk 3 seviyeyi goster
        level = root.replace(target, '').count(os.sep)
        if level > 3: continue
        
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        for f in files:
            size_kb = os.path.getsize(os.path.join(root, f)) / 1024
            print(f"{indent}  {f} ({size_kb:.1f} KB)")
