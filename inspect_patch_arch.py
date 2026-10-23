import os

backend = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend'
pm_path = os.path.join(backend, 'position_manager.py')

print("=== 1. MEVCUT KODDA PT KONTROL BLOGU VE F-YORUMLARI (1595-1615) ===")
lines = open(pm_path, 'r', encoding='utf-8').readlines()
for j in range(1595, min(1615, len(lines))):
    print(f"[{j+1}] {lines[j].rstrip()}")

print("\n=== 2. YEDEKLERDE PT KONTROL SATIRI VAR MI? ===")
backups = ['.bak_f354', '.bak_f405', '.bak_f410', '.bak_f411', '.bak_f345', '.bak_f346', '.bak_f333']
for bk in backups:
    bk_path = pm_path + bk
    if os.path.exists(bk_path):
        try:
            bk_lines = open(bk_path, 'r', encoding='utf-8').readlines()
            found = None
            for i, l in enumerate(bk_lines):
                if "pt_enabled and not pt_done_flag" in l:
                    found = (i+1, l.strip()[:200])
                    break
            if found:
                print(f"  [{bk}] Satir {found[0]}: {found[1]}")
            else:
                print(f"  [{bk}] PT kontrol satiri bulunamadi (farkli yazilmis olabilir).")
        except Exception as e:
            print(f"  [{bk}] Okuma hatasi: {e}")
    else:
        print(f"  [{bk}] Yedek yok.")

print("\n=== 3. TUM YEDEKLERDE 'state[\"active\"]' GECEN PT SATIRLARI ===")
import glob
for bk_path in sorted(glob.glob(pm_path + '.bak_*')):
    try:
        bk_lines = open(bk_path, 'r', encoding='utf-8').readlines()
        for i, l in enumerate(bk_lines):
            if "pt_enabled" in l and "state" in l and "active" in l and "profit_pct" in l:
                print(f"  [{os.path.basename(bk_path)}] Satir {i+1}: {l.strip()[:250]}")
                break
    except: pass
