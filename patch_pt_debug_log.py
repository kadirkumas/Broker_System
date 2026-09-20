import shutil
import os

PM_SRC = 'backend/position_manager.py'

if not os.path.exists(PM_SRC):
    print(f"[HATA] {PM_SRC} bulunamadi")
    exit(1)

shutil.copy2(PM_SRC, PM_SRC + '.bak_pt_debug')
print(f"[1/3] Yedek: {PM_SRC}.bak_pt_debug")

with open(PM_SRC, 'r', encoding='utf-8', newline='') as f:
    pm = f.read().replace('\r\n', '\n')

# 1. PT tetikleme yerine DEBUG log ekle
old = """            if pt_enabled and not pt_done_flag and not state["active"] and profit_pct >= tp_pct:
                pt_close_vol = pos["total_vol"] * (pt_percent_val / 100.0)
                # ⚡ Test modunda min notional uygulanmaz (gercek emir yok)
                _is_test = bool(getattr(self.order_manager, 'test_mode', False)) if self.order_manager else False
                MIN_ORDER_USDT = 0.5 if _is_test else 5.0"""

new = """            if pt_enabled and not pt_done_flag and not state["active"] and profit_pct >= tp_pct:
                pt_close_vol = pos["total_vol"] * (pt_percent_val / 100.0)
                # ⚡ DEBUG: Tum girdi degerlerini logla
                print(f"[PT-DEBUG] {symbol} | pos_total_vol={pos['total_vol']} | "
                      f"pt_percent={pt_percent_val} | pt_close_vol={pt_close_vol} | "
                      f"pt_enabled={pt_enabled} | pt_done={pt_done_flag} | "
                      f"profit_pct={profit_pct*100:.2f}%")
                # ⚡ Test modunda min notional uygulanmaz (gercek emir yok)
                _is_test = bool(getattr(self.order_manager, 'test_mode', False)) if self.order_manager else False
                MIN_ORDER_USDT = 0.5 if _is_test else 5.0"""

if '[PT-DEBUG]' in pm:
    print("[2/3] position_manager.py: PT DEBUG zaten var (atlandi)")
elif old in pm:
    pm = pm.replace(old, new, 1)
    print("[2/3] position_manager.py: PT tetikleme DEBUG eklendi")
else:
    print("[2/3] UYARI: PT tetikleme blogu bulunamadi (atlandi)")

# 2. _execute_partial_close basina debug log
old2 = """        conn = get_db_connection()
        row = conn.execute("SELECT * FROM active_trades WHERE symbol = ?", (symbol,)).fetchone()
        conn.close()
        if not row:
            print(f"[PARTIAL-TP] {symbol} aktif pozisyon yok")
            return None
        
        trade = dict(row)
        avg_price = trade["avg_price"]
        trade_type = trade["trade_type"]"""

new2 = """        conn = get_db_connection()
        row = conn.execute("SELECT * FROM active_trades WHERE symbol = ?", (symbol,)).fetchone()
        conn.close()
        if not row:
            print(f"[PARTIAL-TP] {symbol} aktif pozisyon yok")
            return None
        
        trade = dict(row)
        # ⚡ DEBUG: DB'den okunan trade ile gelen parametreleri karsilastir
        print(f"[PT-DEBUG-EXEC] {symbol} | close_vol_usdt={close_vol_usdt} | "
              f"trade.total_vol={trade['total_vol']} | trade.initial_vol={trade.get('initial_vol')} | "
              f"trade.avg_price={trade['avg_price']} | pt_percent={pt_percent}")
        avg_price = trade["avg_price"]
        trade_type = trade["trade_type"]"""

if '[PT-DEBUG-EXEC]' in pm:
    print("[3/3] position_manager.py: EXEC DEBUG zaten var (atlandi)")
elif old2 in pm:
    pm = pm.replace(old2, new2, 1)
    print("[3/3] position_manager.py: EXEC DEBUG eklendi")
else:
    print("[3/3] UYARI: _execute_partial_close baslangici bulunamadi (atlandi)")

with open(PM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(pm.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI - DEBUG LOG AKTIF")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print("  2. Yeni bir PT tetiklenmesini bekle")
print("  3. Log'lari topla ve bana yolla:")
print("     [PT-DEBUG] ...")
print("     [PT-DEBUG-EXEC] ...")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {PM_SRC}.bak_pt_debug {PM_SRC} -Force")