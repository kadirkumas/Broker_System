import asyncio
import time
from backend.database import get_db_connection


class PositionManager:
    def __init__(self, client, order_manager=None):
        self.client = client
        self.order_manager = order_manager
        self.trailing_state = {}

    async def get_current_prices(self, symbols: list) -> dict:
        if not symbols:
            return {}
        try:
            tickers = await asyncio.to_thread(self.client.futures_ticker)
            prices = {}
            for t in tickers:
                sym = t.get("symbol")
                if sym in symbols:
                    price_val = t.get("price") or t.get("lastPrice")
                    if price_val is not None:
                        prices[sym] = float(price_val)
            return prices
        except Exception as e:
            print(f"[!] Fiyat çekilemedi: {e}")
            return {}

    def get_all_open_positions(self) -> list:
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM active_trades").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _get_strategy_params(self, strategy_name: str, strategies_config: dict) -> dict:
        defaults = {"takeProfit": 1.5, "trailing": 0.3, "stopLoss": 3.0,
                    "useDCA": False, "baseOrder": 10, "volMultiplier": 1.2, "steps": "1.5, 3, 5"}
        if strategy_name and strategy_name in strategies_config:
            cfg = strategies_config[strategy_name]
            return {
                "takeProfit": float(cfg.get("takeProfit", defaults["takeProfit"])),
                "trailing": float(cfg.get("trailing", defaults["trailing"])),
                "stopLoss": float(cfg.get("stopLoss", defaults["stopLoss"])),
                "useDCA": bool(cfg.get("useDCA", defaults["useDCA"])),
                "baseOrder": float(cfg.get("baseOrder", defaults["baseOrder"])),
                "volMultiplier": float(cfg.get("volMultiplier", defaults["volMultiplier"])),
                "steps": cfg.get("steps", defaults["steps"]),
            }
        return defaults

    # ------------------------------------------------------------------
    # DCA: Kademeli alım
    # ------------------------------------------------------------------
    async def _check_dca(self, pos: dict, current_price: float, sCfg: dict) -> bool:
        """Fiyat DCA kademesine düştüyse yeni alım yapar."""
        if not sCfg.get("useDCA"):
            return False

        steps_str = sCfg.get("steps", "1.5, 3, 5")
        try:
            steps = [float(s.strip()) for s in str(steps_str).split(",") if s.strip()]
        except Exception:
            return False

        dca_count = pos["dca_count"] or 0
        if dca_count >= len(steps):
            return False

        symbol = pos["symbol"]
        trade_type = pos["trade_type"]
        initial_price = pos.get("initial_price") or pos["avg_price"]
        base_order = sCfg.get("baseOrder", 10)
        vol_mult = sCfg.get("volMultiplier", 1.2)

        next_step_pct = steps[dca_count] / 100
        if trade_type == "BUY":
            trigger_price = initial_price * (1 - next_step_pct)
            hit = current_price <= trigger_price
        else:
            trigger_price = initial_price * (1 + next_step_pct)
            hit = current_price >= trigger_price

        if not hit:
            return False

        new_count = dca_count + 1
        step_vol = base_order * (vol_mult ** new_count)

        old_total_vol = pos["total_vol"]
        old_avg = pos["avg_price"]
        new_total_vol = old_total_vol + step_vol
        new_avg = ((old_avg * old_total_vol) + (current_price * step_vol)) / new_total_vol

        conn = get_db_connection()
        conn.execute(
            "UPDATE active_trades SET total_vol = ?, avg_price = ?, dca_count = ? WHERE symbol = ?",
            (new_total_vol, new_avg, new_count, symbol)
        )
        conn.commit()
        conn.close()

        print(f"[DCA] {symbol} Kademe {new_count}/{len(steps)} | "
              f"Fiyat: {current_price:.6f} | Tetik: {trigger_price:.6f} | "
              f"+{step_vol:.2f} USDT | Toplam: {new_total_vol:.2f} USDT | "
              f"Yeni Ort: {new_avg:.6f}")

        return True

    # ------------------------------------------------------------------
    # Pozisyon kapatma
    # ------------------------------------------------------------------
    async def _get_funding_fee(self, symbol: str, entry_time: int, exit_time: int) -> float:
        """
        Binance'ten bu pozisyon icin odenen/alinan funding ucretini ceker.
        Negatif = odenen (kârdan duser), Pozitif = alinan.
        """
        try:
            incomes = await asyncio.to_thread(
                self.client.futures_income_history,
                symbol=symbol,
                incomeType="FUNDING_FEE",
                startTime=entry_time * 1000,
                endTime=exit_time * 1000,
                limit=100
            )
            total = sum(float(inc.get("income", 0)) for inc in incomes)
            if total != 0:
                print(f"[FUNDING] {symbol}: {total:+.4f} USDT ({len(incomes)} kayit)")
            return total
        except Exception as e:
            print(f"[!] Funding cekilemedi {symbol}: {e}")
            return 0.0

    async def _execute_close(self, symbol: str, exit_price: float, reason: str, force: bool = False):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM active_trades WHERE symbol = ?", (symbol,)).fetchone()
        conn.close()
        if not row:
            return None

        trade = dict(row)

        # ⚡ VALIDASYON 1: Fiyat kontrolü (force=True ise atla)
        avg_price = trade["avg_price"]
        
        if not force:
            if not exit_price or exit_price <= 0:
                print(f"[!] Geçersiz exit fiyatı {symbol}: {exit_price} - kapatma iptal")
                return None
            if not avg_price or avg_price <= 0:
                print(f"[!] Geçersiz avg fiyat {symbol}: {avg_price} - kapatma iptal")
                return None

            ratio = exit_price / avg_price
            if ratio > 10 or ratio < 0.1:
                print(f"[!] Şüpheli fiyat oranı {symbol}: exit={exit_price:.8f} / avg={avg_price:.8f} = {ratio:.2f}x - kapatma iptal")
                return None
        else:
            if not exit_price or exit_price <= 0:
                exit_price = avg_price
                print(f"[FORCE] {symbol}: Geçersiz fiyat, avg_price kullanılıyor")

        if trade["trade_type"] == "BUY":
            pnl_pct = (exit_price - avg_price) / avg_price
        else:
            pnl_pct = (avg_price - exit_price) / avg_price

        # ⚡ GERCEK KOMISYON HESABI (taker/maker ayrimi)
        # Giris (MARKET): taker
        # DCA (LIMIT): maker
        # Cikis (MARKET/TP/SL): taker
        
        if self.order_manager and hasattr(self.order_manager, 'get_commission_rate'):
            comm_rates = self.order_manager.get_commission_rate(symbol)
        else:
            comm_rates = {"taker": 0.0004, "maker": 0.0002}
        
        taker_rate = comm_rates.get("taker", 0.0004)
        maker_rate = comm_rates.get("maker", 0.0002)
        
        total_vol = trade["total_vol"]
        initial_vol = trade.get("initial_vol") or total_vol
        dca_vol = max(0, total_vol - initial_vol)
        
        entry_comm = initial_vol * taker_rate
        dca_comm = dca_vol * maker_rate
        exit_comm = total_vol * taker_rate
        commission = entry_comm + dca_comm + exit_comm
        
        gross_pnl = trade["total_vol"] * pnl_pct
        
        # ⚡ Funding ucretini cek (Binance'ten)
        exit_time = int(time.time())
        funding_fee = await self._get_funding_fee(symbol, trade["entry_time"], exit_time)
        
        # net_pnl = brut - komisyon + funding
        # (funding negatifse duser, pozitifse ekler)
        net_pnl = gross_pnl - commission + funding_fee

        # ⚡ VALIDASYON 3-4: Sadece force=False için
        if not force:
            max_allowed = trade["total_vol"] * 2
            if abs(net_pnl) > max_allowed:
                print(f"[!] Anormal PNL {symbol}: {net_pnl:.4f} USDT (limit: ±{max_allowed:.2f}, vol: {trade['total_vol']:.2f}) - kapatma iptal")
                return None

            if pnl_pct < -1.0 or pnl_pct > 5.0:
                print(f"[!] Anormal PNL% {symbol}: {pnl_pct*100:.2f}% - kapatma iptal")
                return None

        strategy_name = trade.get("strategy_name") or "UNKNOWN"
        dca_count = trade.get("dca_count") or 0
        leverage = trade.get("leverage") or 1

        conn = get_db_connection()
        conn.execute(
            """INSERT INTO trade_history 
               (symbol, trade_type, total_vol, entry_price, exit_price, 
                pnl_amount, pnl_pct, entry_time, exit_time,
                strategy_name, dca_count, close_reason, leverage, funding_fee)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, trade["trade_type"], trade["total_vol"], avg_price,
             exit_price, net_pnl, pnl_pct * 100, trade["entry_time"], exit_time,
             strategy_name, dca_count, reason, leverage, funding_fee)
        )
        conn.commit()
        conn.close()

        if self.order_manager:
            try:
                await asyncio.to_thread(self.order_manager.close_position, symbol=symbol)
            except Exception as e:
                print(f"[!] OrderManager close hatası: {e}")

        sign = "+" if net_pnl >= 0 else ""
        dca_info = f" (DCA:{dca_count})" if dca_count > 0 else ""
        lev_info = f" [{leverage}x]" if leverage > 1 else ""
        print(f"[✓ KAPANIŞ] {symbol}{dca_info}{lev_info} | {reason} | Çıkış: {exit_price:.6f} | "
              f"Kâr: {sign}{pnl_pct*100:.2f}% | Kom: -{commission:.4f} | Net: {sign}{net_pnl:.4f} USDT")

        return {
            "symbol": symbol,
            "exit_price": exit_price,
            "pnl_pct": pnl_pct * 100,
            "net_pnl": net_pnl,
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # Ana döngü
    # ------------------------------------------------------------------
    async def monitor_positions(self, strategies_config: dict):
        positions = self.get_all_open_positions()
        if not positions:
            return

        symbols = [p["symbol"] for p in positions]
        prices = await self.get_current_prices(symbols)
        if not prices:
            return

        for pos in positions:
            symbol = pos["symbol"]
            if symbol not in prices:
                continue

            current_price = prices[symbol]
            entry_price = pos["avg_price"]
            trade_type = pos["trade_type"]
            position_key = symbol

            strategy_name = pos.get("strategy_name") or "RSI_SCALPER"
            params = self._get_strategy_params(strategy_name, strategies_config)

            tp_pct = params["takeProfit"] / 100
            trailing_pct = params["trailing"] / 100
            sl_pct = params["stopLoss"] / 100

            if trade_type == "BUY":
                profit_pct = (current_price - entry_price) / entry_price
            else:
                profit_pct = (entry_price - current_price) / entry_price

            # 1. DCA kontrolü (trailing aktif değilse)
            state = self.trailing_state.get(position_key, {"active": False, "hwm": None})
            if not state.get("active"):
                dca_done = await self._check_dca(pos, current_price, params)
                if dca_done:
                    positions_after = self.get_all_open_positions()
                    pos = next((p for p in positions_after if p["symbol"] == symbol), None)
                    if not pos:
                        continue
                    entry_price = pos["avg_price"]
                    if trade_type == "BUY":
                        profit_pct = (current_price - entry_price) / entry_price
                    else:
                        profit_pct = (entry_price - current_price) / entry_price

            # 2. Stop Loss
            if profit_pct <= -sl_pct:
                await self._execute_close(symbol, current_price,
                                          f"STOP LOSS ({profit_pct*100:.2f}%)")
                self.trailing_state.pop(position_key, None)
                continue

            # 3. Trailing state
            if position_key not in self.trailing_state:
                self.trailing_state[position_key] = {"active": False, "hwm": None}
            state = self.trailing_state[position_key]

            if not state["active"] and profit_pct >= tp_pct:
                state["active"] = True
                state["hwm"] = current_price
                print(f"[TTP] {symbol} Trailing AKTİF | Kâr: {profit_pct*100:.2f}% | HWM: {current_price:.6f}")

            # 4. Trailing aktifse kapanış kontrolü
            if state["active"]:
                if trade_type == "BUY":
                    if current_price > state["hwm"]:
                        state["hwm"] = current_price
                    trigger = state["hwm"] * (1 - trailing_pct)
                    if current_price <= trigger:
                        await self._execute_close(symbol, current_price,
                                                  f"TRAILING ({profit_pct*100:.2f}%)")
                        self.trailing_state.pop(position_key, None)
                else:
                    if current_price < state["hwm"]:
                        state["hwm"] = current_price
                    trigger = state["hwm"] * (1 + trailing_pct)
                    if current_price >= trigger:
                        await self._execute_close(symbol, current_price,
                                                  f"TRAILING ({profit_pct*100:.2f}%)")
                        self.trailing_state.pop(position_key, None)