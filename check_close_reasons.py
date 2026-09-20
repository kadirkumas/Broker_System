import sqlite3

conn = sqlite3.connect('backend/bot_data.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print("BENZERSIZ close_reason DEGERLERI")
print("=" * 70)
print()

rows = cur.execute("""
    SELECT 
        close_reason,
        COUNT(*) as cnt
    FROM trade_history
    WHERE close_reason IS NOT NULL
    GROUP BY close_reason
    ORDER BY cnt DESC
""").fetchall()

if not rows:
    print("  Kayit yok.")
else:
    for r in rows:
        reason = r['close_reason'] or '(bos)'
        # Ilk 40 karakter, uzunsa ...
        display = reason if len(reason) <= 40 else reason[:37] + "..."
        print(f"  {r['cnt']:>5} x | {display}")

print()
print("=" * 70)
print("RENKLI ONIZLEME")
print("=" * 70)
print()
print("Asagidaki eşleşmelere gore gruplandirma yapacagiz:")
print("  PARTIAL TP  <- '%PARTIAL%' iceriyor")
print("  TAKE PROFIT <- '%TAKE%' iceriyor (PARTIAL haric)")
print("  STOP LOSS   <- '%STOP%' iceriyor")
print("  TRAILING    <- '%TRAILING%' iceriyor")
print("  DELISTED    <- '%DELIST%' iceriyor")
print("  TIME LIMIT  <- '%TIME%' veya '%AGE%' iceriyor")
print("  DIGER       <- hicbiri")

conn.close()
print()
print("=" * 70)