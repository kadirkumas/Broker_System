"""
ASAP Strategy - As Soon As Possible
====================================
Surekli islem acan, dinamik DCA + PT + AI TTP ile yonetilen strateji.
SL YOK. Korumalar: cooldown + 5 katman filtresi + time-based exit + marjin cap.

F176b - Tam govde.
"""
import time
import numpy as np
from .base import BaseStrategy


# ============================================================
# LOCAL INDICATORS
# ============================================================

def _calc_rsi(closes, period=14):
    """Wilder smoothing RSI."""
    if len(closes) <= period:
        return [None] * len(closes)
    arr = np.array(closes, dtype=float)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    rsi_values = [None] * period
    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100 - (100 / (1 + rs)))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + float(gains[i])) / period
        avg_loss = (avg_loss * (period - 1) + float(losses[i])) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))
    return rsi_values


def _calc_ema(prices, period):
    """EMA - son deger dondur. None padding ile."""
    if len(prices) < period:
        return []
    arr = np.array(prices, dtype=float)
    multiplier = 2.0 / (period + 1)
    ema = [float(np.mean(arr[:period]))]
    for price in arr[period:]:
        ema.append((float(price) - ema[-1]) * multiplier + ema[-1])
    return [None] * (period - 1) + ema


def _calc_atr(highs, lows, closes, period=14):
    """Son ATR degeri."""
    if len(highs) < period + 1:
        return None
    trs = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = float(np.mean(trs[:period]))
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


# ============================================================
# F193b: Shared state (engine + position_manager tarafindan kullanilir)
# ============================================================
_SHARED_COOLDOWNS = {}      # {symbol: {"until": ts, "reason": str}}
_SHARED_ENTRY_COUNTS = {}   # {symbol: int}


def asap_set_cooldown(symbol: str, seconds: int, reason: str):
    """Engine/position_manager tarafindan cagrilir."""
    import time as _t
    _SHARED_COOLDOWNS[symbol] = {"until": _t.time() + seconds, "reason": reason}


def asap_get_cooldown(symbol: str):
    """Returns: {"until": ts, "reason": str} veya None"""
    return _SHARED_COOLDOWNS.get(symbol)


def asap_check_cooldown(symbol: str):
    """Returns: (allowed: bool, remaining_sec: int, reason: str)"""
    import time as _t
    cd = _SHARED_COOLDOWNS.get(symbol)
    if not cd:
        return True, 0, ""
    remaining = int(cd["until"] - _t.time())
    if remaining <= 0:
        _SHARED_COOLDOWNS.pop(symbol, None)
        return True, 0, ""
    return False, remaining, cd.get("reason", "")


def asap_inc_entry(symbol: str) -> int:
    """Entry count artir, yeni degeri dondur."""
    _SHARED_ENTRY_COUNTS[symbol] = _SHARED_ENTRY_COUNTS.get(symbol, 0) + 1
    return _SHARED_ENTRY_COUNTS[symbol]


def asap_get_entry_count(symbol: str) -> int:
    return _SHARED_ENTRY_COUNTS.get(symbol, 0)


def asap_reset(symbol: str):
    _SHARED_COOLDOWNS.pop(symbol, None)
    _SHARED_ENTRY_COUNTS.pop(symbol, None)



# ============================================================
# ASAP STRATEGY
# ============================================================

