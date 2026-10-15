import json
import sqlite3
import os
import shutil
import time
import asyncio
import contextlib
import base64
import secrets
import hashlib as _hashlib
import urllib.request as _urlreq
import urllib.error as _urlerr
from pathlib import Path

from fastapi import HTTPException, Request, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from starlette.staticfiles import StaticFiles as StarletteStaticFiles
from binance.client import Client
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# .ENV DOSYASI
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

print(f"[*] .env dosyası aranıyor: {ENV_PATH}")
print(f"[*] .env var mı: {ENV_PATH.exists()}")

if not ENV_PATH.exists():
    raise RuntimeError(
        f"HATA: .env dosyası bulunamadı!\n"
        f"Beklenen konum: {ENV_PATH}\n"
        f"Lütfen proje kök klasöründe .env dosyası oluşturun."
    )

load_dotenv(dotenv_path=ENV_PATH, override=True)


# ══════════════════════════════════════════════════════════════════
# F147: Trade history LRU cache (100 coin olcegi icin)
# ══════════════════════════════════════════════════════════════════
import threading as _threading_f147

_HIST_CACHE_F147 = {}
_HIST_CACHE_LOCK_F147 = _threading_f147.Lock()
_HIST_CACHE_TTL_F147 = 15        # saniye
_HIST_CACHE_CAP_F147 = 300       # maksimum entry (100 coin + history varyantlari)


def _f147_cache_get(key):
    with _HIST_CACHE_LOCK_F147:
        ent = _HIST_CACHE_F147.get(key)
        if ent and (time.time() - ent[0]) < _HIST_CACHE_TTL_F147:
            return ent[1]
        return None


def _f147_cache_put(key, value):
    with _HIST_CACHE_LOCK_F147:
        _HIST_CACHE_F147[key] = (time.time(), value)
        if len(_HIST_CACHE_F147) > _HIST_CACHE_CAP_F147:
            # En eski %20'yi temizle
            n_drop = _HIST_CACHE_CAP_F147 // 5
            oldest = sorted(_HIST_CACHE_F147.items(),
                            key=lambda kv: kv[1][0])[:n_drop]
            for k, _ in oldest:
                _HIST_CACHE_F147.pop(k, None)


def _f147_indexes_ensure():
    """F147: composite index'leri bir kez olustur."""
    try:
        _c = get_db_connection()
        _c.execute("CREATE INDEX IF NOT EXISTS idx_history_symbol_exit "
                   "ON trade_history(symbol, exit_time DESC)")
        _c.execute("CREATE INDEX IF NOT EXISTS idx_history_exit "
                   "ON trade_history(exit_time DESC)")
        _c.commit()
        _c.close()
        print("[F147] history indexleri hazir")
    except Exception as _e147:
        print(f"[F147] index hata: {_e147}")


# Startup'ta bir kez calistir
try:
    _f147_indexes_ensure()
except Exception:
    pass


API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
USE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
# F117: SIMULATE_ORDERS env - true ise emirler simule edilir, false ise Binance'e gonderilir
SIMULATE_ORDERS = os.getenv("SIMULATE_ORDERS", "false").lower() == "true"

# ⚡ Web arayuz sifre korumasi
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
AUTH_ENABLED = bool(ADMIN_PASSWORD)

# DB Sync
SYNC_MODE = os.getenv("SYNC_MODE", "standalone").strip().lower()
IS_MASTER = (SYNC_MODE == "master")
IS_REPLICA = (SYNC_MODE == "replica")
CLOUD_SYNC_URL = os.getenv("CLOUD_SYNC_URL", "").strip().rstrip("/")
SYNC_TOKEN = os.getenv("SYNC_TOKEN", "").strip()
SYNC_INTERVAL_SEC = int(os.getenv("SYNC_INTERVAL_SEC", "30"))
SYNC_ENABLED = IS_MASTER and bool(CLOUD_SYNC_URL) and bool(SYNC_TOKEN)

print(f"[*] Sync modu: {SYNC_MODE} | master={IS_MASTER} replica={IS_REPLICA}")
if SYNC_ENABLED:
    print(f"[*] Sync aktif: {CLOUD_SYNC_URL} (her {SYNC_INTERVAL_SEC}sn)")

print(f"[*] API_KEY yüklendi mi: {'EVET' if API_KEY else 'HAYIR'}")
print(f"[*] API_SECRET yüklendi mi: {'EVET' if API_SECRET else 'HAYIR'}")
print(f"[*] Testnet modu: {USE_TESTNET}")
print(f"[*] Web Arayuz Auth: {'AKTIF' if AUTH_ENABLED else 'PASIF'} (kullanici: {ADMIN_USERNAME})")

if not API_KEY or not API_SECRET:
    raise RuntimeError("HATA: .env dosyasında BINANCE_API_KEY veya BINANCE_API_SECRET eksik!")

# ----------------------------------------------------------------------
# BACKEND MODÜLLERİ
# ----------------------------------------------------------------------
from backend.strategy_engine import StrategyEngine, load_config, save_config
from backend.order_manager import OrderManager
from backend.position_manager import PositionManager
from backend.database import init_db, get_db_connection
from backend import telegram_notifier

# ----------------------------------------------------------------------
# BINANCE CLIENT + MOTORLAR
# ----------------------------------------------------------------------
def _create_binance_client(max_retries=5, delay_sec=10):
    """F132: Binance client olustur, 502/503 alirsa retry."""
    import time as _t
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            # F134: ping=False - Spot testnet down olsa bile client olusur
            # Ilk futures cagrisi FUTURES testnet'e otomatik baglanir
            try:
                c = Client(API_KEY, API_SECRET, testnet=USE_TESTNET, ping=False)
            except TypeError:
                # Eski surum ping param yoksa - fallback subclass
                _orig_init = Client.__init__
                def _patched_init(self, *args, **kwargs):
                    kwargs['ping'] = False
                    try:
                        _orig_init(self, *args, **kwargs)
                    except TypeError:
                        kwargs.pop('ping', None)
                        _orig_init(self, *args, **kwargs)
                Client.__init__ = _patched_init
                c = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)
            print(f"[F132] Binance client OK (deneme {attempt})")
            return c
        except Exception as _e:
            last_err = _e
            _msg = str(_e)[:120]
            print(f"[F132] Client deneme {attempt}/{max_retries} HATA: {_msg}")
            if attempt < max_retries:
                _t.sleep(delay_sec)
    print(f"[F132] [UYARI] {max_retries} denemede client olusturulamadi. Son hata: {last_err}")
    print(f"[F132] Backend offline modda baslayacak. /api/health endpointi bos donebilir.")
    return None


client = _create_binance_client()
if client is None:
    print("[F132] [UYARI] Binance client None! OrderManager olusturulamiyor.")
    order_manager = None
else:
    order_manager = OrderManager(client, symbol="BTCUSDT", test_mode=SIMULATE_ORDERS)  # F117: SIMULATE_ORDERS env
position_manager = PositionManager(client, order_manager=order_manager)
bot = StrategyEngine(client, order_manager=order_manager, position_manager=position_manager)


# ----------------------------------------------------------------------
# SUNUCU YAŞAM DÖNGÜSÜ
# ----------------------------------------------------------------------
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # ⚡ REPLICA KORUMASI: Cloud'da bot ASLA calismaz
    if IS_REPLICA:
        print("[REPLICA-GUARD] Replica modu algilandi - bot BASLATILMIYOR")
        # F202: Sadece memory'de active=False yap. DISKE YAZMA!
        # Sebep: load_config() normalize ediyor ve dosya kucultiyor (5949->5730)
        try:
            _cfg = load_config()
            if _cfg.get("active", False):
                _cfg["active"] = False
                # save_config(_cfg)  # F202: KALDIRILDI
                bot.config = _cfg
                print("[REPLICA-GUARD] bot_config.active = False (memory only, disk dokunulmadi)")
            else:
                print("[REPLICA-GUARD] bot_config.active zaten False")
        except Exception as _e:
            print(f"[REPLICA-GUARD] Config override hatasi: {_e}")

        # Sync loop calissin (replica veri alir)
        sync_task = asyncio.create_task(_sync_loop()) if SYNC_ENABLED else None

        try:
            yield
        finally:
            if sync_task:
                sync_task.cancel()
                try:
                    await sync_task
                except asyncio.CancelledError:
                    pass
    else:
        # MASTER modu - normal akis
        task = asyncio.create_task(bot.start())
        sync_task = asyncio.create_task(_sync_loop()) if SYNC_ENABLED else None
        try:
            yield
        finally:
            bot.stop()
            task.cancel()
            if sync_task:
                sync_task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if sync_task:
                try:
                    await sync_task
                except asyncio.CancelledError:
                    pass


# ----------------------------------------------------------------------
# FASTAPI
# ----------------------------------------------------------------------
app = FastAPI(title="Broker System API", lifespan=lifespan)


@app.middleware("http")
async def readonly_middleware(request: Request, call_next):
    if not IS_REPLICA:
        return await call_next(request)
    if request.url.path.startswith("/api/sync/"):
        return await call_next(request)
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        return Response(
            content='{"status":"error","message":"Replica mode: read-only"}',
            status_code=403,
            media_type="application/json"
        )
    return await call_next(request)


