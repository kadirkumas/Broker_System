import sqlite3

DB_PATH = 'backend/bot_data.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print("KISMI TP ATLANDI MI? (pt_done=1 ama pt_volume=0)")
print("=" * 70)
print()

# Aktif pozisyonlarda pt_done=1 ama pt_volume=0 olanlar (atlanmis demek)
rows = cur.execute("""
    SELECT symbol, strategy_name, total_vol, pt_enabled, pt_percent, pt_done, pt_volume
    FROM active_trades
    WHERE pt_enabled = 1
    ORDER BY entry_time DESC
""").fetchall()

if not rows:
    print("  PT aktif pozisyon yok.")
else:
    print(f"  {'Sembol':<16} {'Vol':<8} {'%50':<6} {'pt_done':<8} {'pt_volume':<10} {'DURUM'}")
    print("  " + "-" * 66)
    for r in rows:
        vol = r['total_vol']
        pt_50 = vol * 0.5
        done = r['pt_done'] or 0
        pvol = r['pt_volume'] or 0
        if done == 1 and pvol == 0:
            durum = "❌ ATLANDI (min notional)"
        elif done == 1 and pvol > 0:
            durum = "✅ PT YAPILDI"
        else:
            durum = "⏳ Bekliyor"
        print(f"  {r['symbol']:<16} {vol:<8.2f} {pt_50:<6.2f} {done:<8} {pvol:<10.2f} {durum}")

conn.close()
print()
print("=" * 70)