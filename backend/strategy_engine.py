import asyncio
import json
import os
import time
from binance.client import Client
from backend.strategies import RSIScalperStrategy, HullSRPStrategy, GridbotScalperStrategy
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
            "takeProfit": 1.5, "trailing": 0.3, "stopLoss": 3.0,
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
            "takeProfit": 2.0, "trailing": 0.5, "stopLoss": 3.0,
            "partialTPEnabled": False, "partialTPPercent": 50,
            "partialTPKeepDCA": True
        },
        "GRIDBOT": {
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
        }
    }
}


def load_config() -> dict:
    """Config'i okur. Eksik alanları varsayılandan ekler."""
    if not os.path.exists(CONFIG_PATH):
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
        Ihlal varsa sebep string'i, yoksa bos string doner.
        """
        cfg = self.config or {}

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
    async def fetch_candles(self, symbol: str, interval: str, limit: int = 500):
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
        elif strategy_name == "GRIDBOT":
            return GridbotScalperStrategy(strat_cfg)
        return None

    # ------------------------------------------------------------------
    # Sinyal DB'ye kaydet
    # ------------------------------------------------------------------
    def _save_signal_to_db(self, signal_id, symbol, strategy_name, signal_type,
                            price, qty, total_usdt, candle_time, created_ms, opened=1, skip_reason=None):
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
            conn.close()
        except Exception as e:
            print(f"[!] Sinyal DB kayıt hatası: {e}")

    # ------------------------------------------------------------------
    # Tek stratejiyi tüm sembollerde çalıştır (PARALEL BATCH)
    # ------------------------------------------------------------------
    async def run_strategy(self, strategy_name: str, strat_cfg: dict, candle_cache: dict):
        strategy = self._create_strategy(strategy_name, strat_cfg)
        if not strategy:
            print(f"[!] Bilinmeyen strateji: {strategy_name}")
            return

        interval = strat_cfg.get("interval", "5m")

        BATCH_SIZE = 1
        for batch_start in range(0, len(self.symbols), BATCH_SIZE):
            if not self.is_running:
                return
            batch = self.symbols[batch_start:batch_start + BATCH_SIZE]
            await asyncio.gather(*[
                self._process_symbol(sym, strategy_name, strategy, strat_cfg, interval, candle_cache)
                for sym in batch
            ], return_exceptions=True)
            await asyncio.sleep(1.2)

    # ------------------------------------------------------------------
    # Tek sembol işleme
    # ------------------------------------------------------------------
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
                candles = await self.fetch_candles(symbol, interval, 500)
                candle_cache[cache_key] = candles

            if not candles:
                return

            open_pos = self.get_open_position(symbol)
            result = strategy.evaluate(candles, open_pos)

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

                # ⚡ Emir aç
                if self.order_manager:
                    side = "BUY" if result["signal"] == "LONG" else "SELL"
                    print(f"\n[>> SİNYAL] {symbol} [{strategy_name}] {result['signal']} | {result['reason']}")

                    leverage = int(strat_cfg.get("leverage", 1))
                    
                    self.order_manager.symbol = symbol
                    
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
                    await asyncio.sleep(5)
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
                await asyncio.sleep(5)

    # ------------------------------------------------------------------
    # Başlat / durdur
    # ------------------------------------------------------------------
    async def start(self):
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