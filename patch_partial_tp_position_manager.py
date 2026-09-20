import shutil
import os

PM_SRC = 'backend/position_manager.py'

if not os.path.exists(PM_SRC):
    print(f"[HATA] {PM_SRC} bulunamadi")
    exit(1)

shutil.copy2(PM_SRC, PM_SRC + '.bak_partial_tp')
print(f"[1/3] Yedek: {PM_SRC}.bak_partial_tp")

changes = 0

with open(PM_SRC, 'r', encoding='utf-8', newline='') as f:
    pm = f.read().replace('\r\n', '\n')

# ============================================================
# 1. _execute_partial_close metodu (yeni)
# ============================================================
anchor = '''    async def _execute_close(self, symbol: str, exit_price: float, reason: str, force: bool = False):'''

new_method = '''    async def _execute_partial_close(self, symbol: str, exit_price: float, close_vol_usdt: float,
                                      pt_percent: float, reason: str):
        """
        Pozisyonun BELIRLI bir USDT hacmini kapatir ve trade_history'e AYRI satir yazar.
        Ana pozisyon active_trades'te KALIR, sadece total_vol kucultulur.
        """
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM active_trades WHERE symbol = ?", (symbol,)).fetchone()
        conn.close()
        if not row:
            print(f"[PARTIAL-TP] {symbol} aktif pozisyon yok")
            return None
        
        trade = dict(row)
        avg_price = trade["avg_price"]
        trade_type = trade["trade_type"]
        
        # --- Validasyonlar ---
        if not exit_price or exit_price <= 0:
            print(f"[PARTIAL-TP] Gecersiz exit {symbol}: {exit_price}")
            return None
        if not avg_price or avg_price <= 0:
            print(f"[PARTIAL-TP] Gecersiz avg {symbol}: {avg_price}")
            return None
        
        ratio = exit_price / avg_price
        if ratio > 10 or ratio < 0.1:
            print(f"[PARTIAL-TP] Supheli oran {symbol}: {ratio:.4f}")
            return None
        
        if close_vol_usdt <= 0 or close_vol_usdt >= trade["total_vol"]:
            print(f"[PARTIAL-TP] Gecersiz hacim {symbol}: {close_vol_usdt} / {trade['total_vol']}")
            return None
        
        # --- PnL ---
        if trade_type == "BUY":
            pnl_pct = (exit_price - avg_price) / avg_price
        else:
            pnl_pct = (avg_price - exit_price) / avg_price
        
        # --- Komisyon (sadece CIKIS) ---
        if self.order_manager and hasattr(self.order_manager, 'get_commission_rate'):
            comm_rates = self.order_manager.get_commission_rate(symbol)
        else:
            comm_rates = {"taker": 0.0004, "maker": 0.0002}
        taker_rate = comm_rates.get("taker", 0.0004)
        
        exit_comm = close_vol_usdt * taker_rate
        gross_pnl = close_vol_usdt * pnl_pct
        net_pnl = gross_pnl - exit_comm
        
        # --- Gercek emir ---
        if self.order_manager:
            try:
                result = await asyncio.to_thread(
                    self.order_manager.partial_close_position,
                    symbol=symbol,
                    close_usdt=close_vol_usdt,
                    current_price=exit_price
                )
                if result.get("status") != "success":
                    print(f"[PARTIAL-TP] Emir hatasi {symbol}: {result}")
                    return None
            except Exception as e:
                print(f"[PARTIAL-TP] OrderManager hata {symbol}: {e}")
                return None
        
        # --- trade_history'e AYRI satir yaz ---
        exit_time = int(time.time())
        strategy_name = trade.get("strategy_name") or "UNKNOWN"
        dca_count = trade.get("dca_count") or 0
        leverage = trade.get("leverage") or 1
        
        conn = get_db_connection()
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
        conn.close()
        
        # --- active_trades guncelle ---
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
        conn.close()
        
        sign = "+" if net_pnl >= 0 else ""
        print(f"[PARTIAL-TP] {symbol} %{pt_percent:.0f} KAPATILDI | "
              f"Fiyat: {exit_price:.6f} | Kapatilan: {close_vol_usdt:.2f} USDT | "
              f"Kalan: {new_total_vol:.2f} USDT | "
              f"Net: {sign}{net_pnl:.4f} USDT")
        
        # --- Telegram ---
        try:
            cfg = load_config()
            tg_cfg = cfg.get("telegram", {})
            if tg_cfg.get("notify_closes", True):
                asyncio.create_task(telegram_notifier.notify_close(
                    symbol=symbol,
                    trade_type=trade_type,
                    entry_price=avg_price,
                    exit_price=exit_price,
                    pnl_pct=pnl_pct * 100,
                    net_pnl=net_pnl,
                    reason=reason,
                    dca_count=dca_count,
                ))
        except Exception as _e:
            print(f"[TG] Kismi TP bildirim hatasi: {_e}")
        
        return {
            "symbol": symbol,
            "closed_volume": close_vol_usdt,
            "remaining_volume": new_total_vol,
            "net_pnl": net_pnl,
            "pnl_pct": pnl_pct * 100,
        }
    
    async def _execute_close(self, symbol: str, exit_price: float, reason: str, force: bool = False):'''

