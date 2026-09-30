# -*- coding: utf-8 -*-
"""
TrendFollowStrategy - Donchian Breakout + EMA Filter
=====================================================
Trend takip stratejisi. Kirilim + trend onayi ile giris.

Mantik:
  1. Fiyat son N mumun en yuksegini kirarsa (Donchian breakout)
  2. VE EMA_fast > EMA_slow ise (trend yukari)
  3. -> LONG acilir
  Ayni sekilde ters yonde SHORT.

Cikis: position_manager (TP/SL/AI-TTP)
DCA : YOK (trend stratejisi)
"""
import numpy as np
from .base import BaseStrategy


def _ema(prices, period):
    """Basit EMA serisi."""
    n = len(prices)
    if n < period:
        return [None] * n
    arr = np.array(prices, dtype=float)
    k = 2.0 / (period + 1)
    out = [None] * (period - 1)
    sma = float(np.mean(arr[:period]))
    out.append(sma)
    prev = sma
    for i in range(period, n):
        cur = (arr[i] - prev) * k + prev
        out.append(cur)
        prev = cur
    return out


def _atr(candles, period=14):
    """Son ATR degeri."""
    n = len(candles)
    if n < period + 1:
        return None
    trs = []
    for i in range(1, n):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr


class TrendFollowStrategy(BaseStrategy):
    name = "TREND_FOLLOW"

    def evaluate(self, candles, current_position=None, **kwargs):
        # Parametreler
        donchian = int(self.params.get("donchianPeriod", 20))
        ema_fast_p = int(self.params.get("emaFast", 20))
        ema_slow_p = int(self.params.get("emaSlow", 50))
        long_enabled = bool(self.params.get("longTrade", True))
        short_enabled = bool(self.params.get("shortTrade", True))
        confirm_close = bool(self.params.get("confirmClose", True))
        min_breakout_pct = float(self.params.get("minBreakoutPct", 0.0))

        # Yeterli veri
        need = max(donchian, ema_fast_p, ema_slow_p) + 5
        if not candles or len(candles) < need:
            return {
                "signal": None,
                "reason": f"Yetersiz veri ({len(candles)}/{need})",
                "meta": {}
            }

        # Aktif mum haric, kapanmis mumlar
        closed = candles[:-1]
        closes = [c["close"] for c in closed]
        highs = [c["high"] for c in closed]
        lows = [c["low"] for c in closed]

        # EMA serileri
        ema_f = _ema(closes, ema_fast_p)
        ema_s = _ema(closes, ema_slow_p)
        if not ema_f or not ema_s or ema_f[-1] is None or ema_s[-1] is None:
            return {"signal": None, "reason": "EMA hesaplanamadi", "meta": {}}

        ef = ema_f[-1]
        es = ema_s[-1]

        # Donchian: onceki N mumun high/low'u (aktif mum haric)
        prev_highs = highs[-donchian:]
        prev_lows = lows[-donchian:]
        donchian_high = max(prev_highs)
        donchian_low = min(prev_lows)

        # Aktif mum
        current_price = candles[-1]["close"]
        candle_time = candles[-1]["time"]

        # ATR (SL onerisi icin meta)
        atr_val = _atr(closed, 14)

        meta = {
            "ema_fast": ef,
            "ema_slow": es,
            "donchian_high": donchian_high,
            "donchian_low": donchian_low,
            "atr": atr_val,
            "candle_time": candle_time,
        }

        # Acik pozisyon varsa sinyal uretme
        if current_position:
            return {
                "signal": None,
                "reason": f"Pozisyon acik (EF={ef:.4f}, ES={es:.4f})",
                "meta": meta,
            }

        # Breakout kontrolu
        # LONG: EMA_fast > EMA_slow VE fiyat > donchian_high
        trend_up = ef > es
        trend_down = ef < es

        # min breakout buffer
        long_level = donchian_high * (1 + min_breakout_pct / 100.0)
        short_level = donchian_low * (1 - min_breakout_pct / 100.0)

        if confirm_close:
            # Kapanis bazli breakout
            long_break = current_price > long_level
            short_break = current_price < short_level
        else:
            # Aktif mumun high/low bazli
            long_break = candles[-1]["high"] > long_level
            short_break = candles[-1]["low"] < short_level

        if long_break and trend_up and long_enabled:
            return {
                "signal": "LONG",
                "reason": f"Donchian breakout UP @ {donchian_high:.4f} | EF>ES",
                "entry_price": current_price,
                "meta": meta,
            }

        if short_break and trend_down and short_enabled:
            return {
                "signal": "SHORT",
                "reason": f"Donchian breakout DOWN @ {donchian_low:.4f} | EF<ES",
                "entry_price": current_price,
                "meta": meta,
            }

        # Sinyal yok
        trend_txt = "UP" if trend_up else "DOWN"
        return {
            "signal": None,
            "reason": f"Trend {trend_txt} | Break bekleniyor (H:{donchian_high:.4f} L:{donchian_low:.4f})",
            "meta": meta,
        }
