# -*- coding: utf-8 -*-
"""
FundingArbitrageStrategy
========================
Funding rate'lerden para kazan.

Mantik:
  Funding (+) ve yuksek  -> SHORT ac (odeme AL)
  Funding (-) ve yuksek  -> LONG  ac (odeme AL)

Kapanis: position_manager (TP/SL/max sure).
Bu strateji DCA ve trailing KULLANMAZ - sabit TP/SL.

Not: Testnet uyumlu "pure funding" modu.
Canlida "spot+futures hedge" modu eklenebilir (Faz 2).
"""
import time
from .base import BaseStrategy


class FundingArbitrageStrategy(BaseStrategy):
    name = "FUNDING_ARBITRAGE"

    def evaluate(self, candles=None, current_position=None, **kwargs):
        """
        candles KULLANILMAZ (funding stratejisi).
        kwargs['funding_data'] = [
            {'symbol': 'BTCUSDT', 'funding': 0.0008, 'next_ts': 1234567890},
            ...
        ]
        """
        funding_data = kwargs.get('funding_data', [])
        if not funding_data:
            return {
                "signal": None,
                "reason": "Funding verisi yok",
                "meta": {"funding_count": 0}
            }

        # ---- Parametreler ----
        min_funding_pct = float(self.params.get('minFundingRate', 0.05))
        min_funding = min_funding_pct / 100.0  # % -> ondalik
        # max: asiri funding = supheli / data hatasi
        max_funding_pct = float(self.params.get('maxFundingRate', 1.0))
        max_funding = max_funding_pct / 100.0
        long_enabled = bool(self.params.get('longEnabled', True))
        short_enabled = bool(self.params.get('shortEnabled', True))
        mode = str(self.params.get('mode', 'both')).lower()

        if mode == 'long':
            short_enabled = False
        elif mode == 'short':
            long_enabled = False

        # ---- Aktif pozisyon varsa sinyal uretme ----
        if current_position:
            return {
                "signal": None,
                "reason": "Pozisyon acik (%s)" % current_position.get('trade_type', '?'),
                "meta": {"funding_count": len(funding_data)}
            }

        # ---- En yuksek |funding| bul (esik ustu) ----
        best = None
        best_abs = 0.0
        skipped_high = 0
        for item in funding_data:
            try:
                fr = float(item.get('funding', 0))
            except Exception:
                continue
            fr_abs = abs(fr)
            # cok yuksek = supheli (data hatasi, likidite sifir vs)
            if fr_abs > max_funding:
                skipped_high += 1
                continue
            if fr_abs > best_abs and fr_abs >= min_funding:
                best = item
                best_abs = fr_abs

        if not best:
            _r = "Funding esik altinda (< %%%.3f)" % (min_funding * 100)
            if skipped_high > 0:
                _r += " | %d sembol asiri yuksek atlandi" % skipped_high
            return {
                "signal": None,
                "reason": _r,
                "meta": {"funding_count": len(funding_data), "skipped_high": skipped_high}
            }

        fr = float(best.get('funding', 0))
        sym = best.get('symbol', '?')
        now = int(time.time())

        # ---- Yon karari ----
        if fr > 0 and short_enabled:
            return {
                "signal": "SHORT",
                "reason": "Funding +%.4f%% (%s)" % (fr * 100, sym),
                "entry_price": None,
                "meta": {
                    "funding_rate": fr,
                    "funding_symbol": sym,
                    "is_funding_arb": True,
                    "candle_time": now,
                }
            }
        elif fr < 0 and long_enabled:
            return {
                "signal": "LONG",
                "reason": "Funding %.4f%% (%s)" % (fr * 100, sym),
                "entry_price": None,
                "meta": {
                    "funding_rate": fr,
                    "funding_symbol": sym,
                    "is_funding_arb": True,
                    "candle_time": now,
                }
            }

        return {
            "signal": None,
            "reason": "Uygun firsat yok",
            "meta": {"funding_count": len(funding_data)}
        }
