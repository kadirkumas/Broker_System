import zipfile
import os
import difflib

zip_path = r'C:\Users\kadir.kumas\Desktop\Broker_Backups\local\broker_local_20261018_150846.zip'
new_pm_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'

# 1. ZIP icindeki position_manager.py dosyasini bul
target_in_zip = None
try:
    with zipfile.ZipFile(zip_path, 'r') as z:
        for name in z.namelist():
            if name.endswith('position_manager.py'):
                target_in_zip = name
                break
except Exception as e:
    print(f"ZIP acma hatasi: {e}")
    target_in_zip = None

if not target_in_zip:
    print("HATA: ZIP icinde position_manager.py bulunamadi!")
else:
    print(f"ZIP icinde bulunan dosya: {target_in_zip}\n")
    
    # ZIP'ten oku
    with zipfile.ZipFile(zip_path, 'r') as z:
        old_content = z.read(target_in_zip).decode('utf-8')
    
    new_content = open(new_pm_path, 'r', encoding='utf-8').read()
    
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')

    print("=== 18 EKIM YEDEGI ILE MEVCUT KOD ARASINDAKI PT/TTP FARKLARI ===")
    
    # Sadece PT ve TTP ile ilgili satirlari filtrele
    keywords = ['pt_enabled', 'state["active"]', 'profit_pct', 'tp_pct', 'pt_done_flag', 'pt_percent_val']
    old_filtered = [l for l in old_lines if any(x in l for x in keywords)]
    new_filtered = [l for l in new_lines if any(x in l for x in keywords)]

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
            print(f"SILINEN/ESKI : {line[1:].strip()[:220]}")
            has_diff = True
        elif line.startswith('+') and not line.startswith('+++'):
            print(f"EKLENEN/YENI : {line[1:].strip()[:220]}")
            has_diff = True
            
    if not has_diff:
        print("\nHicbir fark yok! PT/TTP mantigi 18 Ekim'den beri degismemis.")
        print("Yani sorun kod degisikliginden degil, piyasa kosullarindan veya baska bir yerden kaynaklaniyor.")
