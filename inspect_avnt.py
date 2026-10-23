import sqlite3
import datetime

db_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\bot_data.db'

print("--- AVNTUSDT POZISYON DETAYI ---")
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("PRAGMA table_info(active_trades)")
    cols = [c[1] for c in cur.fetchall()]
    
    cur.execute("SELECT * FROM active_trades WHERE symbol LIKE '%AVNT%'")
    row = cur.fetchone()
    
    if row:
        t = dict(zip(cols, row))
        entry_time = t.get('entry_time', 0)
        now_ts = int(datetime.datetime.now().timestamp())
        diff_hours = (now_ts - entry_time) / 3600.0
        
        print(f"Sembol       : {t.get('symbol')}")
        print(f"Strateji     : {t.get('strategy_name')}")
        print(f"Yon          : {t.get('trade_type')}")
        print(f"Ilk Giris    : {t.get('initial_price')}")
        print(f"Ort. Fiyat   : {t.get('avg_price')}")
        print(f"DCA Sayisi   : {t.get('dca_count')}")
        print(f"Kaldirac     : {t.get('leverage')}x")
        print(f"Giris Zamani : {datetime.datetime.fromtimestamp(entry_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Gecen Sure   : {diff_hours:.2f} saat")
        
        # PT (Partial TP) ayarlari
        print(f"PT Aktif mi  : {t.get('pt_enabled')}")
        print(f"PT Yuzdesi   : %{t.get('pt_percent')}")
        print(f"PT Tamamlandi: {t.get('pt_done')}")
    else:
        print("AVNTUSDT aktif islem bulunamadi.")
    conn.close()
except Exception as e:
    print("DB okuma hatasi:", e)

print("\n--- TTP KODU: tp_pct VE trail_steps (GUNCEL) ---")
p = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'
lines = open(p, 'r', encoding='utf-8').readlines()
for i, l in enumerate(lines):
    if "tp_pct = params" in l or "_trail_steps = " in l or "profit_pct = " in l:
        print(f"[{i+1}] {l.strip()[:250]}")
