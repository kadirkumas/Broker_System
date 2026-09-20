import sqlite3
import json

DB_PATH = 'backend/bot_data.db'
CONFIG_PATH = 'backend/bot_config.json'

print("=" * 70)
print("KISMI TP TESHIS RAPORU")
print("=" * 70)

# --- 1. Config kontrolu ---
print("\n[1] BOT CONFIG - PT AYARLARI")
print("-" * 70)
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    for strat_name in ['RSI_SCALPER', 'HULL_SRP', 'GRIDBOT']:
        s = cfg.get('strategies', {}).get(strat_name, {})
        enabled = s.get('partialTPEnabled', 'YOK')
        percent = s.get('partialTPPercent', 'YOK')
        keep_dca = s.get('partialTPKeepDCA', 'YOK')
        strat_enabled = s.get('enabled', False)
        tp = s.get('takeProfit', '?')
        print(f"  {strat_name:15} | aktif={strat_enabled} | PT={enabled} | %{percent} | KeepDCA={keep_dca} | TP={tp}%")
except Exception as e:
    print(f"  HATA: {e}")

# --- 2. Aktif pozisyonlar - PT snapshot ---
print("\n[2] AKTIF POZISYONLAR - PT SNAPSHOT")
print("-" * 70)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

try:
    rows = cur.execute("""
        SELECT symbol, strategy_name, pt_enabled, pt_percent, pt_done, 
               pt_volume, pt_pnl, pt_keep_dca, total_vol, avg_price
        FROM active_trades
        ORDER BY entry_time DESC LIMIT 20
    """).fetchall()
    
    if not rows:
        print("  Aktif pozisyon yok.")
    else:
        print(f"  Toplam {len(rows)} aktif pozisyon (son 20):\n")
        print(f"  {'Sembol':<16} {'Strateji':<14} {'PT':<4} {'%':<5} {'Done':<5} {'Vol':<10} {'PnL':<10}")
        print("  " + "-" * 66)
        for r in rows:
            pt_en = r['pt_enabled'] if r['pt_enabled'] is not None else '-'
            pt_pc = r['pt_percent'] if r['pt_percent'] is not None else '-'
            pt_dn = r['pt_done'] if r['pt_done'] is not None else '-'
            pt_vol = r['pt_volume'] if r['pt_volume'] is not None else '-'
            pt_pnl = f"{r['pt_pnl']:.4f}" if r['pt_pnl'] else '-'
            print(f"  {r['symbol']:<16} {str(r['strategy_name'] or '-'):<14} {str(pt_en):<4} {str(pt_pc):<5} {str(pt_dn):<5} {str(pt_vol):<10} {pt_pnl:<10}")
except Exception as e:
    print(f"  HATA: {e}")

# --- 3. Son kapanan islemler (partial flag'li) ---
print("\n[3] SON KAPANAN ISLEMLER")
print("-" * 70)
try:
    rows = cur.execute("""
        SELECT id, symbol, strategy_name, is_partial, close_reason, 
               pnl_pct, pnl_amount, total_vol, entry_time, exit_time
        FROM trade_history
        ORDER BY exit_time DESC LIMIT 30
    """).fetchall()
    
    if not rows:
        print("  Islem gecmisi bos.")
    else:
        print(f"  Son {len(rows)} islem:\n")
        print(f"  {'ID':<6} {'Sembol':<14} {'Strateji':<14} {'PT':<4} {'PnL%':<8} {'Sebep':<22}")
        print("  " + "-" * 78)
        for r in rows:
            is_pt = 'YES' if r['is_partial'] == 1 else '-'
            reason = (r['close_reason'] or '')[:20]
            pnl = f"{r['pnl_pct']:+.2f}" if r['pnl_pct'] is not None else '?'
            print(f"  {r['id']:<6} {r['symbol']:<14} {str(r['strategy_name'] or '-'):<14} {is_pt:<4} {pnl:<8} {reason:<22}")
except Exception as e:
    print(f"  HATA: {e}")

# --- 4. CHILLGUYUSDT ozel kontrol ---
print("\n[4] CHILLGUYUSDT OZEL KONTROL")
print("-" * 70)
try:
    # Aktif mi?
    active = cur.execute("SELECT * FROM active_trades WHERE symbol='CHILLGUYUSDT'").fetchone()
    if active:
        print(f"  AKTIF: pt_enabled={active['pt_enabled']}, pt_done={active['pt_done']}, pt_percent={active['pt_percent']}")
    else:
        print("  Aktif degil (kapandi)")
    
    # Kapanmis islemleri
    hist = cur.execute("""
        SELECT * FROM trade_history 
        WHERE symbol='CHILLGUYUSDT' 
        ORDER BY exit_time DESC LIMIT 5
    """).fetchall()
    
    print(f"\n  Son {len(hist)} kapanan islem:")
    for h in hist:
        is_pt = 'PARTIAL' if h['is_partial'] == 1 else 'NORMAL'
        print(f"    ID={h['id']} | {is_pt} | PnL={h['pnl_pct']:.2f}% | Vol={h['total_vol']} | Sebep={h['close_reason']}")
except Exception as e:
    print(f"  HATA: {e}")

# --- 5. Sema kontrolu ---
print("\n[5] TABLO SEMA KONTROLU")
print("-" * 70)
try:
    cols_at = [row[1] for row in cur.execute("PRAGMA table_info(active_trades)").fetchall()]
    pt_cols_at = [c for c in cols_at if c.startswith('pt_')]
    print(f"  active_trades pt_* sutunlari: {pt_cols_at}")
    
    cols_th = [row[1] for row in cur.execute("PRAGMA table_info(trade_history)").fetchall()]
    pt_cols_th = [c for c in cols_th if c.startswith('is_') or c.startswith('pt_')]
    print(f"  trade_history pt_*/is_* sutunlari: {pt_cols_th}")
except Exception as e:
    print(f"  HATA: {e}")

conn.close()
print("\n" + "=" * 70)