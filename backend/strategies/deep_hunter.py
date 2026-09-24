# -*- coding: utf-8 -*-
"""
DeepHunterStrategy
==================
Trend bolgesine gore dip al / tepe sat.

Mantik:
  EMA(N) trend belirleyici
  LONG  : fiyat < EMA*(1 - X%)  VE  RSI < Y   (dip)
  SHORT : fiyat > EMA*(1 + X%)  VE  RSI > Z   (tepe)

Cikis: position_manager (TP / Trailing / Partial TP)
DCA : Klasik (initial_price bazli, config 'steps')
"""

import numpy as np
from .base import BaseStrategy


def _calc_rsi(closes: list, period: int = 7) -> list:
    """Wilder smoothing RSI."""
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


def _calc_ema(prices: list, period: int) -> list:
    """Basit EMA (indicators.calculate_ema ile ayni mantik, izole)."""
    if not prices or len(prices) < period:
        return [None] * len(prices)

    arr = np.array(prices, dtype=float)
    ema = [None] * (period - 1)
    first_sma = float(np.mean(arr[:period]))
    ema.append(first_sma)

    multiplier = 2.0 / (period + 1)
    prev = first_sma
    for i in range(period, len(arr)):
        curr = (arr[i] - prev) * multiplier + prev
        ema.append(curr)
        prev = curr
    return ema


class DeepHunterStrategy(BaseStrategy):
    name = "DEEP_HUNTER"

    def evaluate(self, candles: list, current_position: dict = None) -> dict:
        # Parametreler
        ema_period   = int(self.params.get("emaPeriod", 200))
        rsi_period   = int(self.params.get("rsiPeriod", 7))
        long_trig_pct  = float(self.params.get("longTriggerPct", 5.5)) / 100.0
        short_trig_pct = float(self.params.get("shortTriggerPct", 15.0)) / 100.0
        long_rsi_max   = float(self.params.get("longRsiMax", 30))
        short_rsi_min  = float(self.params.get("shortRsiMin", 75))
        long_enabled   = bool(self.params.get("longTrade", True))
        short_enabled  = bool(self.params.get("shortTrade", True))

        # Yeterli veri
        need = max(ema_period, rsi_period) + 5
        if not candles or len(candles) < need:
            return {
                "signal": None,
                "reason": f"Yetersiz veri ({len(candles)}/{need})",
                "meta": {"ema": None, "rsi": None}
            }

        # Kapali mumlar (aktif mum haric)
        closed_candles = candles[:-1]
        closes = [c["close"] for c in closed_candles]

        # Hesaplamalar
        ema = _calc_ema(closes, ema_period)
        rsi = _calc_rsi(closes, rsi_period)
        current_ema = ema[-1] if ema else None
        current_rsi = rsi[-1] if rsi else None

        if current_ema is None or current_rsi is None:
            return {
                "signal": None,
                "reason": "Hesaplama basarisiz",
                "meta": {"ema": None, "rsi": None}
            }

        # Aktif mum fiyati
        current_price = candles[-1]["close"]
        candle_time   = candles[-1]["time"]

        # Pozisyon varsa yeni sinyal yok (DCA position_manager'da)
        if current_position:
            return {
                "signal": None,
                "reason": f"Pozisyon acik, EMA={current_ema:.4f} RSI={current_rsi:.1f}",
                "meta": {"ema": current_ema, "rsi": current_rsi, "candle_time": candle_time}
            }

        # Tetikleyici fiyatlar
        long_trigger_price  = current_ema * (1 - long_trig_pct)
        short_trigger_price = current_ema * (1 + short_trig_pct)

        # Kosullar
        long_cond  = (current_price < long_trigger_price)  and (current_rsi < long_rsi_max)  and long_enabled
        short_cond = (current_price > short_trigger_price) and (current_rsi > short_rsi_min) and short_enabled

        if long_cond:
            deviation = (current_ema - current_price) / current_ema * 100
            return {
                "signal": "LONG",
                "reason": f"DIP: EMA-{deviation:.2f}%, RSI={current_rsi:.1f}<{long_rsi_max}",
                "entry_price": current_price,
                "meta": {"ema": current_ema, "rsi": current_rsi, "candle_time": candle_time,
                         "deviation_pct": -deviation}
            }

        if short_cond:
            deviation = (current_price - current_ema) / current_ema * 100
            return {
                "signal": "SHORT",
                "reason": f"TEPE: EMA+{deviation:.2f}%, RSI={current_rsi:.1f}>{short_rsi_min}",
                "entry_price": current_price,
                "meta": {"ema": current_ema, "rsi": current_rsi, "candle_time": candle_time,
                         "deviation_pct": deviation}
            }

        # Sinyal yok
        deviation = (current_price - current_ema) / current_ema * 100
        return {
            "signal": None,
            "reason": f"EMA={current_ema:.4f} ({deviation:+.2f}%) RSI={current_rsi:.1f}",
            "meta": {"ema": current_ema, "rsi": current_rsi, "deviation_pct": deviation}
        }
