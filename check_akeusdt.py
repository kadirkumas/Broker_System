import sqlite3

DB_PATH = 'backend/bot_data.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print("AKEUSDT DETAYLI DB KONTROLU")
print("=" * 70)
print()

# trade_history'deki son AKEUSDT islemleri
print("[1] trade_history - Son AKEUSDT kayitlari")
print("-" * 70)
rows = cur.execute("""
    SELECT id, is_partial, total_vol, entry_price, exit_price,
           pnl_amount, pnl_pct, commission, close_reason
    FROM trade_history 
    WHERE symbol = 'AKEUSDT' 
    ORDER BY exit_time DESC LIMIT 5
""").fetchall()

for r in rows:
    print(f"  ID={r['id']} | PT={r['is_partial']} | Vol={r['total_vol']} | "
          f"Entry={r['entry_price']} | Exit={r['exit_price']}")
    print(f"    PnL%={r['pnl_pct']:.4f} | PnL={r['pnl_amount']:.4f} | "
          f"Komisyon={r['commission']} | Sebep={r['close_reason']}")
    print()

# Aktif AKEUSDT pozisyonu (varsa)
print("[2] active_trades - AKEUSDT (varsa)")
print("-" * 70)
active = cur.execute("""
    SELECT symbol, total_vol, initial_vol, avg_price, 
           pt_enabled, pt_percent, pt_done, pt_volume, pt_pnl,
           dca_count, entry_is_maker
    FROM active_trades WHERE symbol='AKEUSDT'
""").fetchone()

if active:
    print(f"  total_vol      = {active['total_vol']}")
    print(f"  initial_vol    = {active['initial_vol']}")
    print(f"  avg_price      = {active['avg_price']}")
    print(f"  dca_count      = {active['dca_count']}")
    print(f"  pt_enabled     = {active['pt_enabled']}")
    print(f"  pt_percent     = {active['pt_percent']}")
    print(f"  pt_done        = {active['pt_done']}")
    print(f"  pt_volume      = {active['pt_volume']}")
    print(f"  pt_pnl         = {active['pt_pnl']}")
    print(f"  entry_is_maker = {active['entry_is_maker']}")
else:
    print("  Aktif AKEUSDT yok (kapandi)")

# Sema kontrolu
print()
print("[3] trade_history sutunlari")
print("-" * 70)
cols = [r[1] for r in cur.execute("PRAGMA table_info(trade_history)").fetchall()]
print(f"  {cols}")

conn.close()
print()
print("=" * 70)