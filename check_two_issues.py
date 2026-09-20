import sqlite3
import json
import urllib.request

DB = 'backend/bot_data.db'

print("=" * 70)
print("BILDIRIM FIYAT + MARKER OFFSET - TESHIS")
print("=" * 70)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ============ SORUN 1: BILDIRIM YANLIS FIYAT ============
print("\n[SORUN 1] COTIUSDT trade_history (DB gercek)")
print("-" * 70)
for r in cur.execute("""
    SELECT id, is_partial, entry_price, exit_price, entry_time, exit_time, close_reason
    FROM trade_history WHERE symbol='COTIUSDT' ORDER BY exit_time DESC LIMIT 5
""").fetchall():
    print(f"  ID={r['id']} | PT={r['is_partial']} | entry={r['entry_price']} | exit={r['exit_price']} | reason={r['close_reason']}")

print("\n[SORUN 1] COTIUSDT signals tablosu (sinyal fiyatlari)")
print("-" * 70)
for r in cur.execute("""
    SELECT signal_id, price, created_at FROM signals WHERE symbol='COTIUSDT' ORDER BY created_at DESC LIMIT 5
""").fetchall():
    print(f"  {r['signal_id']} | price={r['price']} | created={r['created_at']}")

# Backend endpoint
print("\n[SORUN 1] BACKEND - /api/engine/recent-signals (COTIUSDT close)")
print("-" * 70)
try:
    url = "http://127.0.0.1:8000/api/engine/recent-signals?limit=200"
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    
    count = 0
    for evt in data:
        if evt.get('symbol') == 'COTIUSDT':
            count += 1
            print(f"  type={evt.get('event_type')} | id={evt.get('id')} | exit_price={evt.get('exit_price')} | entry={evt.get('entry_price')} | is_partial={evt.get('is_partial')}")
    if count == 0:
        print("  COTIUSDT event bulunamadi")
except Exception as e:
    print(f"  HATA: {e}")

# ============ SORUN 2: MARKER OFFSET ============
print("\n[SORUN 2] Chart interval ve entry_time ornekleri")
print("-" * 70)
# En son kapanan FLOCKUSDT islemi
for r in cur.execute("""
    SELECT id, symbol, entry_time, exit_time, is_partial
    FROM trade_history WHERE symbol='FLOCKUSDT' ORDER BY exit_time DESC LIMIT 3
""").fetchall():
    import time
    et = time.strftime('%H:%M:%S', time.localtime(r['entry_time']))
    xt = time.strftime('%H:%M:%S', time.localtime(r['exit_time']))
    print(f"  ID={r['id']} | entry={et} | exit={xt} | entry_unix={r['entry_time']} | exit_unix={r['exit_time']}")

# Aktif chart interval'ini goster
print("\n[SORUN 2] Su andaki chart interval")
print("-" * 70)
print("  (Kullanicidan: '5d' = 5 dakikalik mum)")
print("  Mum basina saniye = 300")

print("\n" + "=" * 70)
print("SONUC: Ciktiyi kopyala, asistan'a gonder")
print("=" * 70)

conn.close()