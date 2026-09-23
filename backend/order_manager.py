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

    def open_dca_position(self, side: str, base_amount_usdt: float = 10.0, strategy_name: str = None,
                          leverage: int = 1, dca_levels: int = 3, step_pct: float = 1.0, tp_pct: float = 1.5, sl_pct: float = 3.0,
                          pt_enabled: int = 0, pt_percent: float = 50, pt_keep_dca: int = 1,
                          use_limit_order: bool = True, limit_timeout_sec: int = 3, fallback_market: bool = True):
        """
        İlk pozisyonu açar. DCA kademeleri position_manager tarafından yönetilir.
        """
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

    def close_position(self, symbol: str = None):
        target_symbol = symbol or self.symbol

        if self.test_mode:
            print(f"[TEST MODU] {target_symbol} pozisyonu kapatıldı.")
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

            self._close_in_db(target_symbol)
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
    
    def _close_in_db(self, symbol: str):
        conn = get_db_connection()
        conn.execute("DELETE FROM active_trades WHERE symbol = ?", (symbol,))
        conn.commit()
        conn.close()