import time
import sqlite3
from binance.client import Client
from backend.database import get_db_connection


class OrderManager:
    # Sınıf seviyesinde cache
    _exchange_info_cache = None
    _exchange_info_time = 0
    # ⚡ Komisyon cache
    _commission_cache = {}

    def __init__(self, client: Client, symbol: str = "BTCUSDT", test_mode: bool = True):
        self.client = client
        self.symbol = symbol
        self.test_mode = test_mode

    def get_commission_rate(self, symbol: str = None) -> dict:
        """
        Sembol icin gercek komisyon oranini Binance'ten ceker.
        1 saat cache.
        
        Returns:
            {"taker": 0.0004, "maker": 0.0002}
        """
        target_symbol = symbol or self.symbol
        now = time.time()
        
        # Cache kontrolu
        if target_symbol in OrderManager._commission_cache:
            cached = OrderManager._commission_cache[target_symbol]
            if now - cached.get("timestamp", 0) < 3600:
                return cached
        
        try:
            data = self.client.futures_commission_rate(symbol=target_symbol)
            result = {
                "taker": float(data.get("takerCommissionRate", 0.0004)),
                "maker": float(data.get("makerCommissionRate", 0.0002)),
                "timestamp": now,
            }
            OrderManager._commission_cache[target_symbol] = result
            print(f"[COMM] {target_symbol} komisyon: taker={result['taker']*100:.4f}%, maker={result['maker']*100:.4f}%")
            return result
        except Exception as e:
            print(f"[!] Komisyon orani alinamadi {target_symbol}: {e}")
            # Varsayilan VIP 0 degerleri
            return {"taker": 0.0004, "maker": 0.0002, "timestamp": now}

    def get_symbol_precision(self, symbol: str = None):
        """Exchange info'yu 5 dakika cache'ler."""
        target_symbol = symbol or self.symbol

        if OrderManager._exchange_info_cache is None or (time.time() - OrderManager._exchange_info_time) > 300:
            try:
                OrderManager._exchange_info_cache = self.client.futures_exchange_info()
                OrderManager._exchange_info_time = time.time()
            except Exception as e:
                print(f"[!] Exchange info hatası: {e}")
                if OrderManager._exchange_info_cache is None:
                    return 2, 3

        for s in OrderManager._exchange_info_cache['symbols']:
            if s['symbol'] == target_symbol:
                return s['pricePrecision'], s['quantityPrecision']
        return 2, 3

    def _set_margin_type(self, symbol: str, mode: str = None) -> bool:
        """F90a: Pozisyon acmadan once margin type degistir. Hata olursa yut."""
        target = mode or getattr(self, "margin_mode", "cross")
        try:
            margin_type = "CROSSED" if target == "cross" else "ISOLATED"
            self.client.futures_change_margin_type(
                symbol=symbol, marginType=margin_type
            )
            print(f"[MARGIN] {symbol} -> {target.upper()}")
            return True
        except Exception as e:
            err = str(e).lower()
            if "no need to change" in err or "already" in err:
                return True
            if "-4046" in err or "not supported" in err:
                print(f"[MARGIN] {symbol} desteklemiyor, atlandi")
                return False
            print(f"[MARGIN] {symbol} hata: {str(e)[:100]}")
            return False

    def open_dca_position(self, side: str, base_amount_usdt: float = 10.0, strategy_name: str = None,
                          leverage: int = 1, dca_levels: int = 3, step_pct: float = 1.0, tp_pct: float = 1.5, sl_pct: float = 3.0,
                          pt_enabled: int = 0, pt_percent: float = 50, pt_keep_dca: int = 1,
                          use_limit_order: bool = True, limit_timeout_sec: int = 3, fallback_market: bool = True):
        """
        İlk pozisyonu açar. DCA kademeleri position_manager tarafından yönetilir.
        """
        # F90a: Margin mode uygula (pozisyon acmadan once)
        self._set_margin_type(self.symbol, getattr(self, "margin_mode", "cross"))

        # ⚡ SON KONTROL: Aynı sembolde zaten pozisyon var mı? (race condition son savunma)
        conn = get_db_connection()
        existing = conn.execute(
            "SELECT id FROM active_trades WHERE symbol = ?", (self.symbol,)
        ).fetchone()
        conn.close()
        
        if existing:
            print(f"[DUP-PREVENT] {self.symbol} zaten açık pozisyonda! Yeni emir reddedildi.")
            return {
                "status": "duplicate",
                "symbol": self.symbol,
                "message": "Aynı sembolde açık pozisyon var"
            }
        
        price_prec, qty_prec = self.get_symbol_precision(self.symbol)
        ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
        current_price = float(ticker['price'])

        qty = round(base_amount_usdt / current_price, qty_prec)
        strat = strategy_name or "UNKNOWN"
        leverage = max(1, int(leverage))
        margin = base_amount_usdt / leverage if leverage > 0 else base_amount_usdt

        if self.test_mode:
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

            # F38: initial_price = entry_price (current_price degil - spike koruma)
            self._save_to_db(
                self.symbol, side, base_amount_usdt, entry_price, 0, strat,
                entry_price, base_amount_usdt, leverage,
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
            }

        # --- GERÇEK EMİR DÖNGÜSÜ (mainnet) ---
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

            tp_side = "SELL" if side == "BUY" else "BUY"
            tp_price = round(entry_price * (1 + (tp_pct / 100) if side == "BUY" else 1 - (tp_pct / 100)), price_prec)
            self.client.futures_create_order(
                symbol=self.symbol,
                side=tp_side,
                type="TAKE_PROFIT_MARKET",
                stopPrice=tp_price,
                closePosition=True
            )

            sl_price = round(entry_price * (1 - (sl_pct / 100) if side == "BUY" else 1 + (sl_pct / 100)), price_prec)
            self.client.futures_create_order(
                symbol=self.symbol,
                side=tp_side,
                type="STOP_MARKET",
                stopPrice=sl_price,
                closePosition=True
            )

            self._save_to_db(
                self.symbol, side, base_amount_usdt, entry_price, 0, strat,
                entry_price, base_amount_usdt, leverage,
                pt_enabled, pt_percent, pt_keep_dca, entry_is_maker
            )
            return {
                "status": "success",
                "mode": "REAL",
                "symbol": self.symbol,
                "strategy": strat,
                "entry_price": entry_price,
                "tp": tp_price,
                "sl": sl_price,
                "leverage": leverage
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==========================================================
    # GRID REEL: Seviye pozisyonu acma
    # ==========================================================
    def open_grid_position(self, side: str, base_amount_usdt: float = 5.0,
                           strategy_name: str = "DYNAMIC_GRID_REEL",
                           leverage: int = 1,
                           grid_group_id: str = None,
                           grid_level: int = 0,
                           grid_side: str = None,
                           grid_entry_price: float = 0,
                           grid_tp_price: float = 0,
                           use_limit_order: bool = True,
                           limit_timeout_sec: int = 3,
                           fallback_market: bool = True):
        """
        Grid seviyesi icin TEK pozisyon acar.
        DCA YOK -- her seviye bagimsiz.

        Duplicate kontrolu: (symbol + grid_group_id + grid_level) UNIQUE
        """
        if grid_group_id is None:
            return {"status": "error", "message": "grid_group_id zorunlu"}

        # ⚡ Duplicate kontrolu (SADECE symbol + level, group bagimsiz)
        # State kaybi durumunda ayni seviye farkli group_id ile tekrar tetiklenebilir.
        # Bunu engellemek icin son 5 dk icinde acilmis ayni seviye varsa atla.
        import time as _time
        conn = get_db_connection()

        # 1) Birebir eslesme (mevcut kontrol)
        existing = conn.execute(
            """SELECT id FROM active_trades
               WHERE symbol = ? AND grid_group_id = ? AND grid_level = ?
                 AND is_grid_position = 1""",
            (self.symbol, grid_group_id, grid_level)
        ).fetchone()

        if existing:
            conn.close()
            print(f"[GRID-DUP] {self.symbol} L{grid_level} zaten acik (ayni grup), atlandi")
            return {"status": "duplicate", "grid_level": grid_level, "reason": "same_group"}

        # 2) YENI: Ayni sembol + seviye, HERHANGI bir grupta, son 5 dk icinde acilmissa atla
        try:
            recent = conn.execute(
                """SELECT id, grid_group_id, entry_time FROM active_trades
                   WHERE symbol = ? AND grid_level = ? AND is_grid_position = 1
                   ORDER BY id DESC LIMIT 1""",
                (self.symbol, grid_level)
            ).fetchone()
        except Exception:
            recent = None

        if recent:
            _age = int(_time.time()) - int(recent["entry_time"] or 0)
            if _age < 300:  # 5 dk
                conn.close()
                print(f"[GRID-DUP] {self.symbol} L{grid_level} son {_age}s icinde acildi "
                      f"(id={recent['id']}, grup={recent['grid_group_id']}) - atlandi")
                return {"status": "duplicate", "grid_level": grid_level, "reason": "recent_same_level"}

        conn.close()

        price_prec, qty_prec = self.get_symbol_precision(self.symbol)
        ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
        current_price = float(ticker["price"])

        qty = round(base_amount_usdt / current_price, qty_prec)
        leverage = max(1, int(leverage))
        margin = base_amount_usdt / leverage if leverage > 0 else base_amount_usdt
        strat = strategy_name or "DYNAMIC_GRID_REEL"

        # ⚡ Grid seviyesinin gercek fiyati (fallback: o anki market)
        _level_price = grid_entry_price if (grid_entry_price and grid_entry_price > 0) else current_price

        # ==========================================================
        # ⚡ SPIKE KORUMASI: current_price ile grid_entry_price arasinda
        # %10'dan fazla fark varsa testnet spike -> REDDET
        # ==========================================================
        if grid_entry_price and grid_entry_price > 0:
            _diff_pct = abs(current_price - grid_entry_price) / grid_entry_price * 100
            if _diff_pct > 10:
                print(f"[SPIKE-GUARD] {self.symbol} L{grid_level} "
                      f"REDDEDILDI! current={current_price:.6f} "
                      f"level={grid_entry_price:.6f} fark=%{_diff_pct:.2f}")
                return {
                    "status": "error",
                    "message": f"Fiyat spike (fark %{_diff_pct:.1f}), işlem reddedildi",
                    "spike_guard": True
                }

        # --- TEST MODU ---
        if self.test_mode:
            if use_limit_order:
                success, entry_price, is_maker, msg = self._place_entry_order_with_fallback(
                    self.symbol, side, qty, price_prec,
                    timeout_sec=limit_timeout_sec, fallback=fallback_market
                )
                if not success:
                    print(f"[!] GRID TEST LIMIT basarisiz: {msg}")
                    return {"status": "error", "message": msg}
                entry_is_maker = 1 if is_maker else 0
                mode_label = "MAKER" if is_maker else "TAKER"
            else:
                entry_is_maker = 0
                mode_label = "MARKET"

            # ⚡ Simulasyonda seviye fiyatini kullan (gercekci grid davranisi)
            entry_price = _level_price

            print(f"[GRID-TEST] {self.symbol} L{grid_level} [{grid_side}] {side} {mode_label} | "
                  f"Seviye: {_level_price} | Market: {current_price} | Vol: {base_amount_usdt} | TP: {grid_tp_price}")

            ok = self._save_grid_to_db(
                symbol=self.symbol,
                side=side,
                total_vol=base_amount_usdt,
                avg_price=entry_price,
                strategy_name=strat,
                initial_price=_level_price,
                initial_vol=base_amount_usdt,
                leverage=leverage,
                entry_is_maker=entry_is_maker,
                grid_group_id=grid_group_id,
                grid_level=grid_level,
                grid_side=grid_side or side,
                grid_entry_price=grid_entry_price,
                grid_tp_price=grid_tp_price,
            )
            return {
                "status": "success" if ok else "error",
                "mode": "TEST",
                "symbol": self.symbol,
                "grid_level": grid_level,
                "grid_group_id": grid_group_id,
                "entry_price": entry_price,
                "order_type": mode_label,
            }

        # --- GERCEK EMIR ---
        try:
            if leverage > 1:
                try:
                    self.client.futures_change_leverage(symbol=self.symbol, leverage=leverage)
                except Exception as le:
                    print(f"[!] Grid leverage ayarlanamadi: {le}")

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
                    symbol=self.symbol, side=side, type="MARKET", quantity=qty
                )
                entry_price = float(order.get("avgPrice") or current_price)
                entry_is_maker = 0

            # ⚡ Grid seviyesi icin TP emri (komsu seviye)
            if grid_tp_price and grid_tp_price > 0:
                tp_side = "SELL" if side == "BUY" else "BUY"
                tp_price_rounded = round(grid_tp_price, price_prec)
                try:
                    self.client.futures_create_order(
                        symbol=self.symbol,
                        side=tp_side,
                        type="TAKE_PROFIT_MARKET",
                        stopPrice=tp_price_rounded,
                        closePosition=True
                    )
                    print(f"[GRID-TP] {self.symbol} L{grid_level} TP emri @ {tp_price_rounded}")
                except Exception as te:
                    print(f"[!] Grid TP emri hatasi {self.symbol}: {te}")

            ok = self._save_grid_to_db(
                symbol=self.symbol,
                side=side,
                total_vol=base_amount_usdt,
                avg_price=entry_price,
                strategy_name=strat,
                initial_price=_level_price,
                initial_vol=base_amount_usdt,
                leverage=leverage,
                entry_is_maker=entry_is_maker,
                grid_group_id=grid_group_id,
                grid_level=grid_level,
                grid_side=grid_side or side,
                grid_entry_price=grid_entry_price,
                grid_tp_price=grid_tp_price,
            )
            return {
                "status": "success" if ok else "error",
                "mode": "REAL",
                "symbol": self.symbol,
                "grid_level": grid_level,
                "grid_group_id": grid_group_id,
                "entry_price": entry_price,
                "tp": grid_tp_price,
                "leverage": leverage,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _save_grid_to_db(self, symbol, side, total_vol, avg_price, strategy_name,
                         initial_price, initial_vol, leverage, entry_is_maker,
                         grid_group_id, grid_level, grid_side,
                         grid_entry_price, grid_tp_price):
        """Grid pozisyonunu active_trades'e yazar (retry + leak fix)."""
        import time as _time
        max_retries = 3
        conn = None
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()
                conn.execute(
                    """INSERT INTO active_trades
                       (symbol, trade_type, total_vol, avg_price, dca_count, entry_time,
                        strategy_name, initial_price, initial_vol, leverage,
                        pt_enabled, pt_percent, pt_done, pt_volume, pt_pnl, pt_keep_dca,
                        entry_is_maker,
                        is_grid_position, grid_group_id, grid_level, grid_side,
                        grid_entry_price, grid_tp_price, grid_created_at, grid_state)
                       VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, ?, 1, ?, ?, ?, ?, ?, ?, 'open')""",
                    (symbol, side, total_vol, avg_price, int(_time.time()),
                     strategy_name, initial_price, initial_vol, leverage,
                     entry_is_maker,
                     grid_group_id, grid_level, grid_side,
                     grid_entry_price, grid_tp_price, int(_time.time()))
                )
                conn.commit()
                return True
            except Exception as e:
                err_lower = str(e).lower()
                if "unique" in err_lower or "integrity" in err_lower:
                    print(f"[GRID-DB] Duplicate, atlandi: {symbol} L{grid_level}")
                    return False
                if "database is locked" in err_lower and attempt < max_retries - 1:
                    _time.sleep(0.5 * (attempt + 1))
                    continue
                print(f"[GRID-DB] INSERT hatasi {symbol} L{grid_level}: {e}")
                return False
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
        return False

    # ==========================================================
    # GRID REEL: Seviye pozisyonu kapatma
    # ==========================================================
    def close_grid_position(self, symbol: str, grid_group_id: str, grid_level: int):
        """Tek grid seviyesini kapatir."""
        if self.test_mode:
            print(f"[GRID-TEST] {symbol} L{grid_level} (grup={grid_group_id}) kapatildi")
            self._close_in_db(symbol, is_grid=True,
                              grid_group_id=grid_group_id, grid_level=grid_level)
            return {"status": "success", "mode": "TEST",
                    "symbol": symbol, "grid_level": grid_level}

        try:
            # Bekleyen TP/SL emirleri varsa iptal
            try:
                self.client.futures_cancel_all_open_orders(symbol=symbol)
            except Exception:
                pass

            positions = self.client.futures_position_information(symbol=symbol)
            pos = next((p for p in positions
                        if p["symbol"] == symbol and float(p["positionAmt"]) != 0), None)
            if pos:
                amt = float(pos["positionAmt"])
                close_side = "SELL" if amt > 0 else "BUY"
                self.client.futures_create_order(
                    symbol=symbol, side=close_side, type="MARKET",
                    quantity=abs(amt), reduceOnly=True
                )

            self._close_in_db(symbol, is_grid=True,
                              grid_group_id=grid_group_id, grid_level=grid_level)
            return {"status": "success", "mode": "REAL",
                    "symbol": symbol, "grid_level": grid_level}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==========================================================
    # MANUEL EMIR - Kullanici tarafindan manuel acilan pozisyon
    # ==========================================================
    def open_manual_position(self, side: str, base_amount_usdt: float = 100.0,
                             order_mode: str = "market",
                             leverage: int = 1,
                             limit_price: float = 0,
                             limit_timeout: int = 5,
                             take_profit: float = 1.5,
                             trailing_steps: str = "",
                             stop_loss: float = 5.0,
                             pt_enabled: int = 0,
                             pt_percent: float = 50,
                             pt_keep_dca: int = 1):
        """
        Manuel emir acar.
        order_mode: "market" | "limit" | "limit_with_fallback"
        Duplicate check YOK (MANUAL strateji icin ozel UNIQUE index kullanilir).
        """
        price_prec, qty_prec = self.get_symbol_precision(self.symbol)
        ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
        current_price = float(ticker["price"])

        qty = round(base_amount_usdt / current_price, qty_prec)
        leverage = max(1, int(leverage))
        margin = base_amount_usdt / leverage if leverage > 0 else base_amount_usdt
        strat = "MANUAL"

        # ============ TEST MODU ============
        if self.test_mode:
            if order_mode == "market":
                entry_price = current_price
                entry_is_maker = 0
                mode_label = "MARKET"
            elif order_mode == "limit":
                entry_price = limit_price if limit_price > 0 else current_price
                entry_is_maker = 1
                mode_label = "LIMIT (MAKER)"
            elif order_mode == "limit_with_fallback":
                success, entry_price, is_maker, msg = self._place_entry_order_with_fallback(
                    self.symbol, side, qty, price_prec,
                    timeout_sec=limit_timeout, fallback=True
                )
                if not success:
                    return {"status": "error", "message": msg}
                entry_is_maker = 1 if is_maker else 0
                mode_label = "LIMIT+FB (MAKER)" if is_maker else "LIMIT+FB (TAKER)"
            else:
                return {"status": "error", "message": f"Gecersiz order_mode: {order_mode}"}

            print(f"[MANUAL-TEST] {self.symbol} {side} {mode_label} | "
                  f"Fiyat: {entry_price} | Vol: {base_amount_usdt} | Lev: {leverage}x | "
                  f"TP: {take_profit}% | TTP: {trailing_steps or '-'} | SL: {stop_loss}%")

            self._save_to_db(
                self.symbol, side, base_amount_usdt, entry_price, 0, strat,
                entry_price, base_amount_usdt, leverage,
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
            }

        # ============ GERCEK EMIR ============
        try:
            if leverage > 1:
                try:
                    self.client.futures_change_leverage(symbol=self.symbol, leverage=leverage)
                except Exception as le:
                    print(f"[!] Leverage ayarlanamadi: {le}")

            if order_mode == "market":
                order = self.client.futures_create_order(
                    symbol=self.symbol, side=side, type="MARKET", quantity=qty
                )
                entry_price = float(order.get("avgPrice") or current_price)
                entry_is_maker = 0

            elif order_mode == "limit":
                if limit_price <= 0:
                    return {"status": "error", "message": "Limit fiyat gerekli"}
                order = self.client.futures_create_order(
                    symbol=self.symbol, side=side, type="LIMIT",
                    timeInForce="GTC", quantity=qty, price=limit_price
                )
                entry_price = limit_price
                entry_is_maker = 1

            elif order_mode == "limit_with_fallback":
                success, entry_price, is_maker, msg = self._place_entry_order_with_fallback(
                    self.symbol, side, qty, price_prec,
                    timeout_sec=limit_timeout, fallback=True
                )
                if not success:
                    return {"status": "error", "message": msg}
                entry_is_maker = 1 if is_maker else 0
            else:
                return {"status": "error", "message": f"Gecersiz order_mode: {order_mode}"}

            # TP/SL emirleri (opsiyonel)
            tp_side = "SELL" if side == "BUY" else "BUY"

            if take_profit > 0:
                try:
                    tp_price = round(
                        entry_price * (1 + take_profit/100) if side == "BUY"
                        else entry_price * (1 - take_profit/100),
                        price_prec
                    )
                    self.client.futures_create_order(
                        symbol=self.symbol, side=tp_side,
                        type="TAKE_PROFIT_MARKET",
                        stopPrice=tp_price, closePosition=True
                    )
                except Exception as _te:
                    print(f"[!] TP emri hatasi: {_te}")

            if stop_loss > 0:
                try:
                    sl_price = round(
                        entry_price * (1 - stop_loss/100) if side == "BUY"
                        else entry_price * (1 + stop_loss/100),
                        price_prec
                    )
                    self.client.futures_create_order(
                        symbol=self.symbol, side=tp_side,
                        type="STOP_MARKET",
                        stopPrice=sl_price, closePosition=True
                    )
                except Exception as _se:
                    print(f"[!] SL emri hatasi: {_se}")

            self._save_to_db(
                self.symbol, side, base_amount_usdt, entry_price, 0, strat,
                entry_price, base_amount_usdt, leverage,
                pt_enabled, pt_percent, pt_keep_dca, entry_is_maker
            )
            return {
                "status": "success",
                "mode": "REAL",
                "symbol": self.symbol,
                "strategy": strat,
                "side": side,
                "entry_price": entry_price,
                "leverage": leverage,
                "margin": round(margin, 4),
                "order_type": order_mode
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def close_position(self, symbol: str = None):
        target_symbol = symbol or self.symbol

        if self.test_mode:
            print(f"[TEST MODU] {target_symbol} klasik pozisyon kapatildi.")
            self._close_in_db(target_symbol)
            return {"status": "success", "mode": "TEST", "symbol": target_symbol, "action": "CLOSED"}

        try:
            self.client.futures_cancel_all_open_orders(symbol=target_symbol)
            positions = self.client.futures_position_information(symbol=target_symbol)
            pos = next((p for p in positions if p['symbol'] == target_symbol and float(p['positionAmt']) != 0), None)

            if pos:
                amt = float(pos['positionAmt'])
                close_side = "SELL" if amt > 0 else "BUY"
                self.client.futures_create_order(
                    symbol=target_symbol,
                    side=close_side,
                    type="MARKET",
                    quantity=abs(amt),
                    reduceOnly=True
                )

            self._close_in_db(target_symbol, is_grid=False)
            return {"status": "success", "mode": "REAL", "symbol": target_symbol, "action": "CLOSED"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _save_to_db(self, symbol, side, total_vol, avg_price, dca_count, strategy_name, initial_price, initial_vol, leverage=1,
                    pt_enabled=0, pt_percent=50, pt_keep_dca=1, entry_is_maker=0):
        """⚡ Retry + connection leak fix"""
        max_retries = 3
        conn = None
        for attempt in range(max_retries):
            try:
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
                return True
            except sqlite3.IntegrityError:
                # Duplicate - normal, sessizce don
                return False
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                print(f"[!] DB kayit hatasi ({symbol}): {e}")
                return False
            except Exception as e:
                print(f"[!] DB kayit hatasi ({symbol}): {e}")
                return False
            finally:
                # ⚡ HER DURUMDA connection'i kapat
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
        return False



    def _place_entry_order_with_fallback(self, symbol, side, qty, price_prec, timeout_sec=3, fallback=True):
        """
        LIMIT emri gonderir, timeout'ta MARKET fallback yapar.
        Test modunda simulasyon yapar (gercek emir GONDERMEZ).
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

            limit_price = round(best_bid if side == "BUY" else best_ask, price_prec)
            print(f"[TEST LIMIT] {symbol} {side} LIMIT @ {limit_price} | bid={best_bid}, ask={best_ask}")
            print(f"[TEST LIMIT] {timeout_sec}sn bekleme simule ediliyor...")
            print(f"[TEST LIMIT] DOLDU @ {limit_price} | MAKER komisyon (0.02%)")
            return (True, limit_price, True, "LIMIT FILLED (TEST)")

        # ============ GERCEK EMIR ============
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
                    print(f"[LIMIT] ERROR FALLBACK MARKET @ {fb_price}")
                    return (True, fb_price, False, "ERROR FALLBACK")
                except Exception as e2:
                    return (False, 0, False, f"Hata: {e} | Fallback: {e2}")
            return (False, 0, False, f"Limit hatasi: {e}")

    def partial_close_position(self, symbol: str, close_usdt: float, current_price: float):
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
    
    def _close_in_db(self, symbol: str, is_grid: bool = False,
                     grid_group_id: str = None, grid_level: int = None):
        """
        Klasik pozisyon : is_grid=False  -> sadece is_grid_position=0 sil
        Grid seviyesi   : is_grid=True   -> symbol+group+level sil
        """
        conn = get_db_connection()
        if is_grid:
            conn.execute(
                """DELETE FROM active_trades
                   WHERE symbol = ? AND grid_group_id = ? AND grid_level = ?
                     AND is_grid_position = 1""",
                (symbol, grid_group_id, grid_level)
            )
        else:
            conn.execute(
                "DELETE FROM active_trades WHERE symbol = ? AND COALESCE(is_grid_position,0) = 0",
                (symbol,)
            )
        conn.commit()
        conn.close()