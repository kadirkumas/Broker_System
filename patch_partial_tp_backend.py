import shutil
import os

DB_SRC = 'backend/database.py'
SE_SRC = 'backend/strategy_engine.py'
OM_SRC = 'backend/order_manager.py'

for src in [DB_SRC, SE_SRC, OM_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_partial_tp')
    print(f"[1/4] Yedek: {src}.bak_partial_tp")

changes = 0

# ============================================================
# 1. database.py: active_trades + trade_history migration
# ============================================================
with open(DB_SRC, 'r', encoding='utf-8', newline='') as f:
    db = f.read().replace('\r\n', '\n')

old_mig_at = '''    migrations_at = {
        "strategy_name": "ALTER TABLE active_trades ADD COLUMN strategy_name TEXT",
        "initial_price": "ALTER TABLE active_trades ADD COLUMN initial_price REAL",
        "initial_vol": "ALTER TABLE active_trades ADD COLUMN initial_vol REAL",
        "leverage": "ALTER TABLE active_trades ADD COLUMN leverage INTEGER DEFAULT 1",
    }'''

new_mig_at = '''    migrations_at = {
        "strategy_name": "ALTER TABLE active_trades ADD COLUMN strategy_name TEXT",
        "initial_price": "ALTER TABLE active_trades ADD COLUMN initial_price REAL",
        "initial_vol": "ALTER TABLE active_trades ADD COLUMN initial_vol REAL",
        "leverage": "ALTER TABLE active_trades ADD COLUMN leverage INTEGER DEFAULT 1",
        "pt_enabled": "ALTER TABLE active_trades ADD COLUMN pt_enabled INTEGER DEFAULT 0",
        "pt_percent": "ALTER TABLE active_trades ADD COLUMN pt_percent REAL DEFAULT 50",
        "pt_done": "ALTER TABLE active_trades ADD COLUMN pt_done INTEGER DEFAULT 0",
        "pt_volume": "ALTER TABLE active_trades ADD COLUMN pt_volume REAL DEFAULT 0",
        "pt_pnl": "ALTER TABLE active_trades ADD COLUMN pt_pnl REAL DEFAULT 0",
        "pt_keep_dca": "ALTER TABLE active_trades ADD COLUMN pt_keep_dca INTEGER DEFAULT 1",
    }'''

if old_mig_at in db:
    db = db.replace(old_mig_at, new_mig_at, 1)
    changes += 1
    print("[2/4] database.py: active_trades PT sutunlari eklendi")
else:
    print("[2/4] HATA: active_trades migrations_at bulunamadi!")
    exit(1)

old_mig_th = '''    migrations_th = {
        "strategy_name": "ALTER TABLE trade_history ADD COLUMN strategy_name TEXT",
        "dca_count": "ALTER TABLE trade_history ADD COLUMN dca_count INTEGER DEFAULT 0",
        "close_reason": "ALTER TABLE trade_history ADD COLUMN close_reason TEXT",
        "leverage": "ALTER TABLE trade_history ADD COLUMN leverage INTEGER DEFAULT 1",
        "funding_fee": "ALTER TABLE trade_history ADD COLUMN funding_fee REAL DEFAULT 0",
    }'''

new_mig_th = '''    migrations_th = {
        "strategy_name": "ALTER TABLE trade_history ADD COLUMN strategy_name TEXT",
        "dca_count": "ALTER TABLE trade_history ADD COLUMN dca_count INTEGER DEFAULT 0",
        "close_reason": "ALTER TABLE trade_history ADD COLUMN close_reason TEXT",
        "leverage": "ALTER TABLE trade_history ADD COLUMN leverage INTEGER DEFAULT 1",
        "funding_fee": "ALTER TABLE trade_history ADD COLUMN funding_fee REAL DEFAULT 0",
        "is_partial": "ALTER TABLE trade_history ADD COLUMN is_partial INTEGER DEFAULT 0",
    }'''

if old_mig_th in db:
    db = db.replace(old_mig_th, new_mig_th, 1)
    changes += 1
    print("[2/4] database.py: trade_history is_partial eklendi")
else:
    print("[2/4] HATA: trade_history migrations_th bulunamadi!")
    exit(1)

with open(DB_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(db.replace('\n', '\r\n'))

# ============================================================
# 2. strategy_engine.py: DEFAULT_CONFIG + PT snapshot
# ============================================================
with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

# RSI_SCALPER
old_rsi = '''            "steps": "1.5, 3, 5",
            "takeProfit": 1.5, "trailing": 0.3, "stopLoss": 3.0
        },'''
new_rsi = '''            "steps": "1.5, 3, 5",
            "takeProfit": 1.5, "trailing": 0.3, "stopLoss": 3.0,
            "partialTPEnabled": False, "partialTPPercent": 50,
            "partialTPKeepDCA": True
        },'''
if old_rsi in se:
    se = se.replace(old_rsi, new_rsi, 1)
    changes += 1
    print("[3/4] strategy_engine.py: RSI_SCALPER PT alanlari")

# HULL_SRP
old_hull = '''            "baseOrder": 10,
            "takeProfit": 2.0, "trailing": 0.5, "stopLoss": 3.0
        },'''
new_hull = '''            "baseOrder": 10,
            "takeProfit": 2.0, "trailing": 0.5, "stopLoss": 3.0,
            "partialTPEnabled": False, "partialTPPercent": 50,
            "partialTPKeepDCA": True
        },'''
if old_hull in se:
    se = se.replace(old_hull, new_hull, 1)
    changes += 1
    print("[3/4] strategy_engine.py: HULL_SRP PT alanlari")

# GRIDBOT
old_grid = '''            "baseOrder": 10,
            "takeProfit": 1.0, "trailing": 0.2, "stopLoss": 3.0
        }'''
new_grid = '''            "baseOrder": 10,
            "takeProfit": 1.0, "trailing": 0.2, "stopLoss": 3.0,
            "partialTPEnabled": False, "partialTPPercent": 50,
            "partialTPKeepDCA": True
        }'''
if old_grid in se:
    se = se.replace(old_grid, new_grid, 1)
    changes += 1
    print("[3/4] strategy_engine.py: GRIDBOT PT alanlari")

# PT snapshot'i open_dca_position cagrisina ekle
old_call = '''                    self.order_manager.symbol = symbol
                    try:
                        await asyncio.to_thread(
                            self.order_manager.open_dca_position,
                            side=side,
                            base_amount_usdt=base_order,
                            strategy_name=strategy_name,
                            leverage=leverage,
                        )'''

new_call = '''                    self.order_manager.symbol = symbol
                    
                    # ⚡ Kismi TP snapshot (acilis anindaki config)
                    pt_enabled = 1 if strat_cfg.get("partialTPEnabled") else 0
                    pt_percent = float(strat_cfg.get("partialTPPercent", 50))
                    pt_keep_dca = 1 if strat_cfg.get("partialTPKeepDCA", True) else 0
                    
                    if pt_enabled:
                        print(f"[PARTIAL-TP] {symbol} PT aktif: %{pt_percent:.0f} | KeepDCA={pt_keep_dca}")
                    
                    try:
                        await asyncio.to_thread(
                            self.order_manager.open_dca_position,
                            side=side,
                            base_amount_usdt=base_order,
                            strategy_name=strategy_name,
                            leverage=leverage,
                            pt_enabled=pt_enabled,
                            pt_percent=pt_percent,
                            pt_keep_dca=pt_keep_dca,
                        )'''

if old_call in se:
    se = se.replace(old_call, new_call, 1)
    changes += 1
    print("[3/4] strategy_engine.py: PT snapshot open_dca_position'a eklendi")
else:
    print("[3/4] UYARI: open_dca_position cagrisi bulunamadi (atlandi)")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

# ============================================================
# 3. order_manager.py: PT parametreleri + partial_close_position
# ============================================================
with open(OM_SRC, 'r', encoding='utf-8', newline='') as f:
    om = f.read().replace('\r\n', '\n')

# 3a. open_dca_position imzasi
old_sig = '''    def open_dca_position(self, side: str, base_amount_usdt: float = 10.0, strategy_name: str = None,
                          leverage: int = 1, dca_levels: int = 3, step_pct: float = 1.0, tp_pct: float = 1.5, sl_pct: float = 3.0):'''

new_sig = '''    def open_dca_position(self, side: str, base_amount_usdt: float = 10.0, strategy_name: str = None,
                          leverage: int = 1, dca_levels: int = 3, step_pct: float = 1.0, tp_pct: float = 1.5, sl_pct: float = 3.0,
                          pt_enabled: int = 0, pt_percent: float = 50, pt_keep_dca: int = 1):'''

if old_sig in om:
    om = om.replace(old_sig, new_sig, 1)
    changes += 1
    print("[4/4] order_manager.py: open_dca_position imzasi guncellendi")

# 3b. _save_to_db cagrilari
old_save1 = '''            self._save_to_db(self.symbol, side, base_amount_usdt, current_price, 0, strat, current_price, base_amount_usdt, leverage)'''
new_save1 = '''            self._save_to_db(self.symbol, side, base_amount_usdt, current_price, 0, strat, current_price, base_amount_usdt, leverage, pt_enabled, pt_percent, pt_keep_dca)'''
if old_save1 in om:
    om = om.replace(old_save1, new_save1, 1)
    changes += 1

old_save2 = '''            self._save_to_db(self.symbol, side, base_amount_usdt, entry_price, 0, strat, entry_price, base_amount_usdt, leverage)'''
new_save2 = '''            self._save_to_db(self.symbol, side, base_amount_usdt, entry_price, 0, strat, entry_price, base_amount_usdt, leverage, pt_enabled, pt_percent, pt_keep_dca)'''
if old_save2 in om:
    om = om.replace(old_save2, new_save2, 1)
    changes += 1

# 3c. _save_to_db metodu
old_save_def = '''    def _save_to_db(self, symbol, side, total_vol, avg_price, dca_count, strategy_name, initial_price, initial_vol, leverage=1):
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO active_trades 
               (symbol, trade_type, total_vol, avg_price, dca_count, entry_time, strategy_name, initial_price, initial_vol, leverage) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, side, total_vol, avg_price, dca_count, int(time.time()),
             strategy_name, initial_price, initial_vol, leverage)
        )
        conn.commit()
        conn.close()'''

new_save_def = '''    def _save_to_db(self, symbol, side, total_vol, avg_price, dca_count, strategy_name, initial_price, initial_vol, leverage=1,
                    pt_enabled=0, pt_percent=50, pt_keep_dca=1):
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO active_trades 
               (symbol, trade_type, total_vol, avg_price, dca_count, entry_time, strategy_name, initial_price, initial_vol, leverage,
                pt_enabled, pt_percent, pt_done, pt_volume, pt_pnl, pt_keep_dca) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?)""",
            (symbol, side, total_vol, avg_price, dca_count, int(time.time()),
             strategy_name, initial_price, initial_vol, leverage,
             pt_enabled, pt_percent, pt_keep_dca)
        )
        conn.commit()
        conn.close()'''

if old_save_def in om:
    om = om.replace(old_save_def, new_save_def, 1)
    changes += 1
    print("[4/4] order_manager.py: _save_to_db guncellendi")

# 3d. partial_close_position metodu
anchor = '''    def _close_in_db(self, symbol: str):'''

new_method = '''    def partial_close_position(self, symbol: str, close_usdt: float, current_price: float):
        """
        Pozisyonun BELIRLI bir USDT hacmini kapatir.
        Test modunda sadece log yazar (DB position_manager tarafindan guncellenir).
        Gercek modda Binance'e reduceOnly MARKET emri gonderir.
        """
        if self.test_mode:
            print(f"[TEST PARTIAL] {symbol} {close_usdt:.2f} USDT kismi kapatma (fiyat: {current_price})")
            return {"status": "success", "mode": "TEST", "symbol": symbol, "closed_usdt": close_usdt}
        
        try:
            _, qty_prec = self.get_symbol_precision(symbol)
            if current_price <= 0:
                return {"status": "error", "message": "Gecersiz fiyat"}
            
            close_qty = round(close_usdt / current_price, qty_prec)
            if close_qty <= 0:
                return {"status": "error", "message": "Hesaplanan miktar 0"}
            
            positions = self.client.futures_position_information(symbol=symbol)
            pos = next((p for p in positions if p['symbol'] == symbol and float(p['positionAmt']) != 0), None)
            if not pos:
                return {"status": "error", "message": "Pozisyon bulunamadi"}
            
            amt = float(pos['positionAmt'])
            if abs(close_qty) >= abs(amt):
                close_qty = abs(amt)
            
            side = "SELL" if amt > 0 else "BUY"
            result = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=abs(close_qty),
                reduceOnly=True
            )
            
            print(f"[PARTIAL] {symbol} kapatildi: {close_qty} adet ({close_usdt:.2f} USDT)")
            return {"status": "success", "mode": "REAL", "symbol": symbol,
                    "closed_qty": close_qty, "closed_usdt": close_usdt, "order": result}
        
        except Exception as e:
            print(f"[PARTIAL] HATA {symbol}: {e}")
            return {"status": "error", "message": str(e)}
    
    def _close_in_db(self, symbol: str):'''

if anchor in om and 'partial_close_position' not in om:
    om = om.replace(anchor, new_method, 1)
    changes += 1
    print("[4/4] order_manager.py: partial_close_position metodu eklendi")

with open(OM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(om.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("Geri donmek icin:")
for src in [DB_SRC, SE_SRC, OM_SRC]:
    print(f"  Copy-Item {src}.bak_partial_tp {src} -Force")