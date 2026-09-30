import asyncio
import json
import os
import shutil
import time
import sqlite3
from binance.client import Client
from backend.strategies import RSIScalperStrategy, HullSRPStrategy, DynamicGridStrategy, DynamicGridReelStrategy, DeepHunterStrategy, FundingArbitrageStrategy, TrendFollowStrategy
from backend.database import get_db_connection
from backend import telegram_notifier


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "bot_config.json")

DEFAULT_CONFIG = {
    "active": False,
    "scan_interval_seconds": 30,
    "position_check_seconds": 10,
    "max_symbols": 30,
    "daily_max_loss": 0,
    "max_open_positions": 0,
    "strategies": {
        "RSI_SCALPER": {
            "enabled": True,
            "interval": "5m",
            "period": 7,
            "longOp": "<", "longVal": 20,
            "shortOp": ">", "shortVal": 80,
            "useDCA": True, "baseOrder": 10, "volMultiplier": 1.2,
            "steps": "1.5, 3, 5",
            "takeProfit": 1.5, "trailing": 0.3, "trailingSteps": "1.5:0.3, 2.5:0.2, 4:0.12, 6:0.07, 10:0.03", "stopLoss": 3.0,
            "partialTPEnabled": False, "partialTPPercent": 50,
            "partialTPKeepDCA": True
        },
        "HULL_SRP": {
            "enabled": False,
            "interval": "15m",
            "period": 10,
            "source": "hl2",
            "longTrade": True,
            "shortTrade": False,
            "baseOrder": 10,
            "takeProfit": 2.0, "trailing": 0.5, "trailingSteps": "1.5:0.3, 2.5:0.2, 4:0.12, 6:0.07, 10:0.03", "stopLoss": 3.0,
            "partialTPEnabled": False, "partialTPPercent": 50,
            "partialTPKeepDCA": True
        },
        "DYNAMIC_GRID_REEL": {
            "enabled": False,
            "interval": "1m",
            "mode": "neutral",
            "distributionType": "arithmetic",
            "gridCount": 20,
            "smaPeriod": 100,
            "pivotLookback": 100,
            "atrPeriod": 14,
            "atrMultiplier": 8,
            "minWidthRatio": 0.4,
            "maxWidthRatio": 0.8,
            "asymmetryRatio": 1.3,
            "recenterHours": 24,
            "recenterBuffer": 0.03,
            "baseOrder": 5,
            "leverage": 5,
            "takeProfit": 0,
            "trailing": 0,
            "stopLoss": 0,
            "useDCA": False,
            "volMultiplier": 1,
            "steps": "",
            "partialTPEnabled": False,
            "partialTPPercent": 50,
            "partialTPKeepDCA": False,
        },
        "DEEP_HUNTER": {
            "enabled": False,
            "interval": "4h",
            "emaPeriod": 200,
            "emaSource": "close",
            "rsiPeriod": 7,
            "longTriggerPct": 5.5,
            "shortTriggerPct": 15.0,
            "longRsiMax": 30,
            "shortRsiMin": 75,
            "longTrade": True,
            "shortTrade": True,
            "useDCA": True,
            "baseOrder": 5,
            "leverage": 5,
            "volMultiplier": 1.0,
            "steps": "5, 13, 25, 40, 60",
            "takeProfit": 1.5,
            "trailing": 0.5,
            "stopLoss": 50,
            "partialTPEnabled": True,
            "partialTPPercent": 50,
            "partialTPKeepDCA": True
        },
    }
}


def load_config() -> dict:
    """Config'i okur. Yoksa once preset'ten kopyala, sonra DEFAULT_CONFIG."""
    if not os.path.exists(CONFIG_PATH):
        # ⚡ Once preset varsa ondan kopyala
        preset_path = os.path.join(os.path.dirname(__file__), "bot_config.default.json")
        if os.path.exists(preset_path):
            try:
                shutil.copy2(preset_path, CONFIG_PATH)
                print(f"[CFG] Preset'ten yuklendi: bot_config.default.json")
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CFG] Preset kopyalama hatasi: {e}")
        # Preset yoksa DEFAULT
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "strategies" not in cfg:
            cfg["strategies"] = {}
        for k, v in DEFAULT_CONFIG["strategies"].items():
            if k not in cfg["strategies"]:
                cfg["strategies"][k] = v
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    except Exception as e:
        print(f"[!] Config okuma hatası: {e}")
        return DEFAULT_CONFIG


