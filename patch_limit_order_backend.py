import shutil
import os

DB_SRC = 'backend/database.py'
OM_SRC = 'backend/order_manager.py'
SE_SRC = 'backend/strategy_engine.py'
PM_SRC = 'backend/position_manager.py'

for src in [DB_SRC, OM_SRC, SE_SRC, PM_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_limit_order')
    print(f"[1/5] Yedek: {src}.bak_limit_order")

changes = 0

# ============================================================
# 1. database.py: active_trades + entry_is_maker
# ============================================================
with open(DB_SRC, 'r', encoding='utf-8', newline='') as f:
    db = f.read().replace('\r\n', '\n')

old_mig = '''        "pt_keep_dca": "ALTER TABLE active_trades ADD COLUMN pt_keep_dca INTEGER DEFAULT 1",
    }'''
new_mig = '''        "pt_keep_dca": "ALTER TABLE active_trades ADD COLUMN pt_keep_dca INTEGER DEFAULT 1",
        "entry_is_maker": "ALTER TABLE active_trades ADD COLUMN entry_is_maker INTEGER DEFAULT 0",
    }'''

if old_mig in db:
    db = db.replace(old_mig, new_mig, 1)
    changes += 1
    print("[2/5] database.py: entry_is_maker sutunu eklendi")
else:
    print("[2/5] HATA: active_trades migrations_at sonu bulunamadi!")
    exit(1)

with open(DB_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(db.replace('\n', '\r\n'))

# ============================================================
# 2. order_manager.py: open_dca_position imza + LIMIT mantigi
# ============================================================
with open(OM_SRC, 'r', encoding='utf-8', newline='') as f:
    om = f.read().replace('\r\n', '\n')

# 2a. Imzaya 3 yeni parametre
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
    print("[3/5] order_manager.py: open_dca_position imzasi")
else:
    print("[3/5] HATA: open_dca_position imzasi bulunamadi!")
    exit(1)

# 2b. TEST MODU blogu
old_test = '''        if self.test_mode:
            print(f"[TEST MODU] {self.symbol} [{strat}] {side} | Fiyat: {current_price} USDT | Adet: {qty} | Kaldıraç: {leverage}x | Marjin: {margin:.4f} | Toplam: {base_amount_usdt:.2f} USDT")
            self._save_to_db(self.symbol, side, base_amount_usdt, current_price, 0, strat, current_price, base_amount_usdt, leverage,
                             pt_enabled, pt_percent, pt_keep_dca)
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
    print("[3/5] order_manager.py: TEST MODU blogu LIMIT simule ediyor")
else:
    print("[3/5] HATA: TEST MODU blogu bulunamadi!")
    exit(1)

# 2c. GERCEK EMIR blogu
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
    print("[3/5] order_manager.py: GERCEK EMIR blogu LIMIT kullaniyor")
else:
    print("[3/5] HATA: GERCEK EMIR blogu bulunamadi!")
    exit(1)

# 2d. _save_to_db cagrisi (GERCEK)
old_save_real = '''            self._save_to_db(self.symbol, side, base_amount_usdt, entry_price, 0, strat, entry_price, base_amount_usdt, leverage,
                             pt_enabled, pt_percent, pt_keep_dca)'''

new_save_real = '''            self._save_to_db(
                self.symbol, side, base_amount_usdt, entry_price, 0, strat,
                entry_price, base_amount_usdt, leverage,
                pt_enabled, pt_percent, pt_keep_dca, entry_is_maker
            )'''

if old_save_real in om:
    om = om.replace(old_save_real, new_save_real, 1)
    changes += 1
    print("[3/5] order_manager.py: _save_to_db cagrisi (gercek) guncellendi")
else:
    print("[3/5] UYARI: gercek _save_to_db cagrisi bulunamadi (atlandi)")

# 2e. _save_to_db metodu
old_save_def = '''    def _save_to_db(self, symbol, side, total_vol, avg_price, dca_count, strategy_name, initial_price, initial_vol, leverage=1,
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

new_save_def = '''    def _save_to_db(self, symbol, side, total_vol, avg_price, dca_count, strategy_name, initial_price, initial_vol, leverage=1,
                    pt_enabled=0, pt_percent=50, pt_keep_dca=1, entry_is_maker=0):
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO active_trades 
               (symbol, trade_type, total_vol, avg_price, dca_count, entry_time, strategy_name, initial_price, initial_vol, leverage,
                pt_enabled, pt_percent, pt_done, pt_volume, pt_pnl, pt_keep_dca, entry_is_maker) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?)""",
            (symbol, side, total_vol, avg_price, dca_count, int(time.time()),
             strategy_name, initial_price, initial_vol, leverage,
             pt_enabled, pt_percent, pt_keep_dca, entry_is_maker)
        )
        conn.commit()
        conn.close()'''

if old_save_def in om:
    om = om.replace(old_save_def, new_save_def, 1)
    changes += 1
    print("[3/5] order_manager.py: _save_to_db guncellendi")
else:
    print("[3/5] HATA: _save_to_db metodu bulunamadi!")
    exit(1)

# 2f. Yeni method: _place_entry_order_with_fallback
anchor = '''    def _close_in_db(self, symbol: str):'''

new_method = '''    def _place_entry_order_with_fallback(self, symbol, side, qty, price_prec, timeout_sec=3, fallback=True):
        """
        LIMIT emri gonderir, timeout'ta MARKET fallback yapar.
        Test modunda simulasyon yapar (gercek emir GONDERMEZ).

        Returns:
            (success: bool, avg_price: float, is_maker: bool, message: str)
        """
        # ============ TEST MODU SIMULASYONU ============
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
                    print(f"[TEST LIMIT] Orderbook alinamadi: {e} / {e2}")
                    return (False, 0, False, f"Orderbook hatasi: {e}")

            if side == "BUY":
                limit_price = round(best_bid, price_prec)
            else:
                limit_price = round(best_ask, price_prec)

            print(f"[TEST LIMIT] {symbol} {side} LIMIT @ {limit_price} | bid={best_bid}, ask={best_ask}")
            print(f"[TEST LIMIT] {timeout_sec}sn bekleme simule ediliyor...")
            print(f"[TEST LIMIT] DOLDU @ {limit_price} | MAKER komisyon (0.02%)")

            return (True, limit_price, True, "LIMIT FILLED (TEST)")

        # ============ GERCEK EMIR ============
        try:
            book = self.client.futures_orderbook_ticker(symbol=symbol)
            best_bid = float(book["bidPrice"])
            best_ask = float(book["askPrice"])

            if side == "BUY":
                limit_price = round(best_bid, price_prec)
            else:
                limit_price = round(best_ask, price_prec)

            # LIMIT emri gonder
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="LIMIT",
                timeInForce="GTC",
                quantity=qty,
                price=limit_price
            )
            order_id = order["orderId"]
            print(f"[LIMIT] {symbol} {side} @ {limit_price} | orderId={order_id}")

            # Timeout bekle
            time.sleep(timeout_sec)

            # Durumu kontrol et
            status = self.client.futures_get_order(symbol=symbol, orderId=order_id)
            order_status = status.get("status")
            executed_qty = float(status.get("executedQty", 0) or 0)
            avg_price = float(status.get("avgPrice", 0) or 0)

            # Hepsini doldurdu mu?
            if order_status == "FILLED":
                print(f"[LIMIT] DOLDU | avg={avg_price} | MAKER komisyon")
                return (True, avg_price if avg_price > 0 else limit_price, True, "LIMIT FILLED")

            # Dolmadi veya kismi doldu
            if order_status in ("NEW", "PARTIALLY_FILLED"):
                try:
                    self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
                    print(f"[LIMIT] Timeout - iptal edildi")
                except Exception as ce:
                    print(f"[LIMIT] Cancel hatasi: {ce}")

                remaining_qty = qty - executed_qty

                # Hepsi dolmus (yaris yaris)
                if remaining_qty <= 0:
                    return (True, avg_price if avg_price > 0 else limit_price, True, "LIMIT PARTIAL FULL")

                # Fallback kapali ise
                if not fallback:
                    print(f"[LIMIT] Fallback kapali - islem iptal")
                    return (False, 0, False, "Limit dolmadi, fallback kapali")

                # MARKET fallback (sadece kalan icin)
                market_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=remaining_qty
                )
                market_price = float(market_order.get("avgPrice", 0) or 0)

                if executed_qty > 0 and market_price > 0:
                    # Ortalama hesap
                    final_avg = ((avg_price * executed_qty) + (market_price * remaining_qty)) / qty
                    print(f"[LIMIT] Partial+Market | avg={final_avg:.6f}")
                    return (True, final_avg, False, "PARTIAL + MARKET")
                elif market_price > 0:
                    print(f"[LIMIT] MARKET FALLBACK @ {market_price}")
                    return (True, market_price, False, "MARKET FALLBACK")
                else:
                    # Market fiyati alinamadi, mevcut fiyati kullan
                    current = self.client.futures_symbol_ticker(symbol=symbol)
                    return (True, float(current["price"]), False, "MARKET FALLBACK (no avg)")

            # Bilinmeyen durum
            return (False, 0, False, f"Bilinmeyen order status: {order_status}")

        except Exception as e:
            print(f"[LIMIT] HATA: {e}")
            # Acil durum: market ile dene
            if fallback:
                try:
                    fb = self.client.futures_create_order(
                        symbol=symbol, side=side, type="MARKET", quantity=qty
                    )
                    fb_price = float(fb.get("avgPrice", 0) or 0)
                    print(f"[LIMIT] ERROR FALLBACK MARKET @ {fb_price}")
                    return (True, fb_price, False, "ERROR FALLBACK")
                except Exception as e2:
                    return (False, 0, False, f"Hata: {e} | Fallback: {e2}")
            return (False, 0, False, f"Limit hatasi: {e}")

    def _close_in_db(self, symbol: str):'''

if anchor in om and '_place_entry_order_with_fallback' not in om:
    om = om.replace(anchor, new_method, 1)
    changes += 1
    print("[3/5] order_manager.py: _place_entry_order_with_fallback eklendi")
else:
    print("[3/5] HATA: _close_in_db cipa bulunamadi!")
    exit(1)

with open(OM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(om.replace('\n', '\r\n'))

# ============================================================
# 3. strategy_engine.py: DEFAULT_CONFIG + cagri
# ============================================================
with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

# 3a. DEFAULT_CONFIG
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
    print("[4/5] strategy_engine.py: DEFAULT_CONFIG'e execution alanlari")
else:
    print("[4/5] HATA: DEFAULT_CONFIG cipa bulunamadi!")
    exit(1)

# 3b. open_dca_position cagrisi
old_call = '''                    try:
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

new_call = '''                    # ⚡ Execution ayarlari
                    use_limit = bool(self.config.get("useLimitOrder", True))
                    limit_timeout = int(self.config.get("limitTimeoutSec", 3))
                    fallback_mkt = bool(self.config.get("fallbackToMarket", True))

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
                            use_limit_order=use_limit,
                            limit_timeout_sec=limit_timeout,
                            fallback_market=fallback_mkt,
                        )'''

if old_call in se:
    se = se.replace(old_call, new_call, 1)
    changes += 1
    print("[4/5] strategy_engine.py: open_dca_position cagrisi guncellendi")
else:
    print("[4/5] UYARI: open_dca_position cagrisi bulunamadi (atlandi)")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

# ============================================================
# 4. position_manager.py: _execute_close MAKER hesabi
# ============================================================
with open(PM_SRC, 'r', encoding='utf-8', newline='') as f:
    pm = f.read().replace('\r\n', '\n')

old_comm = '''        entry_comm = initial_vol * taker_rate
        dca_comm = dca_vol * maker_rate
        exit_comm = total_vol * taker_rate'''

new_comm = '''        # ⚡ Giris MAKER mi TAKER mi?
        entry_is_maker = trade.get("entry_is_maker") or 0
        entry_rate = maker_rate if entry_is_maker else taker_rate
        entry_comm = initial_vol * entry_rate
        dca_comm = dca_vol * maker_rate
        exit_comm = total_vol * taker_rate'''

if old_comm in pm:
    pm = pm.replace(old_comm, new_comm, 1)
    changes += 1
    print("[5/5] position_manager.py: MAKER komisyon hesabi eklendi")
else:
    print("[5/5] UYARI: komisyon blogu bulunamadi (atlandi)")

with open(PM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(pm.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Giris emirleri artik LIMIT + Fallback (3sn timeout)")
print("  - Test modunda LIMIT akisi simule edilir (log)")
print("  - MAKER komisyon (0.02%) -> TAKER (0.04%) yarisi")
print("  - entry_is_maker DB'ye yazilir (komisyon hesabi dogru)")
print("  - TP/SL MARKET kalir (acil cikis)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend'i Ctrl+C ile durdur")
print("  2. py -m uvicorn backend.main:app --reload")
print("  3. Backend log'unda '[DB] active_trades + entry_is_maker' gormelisin")
print()
print("Geri donmek icin:")
for src in [DB_SRC, OM_SRC, SE_SRC, PM_SRC]:
    print(f"  Copy-Item {src}.bak_limit_order {src} -Force")