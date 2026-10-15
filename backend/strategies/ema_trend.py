# -*- coding: utf-8 -*-
"""
EmaTrendStrategy
================
Basit EMA kesisim:
  - Kapanis > EMA(N) -> LONG
  - Kapanis < EMA(N) -> SHORT

DCA + AI TTP + Partial TP devralir (position_manager).
Cikis: TP / AI TTP / Partial TP / SL
"""

import numpy as np
from .base import BaseStrategy


def _calc_ema(prices: list, period: int) -> list:
    """Klasik EMA (ilk deger SMA, sonra EMA formulu)."""
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


class EmaTrendStrategy(BaseStrategy):
    name = "EMA_TREND"

    def evaluate(self, candles: list, current_position: dict = None) -> dict:
        # Parametreler
        ema_period = int(self.params.get("emaPeriod", 200))
        long_enabled = bool(self.params.get("longTrade", True))
        short_enabled = bool(self.params.get("shortTrade", True))

        # Yeterli veri
        need = ema_period + 5
        if not candles or len(candles) < need:
            return {
                "signal": None,
                "reason": f"Yetersiz veri ({len(candles)}/{need})",
                "meta": {"ema": None, "ema_period": ema_period},
            }

        # Kapanmis mumlar (aktif mum haric)
        closed_candles = candles[:-1]
        closes = [c["close"] for c in closed_candles]

        # EMA hesapla
        ema = _calc_ema(closes, ema_period)
        current_ema = ema[-1] if ema else None
        if current_ema is None:
            return {
                "signal": None,
                "reason": "EMA hesaplanamadi",
                "meta": {"ema": None, "ema_period": ema_period},
            }

        # Aktif mum fiyati (emir icin)
        current_price = candles[-1]["close"]
        candle_time = candles[-1]["time"]

        # Kapanmis son mum fiyati (sinyal icin)
        last_closed_price = closed_candles[-1]["close"]

        meta = {
            "ema": current_ema,
            "ema_period": ema_period,
            "candle_time": candle_time,
            "last_close": last_closed_price,
        }

        # Pozisyon aciksa yeni sinyal yok
        if current_position:
            return {
                "signal": None,
                "reason": f"Pozisyon acik, EMA{ema_period}={current_ema:.6f}",
                "meta": meta,
            }

        # Sinyal: close > EMA -> LONG, close < EMA -> SHORT
        if last_closed_price > current_ema and long_enabled:
            dev = (last_closed_price - current_ema) / current_ema * 100
            return {
                "signal": "LONG",
                "reason": f"EMA{ema_period} ustunde: {last_closed_price:.6f} > {current_ema:.6f} (+{dev:.2f}%)",
                "entry_price": current_price,
                "meta": meta,
            }

        if last_closed_price < current_ema and short_enabled:
            dev = (current_ema - last_closed_price) / current_ema * 100
            return {
                "signal": "SHORT",
                "reason": f"EMA{ema_period} altinda: {last_closed_price:.6f} < {current_ema:.6f} (-{dev:.2f}%)",
                "entry_price": current_price,
                "meta": meta,
            }

        return {
            "signal": None,
            "reason": f"Esitlik veya filtre disi (EMA={current_ema:.6f})",
            "meta": meta,
        }
