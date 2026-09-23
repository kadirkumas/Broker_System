"""
Dynamic Grid Strategy - Adaptive Multi-Level Grid
Referans: Hibrit (SMA + Pivot ortalamasi)
Genislik: ATR bazli (min-max arasinda kisitli)
Asimetri: Trend yonune gore
Recenter: Belirli araliklarla veya range kirilirsa
Mode: Neutral (LONG + SHORT)
"""
import numpy as np
import time
from .base import BaseStrategy


def _calc_sma(closes, period):
    """Basit hareketli ortalama - sadece son degeri doner."""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def _calc_atr(highs, lows, closes, period=14):
    """Wilder ATR - son deger."""
    n = len(closes)
    if n < period + 1:
        return None
    trs = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr


class DynamicGridStrategy(BaseStrategy):
    """Adaptive Dynamic Grid Strategy"""
    name = "DYNAMIC_GRID"

    def __init__(self, params):
        super().__init__(params)
        # Cache: her sembol icin ayri tutulur (engine tarafindan)
        # Ama basitlik icin strateji instance'i tek sembol varsayar
        self._last_recenter_ts = 0
        self._cached_reference = None
        self._cached_top = None
        self._cached_bottom = None
        self._cached_levels = None

    def _calc_reference(self, candles):
        """Hibrit referans noktasi hesapla."""
        sma_period = int(self.params.get("smaPeriod", 100))
        pivot_lookback = int(self.params.get("pivotLookback", 100))
        atr_period = int(self.params.get("atrPeriod", 14))
        atr_mult = float(self.params.get("atrMultiplier", 8))
        min_wr = float(self.params.get("minWidthRatio", 0.4))
        max_wr = float(self.params.get("maxWidthRatio", 0.8))

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        # 1. SMA merkez
        sma_center = _calc_sma(closes, sma_period)
        if sma_center is None:
            return None

        # 2. Pivot merkez (son N mumun ortasi)
        lookback = min(pivot_lookback, len(candles))
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        pivot_high = max(recent_highs)
        pivot_low = min(recent_lows)
        pivot_center = (pivot_high + pivot_low) / 2
        recent_range = pivot_high - pivot_low

        # 3. Hibrit merkez
        reference = (sma_center + pivot_center) / 2

        # 4. Genislik (ATR bazli, min-max arasinda)
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

        # 5. Asimetri (trend yonune gore)
        asymmetry = float(self.params.get("asymmetryRatio", 1.3))
        current_price = closes[-1]

        if current_price > sma_center:
            # Boga piyasasi -> ust daha genis
            top = reference + width * asymmetry
            bottom = reference - width * (2 - asymmetry)
        else:
            # Ayi piyasasi -> alt daha genis
            top = reference + width * (2 - asymmetry)
            bottom = reference - width * asymmetry

        # Guvenlik: bottom pozitif olmali
        if bottom <= 0:
            bottom = reference * 0.5

        return {
            "reference": reference,
            "top": top,
            "bottom": bottom,
            "sma": sma_center,
            "pivot_high": pivot_high,
            "pivot_low": pivot_low,
            "atr": atr,
            "width": width,
        }

    def _build_levels(self, reference, top, bottom, grid_count, dist_type="arithmetic"):
        """Asimetrik grid seviyeleri olustur."""
        levels = []
        if reference <= bottom or reference >= top:
            return levels

        half_count = grid_count // 2

        # Üst taraf (SELL)
        upper_range = top - reference
        if upper_range > 0:
            if dist_type == "geometric":
                ratio = (top / reference) ** (1.0 / half_count) if reference > 0 else 1
                for i in range(1, half_count + 1):
                    price = reference * (ratio ** i)
                    levels.append({"index": i, "price": price, "side": "SELL"})
            else:
                step = upper_range / half_count
                for i in range(1, half_count + 1):
                    price = reference + step * i
                    levels.append({"index": i, "price": price, "side": "SELL"})

        # Alt taraf (BUY)
        lower_range = reference - bottom
        if lower_range > 0:
            if dist_type == "geometric":
                ratio = (reference / bottom) ** (1.0 / half_count) if bottom > 0 else 1
                for i in range(1, half_count + 1):
                    price = reference / (ratio ** i)
                    levels.append({"index": -i, "price": price, "side": "BUY"})
            else:
                step = lower_range / half_count
                for i in range(1, half_count + 1):
                    price = reference - step * i
                    levels.append({"index": -i, "price": price, "side": "BUY"})

        return levels

    def evaluate(self, candles, current_position=None):
        # Minimum veri kontrolu
        sma_period = int(self.params.get("smaPeriod", 100))
        pivot_lookback = int(self.params.get("pivotLookback", 100))
        min_needed = max(sma_period, pivot_lookback) + 10

        if not candles or len(candles) < min_needed:
            return {"signal": None, "reason": "Yetersiz veri", "meta": {}}

        current_price = candles[-1]["close"]
        prev_price = candles[-2]["close"]
        candle_time = candles[-1]["time"]

        # Recenter kontrolu
        recenter_hours = float(self.params.get("recenterHours", 24))
        recenter_buffer = float(self.params.get("recenterBuffer", 0.03))
        now = time.time()

        need_recenter = False

        # 1. Zaman bazli
        if self._last_recenter_ts == 0:
            need_recenter = True
        elif recenter_hours > 0 and (now - self._last_recenter_ts) >= recenter_hours * 3600:
            need_recenter = True

        # 2. Range kirilma
        if not need_recenter and self._cached_top and self._cached_bottom:
            buffer_top = self._cached_top * (1 + recenter_buffer)
            buffer_bottom = self._cached_bottom * (1 - recenter_buffer)
            if current_price > buffer_top or current_price < buffer_bottom:
                need_recenter = True

        # Referans ve seviyeleri guncelle
        if need_recenter or self._cached_levels is None:
            ref_data = self._calc_reference(candles)
            if ref_data is None:
                return {"signal": None, "reason": "Referans hesaplanamadi", "meta": {}}

            self._cached_reference = ref_data["reference"]
            self._cached_top = ref_data["top"]
            self._cached_bottom = ref_data["bottom"]
            self._last_recenter_ts = now

            grid_count = int(self.params.get("gridCount", 20))
            dist_type = str(self.params.get("distributionType", "arithmetic")).lower()

            self._cached_levels = self._build_levels(
                ref_data["reference"], ref_data["top"], ref_data["bottom"],
                grid_count, dist_type
            )

            print(f"[GRID] Recenter: ref={ref_data['reference']:.4f} "
                  f"top={ref_data['top']:.4f} bottom={ref_data['bottom']:.4f} "
                  f"({len(self._cached_levels)} seviye)")

        # Meta (chart icin)
        meta = {
            "grid_center": self._cached_reference,
            "grid_top": self._cached_top,
            "grid_bottom": self._cached_bottom,
            "grid_levels": self._cached_levels,
            "grid_type": self.params.get("distributionType", "arithmetic"),
            "mode": self.params.get("mode", "neutral"),
            "recenter_ts": self._last_recenter_ts,
            "candle_time": candle_time,
        }

        # Pozisyon acikken sinyal uretme
        if current_position:
            return {"signal": None, "reason": "Pozisyon acik", "meta": meta}

        # Mod filtresi
        mode = str(self.params.get("mode", "neutral")).lower()
        allow_long = mode in ("neutral", "long")
        allow_short = mode in ("neutral", "short")

        # Grid seviyelerini tara
        for level in self._cached_levels:
            lvl_price = level["price"]
            lvl_side = level["side"]

            if lvl_side == "BUY" and allow_long:
                # Fiyat asagi gecti mi?
                if prev_price > lvl_price >= current_price:
                    return {
                        "signal": "LONG",
                        "reason": f"Grid BUY @ {lvl_price:.6f} (idx {level['index']})",
                        "entry_price": current_price,
                        "meta": meta,
                    }

            elif lvl_side == "SELL" and allow_short:
                # Fiyat yukari gecti mi?
                if prev_price < lvl_price <= current_price:
                    return {
                        "signal": "SHORT",
                        "reason": f"Grid SELL @ {lvl_price:.6f} (idx {level['index']})",
                        "entry_price": current_price,
                        "meta": meta,
                    }

        return {"signal": None, "reason": "Grid tetiklenmedi", "meta": meta}