# ======================================================================
# HTTP BASIC AUTH MIDDLEWARE
# ======================================================================
from fastapi import Request
from fastapi.responses import Response


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Tum endpoint'leri HTTP Basic Auth ile korur."""
    # Auth kapaliysa gecir
    if not AUTH_ENABLED:
        return await call_next(request)

    # Favicon ve robots.txt bypass
    if request.url.path in ("/favicon.ico", "/robots.txt"):
        return await call_next(request)

    # ⚡ Sync endpoint bypass (X-Sync-Token ile korunuyor)
    if request.url.path.startswith("/api/sync/"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")

    # Header yoksa 401
    if not auth_header.startswith("Basic "):
        return Response(
            content="Kimlik dogrulama gerekli",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Broker System", charset="UTF-8"'}
        )

    # Decode
    try:
        encoded = auth_header[6:]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return Response(
            content="Gecersiz auth formati",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Broker System", charset="UTF-8"'}
        )

    # Timing-safe karsilastirma
    user_ok = secrets.compare_digest(username.encode(), ADMIN_USERNAME.encode())
    pass_ok = secrets.compare_digest(password.encode(), ADMIN_PASSWORD.encode())

    if not (user_ok and pass_ok):
        print(f"[AUTH] BASARISIZ giris denemesi: {username} ({request.client.host})")
        return Response(
            content="Kullanici adi veya sifre hatali",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Broker System", charset="UTF-8"'}
        )

    # Basarili
    return await call_next(request)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


class NoCacheStaticFiles(StarletteStaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.mount("/static", NoCacheStaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ----------------------------------------------------------------------
# DEV TOOLS - Backend stop / restart
# ----------------------------------------------------------------------
@app.post("/api/dev/stop")
async def dev_stop():
    """Backend process'ini kapatir (dev araci)."""
    async def _delayed_exit():
        await asyncio.sleep(0.8)
        print("[DEV] Backend kapatiliyor (os._exit)...")
        os._exit(0)
    asyncio.create_task(_delayed_exit())
    return {"status": "success", "message": "Backend kapatiliyor"}


@app.post("/api/dev/restart")
async def dev_restart():
    """main.py mtime'ini gunceller -> uvicorn --reload yeniden baslatir."""
    try:
        import time as _time
        main_file = Path(__file__)
        os.utime(main_file, (_time.time(), _time.time()))
        print("[DEV] Reload tetiklendi (main.py touch)")
        return {"status": "success", "message": "Reload tetiklendi"}
    except Exception as e:
        return {"status": "error", "message": str(e)}



# ----------------------------------------------------------------------
# TEMEL
# ----------------------------------------------------------------------
@app.get("/m")
async def mobile_index():
    """Mobil dashboard (izole)."""
    return FileResponse(str(FRONTEND_DIR / "mobile" / "index.html"))


@app.get("/mobile")
async def mobile_index_alias():
    """Mobil dashboard alias."""
    return FileResponse(str(FRONTEND_DIR / "mobile" / "index.html"))


@app.get("/")
async def read_index(request: Request):
    # Mobil UA -> /m yonlendir (desktop=1 ile opt-out)
    try:
        ua = request.headers.get("user-agent", "").lower()
        is_mobile = any(x in ua for x in [
            "iphone", "ipod", "android", "mobile",
            "blackberry", "opera mini", "windows phone"
        ])
        if is_mobile and "desktop=1" not in str(request.url):
            return RedirectResponse(url="/m")
    except Exception as _e:
        print(f"[MOBILE-REDIRECT] hata: {_e}")
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/favicon.ico")
async def favicon():
    """Tarayıcının otomatik istediği favicon.ico'yu SVG'ye yönlendirir."""
    return RedirectResponse(url="/static/favicon.svg")


# ----------------------------------------------------------------------
# CÜZDAN
# ----------------------------------------------------------------------
# F18: Global ticker cache (paylasilan)
_TICKER_CACHE = {"ts": 0, "data": None}
_TICKER_CACHE_TTL = 10  # saniye

_WALLET_RATE_LOG = {"ts": 0}


async def _get_futures_tickers_cached():
    """futures_ticker sonucu 10 sn cache."""
    import time as _t
    _now = _t.time()
    if _TICKER_CACHE["data"] and (_now - _TICKER_CACHE["ts"]) < _TICKER_CACHE_TTL:
        return _TICKER_CACHE["data"]
    try:
        tickers = await asyncio.to_thread(client.futures_ticker)
        _TICKER_CACHE["ts"] = _now
        _TICKER_CACHE["data"] = tickers
        return tickers
    except Exception as e:
        _err = str(e)
        if "-1003" in _err or "Too many" in _err:
            print(f"[TICKER] Rate limit - eski cache donduruluyor")
            return _TICKER_CACHE["data"] or []
        raise


# F9: Wallet cache (30 sn)
_WALLET_CACHE = {"ts": 0, "data": None}
_WALLET_CACHE_TTL = 30  # saniye


# F60a: Risk metrikleri
def _calc_risk_metrics_sync():
    """
    Kullanilan marjin / guncel bakiye * 100
    Guncel bakiye = wallet + unrealized PnL
    """
    try:
        used_margin = 0.0
        unrealized = 0.0
        trade_count = 0

        conn = get_db_connection()
        rows = conn.execute("""
            SELECT symbol, total_vol, leverage, trade_type, avg_price
            FROM active_trades
        """).fetchall()
        conn.close()

        for r in rows:
            r = dict(r)
            vol = float(r.get("total_vol") or 0)
            lev = max(1, int(r.get("leverage") or 1))
            used_margin += vol / lev
            trade_count += 1

        # Bakiye
        try:
            balances = client.futures_account_balance()
            balance = 0.0
            for b in balances:
                if b.get("asset") == "USDT":
                    balance = float(b.get("balance", 0))
                    break
        except Exception:
            balance = 0.0

        equity = max(balance, 0.01)
        risk_pct = (used_margin / equity) * 100 if equity > 0 else 0

        return {
            "used_margin": round(used_margin, 4),
            "equity": round(equity, 4),
            "balance": round(balance, 4),
            "unrealized": round(unrealized, 4),
            "risk_pct": round(risk_pct, 2),
            "trade_count": trade_count,
        }
    except Exception as e:
        print(f"[RISK] Hesap hatasi: {e}")
        return {
            "used_margin": 0, "equity": 0, "balance": 0,
            "unrealized": 0, "risk_pct": 0, "trade_count": 0,
        }


@app.get("/api/risk/status")
async def risk_status():
    """Anlik risk seviyesi."""
    m = await asyncio.to_thread(_calc_risk_metrics_sync)

    # Config'den esik
    try:
        cfg = load_config()
        max_ratio = float(cfg.get("max_margin_ratio", 60.0))
    except Exception:
        max_ratio = 60.0

    m["max_ratio"] = max_ratio
    m["is_over_limit"] = m["risk_pct"] >= max_ratio
    m["status"] = "critical" if m["is_over_limit"] else "ok"

    return m


@app.get("/api/wallet")
async def get_wallet():
    # Cache kontrolu
    import time as _t
    _now = _t.time()
    if _WALLET_CACHE["data"] and (_now - _WALLET_CACHE["ts"]) < _WALLET_CACHE_TTL:
        return _WALLET_CACHE["data"]

    try:
        assets = []
        total_usdt = 0.0
        available_usdt = 0.0

        # --- FUTURES BAKIYE ---
        try:
            futures_balances = await asyncio.to_thread(client.futures_account_balance)
            for b in futures_balances:
                bal = float(b.get('balance', 0))
                avail = float(b.get('withdrawAvailable', b.get('availableBalance', 0)))
                asset = b.get('asset', '')
                if asset == 'USDT':
                    total_usdt += bal
                    available_usdt += avail
                if bal > 0 or avail > 0:
                    assets.append({
                        "coin": asset,
                        "wallet_type": "Vadeli",
                        "balance": f"{bal:.4f}" if bal < 1 else f"{bal:.2f}",
                        "available": f"{avail:.4f}" if avail < 1 else f"{avail:.2f}"
                    })
        except Exception as e:
            _err = str(e)
            if "-1003" in _err or "Too many requests" in _err:
                import time as _t2
                _n = _t2.time()
                if _n - _WALLET_RATE_LOG["ts"] >= 180:
                    _WALLET_RATE_LOG["ts"] = _n
                    print(f"[WALLET] Rate limit (futures) - 3dk susturuldu")
            else:
                print(f"[!] Futures bakiye okuma hatasi: {_err[:120]}")

        # --- SPOT BAKIYE (sadece mainnet) ---
        # Testnet'te spot API izni yok (-2015 hatasi normal)
        if not USE_TESTNET:
            try:
                spot_account = await asyncio.to_thread(client.get_account)
                for b in spot_account.get('balances', []):
                    free = float(b.get('free', 0))
                    locked = float(b.get('locked', 0))
                    total = free + locked
                    if total > 0.0001:
                        assets.append({
                            "coin": b.get('asset', ''),
                            "wallet_type": "Spot",
                            "balance": f"{total:.4f}" if total < 1 else f"{total:.2f}",
                            "available": f"{free:.4f}" if free < 1 else f"{free:.2f}"
                        })
            except Exception as e:
                print(f"[!] Spot bakiye okuma hatasi: {str(e)[:120]}")

        result = {
            "status": "success",
            "balance": round(total_usdt, 2),
            "available": round(available_usdt, 2),
            "assets": assets,
            "cached_at": int(_now),
        }

        # Cache'e yaz
        _WALLET_CACHE["ts"] = _now
        _WALLET_CACHE["data"] = result

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------------------------------------------------------------
# BOT STATUS
# ----------------------------------------------------------------------
@app.get("/api/bot/status")
async def get_bot_status():
    return bot.get_status()


# ----------------------------------------------------------------------
# STRATEJİ MOTORU ENDPOINT'LERİ
# ----------------------------------------------------------------------
@app.get("/api/engine/status")
async def engine_status():
    return bot.get_status()


@app.get("/api/symbols/list")
async def symbols_list():
    """
    Bot'un taranan TUM sembol listesini dondurur.
    Mobile manuel emir dropdown icin kullanilir.
    """
    symbols = list(bot.symbols or [])
    return {
        "status": "success",
        "count": len(symbols),
        "symbols": symbols
    }


@app.get("/api/engine/signals")
async def engine_signals():
    return bot.latest_signals


@app.get("/api/engine/config")
async def get_engine_config():
    return bot.config


# ============================================================
# CHART SETTINGS ENDPOINTS (Kalici Grafik Ayarlari)
# ============================================================
# F36: Chart settings ayri dosyada (race condition fix)
_CHART_SETTINGS_PATH = Path(__file__).resolve().parent / "chart_settings.json"


def _load_chart_settings():
    if not _CHART_SETTINGS_PATH.exists():
        return {}
    try:
        with open(_CHART_SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[CHART-SETTINGS] load hata: {e}")
        return {}


def _save_chart_settings(data):
    try:
        with open(_CHART_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[CHART-SETTINGS] save hata: {e}")
        return False


@app.get("/api/chart-settings")
def get_chart_settings():
    """Grafik ayarlarini chart_settings.json'dan dondurur (ayri dosya)."""
    return _load_chart_settings()


@app.post("/api/chart-settings")
def update_chart_settings(settings: dict):
    """Grafik ayarlarini chart_settings.json'a kaydeder (ayri dosya)."""
    ok = _save_chart_settings(settings)
    if ok:
        return {"status": "ok", "saved": True}
    return {"status": "error", "message": "Kaydetme basarisiz"}


@app.post("/api/engine/config")
async def update_engine_config(new_cfg: dict):
    # F90a: Margin mode degisti mi?
    try:
        old_cfg = load_config()
        old_mode = old_cfg.get("margin_mode", "cross")
        new_mode = new_cfg.get("margin_mode", old_mode)

        if old_mode != new_mode:
            presets = new_cfg.get("margin_presets", {}) or {}
            preset = presets.get(new_mode, {}) or {}

            # Aktif pozisyon var mi kontrol
            try:
                conn = get_db_connection()
                cnt = conn.execute("SELECT COUNT(*) FROM active_trades").fetchone()[0]
                conn.close()
            except Exception:
                cnt = 0

            if cnt > 0:
                print(f"[MARGIN] Mod degisikligi var ama {cnt} acik pozisyon! "
                      f"Sadece YENI pozisyonlar etkilenecek.")

            applied = 0
            for sname, scfg in (new_cfg.get("strategies", {}) or {}).items():
                if isinstance(scfg, dict):
                    for k, v in preset.items():
                        scfg[k] = v
                    applied += 1

            print(f"[MARGIN] Mod degisti: {old_mode} -> {new_mode}")
            print(f"[MARGIN] Preset uygulandi: {preset} ({applied} strateji)")
    except Exception as e:
        print(f"[MARGIN] Preset uygulama hatasi: {e}")

    save_config(new_cfg)
    bot.config = new_cfg
    return {"status": "success", "config": new_cfg}


@app.post("/api/engine/toggle")
async def toggle_engine(active: bool = True, force: bool = False):
    """Motoru açar/kapatır. Kapatırken açık pozisyon uyarısı verir."""
    cfg = load_config()

    if not active and not force:
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) as c FROM active_trades").fetchone()["c"]
        conn.close()
        if count > 0:
            return {
                "status": "warning",
                "active_positions": count,
                "message": f"{count} açık pozisyon var. force=true ile zorla kapatabilirsiniz."
            }

    cfg["active"] = active
    save_config(cfg)
    bot.config = cfg
    print(f"[*] Strateji motoru {'AKTİF' if active else 'PASİF'} edildi.")
    return {"status": "success", "active": active}


@app.post("/api/engine/symbols/refresh")
async def refresh_symbols():
    await bot.refresh_symbol_list()
    return {"status": "success", "symbols_count": len(bot.symbols)}


# ----------------------------------------------------------------------
# SON SİNYALLER (DB'den — kalıcı)
# ----------------------------------------------------------------------
@app.get("/api/engine/recent-signals")
async def get_recent_signals(limit: int = 100):
    """
    Sinyaller + kapanan işlemleri birleşik döner.
    Her kayıt event_type: "signal" | "close"
    Timestamp DESC sıralı.
    """
    conn = get_db_connection()
    
    # Açılan sinyaller
    signals_rows = conn.execute(
        """SELECT signal_id as id, symbol, strategy_name as strategy, signal, 
                  price, qty, total_usdt, candle_time, created_at, 
                  opened_position, skip_reason
           FROM signals 
           ORDER BY created_at DESC 
           LIMIT ?""",
        (limit,)
    ).fetchall()
    
    # Kapanan işlemler
    closes_rows = conn.execute(
        """SELECT id, symbol, trade_type, total_vol, entry_price, exit_price,
                  pnl_amount, pnl_pct, entry_time, exit_time, strategy_name,
                  dca_count, close_reason, leverage, is_partial, commission
           FROM trade_history 
           ORDER BY exit_time DESC 
           LIMIT ?""",
        (limit,)
    ).fetchall()
    
    conn.close()
    
    result = []
    
    # Sinyalleri işle
    for r in signals_rows:
        d = dict(r)
        d["event_type"] = "signal"
        d["display_symbol"] = d["symbol"] + ".P"
        d["timestamp"] = d.get("created_at", 0)
        result.append(d)
    
    # Kapanışları işle
    for r in closes_rows:
        d = dict(r)
        d["event_type"] = "close"
        d["display_symbol"] = d["symbol"] + ".P"
        d["timestamp"] = (d.get("exit_time") or 0) * 1000  # saniye → ms
        d["signal"] = "LONG" if d.get("trade_type") == "BUY" else "SHORT"
        result.append(d)
    
    # Timestamp DESC sırala
    result.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    
    return result[:limit]


# ----------------------------------------------------------------------
# MANUEL EMİR
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# MANUEL EMIR - Detayli form ile manuel emir acma
# ----------------------------------------------------------------------
@app.post("/api/trade/manual")
async def manual_order(payload: dict):
    """
    Manuel emir acma (MARKET / LIMIT).
    Ayni sembolde acik pozisyon varsa 'duplicate_warning' doner.
    confirm_overwrite=true ise MANUAL strateji olarak acilir.
    """
    import time as _t

    symbol = str(payload.get("symbol", "")).upper().replace(".P", "")
    side = str(payload.get("side", "BUY")).upper()
    order_mode = str(payload.get("order_mode", "market")).lower()
    base_order = float(payload.get("base_order", 100))
    leverage = int(payload.get("leverage", 1))
    limit_price = float(payload.get("limit_price", 0) or 0)
    limit_timeout = int(payload.get("limit_timeout", 5))
    take_profit = float(payload.get("take_profit", 0) or 0)
    trailing_steps = str(payload.get("trailingSteps", "") or "")
    stop_loss = float(payload.get("stop_loss", 0) or 0)
    pt_enabled = 1 if payload.get("partial_tp_enabled") else 0
    pt_percent = float(payload.get("partial_tp_percent", 50))
    pt_keep_dca = 1 if payload.get("partial_tp_keep_dca", True) else 0
    confirm_overwrite = bool(payload.get("confirm_overwrite", False))

    # Validasyon
    if not symbol:
        return {"status": "error", "message": "Sembol gerekli"}
    if side not in ("BUY", "SELL"):
        return {"status": "error", "message": "Gecersiz yon"}
    if base_order <= 0:
        return {"status": "error", "message": "Miktar > 0 olmali"}
    if order_mode not in ("market", "limit", "limit_with_fallback"):
        return {"status": "error", "message": "Gecersiz emir tipi"}
    if order_mode in ("limit", "limit_with_fallback") and limit_price <= 0 and order_mode == "limit":
        return {"status": "error", "message": "LIMIT icin fiyat gerekli"}

    # Duplicate kontrol: ayni sembolde strateji pozisyonu var mi?
    if not confirm_overwrite:
        conn = get_db_connection()
        existing = conn.execute(
            """SELECT id, strategy_name, trade_type FROM active_trades
               WHERE symbol = ? AND COALESCE(is_grid_position,0) = 0
                 AND (strategy_name IS NULL OR strategy_name != 'MANUAL')""",
            (symbol,)
        ).fetchone()
        conn.close()

        if existing:
            return {
                "status": "duplicate_warning",
                "message": f"{symbol} icin zaten acik pozisyon var ({existing['strategy_name']}).",
                "existing": dict(existing)
            }

    # Emir ac
    order_manager.symbol = symbol
    result = await asyncio.to_thread(
        order_manager.open_manual_position,
        side=side,
        base_amount_usdt=base_order,
        order_mode=order_mode,
        leverage=leverage,
        limit_price=limit_price,
        limit_timeout=limit_timeout,
        take_profit=take_profit,
        trailing_steps=trailing_steps,
        stop_loss=stop_loss,
        pt_enabled=pt_enabled,
        pt_percent=pt_percent,
        pt_keep_dca=pt_keep_dca,
    )

    print(f"[MANUAL] {symbol} {side} {order_mode} | {base_order} USDT | {leverage}x | "
          f"result={result.get('status')}")

    return result


@app.post("/api/trade/open")
async def trigger_trade(symbol: str = "BTCUSDT", side: str = "BUY"):
    clean_symbol = symbol.replace(".P", "")
    order_manager.symbol = clean_symbol
    result = order_manager.open_dca_position(side=side, base_amount_usdt=10.0,
                                              strategy_name="MANUAL")
    return result


@app.post("/api/trade/close")
async def trigger_close(symbol: str = "BTCUSDT"):
    clean_symbol = symbol.replace(".P", "")
    result = order_manager.close_position(symbol=clean_symbol)
    return result


@app.post("/api/trade/close-all")
async def close_all_trades():
    """
    FIX B3: Sadece KLASIK (grid olmayan) pozisyonlari kapatir.
    Grid pozisyonu OLAN semboller ATLANIR (Binance emirleri korunur).
    """
    conn = get_db_connection()
    trades = conn.execute("""
        SELECT DISTINCT symbol FROM active_trades
        WHERE COALESCE(is_grid_position, 0) = 0
          AND symbol NOT IN (
              SELECT symbol FROM active_trades WHERE is_grid_position = 1
          )
    """).fetchall()
    conn.close()
    results = []
    for t in trades:
        r = order_manager.close_position(symbol=t["symbol"])
        results.append({"symbol": t["symbol"], "result": r.get("status")})
    return {"status": "success", "closed": len(results), "details": results}


@app.post("/api/trade/close-all-force")
async def close_all_trades_force():
    """
    F119 - Binance-driven close-all-force.
    SORUN COZUMU: Once Binance API'den TUM acik pozisyonlari cek
    (DB symbol listesine guvenmiyoruz), sonra hepsini parcalara bolerek kapat.
    Max qty limitini otomatik handle eder.
    """
    import math as _math
    import asyncio as _aio

    # 1) DB sayilari (rapor icin)
    conn = get_db_connection()
    n_classic = conn.execute(
        "SELECT COUNT(*) FROM active_trades WHERE COALESCE(is_grid_position,0)=0"
    ).fetchone()[0]
    n_grid = conn.execute(
        "SELECT COUNT(*) FROM active_trades WHERE is_grid_position=1"
    ).fetchone()[0]
    db_symbols = [r["symbol"] for r in conn.execute(
        "SELECT DISTINCT symbol FROM active_trades"
    ).fetchall()]

    is_real = hasattr(order_manager, "client") and not getattr(order_manager, "test_mode", False)

    if not is_real:
        # Test modu: sadece DB temizle
        conn.execute("DELETE FROM active_trades")
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "closed_classic": n_classic,
            "closed_grid": n_grid,
            "total": n_classic + n_grid,
            "mode": "test",
            "message": "Test modu - sadece DB temizlendi",
        }

    # 2) Binance'ten TUM acik pozisyonlari cek (F119!)
    print("[CLOSE-ALL-FORCE] F119: Binance'ten TUM pozisyonlar cekiliyor...")
    try:
        all_positions = order_manager.client.futures_position_information()
    except Exception as _e:
        return {"status": "error", "message": f"Binance pozisyon sorgu: {_e}"}

    open_pos = [p for p in all_positions if float(p.get("positionAmt", 0)) != 0]
    print(f"[CLOSE-ALL-FORCE] Binance'te {len(open_pos)} acik pozisyon bulundu")

    # DB disi (hayalet) pozisyonlar
    ghost_syms = [p['symbol'] for p in open_pos if p['symbol'] not in db_symbols]
    if ghost_syms:
        print(f"[CLOSE-ALL-FORCE] HAYALET pozisyonlar (DB disi): {len(ghost_syms)}")
        for s in ghost_syms[:10]:
            print(f"   - {s}")

    # 3) Exchange info cache (maxQty icin)
    try:
        _exchange_info = order_manager.client.futures_exchange_info()
        _sym_map = {s['symbol']: s for s in _exchange_info['symbols']}
    except Exception as _e:
        print(f"[CLOSE-ALL-FORCE] Exchange info uyari: {_e}")
        _sym_map = {}

    # 4) Acik emirleri iptal et (Binance'ten TUM)
    cancelled = 0
    try:
        all_orders = order_manager.client.futures_get_open_orders()
        for _o in all_orders:
            try:
                order_manager.client.futures_cancel_order(symbol=_o['symbol'], orderId=_o['orderId'])
                cancelled += 1
            except Exception:
                pass
        print(f"[CLOSE-ALL-FORCE] {cancelled} acik emir iptal edildi")
    except Exception as _e:
        print(f"[CLOSE-ALL-FORCE] Emir iptal uyari: {_e}")

    # 5) Her pozisyonu MARKET reduceOnly ile kapat (maxQty handling ile)
    closed_pos = 0
    failed = 0
    closed_syms = []

    for _p in open_pos:
        _sym = _p['symbol']
        _amt = float(_p['positionAmt'])
        if _amt == 0:
            continue

        _side = "SELL" if _amt > 0 else "BUY"
        _total_qty = abs(_amt)

        # maxQty ve stepSize bul
        _max_qty = None
        _step = None
        _sym_info = _sym_map.get(_sym)
        if _sym_info:
            for _f in _sym_info['filters']:
                if _f['filterType'] == 'MARKET_LOT_SIZE':
                    _max_qty = float(_f['maxQty'])
                    _step = float(_f['stepSize'])
                    break
            if not _max_qty:
                for _f in _sym_info['filters']:
                    if _f['filterType'] == 'LOT_SIZE':
                        _max_qty = float(_f['maxQty'])
                        _step = float(_f['stepSize'])
                        break

        try:
            if _max_qty and _step and _total_qty > _max_qty:
                # Parcalara bol
                _chunk = _math.floor(_max_qty * 0.9 / _step) * _step
                _remaining = _total_qty
                _iter = 0
                _ok = True
                while _remaining > 0 and _iter < 50:
                    _iter += 1
                    _this_qty = min(_chunk, _remaining)
                    _this_qty = _math.floor(_this_qty / _step) * _step
                    if _this_qty <= 0:
                        break
                    try:
                        order_manager.client.futures_create_order(
                            symbol=_sym, side=_side, type="MARKET",
                            quantity=_this_qty, reduceOnly=True
                        )
                        _remaining -= _this_qty
                    except Exception as _ce:
                        print(f"[CLOSE-ALL-FORCE] {_sym} parca hata: {str(_ce)[:100]}")
                        _ok = False
                        break
                if _ok:
                    closed_pos += 1
                    closed_syms.append(_sym)
                    print(f"[CLOSE-ALL-FORCE] {_sym} pozisyon kapatildi (parcali, amt={_amt})")
                else:
                    failed += 1
            else:
                # Tek emir yeterli
                order_manager.client.futures_create_order(
                    symbol=_sym, side=_side, type="MARKET",
                    quantity=_total_qty, reduceOnly=True
                )
                closed_pos += 1
                closed_syms.append(_sym)
                print(f"[CLOSE-ALL-FORCE] {_sym} pozisyon kapatildi (amt={_amt})")
        except Exception as _pe:
            failed += 1
            print(f"[CLOSE-ALL-FORCE] {_sym} HATA: {str(_pe)[:120]}")

    # 6) DB temizligi (F136: once history'ye yaz)
    try:
        import time as _t_f136
        _now_f136 = int(_t_f136.time())
        _rows_f136 = conn.execute("SELECT * FROM active_trades").fetchall()
        for _r in _rows_f136:
            try:
                _pos = dict(_r)
                _avg = float(_pos.get("avg_price") or 0)
                _vol = float(_pos.get("total_vol") or 0)
                _ttype = _pos.get("trade_type", "BUY")
                _strat = _pos.get("strategy_name") or "UNKNOWN"
                _lev = _pos.get("leverage") or 1
                # Gercek exit fiyatini Binance'ten al (varsa)
                _exit = 0
                try:
                    _bp = binance_positions.get(_pos['symbol'])
                    if _bp:
                        _exit = _bp.get("mark_price") or 0
                except Exception:
                    pass
                if _exit <= 0:
                    _exit = _avg
                # PnL hesabi (mark'a gore)
                if _ttype == "BUY":
                    _pnl_pct = (_exit - _avg) / _avg if _avg > 0 else 0
                else:
                    _pnl_pct = (_avg - _exit) / _avg if _avg > 0 else 0
                _pnl_usdt = _vol * _pnl_pct
                conn.execute(
                    """INSERT INTO trade_history
                       (symbol, trade_type, total_vol, entry_price, initial_price, exit_price,
                        pnl_amount, pnl_pct, entry_time, exit_time,
                        strategy_name, dca_count, close_reason, leverage, funding_fee, commission)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CLOSE-ALL-FORCE', ?, 0, 0)""",
                    (_pos['symbol'], _ttype, _vol, _avg,
                     _pos.get("initial_price") or _avg, _exit,
                     _pnl_usdt, _pnl_pct * 100, _pos.get("entry_time"), _now_f136,
                     _strat, _pos.get("dca_count") or 0, _lev)
                )
            except Exception as _e_h:
                print(f"[F136] {_pos.get('symbol','?')} history hata: {str(_e_h)[:80]}")
        print(f"[F136] {len(_rows_f136)} pozisyon trade_history'ye yazildi (CLOSE-ALL-FORCE)")
    except Exception as _e_h_all:
        print(f"[F136] history kayit genel hata: {_e_h_all}")
    
    conn.execute("DELETE FROM active_trades")
    conn.execute("DELETE FROM grid_state")
    conn.commit()
    conn.close()

    print(f"[CLOSE-ALL-FORCE] OZET: {closed_pos} kapandi, {failed} basarisiz, DB {n_classic+n_grid} silindi")

    return {
        "status": "success",
        "closed_classic": n_classic,
        "closed_grid": n_grid,
        "total": n_classic + n_grid,
        "binance_found": len(open_pos),
        "binance_closed": closed_pos,
        "binance_failed": failed,
        "ghost_positions": len(ghost_syms),
        "symbols": closed_syms[:50],
        "cancelled_orders": cancelled,
        "mode": "real",
    }


@app.get("/api/trade/active-with-pnl")
async def get_active_trades_with_pnl():
    """Aktif pozisyonlar + anlik PnL (Binance fiyatlarindan)."""
    conn = get_db_connection()
    trades = conn.execute("SELECT * FROM active_trades").fetchall()
    conn.close()
    trades = [dict(t) for t in trades]
    if not trades:
        return []
    try:
        tickers = await _get_futures_tickers_cached()
        price_map = {}
        for t in tickers:
            sym = t.get("symbol")
            p = t.get("price") or t.get("lastPrice")
            if sym and p is not None:
                price_map[sym] = float(p)
    except Exception as e:
        print(f"[!] PnL fiyat cekme hatasi: {str(e)[:80]}")
        for t in trades:
            t["unrealized_pnl"] = 0.0
            t["unrealized_pnl_pct"] = 0.0
            t["current_price"] = 0.0
        return trades

    # F124: Binance gercek notional (DB total_vol yerine gercek pozisyon)
    binance_positions = {}
    try:
        _pos_list = await asyncio.to_thread(order_manager.client.futures_position_information)
        # F139: DB'de olmayan snapshot/ghost pozisyonlarini atla
        _db_syms = {t.get("symbol") for t in trades}
        _all_open = [p for p in _pos_list if float(p.get("positionAmt", 0) or 0) != 0]
        _extra = len(_all_open) - len([p for p in _all_open if p.get("symbol") in _db_syms])
        if _extra > 0:
            print(f"[F139] {len(_all_open)} Binance poz / {len(_db_syms)} DB kaydi "
                  f"({_extra} snapshot-ignore)")
        for _p in _pos_list:
            _amt = float(_p.get("positionAmt", 0) or 0)
            if _amt != 0:
                _sym = _p.get("symbol")
                # F139: DB'de yoksa atla
                if _sym not in _db_syms:
                    continue
                _mark = float(_p.get("markPrice", 0) or 0)
                _entry = float(_p.get("entryPrice", 0) or 0)
                binance_positions[_sym] = {
                    "amt": abs(_amt),
                    "signed_amt": _amt,
                    "mark_price": _mark,
                    "entry_price": _entry,
                    "notional_actual": abs(_amt) * _mark if _mark > 0 else 0,
                    "notional_at_entry": abs(_amt) * _entry if _entry > 0 else 0,
                    "side": "BUY" if _amt > 0 else "SELL",
                    # F131: Binance'in hazir alanlari
                    "unrealized_profit": float(_p.get("unRealizedProfit", 0) or 0),
                    "liquidation_price": float(_p.get("liquidationPrice", 0) or 0),
                    "initial_margin": float(_p.get("initialMargin", 0) or 0),
                    "leverage": int(_p.get("leverage", 0) or 0),
                    "margin_type": _p.get("marginType", "") or "",
                    "break_even_price": float(_p.get("breakEvenPrice", 0) or 0),
                }
    except Exception as _be:
        print(f"[F124] Binance pozisyon sorgu hatasi: {str(_be)[:100]}")
    # F85: config'ten SL degerlerini al (strateji bazli)
    try:
        _cfg_all = load_config()
        _strats_cfg = _cfg_all.get("strategies", {}) or {}
    except Exception:
        _strats_cfg = {}

    for t in trades:
        sym = t.get("symbol", "")
        cur = price_map.get(sym)

        # F124: Binance'teki gercek notional'i ekle
        _bp = binance_positions.get(sym)
        if _bp:
            t["notional_actual"] = round(_bp["notional_actual"], 4)
            t["notional_at_entry"] = round(_bp["notional_at_entry"], 4)
            t["qty_actual"] = _bp["amt"]
            t["binance_mark_price"] = _bp["mark_price"]
            t["binance_entry_price"] = _bp["entry_price"]
            t["on_binance"] = True
            # F131: Binance hazir alanlari
            t["binance_unrealized_profit"] = _bp["unrealized_profit"]
            t["binance_liquidation_price"] = _bp["liquidation_price"]
            t["binance_initial_margin"] = _bp["initial_margin"]
            t["binance_leverage"] = _bp["leverage"]
            t["binance_margin_type"] = _bp["margin_type"]
            t["binance_break_even_price"] = _bp["break_even_price"]
        else:
            t["notional_actual"] = float(t.get("total_vol") or 0)
            t["qty_actual"] = 0
            t["on_binance"] = False

        # F85: SL + LIQ hesabi (cur olmasa da yapilabilir)
        try:
            _avg = float(t.get("avg_price") or 0)
            _lev = max(1, int(t.get("leverage") or 1))
            _ttype = t.get("trade_type", "BUY")
            _strat_name = t.get("strategy_name") or ""

            if _avg > 0:
                # FIX F101: Cross modda per-position LIQ gosterme (yaniltici)
                _margin_mode = _cfg_all.get("margin_mode", "cross")
                if _margin_mode == "isolated":
                    # ISOLATED: per-position LIQ hesabi (maintenance ~%0.5)
                    _maint = 0.005
                    if _ttype == "BUY":  # LONG
                        _liq = _avg * (1 - 1.0/_lev + _maint)
                    else:  # SHORT
                        _liq = _avg * (1 + 1.0/_lev - _maint)
                    t["liq_price"] = round(max(0, _liq), 10)
                else:
                    # CROSS: hesap bazli, per-position gosterme
                    t["liq_price"] = None
                    t["liq_price_note"] = "cross_mode"

                # SL hesabi: config'ten, LIQ-safe cap'li
                _s_cfg = _strats_cfg.get(_strat_name, {}) or {}
                _sl_cfg_pct = float(_s_cfg.get("stopLoss", 65))
                # LIQ-safe cap (F84 mantigi)
                _liq_pct = (100.0 / _lev) - 1.0
                _max_sl_pct = _liq_pct * 0.85
                _sl_pct = min(_sl_cfg_pct, _max_sl_pct)

                if _ttype == "BUY":
                    _sl_price = _avg * (1 - _sl_pct / 100.0)
                else:
                    _sl_price = _avg * (1 + _sl_pct / 100.0)
                t["sl_price"] = round(_sl_price, 10)
                t["sl_pct_effective"] = round(_sl_pct, 2)
        except Exception as _e:
            print(f"[F85] SL/LIQ hesap hatasi {sym}: {_e}")

        if cur is None:
            t["unrealized_pnl"] = 0.0
            t["unrealized_pnl_pct"] = 0.0
            t["current_price"] = 0.0
            continue
        avg = float(t.get("avg_price") or 0)
        vol = float(t.get("total_vol") or 0)
        ttype = t.get("trade_type", "BUY")
        if avg <= 0:
            t["unrealized_pnl"] = 0.0
            t["unrealized_pnl_pct"] = 0.0
            t["current_price"] = cur
            continue
        pnl_pct = (cur - avg) / avg if ttype == "BUY" else (avg - cur) / avg
        pnl_usdt = vol * pnl_pct
        t["current_price"] = cur
        t["unrealized_pnl"] = round(pnl_usdt, 4)
        t["unrealized_pnl_pct"] = round(pnl_pct * 100, 4)
    return trades


@app.get("/api/trade/active")
async def get_active_trades():
    conn = get_db_connection()
    trades = conn.execute("SELECT * FROM active_trades").fetchall()
    conn.close()
    return [dict(t) for t in trades]


@app.get("/api/trade/history")
async def get_trade_history(limit: int = 100, symbol: str = None):
    """F147: symbol filtresi + LRU cache (15 sn TTL).

    - symbol verilirse: SADECE o sembolun history'si (100 coin olcegi icin kritik)
    - symbol yoksa: eski davranis (son N kayit)
    - Ayni (symbol, limit) 15 sn icinde tekrarlanirsa cache'den doner
    """
    _sym_f147 = (symbol or "").strip().upper() or None
    _key_f147 = f"{_sym_f147 or '_ALL_'}:{limit}"

    _cached_f147 = _f147_cache_get(_key_f147)
    if _cached_f147 is not None:
        return _cached_f147

    conn = get_db_connection()
    if _sym_f147:
        rows = conn.execute(
            "SELECT * FROM trade_history WHERE symbol = ? "
            "ORDER BY exit_time DESC LIMIT ?",
            (_sym_f147, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM trade_history ORDER BY exit_time DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()

    result = [dict(r) for r in rows]
    _f147_cache_put(_key_f147, result)
    return result


# ----------------------------------------------------------------------
# STRATEJİ İSTATİSTİKLERİ
# ----------------------------------------------------------------------
@app.get("/api/stats/strategies")
async def get_strategy_stats():
    """
    Her stratejinin performansı:
    - Toplam işlem
    - Kazanç/kayıp sayısı
    - Win rate
    - Toplam net PNL
    - Ort. PNL %
    - En iyi / en kötü işlem
    """
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            COALESCE(strategy_name, 'UNKNOWN') as strategy_name,
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_amount <= 0 THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(pnl_amount), 4) as total_pnl,
            ROUND(AVG(pnl_pct), 4) as avg_pnl_pct,
            ROUND(MAX(pnl_amount), 4) as best_trade,
            ROUND(MIN(pnl_amount), 4) as worst_trade,
            ROUND(AVG(dca_count), 2) as avg_dca
        FROM trade_history
        GROUP BY strategy_name
        ORDER BY total_pnl DESC
    """).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        total = d["total_trades"] or 0
        wins = d["wins"] or 0
        d["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0
        result.append(d)
    return result


@app.get("/api/stats/daily")
async def get_daily_stats(days: int = 7):
    """
    Son N günün günlük PNL özeti.
    TÜRKİYE SAATİ (UTC+3) kullanır - frontend ile uyumlu.
    """
    conn = get_db_connection()
    # ⚡ +3 saat ekleyip TR saat dilimine göre grupluyoruz
    rows = conn.execute("""
        SELECT 
            DATE(exit_time + 10800, 'unixepoch') as date,
            COUNT(*) as trades,
            ROUND(SUM(pnl_amount), 4) as net_pnl,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_amount <= 0 THEN 1 ELSE 0 END) as losses
        FROM trade_history
        WHERE exit_time >= ?
        GROUP BY DATE(exit_time + 10800, 'unixepoch')
        ORDER BY date DESC
    """, (int(time.time()) - (days * 86400),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/stats/signals")
async def get_signal_stats():
    """Sinyal istatistikleri + tutarlılık kontrolü."""
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    opened = conn.execute("SELECT COUNT(*) FROM signals WHERE opened_position = 1").fetchone()[0]
    skipped = conn.execute("SELECT COUNT(*) FROM signals WHERE opened_position = 0").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM active_trades").fetchone()[0]
    closed = conn.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0]
    conn.close()
    
    consistent = (opened == active + closed)
    
    return {
        "total_signals": total,
        "opened_signals": opened,
        "skipped_signals": skipped,
        "active_positions": active,
        "closed_positions": closed,
        "sum_check": active + closed,
        "consistent": consistent,
        "difference": opened - (active + closed)
    }


@app.get("/api/stats/funding")
async def get_funding_stats():
    """
    FUNDING_ARBITRAGE stratejisi icin ozet istatistik.
    trade_history'de strategy_name='FUNDING_ARBITRAGE' olan kayitlari analiz eder.
    """
    conn = get_db_connection()

    try:
        rows = conn.execute("""
            SELECT
                symbol,
                trade_type,
                total_vol,
                entry_price,
                exit_price,
                pnl_amount,
                pnl_pct,
                funding_fee,
                commission,
                close_reason,
                entry_time,
                exit_time,
                leverage
            FROM trade_history
            WHERE strategy_name = 'FUNDING_ARBITRAGE'
            ORDER BY exit_time DESC
        """).fetchall()
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}

    conn.close()

    if not rows:
        return {
            "status": "no_data",
            "message": "Henuz funding arbitrage islemi yok"
        }

    total_trades = len(rows)
    total_pnl = 0.0
    total_funding = 0.0
    total_commission = 0.0
    wins = 0
    long_trades = 0
    short_trades = 0
    funding_pos_count = 0
    funding_neg_count = 0

    by_symbol = {}
    reasons = {}

    for r in rows:
        r = dict(r)
        pnl = float(r.get('pnl_amount') or 0)
        fund = float(r.get('funding_fee') or 0)
        comm = float(r.get('commission') or 0)
        vol = float(r.get('total_vol') or 0)
        sym = r.get('symbol') or 'UNKNOWN'
        ttype = r.get('trade_type') or 'BUY'
        reason = (r.get('close_reason') or 'UNKNOWN').upper()

        total_pnl += pnl
        total_funding += fund
        total_commission += comm
        if pnl > 0:
            wins += 1
        if ttype == 'BUY':
            long_trades += 1
        else:
            short_trades += 1
        if fund > 0:
            funding_pos_count += 1
        elif fund < 0:
            funding_neg_count += 1

        # Sembol bazli
        if sym not in by_symbol:
            by_symbol[sym] = {
                'trades': 0, 'wins': 0,
                'pnl': 0.0, 'funding': 0.0, 'commission': 0.0,
                'long': 0, 'short': 0,
            }
        s = by_symbol[sym]
        s['trades'] += 1
        s['pnl'] += pnl
        s['funding'] += fund
        s['commission'] += comm
        if pnl > 0:
            s['wins'] += 1
        if ttype == 'BUY':
            s['long'] += 1
        else:
            s['short'] += 1

        # Kapanis sebebi normalize
        if 'FUNDING_TP' in reason or ('TP' in reason and 'SL' not in reason):
            key = 'TP'
        elif 'FUNDING_SL' in reason or 'SL' in reason or 'STOP' in reason:
            key = 'SL'
        elif 'MANUAL' in reason:
            key = 'MANUAL'
        else:
            key = 'DIGER'
        reasons[key] = reasons.get(key, 0) + 1

    avg_pnl = total_pnl / total_trades if total_trades else 0
    avg_funding = total_funding / total_trades if total_trades else 0
    win_rate = (wins / total_trades * 100) if total_trades else 0

    # Sembol listesi (PnL DESC)
    by_symbol_list = []
    for k, v in by_symbol.items():
        by_symbol_list.append({
            'symbol': k,
            'trades': v['trades'],
            'wins': v['wins'],
            'win_rate': round(v['wins'] / v['trades'] * 100, 2) if v['trades'] > 0 else 0,
            'total_pnl': round(v['pnl'], 4),
            'total_funding': round(v['funding'], 4),
            'total_commission': round(v['commission'], 4),
            'long': v['long'],
            'short': v['short'],
        })
    by_symbol_list.sort(key=lambda x: x['total_pnl'], reverse=True)

    return {
        "status": "success",
        "summary": {
            "total_trades": total_trades,
            "total_pnl": round(total_pnl, 4),
            "total_funding": round(total_funding, 4),
            "total_commission": round(total_commission, 4),
            "avg_pnl_per_trade": round(avg_pnl, 4),
            "avg_funding_per_trade": round(avg_funding, 4),
            "wins": wins,
            "losses": total_trades - wins,
            "win_rate": round(win_rate, 2),
            "long_trades": long_trades,
            "short_trades": short_trades,
            "funding_income_count": funding_pos_count,
            "funding_cost_count": funding_neg_count,
        },
        "by_symbol": by_symbol_list[:50],
        "reasons": reasons,
    }


@app.post("/api/stats/reset")
async def reset_stats():
    """Tüm istatistik verilerini sıfırlar (test için)."""
    conn = get_db_connection()
    conn.execute("DELETE FROM trade_history")
    conn.execute("DELETE FROM signals")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "İstatistik verileri sıfırlandı"}

# ----------------------------------------------------------------------
# ADMIN - TÜM VERİYİ SIFIRLA (test için)
# ----------------------------------------------------------------------
@app.get("/api/health/dca")
async def dca_health():
    """
    DCA saglik kontrolu:
    - initial_price == avg_price olanlar (bug gostergesi)
    - dca_count > 0 olup initial_price = avg_price olanlar
    """
    import json as _json
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, symbol, strategy_name, initial_price, avg_price,
               total_vol, dca_count, dca_history
        FROM active_trades
        WHERE dca_count > 0
    """).fetchall()
    conn.close()

    issues = []
    for r in rows:
        r = dict(r)
        ini = float(r.get("initial_price") or 0)
        avg = float(r.get("avg_price") or 0)
        cnt = int(r.get("dca_count") or 0)

        if ini <= 0 or avg <= 0:
            continue

        # initial_price == avg_price (DCA yapildiysa anormal)
        if abs(ini - avg) < 1e-9:
            issues.append({
                "id": r["id"],
                "symbol": r["symbol"],
                "strategy": r.get("strategy_name"),
                "issue": "initial_price == avg_price",
                "initial_price": ini,
                "avg_price": avg,
                "dca_count": cnt,
            })
            continue

        # DCA history tetik fiyat kontrolu
        try:
            dh = _json.loads(r.get("dca_history") or "[]")
            if dh and cnt > 0:
                # Ilk DCA tetiginde initial_price'a gore beklenen
                first_trigger = float(dh[0].get("price", 0) or 0)
                # Bu tetik fiyat initial'dan asagi mi?
                if first_trigger > ini:
                    issues.append({
                        "id": r["id"],
                        "symbol": r["symbol"],
                        "strategy": r.get("strategy_name"),
                        "issue": "DCA1 fiyati initial_price'tan yukarida",
                        "initial_price": ini,
                        "first_dca": first_trigger,
                        "dca_count": cnt,
                    })
        except Exception:
            pass

    return {
        "status": "ok",
        "total_dca_positions": len(rows),
        "issues_found": len(issues),
        "issues": issues,
    }


@app.post("/api/admin/reset-all")
async def admin_reset_all():
    """
    Test amaçlı: tüm sinyalleri, açık pozisyonları ve işlem geçmişini siler.
    DB'yi tertemiz başlatır.
    """
    conn = get_db_connection()
    
    # Sayıları al
    counts = {
        "signals": conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0],
        "active_trades": conn.execute("SELECT COUNT(*) FROM active_trades").fetchone()[0],
        "trade_history": conn.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0],
    }
    
    # Sil
    conn.execute("DELETE FROM signals")
    conn.execute("DELETE FROM active_trades")
    conn.execute("DELETE FROM trade_history")
    conn.commit()
    conn.close()
    
    print(f"[ADMIN] Sıfırlama: {counts['signals']} sinyal, {counts['active_trades']} pozisyon, {counts['trade_history']} geçmiş silindi")
    
    return {"status": "success", "cleared": counts}

