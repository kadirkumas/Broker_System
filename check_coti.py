import sqlite3

DB_PATH = 'backend/bot_data.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print("COTIUSDT GERCEK DEGERLER (DB)")
print("=" * 70)
print()

# Son COTIUSDT islemleri
rows = cur.execute("""
    SELECT id, symbol, trade_type, total_vol, entry_price, exit_price,
           pnl_amount, pnl_pct, is_partial, close_reason, commission
    FROM trade_history 
    WHERE symbol = 'COTIUSDT' 
    ORDER BY exit_time DESC LIMIT 5
""").fetchall()

if not rows:
    print("  COTIUSDT islemi bulunamadi.")
else:
    for r in rows:
        is_p = "PARTIAL" if r['is_partial'] == 1 else "NORMAL"
        pnl_hesap = ((r['exit_price'] - r['entry_price']) / r['entry_price'] * 100) if r['trade_type'] == 'BUY' else ((r['entry_price'] - r['exit_price']) / r['entry_price'] * 100)
        print(f"  ID={r['id']} | {is_p} | {r['trade_type']}")
        print(f"    Hacim:       {r['total_vol']} USDT")
        print(f"    Giris:       {r['entry_price']}")
        print(f"    Cikis:       {r['exit_price']}")
        print(f"    DB pnl_pct:  {r['pnl_pct']:.4f}%")
        print(f"    Manuel:      {pnl_hesap:.4f}%")
        print(f"    Net PnL:     {r['pnl_amount']:.4f} USDT")
        print(f"    Sebep:       {r['close_reason']}")
        print()

# Kolon kontrolu
print("[KOLON KONTROLU]")
cols = [row[1] for row in cur.execute("PRAGMA table_info(trade_history)").fetchall()]
print(f"  trade_history sutunlari: {cols}")
print(f"  'commission' var mi?     {'EVET' if 'commission' in cols else 'HAYIR'}")

conn.close()
print()
print("=" * 70)