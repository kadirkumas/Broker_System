import sqlite3

DB = 'backend/bot_data.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print("OPUSDT - KONTROL")
print("=" * 70)
print()

# 1. trade_history - OPUSDT son kayitlar
print("[1] trade_history (son OPUSDT islemleri)")
print("-" * 70)
for r in cur.execute("""
    SELECT id, is_partial, total_vol, entry_price, exit_price, 
           pnl_amount, pnl_pct, commission, close_reason
    FROM trade_history WHERE symbol='OPUSDT' 
    ORDER BY exit_time DESC LIMIT 5
""").fetchall():
    print(f"  ID={r['id']} | PT={r['is_partial']} | Vol={r['total_vol']} USDT | "
          f"PnL={r['pnl_amount']:+.4f} USDT | Kom={r['commission']} | {r['close_reason']}")
print()

# 2. active_trades - OPUSDT (aktif mi?)
print("[2] active_trades - OPUSDT")
print("-" * 70)
r = cur.execute("""
    SELECT total_vol, initial_vol, avg_price, pt_done, pt_volume, pt_pnl, entry_is_maker
    FROM active_trades WHERE symbol='OPUSDT'
""").fetchone()

if r:
    print(f"  total_vol      = {r['total_vol']}    ← 5.00 bekleniyor")
    print(f"  initial_vol    = {r['initial_vol']}    ← 5.00 bekleniyor (PT sonrasi)")
    print(f"  avg_price      = {r['avg_price']}")
    print(f"  pt_done        = {r['pt_done']}    ← 1 bekleniyor")
    print(f"  pt_volume      = {r['pt_volume']}    ← 5.00 bekleniyor")
    print(f"  pt_pnl         = {r['pt_pnl']}    ← 0.1032 bekleniyor")
    print(f"  entry_is_maker = {r['entry_is_maker']}    ← 1 bekleniyor (LIMIT)")
else:
    print("  Aktif OPUSDT yok (kapanmis)")

conn.close()
print()
print("=" * 70)