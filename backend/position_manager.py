import asyncio
import time
import json
from backend.database import get_db_connection
from backend import telegram_notifier
from backend.strategy_engine import load_config


class PositionManager:
    def __init__(self, client, order_manager=None):
        self.client = client
        self.order_manager = order_manager
        self.trailing_state = {}
        self._closing_locks = {}

    # ------------------------------------------------------------------
    # AI TTP - Kademeli Trailing Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_trailing_steps(steps_str):
        """
        "1.5:0.3, 2.5:0.2" -> [(1.5, 0.3), (2.5, 0.2)]
        """
        if not steps_str:
            return []
        result = []
        for pair in str(steps_str).split(","):
            pair = pair.strip()
            if not pair or ":" not in pair:
                continue
            try:
                k, v = pair.split(":", 1)
                kf = float(k.strip())
                vf = float(v.strip())
                if kf >= 0 and vf > 0:
                    result.append((kf, vf))
            except Exception:
                pass
        result.sort(key=lambda x: x[0])
        return result

    def _get_ai_ttp_pct(self, steps, profit_pct, state):
        """
        Ratchet (geri donmez) kademeli trail yuzdesi.
        profit_pct: 0.025 = %2.5 kar
        doner: 0.002 = %0.2 trail
        """
        if not steps:
            return state.get("trail_pct") or 0.003

        best = state.get("trail_pct")
        for k_pct, t_pct in steps:
            if profit_pct >= k_pct / 100.0:
                cand = t_pct / 100.0
                if best is None or cand < best:
                    best = cand
            else:
                break
        if best is None:
            best = steps[0][1] / 100.0
        state["trail_pct"] = best
        return best

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
        defaults = {"takeProfit": 1.5, "trailing": 0.3,
                    "trailingSteps": "1.5:0.3, 2.5:0.2, 4:0.12, 6:0.07, 10:0.03",
                    "stopLoss": 3.0,
                    "useDCA": False, "baseOrder": 10, "volMultiplier": 1.2, "steps": "1.5, 3, 5",
                    "dcaMinDistancePct": 5.0, "dcaMinTimeMin": 15,
                    # FIX F100: eksik alanlar
                    "dcaDynamic": False,
                    "dcaAtrMultiplier": 2.0,
                    "dcaMinStep": 4.0,
                    "dcaMaxSteps": 3,
                    "dcaMomentumFactor": 2.0,
                    "dcaVolMultiplier": 1.3,
                    "dcaStepScale": 1.5,  # F333: Adim Carpani
                    "interval": "15m"}
        if strategy_name and strategy_name in strategies_config:
            cfg = strategies_config[strategy_name]
            return {
            "maxHoldHours": (strategies_config.get(strategy_name, {}) or {}).get("maxHoldHours", 72),
                "takeProfit": float(cfg.get("takeProfit", defaults["takeProfit"])),
                "trailing": float(cfg.get("trailing", defaults["trailing"])),
                "trailingSteps": cfg.get("trailingSteps", defaults["trailingSteps"]),
                "stopLoss": float(cfg.get("stopLoss", defaults["stopLoss"])),
                "useDCA": bool(cfg.get("useDCA", defaults["useDCA"])),
                "baseOrder": float(cfg.get("baseOrder", defaults["baseOrder"])),
                "volMultiplier": float(cfg.get("volMultiplier", defaults["volMultiplier"])),
                "steps": cfg.get("steps", defaults["steps"]),
                "dcaMinDistancePct": float(cfg.get("dcaMinDistancePct", defaults["dcaMinDistancePct"])),
                "dcaMinTimeMin": int(cfg.get("dcaMinTimeMin", defaults["dcaMinTimeMin"])),
                # FIX F100: eksik alanlar
                "dcaDynamic": bool(cfg.get("dcaDynamic", defaults["dcaDynamic"])),
                "dcaAtrMultiplier": float(cfg.get("dcaAtrMultiplier", defaults["dcaAtrMultiplier"])),
                "dcaMinStep": float(cfg.get("dcaMinStep", defaults["dcaMinStep"])),
                "dcaMaxSteps": int(cfg.get("dcaMaxSteps", defaults["dcaMaxSteps"])),
                "dcaMomentumFactor": float(cfg.get("dcaMomentumFactor", defaults["dcaMomentumFactor"])),
                "dcaVolMultiplier": float(cfg.get("dcaVolMultiplier", defaults["dcaVolMultiplier"])),
                "dcaStepScale": float(cfg.get("dcaStepScale", defaults["dcaStepScale"])),
                "interval": str(cfg.get("interval", defaults["interval"])),
            }
        return defaults

    # ------------------------------------------------------------------
    # F68: Dinamik DCA helpers (dcaDynamic flag kullanan stratejiler icin)
    # ------------------------------------------------------------------
    _atr_pct_cache = {}   # {symbol_interval: (atr_pct, ts)}
    _mom_cache = {}       # {symbol_interval: (momentum, ts)}
    _dip_cache = {}       # {symbol_interval: (dip_position, ts)}

    async def _get_atr_pct_for_symbol(self, symbol: str, ttl_sec: int = 60, interval: str = "15m") -> float:
        """Son 30 mumun ATR%'sini hesaplar. Cache 60 sn (interval bazli)."""
        import time as _t
        now = _t.time()
        cache_key = "%s_%s" % (symbol, interval)
        cached = self.__class__._atr_pct_cache.get(cache_key)
        if cached and (now - cached[1]) < ttl_sec:
            return cached[0]

        try:
            klines = await asyncio.to_thread(
                self.client.futures_klines,
                symbol=symbol, interval=interval, limit=30
            )
            if not klines or len(klines) < 15:
                return 1.5

            trs = []
            prev_close = float(klines[0][4])
            for k in klines[1:]:
                h = float(k[2]); l = float(k[3]); c = float(k[4])
                tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
                trs.append(tr)
                prev_close = c

            if len(trs) < 14:
                return 1.5

            atr = sum(trs[:14]) / 14
            for i in range(14, len(trs)):
                atr = (atr * 13 + trs[i]) / 14

            current_price = float(klines[-1][4])
            atr_pct = (atr / current_price * 100) if current_price > 0 else 1.5

            self.__class__._atr_pct_cache[cache_key] = (atr_pct, now)
            return atr_pct
        except Exception as e:
            print(f"[DCA-DYN] ATR hata {symbol}: {str(e)[:80]}")
            return 1.5

    async def _get_momentum_for_symbol(self, symbol: str, ttl_sec: int = 60, interval: str = "15m") -> float:
        """Son 5 mumun ortalama dusus hizi (%/mum). Cache 60 sn (interval bazli)."""
        import time as _t
        now = _t.time()
        cache_key = "%s_%s" % (symbol, interval)
        cached = self.__class__._mom_cache.get(cache_key)
        if cached and (now - cached[1]) < ttl_sec:
            return cached[0]

        try:
            klines = await asyncio.to_thread(
                self.client.futures_klines,
                symbol=symbol, interval=interval, limit=10
            )
            if not klines or len(klines) < 6:
                return 0.0

            closes = [float(k[4]) for k in klines]
            drops = []
            for i in range(-5, 0):
                change = (closes[i] - closes[i-1]) / closes[i-1] * 100
                if change < 0:
                    drops.append(abs(change))

            momentum = sum(drops) / len(drops) if drops else 0.0
            self.__class__._mom_cache[cache_key] = (momentum, now)
            return momentum
        except Exception as e:
            print(f"[DCA-DYN] Mom hata {symbol}: {str(e)[:80]}")
            return 0.0

    # ------------------------------------------------------------------
    # F83: Dip algilama
    # ------------------------------------------------------------------
    async def _get_dip_position(self, symbol: str, interval: str = "15m", ttl_sec: int = 60) -> float:
        """
        Fiyatin son 20 mumun range'indeki pozisyonu.
        0.0 = dipte (en dusuk), 1.0 = tepede (en yuksek).
        Cache 60 sn.
        """
        import time as _t
        now = _t.time()
        cache_key = "%s_%s" % (symbol, interval)
        cached = self.__class__._dip_cache.get(cache_key)
        if cached and (now - cached[1]) < ttl_sec:
            return cached[0]

        try:
            klines = await asyncio.to_thread(
                self.client.futures_klines,
                symbol=symbol, interval=interval, limit=25
            )
            if not klines or len(klines) < 20:
                return 0.5

            highs = [float(k[2]) for k in klines[-20:]]
            lows = [float(k[3]) for k in klines[-20:]]
            cur = float(klines[-1][4])

            hi = max(highs)
            lo = min(lows)
            rng = hi - lo
            if rng <= 0:
                return 0.5

            pos = (cur - lo) / rng
            pos = max(0.0, min(1.0, pos))
            self.__class__._dip_cache[cache_key] = (pos, now)
            return pos
        except Exception as e:
            print(f"[DCA-DIP] hata {symbol}: {str(e)[:80]}")
            return 0.5

    # ------------------------------------------------------------------
    # DCA: Kademeli alım
    # ------------------------------------------------------------------
    async def _check_dca(self, pos: dict, current_price: float, sCfg: dict) -> bool:
        """Fiyat DCA kademesine düştüyse yeni alım yapar."""
        # FIX F96: dcaDynamic tek basina da yeterli
        if not sCfg.get("useDCA") and not sCfg.get("dcaDynamic"):
            return False

        steps_str = sCfg.get("steps", "1.5, 3, 5")
        try:
            steps = [float(s.strip()) for s in str(steps_str).split(",") if s.strip()]
        except Exception:
            return False

        dca_count = pos["dca_count"] or 0
        # F157b: Dinamik modda max 7 kademe, statik modda len(steps)
        _dyn_cap_f157b = bool(sCfg.get("dcaDynamic", False))
        _max_dca_f157b = 7 if _dyn_cap_f157b else len(steps)
        if dca_count >= _max_dca_f157b:
            if _dyn_cap_f157b:
                print(f"[F157b-MAX] {symbol} maks kademe {_max_dca_f157b} (dinamik), dur")
            return False
            return False

        # FIX B6: margin_presets.dcaMaxSteps global kontrolu
        try:
            _cfg_b6 = load_config()
            _mode_b6 = _cfg_b6.get("margin_mode", "cross")
            _presets_b6 = _cfg_b6.get("margin_presets", {}) or {}
            _preset_b6 = _presets_b6.get(_mode_b6, {}) or {}
            _max_dca_b6 = _preset_b6.get("dcaMaxSteps")
            if _max_dca_b6 is not None:
                _max_dca_b6 = int(_max_dca_b6)
                if dca_count >= _max_dca_b6:
                    _sym_b6 = pos.get("symbol", "?")
                    print(f"[DCA-PRESET] {_sym_b6} mod={_mode_b6} "
                          f"kademe={dca_count}/{_max_dca_b6} limit -> yeni DCA atlandi")
                    return False
        except Exception as _e_b6:
            print(f"[DCA-PRESET] preset kontrol hatasi: {_e_b6}")

        symbol = pos["symbol"]
        trade_type = pos["trade_type"]
        initial_price = pos.get("initial_price") or pos["avg_price"]
        base_order = sCfg.get("baseOrder", 10)
        vol_mult = sCfg.get("volMultiplier", 1.2)

        # F153: Dinamik mod ise statik steps[] listesini ATLA
        #   - dcaDynamic=True  -> sadece dcaMinDistancePct alt kapi
        #   - dcaDynamic=False -> eski davranis (steps[dca_count])
        _dyn_early_f153 = bool(sCfg.get("dcaDynamic", False))
        if _dyn_early_f153:
            _min_dist_cfg_f153 = float(sCfg.get("dcaMinDistancePct", 2.0))
            _step_scale = float(sCfg.get("dcaStepScale", 1.5))
            
            # F333: Bilesik Adim Carpani (Her kademede mesafe artar)
            _effective_step_pct = _min_dist_cfg_f153 * (_step_scale ** dca_count)
            next_step_pct = _effective_step_pct / 100.0
            
            print(f"[F333-DYN] {symbol} dinamik mod | adim carpani={_step_scale} | kademe={dca_count} | mesafe=%{_effective_step_pct:.2f}")
        else:
            next_step_pct = steps[dca_count] / 100

        # F159: Artimsal DCA - base = son DCA (varsa), yoksa initial_price
        _f159_base = initial_price
        try:
            import json as _json_f159
            _dh_f159 = pos.get("dca_history") or "[]"
            _hist_f159 = _json_f159.loads(_dh_f159) if isinstance(_dh_f159, str) else _dh_f159
            if _hist_f159 and len(_hist_f159) > 0:
                _last_dca_f159 = float(_hist_f159[-1].get("price", 0))
                if _last_dca_f159 > 0:
                    _f159_base = _last_dca_f159
        except Exception:
            pass
        if trade_type == "BUY":
            trigger_price = _f159_base * (1 - next_step_pct)
            hit = current_price <= trigger_price
        else:
            trigger_price = _f159_base * (1 + next_step_pct)
            hit = current_price >= trigger_price

        if not hit:
            return False

        # ⚡ DCA HIBRIT KORUMA
        # 1) Sira: fiyat son DCA'dan dogru yonde olmali
        # 2) Mesafe < %2 -> ATLA
        # 3) Mesafe %2-%5 ve sure <5dk -> ATLA
        # 4) Mesafe >%5 -> HEMEN AC (pump/dump istisnasi)
        try:
            import json as _json
            import time as _time
            _dh = pos.get("dca_history") or "[]"
            if isinstance(_dh, str):
                _history = _json.loads(_dh)
            else:
                _history = _dh
            if _history and len(_history) > 0:
                _last_dca_price = float(_history[-1].get("price", 0))
                _last_dca_time = int(_history[-1].get("time", 0))
                if _last_dca_price > 0:
                    # 1) SIRA: fiyat son DCA'dan dogru yonde mi?
                    if trade_type == "BUY" and current_price >= _last_dca_price:
                        return False
                    if trade_type == "SELL" and current_price <= _last_dca_price:
                        return False

                    # 2) MESAFE HESABI
                    if trade_type == "BUY":
                        _diff_pct = (_last_dca_price - current_price) / _last_dca_price * 100
                    else:
                        _diff_pct = (current_price - _last_dca_price) / _last_dca_price * 100

                    # F59: config'den parametreler
                    _min_dist = float(sCfg.get("dcaMinDistancePct", 5.0))
                    _min_time_min = int(sCfg.get("dcaMinTimeMin", 15))
                    _min_time = _min_time_min * 60

                    # F83: dcaDynamic flag aktif olan stratejiler icin dinamik hesap
                    _dyn = bool(sCfg.get("dcaDynamic", False))

                    if _dyn:
                        try:
                            # --- 1) Strateji intervalinden ATR/momentum cek ---
                            _strat_interval = str(sCfg.get("interval", "15m"))

                            _atr_pct = await self._get_atr_pct_for_symbol(symbol, interval=_strat_interval)
                            _momentum = await self._get_momentum_for_symbol(symbol, interval=_strat_interval)
                            _dip = await self._get_dip_position(symbol, interval=_strat_interval)

                            # --- 2) Parametreler ---
                            _atr_mult = float(sCfg.get("dcaAtrMultiplier", 2.0))
                            _dca_base = float(sCfg.get("dcaMinStep", 4))

                            # F157: Dinamik max kademe (min 4, piyasa dustukce 5-6-7)
                            _cfg_max_steps_f157 = int(sCfg.get("dcaMaxSteps", 4))
                            _min_steps_f157 = max(4, _cfg_max_steps_f157)  # asla 4'un alti

                            if initial_price > 0:
                                _dd_pct_f157 = abs((current_price - initial_price) / initial_price) * 100
                            else:
                                _dd_pct_f157 = 0.0

                            if _dd_pct_f157 >= 50:
                                _dyn_max_f157 = 7
                            elif _dd_pct_f157 >= 35:
                                _dyn_max_f157 = 6
                            elif _dd_pct_f157 >= 20:
                                _dyn_max_f157 = 5
                            else:
                                _dyn_max_f157 = 4

                            _max_steps = max(_min_steps_f157, _dyn_max_f157)
                            _step_idx = dca_count + 1

                            print(f"[F157-MAX] {symbol} dd={_dd_pct_f157:.2f}% | "
                                  f"max_kademe={_max_steps} (min={_min_steps_f157})")

                            # dcaMaxSteps limiti
                            if _step_idx > _max_steps:
                                print(f"[DCA-MAX] {symbol} kademe {_step_idx} > max {_max_steps}, atlandi")
                                return False

                            # --- 3) Baz adim: ATR x carpan x kademe ---
                            _atr_step = _atr_pct * _atr_mult * _step_idx
                            _dyn_step = _dca_base + (_step_idx - 1) * (_dca_base * 0.5)
                            _final_step = max(_min_dist, _dyn_step, _atr_step)

                            # --- 4) Dip algilama ---
                            # Dip pozisyonu: 0=dip, 1=tepe
                            # Dipteyse: adim kucul (yaklastir)
                            # Tepedeyse: adim buyut (uzaklastir)
                            if _dip < 0.25:
                                _dip_mult = 0.75  # dipte -> %25 daha yakin
                                _dip_label = "DIP"
                            elif _dip > 0.75:
                                _dip_mult = 1.30  # tepede -> %30 daha uzak
                                _dip_label = "TEPE"
                            else:
                                _dip_mult = 1.0
                                _dip_label = "ORTA"

                            _final_step = _final_step * _dip_mult

                            # --- 5) LIQ KORUMASI (KRITIK) ---
                            _lev = max(1, int(pos.get("leverage") or 1))
                            # 3x -> LIQ ~%33, 5x -> ~%20
                            _liq_pct = (100.0 / _lev) - 1.0  # 1% emniyet payi
                            _liq_safe = _liq_pct * 0.7  # %70 emniyetli kullanim

                            # Kümülatif: DCA1 + DCA2 + DCA3 ... toplamı
                            _cumulative = 0.0
                            for k in range(1, _step_idx + 1):
                                _k_step = max(_min_dist, _dca_base + (k - 1) * (_dca_base * 0.5),
                                              _atr_pct * _atr_mult * k) * _dip_mult
                                _cumulative += _k_step

                            if _cumulative > _liq_safe:
                                # Kırp
                                _scale = _liq_safe / _cumulative
                                _final_step = _final_step * _scale
                                print(f"[DCA-LIQ-GUARD] {symbol} step kirpildi x{_scale:.2f} "
                                      f"(cum %{_cumulative:.1f} > safe %{_liq_safe:.1f})")

                            # --- 6) Dinamik zaman ---
                            _mom_factor = float(sCfg.get("dcaMomentumFactor", 2.0))
                            _dyn_time_min = max(_min_time_min,
                                                _min_time_min + int(_momentum * _mom_factor))
                            # Dipteyse daha kisa bekle, tepedeyse daha uzun
                            _dyn_time_min = int(_dyn_time_min * (0.5 if _dip < 0.25 else (1.5 if _dip > 0.75 else 1.0)))
                            _dyn_time = _dyn_time_min * 60

                            print(f"[DCA-DYN] {symbol} kademe {_step_idx}/{_max_steps} | "
                                  f"atr%={_atr_pct:.2f} mom={_momentum:.2f} dip={_dip:.2f}({_dip_label}) | "
                                  f"step=%{_final_step:.2f} time={_dyn_time_min}dk "
                                  f"(min=%{_min_dist:.1f} statik)")

                            _min_dist = _final_step
                            # F171: SL icin cache
                            if not hasattr(self, "_dca_last_step"):
                                self._dca_last_step = {}
                            self._dca_last_step[symbol] = float(_final_step)
                            _min_time = _dyn_time
                            _min_time_min = _dyn_time_min
                        except Exception as _de:
                            print(f"[DCA-DYN] {symbol} hata, statik kullaniyor: {_de}")

                    # 3) MESAFE KONTROLU
                    if _diff_pct < _min_dist:
                        # FIX SP2: 5 dk'da 1 log
                        import time as _t_sp2
                        _now_sp2 = _t_sp2.time()
                        if not hasattr(self, "_dca_skip_log"):
                            self._dca_skip_log = {}
                        _last = self._dca_skip_log.get(symbol, 0)
                        if _now_sp2 - _last >= 300:
                            self._dca_skip_log[symbol] = _now_sp2
                            print(f"[DCA-SKIP] {symbol} mesafe yetersiz: %{_diff_pct:.3f} < %{_min_dist:.2f}")
                        return False

                    # 4) SURE KONTROLU
                    if _last_dca_time > 0:
                        _age = int(_time.time()) - _last_dca_time
                        if _age < _min_time:
                            _rem = _min_time - _age
                            # FIX SP2: 5 dk'da 1 log
                            import time as _t_sp2b
                            _now_sp2b = _t_sp2b.time()
                            if not hasattr(self, "_dca_skip_time_log"):
                                self._dca_skip_time_log = {}
                            _last_b = self._dca_skip_time_log.get(symbol, 0)
                            if _now_sp2b - _last_b >= 300:
                                self._dca_skip_time_log[symbol] = _now_sp2b
                                print(f"[DCA-SKIP] {symbol} sure yetersiz: {_age}sn < {_min_time}sn "
                                      f"(kalan: {_rem}sn, mesafe %{_diff_pct:.2f})")
                            return False

                    _age_disp = _age if _last_dca_time > 0 else 0
                    print(f"[DCA-OK] {symbol} mesafe %{_diff_pct:.2f} sure {_age_disp}sn "
                          f"(min mesafe %{_min_dist:.2f}, min sure {_min_time_min}dk)")
        except Exception as _e:
            print(f"[DCA-ORDER] history parse hatasi: {_e}")

        new_count = dca_count + 1
        step_vol = base_order * (vol_mult ** new_count)

        # ============================================================
        # F142: BINANCE'E GERCEK DCA EMRI GONDER
        # ============================================================
        # KRITIK: Emir basarisiz olursa DB guncellenmez
        _dca_exec_price = None
        _dca_exec_vol = None
        if self.order_manager and not getattr(self.order_manager, 'test_mode', False):
            try:
                import asyncio as _aio_dca
                # 1) Anlik fiyat
                _ticker_dca = await _aio_dca.to_thread(
                    self.order_manager.client.futures_symbol_ticker, symbol=symbol
                )
                _live_price = float(_ticker_dca['price'])
                if _live_price <= 0:
                    print(f"[DCA-EXEC] {symbol} gecersiz fiyat, DCA atlandi")
                    return False
                
                # 2) Precision ve qty
                _, _qty_prec = self.order_manager.get_symbol_precision(symbol)
                _qty = round(step_vol / _live_price, _qty_prec)
                if _qty <= 0:
                    print(f"[DCA-EXEC] {symbol} qty=0 (step_vol={step_vol}, price={_live_price}), atlandi")
                    return False

                # F218a - MinNotional (Dust) Kalkani
                _min_notional = 5.0
                _calc_notional = _qty * _live_price
                if _calc_notional < _min_notional:
                    print(f"[DCA-SKIP] {symbol} DCA iptal: Hesaplanan tutar {_calc_notional:.2f} USDT < MinNotional {_min_notional} USDT")
                    return False
                
                # 3) Emir yonu: pozisyon yonu ile AYNI (DCA ek alim)
                _dca_side = trade_type  # BUY pozisyon -> BUY DCA, SELL pozisyon -> SELL DCA
                
                # 4) MARKET emri gonder
                print(f"[DCA-EXEC] {symbol} DCA#{new_count} MARKET {_dca_side} qty={_qty} (beklenen ~{step_vol} USDT)")
                _order = await _aio_dca.to_thread(
                    self.order_manager.client.futures_create_order,
                    symbol=symbol,
                    side=_dca_side,
                    type="MARKET",
                    quantity=_qty
                )
                
                _oid = _order.get('orderId')
                if not _oid:
                    print(f"[DCA-EXEC] {symbol} emir reddedildi: {_order}")
                    return False
                
                # 5) Gercek fill fiyatini al
                try:
                    import time as _t_dca
                    _t_dca.sleep(0.3)
                    _detail = await _aio_dca.to_thread(
                        self.order_manager.client.futures_get_order,
                        symbol=symbol, orderId=_oid
                    )
                    _dca_exec_price = float(_detail.get('avgPrice') or _detail.get('price') or _live_price)
                    _exec_qty = float(_detail.get('executedQty') or _qty)
                    _dca_exec_vol = _exec_qty * _dca_exec_price
                    print(f"[DCA-EXEC] {symbol} FILL @ {_dca_exec_price} | qty={_exec_qty} | hacim={_dca_exec_vol:.4f} USDT")
                except Exception as _fe:
                    _dca_exec_price = _live_price
                    _dca_exec_vol = _qty * _live_price
                    print(f"[DCA-EXEC] {symbol} fill okunamadi, yaklasik: {_dca_exec_vol:.4f} USDT | {str(_fe)[:60]}")
                
            except Exception as _de:
                print(f"[DCA-EXEC] {symbol} HATA: {str(_de)[:150]}")
                return False
        else:
            # Test modu -> simule
            _dca_exec_price = current_price
            _dca_exec_vol = step_vol
            print(f"[DCA-EXEC] {symbol} TEST modu DCA#{new_count} | {step_vol} USDT")

        # ============================================================
        # 6) DB GUNCELLE (emir basarili ise)
        # ============================================================
        # Gercek exec fiyati/hacmi kullan
        _use_vol = _dca_exec_vol if _dca_exec_vol and _dca_exec_vol > 0 else step_vol
        _use_price = _dca_exec_price if _dca_exec_price and _dca_exec_price > 0 else current_price

        old_total_vol = pos["total_vol"]
        old_avg = pos["avg_price"]
        new_total_vol = old_total_vol + _use_vol
        # F150: QTY-agirlikli ortalama (vol-agirlikli DEGIL)
        # vol = qty * price oldugundan, vol ile qty ters iliskili.
        # Dogru formül:  toplam_vol / toplam_qty
        _old_qty_f150 = (old_total_vol / old_avg) if old_avg > 0 else 0
        _new_qty_f150 = (_use_vol / _use_price) if _use_price > 0 else 0
        _tot_qty_f150 = _old_qty_f150 + _new_qty_f150
        if _tot_qty_f150 > 0:
            new_avg = new_total_vol / _tot_qty_f150
        else:
            new_avg = ((old_avg * old_total_vol) + (_use_price * _use_vol)) / new_total_vol  # fallback

        # ⚡ DCA history kaydı (zaman + fiyat + kademe)
        try:
            old_history = json.loads(pos.get("dca_history") or "[]")
        except Exception:
            old_history = []

        old_history.append({
            "time": int(time.time()),
            "price": float(_use_price),  # F142: gercek fill fiyati
            "step": int(new_count),
            "vol": float(_use_vol),       # F142: gercek hacim
            "avg_after": float(new_avg),
        })

        # F41: DCA runtime debug (initial_price korunuyor mu?)
        try:
            print(f"[DCA-DEBUG-BEFORE] {symbol} DCA#{new_count}")
            print(f"  input   : initial_price={initial_price:.8f} avg_before={old_avg:.8f} current={current_price:.8f}")
            print(f"  output  : new_avg={new_avg:.8f} new_total_vol={new_total_vol:.2f} dca_count={new_count}")
        except Exception:
            pass

        conn = get_db_connection()
        conn.execute(
            "UPDATE active_trades SET total_vol = ?, avg_price = ?, dca_count = ?, dca_history = ? WHERE symbol = ?",
            (new_total_vol, new_avg, new_count, json.dumps(old_history), symbol)
        )
        conn.commit()
        conn.close()

        # F41: SQL sonrasi DB'den oku (initial_price korunuyor mu?)
        try:
            _chk = get_db_connection()
            _r = _chk.execute(
                "SELECT initial_price, avg_price, total_vol, dca_count FROM active_trades WHERE symbol = ?",
                (symbol,)
            ).fetchone()
            _chk.close()
            if _r:
                print(f"[DCA-DEBUG-AFTER] {symbol}")
                print(f"  db_after: initial_price={_r[0]:.8f} avg_price={_r[1]:.8f} total_vol={_r[2]:.2f} dca_count={_r[3]}")
                if abs(_r[0] - _r[1]) < 1e-8:
                    print(f"  !!! UYARI: initial_price == avg_price (bug gostergesi)")
        except Exception as _e:
            print(f"[DCA-DEBUG-AFTER] hata: {_e}")

        print(f"[DCA-LOG] {symbol} kademe {new_count} -> dca_history: {len(old_history)} kayit")

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

    def _reset_stuck_pt_flags(self):
        """
        Test modunda yanlislikla pt_done=1 yapilmis ama pt_volume=0 olan
        kayitlari geri al (atlanmis kismi TP'ler tekrar denenebilsin).
        """
        try:
            _is_test = bool(getattr(self.order_manager, 'test_mode', False)) if self.order_manager else False
            if not _is_test:
                return
            conn = get_db_connection()
            cur = conn.execute(
                "UPDATE active_trades SET pt_done = 0 WHERE pt_done = 1 AND (pt_volume IS NULL OR pt_volume = 0)"
            )
            cnt = cur.rowcount
            conn.commit()
            conn.close()
            if cnt > 0:
                print(f"[PARTIAL-TP] {cnt} stuck pt_done=0 olarak sifirlandi (test modu)")
        except Exception as e:
            print(f"[PARTIAL-TP] Reset hatasi: {e}")

    async def _execute_partial_close(self, symbol: str, exit_price: float, close_vol_usdt: float,
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
        # ⚡ DEBUG: DB'den okunan trade ile gelen parametreleri karsilastir
        print(f"[PT-DEBUG-EXEC] {symbol} | close_vol_usdt={close_vol_usdt} | "
              f"trade.total_vol={trade['total_vol']} | trade.initial_vol={trade.get('initial_vol')} | "
              f"trade.avg_price={trade['avg_price']} | pt_percent={pt_percent}")
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
            # F91: BIR KEZ reddet ve PT'yi iptal et (spam engelle)
            print(f"[PARTIAL-TP] Supheli oran {symbol}: {ratio:.4f} -> PT IPTAL")
            try:
                conn = get_db_connection()
                conn.execute(
                    "UPDATE active_trades SET pt_done = 1, pt_enabled = 0 WHERE symbol = ?",
                    (symbol,)
                )
                conn.commit()
                conn.close()
            except Exception as _e:
                print(f"[PARTIAL-TP] PT iptal DB hatasi: {_e}")
            return None
        
        if close_vol_usdt <= 0 or close_vol_usdt >= trade["total_vol"]:
            print(f"[PARTIAL-TP] Gecersiz hacim {symbol}: {close_vol_usdt} / {trade['total_vol']}")
            return None
        
        # FIX F97: ONCE kapat, gercek fill al
        if self.order_manager:
            try:
                result_f97 = await asyncio.to_thread(
                    self.order_manager.partial_close_position,
                    symbol=symbol,
                    close_usdt=close_vol_usdt,
                    current_price=exit_price
                )
                if result_f97.get("status") != "success":
                    print(f"[F97] {symbol} partial close hatasi: {result_f97}")
                    # F126: Pozisyon Binance'te yoksa DB'den sil (kök çözüm)
                    _msg = str(result_f97.get("message", "")).lower()
                    # F274: -2022 ReduceOnly hatasi da pozisyonun olmadigini gosterir
                    if "bulunamadi" in _msg or "not found" in _msg or "does not exist" in _msg or "-2022" in _msg or "reduceonly" in _msg:
                        print(f"[F126] {symbol} Binance'te yok! DB temizleniyor...")
                        try:
                            _c = get_db_connection()
                            # F136+F138: once history'ye yaz (GERCEK exit_price ile)
                            try:
                                import time as _t_f136b
                                _now_f136b = int(_t_f136b.time())
                                _row_f136b = _c.execute("SELECT * FROM active_trades WHERE symbol = ?", (symbol,)).fetchone()
                                if _row_f136b:
                                    _p = dict(_row_f136b)
                                    _avg_f = float(_p.get("avg_price") or 0)
                                    _vol_f = float(_p.get("total_vol") or 0)
                                    _tt_f = _p.get("trade_type", "BUY")
                                    
                                    # F138: gercek exit_price - parametre olarak gelen exit_price
                                    _exit_real_f138 = float(exit_price) if exit_price and exit_price > 0 else _avg_f
                                    
                                    # F138: PnL hesabi
                                    if _avg_f > 0:
                                        if _tt_f == "BUY":
                                            _pnl_pct_f138 = (_exit_real_f138 - _avg_f) / _avg_f
                                        else:
                                            _pnl_pct_f138 = (_avg_f - _exit_real_f138) / _avg_f
                                    else:
                                        _pnl_pct_f138 = 0
                                    _pnl_usdt_f138 = _vol_f * _pnl_pct_f138
                                    
                                    _c.execute(
                                        """INSERT INTO trade_history
                                           (symbol, trade_type, total_vol, entry_price, initial_price, exit_price,
                                            pnl_amount, pnl_pct, entry_time, exit_time,
                                            strategy_name, dca_count, close_reason, leverage, funding_fee, commission)
                                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RECONCILED', ?, 0, 0)""",
                                        (symbol, _tt_f, _vol_f, _avg_f,
                                         _p.get("initial_price") or _avg_f, _exit_real_f138,
                                         _pnl_usdt_f138, _pnl_pct_f138 * 100,
                                         _p.get("entry_time"), _now_f136b,
                                         _p.get("strategy_name") or "UNKNOWN", _p.get("dca_count") or 0,
                                         _p.get("leverage") or 1)
                                    )
                                    print(f"[F138] {symbol} exit={_exit_real_f138:.6f} | PnL={_pnl_usdt_f138:+.4f} USDT ({_pnl_pct_f138*100:+.2f}%)")
                            except Exception as _h_f136b:
                                print(f"[F136] {symbol} history hata: {str(_h_f136b)[:80]}")
                            _c.execute("DELETE FROM active_trades WHERE symbol = ?", (symbol,))
                            _c.commit()
                            _c.close()
                            print(f"[F126] {symbol} DB'den silindi + history'ye yazildi")
                        except Exception as _e126:
                            print(f"[F126] DB silme hatasi: {_e126}")
                        return "RECONCILED"
                    return None

                # ═══ F143: GERCEK EMIR DOGRULAMASI ═══
                # partial_close_position "success" dönse bile Binance'te gerçekten
                # pozisyon azalmış mı kontrol et. Azalmamışsa DB'yi GÜNCELLEME.
                import os as _os_f143b
                _sim_env_f143b = _os_f143b.environ.get("SIMULATE_ORDERS", "false").strip().lower() == "true"
                _mode_f143b = result_f97.get("mode", "REAL")
                _verified_f143b = result_f97.get("verified_reduction_qty", None)

                if _mode_f143b == "TEST" and not _sim_env_f143b:
                    print(f"[F143] {symbol} PT IPTAL: order_manager test_mode=True ama SIMULATE_ORDERS=false")
                    print(f"[F143] {symbol} Binance'e gercek emir GONDERILMEDI - DB guncellenmiyor")
                    return None

                if _mode_f143b == "REAL" and _verified_f143b is not None and _verified_f143b <= 0:
                    print(f"[F143] {symbol} PT IPTAL: Binance'te pozisyon AZALMADI "
                          f"(delta={_verified_f143b}) - DB guncellenmiyor")
                    return None

                if _mode_f143b == "REAL" and _verified_f143b is None:
                    print(f"[F143-UYARI] {symbol} verified_reduction_qty donmedi - "
                          f"eski surum order_manager olabilir, DB guncelleniyor")

                if result_f97.get("exit_price", 0) > 0:
                    exit_price = result_f97["exit_price"]
                    print(f"[F97] {symbol} partial fill: {exit_price}")
            except Exception as _e_f97:
                print(f"[F97] {symbol} partial close exception: {_e_f97}")
                # F126: Exception'da da ayni kontrol
                _msg2 = str(_e_f97).lower()
                if "bulunamadi" in _msg2 or "not found" in _msg2 or "does not exist" in _msg2 or "-2022" in _msg2 or "reduceonly" in _msg2:
                    print(f"[F126] {symbol} (exception) Binance'te yok, DB temizleniyor...")
                    try:
                        _c2 = get_db_connection()
                        _c2.execute("DELETE FROM active_trades WHERE symbol = ?", (symbol,))
                        _c2.commit()
                        _c2.close()
                    except Exception: pass
                    return "RECONCILED"
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
        
        # FIX F97: Gercek emir yukarida yapildi
        
        # --- trade_history'e AYRI satir yaz ---
        exit_time = int(time.time())
        strategy_name = trade.get("strategy_name") or "UNKNOWN"
        dca_count = trade.get("dca_count") or 0
        leverage = trade.get("leverage") or 1
        
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO trade_history 
               (symbol, trade_type, total_vol, entry_price, initial_price, exit_price,
                pnl_amount, pnl_pct, entry_time, exit_time,
                strategy_name, dca_count, close_reason, leverage, funding_fee, is_partial, commission)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)""",
            (symbol, trade_type, close_vol_usdt, avg_price,
             trade.get("initial_price") or avg_price, exit_price,
             net_pnl, pnl_pct * 100, trade["entry_time"], exit_time,
             strategy_name, dca_count, reason, leverage, exit_comm)
        )
        conn.commit()
        conn.close()
        
        # --- active_trades guncelle ---
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
                    leverage=trade.get("leverage", 1) if 'trade' in locals() else leverage,
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
                # F94: Bu pozisyonu bir daha denemesin (spike magduru)
                try:
                    _c = get_db_connection()
                    _c.execute(
                        "UPDATE active_trades SET pt_enabled = 0, pt_done = 1 WHERE symbol = ?",
                        (symbol,)
                    )
                    _c.commit()
                    _c.close()
                    print(f"[F94] {symbol} PT deaktive edildi (spike magduru)")
                except Exception as _e:
                    print(f"[F94] DB hata: {_e}")
                return None
        else:
            if not exit_price or exit_price <= 0:
                exit_price = avg_price
                print(f"[FORCE] {symbol}: Geçersiz fiyat, avg_price kullanılıyor")

        # FIX F97: ONCE Binance'te kapat, gercek fill al
        actual_exit_price = exit_price
        if self.order_manager:
            try:
                close_result = await asyncio.to_thread(
                    self.order_manager.close_position, symbol=symbol
                )
                if close_result and close_result.get("exit_price", 0) > 0:
                    actual_exit_price = close_result["exit_price"]
                    print(f"[F97] {symbol} kapanis fill: {actual_exit_price} (ticker: {exit_price})")
                else:
                    # FIX LOG-THROTTLE: test modu netlestir
                    _is_test_mode = bool(getattr(self.order_manager, 'test_mode', False)) if self.order_manager else False
                    if _is_test_mode:
                        print(f"[F97] {symbol} TEST modu (fill simulasyon yok) - ticker: {exit_price}")
                    else:
                        print(f"[F97] {symbol} fill alinamadi, ticker kullaniliyor: {exit_price}")
            except Exception as _e_f97:
                print(f"[F97] {symbol} close hatasi: {_e_f97} - ticker kullaniliyor")

        exit_price = actual_exit_price

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
        
        entry_is_maker = trade.get("entry_is_maker") or 0
        entry_rate = maker_rate if entry_is_maker else taker_rate
        entry_comm = initial_vol * entry_rate
        dca_comm = dca_vol * maker_rate
        exit_comm = total_vol * taker_rate
        commission = entry_comm + dca_comm + exit_comm
        
        gross_pnl = trade["total_vol"] * pnl_pct
        
        # ⚡ Funding ucretini cek (Binance'ten)
        exit_time = int(time.time())
        funding_fee = await self._get_funding_fee(symbol, trade["entry_time"], exit_time)
        
        # F250: Adaletli Funding Dagitimi
        # Gecmiste PT yapildiysa, toplam funding'i hacimlere oranla
        _pt_vol = trade.get("pt_volume", 0) or 0
        _tot_vol = total_vol + _pt_vol
        _funding_ratio = total_vol / _tot_vol if _tot_vol > 0 else 1.0
        _funding_ttp = funding_fee * _funding_ratio

        # net_pnl = brut - komisyon + funding
        # (funding negatifse duser, pozitifse ekler)
        net_pnl = gross_pnl - commission + _funding_ttp
        # F194d: ASAP kapanis -> cooldown
        if trade.get("strategy_name") == "ASAP":
            try:
                from backend.strategies.asap import asap_set_cooldown
                _cfg2 = load_config()
                _a2 = _cfg2.get("strategies", {}).get("ASAP", {})
                _rs = str(reason or "").upper()
                if "PARTIAL" in _rs or "TP" in _rs or "TTP" in _rs or "TRAIL" in _rs:
                    _cd = int(_a2.get("cooldownAfterTP", 1)) * 60
                    asap_set_cooldown(symbol, _cd, "tp")
                    print(f"[F194d] {symbol} on_tp -> cooldown {_cd}s")
                else:
                    _cd = int(_a2.get("cooldownAfterExit", 1)) * 60
                    asap_set_cooldown(symbol, _cd, "exit")
                    print(f"[F194d] {symbol} on_exit -> cooldown {_cd}s")
            except Exception as _e194d:
                print(f"[F194d] cooldown set hatasi: {_e194d}")
        # F193b: ASAP TP/exit hook
        if (trade.get("strategy_name") == "ASAP"):
            try:
                from backend.strategies.asap import asap_set_cooldown
                _rsn = str(reason or "").upper()
                _cfg_pm = load_config()
                _asap_cfg = _cfg_pm.get("strategies", {}).get("ASAP", {})
                if "PARTIAL" in _rsn or "TP" in _rsn or "TTP" in _rsn:
                    _cd = int(_asap_cfg.get("cooldownAfterTP", 10)) * 60
                    asap_set_cooldown(symbol, _cd, "tp")
                    print(f"[F193b] {symbol} on_tp -> cooldown {int(_cd/60)} dk")
                else:
                    _cd = int(_asap_cfg.get("cooldownAfterExit", 30)) * 60
                    asap_set_cooldown(symbol, _cd, "exit")
                    print(f"[F193b] {symbol} on_exit -> cooldown {int(_cd/60)} dk")
            except Exception as _e193b3:
                print(f"[F193b] on_exit hatasi: {_e193b3}")

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
               (symbol, trade_type, total_vol, entry_price, initial_price, exit_price, 
                pnl_amount, pnl_pct, entry_time, exit_time,
                strategy_name, dca_count, close_reason, leverage, funding_fee, commission)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, trade["trade_type"], trade["total_vol"], avg_price,
             trade.get("initial_price") or avg_price, exit_price,
             net_pnl, pnl_pct * 100, trade["entry_time"], exit_time,
             strategy_name, dca_count, reason, leverage, funding_fee, commission)
        )
        # F273: Kapanis basariliysa aktif pozisyonu DB'den SIL (Mukerrer kapanisi onler)
        conn.execute("DELETE FROM active_trades WHERE symbol = ?", (symbol,))
        conn.commit()
        conn.close()

        # FIX F97: Binance kapatma yukarida yapildi
        sign = "+" if net_pnl >= 0 else ""
        dca_info = f" (DCA:{dca_count})" if dca_count > 0 else ""
        lev_info = f" [{leverage}x]" if leverage > 1 else ""
        print(f"[✓ KAPANIŞ] {symbol}{dca_info}{lev_info} | {reason} | Çıkış: {exit_price:.6f} | "
              f"Kâr: {sign}{pnl_pct*100:.2f}% | Kom: -{commission:.4f} | Net: {sign}{net_pnl:.4f} USDT")
        
        # ⚡ Telegram bildirimi (ayar kontrolü ile)
        try:
            cfg = load_config()
            tg_cfg = cfg.get("telegram", {})
            if tg_cfg.get("notify_closes", True):
                asyncio.create_task(telegram_notifier.notify_close(
                    symbol=symbol,
                    trade_type=trade["trade_type"],
                    entry_price=avg_price,
                    exit_price=exit_price,
                    pnl_pct=pnl_pct * 100,
                    net_pnl=net_pnl,
                    reason=reason,
                    dca_count=dca_count,
                    leverage=trade.get("leverage", 1) if 'trade' in locals() else leverage,
                ))
        except Exception as _e:
            print(f"[TG] Kapanış bildirim hatası: {_e}")

        return {
            "symbol": symbol,
            "exit_price": exit_price,
            "pnl_pct": pnl_pct * 100,
            "net_pnl": net_pnl,
            "reason": reason,
        }

    # ==================================================================
    # GRID REEL: Grubu kapat (recenter sonrasi eski grup temizligi)
    # ==================================================================
    async def _close_grid_group(self, symbol: str, group_id: str,
                                 reason: str = "GRID RECENTER"):
        """
        Recenter sonrasi eski grubun tum pozisyonlarini piyasa fiyatindan kapatir.
        """
        if not group_id:
            return 0

        conn = get_db_connection()
        rows = conn.execute("""
            SELECT * FROM active_trades
            WHERE symbol = ? AND grid_group_id = ? AND is_grid_position = 1
        """, (symbol, group_id)).fetchall()
        conn.close()

        if not rows:
            return 0

        # Anlik fiyat
        prices = await self.get_current_prices([symbol])
        current_price = prices.get(symbol)
        if not current_price:
            print(f"[GRID-CLEANUP] {symbol} grup {group_id} fiyat alinamadi")
            return 0

        closed = 0
        for row in rows:
            pos = dict(row)
            print(f"[GRID-CLEANUP] {symbol} L{pos.get('grid_level')} "
                  f"(grup={group_id}) kapatiliyor @ {current_price:.6f} | {reason}")
            try:
                await self._execute_grid_close(pos, current_price, reason)
                closed += 1
            except Exception as e:
                print(f"[GRID-CLEANUP] Hata: {e}")

        print(f"[GRID-CLEANUP] {symbol} grup {group_id} -> {closed} pozisyon kapatildi")
        return closed

    # ==================================================================
    # GRID REEL: Seviye izleme
    # ==================================================================
    async def _check_grid_positions(self, grid_positions: list, prices: dict):
        """
        Grid seviyelerini izler. Her seviyenin TP'si sabit (grid_tp_price).
        Fiyat TP'ye ulasirsa seviye kapanir. DCA / trailing YOK.
        """
        for pos in grid_positions:
            symbol = pos["symbol"]
            if symbol not in prices:
                continue

            current_price = prices[symbol]
            entry_price = pos["avg_price"]
            trade_type = pos["trade_type"]
            grid_tp_price = pos.get("grid_tp_price")
            grid_level = pos.get("grid_level") or 0

            if not grid_tp_price or grid_tp_price <= 0 or entry_price <= 0:
                continue

            # --- TP kontrolu ---
            hit = False
            if trade_type == "BUY" and current_price >= grid_tp_price:
                hit = True
            elif trade_type == "SELL" and current_price <= grid_tp_price:
                hit = True

            if hit:
                await self._execute_grid_close(pos, current_price, "GRID TP")

    async def _execute_grid_close(self, pos: dict, exit_price: float, reason: str):
        """
        Grid seviyesini kapatir + trade_history'e yazar + OrderManager'i cagirir.
        """
        symbol = pos["symbol"]
        grid_group_id = pos.get("grid_group_id")
        grid_level = pos.get("grid_level") or 0

        # --- Validasyon ---
        entry_price = pos["avg_price"]
        if not entry_price or entry_price <= 0:
            print(f"[GRID-CLOSE] Gecersiz giris {symbol} L{grid_level}")
            return None
        if not exit_price or exit_price <= 0:
            print(f"[GRID-CLOSE] Gecersiz cikis {symbol} L{grid_level}")
            return None

        ratio = exit_price / entry_price
        if ratio > 10 or ratio < 0.1:
            print(f"[GRID-CLOSE] Supheli oran {symbol}: {ratio:.4f}")
            return None

        # --- Komisyon ---
        if self.order_manager and hasattr(self.order_manager, "get_commission_rate"):
            comm_rates = self.order_manager.get_commission_rate(symbol)
        else:
            comm_rates = {"taker": 0.0004, "maker": 0.0002}

        taker_rate = comm_rates.get("taker", 0.0004)
        maker_rate = comm_rates.get("maker", 0.0002)

        total_vol = pos["total_vol"]
        entry_is_maker = pos.get("entry_is_maker") or 0
        entry_rate = maker_rate if entry_is_maker else taker_rate
        commission = (total_vol * entry_rate) + (total_vol * taker_rate)

        # FIX F97: ONCE Binance'te kapat, gercek fill al
        actual_exit_price = exit_price
        if self.order_manager:
            try:
                close_result = await asyncio.to_thread(
                    self.order_manager.close_grid_position,
                    symbol=symbol,
                    grid_group_id=grid_group_id,
                    grid_level=grid_level,
                )
                if close_result and close_result.get("exit_price", 0) > 0:
                    actual_exit_price = close_result["exit_price"]
                    print(f"[F97] {symbol} L{grid_level} kapanis fill: {actual_exit_price}")
                else:
                    print(f"[F97] {symbol} L{grid_level} fill alinamadi, ticker: {exit_price}")
            except Exception as _e_f97:
                print(f"[F97] {symbol} L{grid_level} close hatasi: {_e_f97}")

        exit_price = actual_exit_price

        # --- PnL ---
        if pos["trade_type"] == "BUY":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        gross_pnl = total_vol * pnl_pct
        # FIX K3: net_pnl asagida funding fee ile hesaplanacak

        # ==========================================================
        # ⚡ ANOMALI KORUMASI: |pnl_pct| > %30 ise kayit YAPMA
        # Grid TP gercekci olarak %1-5 olur, %30+ testnet spike demek
        # ==========================================================
        if abs(pnl_pct * 100) > 30:
            print(f"[SPIKE-GUARD] {symbol} L{grid_level} ANOMALI "
                  f"REDDEDILDI! entry={entry_price:.6f} exit={exit_price:.6f} "
                  f"pnl=%{pnl_pct*100:.2f}")
            # FIX F97: Pozisyon yukarida kapatildi
            return {
                "symbol": symbol,
                "grid_level": grid_level,
                "skipped": True,
                "reason": f"anomaly_pnl_{pnl_pct*100:.2f}",
            }

        exit_time = int(time.time())
        # FIX K3: funding fee cek (Binance'ten)
        funding_fee = await self._get_funding_fee(
            symbol, pos.get("entry_time", exit_time), exit_time
        )
        net_pnl = gross_pnl - commission + funding_fee
        strategy_name = pos.get("strategy_name") or "DYNAMIC_GRID_REEL"
        leverage = pos.get("leverage") or 1

        # --- trade_history'e yaz ---
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO trade_history
               (symbol, trade_type, total_vol, entry_price, initial_price, exit_price,
                pnl_amount, pnl_pct, entry_time, exit_time,
                strategy_name, dca_count, close_reason, leverage, funding_fee, commission)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (symbol, pos["trade_type"], total_vol, entry_price,
             pos.get("initial_price") or entry_price, exit_price,
             net_pnl, pnl_pct * 100, pos["entry_time"], exit_time,
             strategy_name, reason, leverage, funding_fee, commission)
        )
        conn.commit()
        conn.close()

        # FIX F97: Binance kapatma yukarida yapildi
        sign = "+" if net_pnl >= 0 else ""
        print(f"[GRID-CLOSE] {symbol} L{grid_level} | {reason} | "
              f"Giris: {entry_price:.6f} Cikis: {exit_price:.6f} | "
              f"{sign}{pnl_pct*100:.2f}% | Kom: -{commission:.4f} | "
              f"Net: {sign}{net_pnl:.4f} USDT")

        # --- Telegram ---
        try:
            cfg = load_config()
            tg_cfg = cfg.get("telegram", {})
            if tg_cfg.get("notify_closes", True):
                asyncio.create_task(telegram_notifier.notify_close(
                    symbol=symbol,
                    trade_type=pos["trade_type"],
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl_pct=pnl_pct * 100,
                    net_pnl=net_pnl,
                    reason=f"{reason} L{grid_level}",
                    dca_count=0,
                    leverage=pos.get("leverage", 1),
                ))
        except Exception as _e:
            print(f"[TG] Grid close bildirim hatasi: {_e}")

        return {
            "symbol": symbol,
            "grid_level": grid_level,
            "exit_price": exit_price,
            "net_pnl": net_pnl,
            "pnl_pct": pnl_pct * 100,
        }

    # ------------------------------------------------------------------
    # Ana döngü
    # ------------------------------------------------------------------
    async def monitor_positions(self, strategies_config: dict):
        positions = self.get_all_open_positions()
        if not positions:
            return

        # ⚡ Grid REEL ve klasik pozisyonlari AYIR
        classic_positions = [p for p in positions if (p.get("is_grid_position") or 0) != 1]
        grid_positions = [p for p in positions if (p.get("is_grid_position") or 0) == 1]

        symbols = [p["symbol"] for p in positions]
        prices = await self.get_current_prices(symbols)
        if not prices:
            return

        # ⚡ 1. GRID seviyelerini izle (TP sabit, DCA yok)
        if grid_positions:
            await self._check_grid_positions(grid_positions, prices)

        # ⚡ 2. Klasik DCA pozisyonlarini izle (eski akis)
        for pos in classic_positions:
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
            sl_pct = params["stopLoss"] / 100
            # F203c: slEnabled=false ise SL TAMAMEN devre disi
            # F221: ASAP icin varsayilan SL KAPALI (default False)
            _default_sl = False if strategy_name == "ASAP" else True
            _f203c_sl_enabled = bool(params.get("slEnabled", _default_sl))
            if not _f203c_sl_enabled:
                sl_pct = 0.0
            # F170c: SL mesafesi = DCA mesafesi x K (K default 1.5)
            # Boylece SL, sonraki DCA seviyesinin ALTINDA kalir
            # F171: Dinamik DCA mesafesi (cache) | fallback: config dcaMinDistancePct
            _f170c_dca_dist = float(params.get("dcaMinDistancePct", 5.0))
            if hasattr(self, "_dca_last_step") and symbol in self._dca_last_step:
                _f170c_dca_dist = float(self._dca_last_step[symbol])
            _f170c_k = float(params.get("slDcaMultiplier", 1.5))
            # F346: F170c DCA ezmesi kullanici istegiyle KALDIRILDI
            pass
            # Log throttle: sembol basi 5 dk
            if not hasattr(self, "_f170c_log"):
                self._f170c_log = {}
            import time as _t_f170c
            _now_f170c = _t_f170c.time()
            if _now_f170c - self._f170c_log.get(symbol, 0) >= 300:
                self._f170c_log[symbol] = _now_f170c
                print(f"[F171] {symbol} SL mesafe: %{_f170c_old_sl_pct*100:.2f} -> %{sl_pct*100:.2f} (next_step=%{_f170c_dca_dist:.2f} x K={_f170c_k})")

            # F170: F84 LIQ-safe cap config ile kontrol (varsayilan KAPALI)
            _f170_liq_safe = False
            try:
                _cfg_f170 = load_config()
                _f170_liq_safe = bool(_cfg_f170.get("slLiqSafeCapEnabled", False))
            except Exception:
                pass
            # F84: LIQ-safe SL (SL > LIQ olmamali)
            try:
                _lev_sl = max(1, int(pos.get("leverage") or 1))
                # LIQ mesafe = (100 / lev) - emniyet
                _liq_pct_sl = (100.0 / _lev_sl) - 1.0
                # SL = LIQ'in %85'i (emniyet payi)
                _auto_sl_pct = (_liq_pct_sl * 0.85) / 100.0
                if False and sl_pct > _auto_sl_pct:
                    _old_sl = sl_pct * 100
                    sl_pct = _auto_sl_pct
                    # Ayni pozisyon icin 1 kez log
                    if not hasattr(self, "_sl_auto_logged"):
                        self._sl_auto_logged = set()
                    # FIX LOG-THROTTLE: sembol basina 5 dk'da 1 log
                    import time as _t_sl
                    _now_sl = _t_sl.time()
                    if not hasattr(self, "_sl_auto_logged"):
                        self._sl_auto_logged = {}
                    # Eski format set ise dict'e cevir
                    if isinstance(self._sl_auto_logged, set):
                        self._sl_auto_logged = {k: 0 for k in self._sl_auto_logged}
                    _last_sl = self._sl_auto_logged.get(position_key, 0)
                    if _now_sl - _last_sl >= 300:
                        self._sl_auto_logged[position_key] = _now_sl
                        print(f"[SL-AUTO] {symbol} lev={_lev_sl}x LIQ=%{_liq_pct_sl:.1f} "
                              f"config=%{_old_sl:.1f} -> SL=%{sl_pct*100:.1f} (LIQ-safe)")
            except Exception as _e_sl_auto:
                print(f"[SL-AUTO] hata {symbol}: {_e_sl_auto}")

            # ⚡ AI TTP - kademeli trailing
            _steps_str = params.get("trailingSteps") or ""
            _trail_steps = self._parse_trailing_steps(_steps_str)
            # Backward compat: trailingSteps yoksa eski trailing degerini kullan
            if not _trail_steps and params.get("trailing"):
                _trail_steps = [(0.0, float(params["trailing"]))]
            # Fallback default
            if not _trail_steps:
                _trail_steps = [(1.5, 0.3), (2.5, 0.2), (4.0, 0.12), (6.0, 0.07), (10.0, 0.03)]
            trailing_pct = _trail_steps[0][1] / 100.0  # sadece init icin

            if trade_type == "BUY":
                profit_pct = (current_price - entry_price) / entry_price
            else:
                profit_pct = (entry_price - current_price) / entry_price

            # 1. DCA kontrolü (trailing pasif + PT sonrasi keep_dca kontrolu)
            state = self.trailing_state.get(position_key, {"active": False, "hwm": None})
            
            pt_done_flag = pos.get("pt_done") or 0
            pt_keep_dca_flag = pos.get("pt_keep_dca")
            if pt_keep_dca_flag is None:
                pt_keep_dca_flag = 1
            skip_dca_after_pt = bool(pt_done_flag and not pt_keep_dca_flag)
            
            if not state.get("active") and not skip_dca_after_pt:
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

            # F180: Time-based exit (maxHoldHours)
            _f180_max_h = params.get("maxHoldHours")
            if _f180_max_h and _f180_max_h > 0:
                _f180_entry_ts = int(pos.get("entry_time") or 0)
                if _f180_entry_ts > 0:
                    import time as _t_f180
                    _f180_age_h = (_t_f180.time() - _f180_entry_ts) / 3600.0
                    if _f180_age_h >= _f180_max_h and profit_pct >= 0:  # F236: Zarari kapama, basabasa gelince kapat
                        print(f"[F180] {symbol} BREAK-EVEN EXIT: yas={_f180_age_h:.1f}s >= {_f180_max_h}s "
                              f"pnl={profit_pct*100:.2f}% -> KAPAT")
                        await self._execute_close(
                            symbol, current_price,
                            f"TIME-EXIT ({_f180_age_h:.1f}s, {profit_pct*100:.2f}%)"
                        )
                        self.trailing_state.pop(position_key, None)
                        continue

            # 2. Stop Loss ⚡ [SL-AFTER-DCA]
            # SL_base = son DCA fiyati (varsa), yoksa avg_price
            # F170b (Secenek B): SL base = initial_price (ilk giris)
            # DCA oldukca asagida son DCA fiyatina kayar
            sl_base_price = pos.get("initial_price") or entry_price
            try:
                import json as _json_sl
                _dh_sl = pos.get("dca_history") or "[]"
                _history_sl = _json_sl.loads(_dh_sl) if isinstance(_dh_sl, str) else _dh_sl
                if _history_sl and len(_history_sl) > 0:
                    _last_dca_price = float(_history_sl[-1].get("price", 0))
                    if _last_dca_price > 0:
                        # F170: SL base = son DCA fiyati
                        sl_base_price = _last_dca_price
                        print(f"[F170] {symbol} SL base=son DCA ({sl_base_price:.6f}) [AVG={entry_price:.6f}]")
            except Exception as _e_sl:
                print(f"[SL-DCA] history parse hatasi ({symbol}): {_e_sl}")

            # F283: Likidasyon (LIQ) Tabanli Evrensel SL
            # F293: Kullanici manuel SL girdiyse onu kullan, yoksa LIQ tabanliyi kullan
            _user_sl_pct = float(params.get("stopLoss", 0))
            if _user_sl_pct > 0:
                _final_sl_pct = _user_sl_pct / 100.0
            else:
                _final_sl_pct = sl_pct # F346: Dogrudan config stopLoss degeri

            sl_hit = False
            if _f203c_sl_enabled and _final_sl_pct > 0:
                _liq_price = float(pos.get("liquidation_price") or 0)
                # F351 IZOLE TEST OVERRIDE
                if "ACE" in symbol:
                    _liq_price = 0.18000
                
                if _liq_price <= 0:
                    # F345: Matematiksel fallback TAMAMEN KALDIRILDI. API 0 donerse SL atlanir.
                    continue
                
                # F329: SL'i KESINLIKLE LIQ fiyatina gore hesapla
                if trade_type == "BUY":
                    sl_trigger = _liq_price * (1 + _final_sl_pct)
                    sl_hit = current_price <= sl_trigger
                else:
                    sl_trigger = _liq_price * (1 - _final_sl_pct)
                    sl_hit = current_price >= sl_trigger
                    
                # Debug logu (kontrol icin)
                # print(f"[F329-SL] {symbol} LIQ={_liq_price:.6f} SL_PCT={_final_sl_pct} Trigger={sl_trigger:.6f}")

            if sl_hit:
                # Gercek zarar yuzdesi (avg_price bazli, rapor icin)
                _real_pct = ((current_price - entry_price) / entry_price * 100) if trade_type == "BUY" \
                            else ((entry_price - current_price) / entry_price * 100)
                # F170b: base = DCA ise 'DCA', degilse 'INIT'
                _base_label = "DCA" if (sl_base_price != (pos.get("initial_price") or entry_price)) else "INIT"
                print(f"[SL-DCA] {symbol} SL | base={sl_base_price:.6f} ({_base_label}) "
                      f"trigger={sl_trigger:.6f} cur={current_price:.6f} real={_real_pct:.2f}%")
                await self._execute_close(symbol, current_price,
                                          f"STOP LOSS ({_real_pct:.2f}%) [base={_base_label}]")
                self.trailing_state.pop(position_key, None)
                continue

            # ⚡ KISMİ TP KONTROLU (trailing'den ONCE)
            pt_enabled = pos.get("pt_enabled") or 0
            pt_done_flag = pos.get("pt_done") or 0
            pt_percent_val = pos.get("pt_percent")
            if pt_percent_val is None:
                pt_percent_val = 50
            
            if pt_enabled and not pt_done_flag and not state["active"] and profit_pct >= tp_pct:
                pt_close_vol = pos["total_vol"] * (pt_percent_val / 100.0)
                # F93: PT-DEBUG logunu 10 dk'da 1 bas
                import time as _t_pt
                _now_pt = _t_pt.time()
                if not hasattr(self, "_pt_debug_last"):
                    self._pt_debug_last = {}
                _last_pt = self._pt_debug_last.get(symbol, 0)
                if _now_pt - _last_pt >= 600:
                    self._pt_debug_last[symbol] = _now_pt
                    print(f"[PT-DEBUG] {symbol} | pos_total_vol={pos['total_vol']} | "
                          f"pt_percent={pt_percent_val} | pt_close_vol={pt_close_vol} | "
                          f"pt_enabled={pt_enabled} | pt_done={pt_done_flag} | "
                          f"profit_pct={profit_pct*100:.2f}%")
                # ⚡ Test modunda min notional uygulanmaz (gercek emir yok)
                _is_test = bool(getattr(self.order_manager, 'test_mode', False)) if self.order_manager else False
                MIN_ORDER_USDT = 0.5 if _is_test else 5.0

                # F130b: PT cok kucukse minPtUsdt'ye yukari cek
                try:
                    _cfg_f130b = load_config()
                    _min_pt = float(_cfg_f130b.get("minPtUsdt", 5.5))
                except Exception:
                    _min_pt = 5.5
                if not _is_test and pt_close_vol < _min_pt:
                    _total_vol_f130b = float(pos["total_vol"] or 0)
                    _safe_max_f130b = _total_vol_f130b * 0.90
                    if _min_pt <= _safe_max_f130b:
                        print(f"[F130b] {symbol} PT {pt_close_vol:.2f} -> {_min_pt:.2f} USDT (minPtUsdt)")
                        pt_close_vol = _min_pt
                    else:
                        print(f"[F130b] {symbol} PT atlandi: total={_total_vol_f130b:.2f}, "
                              f"minPtUsdt={_min_pt:.2f} > %90 ({_safe_max_f130b:.2f})")
                
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
                    # F93b: ayni mesaji 10 dk'da 1 bas
                    import time as _t_pt2
                    _now_pt2 = _t_pt2.time()
                    if not hasattr(self, "_pt_trig_last"):
                        self._pt_trig_last = {}
                    _last_trig = self._pt_trig_last.get(symbol, 0)
                    if _now_pt2 - _last_trig >= 600:
                        self._pt_trig_last[symbol] = _now_pt2
                        print(f"[PARTIAL-TP] {symbol} tetiklendi: %{pt_percent_val:.0f} "
                              f"({pt_close_vol:.2f} USDT) | Kar: {profit_pct*100:.2f}%")
                    
                    self._closing_locks[symbol] = True
                    # F252: PT islemi sirasinda bu sembolu kilitle
                    try:
                        pt_result = await self._execute_partial_close(
                            symbol, current_price, pt_close_vol, pt_percent_val, reason
                        )
                    finally:
                        self._closing_locks[symbol] = False
                    
                    if pt_result == "RECONCILED":
                        # F126: Pozisyon Binance'te yoktu, DB'den silindi
                        print(f"[F126] {symbol} reconcile edildi (pozisyon artik yok)")
                        continue
                    elif pt_result:
                        self.trailing_state[position_key] = {"active": False, "hwm": None}
                        print(f"[PARTIAL-TP] {symbol} trailing RESET | "
                              f"Kalan: {pt_result['remaining_volume']:.2f} USDT")
                    else:
                        print(f"[PARTIAL-TP] {symbol} basarisiz, sonraki tick tekrar denecek")
                    
                    continue
            
            # 3. Trailing state
            if position_key not in self.trailing_state:
                self.trailing_state[position_key] = {"active": False, "hwm": None, "trail_pct": None}
            state = self.trailing_state[position_key]

            if not state["active"] and profit_pct >= tp_pct:
                state["active"] = True
                state["hwm"] = current_price
                # Ilk kademeyi hesapla
                _t0 = self._get_ai_ttp_pct(_trail_steps, profit_pct, state)
                # F94b: AI-TTP logunu 10 dk'da 1 bas
                import time as _t_ai
                _now_ai = _t_ai.time()
                if not hasattr(self, "_ai_ttp_log_last"):
                    self._ai_ttp_log_last = {}
                _last_ai = self._ai_ttp_log_last.get(symbol, 0)
                if _now_ai - _last_ai >= 600:
                    self._ai_ttp_log_last[symbol] = _now_ai
                    print(f"[AI-TTP] {symbol} AKTIF | Kâr: {profit_pct*100:.2f}% | Trail: %{_t0*100:.2f} | HWM: {current_price:.6f}")

            # 4. Trailing aktifse kapanış kontrolü (kademeli)
            if state["active"]:
                # ⚡ Her tick'te kademeyi guncelle (ratchet - geri donmez)
                _old_trail = state.get("trail_pct")
                _cur_trail = self._get_ai_ttp_pct(_trail_steps, profit_pct, state)
                if _old_trail is None or _cur_trail < _old_trail:
                    print(f"[AI-TTP] {symbol} Kademe geçişi: %{(_old_trail or 0)*100:.2f} -> %{_cur_trail*100:.2f} | Kâr: {profit_pct*100:.2f}%")

                if trade_type == "BUY":
                    if current_price > state["hwm"]:
                        state["hwm"] = current_price
                    trigger = state["hwm"] * (1 - _cur_trail)
                    if current_price <= trigger:
                        self._closing_locks[symbol] = True
                        try:
                            await self._execute_close(symbol, current_price,
                                                      f"AI-TTP ({profit_pct*100:.2f}%)")
                            self.trailing_state.pop(position_key, None)
                        finally:
                            self._closing_locks[symbol] = False
                else:
                    if current_price < state["hwm"]:
                        state["hwm"] = current_price
                    trigger = state["hwm"] * (1 + _cur_trail)
                    if current_price >= trigger:
                        self._closing_locks[symbol] = True
                        try:
                            await self._execute_close(symbol, current_price,
                                                      f"AI-TTP ({profit_pct*100:.2f}%)")
                            self.trailing_state.pop(position_key, None)
                        finally:
                            self._closing_locks[symbol] = False