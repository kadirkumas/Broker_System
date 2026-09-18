import numpy as np
from .base import BaseStrategy


def _calc_wma(data: list, period: int) -> list:
    """Ağırlıklı hareketli ortalama (WMA)"""
    result = []
    norm = (period * (period + 1)) / 2
    for i in range(len(data)):
        if i < period - 1:
            result.append(None)
            continue
        window = data[i - period + 1: i + 1]
        if any(v is None for v in window):
            result.append(None)
            continue
        s = sum(window[k] * (k + 1) for k in range(period))
        result.append(s / norm)
    return result


def _calc_hma(data: list, period: int) -> list:
    """Hull Moving Average = WMA(2*WMA(n/2) - WMA(n), sqrt(n))"""
    half = max(1, int(period / 2))
    sqrt_p = max(1, int(np.sqrt(period)))

    wma_full = _calc_wma(data, period)
    wma_half = _calc_wma(data, half)

    diff = []
    for i in range(len(data)):
        if wma_full[i] is None or wma_half[i] is None:
            diff.append(None)
        else:
            diff.append(2 * wma_half[i] - wma_full[i])

    return _calc_wma(diff, sqrt_p)


class HullSRPStrategy(BaseStrategy):
    """HULL/Hl2 - SRP EXIT stratejisi (frontend ile aynı mantık)"""
    name = "HULL_SRP"

    def evaluate(self, candles: list, current_position: dict = None) -> dict:
        if not candles or len(candles) < 30:
            return {"signal": None, "reason": "Yetersiz veri", "meta": {}}

        period = int(self.params.get("period", 10))
        source = self.params.get("source", "hl2")
        long_enabled = self.params.get("longTrade", True)
        short_enabled = self.params.get("shortTrade", False)

        # Kapanmış mumları kullan
        closed = candles[:-1]

        # Kaynak fiyat
        if source == "hl2":
            src = [(c["high"] + c["low"]) / 2 for c in closed]
        elif source == "open":
            src = [c["open"] for c in closed]
        else:
            src = [c["close"] for c in closed]

        hma = _calc_hma(src, period)

        if len(hma) < 3 or hma[-1] is None or hma[-2] is None or hma[-3] is None:
            return {"signal": None, "reason": "HMA hesaplanamadı", "meta": {}}

        current = hma[-1]
        prev = hma[-2]
        prev2 = hma[-3]

        is_rising = current > prev
        turn_green = is_rising and prev <= prev2
        turn_red = (not is_rising) and prev > prev2

        current_price = candles[-1]["close"]
        candle_time = candles[-1]["time"]

        if current_position:
            return {
                "signal": None,
                "reason": f"Pozisyon açık, HMA={current:.4f}",
                "meta": {"hma": current}
            }

        if turn_green and long_enabled:
            return {
                "signal": "LONG",
                "reason": f"HMA dönüş YEŞİL ({prev:.4f}->{current:.4f})",
                "entry_price": current_price,
                "meta": {"hma": current, "candle_time": candle_time}
            }

        if turn_red and short_enabled:
            return {
                "signal": "SHORT",
                "reason": f"HMA dönüş KIRMIZI ({prev:.4f}->{current:.4f})",
                "entry_price": current_price,
                "meta": {"hma": current, "candle_time": candle_time}
            }

        return {
            "signal": None,
            "reason": f"HMA={current:.4f} ({'YEŞİL' if is_rising else 'KIRMIZI'})",
            "meta": {"hma": current}
        }