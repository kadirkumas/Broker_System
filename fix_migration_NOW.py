import sqlite3
import os

DB_PATH = 'backend/bot_data.db'

print("=" * 60)
print("ACIL MIGRATION - trade_history.initial_price")
print("=" * 60)
print()

if not os.path.exists(DB_PATH):
    print(f"[HATA] {DB_PATH} bulunamadi!")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Mevcut sutunlar
cols = [row[1] for row in cur.execute("PRAGMA table_info(trade_history)").fetchall()]
print(f"Sutun sayisi: {len(cols)}")

if 'initial_price' in cols:
    print("[OK] initial_price ZATEN VAR")
else:
    print("[*] initial_price EKLENIYOR...")
    try:
        cur.execute("ALTER TABLE trade_history ADD COLUMN initial_price REAL DEFAULT 0")
        conn.commit()
        print("[OK] Sutun EKLENDI")
        
        cur.execute("UPDATE trade_history SET initial_price = entry_price WHERE initial_price = 0 OR initial_price IS NULL")
        conn.commit()
        print(f"[OK] {cur.rowcount} kayit guncellendi")
    except Exception as e:
        print(f"[HATA] {e}")
        conn.close()
        exit(1)

# DOGRULAMA
cols2 = [row[1] for row in cur.execute("PRAGMA table_info(trade_history)").fetchall()]
has_col = 'initial_price' in cols2

print()
print(f"DOGRULAMA: initial_price = {'VAR ✅' if has_col else 'YOK ❌'}")
print(f"Toplam sutun  : {len(cols2)}")

# Ornek kayit
row = cur.execute("SELECT id, symbol, entry_price, initial_price FROM trade_history LIMIT 3").fetchall()
print()
print("Ornek kayitlar:")
for r in row:
    print(f"  ID={r[0]} {r[1]} entry={r[2]} initial={r[3]}")

conn.close()
print()
print("=" * 60)
if has_col:
    print("BASARILI ✅")
else:
    print("BASARISIZ ❌")
print("=" * 60)