class ASAPStrategy(BaseStrategy):
    name = "ASAP"

    DEFAULTS = {
        # F194a: tek katman — EMA200 trend
        "emaSlowPeriod": 200,
        # Cooldown (1 mum = 60 sn)
        "cooldownAfterTP": 1,
        "cooldownAfterExit": 1,
        "cooldownAfter3rdEntry": 1,
        # Davranis
        "maxHoldHours": 24,
        "maxPosPerSymbol": 1,
        # Kullanilmayan (uyumluluk icin)
        "emaFastPeriod": 20,
        "rsiPeriod": 14,
        "atrPeriod": 14,
    }

    def __init__(self, params: dict):
        super().__init__(params)
        self.cfg = dict(self.DEFAULTS)
        self.cfg.update(params or {})
        # Engine tarafindan set edilebilir (_symbol cfg icine konur)
        self._symbol = self.cfg.get("_symbol", "")
        # Cooldown state
        self._cooldown_until = 0.0
        self._cooldown_reason = None
        self._entry_count = 0

    # ------------------------------------------------------------------
    # ANA FONKSIYON
    # ------------------------------------------------------------------
    def evaluate(self, candles: list, current_position: dict = None) -> dict:
        """F194a: Sadece EMA200 trend. 5 katman kaldirildi."""
        symbol = self._symbol or (current_position.get("symbol") if current_position else "")

        # 1. Veri kontrolu (EMA200 icin 210 mum gerekli)
        need = self.cfg["emaSlowPeriod"] + 10
        n = len(candles) if candles else 0
        if not candles or n < need:
            return {"signal": None,
                    "reason": f"[ASAP] Yetersiz veri ({n}<{need})",
                    "meta": {}}

        # 2. Pozisyon var mi? (maxHoldHours kontrolu — degismedi)
        if current_position:
            return self._check_time_exit(candles, current_position)

        # 3. Cooldown (shared)
        try:
            from backend.strategies.asap import asap_check_cooldown
            ok, rem, rsn = asap_check_cooldown(symbol)
            if not ok:
                return {"signal": None,
                        "reason": f"[ASAP] Cooldown ({rsn}) {rem}s",
                        "meta": {}}
        except Exception:
            pass

        # 4. Trend: fiyat vs EMA200
        closes = [c["close"] for c in candles]
        ema200 = _calc_ema(closes, self.cfg["emaSlowPeriod"])
        if not ema200 or ema200[-1] is None:
            return {"signal": None, "reason": "[ASAP] EMA200 hesaplanamadi", "meta": {}}

        cur = closes[-1]
        ema_val = ema200[-1]
        diff_pct = (cur - ema_val) / ema_val * 100

        if cur > ema_val:
            side = "LONG"
        elif cur < ema_val:
            side = "SHORT"
        else:
            return {"signal": None, "reason": "[ASAP] Fiyat=EMA200", "meta": {}}

        # 5. Sinyal
        return {
            "signal": side,
            "reason": f"[ASAP] {side} @ {cur:.6f} | fiyat vs EMA200: %{diff_pct:+.3f}",
            "entry_price": cur,
            "meta": {"side": side, "ema200": ema_val, "ema_diff_pct": diff_pct},
        }

    def on_tp(self, symbol: str = None):
        cd = self.cfg["cooldownAfterTP"] * 60
        self._cooldown_until = time.time() + cd
        self._cooldown_reason = "tp"
        print(f"[ASAP] {self._symbol or symbol} on_tp -> cooldown {self.cfg['cooldownAfterTP']} dk")

    def on_exit(self, symbol: str = None):
        cd = self.cfg["cooldownAfterExit"] * 60
        self._cooldown_until = time.time() + cd
        self._cooldown_reason = "exit"
        print(f"[ASAP] {self._symbol or symbol} on_exit -> cooldown {self.cfg['cooldownAfterExit']} dk")

    def on_entry(self, symbol: str = None):
        self._entry_count += 1
        if self._entry_count >= 3:
            cd = self.cfg["cooldownAfter3rdEntry"] * 60
            self._cooldown_until = max(self._cooldown_until, time.time() + cd)
            self._cooldown_reason = "entry3"
            print(f"[ASAP] {self._symbol or symbol} 3. giris -> cooldown {self.cfg['cooldownAfter3rdEntry']} dk")

    def get_state_snapshot(self, symbol: str = None) -> dict:
        return {
            "symbol": self._symbol or symbol,
            "cooldown_until": self._cooldown_until,
            "cooldown_reason": self._cooldown_reason,
            "cooldown_remaining_sec": max(0, int(self._cooldown_until - time.time())),
            "entry_count": self._entry_count,
        }

    def reset_symbol(self, symbol: str = None):
        self._cooldown_until = 0.0
        self._cooldown_reason = None
        self._entry_count = 0

    # ------------------------------------------------------------------
    # YARDIMCI METODLAR
    # ------------------------------------------------------------------
    def _check_cooldown(self):
        now = time.time()
        if now < self._cooldown_until:
            remaining = int(self._cooldown_until - now)
            return False, f"[ASAP] Cooldown ({self._cooldown_reason}) - {remaining}s kaldi"
        return True, ""

    def _check_time_exit(self, candles, pos):
        """Pozisyon maxHoldHours asildi VE zararda ise CLOSE sinyali."""
        entry_time = pos.get("entry_time") or 0
        if entry_time <= 0:
            return {"signal": None,
                    "reason": "[ASAP] Pozisyon acik, entry_time yok",
                    "meta": {}}

        age_h = (time.time() - entry_time) / 3600.0
        max_h = self.cfg["maxHoldHours"]

        if age_h < max_h:
            return {"signal": None,
                    "reason": f"[ASAP] Pozisyon acik ({age_h:.1f}s < {max_h}s)",
                    "meta": {}}

        avg = float(pos.get("avg_price") or 0)
        cur = candles[-1]["close"]
        tt = pos.get("trade_type", "BUY")
        if avg <= 0:
            return {"signal": None, "reason": "[ASAP] avg_price yok", "meta": {}}

        if tt == "BUY":
            pnl_pct = (cur - avg) / avg * 100
        else:
            pnl_pct = (avg - cur) / avg * 100

        if pnl_pct < 0:
            return {
                "signal": "CLOSE",
                "reason": f"[ASAP] TIME-EXIT {age_h:.1f}s zararda ({pnl_pct:.2f}%)",
                "meta": {"time_exit": True, "age_hours": age_h, "pnl_pct": pnl_pct},
            }
        return {"signal": None,
                "reason": f"[ASAP] {age_h:.1f}s ama karli ({pnl_pct:.2f}%), PT/TTP bekle",
                "meta": {}}

    def _detect_side(self, candles):
        """EMA20 vs EMA50 -> 'LONG'|'SHORT'|None"""
        closes = [c["close"] for c in candles]
        ema_f = _calc_ema(closes, self.cfg["emaFastPeriod"])
        ema_s = _calc_ema(closes, self.cfg["emaSlowPeriod"])
        if not ema_f or not ema_s or ema_f[-1] is None or ema_s[-1] is None:
            return None
        diff_pct = (ema_f[-1] - ema_s[-1]) / ema_s[-1] * 100
        neutral = self.cfg["trendNeutralPct"]
        if diff_pct > neutral:
            return "LONG"
        elif diff_pct < -neutral:
            return "SHORT"
        return None

    def _passes_filters(self, candles, side):
        """5 katman: anti-chase, overextension, RSI, range (trend zaten detect)."""
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        cur = closes[-1]
        meta = {}

        # 1. Anti-chase
        ml = self.cfg["moveLookback"]
        if len(closes) > ml:
            old = closes[-ml - 1]
            move_pct = abs((cur - old) / old * 100) if old > 0 else 0
            meta["move_pct"] = move_pct
            if move_pct > self.cfg["maxMoveLastHour"]:
                return False, (f"[ASAP] Anti-chase: son {ml} mumda "
                               f"%{move_pct:.2f} > %{self.cfg['maxMoveLastHour']}"), meta

        # 2. Overextension
        ema_f = _calc_ema(closes, self.cfg["emaFastPeriod"])
        if ema_f and ema_f[-1]:
            ema_dist = abs(cur - ema_f[-1]) / ema_f[-1] * 100
            meta["ema_dist"] = ema_dist
            if ema_dist > self.cfg["maxEmaDistance"]:
                return False, (f"[ASAP] Overextension: EMA20'den "
                               f"%{ema_dist:.2f} > %{self.cfg['maxEmaDistance']}"), meta

        # 3. RSI
        rsi = _calc_rsi(closes, self.cfg["rsiPeriod"])
        rsi_val = rsi[-1] if rsi else None
        if rsi_val is not None:
            meta["rsi"] = rsi_val
            if side == "LONG" and rsi_val > self.cfg["rsiMaxBuy"]:
                return False, (f"[ASAP] RSI {rsi_val:.1f} > {self.cfg['rsiMaxBuy']} "
                               f"(LONG overbought)"), meta
            if side == "SHORT" and rsi_val < self.cfg["rsiMinSell"]:
                return False, (f"[ASAP] RSI {rsi_val:.1f} < {self.cfg['rsiMinSell']} "
                               f"(SHORT oversold)"), meta

        # 4. Range position
        rl = self.cfg["rangeLookback"]
        if len(candles) >= rl:
            recent_high = max(highs[-rl:])
            recent_low = min(lows[-rl:])
            rng = recent_high - recent_low
            if rng > 0:
                range_pos = (cur - recent_low) / rng
                meta["range_pos"] = range_pos
                meta["range_high"] = recent_high
                meta["range_low"] = recent_low
                if side == "LONG" and range_pos > self.cfg["rangeMaxBuy"]:
                    return False, (f"[ASAP] Range pos {range_pos:.2f} > "
                                   f"{self.cfg['rangeMaxBuy']} (LONG ust yari)"), meta
                if side == "SHORT" and range_pos < self.cfg["rangeMinSell"]:
                    return False, (f"[ASAP] Range pos {range_pos:.2f} < "
                                   f"{self.cfg['rangeMinSell']} (SHORT alt yari)"), meta

        return True, "[ASAP] 5 katman gecti", meta
