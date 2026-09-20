import shutil
import os

DB_SRC = 'backend/database.py'
PM_SRC = 'backend/position_manager.py'

for src in [DB_SRC, PM_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_commission_fix')
    print(f"[1/3] Yedek: {src}.bak_commission_fix")

changes = 0

# ============================================================
# 1. database.py: trade_history + commission sutunu
# ============================================================
with open(DB_SRC, 'r', encoding='utf-8', newline='') as f:
    db = f.read().replace('\r\n', '\n')

old_mig = '''        "is_partial": "ALTER TABLE trade_history ADD COLUMN is_partial INTEGER DEFAULT 0",
    }'''

new_mig = '''        "is_partial": "ALTER TABLE trade_history ADD COLUMN is_partial INTEGER DEFAULT 0",
        "commission": "ALTER TABLE trade_history ADD COLUMN commission REAL DEFAULT 0",
    }'''

if 'commission' in db:
    print("[2/3] database.py: commission sutunu zaten var (atlandi)")
elif old_mig in db:
    db = db.replace(old_mig, new_mig, 1)
    changes += 1
    print("[2/3] database.py: commission sutunu eklendi")
else:
    print("[2/3] UYARI: migrations_th bulunamadi (atlandi)")

with open(DB_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(db.replace('\n', '\r\n'))

# ============================================================
# 2. position_manager.py: initial_vol guncelle + commission DB'ye yaz
# ============================================================
with open(PM_SRC, 'r', encoding='utf-8', newline='') as f:
    pm = f.read().replace('\r\n', '\n')

# 2a. _execute_partial_close: trade_history INSERT'ine commission ekle
old_ins = '''        conn = get_db_connection()
        conn.execute(
            """INSERT INTO trade_history 
               (symbol, trade_type, total_vol, entry_price, exit_price,
                pnl_amount, pnl_pct, entry_time, exit_time,
                strategy_name, dca_count, close_reason, leverage, funding_fee, is_partial)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)""",
            (symbol, trade_type, close_vol_usdt, avg_price, exit_price,
             net_pnl, pnl_pct * 100, trade["entry_time"], exit_time,
             strategy_name, dca_count, reason, leverage)
        )
        conn.commit()
        conn.close()'''

new_ins = '''        conn = get_db_connection()
        conn.execute(
            """INSERT INTO trade_history 
               (symbol, trade_type, total_vol, entry_price, exit_price,
                pnl_amount, pnl_pct, entry_time, exit_time,
                strategy_name, dca_count, close_reason, leverage, funding_fee, is_partial, commission)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)""",
            (symbol, trade_type, close_vol_usdt, avg_price, exit_price,
             net_pnl, pnl_pct * 100, trade["entry_time"], exit_time,
             strategy_name, dca_count, reason, leverage, exit_comm)
        )
        conn.commit()
        conn.close()'''

if 'is_partial, commission)' in pm:
    print("[3/3] position_manager.py: PT INSERT zaten guncel (atlandi)")
elif old_ins in pm:
    pm = pm.replace(old_ins, new_ins, 1)
    changes += 1
    print("[3/3] position_manager.py: PT INSERT commission eklendi")
else:
    print("[3/3] UYARI: PT INSERT blogu bulunamadi (atlandi)")

# 2b. _execute_partial_close: active_trades UPDATE'e initial_vol ekle
old_upd = '''        # --- active_trades guncelle ---
        new_total_vol = trade["total_vol"] - close_vol_usdt
        old_pt_volume = trade.get("pt_volume") or 0
        old_pt_pnl = trade.get("pt_pnl") or 0
        new_pt_volume = old_pt_volume + close_vol_usdt
        new_pt_pnl = old_pt_pnl + net_pnl
        
        conn = get_db_connection()
        conn.execute(
            """UPDATE active_trades 
               SET total_vol = ?, pt_done = 1, pt_volume = ?, pt_pnl = ?
               WHERE symbol = ?""",
            (new_total_vol, new_pt_volume, new_pt_pnl, symbol)
        )
        conn.commit()
        conn.close()'''

new_upd = '''        # --- active_trades guncelle ---
        # ⚡ PT sonrasi kalan kisim icin initial_vol de guncellenir.
        # Boylece trailing/TP kapanisinda giris komisyonu SADECE kalan hacim uzerinden hesaplanir.
        new_total_vol = trade["total_vol"] - close_vol_usdt
        new_initial_vol = new_total_vol
        old_pt_volume = trade.get("pt_volume") or 0
        old_pt_pnl = trade.get("pt_pnl") or 0
        new_pt_volume = old_pt_volume + close_vol_usdt
        new_pt_pnl = old_pt_pnl + net_pnl
        
        conn = get_db_connection()
        conn.execute(
            """UPDATE active_trades 
               SET total_vol = ?, initial_vol = ?, pt_done = 1, pt_volume = ?, pt_pnl = ?
               WHERE symbol = ?""",
            (new_total_vol, new_initial_vol, new_pt_volume, new_pt_pnl, symbol)
        )
        conn.commit()
        conn.close()'''

if 'new_initial_vol = new_total_vol' in pm:
    print("[3/3] position_manager.py: PT UPDATE zaten guncel (atlandi)")
elif old_upd in pm:
    pm = pm.replace(old_upd, new_upd, 1)
    changes += 1
    print("[3/3] position_manager.py: PT UPDATE initial_vol guncellendi")
else:
    print("[3/3] UYARI: PT UPDATE blogu bulunamadi (atlandi)")

# 2c. _execute_close: trade_history INSERT'ine commission ekle
old_close_ins = '''        conn.execute(
            """INSERT INTO trade_history 
               (symbol, trade_type, total_vol, entry_price, exit_price, 
                pnl_amount, pnl_pct, entry_time, exit_time,
                strategy_name, dca_count, close_reason, leverage, funding_fee)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, trade["trade_type"], trade["total_vol"], avg_price,
             exit_price, net_pnl, pnl_pct * 100, trade["entry_time"], exit_time,
             strategy_name, dca_count, reason, leverage, funding_fee)
        )'''

new_close_ins = '''        conn.execute(
            """INSERT INTO trade_history 
               (symbol, trade_type, total_vol, entry_price, exit_price, 
                pnl_amount, pnl_pct, entry_time, exit_time,
                strategy_name, dca_count, close_reason, leverage, funding_fee, commission)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, trade["trade_type"], trade["total_vol"], avg_price,
             exit_price, net_pnl, pnl_pct * 100, trade["entry_time"], exit_time,
             strategy_name, dca_count, reason, leverage, funding_fee, commission)
        )'''

if 'funding_fee, commission)' in pm:
    print("[3/3] position_manager.py: normal close INSERT zaten guncel (atlandi)")
elif old_close_ins in pm:
    pm = pm.replace(old_close_ins, new_close_ins, 1)
    changes += 1
    print("[3/3] position_manager.py: normal close INSERT commission eklendi")
else:
    print("[3/3] UYARI: normal close INSERT blogu bulunamadi (atlandi)")

with open(PM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(pm.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("NOT: 'UYARI' gordüysen, o blogu bana gonder, ozel patch yazarim.")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print("  2. Log'da '[DB] trade_history + commission' gormelisin")
print("  3. Mevcut kayitlar commission=0 gosterir (frontend fallback yapar)")
print()
print("Geri donmek icin:")
for src in [DB_SRC, PM_SRC]:
    print(f"  Copy-Item {src}.bak_commission_fix {src} -Force")