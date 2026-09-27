# -*- coding: utf-8 -*-
"""
Dynamic Grid REEL -- Gercek Grid Stratejisi
============================================

Her grid seviyesi BAGIMSIZ bir pozisyon acar.
Mevcut DYNAMIC_GRID (DCA'li) ile PARALEL calisir, onu BOZMAZ.

Fark:
  DYNAMIC_GRID      : Tek pozisyon + DCA kademeleri
  DYNAMIC_GRID_REEL : Her seviye ayri pozisyon, DCA yok

Grid mantigi:
  - Referans etrafinda N/2 SELL (ust) + N/2 BUY (alt)
  - Fiyat bir seviyeye dokundugunda o yonde emir tetiklenir
  - Her seviyenin TP'si = komsu seviye
      * BUY  seviyesi icin TP = bir ustteki seviye
      * SELL seviyesi icin TP = bir alttaki seviye
  - Fiyat TP'ye ulasirsa o seviye kapanir, yeniden bekler
"""
import time
import uuid
from .base import BaseStrategy
from .dynamic_grid import _calc_sma, _calc_atr


class DynamicGridReelStrategy(BaseStrategy):
    name = "DYNAMIC_GRID_REEL"

    def __init__(self, params):
        super().__init__(params)
        # Sembol bazli state -- multi-position icin ZORUNLU
        self._symbol_state = {}

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def _state(self, symbol):
        if symbol not in self._symbol_state:
            self._symbol_state[symbol] = {
                "group_id": None,
                "prev_group_id": None,
                "reference": None,
                "top": None,
                "bottom": None,
                "levels": None,
                "last_recenter_ts": 0,
                "triggered_levels": set(),
                "recenter_happened": False,
            }
        return self._symbol_state[symbol]

    def reset_symbol(self, symbol):
        self._symbol_state.pop(symbol, None)

    def get_state_snapshot(self, symbol):
        """
        Symbol'un mevcut grid durumunu dondur (DB'ye kaydetmek icin).
        State yoksa None doner.
        """
        st = self._symbol_state.get(symbol)
        if not st or not st.get("reference"):
            return None
        return {
            "group_id": st.get("group_id"),
            "reference": st.get("reference"),
            "top": st.get("top"),
            "bottom": st.get("bottom"),
            "levels": st.get("levels") or [],
            "recenter_ts": st.get("last_recenter_ts", 0),
            "mode": self.params.get("mode", "neutral"),
            "interval": self.params.get("interval", "1m"),
        }

    # ------------------------------------------------------------------
    # Referans ve seviye hesaplama
    # ------------------------------------------------------------------
    def _calc_reference(self, candles):
        sma_period = int(self.params.get("smaPeriod", 100))
        pivot_lookback = int(self.params.get("pivotLookback", 100))
        atr_period = int(self.params.get("atrPeriod", 14))
        atr_mult = float(self.params.get("atrMultiplier", 8))
        min_wr = float(self.params.get("minWidthRatio", 0.4))
        max_wr = float(self.params.get("maxWidthRatio", 0.8))

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        sma_center = _calc_sma(closes, sma_period)
        if sma_center is None:
            return None

        lookback = min(pivot_lookback, len(candles))
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        pivot_high = max(recent_highs)
        pivot_low = min(recent_lows)
        pivot_center = (pivot_high + pivot_low) / 2
        recent_range = pivot_high - pivot_low

        reference = (sma_center + pivot_center) / 2

        atr = _calc_atr(highs, lows, closes, atr_period)
        if atr is None or atr <= 0:
            return None

        atr_width = atr * atr_mult
        min_width = recent_range * min_wr
        max_width = recent_range * max_wr

        width = max(atr_width, min_width)
        width = min(width, max_width)
        if width <= 0:
            return None

        asymmetry = float(self.params.get("asymmetryRatio", 1.3))
        current_price = closes[-1]

        if current_price > sma_center:
            top = reference + width * asymmetry
            bottom = reference - width * (2 - asymmetry)
        else:
            top = reference + width * (2 - asymmetry)
            bottom = reference - width * asymmetry

        if bottom <= 0:
            bottom = reference * 0.5

        return {
            "reference": reference,
            "top": top,
            "bottom": bottom,
            "sma": sma_center,
            "atr": atr,
            "width": width,
        }

    def _build_levels(self, reference, top, bottom, grid_count, dist_type):
        levels = []
        if reference <= bottom or reference >= top:
            return levels

        half_count = grid_count // 2
        if half_count < 1:
            return levels

        upper_range = top - reference
        if upper_range > 0:
            if dist_type == "geometric":
                ratio = (top / reference) ** (1.0 / half_count) if reference > 0 else 1
                for i in range(1, half_count + 1):
                    levels.append({"index": i, "price": reference * (ratio ** i), "side": "SELL"})
            else:
                step = upper_range / half_count
                for i in range(1, half_count + 1):
                    levels.append({"index": i, "price": reference + step * i, "side": "SELL"})

        lower_range = reference - bottom
        if lower_range > 0:
            if dist_type == "geometric":
                ratio = (reference / bottom) ** (1.0 / half_count) if bottom > 0 else 1
                for i in range(1, half_count + 1):
                    levels.append({"index": -i, "price": reference / (ratio ** i), "side": "BUY"})
            else:
                step = lower_range / half_count
                for i in range(1, half_count + 1):
                    levels.append({"index": -i, "price": reference - step * i, "side": "BUY"})

        return levels

    def _find_tp_for_level(self, levels, level_index):
        """
        BUY  icin TP = bir ustteki seviye
        SELL icin TP = bir alttaki seviye
        """
        if not levels:
            return None
        sorted_lvls = sorted(levels, key=lambda x: x["index"])
        for i, lvl in enumerate(sorted_lvls):
            if lvl["index"] == level_index:
                if level_index < 0:
                    if i + 1 < len(sorted_lvls):
                        return sorted_lvls[i + 1]["price"]
                elif level_index > 0:
                    if i - 1 >= 0:
                        return sorted_lvls[i - 1]["price"]
        return None

    # ------------------------------------------------------------------
    # ANA evaluate
    # ------------------------------------------------------------------
    def evaluate(self, candles, current_position=None, symbol=None):
        """
        Yeni sinyal uretir. Acik pozisyon DB'de tutulur (position_manager izler).
        symbol parametresi engine tarafindan gecirilir.
        """
        sma_period = int(self.params.get("smaPeriod", 100))
        pivot_lookback = int(self.params.get("pivotLookback", 100))
        min_needed = max(sma_period, pivot_lookback) + 10

        if not candles or len(candles) < min_needed:
            return {"signal": None, "reason": "Yetersiz veri", "meta": {}}

        current_candle = candles[-1]
        current_price = current_candle["close"]
        current_high = current_candle["high"]
        current_low = current_candle["low"]
        prev_price = candles[-2]["close"]
        candle_time = current_candle["time"]

        sym = symbol or self.params.get("_symbol", "UNKNOWN")
        st = self._state(sym)

        recenter_hours = float(self.params.get("recenterHours", 24))
        recenter_buffer = float(self.params.get("recenterBuffer", 0.03))
        now = time.time()

        need_recenter = False
        if st["last_recenter_ts"] == 0:
            need_recenter = True
        elif recenter_hours > 0 and (now - st["last_recenter_ts"]) >= recenter_hours * 3600:
            need_recenter = True

        if not need_recenter and st["top"] and st["bottom"]:
            buffer_top = st["top"] * (1 + recenter_buffer)
            buffer_bottom = st["bottom"] * (1 - recenter_buffer)
            if current_price > buffer_top or current_price < buffer_bottom:
                need_recenter = True

        if need_recenter or st["levels"] is None:
            ref_data = self._calc_reference(candles)
            if ref_data is None:
                return {"signal": None, "reason": "Referans hesaplanamadi", "meta": {}}

            # ⚡ Eski grubu hatirla (engine temizleyecek)
            _old_group = st.get("group_id")
            if _old_group:
                st["prev_group_id"] = _old_group
                st["recenter_happened"] = True
                print(f"[GRID-REEL] {sym} RECENTER -> yeni grup, eski={_old_group} kapatilacak")

            st["reference"] = ref_data["reference"]
            st["top"] = ref_data["top"]
            st["bottom"] = ref_data["bottom"]
            st["last_recenter_ts"] = now
            st["group_id"] = str(uuid.uuid4())[:8]
            st["triggered_levels"] = set()

            grid_count = int(self.params.get("gridCount", 20))
            dist_type = str(self.params.get("distributionType", "arithmetic")).lower()

            st["levels"] = self._build_levels(
                ref_data["reference"], ref_data["top"], ref_data["bottom"],
                grid_count, dist_type
            )

            print(f"[GRID-REEL] {sym} RECENTER | ref={ref_data['reference']:.4f} "
                  f"top={ref_data['top']:.4f} bottom={ref_data['bottom']:.4f} | "
                  f"{len(st['levels'])} seviye | group={st['group_id']}")

        meta = {
            "grid_group_id": st["group_id"],
            "grid_reference": st["reference"],
            "grid_top": st["top"],
            "grid_bottom": st["bottom"],
            "grid_levels": st["levels"],
            "grid_type": self.params.get("distributionType", "arithmetic"),
            "candle_time": candle_time,
            # ⚡ Recenter bilgisi
            "recenter_happened": st.get("recenter_happened", False),
            "prev_group_id": st.get("prev_group_id"),
        }

        # Flag'i temizle (engine bir kez islesin)
        st["recenter_happened"] = False

        mode = str(self.params.get("mode", "neutral")).lower()
        allow_long = mode in ("neutral", "long")
        allow_short = mode in ("neutral", "short")

        for level in st["levels"]:
            lvl_price = level["price"]
            lvl_side = level["side"]
            lvl_index = level["index"]

            if lvl_index in st["triggered_levels"]:
                continue

            if lvl_side == "BUY" and allow_long:
                # ⚡ Temas bazli: prev kapanis seviyenin USTUNDE + bu mumda low seviyeye DOKUNDU
                # VEYA klasik: prev > lvl >= current
                touched = (prev_price > lvl_price and current_low <= lvl_price)
                crossed = (prev_price > lvl_price >= current_price)
                if touched or crossed:
                    tp_price = self._find_tp_for_level(st["levels"], lvl_index)
                    st["triggered_levels"].add(lvl_index)
                    return {
                        "signal": "LONG",
                        "reason": f"Grid BUY @ {lvl_price:.6f} (idx {lvl_index}) -> TP {tp_price}",
                        "entry_price": current_price,
                        "meta": {
                            **meta,
                            "grid_level": lvl_index,
                            "grid_side": "BUY",
                            "grid_entry_price": lvl_price,
                            "grid_tp_price": tp_price,
                            "is_grid_reel": True,
                        },
                    }

            elif lvl_side == "SELL" and allow_short:
                # ⚡ Temas bazli: prev kapanis seviyenin ALTINDA + bu mumda high seviyeye DOKUNDU
                # VEYA klasik: prev < lvl <= current
                touched = (prev_price < lvl_price and current_high >= lvl_price)
                crossed = (prev_price < lvl_price <= current_price)
                if touched or crossed:
                    tp_price = self._find_tp_for_level(st["levels"], lvl_index)
                    st["triggered_levels"].add(lvl_index)
                    return {
                        "signal": "SHORT",
                        "reason": f"Grid SELL @ {lvl_price:.6f} (idx {lvl_index}) -> TP {tp_price}",
                        "entry_price": current_price,
                        "meta": {
                            **meta,
                            "grid_level": lvl_index,
                            "grid_side": "SELL",
                            "grid_entry_price": lvl_price,
                            "grid_tp_price": tp_price,
                            "is_grid_reel": True,
                        },
                    }

        return {"signal": None, "reason": "Grid tetiklenmedi", "meta": meta}
