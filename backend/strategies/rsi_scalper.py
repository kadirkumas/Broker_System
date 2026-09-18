import numpy as np
from .base import BaseStrategy


def _calc_rsi(closes: list, period: int = 7) -> list:
    """Wilder smoothing RSI - frontend ile uyumlu."""
    if len(closes) <= period:
        return [None] * len(closes)

    arr = np.array(closes, dtype=float)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    rsi_values = [None] * period
    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100 - (100 / (1 + rs)))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

    return rsi_values


class RSIScalperStrategy(BaseStrategy):
    name = "RSI_SCALPER"

    def evaluate(self, candles: list, current_position: dict = None) -> dict:
        # 20 kapanmış mum + 1 aktif mum = en az 21 mum gerekli
        if not candles or len(candles) < 21:
            return {"signal": None, "reason": "Yetersiz veri", "meta": {"rsi": None}}

        period = int(self.params.get("period", 7))
        long_op = self.params.get("longOp", "<")
        long_val = float(self.params.get("longVal", 20))
        short_op = self.params.get("shortOp", ">")
        short_val = float(self.params.get("shortVal", 80))

        # ⚡ KRİTİK: Sinyal kontrolü için KAPANMIŞ mumları kullan
        # Son (aktif, kapanmamış) mumu hariç tut
        closed_candles = candles[:-1]
        closes = [c["close"] for c in closed_candles]
        rsi = _calc_rsi(closes, period)

        current_rsi = rsi[-1]
        prev_rsi = rsi[-2] if len(rsi) > 1 else None

        if current_rsi is None or prev_rsi is None:
            return {"signal": None, "reason": "RSI hesaplanamadı", "meta": {"rsi": None}}

        # Emir fiyatı için son (aktif) mumun kapanış fiyatını kullan
        current_price = candles[-1]["close"]
        candle_time = candles[-1]["time"]

        # Açık pozisyon varsa yeni sinyal üretme
        if current_position:
            return {
                "signal": None,
                "reason": f"Pozisyon açık, RSI={current_rsi:.2f}",
                "meta": {"rsi": current_rsi}
            }

        # LONG sinyali (crossing)
        long_trigger = False
        if long_op == "<":
            long_trigger = current_rsi < long_val and prev_rsi >= long_val
        else:
            long_trigger = current_rsi > long_val and prev_rsi <= long_val

        # SHORT sinyali (crossing)
        short_trigger = False
        if short_op == "<":
            short_trigger = current_rsi < short_val and prev_rsi >= short_val
        else:
            short_trigger = current_rsi > short_val and prev_rsi <= short_val

        if long_trigger:
            return {
                "signal": "LONG",
                "reason": f"RSI {prev_rsi:.2f} -> {current_rsi:.2f} (LONG {long_op}{long_val})",
                "entry_price": current_price,
                "meta": {"rsi": current_rsi, "candle_time": candle_time}
            }

        if short_trigger:
            return {
                "signal": "SHORT",
                "reason": f"RSI {prev_rsi:.2f} -> {current_rsi:.2f} (SHORT {short_op}{short_val})",
                "entry_price": current_price,
                "meta": {"rsi": current_rsi, "candle_time": candle_time}
            }

        return {
            "signal": None,
            "reason": f"RSI={current_rsi:.2f} (bekleniyor)",
            "meta": {"rsi": current_rsi}
        }