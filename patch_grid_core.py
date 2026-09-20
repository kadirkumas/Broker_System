import shutil
import os

GRID_SRC = 'backend/strategies/gridbot.py'
SE_SRC = 'backend/strategy_engine.py'

for src in [GRID_SRC, SE_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_grid_core')
    print(f"[1/5] Yedek: {src}.bak_grid_core")

changes = 0

# ============================================================
# 1. gridbot.py: TAMAMEN YENI (Gerçek Grid)
# ============================================================
new_grid = '''from .base import BaseStrategy


def _calc_sma(values, period):
    """Basit hareketli ortalama."""
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        result.append(sum(window) / period)
    return result


def _calc_atr(candles, period=14):
    """Wilder smoothing ATR."""
    if len(candles) < period + 1:
        return [None] * len(candles)
    
    trs = [None]  # ilk mum için TR yok
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    
    result = [None] * period
    if len(trs) <= period:
        return result
    
    first_atr = sum(trs[1:period + 1]) / period
    result.append(first_atr)
    
    for i in range(period + 1, len(trs)):
        atr = (result[-1] * (period - 1) + trs[i]) / period
        result.append(atr)
    
    return result


class GridbotScalperStrategy(BaseStrategy):
    """
    Gercek Grid (izgara) stratejisi.
    
    - Merkez: SMA(period)
    - Genislik: ATR(atrPeriod) x atrMultiplier
    - gridCount kadar seviye (merkez alti BUY, merkez ustu SELL)
    - Fiyat BUY seviyesini asagi gecerse -> LONG
    - Fiyat SELL seviyesini yukari gecerse -> SHORT
    """
    name = "GRIDBOT"

    def __init__(self, params):
        super().__init__(params)
        self.gridType = str(params.get("gridType", "geometric")).lower()
        self.gridCount = int(params.get("gridCount", 20))
        self.smaPeriod = int(params.get("smaPeriod", 100))
        self.atrPeriod = int(params.get("atrPeriod", 14))
        self.atrMultiplier = float(params.get("atrMultiplier", 5))

    def _build_grid(self, center, width):
        """Merkez etrafinda simetrik grid seviyeleri uretir."""
        levels = []
        half = self.gridCount // 2
        if half == 0:
            half = 1

        if self.gridType == "geometric":
            # Geometrik: esit % araliklarla
            half_pct = (width / 2.0) / center if center > 0 else 0
            step_pct = half_pct / half if half > 0 else 0
            for i in range(-half, half + 1):
                price = center * ((1 + step_pct) ** i)
                if i < 0:
                    side = "BUY"
                elif i > 0:
                    side = "SELL"
                else:
                    side = "CENTER"
                levels.append({"index": i, "price": price, "side": side})
        else:
            # Aritmetik: esit mutlak araliklarla
            step = (width / 2.0) / half if half > 0 else 0
            for i in range(-half, half + 1):
                price = center + (i * step)
                if price <= 0:
                    continue
                if i < 0:
                    side = "BUY"
                elif i > 0:
                    side = "SELL"
                else:
                    side = "CENTER"
                levels.append({"index": i, "price": price, "side": side})
        return levels

    def evaluate(self, candles: list, current_position: dict = None) -> dict:
        min_candles = max(self.smaPeriod, self.atrPeriod) + 5
        if not candles or len(candles) < min_candles:
            return {"signal": None, "reason": "Yetersiz veri", "meta": {}}

        closes = [c["close"] for c in candles]

        # SMA ve ATR hesapla
        sma_values = _calc_sma(closes, self.smaPeriod)
        atr_values = _calc_atr(candles, self.atrPeriod)

        current_sma = sma_values[-1] if sma_values else None
        current_atr = atr_values[-1] if atr_values else None

        if current_sma is None or current_atr is None or current_sma <= 0:
            return {"signal": None, "reason": "SMA/ATR hesaplanamadi", "meta": {}}

        # Grid olustur
        center = current_sma
        width = current_atr * self.atrMultiplier
        grid_levels = self._build_grid(center, width)

        current_price = candles[-1]["close"]
        prev_price = candles[-2]["close"]
        candle_time = candles[-1]["time"]

        meta = {
            "grid_center": center,
            "grid_width": width,
            "grid_levels": grid_levels,
            "grid_type": self.gridType,
            "sma": current_sma,
            "atr": current_atr,
            "candle_time": candle_time,
        }

        # Pozisyon acikken sinyal uretme
        if current_position:
            return {"signal": None, "reason": "Pozisyon acik", "meta": meta}

        # Grid seviyelerini tara
        for level in grid_levels:
            lvl_price = level["price"]
            lvl_side = level["side"]

            if lvl_side == "BUY":
                # Fiyat bu BUY seviyesini ASAGI gecti mi?
                if prev_price > lvl_price >= current_price:
                    return {
                        "signal": "LONG",
                        "reason": f"Grid BUY @ {lvl_price:.6f} (idx {level['index']})",
                        "entry_price": current_price,
                        "meta": meta,
                    }

            elif lvl_side == "SELL":
                # Fiyat bu SELL seviyesini YUKARI gecti mi?
                if prev_price < lvl_price <= current_price:
                    return {
                        "signal": "SHORT",
                        "reason": f"Grid SELL @ {lvl_price:.6f} (idx {level['index']})",
                        "entry_price": current_price,
                        "meta": meta,
                    }

        return {"signal": None, "reason": "Grid tetiklenmedi", "meta": meta}
'''

with open(GRID_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(new_grid.replace('\n', '\r\n'))
changes += 1
print("[2/5] gridbot.py: Gercek grid stratejisi yazildi")

# ============================================================
# 2. strategy_engine.py: DEFAULT_CONFIG guncelle
# ============================================================
with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

old_grid_cfg = '''        "GRIDBOT": {
            "enabled": False,
            "interval": "15m",
            "lookback": 8,
            "baseOrder": 10,
            "takeProfit": 1.0, "trailing": 0.2, "stopLoss": 3.0,
            "partialTPEnabled": False, "partialTPPercent": 50,
            "partialTPKeepDCA": True
        }'''

new_grid_cfg = '''        "GRIDBOT": {
            "enabled": False,
            "interval": "15m",
            "gridType": "geometric",
            "gridCount": 20,
            "smaPeriod": 100,
            "atrPeriod": 14,
            "atrMultiplier": 5,
            "baseOrder": 10,
            "leverage": 5,
            "takeProfit": 0.6, "trailing": 0.15, "stopLoss": 8.0,
            "useDCA": True, "volMultiplier": 1.5, "steps": "1, 2, 3, 5",
            "partialTPEnabled": True, "partialTPPercent": 50,
            "partialTPKeepDCA": True
        }'''

if 'gridCount' in se:
    print("[3/5] strategy_engine.py: GRIDBOT config zaten yeni (atlandi)")
elif old_grid_cfg in se:
    se = se.replace(old_grid_cfg, new_grid_cfg, 1)
    changes += 1
    print("[3/5] strategy_engine.py: GRIDBOT yeni config eklendi")
else:
    print("[3/5] UYARI: GRIDBOT DEFAULT_CONFIG blogu bulunamadi (atlandi)")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

print("[4/5] Kaydedildi")
print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - GridbotScalperStrategy -> Gercek grid (SMA+ATR bazli)")
print("  - gridType: geometric/arithmetic")
print("  - gridCount, smaPeriod, atrPeriod, atrMultiplier")
print("  - meta.grid_levels chart icin donuyor")
print()
print("NOT: bot_config.json'da eski 'lookback' alani kalirsa ignore edilir.")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print("  2. Test: /api/engine/config cagirip GRIDBOT alanlarini kontrol et")
print()
print("Geri donmek icin:")
for src in [GRID_SRC, SE_SRC]:
    print(f"  Copy-Item {src}.bak_grid_core {src} -Force")