# ----------------------------------------------------------------------
# ADMIN - ANORMAL ISLEMLERI TEMIZLE
# Testnet fiyat hatalarindan kaynaklanan bozuk kayitlari siler
# ----------------------------------------------------------------------
@app.post("/api/admin/clean-anomalies")
async def admin_clean_anomalies(min_pnl_pct: float = 30.0, min_ratio: float = 1.5):
    """
    Testnet fiyat hatasi kaynakli anormal islemleri siler.
    
    Args:
        min_pnl_pct: Bu yuzdeden fazla (mutlak deger) kâr/zarar = anormal
        min_ratio: exit/entry orani bu degerin disindaysa = anormal
    """
    conn = get_db_connection()
    
    # Once anormal kayitlari bul (rapor icin)
    rows = conn.execute("""
        SELECT id, symbol, entry_price, exit_price, pnl_pct
        FROM trade_history
        WHERE ABS(pnl_pct) > ?
           OR (entry_price > 0 AND (
                (exit_price / entry_price) > ?
                OR (exit_price / entry_price) < ?
           ))
    """, (min_pnl_pct, min_ratio, 1.0 / min_ratio)).fetchall()
    
    anomalies = [dict(r) for r in rows]
    
    # Sil
    conn.execute("""
        DELETE FROM trade_history
        WHERE ABS(pnl_pct) > ?
           OR (entry_price > 0 AND (
                (exit_price / entry_price) > ?
                OR (exit_price / entry_price) < ?
           ))
    """, (min_pnl_pct, min_ratio, 1.0 / min_ratio))
    
    conn.commit()
    conn.close()
    
    print(f"[ADMIN] {len(anomalies)} anormal islem silindi")
    for a in anomalies[:10]:
        print(f"      - {a['symbol']}: giris={a['entry_price']}, cikis={a['exit_price']}, pnl={a['pnl_pct']:.2f}%")
    
    return {
        "status": "success",
        "deleted_count": len(anomalies),
        "deleted": anomalies[:50]
    }

