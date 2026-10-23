import sqlite3
import os

db_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\bot_data.db'
pm_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'

print("=== 1. VERITABANI: TUM KOLONLAR (GUNCEL) ===")
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(active_trades)")
    cols = cur.fetchall()
    for c in cols:
        print(f"  {c[0]}. {c[1]} ({c[2]})")
    
    # TTP arama (esnek)
    col_names = [c[1].lower() for c in cols]
    ttp_like = [c for c in col_names if 'ttp' in c or 'trail' in c or 'hwm' in c or 'peak' in c or 'high' in c or 'low' in c]
    print(f"\n  -> TTP/HWM benzeri kolonlar: {ttp_like if ttp_like else 'YOK'}")
    conn.close()
except Exception as e:
    print("DB Hatasi:", e)

print("\n=== 2. POSITION_MANAGER.PY: TTP STATE KAYIT/OKUMA NOKTALARI ===")
try:
    lines = open(pm_path, 'r', encoding='utf-8').readlines()
    found = 0
    for i, l in enumerate(lines):
        # TTP state'inin kaydedildigi veya okundugu her yer
        if ('trailing_state' in l or 'ttp_active' in l or 'ttp_hwm' in l or 'hwm' in l) and ('=' in l or '.get(' in l or 'update' in l or 'save' in l):
            if found < 12:
                print(f"[{i+1}] {l.strip()[:220]}")
                found += 1
    if found == 0:
        print("Hicbir TTP kayit/okuma noktasi bulunamadi.")
except Exception as e:
    print("PM Hatasi:", e)

print("\n=== 3. ACTIVE_TRADES ORNEK KAYIT (PARTIUSDT) ===")
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM active_trades WHERE symbol LIKE '%PARTI%' LIMIT 1")
    row = cur.fetchone()
    if row:
        cur.execute("PRAGMA table_info(active_trades)")
        cols = [c[1] for c in cur.fetchall()]
        for col, val in zip(cols, row):
            if val is not None and val != '':
                print(f"  {col}: {val}")
    else:
        print("PARTIUSDT kaydi bulunamadi.")
    conn.close()
except Exception as e:
    print("DB Hatasi:", e)
