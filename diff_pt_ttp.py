import os
import difflib

# Kullanicinin belirttigi yedek klasoru (tam yolunu tahmin ediyorum, gerekirse duzeltiriz)
backup_root = r'C:\Users\kadir.kumas\Desktop\Broker_Backups\broker_local_20261018_150846'

# Yedek klasorunun icinde backend var mi diye kontrol et
if os.path.exists(os.path.join(backup_root, 'backend', 'position_manager.py')):
    old_pm_path = os.path.join(backup_root, 'backend', 'position_manager.py')
elif os.path.exists(os.path.join(backup_root, 'position_manager.py')):
    old_pm_path = os.path.join(backup_root, 'position_manager.py')
else:
    print(f"HATA: Yedek klasorunde position_manager.py bulunamadi! Yol: {backup_root}")
    old_pm_path = None

new_pm_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'

if old_pm_path and os.path.exists(old_pm_path):
    print("=== 18 EKIM YEDEGI ILE MEVCUT KOD ARASINDAKI FARKLAR (PT/TTP BLOGU) ===")
    old_lines = open(old_pm_path, 'r', encoding='utf-8').readlines()
    new_lines = open(new_pm_path, 'r', encoding='utf-8').readlines()

    # Sadece PT ve TTP ile ilgili satirlari karsilastir
    diff = difflib.unified_diff(
        [l for l in old_lines if 'pt_enabled' in l or 'state["active"]' in l or 'profit_pct' in l or 'tp_pct' in l],
        [l for l in new_lines if 'pt_enabled' in l or 'state["active"]' in l or 'profit_pct' in l or 'tp_pct' in l],
        fromfile='18_EKIM_YEDEGI',
        tofile='MEVCUT_KOD',
        lineterm=''
    )

    for line in diff:
        print(line.rstrip())