if anchor in pm and '_execute_partial_close' not in pm:
    pm = pm.replace(anchor, new_method, 1)
    changes += 1
    print("[2/3] _execute_partial_close metodu eklendi")
else:
    print("[2/3] HATA: _execute_close cipa bulunamadi!")
    exit(1)

# ============================================================
# 2. DCA kontrolu: PT sonrasi keep_dca=0 ise DCA atla
# ============================================================
old_dca = '''            # 1. DCA kontrolü (trailing aktif değilse)
            state = self.trailing_state.get(position_key, {"active": False, "hwm": None})
            if not state.get("active"):
                dca_done = await self._check_dca(pos, current_price, params)'''

new_dca = '''            # 1. DCA kontrolü (trailing pasif + PT sonrasi keep_dca kontrolu)
            state = self.trailing_state.get(position_key, {"active": False, "hwm": None})
            
            pt_done_flag = pos.get("pt_done") or 0
            pt_keep_dca_flag = pos.get("pt_keep_dca")
            if pt_keep_dca_flag is None:
                pt_keep_dca_flag = 1
            skip_dca_after_pt = bool(pt_done_flag and not pt_keep_dca_flag)
            
            if not state.get("active") and not skip_dca_after_pt:
                dca_done = await self._check_dca(pos, current_price, params)'''

if old_dca in pm:
    pm = pm.replace(old_dca, new_dca, 1)
    changes += 1
    print("[2/3] DCA kontrolu guncellendi")
else:
    print("[2/3] UYARI: DCA kontrolu bulunamadi (atlandi)")

# ============================================================
# 3. Kismi TP tetikleme (trailing'den ONCE)
# ============================================================
old_trail = '''            # 3. Trailing state
            if position_key not in self.trailing_state:
                self.trailing_state[position_key] = {"active": False, "hwm": None}
            state = self.trailing_state[position_key]

            if not state["active"] and profit_pct >= tp_pct:
                state["active"] = True
                state["hwm"] = current_price
                print(f"[TTP] {symbol} Trailing AKTİF | Kâr: {profit_pct*100:.2f}% | HWM: {current_price:.6f}")'''

new_trail = '''            # ⚡ KISMİ TP KONTROLU (trailing'den ONCE)
            pt_enabled = pos.get("pt_enabled") or 0
            pt_done_flag = pos.get("pt_done") or 0
            pt_percent_val = pos.get("pt_percent")
            if pt_percent_val is None:
                pt_percent_val = 50
            
            if pt_enabled and not pt_done_flag and not state["active"] and profit_pct >= tp_pct:
                pt_close_vol = pos["total_vol"] * (pt_percent_val / 100.0)
                MIN_ORDER_USDT = 5.0
                
                if pt_close_vol < MIN_ORDER_USDT:
                    print(f"[PARTIAL-TP] {symbol} atlandi: kapatilacak cok kucuk "
                          f"({pt_close_vol:.2f} < {MIN_ORDER_USDT} USDT)")
                    try:
                        conn = get_db_connection()
                        conn.execute("UPDATE active_trades SET pt_done = 1 WHERE symbol = ?", (symbol,))
                        conn.commit()
                        conn.close()
                    except Exception as _e:
                        print(f"[PARTIAL-TP] pt_done guncelleme hatasi: {_e}")
                else:
                    reason = f"PARTIAL TP ({profit_pct*100:.2f}%)"
                    print(f"[PARTIAL-TP] {symbol} tetiklendi: %{pt_percent_val:.0f} "
                          f"({pt_close_vol:.2f} USDT) | Kar: {profit_pct*100:.2f}%")
                    
                    pt_result = await self._execute_partial_close(
                        symbol, current_price, pt_close_vol, pt_percent_val, reason
                    )
                    
                    if pt_result:
                        self.trailing_state[position_key] = {"active": False, "hwm": None}
                        print(f"[PARTIAL-TP] {symbol} trailing RESET | "
                              f"Kalan: {pt_result['remaining_volume']:.2f} USDT")
                    else:
                        print(f"[PARTIAL-TP] {symbol} basarisiz, sonraki tick tekrar denecek")
                    
                    continue
            
            # 3. Trailing state
            if position_key not in self.trailing_state:
                self.trailing_state[position_key] = {"active": False, "hwm": None}
            state = self.trailing_state[position_key]

            if not state["active"] and profit_pct >= tp_pct:
                state["active"] = True
                state["hwm"] = current_price
                print(f"[TTP] {symbol} Trailing AKTİF | Kâr: {profit_pct*100:.2f}% | HWM: {current_price:.6f}")'''

if old_trail in pm:
    pm = pm.replace(old_trail, new_trail, 1)
    changes += 1
    print("[3/3] Kismi TP tetikleme eklendi")
else:
    print("[3/3] HATA: Trailing state cipa bulunamadi!")
    exit(1)

with open(PM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(pm.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("Geri donmek icin:")
print(f"  Copy-Item {PM_SRC}.bak_partial_tp {PM_SRC} -Force")