def save_config(cfg: dict):
    """Config'i diske yazar."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ⚡ Global DB write lock - ayni anda tek yazici
_DB_WRITE_LOCK = asyncio.Lock()


class StrategyEngine:
    def __init__(self, client: Client, order_manager=None, position_manager=None):
        self.client = client
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.is_running = False
        self.config = load_config()
        self.symbols = []
        self.latest_signals = {}
        self.stats = {"scans": 0, "signals_found": 0, "errors": 0, "last_scan": None}
        # ⚡ Aynı mumda tekrar sinyal üretmemek için hafıza
        self.last_signal_candle = {}
        # ⚡ Son sinyallerin RAM kopyası (hızlı erişim için)
        self.recent_signals = []
        # ⚡ İki paralel döngünün task referansları
        self._scan_task = None
        self._position_task = None
        # ⚡ Delist cache
        self._delisted_symbols_cache = set()
        self._delisted_cache_time = 0
        # ⚡ Duplicate prevention: sembol bazlı kilit
        self._symbol_locks = {}
        # ⚡ Multi-position state: strategy instance cache (symbol bazli)
        # DYNAMIC_GRID_REEL gibi stateful stratejiler icin ZORUNLU
        self._strategy_cache = {}

    # ------------------------------------------------------------------
    # Sembol listesi
    # ------------------------------------------------------------------
    async def refresh_symbol_list(self):
        try:
            tickers = await asyncio.to_thread(self.client.futures_ticker)
            usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
            usdt.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
            max_sym = int(self.config.get("max_symbols", 30))
            self.symbols = [t["symbol"] for t in usdt[:max_sym]]
            print(f"[*] Taranacak sembol sayısı: {len(self.symbols)}")
        except Exception as e:
            print(f"[!] Sembol listesi alınamadı: {e}")

    # ------------------------------------------------------------------
    # Açık pozisyon kontrolü
    # ------------------------------------------------------------------
    def get_open_position(self, symbol: str) -> dict:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM active_trades WHERE symbol = ?", (symbol,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_open_positions(self) -> list:
        """Tum acik pozisyonlari dondurur."""
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM active_trades").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # A1/A2: RISK LIMIT KONTROLU
    # ------------------------------------------------------------------
    def _check_risk_limits(self) -> str:
        """
        A1: Gunluk max zarar limiti (TR saatine gore)
        A2: Max acik pozisyon sayisi
        A3: F60a - Marjin orani (%)
        Ihlal varsa sebep string'i, yoksa bos string doner.
        """
        cfg = self.config or {}

        # --- A3: F60a Marjin orani kontrolu ---
        try:
            max_ratio = float(cfg.get("max_margin_ratio", 60.0))
        except Exception:
            max_ratio = 60.0

        if max_ratio > 0:
            try:
                conn = get_db_connection()
                rows = conn.execute(
                    "SELECT total_vol, leverage FROM active_trades"
                ).fetchall()
                conn.close()

                used_margin = 0.0
                for r in rows:
                    r = dict(r)
                    vol = float(r.get("total_vol") or 0)
                    lev = max(1, int(r.get("leverage") or 1))
                    used_margin += vol / lev

                # Bakiye
                try:
                    balances = self.client.futures_account_balance()
                    balance = 0.0
                    for b in balances:
                        if b.get("asset") == "USDT":
                            balance = float(b.get("balance", 0))
                            break
                except Exception:
                    balance = 0.0

                if balance > 0:
                    ratio = (used_margin / balance) * 100
                    if ratio >= max_ratio:
                        return f"Marjin limiti asildi ({ratio:.1f}%/{max_ratio:.0f}%)"
            except Exception as e:
                print(f"[RISK] A3 kontrol hatasi: {e}")

        # --- Eski kontroller (A1, A2) ---

        # --- A2: Max acik pozisyon ---
        try:
            max_open = int(cfg.get("max_open_positions", 0) or 0)
        except Exception:
            max_open = 0

        if max_open > 0:
            try:
                conn = get_db_connection()
                row = conn.execute("SELECT COUNT(*) as c FROM active_trades").fetchone()
                conn.close()
                cnt = row["c"] if row else 0
                if cnt >= max_open:
                    return f"Max acik pozisyon limiti ({cnt}/{max_open})"
            except Exception as e:
                print(f"[RISK] A2 kontrol hatasi: {e}")

        # --- A1: Gunluk max zarar (TR saati = UTC+3) ---
        try:
            max_loss = float(cfg.get("daily_max_loss", 0) or 0)
        except Exception:
            max_loss = 0.0

        if max_loss > 0:
            try:
                conn = get_db_connection()
                row = conn.execute("""
                    SELECT COALESCE(SUM(pnl_amount), 0) as total
                    FROM trade_history
                    WHERE DATE(exit_time + 10800, 'unixepoch') = DATE('now', '+3 hours')
                """).fetchone()
                conn.close()
                today_pnl = float(row["total"]) if row else 0.0
                if today_pnl <= -max_loss:
                    return f"Gunluk max zarar limiti ({today_pnl:.2f}/{max_loss:.2f} USDT)"
            except Exception as e:
                print(f"[RISK] A1 kontrol hatasi: {e}")

        return ""

    # ------------------------------------------------------------------
    # Mum çekme
    # ------------------------------------------------------------------
    async def fetch_candles(self, symbol: str, interval: str, limit: int = 200):
        try:
            klines = await asyncio.to_thread(
                self.client.futures_klines,
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            return [
                {
                    "time": int(k[0] / 1000),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in klines
            ]
        except Exception as e:
            print(f"[!] {symbol} mum verisi alınamadı: {e}")
            return []

    # ------------------------------------------------------------------
    # Strateji seçici
    # ------------------------------------------------------------------
    def _create_strategy(self, strategy_name: str, strat_cfg: dict):
        if strategy_name == "RSI_SCALPER":
            return RSIScalperStrategy(strat_cfg)
        elif strategy_name == "HULL_SRP":
            return HullSRPStrategy(strat_cfg)
        elif strategy_name == "DYNAMIC_GRID":
            return DynamicGridStrategy(strat_cfg)
        elif strategy_name == "DYNAMIC_GRID_REEL":
            return DynamicGridReelStrategy(strat_cfg)
        elif strategy_name == "DEEP_HUNTER":
            return DeepHunterStrategy(strat_cfg)
        elif strategy_name == "FUNDING_ARBITRAGE":
            return FundingArbitrageStrategy(strat_cfg)
        elif strategy_name == "TREND_FOLLOW":
            return TrendFollowStrategy(strat_cfg)
        return None

    def _create_strategy_for_symbol(self, strategy_name: str, strat_cfg: dict, symbol: str):
        """
        Symbol-bazli strategy instance cache.
        Stateful stratejiler (DYNAMIC_GRID, DYNAMIC_GRID_REEL) icin ZORUNLU.
        Diger stratejiler icin normal create (cache kullanma).
        """
        STATEFUL = {"DYNAMIC_GRID_REEL", "DYNAMIC_GRID"}
        if strategy_name not in STATEFUL:
            return self._create_strategy(strategy_name, strat_cfg)

        cache_key = f"{strategy_name}::{symbol}"
        if cache_key not in self._strategy_cache:
            self._strategy_cache[cache_key] = self._create_strategy(strategy_name, strat_cfg)
        return self._strategy_cache[cache_key]

    # ------------------------------------------------------------------
    # Sinyal DB'ye kaydet
    # ------------------------------------------------------------------
    def _save_signal_to_db(self, signal_id, symbol, strategy_name, signal_type,
                            price, qty, total_usdt, candle_time, created_ms, opened=1, skip_reason=None):
        """⚡ Retry + connection leak fix"""
        max_retries = 3
        conn = None
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()
                conn.execute(
                    """INSERT OR IGNORE INTO signals 
                       (signal_id, symbol, strategy_name, signal, price, qty, total_usdt, 
                        candle_time, created_at, opened_position, skip_reason)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (signal_id, symbol, strategy_name, signal_type, price, qty,
                     total_usdt, candle_time, created_ms, opened, skip_reason)
                )
                conn.commit()
                return True
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                print(f"[!] Sinyal DB hatasi ({symbol}): {e}")
                return False
            except Exception as e:
                print(f"[!] Sinyal DB hatasi ({symbol}): {e}")
                return False
            finally:
                # ⚡ HER DURUMDA connection'i kapat
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
        return False


    # ------------------------------------------------------------------
    # Tek stratejiyi tüm sembollerde çalıştır (PARALEL BATCH)
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # VOLATILITE SIRALAMASI - test_symbol sayi girildiginde kullanilir
    # Skor = |priceChangePercent| + (high - low) / close * 100
    # 60 sn cache (API spam yok)
    # ------------------------------------------------------------------
    _vol_cache = {"ts": 0, "n": 0, "symbols": []}

    def _get_top_volatile(self, n: int):
        """En volatil N USDT-M futures coinini dondur."""
        import time as _t

        # Cache kontrolu
        now = _t.time()
        cache = StrategyEngine._vol_cache
        if (now - cache.get("ts", 0) < 60) and cache.get("n") == n and cache.get("symbols"):
            return cache["symbols"]

        try:
            tickers = self.client.futures_ticker()
        except Exception as e:
            print(f"[VOL] ticker cekilemedi: {e}")
            return []

        scored = []
        for t in tickers:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            try:
                last = float(t.get("lastPrice", 0) or 0)
                high = float(t.get("highPrice", 0) or 0)
                low = float(t.get("lowPrice", 0) or 0)
                chg = abs(float(t.get("priceChangePercent", 0) or 0))
            except Exception:
                continue
            if last <= 0 or high <= 0 or low <= 0:
                continue

            vol_a = chg                          # A: 24h degisim %
            vol_b = (high - low) / last * 100    # B: intraday range %
            score = vol_a + vol_b                # A + B

            scored.append((sym, score, vol_a, vol_b))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:n]

        result = [s[0] for s in top]

        # Cache guncelle
        StrategyEngine._vol_cache["ts"] = now
        StrategyEngine._vol_cache["n"] = n
        StrategyEngine._vol_cache["symbols"] = result

        # Log
        print(f"[VOL] En volatil {n} coin (A+B skoru):")
        for sym, score, a, b in top:
            print(f"      {sym:<16} skor={score:>7.2f}  (A={a:>6.2f}% + B={b:>6.2f}%)")

        return result

    async def _run_funding_arbitrage(self, strategy, strat_cfg):
        """
        FUNDING ARBITRAGE icin ozel tarama yolu.
        Mum yerine bulk funding rate ceker, en yuksek |funding|'i bulur.
        Rate limit: 60 saniyede 1 kez cagrilir.
        """
        try:
            if not self.config.get("active", False):
                return

            # Rate limit: 60 sn min interval (API spamini onler)
            _now = time.time()
            if not hasattr(self, "_funding_last_fetch"):
                self._funding_last_fetch = 0
            if _now - self._funding_last_fetch < 60:
                return
            self._funding_last_fetch = _now

            # Bulk mark price + funding
            try:
                premiums = await asyncio.to_thread(self.client.futures_mark_price)
            except Exception as e:
                _err = str(e)
                if "-1003" in _err or "Too many" in _err:
                    print(f"[FUNDING] Rate limit - 90 sn bekleniyor")
                    self._funding_last_fetch = _now + 30  # ekstra bekleme
                else:
                    print(f"[FUNDING] Mark price hatasi: {_err[:100]}")
                return

            if not premiums:
                return

            # Sembol filtresi
            scan_set = set(self.symbols or [])
            funding_data = []
            for p in premiums:
                sym = p.get("symbol", "")
                if scan_set and sym not in scan_set:
                    continue
                try:
                    fr = float(p.get("lastFundingRate", 0) or 0)
                except Exception:
                    continue
                funding_data.append({
                    "symbol": sym,
                    "funding": fr,
                    "mark_price": float(p.get("markPrice", 0) or 0),
                    "next_ts": int(p.get("nextFundingTime", 0) or 0),
                })

            if not funding_data:
                return

            # Strateji karari
            result = strategy.evaluate(funding_data=funding_data)
            sig = result.get("signal")
            meta = result.get("meta", {}) or {}

            if sig not in ("LONG", "SHORT"):
                # Log spamini onleme (60 sn'de 1)
                _now = int(time.time())
                if not hasattr(self, "_funding_last_log") or _now - self._funding_last_log >= 60:
                    self._funding_last_log = _now
                    print(f"[FUNDING] {result.get('reason', '?')} | {len(funding_data)} sembol")
                return

            symbol = meta.get("funding_symbol")
            fr_rate = float(meta.get("funding_rate", 0))
            if not symbol:
                return

            print(f"\n[FUNDING] FIRSAT: {symbol} {sig} | Funding {fr_rate*100:+.4f}%")

            if not self.config.get("active", False):
                return

            risk_reason = self._check_risk_limits()
            if risk_reason:
                print(f"[FUNDING] Risk limit: {risk_reason}")
                return

            existing = self.get_open_position(symbol)
            if existing:
                # Log spam koruma: ayni sembol icin 5 dk'da 1
                _now2 = time.time()
                if not hasattr(self, "_funding_skip_log"):
                    self._funding_skip_log = {}
                _last = self._funding_skip_log.get(symbol, 0)
                if _now2 - _last >= 300:
                    print(f"[FUNDING] {symbol} zaten acik, atlandi (5dk log)")
                    self._funding_skip_log[symbol] = _now2
                return

            base_order = float(strat_cfg.get("baseOrder", 20))
            leverage = int(strat_cfg.get("leverage", 3))
            tp_pct = float(strat_cfg.get("takeProfit", 0.3))
            sl_pct = float(strat_cfg.get("stopLoss", 1.5))

            self.order_manager.symbol = symbol

            try:
                order_result = await asyncio.to_thread(
                    self.order_manager.open_dca_position,
                    side="BUY" if sig == "LONG" else "SELL",
                    base_amount_usdt=base_order,
                    strategy_name="FUNDING_ARBITRAGE",
                    leverage=leverage,
                    tp_pct=tp_pct,
                    sl_pct=sl_pct,
                    use_limit_order=False,
                )
            except Exception as e:
                print(f"[FUNDING] Emir hatasi: {e}")
                return

            status = order_result.get("status")
            _now_ms = int(time.time() * 1000)
            _sig_id = f"{symbol}_FUNDING_{_now_ms}"

            if status == "success":
                print(f"[FUNDING] Emir ACILDI: {symbol} {sig}")
                self._save_signal_to_db(
                    _sig_id, symbol, "FUNDING_ARBITRAGE", sig,
                    order_result.get("entry_price", 0), 0, base_order,
                    int(time.time()), _now_ms,
                    opened=1, skip_reason=None
                )
                self.stats["signals_found"] += 1
            else:
                print(f"[FUNDING] Emir BASARISIZ: {status}")
                self._save_signal_to_db(
                    _sig_id, symbol, "FUNDING_ARBITRAGE", sig,
                    0, 0, base_order,
                    int(time.time()), _now_ms,
                    opened=0, skip_reason=str(order_result.get("message", "hata"))
                )

        except Exception as e:
            self.stats["errors"] += 1
            print(f"[FUNDING] Genel hata: {e}")

    async def run_strategy(self, strategy_name: str, strat_cfg: dict, candle_cache: dict):
        strategy = self._create_strategy(strategy_name, strat_cfg)
        if not strategy:
            print(f"[!] Bilinmeyen strateji: {strategy_name}")
            return

        # FUNDING ARBITRAGE ozel yolu (mum taramaz)
        if strategy_name == "FUNDING_ARBITRAGE":
            await self._run_funding_arbitrage(strategy, strat_cfg)
            return

        interval = strat_cfg.get("interval", "5m")

        # ⚡ TEST SEMBOL SAYI filtresi
        #  - Bos    -> normal tarama (self.symbols)
        #  - Sayi   -> en volatil N coin
        #  - Gecersiz deger -> normal tarama (log ile uyari)
        test_val = str(strat_cfg.get("test_symbol") or "").strip()
        scan_symbols = None

        if test_val:
            try:
                n = int(test_val)
                if n > 0:
                    vol_symbols = self._get_top_volatile(n)
                    if vol_symbols:
                        scan_symbols = vol_symbols
                        print(f"[TEST-N] {strategy_name} SADECE en volatil {n} coin:")
                        for s in vol_symbols:
                            print(f"         - {s}")
                    else:
                        print(f"[TEST-N] {strategy_name} volatilite listesi bos, normal tarama")
                else:
                    print(f"[TEST-N] {strategy_name} test_symbol={n} gecersiz (0 veya negatif), normal tarama")
            except ValueError:
                print(f"[TEST-N] {strategy_name} test_symbol='{test_val}' gecersiz (sadece sayi), normal tarama")

        if scan_symbols is None:
            scan_symbols = self.symbols

        BATCH_SIZE = 3
        for batch_start in range(0, len(scan_symbols), BATCH_SIZE):
            if not self.is_running:
                return

            # ⚡ RACE-CONDITION GUARD: Bot pasifse tarama derhal durdur
            if not self.config.get("active", False):
                print(f"[SCAN] Bot pasif -> tarama durduruldu (batch {batch_start}/{len(scan_symbols)})")
                return
            batch = scan_symbols[batch_start:batch_start + BATCH_SIZE]
            await asyncio.gather(*[
                self._process_symbol(sym, strategy_name, strategy, strat_cfg, interval, candle_cache)
                for sym in batch
            ], return_exceptions=True)
            await asyncio.sleep(1.5)

    # ------------------------------------------------------------------
    # Tek sembol işleme
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # GRID STATE - Backend tek dogru kaynak
    # ------------------------------------------------------------------
    def _save_grid_state_to_db(self, symbol, strategy_name, snapshot):
        """Grid state'i DB'ye UPSERT et (her recenter'da)."""
        if not snapshot:
            return
        import time as _t
        try:
            import json as _json
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO grid_state
                    (symbol, strategy_name, group_id, reference, top, bottom,
                     levels_json, interval, mode, recenter_ts, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    strategy_name = excluded.strategy_name,
                    group_id      = excluded.group_id,
                    reference     = excluded.reference,
                    top           = excluded.top,
                    bottom        = excluded.bottom,
                    levels_json   = excluded.levels_json,
                    interval      = excluded.interval,
                    mode          = excluded.mode,
                    recenter_ts   = excluded.recenter_ts,
                    updated_at    = excluded.updated_at
            """, (
                symbol,
                strategy_name,
                snapshot.get("group_id"),
                float(snapshot.get("reference") or 0),
                float(snapshot.get("top") or 0),
                float(snapshot.get("bottom") or 0),
                _json.dumps(snapshot.get("levels") or []),
                snapshot.get("interval", "1m"),
                snapshot.get("mode", "neutral"),
                int(snapshot.get("recenter_ts") or 0),
                int(_t.time()),
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[GRID-STATE] DB kayit hatasi {symbol}: {e}")

    async def _process_symbol(self, symbol, strategy_name, strategy, strat_cfg, interval, candle_cache):
        # ⚡ SEMBOL BAZLI KİLİT (race condition engeli)
        lock = self._get_symbol_lock(symbol)
        
        async with lock:
            await self._process_symbol_locked(symbol, strategy_name, strategy, strat_cfg, interval, candle_cache)
    
    async def _process_symbol_locked(self, symbol, strategy_name, strategy, strat_cfg, interval, candle_cache):
        try:
            cache_key = f"{symbol}_{interval}"
            if cache_key in candle_cache:
                candles = candle_cache[cache_key]
            else:
                candles = await self.fetch_candles(symbol, interval, 200)
                candle_cache[cache_key] = candles

            if not candles:
                return

            # ⚡ Stateful stratejiler icin symbol-bazli instance
            symbol_strategy = self._create_strategy_for_symbol(strategy_name, strat_cfg, symbol)

            # ⚡ GRID REEL: acik pozisyon kontrolu YAPMA
            # Her seviye bagimsiz -- strateji kendi tetiklenmis seviyeleri tutuyor.
            # Ayni sembolde ayni anda 10+ grid seviyesi olabilir.
            if strategy_name == "DYNAMIC_GRID_REEL":
                open_pos = None
                result = symbol_strategy.evaluate(candles, open_pos, symbol=symbol)
                # ⚡ Grid state'i DB'ye kaydet (tek dogru kaynak)
                try:
                    _snap = symbol_strategy.get_state_snapshot(symbol)
                    if _snap:
                        self._save_grid_state_to_db(symbol, strategy_name, _snap)
                except Exception as _ge:
                    print(f"[GRID-STATE] snapshot hatasi {symbol}: {_ge}")

                # ⚡ RECENTER: eski grubun tum pozisyonlarini kapat
                _meta = result.get("meta", {}) or {}
                if _meta.get("recenter_happened") and _meta.get("prev_group_id"):
                    _old_gid = _meta.get("prev_group_id")
                    if self.position_manager and hasattr(self.position_manager, "_close_grid_group"):
                        asyncio.create_task(self.position_manager._close_grid_group(
                            symbol, _old_gid, "GRID RECENTER"
                        ))
                        print(f"[RECENTER-CLEANUP] {symbol} eski grup {_old_gid} kapatiliyor (async)")
            else:
                open_pos = self.get_open_position(symbol)
                result = symbol_strategy.evaluate(candles, open_pos)

            current_price = candles[-1]["close"]
            meta = result.get("meta", {})
            rsi_val = meta.get("rsi") if isinstance(meta, dict) else None
            hma_val = meta.get("hma") if isinstance(meta, dict) else None

            signal_key = f"{symbol}_{strategy_name}"
            self.latest_signals[signal_key] = {
                "symbol": symbol,
                "strategy": strategy_name,
                "interval": interval,
                "price": current_price,
                "rsi": rsi_val,
                "hma": hma_val,
                "signal": result.get("signal"),
                "reason": result.get("reason", ""),
                "has_position": open_pos is not None,
                "time": candles[-1]["time"],
            }

            # ⚡ Sinyal varsa işleme al
            if result.get("signal") in ("LONG", "SHORT"):
                candle_time = candles[-1]["time"]
                last_time = self.last_signal_candle.get(signal_key)
                if last_time == candle_time:
                    return

                base_order = float(strat_cfg.get("baseOrder", 10))
                try:
                    qty = round(base_order / current_price, 6) if current_price > 0 else 0
                except Exception:
                    qty = 0

                signal_id = f"{symbol}_{strategy_name}_{candle_time}"
                created_ms = int(time.time() * 1000)

                # ⚡ Açık pozisyon varsa → DB'ye kaydet ama emir açma
                if open_pos:
                    self._save_signal_to_db(
                        signal_id, symbol, strategy_name, result["signal"],
                        current_price, qty, base_order, candle_time, created_ms,
                        opened=0, skip_reason="Pozisyon zaten açık"
                    )
                    self.last_signal_candle[signal_key] = candle_time
                    return

                # ⚡ A1/A2: Risk limit kontrolu
                risk_reason = self._check_risk_limits()
                if risk_reason:
                    print(f"[RISK] {symbol} sinyal atlandi: {risk_reason}")
                    self._save_signal_to_db(
                        signal_id, symbol, strategy_name, result["signal"],
                        current_price, qty, base_order, candle_time, created_ms,
                        opened=0, skip_reason=risk_reason
                    )
                    self.last_signal_candle[signal_key] = candle_time
                    return

                # ⚡ RACE-CONDITION GUARD: Emir açmadan önce bot aktif mi?
                if not self.config.get("active", False):
                    self._save_signal_to_db(
                        signal_id, symbol, strategy_name, result["signal"],
                        current_price, qty, base_order, candle_time, created_ms,
                        opened=0, skip_reason="Bot pasif (guard)"
                    )
                    self.last_signal_candle[signal_key] = candle_time
                    return

                # ⚡ Emir aç
                if self.order_manager:
                    side = "BUY" if result["signal"] == "LONG" else "SELL"
                    print(f"\n[>> SİNYAL] {symbol} [{strategy_name}] {result['signal']} | {result['reason']}")

                    leverage = int(strat_cfg.get("leverage", 1))
                    self.order_manager.symbol = symbol

                    # ⚡ GRID REEL mi? -> open_grid_position
                    _meta = result.get("meta", {}) or {}
                    if _meta.get("is_grid_reel"):
                        try:
                            grid_result = await asyncio.to_thread(
                                self.order_manager.open_grid_position,
                                side=side,
                                base_amount_usdt=base_order,
                                strategy_name=strategy_name,
                                leverage=leverage,
                                grid_group_id=_meta.get("grid_group_id"),
                                grid_level=int(_meta.get("grid_level") or 0),
                                grid_side=_meta.get("grid_side") or ("BUY" if side == "BUY" else "SELL"),
                                grid_entry_price=float(_meta.get("grid_entry_price") or 0),
                                grid_tp_price=float(_meta.get("grid_tp_price") or 0),
                                use_limit_order=bool(self.config.get("useLimitOrder", True)),
                                limit_timeout_sec=int(self.config.get("limitTimeoutSec", 3)),
                                fallback_market=bool(self.config.get("fallbackToMarket", True)),
                            )
                            _opened = 1 if grid_result.get("status") == "success" else 0
                            _skip = None if _opened else (grid_result.get("message") or "grid hata")
                            self._save_signal_to_db(
                                signal_id, symbol, strategy_name, result["signal"],
                                current_price, qty, base_order, candle_time, created_ms,
                                opened=_opened, skip_reason=_skip
                            )
                            if _opened:
                                self.stats["signals_found"] += 1
                        except Exception as ge:
                            print(f"[!] Grid emir hatasi {symbol}: {ge}")
                            self._save_signal_to_db(
                                signal_id, symbol, strategy_name, result["signal"],
                                current_price, qty, base_order, candle_time, created_ms,
                                opened=0, skip_reason=f"Grid emir hatasi: {ge}"
                            )
                    else:
                        # ==================== KLASIK DCA (eski akis) ====================
                        # ⚡ Kismi TP snapshot (acilis anindaki config)
                        pt_enabled = 1 if strat_cfg.get("partialTPEnabled") else 0
                        pt_percent = float(strat_cfg.get("partialTPPercent", 50))
                        pt_keep_dca = 1 if strat_cfg.get("partialTPKeepDCA", True) else 0

                        if pt_enabled:
                            print(f"[PARTIAL-TP] {symbol} PT aktif: %{pt_percent:.0f} | KeepDCA={pt_keep_dca}")

                        try:
                            await asyncio.to_thread(
                                self.order_manager.open_dca_position,
                                side=side,
                                base_amount_usdt=base_order,
                                strategy_name=strategy_name,
                                leverage=leverage,
                                pt_enabled=pt_enabled,
                                pt_percent=pt_percent,
                                pt_keep_dca=pt_keep_dca,
                                use_limit_order=bool(self.config.get("useLimitOrder", True)),
                                limit_timeout_sec=int(self.config.get("limitTimeoutSec", 3)),
                                fallback_market=bool(self.config.get("fallbackToMarket", True)),
                            )
                            self._save_signal_to_db(
                                signal_id, symbol, strategy_name, result["signal"],
                                current_price, qty, base_order, candle_time, created_ms,
                                opened=1, skip_reason=None
                            )
                            self.stats["signals_found"] += 1
                        except Exception as oe:
                            print(f"[!] Emir açma hatası {symbol}: {oe}")
                            self._save_signal_to_db(
                                signal_id, symbol, strategy_name, result["signal"],
                                current_price, qty, base_order, candle_time, created_ms,
                                opened=0, skip_reason=f"Emir hatası: {oe}"
                            )

                self.last_signal_candle[signal_key] = candle_time

                # ⚡ RAM kopyasına da ekle
                signal_entry = {
                    "id": signal_id,
                    "symbol": symbol,
                    "display_symbol": symbol + ".P",
                    "strategy": strategy_name,
                    "signal": result["signal"],
                    "price": current_price,
                    "qty": qty,
                    "total_usdt": base_order,
                    "candle_time": candle_time,
                    "created_at": created_ms,
                }
                # ⚡ Grid REEL meta bilgisini de sakla
                if isinstance(meta, dict) and meta.get("is_grid_reel"):
                    signal_entry["grid_level"] = meta.get("grid_level")
                    signal_entry["grid_group_id"] = meta.get("grid_group_id")
                    signal_entry["grid_tp_price"] = meta.get("grid_tp_price")

                self.recent_signals.insert(0, signal_entry)
                if len(self.recent_signals) > 100:
                    self.recent_signals = self.recent_signals[:100]

        except Exception as e:
            self.stats["errors"] += 1
            print(f"[!] {symbol} hata: {e}")

    # ------------------------------------------------------------------
    # DÖNGÜ 1: Sinyal tarama
    # ------------------------------------------------------------------
    async def _scan_loop(self):
        while self.is_running:
            try:
                self.config = load_config()

                if not self.config.get("active", False):
                    await asyncio.sleep(1.5)
                    continue

                self.stats["scans"] += 1
                self.stats["last_scan"] = time.time()

                candle_cache = {}

                strategies = self.config.get("strategies", {})
                for strat_name, strat_cfg in strategies.items():
                    if strat_cfg.get("enabled"):
                        await self.run_strategy(strat_name, strat_cfg, candle_cache)

                interval_sec = int(self.config.get("scan_interval_seconds", 30))
                await asyncio.sleep(interval_sec)

            except asyncio.CancelledError:
                return
            except Exception as e:
                self.stats["errors"] += 1
                print(f"[!] Scan loop hata: {e}")
                await asyncio.sleep(10)

    # ------------------------------------------------------------------
    # DÖNGÜ 2: Pozisyon izleme
    # ------------------------------------------------------------------
    def _get_symbol_lock(self, symbol: str):
        """Sembol bazlı asyncio.Lock döner (thread-safe)."""
        if symbol not in self._symbol_locks:
            self._symbol_locks[symbol] = asyncio.Lock()
        return self._symbol_locks[symbol]

    # ------------------------------------------------------------------
    # DELIST KONTROLU - acik pozisyonu olan delist sembolleri kapatir
    # ------------------------------------------------------------------
    async def _check_delisted_symbols(self):
        """Delist olmus sembolleri kontrol eder, acik pozisyonlari kapatir."""
        import time as _time
        cfg = load_config()
        
        if not cfg.get("auto_close_delisted", True):
            return
        
        if _time.time() - getattr(self, '_delisted_cache_time', 0) > 1800:
            try:
                info = await asyncio.to_thread(self.client.futures_exchange_info)
                new_cache = set()
                for s in info.get("symbols", []):
                    status = s.get("status", "TRADING")
                    if status not in ("TRADING", "PENDING_TRADING"):
                        new_cache.add(s["symbol"])
                
                old_cache = getattr(self, '_delisted_symbols_cache', set())
                newly = new_cache - old_cache
                if newly and getattr(self, '_delisted_cache_time', 0) > 0:
                    for sym in newly:
                        print(f"[DELIST] YENI DELIST: {sym}")
                        try:
                            tg_cfg = self.config.get("telegram", {})
                            if tg_cfg.get("notify_delisting", True):
                                asyncio.create_task(telegram_notifier.notify_delisting(sym))
                        except Exception:
                            pass
                        self.recent_signals.insert(0, {
                            "id": f"DELIST_{sym}_{int(_time.time())}",
                            "symbol": sym,
                            "display_symbol": sym + ".P",
                            "strategy": "SYSTEM",
                            "signal": "DELIST",
                            "price": 0, "qty": 0, "total_usdt": 0,
                            "candle_time": int(_time.time()),
                            "created_at": int(_time.time() * 1000),
                        })
                
                self._delisted_symbols_cache = new_cache
                self._delisted_cache_time = _time.time()
                if new_cache:
                    print(f"[DELIST] Takip edilen delist sayisi: {len(new_cache)}")
            except Exception as e:
                print(f"[!] Delist liste alinamadi: {e}")
                return
        
        cache = getattr(self, '_delisted_symbols_cache', set())
        if not cache:
            return
        
        positions = self.get_all_open_positions()
        if not positions:
            return
        
        for pos in positions:
            sym = pos["symbol"]
            if sym in cache:
                print(f"[DELIST] {sym} delist edilmis! Kapatiliyor...")
                exit_price = pos["avg_price"]
                try:
                    ticker = await asyncio.to_thread(self.client.futures_symbol_ticker, symbol=sym)
                    if ticker and "price" in ticker:
                        exit_price = float(ticker["price"])
                except Exception:
                    pass
                
                if self.position_manager:
                    try:
                        await self.position_manager._execute_close(
                            sym, exit_price, "DELISTED", force=True
                        )
                    except Exception as e:
                        print(f"[!] Delist kapatma hatasi {sym}: {e}")

    async def _position_loop(self):
        while self.is_running:
            try:
                cfg = load_config()

                if cfg.get("active", False):
                    # ⚡ 1. Delist kontrolü
                    await self._check_delisted_symbols()
                    
                    # ⚡ 2. Normal pozisyon izleme
                    if self.position_manager:
                        await self.position_manager.monitor_positions(
                            cfg.get("strategies", {})
                        )

                check_sec = int(cfg.get("position_check_seconds", 6))
                await asyncio.sleep(check_sec)

            except asyncio.CancelledError:
                return
            except Exception as e:
                print(f"[!] Position loop hata: {e}")
                await asyncio.sleep(1.5)

    # ------------------------------------------------------------------
    # Başlat / durdur
    # ------------------------------------------------------------------
    async def start(self):
        # ⚡ REPLICA KORUMASI: Cloud'da hicbir zaman tarama baslatma
        import os as _os
        _mode = _os.getenv("SYNC_MODE", "standalone").strip().lower()
        if _mode == "replica":
            print("[REPLICA-GUARD] Strategy Engine REPLICA modunda - tarama BASLATILMADI")
            return

        self.is_running = True
        print("[*] Strategy Engine başlatıldı.")

        await self.refresh_symbol_list()

        # ⚡ Test modunda yanlislikla kilitlenmis PT flag'lerini temizle
        if self.position_manager and hasattr(self.position_manager, '_reset_stuck_pt_flags'):
            self.position_manager._reset_stuck_pt_flags()

        self._scan_task = asyncio.create_task(self._scan_loop())
        self._position_task = asyncio.create_task(self._position_loop())

        try:
            await asyncio.gather(self._scan_task, self._position_task)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[!] Engine görev hatası: {e}")

    def stop(self):
        self.is_running = False
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
        if self._position_task and not self._position_task.done():
            self._position_task.cancel()

    # ------------------------------------------------------------------
    # Durum bilgisi
    # ------------------------------------------------------------------
    def get_status(self) -> dict:
        result = {
            "running": self.is_running,
            "config": self.config,
            "symbols_count": len(self.symbols),
            "symbols": self.symbols[:50],
            "stats": self.stats,
            "signals": self.latest_signals,
            "recent_signals": self.recent_signals[:50],
        }
        if self.position_manager:
            result["trailing_state"] = self.position_manager.trailing_state
        return result