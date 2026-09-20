import shutil
import os

OM_SRC = 'backend/order_manager.py'

if not os.path.exists(OM_SRC):
    print(f"[HATA] {OM_SRC} bulunamadi")
    exit(1)

shutil.copy2(OM_SRC, OM_SRC + '.bak_fix_om')
print(f"[1/2] Yedek: {OM_SRC}.bak_fix_om")

with open(OM_SRC, 'r', encoding='utf-8', newline='') as f:
    om = f.read().replace('\r\n', '\n')

# Zaten var mi?
if 'def _place_entry_order_with_fallback' in om:
    print("[2/2] _place_entry_order_with_fallback zaten var (atlandi)")
    exit(0)

# Cipa: partial_close_position metodu (bu kesin var, onceki patch'te eklendi)
anchor = '    def partial_close_position(self, symbol: str, close_usdt: float, current_price: float):'

if anchor not in om:
    # Alternatif cipa
    anchor = '    def _close_in_db(self, symbol: str):'

if anchor not in om:
    print("[2/2] HATA: Cipa bulunamadi! (ne partial_close_position ne _close_in_db)")
    exit(1)

new_method = '''    def _place_entry_order_with_fallback(self, symbol, side, qty, price_prec, timeout_sec=3, fallback=True):
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

'''

om = om.replace(anchor, new_method + anchor, 1)
print("[2/2] _place_entry_order_with_fallback metodu eklendi")

with open(OM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(om.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload modundaysa otomatik yuklenir")
print("  2. Degilse Ctrl+C + py -m uvicorn backend.main:app --reload")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {OM_SRC}.bak_fix_om {OM_SRC} -Force")