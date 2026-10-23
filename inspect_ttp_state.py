import sqlite3
import os

db_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\bot_data.db'
pm_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'

print("--- 1. VERITABANI: active_trades KOLONLARI ---")
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(active_trades)")
    cols = [c[1] for c in cur.fetchall()]
    print("Mevcut kolonlar:", cols)
    
    # TTP ile ilgili kolon var mi?
    ttp_cols = [c for c in cols if 'ttp' in c.lower() or 'hwm' in c.lower() or 'trail' in c.lower()]
    if ttp_cols:
        print("TTP/HWM kolonlari BULUNDU:", ttp_cols)
    else:
        print("TTP/HWM kolonlari YOK. (Veritabanina eklenecek)")
    conn.close()
except Exception as e:
    print("DB Hatasi:", e)

print("\n--- 2. POSITION_MANAGER.PY: trailing_state KULLANIMI ---")
try:
    lines = open(pm_path, 'r', encoding='utf-8').readlines()
    found = 0
    for i, l in enumerate(lines):
        if "trailing_state" in l:
            start = max(0, i - 2)
            end = min(len(lines), i + 5)
            print(f"\n--- Satir {i+1} Civari ---")
            for j in range(start, end):
                prefix = ">> " if j == i else "   "
                print(f"{prefix}{j+1}: {lines[j].rstrip()}")
            found += 1
            if found >= 5: break
    if found == 0:
        print("trailing_state kullanimi bulunamadi (belki farkli bir degisken adi var).")
except Exception as e:
    print("PM Hatasi:", e)