# ----------------------------------------------------------------------
# GRID STATE - Backend grid durumu (tek dogru kaynak)
# ----------------------------------------------------------------------
@app.get("/api/grid/state/{symbol}")
async def get_grid_state(symbol: str):
    """
    Sembolun mevcut grid durumunu dondurur.
    Frontend grafigi bu veriden cizer -> sapma olmaz.
    """
    import json as _json
    sym = symbol.replace(".P", "").upper()
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM grid_state WHERE symbol = ?", (sym,)
        ).fetchone()
        conn.close()

        if not row:
            return {"status": "not_found", "symbol": sym}

        d = dict(row)
        levels = []
        try:
            levels = _json.loads(d.get("levels_json") or "[]")
        except Exception:
            levels = []

        now = int(time.time())
        age = now - int(d.get("updated_at") or now)

        return {
            "status": "ok",
            "symbol": sym,
            "strategy": d.get("strategy_name"),
            "group_id": d.get("group_id"),
            "reference": d.get("reference"),
            "top": d.get("top"),
            "bottom": d.get("bottom"),
            "levels": levels,
            "interval": d.get("interval"),
            "mode": d.get("mode"),
            "recenter_ts": d.get("recenter_ts"),
            "updated_at": d.get("updated_at"),
            "age_sec": age,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/grid/state-all")
async def get_grid_state_all():
    """Tum aktif grid state'lerini dondurur (toplu)."""
    import json as _json
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM grid_state ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()

        out = []
        for row in rows:
            d = dict(row)
            try:
                d["levels"] = _json.loads(d.get("levels_json") or "[]")
            except Exception:
                d["levels"] = []
            out.append(d)
        return {"status": "ok", "count": len(out), "data": out}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------------------------------------------------------------
# FUNDING RATE - Anlık funding oranı ve sonraki zaman
# ----------------------------------------------------------------------
@app.get("/api/funding/{symbol}")
async def get_funding(symbol: str):
    """Sembol icin anlik funding oranini ve sonraki funding zamanini doner."""
    try:
        premium = client.futures_mark_price(symbol=symbol)
        funding_rate = float(premium.get("lastFundingRate", 0))
        next_funding_time = int(premium.get("nextFundingTime", 0))
        mark_price = float(premium.get("markPrice", 0))
        
        # 8 saatlik funding maliyeti (pozisyon basina)
        daily_funding_pct = funding_rate * 3 * 100  # gunde 3 kez
        
        return {
            "status": "success",
            "symbol": symbol,
            "funding_rate": funding_rate,
            "funding_rate_pct": round(funding_rate * 100, 4),
            "daily_funding_pct": round(daily_funding_pct, 4),
            "next_funding_time": next_funding_time,
            "mark_price": mark_price,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/funding-batch")
async def get_funding_batch(symbols: str = ""):
    """Birden fazla sembol icin funding oranlarini toplu doner."""
    try:
        premiums = client.futures_mark_price()
        symbol_set = set(s.strip().upper() for s in symbols.split(",") if s.strip())
        
        result = {}
        for p in premiums:
            sym = p.get("symbol", "")
            if not symbol_set or sym in symbol_set:
                result[sym] = {
                    "funding_rate": float(p.get("lastFundingRate", 0)),
                    "next_funding_time": int(p.get("nextFundingTime", 0)),
                    "mark_price": float(p.get("markPrice", 0)),
                }
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------------------------------------------------------------
# KOMISYON ORANI - Sembol icin gercek taker/maker orani
# ----------------------------------------------------------------------
@app.get("/api/commission/{symbol}")
async def get_commission(symbol: str):
    """Sembol icin gercek komisyon oranini doner (VIP + BNB dahil)."""
    try:
        rates = order_manager.get_commission_rate(symbol)
        return {
            "status": "success",
            "symbol": symbol,
            "taker": rates.get("taker", 0.0004),
            "maker": rates.get("maker", 0.0002),
            "taker_pct": round(rates.get("taker", 0.0004) * 100, 4),
            "maker_pct": round(rates.get("maker", 0.0002) * 100, 4),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------------------------------------------------------------
# İŞLEM GEÇMİŞİ - KALICI SİLME (frontend + DB)
# ----------------------------------------------------------------------
@app.delete("/api/trade/history/{trade_id}")
async def delete_trade_history(trade_id: int):
    """
    Belirtilen işlem kaydını DB'den kalıcı olarak siler.
    Frontend'deki kullanıcı 'X' butonuyla tetikler.
    """
    conn = get_db_connection()
    row = conn.execute("SELECT id, symbol FROM trade_history WHERE id = ?", (trade_id,)).fetchone()
    
    if not row:
        conn.close()
        return {"status": "error", "message": "İşlem bulunamadı"}
    
    symbol = row["symbol"]
    conn.execute("DELETE FROM trade_history WHERE id = ?", (trade_id,))
    conn.commit()
    conn.close()
    
    print(f"[DELETE] İşlem #{trade_id} ({symbol}) kalıcı olarak silindi")
    
    return {"status": "success", "deleted_id": trade_id, "symbol": symbol}

# ----------------------------------------------------------------------
# TELEGRAM BİLDİRİM ENDPOINT'LERİ
# ----------------------------------------------------------------------
@app.get("/api/telegram/status")
async def telegram_status():
    """Telegram ayarları yapılmış mı?"""
    return {
        "status": "success",
        "configured": telegram_notifier.is_configured(),
    }


@app.post("/api/telegram/test")
async def telegram_test():
    """Test mesajı gönderir."""
    if not telegram_notifier.is_configured():
        return {
            "status": "error",
            "message": "Telegram ayarları eksik. .env dosyasında TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID olmalı."
        }
    
    result = await telegram_notifier.send_telegram_message(
        "🔔 <b>Broker System</b>\n\n"
        "✅ Telegram bildirimleri başarıyla bağlandı!\n"
        "Artık sinyal ve kapanış bildirimleri buraya gelecek."
    )
    
    if result.get("ok"):
        return {"status": "success", "message": "Test mesajı gönderildi"}
    else:
        return {"status": "error", "message": result.get("description") or result.get("message") or "Bilinmeyen hata"}

# ----------------------------------------------------------------------
# İSTATİSTİK - Sembol bazlı analiz
# ----------------------------------------------------------------------
@app.get("/api/stats/symbols")
async def get_symbol_stats(min_trades: int = 1):
    """Sembol başına kâr/zarar istatistikleri."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            symbol,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_amount <= 0 THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(pnl_amount), 4) as total_pnl,
            ROUND(AVG(pnl_pct), 4) as avg_pnl_pct,
            ROUND(MAX(pnl_amount), 4) as best,
            ROUND(MIN(pnl_amount), 4) as worst
        FROM trade_history
        WHERE ABS(pnl_amount) < (total_vol * 5)
        GROUP BY symbol
        HAVING COUNT(*) >= ?
        ORDER BY total_pnl DESC
    """, (min_trades,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        total = d["trades"] or 0
        wins = d["wins"] or 0
        d["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0
        result.append(d)
    return result


# ----------------------------------------------------------------------
# İSTATİSTİK - Kapanış sebebi analizi
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# BACKTEST - Async task-based backtest engine
# ----------------------------------------------------------------------
from backend import backtest_engine
import uuid
from datetime import datetime
import io
import csv
from fastapi.responses import StreamingResponse


@app.post("/api/backtest/start")
async def backtest_start(payload: dict):
    """Backtest baslatir, task_id doner."""
    symbol = str(payload.get("symbol", "BTCUSDT")).upper()
    strategy = payload.get("strategy", "RSI_SCALPER")
    params = payload.get("params", {})
    initial_balance = float(payload.get("initial_balance", 1000))
    interval = payload.get("interval", "4h")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    mode = str(payload.get("mode", "futures")).lower()  # futures | spot

    task_id = str(uuid.uuid4())[:8]

    backtest_engine.create_task(task_id, symbol, strategy, params, initial_balance, interval)

    # Arka planda calistir
    asyncio.create_task(asyncio.to_thread(
        backtest_engine.run_backtest_sync,
        task_id, client, symbol, strategy, params, initial_balance, interval, start_date, end_date, mode
    ))

    return {"status": "success", "task_id": task_id}


@app.get("/api/backtest/status/{task_id}")
async def backtest_status(task_id: str):
    task = backtest_engine.get_task(task_id)
    if not task:
        return {"status": "not_found"}
    return {
        "status": task["status"],
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
    }


@app.get("/api/backtest/result/{task_id}")
async def backtest_result(task_id: str):
    task = backtest_engine.get_task(task_id)
    if not task:
        return {"status": "not_found"}
    if task["status"] == "error":
        return {"status": "error", "message": task.get("message", "")}
    if task["status"] != "done":
        return {"status": task["status"], "message": task.get("message", "")}
    return {"status": "done", "result": task["result"]}


@app.get("/api/backtest/csv/{task_id}")
async def backtest_csv(task_id: str):
    task = backtest_engine.get_task(task_id)
    if not task or task["status"] != "done":
        return {"status": "error", "message": "Sonuc hazir degil"}

    result = task["result"]
    trades = result.get("trades", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["#", "Entry Time", "Exit Time", "Side", "Entry Price", "Exit Price",
                     "Volume USDT", "PnL %", "PnL USDT", "Reason", "DCA"])

    for i, t in enumerate(trades, 1):
        try:
            et = datetime.fromtimestamp(t["entry_time"]).strftime("%Y-%m-%d %H:%M:%S")
            xt = datetime.fromtimestamp(t["exit_time"]).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            et = str(t.get("entry_time", ""))
            xt = str(t.get("exit_time", ""))

        writer.writerow([
            i, et, xt, t["side"],
            t["entry_price"], t["exit_price"], t["total_vol"],
            t["pnl_pct"], t["pnl_amount"], t["reason"], t["dca_count"],
        ])

    output.seek(0)
    filename = f"backtest_{result['symbol']}_{task_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/stats/symbols-by-count")
async def get_symbols_by_count(min_trades: int = 1):
    """Coin islem sayisina gore siralama (buyukten kucuge)."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            symbol,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_amount <= 0 THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(pnl_amount), 4) as total_pnl,
            ROUND(AVG(pnl_pct), 4) as avg_pnl_pct,
            ROUND(MAX(pnl_amount), 4) as best,
            ROUND(MIN(pnl_amount), 4) as worst
        FROM trade_history
        WHERE ABS(pnl_amount) < (total_vol * 5)
        GROUP BY symbol
        HAVING COUNT(*) >= ?
        ORDER BY trades DESC, total_pnl DESC
    """, (min_trades,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        total = d["trades"] or 0
        wins = d["wins"] or 0
        d["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0
        result.append(d)
    return result


@app.get("/api/stats/close-reasons")
async def get_close_reason_stats():
    """Kapanış sebeplerine göre analiz (TP/Trailing/SL)."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            CASE 
                WHEN close_reason LIKE '%PARTIAL%' THEN 'PARTIAL TP'
                WHEN close_reason LIKE '%AI-TTP%' THEN 'AI TTP'
                WHEN close_reason LIKE '%AI TTP%' THEN 'AI TTP'
                WHEN close_reason LIKE '%TRAILING%' THEN 'AI TTP'
                WHEN close_reason LIKE '%STOP%' THEN 'STOP LOSS'
                WHEN close_reason LIKE '%DELIST%' THEN 'DELISTED'
                WHEN close_reason LIKE '%TIME%' THEN 'TIME LIMIT'
                WHEN close_reason LIKE '%TAKE%' THEN 'TAKE PROFIT'
                ELSE 'DIGER'
            END as reason,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl_amount), 4) as total_pnl,
            ROUND(AVG(pnl_pct), 4) as avg_pnl_pct
        FROM trade_history
        WHERE ABS(pnl_amount) < (total_vol * 5)
        GROUP BY reason
        ORDER BY total_pnl DESC
    """).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        total = d["trades"] or 0
        wins = d["wins"] or 0
        d["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0
        result.append(d)
    return result


# ======================================================================
# DB SYNC
# ======================================================================
DB_SYNC_PATH = Path(__file__).resolve().parent / "bot_data.db"


async def _sync_push_once() -> bool:
    # FIX B2: WAL checkpoint - son veriyi .db'ye flush et
    try:
        _ck = sqlite3.connect(str(DB_SYNC_PATH), timeout=10.0)
        _ck.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        _ck.close()
    except Exception as _ck_e:
        print(f"[SYNC] WAL checkpoint hatasi (devam): {_ck_e}")

    try:
        if not DB_SYNC_PATH.exists():
            return False
        with open(DB_SYNC_PATH, 'rb') as f:
            data = f.read()
        if len(data) < 1024:
            return False
        url = f"{CLOUD_SYNC_URL}/api/sync/db-receive"
        auth_str = f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()
        req = _urlreq.Request(
            url, data=data, method='POST',
            headers={
                'Content-Type': 'application/octet-stream',
                'X-Sync-Token': SYNC_TOKEN,
                'Authorization': f'Basic {auth_b64}',
                'Content-Length': str(len(data)),
            }
        )
        def _do():
            try:
                with _urlreq.urlopen(req, timeout=20) as resp:
                    return resp.status, resp.read()[:200]
            except _urlerr.HTTPError as he:
                return he.code, b''
            except Exception as e:
                return -1, str(e).encode()[:200]
        status, body = await asyncio.to_thread(_do)
        if status == 200:
            # FIX SP1: basari logu 5 dk'da 1
            import time as _t_sp1
            _now_sp1 = _t_sp1.time()
            if not hasattr(_sync_push_once, "_last_ok_log") or (_now_sp1 - _sync_push_once._last_ok_log) >= 300:
                _sync_push_once._last_ok_log = _now_sp1
                print(f"[SYNC] push OK | {len(data)} byte")
            return True
        # FIX SP1: hata logu 5 dk'da 1
        import time as _t_sp1b
        _now_sp1b = _t_sp1b.time()
        if not hasattr(_sync_push_once, "_last_err_log") or (_now_sp1b - _sync_push_once._last_err_log) >= 300:
            _sync_push_once._last_err_log = _now_sp1b
            print(f"[SYNC] push hata | status={status} | {body[:100]}")
        return False
    except Exception as e:
        print(f"[SYNC] push exception: {e}")
        return False


async def _sync_loop():
    last_hash = None
    print("[SYNC] Loop basladi")
    while True:
        try:
            await asyncio.sleep(SYNC_INTERVAL_SEC)
            if not DB_SYNC_PATH.exists():
                continue
            with open(DB_SYNC_PATH, 'rb') as f:
                data = f.read()
            cur_hash = _hashlib.md5(data).hexdigest()
            if cur_hash == last_hash:
                continue
            if await _sync_push_once():
                last_hash = cur_hash
        except asyncio.CancelledError:
            print("[SYNC] Loop durduruldu")
            raise
        except Exception as e:
            print(f"[SYNC] Loop hata: {e}")
            await asyncio.sleep(60)


@app.post("/api/sync/db-receive")
async def sync_db_receive(request: Request):
    if not IS_REPLICA:
        return {"status": "ignored", "reason": "not_replica"}
    token = request.headers.get("X-Sync-Token", "")
    if not SYNC_TOKEN or token != SYNC_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid sync token")
    body = await request.body()
    if len(body) < 1024:
        raise HTTPException(status_code=400, detail="DB cok kucuk")
    db_path = Path(__file__).resolve().parent / "bot_data.db"
    try:
        if db_path.exists():
            shutil.copy2(str(db_path), str(db_path) + ".bak_sync_recv")
    except Exception as e:
        print(f"[SYNC-RECV] yedek uyari: {e}")
    tmp = str(db_path) + ".sync_tmp"
    try:
        with open(tmp, 'wb') as f:
            f.write(body)
        os.replace(tmp, str(db_path))
        # FIX K1: WAL/SHM temizle (eski WAL yeni DB'ye karismasin)
        for _ext in ("-wal", "-shm"):
            _p = Path(str(db_path) + _ext)
            try:
                if _p.exists():
                    _p.unlink()
                    print(f"[SYNC-RECV] {_p.name} temizlendi")
            except Exception as _e_clean:
                print(f"[SYNC-RECV] {_p.name} temizleme hatasi: {_e_clean}")
        print(f"[SYNC-RECV] DB guncellendi | {len(body)} byte")
        return {"status": "ok", "size": len(body)}
    except Exception as e:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Yazma hatasi: {e}")

