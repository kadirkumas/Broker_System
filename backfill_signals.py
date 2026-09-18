import sqlite3

DB_PATH = 'backend/bot_data.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Aktif pozisyonları çek
rows = conn.execute('SELECT * FROM active_trades').fetchall()
print(f"Aktif pozisyon sayısı: {len(rows)}")

count = 0
for r in rows:
    sid = f"BACKFILL_{r['symbol']}_{r['entry_time']}"
    
    # Zaten var mı?
    exists = conn.execute('SELECT 1 FROM signals WHERE signal_id = ?', (sid,)).fetchone()
    if exists:
        continue
    
    sig_type = 'LONG' if r['trade_type'] == 'BUY' else 'SHORT'
    price = r['avg_price']
    init_vol = r['initial_vol'] or r['total_vol']
    qty = round(init_vol / price, 6) if price > 0 else 0
    strat = r['strategy_name'] or 'UNKNOWN'
    
    conn.execute(
        '''INSERT INTO signals 
           (signal_id, symbol, strategy_name, signal, price, qty, total_usdt, 
            candle_time, created_at, opened_position) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''',
        (sid, r['symbol'], strat, sig_type, price, qty, init_vol,
         r['entry_time'], r['entry_time'] * 1000)
    )
    count += 1

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
conn.close()

print(f"Eklendi: {count} sinyal")
print(f"Toplam signals tablosu: {total} kayit")