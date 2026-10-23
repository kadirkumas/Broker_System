import os
import difflib

backup_root = r'C:\Users\kadir.kumas\Desktop\Broker_Backups'
new_pm_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'

# 1. Yedekler arasinda position_manager.py dosyasini bul
target_backup = None
for root, dirs, files in os.walk(backup_root):
    if 'position_manager.py' in files and '20261018_150846' in root:
        target_backup = os.path.join(root, 'position_manager.py')
        break

if not target_backup:
    print("HATA: 20261018_150846 iceren klasorde position_manager.py bulunamadi!")
    print("Bulunan tum position_manager.py dosyalari:")
    for root, dirs, files in os.walk(backup_root):
        if 'position_manager.py' in files:
            print(f" - {os.path.join(root, 'position_manager.py')}")
else:
    print(f"Karsilastirilacak Yedek: {target_backup}")
    print(f"Mevcut Kod           : {new_pm_path}\n")
    
    old_lines = open(target_backup, 'r', encoding='utf-8').readlines()
    new_lines = open(new_pm_path, 'r', encoding='utf-8').readlines()

    print("=== 18 EKIM YEDEGI ILE MEVCUT KOD ARASINDAKI PT/TTP FARKLARI ===")
    
    # Sadece PT ve TTP ile ilgili satirlari filtrele
    old_filtered = [l for l in old_lines if any(x in l for x in ['pt_enabled', 'state["active"]', 'profit_pct', 'tp_pct'])]
    new_filtered = [l for l in new_lines if any(x in l for x in ['pt_enabled', 'state["active"]', 'profit_pct', 'tp_pct'])]

    diff = difflib.unified_diff(
        old_filtered,
        new_filtered,
        fromfile='18_EKIM_YEDEGI',
        tofile='MEVCUT_KOD',
        lineterm=''
    )

    has_diff = False
    for line in diff:
        if line.startswith('-') and not line.startswith('---'):
            print(f"SILINEN/ESKI : {line[1:].strip()[:200]}")
            has_diff = True
        elif line.startswith('+') and not line.startswith('+++'):
            print(f"EKLENEN/YENI : {line[1:].strip()[:200]}")
            has_diff = True
            
    if not has_diff:
        print("Hicbir fark yok! PT/TTP mantigi 18 Ekim'den beri degismemis.")
