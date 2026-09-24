import numpy as np

def calculate_hl2(highs: list, lows: list) -> list:
    """(High + Low) / 2 medyan fiyat hesabı"""
    return [(h + l) / 2.0 for h, l in zip(highs, lows)]

def calculate_wma(data: list, period: int) -> list:
    """Ağırlıklı Hareketli Ortalama (WMA)"""
    if len(data) < period:
        return []
    
    weights = np.arange(1, period + 1)
    wma = []
    for i in range(period - 1, len(data)):
        window = data[i - period + 1 : i + 1]
        wma.append(np.dot(window, weights) / weights.sum())
    return wma

def calculate_hull_ma(prices: list, period: int = 9) -> list:
    """
    HULL MA = WMA(2 * WMA(n/2) - WMA(n)), sqrt(n)
    """
    if len(prices) < period:
        return []

    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))

    wma_half = calculate_wma(prices, half_period)
    wma_full = calculate_wma(prices, period)

    # Boyutları eşitlemek için kesişim boyutu
    min_len = min(len(wma_half), len(wma_full))
    wma_half = wma_half[-min_len:]
    wma_full = wma_full[-min_len:]

    diff = [2 * h - f for h, f in zip(wma_half, wma_full)]
    return calculate_wma(diff, sqrt_period)

import numpy as np

def calculate_hl2(highs: list, lows: list) -> list:
    return [(h + l) / 2.0 for h, l in zip(highs, lows)]

def calculate_wma(data: list, period: int) -> list:
    if len(data) < period:
        return []
    weights = np.arange(1, period + 1)
    wma = []
    for i in range(period - 1, len(data)):
        window = data[i - period + 1 : i + 1]
        wma.append(np.dot(window, weights) / weights.sum())
    return wma

def calculate_hull_ma(prices: list, period: int = 9) -> list:
    if len(prices) < period:
        return []
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    wma_half = calculate_wma(prices, half_period)
    wma_full = calculate_wma(prices, period)
    min_len = min(len(wma_half), len(wma_full))
    wma_half = wma_half[-min_len:]
    wma_full = wma_full[-min_len:]
    diff = [2 * h - f for h, f in zip(wma_half, wma_full)]
    return calculate_wma(diff, sqrt_period)

def calculate_rsi(prices: list, period: int = 7) -> float:
    """TradingView uyumlu Wilder Smoothing RSI (Periyot: 7)"""
    if len(prices) <= period:
        return 50.0

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(float(100.0 - (100.0 / (1.0 + rs))), 2)

def calculate_ema(prices: list, period: int = 200) -> list:
    """
    Exponential Moving Average (EMA).
    Ilk deger SMA, sonra klasik EMA formul.

    Args:
        prices: kapanis fiyatlari listesi
        period: EMA periyodu (varsayilan 200)

    Returns:
        EMA degerleri listesi (ilk period-1 eleman None)
    """
    if not prices or len(prices) < period:
        return [None] * len(prices)

    import numpy as _np
    arr = _np.array(prices, dtype=float)
    ema = [None] * (period - 1)

    # Ilk EMA = SMA
    first_sma = float(_np.mean(arr[:period]))
    ema.append(first_sma)

    # Sonraki EMA'lar
    multiplier = 2.0 / (period + 1)
    prev_ema = first_sma
    for i in range(period, len(arr)):
        curr = (arr[i] - prev_ema) * multiplier + prev_ema
        ema.append(curr)
        prev_ema = curr

    return ema

