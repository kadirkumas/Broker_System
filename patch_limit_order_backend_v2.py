import shutil
import os

OM_SRC = 'backend/order_manager.py'
SE_SRC = 'backend/strategy_engine.py'
PM_SRC = 'backend/position_manager.py'

# database.py zaten islendi, backup'a gerek yok
for src in [OM_SRC, SE_SRC, PM_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_limit_order_v2')
    print(f"[1/4] Yedek: {src}.bak_limit_order_v2")

changes = 0

# ============================================================
# 1. order_manager.py
# ============================================================
with open(OM_SRC, 'r', encoding='utf-8', newline='') as f:
    om = f.read().replace('\r\n', '\n')

# 1a. Imza
old_sig = '''    def open_dca_position(self, side: str, base_amount_usdt: float = 10.0, strategy_name: str = None,
                          leverage: int = 1, dca_levels: int = 3, step_pct: float = 1.0, tp_pct: float = 1.5, sl_pct: float = 3.0,
                          pt_enabled: int = 0, pt_percent: float = 50, pt_keep_dca: int = 1):'''

new_sig = '''    def open_dca_position(self, side: str, base_amount_usdt: float = 10.0, strategy_name: str = None,
                          leverage: int = 1, dca_levels: int = 3, step_pct: float = 1.0, tp_pct: float = 1.5, sl_pct: float = 3.0,
                          pt_enabled: int = 0, pt_percent: float = 50, pt_keep_dca: int = 1,
                          use_limit_order: bool = True, limit_timeout_sec: int = 3, fallback_market: bool = True):'''

if old_sig in om:
    om = om.replace(old_sig, new_sig, 1)
    changes += 1
    print("[2/4] order_manager.py: imza guncellendi")
else:
    print("[2/4] HATA: imza bulunamadi!")
    exit(1)

# 1b. TEST MODU blogu (TEK SATIR _save_to_db cagrisi ile)
old_test = '''        if self.test_mode:
            print(f"[TEST MODU] {self.symbol} [{strat}] {side} | Fiyat: {current_price} USDT | Adet: {qty} | Kaldıraç: {leverage}x | Marjin: {margin:.4f} | Toplam: {base_amount_usdt:.2f} USDT")
            self._save_to_db(self.symbol, side, base_amount_usdt, current_price, 0, strat, current_price, base_amount_usdt, leverage, pt_enabled, pt_percent, pt_keep_dca)
            return {
                "status": "success",
                "mode": "TEST",
                "symbol": self.symbol,
                "strategy": strat,
                "side": side,
                "entry_price": current_price,
                "quantity": base_amount_usdt,
                "leverage": leverage,
                "margin": round(margin, 4)
            }'''

new_test = '''        if self.test_mode:
            # ⚡ LIMIT + Fallback simulasyonu
            if use_limit_order:
                success, entry_price, is_maker, msg = self._place_entry_order_with_fallback(
                    self.symbol, side, qty, price_prec,
                    timeout_sec=limit_timeout_sec, fallback=fallback_market
                )
                if not success:
                    print(f"[!] Test LIMIT basarisiz: {msg}")
                    return {"status": "error", "message": msg}
                entry_is_maker = 1 if is_maker else 0
                mode_label = "MAKER" if is_maker else "TAKER"
            else:
                entry_price = current_price
                entry_is_maker = 0
                mode_label = "MARKET"
                print(f"[TEST MODU] {self.symbol} [{strat}] {side} MARKET | Fiyat: {entry_price} | Adet: {qty} | Kaldıraç: {leverage}x | Marjin: {margin:.4f} | Toplam: {base_amount_usdt:.2f} USDT")

            self._save_to_db(
                self.symbol, side, base_amount_usdt, entry_price, 0, strat,
                current_price, base_amount_usdt, leverage,
                pt_enabled, pt_percent, pt_keep_dca, entry_is_maker
            )
            return {
                "status": "success",
                "mode": "TEST",
                "symbol": self.symbol,
                "strategy": strat,
                "side": side,
                "entry_price": entry_price,
                "quantity": base_amount_usdt,
                "leverage": leverage,
                "margin": round(margin, 4),
                "order_type": mode_label
            }'''

if old_test in om:
    om = om.replace(old_test, new_test, 1)
    changes += 1
    print("[2/4] order_manager.py: TEST MODU bloku LIMIT simule ediyor")
else:
    print("[2/4] HATA: TEST MODU bloku bulunamadi!")
    print("    order_manager.py'deki mevcut test_mode bloku:")
    idx = om.find('if self.test_mode:')
    if idx > 0:
        print(om[idx:idx+700])
    exit(1)

# 1c. GERCEK EMIR blogu
old_real = '''        # --- GERÇEK EMİR DÖNGÜSÜ (mainnet) ---
        try:
            # Kaldıraç ayarla
            if leverage > 1:
                try:
                    self.client.futures_change_leverage(symbol=self.symbol, leverage=leverage)
                    print(f"[LEV] {self.symbol} Kaldıraç {leverage}x olarak ayarlandı")
                except Exception as le:
                    print(f"[!] Leverage ayarlanamadı {self.symbol}: {le}")

            self.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                type="MARKET",
                quantity=qty
            )
            entry_price = current_price

            tp_side = "SELL" if side == "BUY" else "BUY"'''

new_real = '''        # --- GERÇEK EMİR DÖNGÜSÜ (mainnet) ---
        try:
            # Kaldıraç ayarla
            if leverage > 1:
                try:
                    self.client.futures_change_leverage(symbol=self.symbol, leverage=leverage)
                    print(f"[LEV] {self.symbol} Kaldıraç {leverage}x olarak ayarlandı")
                except Exception as le:
                    print(f"[!] Leverage ayarlanamadı {self.symbol}: {le}")

            # ⚡ LIMIT + Fallback girisi
            if use_limit_order:
                success, entry_price, is_maker, msg = self._place_entry_order_with_fallback(
                    self.symbol, side, qty, price_prec,
                    timeout_sec=limit_timeout_sec, fallback=fallback_market
                )
                if not success:
                    return {"status": "error", "message": msg}
                entry_is_maker = 1 if is_maker else 0
            else:
                order = self.client.futures_create_order(
                    symbol=self.symbol,
                    side=side,
                    type="MARKET",
                    quantity=qty
                )
                entry_price = float(order.get("avgPrice") or current_price)
                entry_is_maker = 0

            tp_side = "SELL" if side == "BUY" else "BUY"'''

if old_real in om:
    om = om.replace(old_real, new_real, 1)
    changes += 1
    print("[2/4] order_manager.py: GERCEK EMIR blogu LIMIT")
else:
    print("[2/4] UYARI: GERCEK EMIR blogu bulunamadi (atlandi)")

# 1d. Gercek _save_to_db cagrisi
old_save_real = '''            self._save_to_db(self.symbol, side, base_amount_usdt, entry_price, 0, strat, entry_price, base_amount_usdt, leverage, pt_enabled, pt_percent, pt_keep_dca)'''
new_save_real = '''            self._save_to_db(
                self.symbol, side, base_amount_usdt, entry_price, 0, strat,
                entry_price, base_amount_usdt, leverage,
                pt_enabled, pt_percent, pt_keep_dca, entry_is_maker
            )'''

if old_save_real in om:
    om = om.replace(old_save_real, new_save_real, 1)
    changes += 1
    print("[2/4] order_manager.py: gercek _save_to_db cagrisi")
else:
    print("[2/4] UYARI: gercek _save_to_db cagrisi bulunamadi (atlandi)")

# 1e. _save_to_db metodu
old_save_def = '''    def _save_to_db(self, symbol, side, total_vol, avg_price, dca_count, strategy_name, initial_price, initial_vol, leverage=1,
                    pt_enabled=0, pt_percent=50, pt_keep_dca=1):'''

new_save_def = '''    def _save_to_db(self, symbol, side, total_vol, avg_price, dca_count, strategy_name, initial_price, initial_vol, leverage=1,
                    pt_enabled=0, pt_percent=50, pt_keep_dca=1, entry_is_maker=0):'''

if old_save_def in om:
    om = om.replace(old_save_def, new_save_def, 1)
    changes += 1
    print("[2/4] order_manager.py: _save_to_db imzasi")
else:
    print("[2/4] UYARI: _save_to_db imzasi bulunamadi (atlandi)")

# 1f. INSERT SQL
old_sql = '''            """INSERT INTO active_trades 
               (symbol, trade_type, total_vol, avg_price, dca_count, entry_time, strategy_name, initial_price, initial_vol, leverage,
                pt_enabled, pt_percent, pt_done, pt_volume, pt_pnl, pt_keep_dca) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?)""",
            (symbol, side, total_vol, avg_price, dca_count, int(time.time()),
             strategy_name, initial_price, initial_vol, leverage,
             pt_enabled, pt_percent, pt_keep_dca)'''

new_sql = '''            """INSERT INTO active_trades 
               (symbol, trade_type, total_vol, avg_price, dca_count, entry_time, strategy_name, initial_price, initial_vol, leverage,
                pt_enabled, pt_percent, pt_done, pt_volume, pt_pnl, pt_keep_dca, entry_is_maker) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?)""",
            (symbol, side, total_vol, avg_price, dca_count, int(time.time()),
             strategy_name, initial_price, initial_vol, leverage,
             pt_enabled, pt_percent, pt_keep_dca, entry_is_maker)'''

if old_sql in om:
    om = om.replace(old_sql, new_sql, 1)
    changes += 1
    print("[2/4] order_manager.py: INSERT SQL guncellendi")
else:
    print("[2/4] UYARI: INSERT SQL bulunamadi (atlandi)")

# 1g. Yeni method: _place_entry_order_with_fallback
anchor = '''    def _close_in_db(self, symbol: str):'''

new_method = '''    def _place_entry_order_with_fallback(self, symbol, side, qty, price_prec, timeout_sec=3, fallback=True):
        """
        LIMIT emri gonderir, timeout'ta MARKET fallback yapar.
        Test modunda simulasyon yapar (gercek emir GONDERMEZ).
        """
        if self.test_mode:
            try:
                book = self.client.futures_orderbook_ticker(symbol=symbol)
                best_bid = float(book["bidPrice"])
                best_ask = float(book["askPrice"])
            except Exception as e:
                try:
                    ticker = self.client.futures_symbol_ticker(symbol=symbol)
                    best_bid = best_ask = float(ticker["price"])
                except Exception as e2:
                    return (False, 0, False, f"Orderbook hatasi: {e}")

            limit_price = round(best_bid if side == "BUY" else best_ask, price_prec)
            print(f"[TEST LIMIT] {symbol} {side} LIMIT @ {limit_price} | bid={best_bid}, ask={best_ask}")
            print(f"[TEST LIMIT] {timeout_sec}sn bekleme simule ediliyor...")
            print(f"[TEST LIMIT] DOLDU @ {limit_price} | MAKER komisyon (0.02%)")
            return (True, limit_price, True, "LIMIT FILLED (TEST)")

        try:
            book = self.client.futures_orderbook_ticker(symbol=symbol)
            best_bid = float(book["bidPrice"])
            best_ask = float(book["askPrice"])

            limit_price = round(best_bid if side == "BUY" else best_ask, price_prec)

            order = self.client.futures_create_order(
                symbol=symbol, side=side, type="LIMIT",
                timeInForce="GTC", quantity=qty, price=limit_price
            )
            order_id = order["orderId"]
            print(f"[LIMIT] {symbol} {side} @ {limit_price} | orderId={order_id}")

            time.sleep(timeout_sec)

            status = self.client.futures_get_order(symbol=symbol, orderId=order_id)
            order_status = status.get("status")
            executed_qty = float(status.get("executedQty", 0) or 0)
            avg_price = float(status.get("avgPrice", 0) or 0)

            if order_status == "FILLED":
                print(f"[LIMIT] DOLDU | avg={avg_price} | MAKER")
                return (True, avg_price if avg_price > 0 else limit_price, True, "LIMIT FILLED")

            if order_status in ("NEW", "PARTIALLY_FILLED"):
                try:
                    self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
                    print(f"[LIMIT] Timeout - iptal")
                except Exception as ce:
                    print(f"[LIMIT] Cancel hatasi: {ce}")

                remaining = qty - executed_qty
                if remaining <= 0:
                    return (True, avg_price if avg_price > 0 else limit_price, True, "PARTIAL FULL")

                if not fallback:
                    return (False, 0, False, "Limit dolmadi, fallback kapali")

                mkt = self.client.futures_create_order(
                    symbol=symbol, side=side, type="MARKET", quantity=remaining
                )
                mkt_price = float(mkt.get("avgPrice", 0) or 0)

                if executed_qty > 0 and mkt_price > 0:
                    final_avg = ((avg_price * executed_qty) + (mkt_price * remaining)) / qty
                    print(f"[LIMIT] Partial+Market | avg={final_avg:.6f}")
                    return (True, final_avg, False, "PARTIAL + MARKET")
                elif mkt_price > 0:
                    print(f"[LIMIT] MARKET FALLBACK @ {mkt_price}")
                    return (True, mkt_price, False, "MARKET FALLBACK")
                else:
                    cur = self.client.futures_symbol_ticker(symbol=symbol)
                    return (True, float(cur["price"]), False, "MARKET FALLBACK")

            return (False, 0, False, f"Bilinmeyen status: {order_status}")

        except Exception as e:
            print(f"[LIMIT] HATA: {e}")
            if fallback:
                try:
                    fb = self.client.futures_create_order(
                        symbol=symbol, side=side, type="MARKET", quantity=qty
                    )
                    fb_price = float(fb.get("avgPrice", 0) or 0)
                    return (True, fb_price, False, "ERROR FALLBACK")
                except Exception as e2:
                    return (False, 0, False, f"Hata: {e} | Fallback: {e2}")
            return (False, 0, False, f"Limit hatasi: {e}")

    def _close_in_db(self, symbol: str):'''

if anchor in om and '_place_entry_order_with_fallback' not in om:
    om = om.replace(anchor, new_method, 1)
    changes += 1
    print("[2/4] order_manager.py: _place_entry_order_with_fallback eklendi")
else:
    print("[2/4] UYARI: _close_in_db cipa bulunamadi veya method zaten var")

with open(OM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(om.replace('\n', '\r\n'))

# ============================================================
# 2. strategy_engine.py
# ============================================================
with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

old_cfg = '''    "max_symbols": 30,
    "daily_max_loss": 0,
    "max_open_positions": 0,
    "strategies": {'''

new_cfg = '''    "max_symbols": 30,
    "daily_max_loss": 0,
    "max_open_positions": 0,
    "useLimitOrder": True,
    "limitTimeoutSec": 3,
    "fallbackToMarket": True,
    "strategies": {'''

if old_cfg in se:
    se = se.replace(old_cfg, new_cfg, 1)
    changes += 1
    print("[3/4] strategy_engine.py: DEFAULT_CONFIG guncellendi")
else:
    print("[3/4] UYARI: DEFAULT_CONFIG cipa bulunamadi (atlandi)")

# open_dca_position cagrisi
old_call = '''                            pt_enabled=pt_enabled,
                            pt_percent=pt_percent,
                            pt_keep_dca=pt_keep_dca,
                        )'''

new_call = '''                            pt_enabled=pt_enabled,
                            pt_percent=pt_percent,
                            pt_keep_dca=pt_keep_dca,
                            use_limit_order=bool(self.config.get("useLimitOrder", True)),
                            limit_timeout_sec=int(self.config.get("limitTimeoutSec", 3)),
                            fallback_market=bool(self.config.get("fallbackToMarket", True)),
                        )'''

if old_call in se:
    se = se.replace(old_call, new_call, 1)
    changes += 1
    print("[3/4] strategy_engine.py: open_dca_position cagrisi")
else:
    print("[3/4] UYARI: open_dca_position cagrisi bulunamadi (atlandi)")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

# ============================================================
# 3. position_manager.py
# ============================================================
with open(PM_SRC, 'r', encoding='utf-8', newline='') as f:
    pm = f.read().replace('\r\n', '\n')

old_comm = '''        entry_comm = initial_vol * taker_rate
        dca_comm = dca_vol * maker_rate
        exit_comm = total_vol * taker_rate'''

new_comm = '''        entry_is_maker = trade.get("entry_is_maker") or 0
        entry_rate = maker_rate if entry_is_maker else taker_rate
        entry_comm = initial_vol * entry_rate
        dca_comm = dca_vol * maker_rate
        exit_comm = total_vol * taker_rate'''

if old_comm in pm:
    pm = pm.replace(old_comm, new_comm, 1)
    changes += 1
    print("[4/4] position_manager.py: MAKER komisyon hesabi")
else:
    print("[4/4] UYARI: komisyon blogu bulunamadi (atlandi)")

with open(PM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(pm.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("NOT: database.py zaten onceki calismada islendi (entry_is_maker)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend'i Ctrl+C ile durdur")
print("  2. py -m uvicorn backend.main:app --reload")
print("  3. Tarayicida Ctrl+Shift+R")
print()
print("Geri donmek icin:")
for src in [OM_SRC, SE_SRC, PM_SRC]:
    print(f"  Copy-Item {src}.bak_limit_order_v2 {src} -Force")