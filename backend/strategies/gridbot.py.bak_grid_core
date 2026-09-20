from .base import BaseStrategy


class GridbotScalperStrategy(BaseStrategy):
    """Pivot High/Low tabanlı gridbot scalper (frontend ile aynı mantık)"""
    name = "GRIDBOT"

    def evaluate(self, candles: list, current_position: dict = None) -> dict:
        lookback = int(self.params.get("lookback", 8))
        min_candles = lookback * 2 + 2

        if not candles or len(candles) < min_candles:
            return {"signal": None, "reason": "Yetersiz veri", "meta": {}}

        # Kapanmış mumlar (aktif mumu hariç tut)
        closed = candles[:-1]

        # Pivot noktası: son 'lookback' mumun öncesindeki mum
        pivot_idx = len(closed) - lookback - 1
        if pivot_idx < lookback:
            return {"signal": None, "reason": "Pivot için geçmiş yetersiz", "meta": {}}

        pivot_high = closed[pivot_idx]["high"]
        pivot_low = closed[pivot_idx]["low"]

        # Sol tarafı kontrol et
        is_pivot_high = True
        is_pivot_low = True
        for j in range(1, lookback + 1):
            if closed[pivot_idx]["high"] <= closed[pivot_idx - j]["high"]:
                is_pivot_high = False
            if closed[pivot_idx]["low"] >= closed[pivot_idx - j]["low"]:
                is_pivot_low = False

        # Sağ tarafı kontrol et
        for j in range(1, lookback + 1):
            if closed[pivot_idx]["high"] < closed[pivot_idx + j]["high"]:
                is_pivot_high = False
            if closed[pivot_idx]["low"] > closed[pivot_idx + j]["low"]:
                is_pivot_low = False

        current_price = candles[-1]["close"]
        candle_time = candles[-1]["time"]

        if current_position:
            return {"signal": None, "reason": "Pozisyon açık", "meta": {}}

        if is_pivot_high:
            return {
                "signal": "SHORT",
                "reason": f"Pivot HIGH ({pivot_high:.4f})",
                "entry_price": current_price,
                "meta": {"pivot": pivot_high, "candle_time": candle_time}
            }

        if is_pivot_low:
            return {
                "signal": "LONG",
                "reason": f"Pivot LOW ({pivot_low:.4f})",
                "entry_price": current_price,
                "meta": {"pivot": pivot_low, "candle_time": candle_time}
            }

        return {"signal": None, "reason": "Pivot yok", "meta": {}}