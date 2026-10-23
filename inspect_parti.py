import json
import sqlite3
import os
import datetime

cfg_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\bot_config.json'
db_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\bot_data.db'

print("--- STRATEJI AYARLARI ---")
try:
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    
    # PARTIUSDT hangi stratejide? Default olarak ASAP veya Hull olabilir, tum stratejileri yazdiralim
    strats = cfg.get('strategies', {})
    for s_name, s_data in strats.items():
        if s_data.get('enabled'):
            print(f"[{s_name}] TP: %{s_data.get('takeProfit', 'YOK')}, Trailing: %{s_data.get('trailing', 'YOK')}, MaxHold: {s_data.get('maxHoldHours', 'YOK')} saat")
except Exception as e:
    print("Config okuma hatasi:", e)

print("\n--- VERITABANI: PARTIUSDT POZISYON DETAYI ---")
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Kolon isimlerini al
    cur.execute("PRAGMA table_info(active_trades)")
    cols = [c[1] for c in cur.fetchall()]
    
    cur.execute("SELECT * FROM active_trades WHERE symbol LIKE '%PARTI%'")
    row = cur.fetchone()
    
    if row:
        t = dict(zip(cols, row))
        entry_time = t.get('entry_time', 0)
        now_ts = int(datetime.datetime.now().timestamp())
        diff_hours = (now_ts - entry_time) / 3600.0
        
        print(f"Sembol       : {t.get('symbol')}")
        print(f"Giris Fiyati : {t.get('initial_price')}")
        print(f"Ort. Fiyat   : {t.get('avg_price')}")
        print(f"Toplam Hacim : {t.get('total_vol')} USDT")
        print(f"DCA Sayisi   : {t.get('dca_count')}")
        print(f"Giris Zamani : {datetime.datetime.fromtimestamp(entry_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Gecen Sure   : {diff_hours:.2f} saat")
        
        # TTP state (eger veritabaninda tutuluyorsa)
        if 'ttp_active' in t:
            print(f"TTP Aktif mi : {t.get('ttp_active')}")
            print(f"TTP HWM      : {t.get('ttp_hwm')}")
    else:
        print("PARTIUSDT aktif islem bulunamadi (Kapanmis olabilir).")
    conn.close()
except Exception as e:
    print("DB okuma hatasi:", e)
