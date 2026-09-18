import sqlite3

DB_PATH = 'backend/bot_data.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=" * 60)
print("AKTIF_TRADES TABLOSU - DURUM")
print("=" * 60)

# Index kontrolü
print("\n[INDEX'LER]")
cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='active_trades'")
indexes = cur.fetchall()
if indexes:
    for r in indexes:
        print(f"  - {r[0]}")
else:
    print("  (hiç index yok!)")

# Duplicate kontrolü
print("\n[DUPLICATE KONTROLÜ]")
cur.execute("""
    SELECT symbol, COUNT(*) as c 
    FROM active_trades 
    GROUP BY symbol 
    HAVING c > 1
""")
dups = cur.fetchall()
if dups:
    print("  !! DUPLICATE VAR !!")
    for r in dups:
        print(f"  {r[0]}: {r[1]} kayıt")
else:
    print("  Temiz (her sembol tek)")

# BRUSDT kontrolü
print("\n[BRUSDT KAYIT]")
cur.execute("SELECT COUNT(*) FROM active_trades WHERE symbol='BRUSDT'")
print(f"  Kayıt sayısı: {cur.fetchone()[0]}")

# Toplam kayıt
print("\n[GENEL]")
cur.execute("SELECT COUNT(*) FROM active_trades")
print(f"  Toplam aktif pozisyon: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM trade_history")
print(f"  Toplam geçmiş işlem: {cur.fetchone()[0]}")

conn.close()
print("\n" + "=" * 60)