import asyncio
import json
import os
import shutil
import time
import sqlite3
from binance.client import Client
from backend.strategies import RSIScalperStrategy, DynamicGridStrategy, DynamicGridReelStrategy, DeepHunterStrategy, EmaTrendStrategy, ASAPStrategy
from backend.strategies.asap import asap_check_cooldown, asap_set_cooldown, asap_reset
from backend.strategies.asap import asap_inc_entry, asap_get_entry_count, asap_set_cooldown, asap_check_cooldown
from backend.database import get_db_connection
from backend import telegram_notifier


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "bot_config.json")

# FIX K2: 5 sn config cache
_CONFIG_CACHE = {"ts": 0.0, "data": None}
_CONFIG_CACHE_TTL = 5.0

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
    """Config'i okur. 5 sn cache (FIX K2)."""
    import time as _t_k2
    _now_k2 = _t_k2.time()
    if _CONFIG_CACHE["data"] is not None and (_now_k2 - _CONFIG_CACHE["ts"]) < _CONFIG_CACHE_TTL:
        return dict(_CONFIG_CACHE["data"])
    _result = _load_config_uncached()
    _CONFIG_CACHE["ts"] = _now_k2
    _CONFIG_CACHE["data"] = _result
    return dict(_result)


def _load_config_uncached() -> dict:
    """Orijinal load_config govdesi (cache'siz)."""
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
    # FIX K2: cache invalidate
    try:
        _CONFIG_CACHE["ts"] = 0
        _CONFIG_CACHE["data"] = None
    except Exception:
        pass


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
    def _load_blocked_symbols(self) -> set:
        """F169: backend/blocked_symbols.txt dosyasindan bloklu sembolleri okur.

        Format:
          - Her satirda bir sembol (orn: FXSUSDT)
          - # ile baslayan satirlar yorum
          - Bos satirlar yok sayilir
          - Dosya yoksa bos set doner (hicbir sembol bloklu degil)

        Etki: Sadece sinyal tarama filtresi icin kullanilir.
              Mevcut pozisyonlar, DCA, PT, TTP, SL etkilenmez.
        """
        try:
            from pathlib import Path as _P_f169
            _bf169 = _P_f169(__file__).resolve().parent / "blocked_symbols.txt"
            if not _bf169.exists():
                return set()
            _out_f169 = set()
            for _ln_f169 in _bf169.read_text(encoding="utf-8").splitlines():
                _s_f169 = _ln_f169.strip()
                if not _s_f169 or _s_f169.startswith("#"):
                    continue
                # Yorum satirinda sembol varsa atla
                if " " in _s_f169 or "\t" in _s_f169:
                    continue
                _out_f169.add(_s_f169.upper())
            return _out_f169
        except Exception as _e_f169:
            print(f"[F169] blocked_symbols.txt okuma hatasi: {_e_f169}")
            return set()

    async def refresh_symbol_list(self):
        try:
            tickers = await asyncio.to_thread(self.client.futures_ticker)
            usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
            usdt.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
            max_sym = int(self.config.get("max_symbols", 30))
            # F169: bloklu sembolleri cikar
            _blocked_f169 = self._load_blocked_symbols()
            _raw_f169 = [t["symbol"] for t in usdt[:max_sym]]
            if _blocked_f169:
                _before_f169 = len(_raw_f169)
                _raw_f169 = [s for s in _raw_f169 if s not in _blocked_f169]
                _skipped_f169 = _before_f169 - len(_raw_f169)
                print(f"[F169] {len(_blocked_f169)} bloklu sembol yuklendi, "
                      f"{_skipped_f169} atlandi")
            self.symbols = _raw_f169
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
    def _check_risk_limits(self, side: str = None, skip_cross_ratio: bool = False) -> str:
        """
        A1: Gunluk max zarar limiti (TR saatine gore)
        A2: Max acik pozisyon sayisi
        A3: F60a - Marjin orani (%)
        A4: F90a - Cross modda %50 long/short limiti
        Ihlal varsa sebep string'i, yoksa bos string doner.
        side: "BUY" | "SELL" | None (yeni sinyal yonu)
        """
        cfg = self.config or {}

        # --- A4: Cross modda yon dengesi (FIX F95: Grid REEL icin atlanir) ---
        margin_mode = cfg.get("margin_mode", "cross")
        if margin_mode == "cross" and side in ("BUY", "SELL") and not skip_cross_ratio:
            try:
                max_long = float(cfg.get("max_long_ratio", 50))
                max_short = float(cfg.get("max_short_ratio", 50))
                max_pos = int(cfg.get("max_open_positions", 100) or 100)

                if max_pos > 0 and (max_long < 100 or max_short < 100):
                    conn = get_db_connection()
                    rows = conn.execute("""
                        SELECT trade_type, COUNT(*) as c FROM active_trades
                        GROUP BY trade_type
                    """).fetchall()
                    conn.close()

                    long_c = 0
                    short_c = 0
                    for r in rows:
                        r = dict(r)
                        if r["trade_type"] == "BUY":
                            long_c = r["c"]
                        elif r["trade_type"] == "SELL":
                            short_c = r["c"]

                    total = long_c + short_c
                    # Yeni pozisyon acilirsa total +1 olacak
                    projected_total = total + 1

                    if side == "BUY":
                        projected_long = long_c + 1
                        pct = (projected_long / projected_total) * 100
                        if pct > max_long:
                            return f"Long orani %{pct:.1f} > %{max_long:.0f} (Cross mod)"
                    elif side == "SELL":
                        projected_short = short_c + 1
                        pct = (projected_short / projected_total) * 100
                        if pct > max_short:
                            return f"Short orani %{pct:.1f} > %{max_short:.0f} (Cross mod)"
            except Exception as e:
                print(f"[RISK] A4 kontrol hatasi: {e}")

        # --- A3: F60a Marjin orani ---

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
    async def fetch_candles(self, symbol: str, interval: str, limit: int = 300):
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
        elif strategy_name == "DYNAMIC_GRID":
            return DynamicGridStrategy(strat_cfg)
        elif strategy_name == "DYNAMIC_GRID_REEL":
            return DynamicGridReelStrategy(strat_cfg)
        elif strategy_name == "DEEP_HUNTER":
            return DeepHunterStrategy(strat_cfg)
        elif strategy_name == "EMA_TREND":
            return EmaTrendStrategy(strat_cfg)
        elif strategy_name == "ASAP":
            return ASAPStrategy(strat_cfg)
        return None

    def _create_strategy_for_symbol(self, strategy_name: str, strat_cfg: dict, symbol: str):
        """
        Symbol-bazli strategy instance cache.
        Stateful stratejiler (DYNAMIC_GRID, DYNAMIC_GRID_REEL, ASAP) icin ZORUNLU.
        Diger stratejiler icin normal create (cache kullanma).
        """
        STATEFUL = {"DYNAMIC_GRID_REEL", "DYNAMIC_GRID", "ASAP"}
        if strategy_name not in STATEFUL:
            return self._create_strategy(strategy_name, strat_cfg)

        cache_key = f"{strategy_name}::{symbol}"
        if cache_key not in self._strategy_cache:
            # F178: ASAP icin _symbol inject et
            if strategy_name == "ASAP":
                _sc = dict(strat_cfg)
                _sc["_symbol"] = symbol
                self._strategy_cache[cache_key] = self._create_strategy(strategy_name, _sc)
            else:
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

    async def _get_top_volatile(self, n: int):
        """En volatil N USDT-M futures coinini dondur."""
        import time as _t

        # Cache kontrolu
        now = _t.time()
        cache = StrategyEngine._vol_cache
        if (now - cache.get("ts", 0) < 60) and cache.get("n") == n and cache.get("symbols"):
            return cache["symbols"]

        try:
            tickers = await asyncio.to_thread(self.client.futures_ticker)
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

    # ------------------------------------------------------------------
    # F181: ASAP sembol havuzu
    # ------------------------------------------------------------------
    async def _get_asap_pool(self, strat_cfg: dict):
        """ASAP icin 30 coinlik havuz sec. 4 filtre: hacim, pump, ATR, blocked."""
        import time as _t_asap

        now = _t_asap.time()
        refresh_h = float(strat_cfg.get("poolRefreshHours", 4))
        cache = getattr(self, "_asap_pool_cache", {"ts": 0, "symbols": []})
        if cache.get("symbols") and (now - cache.get("ts", 0)) < refresh_h * 3600:
            return cache["symbols"]

        n_target = int(strat_cfg.get("symbolCount", 30))
        min_vol = float(strat_cfg.get("minVolume24h", 10_000_000))
        atr_min = float(strat_cfg.get("atrMinPct", 2.0))
        atr_max = float(strat_cfg.get("atrMaxPct", 6.0))
        max_move = float(strat_cfg.get("maxMove24hPct", 15.0))
        interval = strat_cfg.get("interval", "15m")

        # 1. Ticker al
        try:
            tickers = await asyncio.to_thread(self.client.futures_ticker)
        except Exception as e:
            print(f"[ASAP-POOL] ticker hata: {e}")
            return cache.get("symbols") or []

        # 2. On filtre (hacim + pump)
        blocked = self._load_blocked_symbols()
        candidates = []
        for t in tickers:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            if sym in blocked:
                continue
            try:
                vol_24h = float(t.get("quoteVolume", 0) or 0)
                chg = abs(float(t.get("priceChangePercent", 0) or 0))
                last = float(t.get("lastPrice", 0) or 0)
            except Exception:
                continue
            if last <= 0:
                continue
            if vol_24h < min_vol:
                continue
            if chg > max_move:
                continue
            candidates.append((sym, vol_24h))

        # Hacme gore sirala, ATR filtresi icin genis havuz (n*3)
        candidates.sort(key=lambda x: x[1], reverse=True)
        pre = [c[0] for c in candidates[:max(n_target * 3, n_target)]]

        # 3. ATR filtresi (position_manager uzerinden)
        pm = getattr(self, "position_manager", None)
        passed = []
        if pm and hasattr(pm, "_get_atr_pct_for_symbol"):
            _f188_none = 0
            _f188_low = 0
            _f188_high = 0
            _f188_err = 0
            _f188_logged = 0
            for sym in pre:
                if len(passed) >= n_target:
                    break
                try:
                    atr_pct = await pm._get_atr_pct_for_symbol(
                        sym, ttl_sec=300, interval=interval
                    )
                except Exception as _ex188:
                    _f188_err += 1
                    if _f188_logged < 5:
                        print(f"[ASAP-POOL-DBG] {sym} HATA: {_ex188}")
                        _f188_logged += 1
                    continue
                if atr_pct is None:
                    _f188_none += 1
                    if _f188_logged < 5:
                        print(f"[ASAP-POOL-DBG] {sym} ATR=None")
                        _f188_logged += 1
                    continue
                # Ilk 10 degeri logla
                if _f188_logged < 10:
                    print(f"[ASAP-POOL-DBG] {sym} atr%={atr_pct:.3f}")
                    _f188_logged += 1
                if atr_min <= atr_pct <= atr_max:
                    passed.append(sym)
                elif atr_pct < atr_min:
                    _f188_low += 1
                else:
                    _f188_high += 1
            print(f"[ASAP-POOL-DBG] red: low(<{atr_min})={_f188_low} "
                  f"high(>{atr_max})={_f188_high} none={_f188_none} err={_f188_err} "
                  f"passed={len(passed)}")
        else:
            print("[ASAP-POOL] position_manager yok, ATR filtresi atlandi")
            passed = pre[:n_target]

        if not passed:
            print(f"[ASAP-POOL] Hic coin gecemedi (pre={len(pre)}, hedef={n_target})")
            return cache.get("symbols") or []

        self._asap_pool_cache = {"ts": now, "symbols": passed}
        print(f"[ASAP-POOL] {len(passed)} coin secildi (hedef {n_target}, "
              f"on filtre {len(pre)} aday):")
        for s in passed[:10]:
            print(f"         - {s}")
        if len(passed) > 10:
            print(f"         ... +{len(passed)-10} daha")
        return passed

    async def run_strategy(self, strategy_name: str, strat_cfg: dict, candle_cache: dict):
        strategy = self._create_strategy(strategy_name, strat_cfg)
        if not strategy:
            print(f"[!] Bilinmeyen strateji: {strategy_name}")
            return

        # F90a-3: Margin mode'u order_manager'a aktar
        try:
            if self.order_manager:
                self.order_manager.margin_mode = self.config.get("margin_mode", "cross")
        except Exception as _me:
            print(f"[MARGIN] engine set hatasi: {_me}")

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
                    vol_symbols = await self._get_top_volatile(n)
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
            # F181: ASAP icin ozel havuz (30 coin, filtreli)
            if strategy_name == "ASAP":
                scan_symbols = await self._get_asap_pool(strat_cfg)
                if not scan_symbols:
                    print(f"[ASAP-POOL] Havuz bos, {strategy_name} tarama atlandi")
                    return
            else:
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
                candles = await self.fetch_candles(symbol, interval, 300)
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

                # F193b: ASAP icin maxPosPerSymbol kontrolu
                if strategy_name == "ASAP":
                    try:
                        _f193b_max = int(strat_cfg.get("maxPosPerSymbol", 2))
                        if _f193b_max > 0:
                            _conn = get_db_connection()
                            _row = _conn.execute(
                                "SELECT COUNT(*) FROM active_trades WHERE symbol = ? AND strategy_name = 'ASAP'",
                                (symbol,)
                            ).fetchone()
                            _conn.close()
                            _cnt = _row[0] if _row else 0
                            if _cnt >= _f193b_max:
                                _reason = f"Max poz/sembol ({_cnt}/{_f193b_max})"
                                print(f"[F193b] {symbol} {_reason} -> sinyal atlandi")
                                self._save_signal_to_db(
                                    signal_id, symbol, strategy_name, result["signal"],
                                    current_price, qty, base_order, candle_time, created_ms,
                                    opened=0, skip_reason=_reason
                                )
                                self.last_signal_candle[signal_key] = candle_time
                                return
                    except Exception as _e193b:
                        print(f"[F193b] maxPos kontrol hatasi: {_e193b}")

                # F194c: ASAP icin cooldown + maxPos kontrol
                if strategy_name == "ASAP":
                    try:
                        _ok, _rem, _rsn = asap_check_cooldown(symbol)
                        if not _ok:
                            _r = f"Cooldown ({_rsn}) {_rem}s"
                            print(f"[F194c] {symbol} {_r}")
                            self.last_signal_candle[signal_key] = candle_time
                            return
                        _mx = int(strat_cfg.get("maxPosPerSymbol", 1))
                        if _mx > 0:
                            _c = get_db_connection()
                            _row = _c.execute(
                                "SELECT COUNT(*) FROM active_trades WHERE symbol = ? AND strategy_name = 'ASAP'",
                                (symbol,)
                            ).fetchone()
                            _c.close()
                            _cnt = _row[0] if _row else 0
                            if _cnt >= _mx:
                                _r = f"Max poz/sembol ({_cnt}/{_mx})"
                                print(f"[F194c] {symbol} {_r}")
                                self._save_signal_to_db(
                                    signal_id, symbol, strategy_name, result["signal"],
                                    current_price, qty, base_order, candle_time, created_ms,
                                    opened=0, skip_reason=_r
                                )
                                self.last_signal_candle[signal_key] = candle_time
                                return
                    except Exception as _e194c:
                        print(f"[F194c] kontrol hatasi: {_e194c}")

                # ⚡ A1/A2: Risk limit kontrolu
                # FIX F95b: Grid tabanli stratejiler icin Cross %50/50 atlanir
                _side_calc = "BUY" if result["signal"] == "LONG" else "SELL"
                _grid_strategies = ("DYNAMIC_GRID", "DYNAMIC_GRID_REEL")
                _is_grid_strategy = strategy_name in _grid_strategies
                risk_reason = self._check_risk_limits(
                    side=_side_calc,
                    skip_cross_ratio=_is_grid_strategy
                )
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
                    # F90a-3: Margin mode'u garanti et
                    self.order_manager.margin_mode = self.config.get("margin_mode", "cross")

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
                            # F193b: ASAP on_entry
                            if strategy_name == "ASAP":
                                try:
                                    _ec = asap_inc_entry(symbol)
                                    _cd3 = int(strat_cfg.get("cooldownAfter3rdEntry", 180)) * 60
                                    if _ec >= 3:
                                        asap_set_cooldown(symbol, _cd3, f"entry3({_ec})")
                                        print(f"[F193b] {symbol} entry#{_ec} -> cooldown {int(_cd3/60)} dk")
                                except Exception as _e193b2:
                                    print(f"[F193b] on_entry hatasi: {_e193b2}")
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
    async def _reconcile_loop(self):
        """F125b: Her 60 sn'de DB ile Binance'i karsilastir, hayaletleri sil."""
        await asyncio.sleep(20)
        strike_count = {}
        max_strikes = 3
        
        # F125b-hb: Ilk heartbeat hemen
        print("[RECONCILE] Loop basladi (heartbeat)")
        
        while self.is_running:
            try:
                if not self.config.get("active", False):
                    await asyncio.sleep(30)
                    continue
                
                # F125b-hb: Her tick'te heartbeat
                print(f"[RECONCILE] Tick calisiyor...")
                
                try:
                    positions = await asyncio.to_thread(
                        self.order_manager.client.futures_position_information
                    )
                    binance_syms = {
                        p['symbol'] for p in positions
                        if float(p.get("positionAmt", 0) or 0) != 0
                    }
                except Exception as _be:
                    print(f"[RECONCILE] Binance hata: {str(_be)[:100]}")
                    await asyncio.sleep(60)
                    continue
                
                # F127: DB'yi Binance'ten guncelle (boyut + avg_price)
                try:
                    _pos_map = {p['symbol']: p for p in positions if float(p.get("positionAmt", 0) or 0) != 0}
                    _conn_sync = get_db_connection()
                    _updates = 0
                    for _sym, _p in _pos_map.items():
                        try:
                            _amt = abs(float(_p.get("positionAmt", 0) or 0))
                            _entry = float(_p.get("entryPrice", 0) or 0)
                            if _amt <= 0 or _entry <= 0:
                                continue
                            _notional = _amt * _entry
                            
                            # DB'deki mevcut degerle karsilastir
                            _row = _conn_sync.execute(
                                "SELECT id, total_vol, avg_price FROM active_trades WHERE symbol = ?",
                                (_sym,)
                            ).fetchone()
                            if not _row:
                                continue
                            
                            _db_vol = float(_row['total_vol'] or 0)
                            _db_avg = float(_row['avg_price'] or 0)
                            
                            # %1'den fazla fark varsa guncelle
                            _vol_diff = abs(_notional - _db_vol) / max(_db_vol, 0.01)
                            _avg_diff = abs(_entry - _db_avg) / max(_db_avg, 0.000001)
                            
                            if _vol_diff > 0.003 or _avg_diff > 0.003:  # F128: %1 -> %0.3
                                _conn_sync.execute(
                                    "UPDATE active_trades SET total_vol = ?, avg_price = ? WHERE symbol = ?",
                                    (round(_notional, 4), _entry, _sym)
                                )
                                _updates += 1
                                print(f"[F127] {_sym} | vol: {_db_vol:.2f} -> {_notional:.2f} | "
                                      f"avg: {_db_avg:.6f} -> {_entry:.6f}")
                        except Exception as _se:
                            print(f"[F127] {_sym} hata: {str(_se)[:80]}")
                    
                    if _updates > 0:
                        _conn_sync.commit()
                        print(f"[F127] {_updates} pozisyon senkron edildi")
                    _conn_sync.close()
                except Exception as _fe:
                    print(f"[F127] sync hata: {str(_fe)[:100]}")
                
                conn = get_db_connection()
                rows = conn.execute(
                    "SELECT id, symbol, strategy_name FROM active_trades"
                ).fetchall()
                
                ghosts = []
                for r in rows:
                    sym = r['symbol']
                    if sym not in binance_syms:
                        strike_count[sym] = strike_count.get(sym, 0) + 1
                        print(f"[RECONCILE] {sym} strike {strike_count[sym]}/{max_strikes}")
                        if strike_count[sym] >= max_strikes:
                            ghosts.append((r['id'], sym))
                    else:
                        strike_count.pop(sym, None)
                
                if ghosts:
                    import time as _t_f136c
                    _now_f136c = int(_t_f136c.time())
                    for gid, sym in ghosts:
                        # F136: DELETE oncesi history'ye yaz
                        try:
                            _row_g = conn.execute("SELECT * FROM active_trades WHERE id=?", (gid,)).fetchone()
                            if _row_g:
                                _pg = dict(_row_g)
                                _avg_g = float(_pg.get("avg_price") or 0)
                                _vol_g = float(_pg.get("total_vol") or 0)
                                _tt_g = _pg.get("trade_type", "BUY")
                                conn.execute(
                                    """INSERT INTO trade_history
                                       (symbol, trade_type, total_vol, entry_price, initial_price, exit_price,
                                        pnl_amount, pnl_pct, entry_time, exit_time,
                                        strategy_name, dca_count, close_reason, leverage, funding_fee, commission)
                                       VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, 'GHOST-CLEANUP', ?, 0, 0)""",
                                    (sym, _tt_g, _vol_g, _avg_g,
                                     _pg.get("initial_price") or _avg_g, _avg_g,
                                     _pg.get("entry_time"), _now_f136c,
                                     _pg.get("strategy_name") or "UNKNOWN", _pg.get("dca_count") or 0,
                                     _pg.get("leverage") or 1)
                                )
                        except Exception as _hg:
                            print(f"[F136] {sym} history hata: {str(_hg)[:80]}")
                        conn.execute("DELETE FROM active_trades WHERE id=?", (gid,))
                        strike_count.pop(sym, None)
                    conn.commit()
                    print(f"[RECONCILE] {len(ghosts)} hayalet silindi + history: {[g[1] for g in ghosts]}")
                else:
                    # F125b-hb: Her tick'te ozet
                    print(f"[RECONCILE] OK - Binance={len(binance_syms)} DB={len(rows)} strike={len(strike_count)}")
                
                conn.close()
                
            except asyncio.CancelledError:
                return
            except Exception as e:
                print(f"[RECONCILE] hata: {str(e)[:120]}")
            
            await asyncio.sleep(60)

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

        # F208: REPLICA olsa bile sembol listesini doldur (mobile API icin)
        try:
            await self.refresh_symbol_list()
        except Exception as _e208:
            print(f"[F208] refresh_symbol_list hata: {_e208}")

        if _mode == "replica":
            print("[REPLICA-GUARD] Strategy Engine REPLICA modunda - tarama BASLATILMADI (sembol listesi hazir)")
            return

        self.is_running = True
        print("[*] Strategy Engine başlatıldı.")

        # ⚡ Test modunda yanlislikla kilitlenmis PT flag'lerini temizle
        if self.position_manager and hasattr(self.position_manager, '_reset_stuck_pt_flags'):
            self.position_manager._reset_stuck_pt_flags()

        self._scan_task = asyncio.create_task(self._scan_loop())
        self._position_task = asyncio.create_task(self._position_loop())
        # F125b: Otomatik reconcile
        self._reconcile_task = asyncio.create_task(self._reconcile_loop())

        try:
            await asyncio.gather(self._scan_task, self._position_task, self._reconcile_task)
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
        # F125b
        try:
            if hasattr(self, '_reconcile_task') and self._reconcile_task and not self._reconcile_task.done():
                self._reconcile_task.cancel()
        except: pass

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